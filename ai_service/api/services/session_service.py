"""
Session management service for questionnaire interactions.
"""

import logging
import json
import uuid
import time
import os
import shutil
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import asyncio
import aiofiles

from ai_service.core.config import settings

logger = logging.getLogger(__name__)

class SessionStore:
    """Enhanced session store for questionnaire interactions with persistence."""

    def __init__(self, persistence_dir: Optional[str] = None):
        """
        Initialize the session store with persistence support.

        Args:
            persistence_dir: Directory for persisting session data
        """
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_expiry: Dict[str, float] = {}
        self.default_expiry = 3600 * 24 * settings.SESSION_EXPIRY_DAYS  # Default days in seconds

        # Use the configured session directory or the provided one
        self.persistence_dir = persistence_dir or settings.SESSION_DIR
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()

        # Create persistence directory
        if not os.path.isdir(self.persistence_dir):
            try:
                os.makedirs(self.persistence_dir, exist_ok=True)
                # Ensure the directory has proper permissions (readable/writable)
                os.chmod(self.persistence_dir, 0o755)  # Standard permissions
                logger.info(f"Session persistence directory created: {self.persistence_dir}")
            except Exception as e:
                logger.error(f"Failed to create persistence directory: {str(e)}")
                raise RuntimeError(f"Cannot create session directory: {str(e)}")

    async def _load_session_file(self, session_id: str) -> bool:
        """
        Load a session from a file.

        Args:
            session_id: The session ID

        Returns:
            True if loaded successfully, False otherwise
        """
        filepath = os.path.join(self.persistence_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            return False

        try:
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                if not content.strip():
                    logger.error(f"Empty session file: {session_id}")
                    # Remove the invalid file
                    os.remove(filepath)
                    return False

                # Parse the content
                session_data = json.loads(content)
                self.sessions[session_id] = session_data

                # Set expiry based on updated_at time + default expiry
                updated_at = session_data.get("updated_at")
                if updated_at:
                    try:
                        dt = datetime.fromisoformat(updated_at)
                        # Convert to timestamp and add expiry
                        self.session_expiry[session_id] = dt.timestamp() + self.default_expiry
                    except (ValueError, TypeError):
                        # If date parsing fails, use current time + expiry
                        self.session_expiry[session_id] = time.time() + self.default_expiry
                else:
                    # Use current time + expiry if no updated_at date
                    self.session_expiry[session_id] = time.time() + self.default_expiry

                logger.info(f"Session loaded from file: {session_id}")
                return True

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing session file {session_id}: {str(e)}")
            # Make a backup of the corrupted file
            backup_file = f"{filepath}.corrupted"
            try:
                shutil.copy2(filepath, backup_file)
                logger.info(f"Backup of corrupted session file created: {backup_file}")
                # Remove the invalid file
                os.remove(filepath)
            except Exception as backup_err:
                logger.error(f"Failed to backup corrupted session file: {str(backup_err)}")

            return False
        except Exception as e:
            logger.error(f"Error reading session file {session_id}: {str(e)}")
            return False

    async def _persist_session(self, session_id: str) -> bool:
        """
        Persist a session to a file.

        Args:
            session_id: The session ID

        Returns:
            True if persisted successfully, False otherwise
        """
        if session_id not in self.sessions:
            logger.warning(f"Cannot persist non-existent session: {session_id}")
            return False

        # Get session data
        session_data = self.sessions[session_id]

        # Create filepath
        filepath = os.path.join(self.persistence_dir, f"{session_id}.json")

        # Use a temporary file to ensure atomic writes
        temp_filepath = f"{filepath}.tmp"

        try:
            # Convert to JSON
            json_data = json.dumps(session_data, indent=2)

            # Write to temporary file first
            async with aiofiles.open(temp_filepath, 'w') as f:
                await f.write(json_data)

            # Rename the temporary file to the final name (atomic operation)
            os.replace(temp_filepath, filepath)

            logger.info(f"Session persisted to file: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error persisting session {session_id}: {str(e)}")
            # Clean up the temporary file if it exists
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except Exception:
                    pass
            return False

    async def create_session(self, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session or update an existing one.

        Args:
            session_id: Optional session ID (generates one if not provided)
            data: Optional initial session data

        Returns:
            The session ID
        """
        # Generate a session ID if not provided
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex}"

        # Initialize or update session data
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "data": data or {},
                "responses": [],
                "current_confidence": 20.0,
                "questions_asked": [],
                "questions_answered": 0,
                "session_metadata": {
                    "client_ip": None,
                    "user_agent": None,
                    "started_at": datetime.now().isoformat()
                }
            }
        else:
            self.sessions[session_id]["updated_at"] = datetime.now().isoformat()
            if data:
                self.sessions[session_id]["data"] = {**self.sessions[session_id].get("data", {}), **data}

        # Set or update expiry time
        self.session_expiry[session_id] = time.time() + self.default_expiry

        # Persist the session
        await self._persist_session(session_id)

        logger.info(f"Session created or updated: {session_id}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID.

        Args:
            session_id: The session ID

        Returns:
            The session data or None if not found
        """
        # Check if session is in memory
        if session_id not in self.sessions:
            # Try to load from disk if not in memory
            loaded = await self._load_session_file(session_id)
            if not loaded:
                logger.warning(f"Session not found: {session_id}")
                return None

        # Check if session has expired
        if time.time() > self.session_expiry.get(session_id, 0):
            logger.warning(f"Session expired: {session_id}")
            await self.delete_session(session_id)
            return None

        # Refresh expiry time
        self.session_expiry[session_id] = time.time() + self.default_expiry

        # Automatic cleanup check
        if time.time() - self.last_cleanup > self.cleanup_interval:
            asyncio.create_task(self.cleanup_expired_sessions())
            self.last_cleanup = time.time()

        return self.sessions[session_id]

    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: The session ID
            data: The data to update

        Returns:
            True if successful, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot update non-existent session: {session_id}")
            return False

        # Update session data
        for key, value in data.items():
            if key == "data" and isinstance(value, dict):
                # Merge with existing data
                if "data" not in session:
                    session["data"] = {}
                session["data"].update(value)
            else:
                # Direct replacement for other fields
                session[key] = value

        session["updated_at"] = datetime.now().isoformat()

        # Refresh expiry time
        self.session_expiry[session_id] = time.time() + self.default_expiry

        # Persist changes
        await self._persist_session(session_id)

        logger.info(f"Session updated: {session_id}")
        return True

    async def add_question_response(self, session_id: str, question_id: str, question_text: str, answer: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a question response to a session.

        Args:
            session_id: The session ID
            question_id: The question ID
            question_text: The question text
            answer: The answer provided
            metadata: Optional additional metadata for the response

        Returns:
            True if successful, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot add response to non-existent session: {session_id}")
            return False

        # Initialize responses array if not present
        if "responses" not in session:
            session["responses"] = []

        # Format the response
        response = {
            "question_id": question_id,
            "question": question_text,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        }

        # Add metadata if provided
        if metadata and isinstance(metadata, dict):
            response["metadata"] = metadata

        # Add response to the session
        session["responses"].append(response)

        # Update last activity timestamp
        session["last_activity"] = datetime.now().isoformat()

        # Persist the session
        return await self.update_session(session_id, session)

    async def get_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all responses for a session.

        Args:
            session_id: The session ID

        Returns:
            List of responses
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot get responses for non-existent session: {session_id}")
            return []

        return session.get("responses", [])

    async def get_confidence(self, session_id: str) -> float:
        """
        Get the current confidence score for a session.

        Args:
            session_id: The session ID

        Returns:
            The confidence score (0-100)
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot get confidence for non-existent session: {session_id}")
            return 20.0  # Default starting confidence

        return session.get("current_confidence", 20.0)

    async def update_confidence(self, session_id: str, confidence: float) -> bool:
        """
        Update the confidence score for a session.

        Args:
            session_id: The session ID
            confidence: The new confidence score

        Returns:
            True if successful, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot update confidence for non-existent session: {session_id}")
            return False

        session["current_confidence"] = confidence
        session["updated_at"] = datetime.now().isoformat()

        # Refresh expiry time
        self.session_expiry[session_id] = time.time() + self.default_expiry

        # Persist changes
        await self._persist_session(session_id)

        logger.info(f"Session confidence updated: {session_id} => {confidence}")
        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions:
            logger.warning(f"Cannot delete non-existent session: {session_id}")
            return False

        # Delete from memory
        del self.sessions[session_id]
        if session_id in self.session_expiry:
            del self.session_expiry[session_id]

        # Delete persisted file if it exists
        filepath = os.path.join(self.persistence_dir, f"{session_id}.json")
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                logger.error(f"Error deleting session file {session_id}: {str(e)}")
                return False

        logger.info(f"Session deleted: {session_id}")
        return True

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        expired_sessions = [sid for sid, expiry in self.session_expiry.items()
                           if current_time > expiry]

        for session_id in expired_sessions:
            await self.delete_session(session_id)

        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        self.last_cleanup = current_time
        return len(expired_sessions)

    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        Get a list of all sessions with their metadata.

        Returns:
            List of session metadata
        """
        sessions_list = []

        # Add all in-memory sessions
        for session_id, session_data in self.sessions.items():
            sessions_list.append({
                "session_id": session_id,
                "created_at": session_data.get("created_at"),
                "updated_at": session_data.get("updated_at"),
                "expires_at": datetime.fromtimestamp(self.session_expiry.get(session_id, 0)).isoformat(),
                "questions_answered": session_data.get("questions_answered", 0),
                "confidence": session_data.get("current_confidence", 0)
            })

        return sessions_list


# Singleton instance
_session_store = None

def get_session_store() -> SessionStore:
    """Get or create the session store singleton"""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
