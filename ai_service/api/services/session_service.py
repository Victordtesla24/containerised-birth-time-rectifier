"""
Session service for API services.

This module provides session management functionality for the API services.
"""

import os
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

# Global session store
_session_store = None

def get_session_store():
    """Get the global session store instance."""
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store

class SessionStore:
    """Session store for managing user sessions."""

    def __init__(self, session_dir: Optional[str] = None):
        """
        Initialize the session store.

        Args:
            session_dir: Directory to store session data. If None, uses 'sessions' directory.
        """
        self.session_dir = session_dir or os.path.join(os.getcwd(), "sessions")
        self.sessions = {}
        self.session_expiry_days = int(os.environ.get("SESSION_EXPIRY_DAYS", "30"))

        # Create session directory if it doesn't exist
        os.makedirs(self.session_dir, exist_ok=True)

        # Load any existing sessions
        self._load_sessions()

        logger.info(f"Session store initialized with directory: {self.session_dir}")

    def _load_sessions(self):
        """Load sessions from the session directory."""
        try:
            if not os.path.exists(self.session_dir):
                return

            for filename in os.listdir(self.session_dir):
                if filename.endswith(".json"):
                    session_id = os.path.splitext(filename)[0]
                    file_path = os.path.join(self.session_dir, filename)

                    try:
                        with open(file_path, "r") as f:
                            session_data = json.load(f)

                            # Check if session is expired
                            created_at = datetime.fromisoformat(session_data.get("created_at", "2000-01-01T00:00:00"))
                            expiry_date = created_at + timedelta(days=self.session_expiry_days)

                            if datetime.now() < expiry_date:
                                self.sessions[session_id] = session_data
                            else:
                                # Remove expired session file
                                os.remove(file_path)
                                logger.info(f"Removed expired session: {session_id}")
                    except Exception as e:
                        logger.error(f"Error loading session {session_id}: {e}")

            logger.info(f"Loaded {len(self.sessions)} sessions from {self.session_dir}")
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")

    async def create_session(self, initial_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session.

        Args:
            initial_data: Initial session data

        Returns:
            Session ID
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}"

        # Create session data
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            **(initial_data or {})
        }

        # Store session in memory
        self.sessions[session_id] = session_data

        # Save session to file
        await self._save_session(session_id, session_data)

        logger.info(f"Created new session: {session_id}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by ID.

        Args:
            session_id: Session ID

        Returns:
            Session data or None if not found
        """
        # Try to get from memory
        session_data = self.sessions.get(session_id)

        # If not in memory, try to load from file
        if session_data is None:
            try:
                file_path = os.path.join(self.session_dir, f"{session_id}.json")
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        session_data = json.load(f)
                        self.sessions[session_id] = session_data
            except Exception as e:
                logger.error(f"Error loading session {session_id}: {e}")
                return None

        # Update last accessed timestamp
        if session_data:
            session_data["last_accessed"] = datetime.now().isoformat()
            await self._save_session(session_id, session_data)

        return session_data

    async def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: Session ID
            data: New session data

        Returns:
            True if session was updated, False otherwise
        """
        # Check if session exists
        if session_id not in self.sessions:
            session = await self.get_session(session_id)
            if not session:
                return False

        # Update session data
        self.sessions[session_id] = data

        # Update last accessed timestamp
        data["last_accessed"] = datetime.now().isoformat()

        # Save session to file
        await self._save_session(session_id, data)

        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if session was deleted, False otherwise
        """
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]

        # Remove from file
        try:
            file_path = os.path.join(self.session_dir, f"{session_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")

        return False

    async def _save_session(self, session_id: str, data: Dict[str, Any]):
        """
        Save session data to file.

        Args:
            session_id: Session ID
            data: Session data
        """
        try:
            file_path = os.path.join(self.session_dir, f"{session_id}.json")
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")

# Initialize the global session store
_session_store = SessionStore()
