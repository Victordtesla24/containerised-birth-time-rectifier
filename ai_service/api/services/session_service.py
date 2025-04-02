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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ai_service.api.models.session import Session

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

            loaded_count = 0
            for filename in os.listdir(self.session_dir):
                if filename.endswith(".json"):
                    session_id = os.path.splitext(filename)[0]
                    file_path = os.path.join(self.session_dir, filename)

                    try:
                        with open(file_path, "r") as f:
                            session_data = json.load(f)

                            # Sanitize datetime fields to ensure they're valid strings
                            for dt_field in ["created_at", "updated_at", "last_accessed"]:
                                if dt_field in session_data:
                                    # Handle different data types gracefully
                                    dt_value = session_data[dt_field]

                                    # Ensure datetime fields are strings
                                    if not isinstance(dt_value, str):
                                        if isinstance(dt_value, (int, float)):
                                            # Convert timestamps to ISO format
                                            session_data[dt_field] = datetime.fromtimestamp(dt_value).isoformat()
                                        elif dt_value is None:
                                            # Use current time for None values
                                            session_data[dt_field] = datetime.now().isoformat()
                                        elif isinstance(dt_value, dict):
                                            # Handle dictionary values (e.g., serialized datetime objects)
                                            session_data[dt_field] = datetime.now().isoformat()
                                            logger.warning(f"Converted complex {dt_field} in session {session_id} to current time")
                                        else:
                                            # Default to current time for any other type
                                            session_data[dt_field] = datetime.now().isoformat()
                                            logger.warning(f"Converted invalid {dt_field} type in session {session_id} to current time")

                            # Check if session is expired
                            # Get the created_at value with a default if not present
                            created_at_value = session_data.get("created_at", datetime.now().isoformat())

                            # Make sure created_at is a string to avoid fromisoformat errors
                            if not isinstance(created_at_value, str):
                                created_at_value = datetime.now().isoformat()
                                session_data["created_at"] = created_at_value

                            # Parse the date safely
                            try:
                                created_at = datetime.fromisoformat(created_at_value)
                            except ValueError:
                                # If parsing fails, use current time
                                logger.warning(f"Invalid date format in session {session_id}: {created_at_value}, using current time")
                                created_at = datetime.now()
                                # Update the session data with correct format
                                session_data["created_at"] = created_at.isoformat()

                            expiry_date = created_at + timedelta(days=self.session_expiry_days)

                            if datetime.now() < expiry_date:
                                self.sessions[session_id] = session_data
                                loaded_count += 1
                            else:
                                # Remove expired session file
                                os.remove(file_path)
                                logger.info(f"Removed expired session: {session_id}")
                    except Exception as e:
                        logger.error(f"Error loading session {session_id}: {e}")
                        # Try to delete corrupted session files
                        try:
                            os.remove(file_path)
                            logger.info(f"Removed corrupted session file: {session_id}")
                        except Exception:
                            logger.warning(f"Failed to remove corrupted session file: {session_id}")

            logger.info(f"Loaded {loaded_count} sessions from {self.session_dir}")
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

async def get_session_by_id(session_id: str, db: AsyncSession) -> Optional[Session]:
    """
    Get a session by ID from the database.

    Args:
        session_id: The session ID to look up
        db: Database session

    Returns:
        Session if found, None otherwise
    """
    try:
        # For a non-SQLAlchemy model, we need a different approach
        # First, check if we can get the session from the file-based store
        session_store = get_session_store()
        session_data = await session_store.get_session(session_id)

        if session_data:
            # Convert to Session object
            return Session.from_dict(session_data)
        return None
    except Exception as e:
        logger.error(f"Error getting session {session_id}: {e}")
        return None


async def create_session(db: AsyncSession, data: Dict[str, Any]) -> Optional[Session]:
    """
    Create a new session in the database.

    Args:
        db: Database session
        data: Session data

    Returns:
        Created session or None if creation failed
    """
    try:
        session = Session.from_dict(data)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating session: {e}")
        return None


async def update_session(db: AsyncSession, session_id: str, data: Dict[str, Any]) -> Optional[Session]:
    """
    Update an existing session in the database.

    Args:
        db: Database session
        session_id: The session ID to update
        data: Updated session data

    Returns:
        Updated session or None if update failed
    """
    try:
        session = await get_session_by_id(session_id, db)
        if not session:
            logger.warning(f"Session {session_id} not found for update")
            return None

        # Update fields
        for key, value in data.items():
            if hasattr(session, key):
                setattr(session, key, value)

        await db.commit()
        await db.refresh(session)
        return session
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating session {session_id}: {e}")
        return None
