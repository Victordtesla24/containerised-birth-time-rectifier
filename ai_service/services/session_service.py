"""
Session management service for the Birth Time Rectifier API.

This module handles session creation, storage, and retrieval.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional
import redis
import json

from ai_service.core.config import settings

logger = logging.getLogger(__name__)

class SessionService:
    """Service for managing user sessions."""

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the session service.

        Args:
            redis_url: Optional Redis URL. If not provided, uses the URL from settings.
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.session_expiry = settings.SESSION_EXPIRY_DAYS * 24 * 60 * 60  # Convert days to seconds

        try:
            self.redis = redis.from_url(self.redis_url)
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    def create_session(self) -> str:
        """
        Create a new session.

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())

        # Create session data
        session_data = {
            "created_at": time.time(),
            "expires_at": time.time() + self.session_expiry,
            "status": "active"
        }

        # Store in Redis if available, otherwise just return the ID
        if self.redis:
            try:
                self.redis.setex(
                    f"session:{session_id}",
                    self.session_expiry,
                    json.dumps(session_data)
                )
                logger.info(f"Created session {session_id} in Redis")
            except Exception as e:
                logger.error(f"Failed to store session in Redis: {e}")

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session.

        Args:
            session_id: The session ID

        Returns:
            Session data or None if not found
        """
        if not self.redis:
            logger.warning("Redis not available for session retrieval")
            return None

        try:
            data = self.redis.get(f"session:{session_id}")
            if not data:
                return None

            return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to retrieve session from Redis: {e}")
            return None

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a session with new data.

        Args:
            session_id: The session ID
            data: The data to update

        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            logger.warning("Redis not available for session update")
            return False

        try:
            # Get existing session data
            session_data = self.get_session(session_id)
            if not session_data:
                logger.warning(f"Session {session_id} not found for update")
                return False

            # Update with new data
            session_data.update(data)

            # Store back in Redis
            self.redis.setex(
                f"session:{session_id}",
                self.session_expiry,
                json.dumps(session_data)
            )

            return True
        except Exception as e:
            logger.error(f"Failed to update session in Redis: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            logger.warning("Redis not available for session deletion")
            return False

        try:
            result = self.redis.delete(f"session:{session_id}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete session from Redis: {e}")
            return False

    def is_valid_session(self, session_id: str) -> bool:
        """
        Check if a session is valid.

        Args:
            session_id: The session ID

        Returns:
            True if valid, False otherwise
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False

        # Check if session has expired
        if session_data.get("expires_at", 0) < time.time():
            return False

        return session_data.get("status") == "active"

    def extend_session(self, session_id: str) -> bool:
        """
        Extend a session's expiry time.

        Args:
            session_id: The session ID

        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            logger.warning("Redis not available for session extension")
            return False

        try:
            # Get existing session data
            session_data = self.get_session(session_id)
            if not session_data:
                logger.warning(f"Session {session_id} not found for extension")
                return False

            # Update expiry time
            session_data["expires_at"] = time.time() + self.session_expiry

            # Store back in Redis
            self.redis.setex(
                f"session:{session_id}",
                self.session_expiry,
                json.dumps(session_data)
            )

            return True
        except Exception as e:
            logger.error(f"Failed to extend session in Redis: {e}")
            return False

    def store_chart_in_session(self, session_id: str, chart_id: str, chart_data: Dict[str, Any]) -> bool:
        """
        Store chart data in a session.

        Args:
            session_id: The session ID
            chart_id: The chart ID
            chart_data: The chart data

        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            logger.warning("Redis not available for storing chart in session")
            return False

        try:
            # Get existing session data
            session_data = self.get_session(session_id)
            if not session_data:
                logger.warning(f"Session {session_id} not found for storing chart")
                return False

            # Initialize charts dict if not exists
            if "charts" not in session_data:
                session_data["charts"] = {}

            # Store chart data
            session_data["charts"][chart_id] = {
                "id": chart_id,
                "created_at": time.time(),
                "data": chart_data
            }

            # Store back in Redis
            self.redis.setex(
                f"session:{session_id}",
                self.session_expiry,
                json.dumps(session_data)
            )

            return True
        except Exception as e:
            logger.error(f"Failed to store chart in session: {e}")
            return False
