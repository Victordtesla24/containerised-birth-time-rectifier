"""
Session model for questionnaire API.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class Session:
    """Represents a user session for questionnaire data."""

    def __init__(self, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """
        Initialize a new Session.

        Args:
            session_id: Optional session ID (generated if not provided)
            data: Optional initial session data
        """
        self.id = session_id or str(uuid.uuid4())
        self.data = data or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create a session from dictionary data."""
        session = cls(session_id=data.get("id"))
        session.data = data.get("data", {})

        # Parse dates if they exist
        if "created_at" in data:
            try:
                session.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                session.created_at = datetime.now()

        if "updated_at" in data:
            try:
                session.updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                session.updated_at = datetime.now()

        return session
