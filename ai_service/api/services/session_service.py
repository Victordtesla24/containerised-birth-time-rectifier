"""
Session management service for questionnaire interactions.
"""

import logging
import json
import uuid
import time
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import asyncio
import aiofiles

logger = logging.getLogger(__name__)

class SessionStore:
    """Enhanced session store for questionnaire interactions with persistence."""

    def __init__(self, persistence_dir: str = "/app/cache/sessions"):
        """
        Initialize the session store with persistence support.

        Args:
            persistence_dir: Directory for persisting session data
        """
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_expiry: Dict[str, float] = {}
        self.default_expiry = 3600 * 24  # 24 hours in seconds
        self.persistence_dir = persistence_dir
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()

        # Create persistence directory
        os.makedirs(self.persistence_dir, exist_ok=True)
        logger.info(f"Session persistence directory created: {self.persistence_dir}")

        # Load persisted sessions
        asyncio.create_task(self._load_persisted_sessions())

        logger.info("Enhanced session store initialized with persistence")

    async def _load_persisted_sessions(self) -> None:
        """Load sessions from persisted files."""
        try:
            if not os.path.exists(self.persistence_dir):
                os.makedirs(self.persistence_dir, exist_ok=True)
                logger.info(f"Created persistence directory: {self.persistence_dir}")
                return

            for filename in os.listdir(self.persistence_dir):
                if not filename.endswith('.json'):
                    continue

                session_id = filename.replace('.json', '')
                try:
                    await self._load_session_file(session_id)
                except Exception as e:
                    logger.error(f"Error loading session {session_id}: {str(e)}")

            logger.info(f"Loaded {len(self.sessions)} persisted sessions")
        except Exception as e:
            logger.error(f"Error loading persisted sessions: {str(e)}")
            raise RuntimeError(f"Failed to load session data: {str(e)}")

    async def _load_session_file(self, session_id: str) -> bool:
        """
        Load a single session file.

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
                session_data = json.loads(content)

                # Check if session has expired
                if "expiry" in session_data:
                    if time.time() > session_data["expiry"]:
                        # Delete expired session file
                        try:
                            os.remove(filepath)
                        except Exception as e:
                            logger.error(f"Error removing expired session file {session_id}: {str(e)}")
                        return False

                    # Set expiry in memory
                    self.session_expiry[session_id] = session_data["expiry"]
                    # Remove expiry from session data as it's tracked separately
                    del session_data["expiry"]
                else:
                    # If no expiry in file, set default
                    self.session_expiry[session_id] = time.time() + self.default_expiry

                self.sessions[session_id] = session_data
                return True
        except Exception as e:
            logger.error(f"Error reading session file {session_id}: {str(e)}")
            raise ValueError(f"Failed to read session file {session_id}: {str(e)}")

    async def _persist_session(self, session_id: str) -> bool:
        """
        Persist session to file.

        Args:
            session_id: The session ID

        Returns:
            True if persisted successfully, False otherwise
        """
        if session_id not in self.sessions:
            logger.error(f"Cannot persist non-existent session: {session_id}")
            return False

        try:
            # Add expiry to session data for persistence
            session_data = self.sessions[session_id].copy()
            session_data["expiry"] = self.session_expiry.get(session_id, time.time() + self.default_expiry)

            filepath = os.path.join(self.persistence_dir, f"{session_id}.json")
            async with aiofiles.open(filepath, 'w') as f:
                await f.write(json.dumps(session_data, indent=2))
            return True
        except Exception as e:
            logger.error(f"Error persisting session {session_id}: {str(e)}")
            raise IOError(f"Failed to persist session {session_id}: {str(e)}")

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
        session["data"] = {**session.get("data", {}), **data}
        session["updated_at"] = datetime.now().isoformat()

        # Refresh expiry time
        self.session_expiry[session_id] = time.time() + self.default_expiry

        # Persist changes
        await self._persist_session(session_id)

        logger.info(f"Session updated: {session_id}")
        return True

    async def add_question_response(self, session_id: str, question_id: str,
                                   question: str, answer: Any,
                                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a question response to the session.

        Args:
            session_id: The session ID
            question_id: The question ID
            question: The question text
            answer: The user's answer
            metadata: Optional metadata about the question/response

        Returns:
            True if successful, False otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot add response to non-existent session: {session_id}")
            return False

        # Add response to session
        if "responses" not in session:
            session["responses"] = []

        timestamp = datetime.now().isoformat()

        # Create response object with enhanced metadata
        response = {
            "question_id": question_id,
            "question": question,
            "answer": answer,
            "timestamp": timestamp,
            "response_time_ms": metadata.get("response_time_ms") if metadata else None,
        }

        # Include optional metadata if provided
        if metadata:
            response["metadata"] = metadata

        session["responses"].append(response)

        # Track questions asked
        if "questions_asked" not in session:
            session["questions_asked"] = []
        session["questions_asked"].append(question_id)

        # Update question count
        session["questions_answered"] = len(session["responses"])
        session["updated_at"] = timestamp

        # Refresh expiry time
        self.session_expiry[session_id] = time.time() + self.default_expiry

        # Persist changes
        await self._persist_session(session_id)

        logger.info(f"Question response added to session {session_id}: {question_id}")
        return True

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
                raise IOError(f"Failed to delete session file: {str(e)}")

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

    async def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about sessions.

        Returns:
            Dictionary with session statistics
        """
        active_count = len(self.sessions)

        # Count sessions by confidence ranges
        confidence_ranges = {
            "low": 0,      # 0-40
            "medium": 0,   # 40-70
            "high": 0      # 70-100
        }

        for session in self.sessions.values():
            confidence = session.get("current_confidence", 0)
            if confidence >= 70:
                confidence_ranges["high"] += 1
            elif confidence >= 40:
                confidence_ranges["medium"] += 1
            else:
                confidence_ranges["low"] += 1

        return {
            "active_sessions": active_count,
            "confidence_distribution": confidence_ranges,
            "last_cleanup": datetime.fromtimestamp(self.last_cleanup).isoformat()
        }

# Singleton instance
_instance = None

def get_session_store() -> SessionStore:
    """Get or create the session store singleton"""
    global _instance
    if _instance is None:
        _instance = SessionStore()
    return _instance
