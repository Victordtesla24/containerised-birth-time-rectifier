"""
Session management service for the API layer.

This module provides a session storage interface for the API layer,
abstracting the underlying storage mechanism (files, Redis, etc.)
"""

import os
import json
import time
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class SessionStore:
    """
    Session storage implementation with file-based persistence.

    This provides a simple interface for storing and retrieving session data
    with local filesystem persistence for development and testing.
    """

    def __init__(self, persistence_dir: Optional[str] = None):
        """
        Initialize the session store.

        Args:
            persistence_dir: Directory to store session data (default: None, uses tmp directory)
        """
        if persistence_dir:
            self.persistence_dir = persistence_dir
        else:
            # Use a directory in the project for session storage
            project_root = Path(__file__).parent.parent.parent.parent
            self.persistence_dir = os.path.join(project_root, "sessions")

        # Create the directory if it doesn't exist
        os.makedirs(self.persistence_dir, exist_ok=True)

        # In-memory cache of sessions
        self._sessions: Dict[str, Dict[str, Any]] = {}

        # Default session expiry time (30 days in seconds)
        self.session_expiry = 30 * 24 * 60 * 60

        logger.info(f"Session store initialized with persistence dir: {self.persistence_dir}")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())

    def _get_session_file_path(self, session_id: str) -> str:
        """Get the file path for a session."""
        return os.path.join(self.persistence_dir, f"{session_id}.json")

    def _load_session_from_file(self, session_id: str) -> Dict[str, Any]:
        """Load session data from file."""
        file_path = self._get_session_file_path(session_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode session file: {file_path}")
            except Exception as e:
                logger.error(f"Error loading session file: {e}")
        return {}

    def _save_session_to_file(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Save session data to file."""
        file_path = self._get_session_file_path(session_id)
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f)
            return True
        except Exception as e:
            logger.error(f"Error saving session file: {e}")
            return False

    def create_session(self, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session.

        Args:
            session_id: Optional session ID (generated if not provided)
            data: Initial session data

        Returns:
            The session ID
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = self._generate_session_id()

        # Create session data
        session_data = data or {}
        session_data.update({
            "created_at": int(time.time()),
            "expires_at": int(time.time()) + self.session_expiry,
            "last_accessed": int(time.time())
        })

        # Store in memory and on disk
        self._sessions[session_id] = session_data
        self._save_session_to_file(session_id, session_data)

        logger.info(f"Created session: {session_id}")
        return session_id

    async def create_session_async(self, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
        """Async version of create_session."""
        return await asyncio.to_thread(self.create_session, session_id, data)

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get session data by ID.

        Args:
            session_id: The session ID

        Returns:
            Session data or empty dict if not found
        """
        # Check cache first
        if session_id in self._sessions:
            session_data = self._sessions[session_id]
        else:
            # Load from file
            session_data = self._load_session_from_file(session_id)
            if session_data:
                self._sessions[session_id] = session_data

        # Check if session exists and is not expired
        if session_data and self.is_valid_session(session_id):
            # Update last accessed time
            session_data["last_accessed"] = int(time.time())
            self._sessions[session_id] = session_data
            return session_data

        return {}

    async def get_session_async(self, session_id: str) -> Dict[str, Any]:
        """Async version of get_session."""
        return await asyncio.to_thread(self.get_session, session_id)

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: The session ID
            data: Data to update (will be merged with existing data)

        Returns:
            True if successful, False otherwise
        """
        # Get existing session
        session_data = self.get_session(session_id)
        if not session_data:
            logger.error(f"Session not found: {session_id}")
            return False

        # Update session data (deep merge)
        self._deep_update(session_data, data)

        # Update last accessed time
        session_data["last_accessed"] = int(time.time())

        # Save to memory and disk
        self._sessions[session_id] = session_data
        success = self._save_session_to_file(session_id, session_data)

        return success

    async def update_session_async(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Async version of update_session."""
        return await asyncio.to_thread(self.update_session, session_id, data)

    def add_question_response(self, session_id: str, question: Dict[str, Any], response: Dict[str, Any]) -> bool:
        """
        Add a question and response to the session.

        Args:
            session_id: The session ID
            question: Question data
            response: Response data

        Returns:
            True if successful, False otherwise
        """
        # Get existing session
        session_data = self.get_session(session_id)
        if not session_data:
            logger.error(f"Session not found: {session_id}")
            return False

        # Initialize questionnaire data if it doesn't exist
        if "questionnaire" not in session_data:
            session_data["questionnaire"] = {
                "questions": [],
                "responses": []
            }

        # Add question and response
        session_data["questionnaire"]["questions"].append(question)
        session_data["questionnaire"]["responses"].append(response)

        # Save to memory and disk
        self._sessions[session_id] = session_data
        success = self._save_session_to_file(session_id, session_data)

        return success

    async def add_question_response_async(self, session_id: str, question: Dict[str, Any], response: Dict[str, Any]) -> bool:
        """Async version of add_question_response."""
        return await asyncio.to_thread(self.add_question_response, session_id, question, response)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if successful, False otherwise
        """
        # Remove from memory
        if session_id in self._sessions:
            del self._sessions[session_id]

        # Remove from disk
        file_path = self._get_session_file_path(session_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted session: {session_id}")
                return True
            except Exception as e:
                logger.error(f"Error deleting session file: {e}")

        return False

    async def delete_session_async(self, session_id: str) -> bool:
        """Async version of delete_session."""
        return await asyncio.to_thread(self.delete_session, session_id)

    def is_valid_session(self, session_id: str) -> bool:
        """
        Check if a session is valid (exists and not expired).

        Args:
            session_id: The session ID

        Returns:
            True if valid, False otherwise
        """
        # Check if session exists in memory
        if session_id in self._sessions:
            session_data = self._sessions[session_id]
        else:
            # Load from file
            session_data = self._load_session_from_file(session_id)
            if session_data:
                self._sessions[session_id] = session_data

        # Check expiration
        if session_data and "expires_at" in session_data:
            current_time = int(time.time())
            return current_time < session_data["expires_at"]

        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        count = 0
        current_time = int(time.time())

        # Get all session files
        for filename in os.listdir(self.persistence_dir):
            if filename.endswith(".json"):
                session_id = filename.replace(".json", "")

                # Load session data
                session_data = self._load_session_from_file(session_id)

                # Check if expired
                if session_data and "expires_at" in session_data and current_time >= session_data["expires_at"]:
                    # Delete session
                    if self.delete_session(session_id):
                        count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} expired sessions")

        return count

    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Deep update a nested dictionary.

        Args:
            target: Target dictionary to update
            source: Source dictionary with updates
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                # Recursively update nested dictionaries
                self._deep_update(target[key], value)
            else:
                # Replace or add the value
                target[key] = value

# Singleton pattern for session store
_session_store: Optional[SessionStore] = None

def get_session_store() -> SessionStore:
    """
    Get the session store instance (singleton).

    Returns:
        SessionStore instance
    """
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
