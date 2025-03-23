"""
Session Service for Birth Time Rectifier.

This module provides session management functionality with Redis integration.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional, List, Tuple, Union

import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

# Redis connection pool (singleton)
REDIS_CONNECTION_POOL = None

class SessionService:
    """Session service for managing user sessions with Redis."""

    def __init__(self):
        """Initialize the session service."""
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.session_expiry = int(os.getenv("SESSION_EXPIRY", "86400"))  # 24 hours default
        self._initialize_redis_pool()

    def _initialize_redis_pool(self):
        """Initialize Redis connection pool if not already initialized."""
        global REDIS_CONNECTION_POOL
        try:
            if REDIS_CONNECTION_POOL is None:
                REDIS_CONNECTION_POOL = redis.ConnectionPool.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0,
                    health_check_interval=30
                )
                logger.info(f"Redis connection pool initialized with URL: {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection pool: {e}")
            raise

    def _get_redis_client(self):
        """Get a Redis client from the connection pool."""
        try:
            if REDIS_CONNECTION_POOL is None:
                self._initialize_redis_pool()

            return redis.Redis(connection_pool=REDIS_CONNECTION_POOL)
        except Exception as e:
            logger.error(f"Failed to get Redis client: {e}")
            raise

    def create_session(self) -> str:
        """
        Create a new session.

        Returns:
            str: The session ID.
        """
        session_id = str(uuid.uuid4())
        session_data = {
            "created_at": int(time.time()),
            "last_accessed": int(time.time()),
            "birth_details": {},
            "questionnaire": {
                "answers": [],
                "current_question_index": 0,
                "confidence_score": 20  # Starting confidence score
            },
            "charts": {
                "original": None,
                "rectified": None
            }
        }

        try:
            redis_client = self._get_redis_client()
            redis_client.setex(
                f"session:{session_id}",
                self.session_expiry,
                json.dumps(session_data)
            )
            logger.info(f"Created new session: {session_id}")
            return session_id
        except RedisError as e:
            logger.error(f"Redis error while creating session: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while creating session: {e}")
            raise

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session data by session ID.

        Args:
            session_id: The session ID.

        Returns:
            Optional[Dict[str, Any]]: The session data or None if not found.
        """
        try:
            redis_client = self._get_redis_client()
            session_data = redis_client.get(f"session:{session_id}")

            if session_data:
                session = json.loads(session_data)
                # Update last accessed time
                session["last_accessed"] = int(time.time())
                redis_client.setex(
                    f"session:{session_id}",
                    self.session_expiry,
                    json.dumps(session)
                )
                return session
            return None
        except RedisError as e:
            logger.error(f"Redis error while getting session {session_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while getting session {session_id}: {e}")
            return None

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update session data.

        Args:
            session_id: The session ID.
            data: The new data to update.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            redis_client = self._get_redis_client()
            # Get current session data
            current_session_data = redis_client.get(f"session:{session_id}")

            if not current_session_data:
                logger.warning(f"Cannot update non-existent session: {session_id}")
                return False

            # Parse and update
            session = json.loads(current_session_data)
            session.update(data)
            session["last_accessed"] = int(time.time())

            # Save back to Redis
            redis_client.setex(
                f"session:{session_id}",
                self.session_expiry,
                json.dumps(session)
            )
            logger.debug(f"Updated session: {session_id}")
            return True
        except RedisError as e:
            logger.error(f"Redis error while updating session {session_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while updating session {session_id}: {e}")
            return False

    def update_birth_details(self, session_id: str, birth_details: Dict[str, Any]) -> bool:
        """
        Update birth details in the session.

        Args:
            session_id: The session ID.
            birth_details: The birth details to store.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            redis_client = self._get_redis_client()
            session_data = redis_client.get(f"session:{session_id}")

            if not session_data:
                logger.warning(f"Cannot update birth details for non-existent session: {session_id}")
                return False

            session = json.loads(session_data)
            session["birth_details"] = birth_details
            session["last_accessed"] = int(time.time())

            redis_client.setex(
                f"session:{session_id}",
                self.session_expiry,
                json.dumps(session)
            )
            logger.info(f"Updated birth details for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating birth details for session {session_id}: {e}")
            return False

    def update_questionnaire_progress(
        self,
        session_id: str,
        answers: List[Dict[str, Any]] = None,
        current_question_index: int = None,
        confidence_score: float = None
    ) -> bool:
        """
        Update questionnaire progress in the session.

        Args:
            session_id: The session ID.
            answers: Updated list of answers.
            current_question_index: Current question index.
            confidence_score: Current confidence score.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            redis_client = self._get_redis_client()
            session_data = redis_client.get(f"session:{session_id}")

            if not session_data:
                logger.warning(f"Cannot update questionnaire for non-existent session: {session_id}")
                return False

            session = json.loads(session_data)

            # Update only the fields that were provided
            if answers is not None:
                session["questionnaire"]["answers"] = answers

            if current_question_index is not None:
                session["questionnaire"]["current_question_index"] = current_question_index

            if confidence_score is not None:
                session["questionnaire"]["confidence_score"] = confidence_score

            session["last_accessed"] = int(time.time())

            redis_client.setex(
                f"session:{session_id}",
                self.session_expiry,
                json.dumps(session)
            )
            logger.debug(f"Updated questionnaire progress for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating questionnaire progress for session {session_id}: {e}")
            return False

    def update_chart_data(self, session_id: str, chart_type: str, chart_data: Dict[str, Any]) -> bool:
        """
        Update chart data in the session.

        Args:
            session_id: The session ID.
            chart_type: Type of chart (original or rectified).
            chart_data: The chart data to store.

        Returns:
            bool: True if successful, False otherwise.
        """
        if chart_type not in ["original", "rectified"]:
            logger.warning(f"Invalid chart type: {chart_type}")
            return False

        try:
            redis_client = self._get_redis_client()
            session_data = redis_client.get(f"session:{session_id}")

            if not session_data:
                logger.warning(f"Cannot update chart data for non-existent session: {session_id}")
                return False

            session = json.loads(session_data)
            session["charts"][chart_type] = chart_data
            session["last_accessed"] = int(time.time())

            redis_client.setex(
                f"session:{session_id}",
                self.session_expiry,
                json.dumps(session)
            )
            logger.info(f"Updated {chart_type} chart data for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating chart data for session {session_id}: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            redis_client = self._get_redis_client()
            result = redis_client.delete(f"session:{session_id}")
            logger.info(f"Deleted session: {session_id}, result: {result}")
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
