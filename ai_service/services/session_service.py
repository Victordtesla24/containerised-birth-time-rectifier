"""
Unified Session Management Service for the Birth Time Rectifier API.

This module handles session creation, storage, and retrieval with support for both
Redis-based and file-based persistence.
"""

import logging
import time
import uuid
import json
import os
import shutil
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta

from ai_service.core.config import settings

# Import aiofiles conditionally to avoid breaking if not available
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

# Import redis conditionally to avoid breaking if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class SessionService:
    """
    Unified service for managing user sessions.

    This service supports both Redis-based and file-based session storage,
    automatically selecting the appropriate backend based on availability.
    """

    def __init__(self, redis_url: Optional[str] = None, persistence_dir: Optional[str] = None):
        """
        Initialize the session service.

        Args:
            redis_url: Optional Redis URL. If not provided, uses the URL from settings.
            persistence_dir: Optional directory for file-based session storage.
        """
        # Session configuration
        self.session_expiry = settings.SESSION_EXPIRY_DAYS * 24 * 60 * 60  # Convert days to seconds

        # In-memory storage (used for both Redis and file-based backends)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_expiry_times: Dict[str, float] = {}

        # Setup Redis backend if available
        self.redis_url = redis_url or settings.REDIS_URL
        self.redis = None

        if REDIS_AVAILABLE and self.redis_url:
            try:
                self.redis = redis.from_url(self.redis_url)
                self.redis.ping()  # Test connection
                logger.info(f"Connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, falling back to file storage")
                self.redis = None

        # Setup file-based persistence
        self.persistence_dir = persistence_dir or settings.SESSION_DIR
        self.use_file_persistence = not bool(self.redis)

        if self.use_file_persistence:
            # Create persistence directory if it doesn't exist
            if not os.path.isdir(self.persistence_dir):
                try:
                    os.makedirs(self.persistence_dir, exist_ok=True)
                    os.chmod(self.persistence_dir, 0o755)  # Standard permissions
                    logger.info(f"Session persistence directory created: {self.persistence_dir}")
                except Exception as e:
                    logger.error(f"Failed to create persistence directory: {str(e)}")
                    raise RuntimeError(f"Cannot create session directory: {str(e)}")

            logger.info(f"Using file-based session storage in {self.persistence_dir}")

        # Setup cleanup
        self.cleanup_interval = 3600  # 1 hour
        self.last_cleanup = time.time()

    def create_session(self, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session.

        Args:
            session_id: Optional session ID (generates one if not provided)
            data: Optional initial session data

        Returns:
            Session ID
        """
        # Generate a session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        # Create session data with timestamp
        timestamp = time.time()
        expires_at = timestamp + self.session_expiry

        session_data = {
            "created_at": timestamp,
            "updated_at": timestamp,
            "expires_at": expires_at,
            "status": "active"
        }

        # Add additional data if provided
        if data:
            session_data.update(data)

        # Store in Redis if available
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
                # Fall back to memory storage
                self.sessions[session_id] = session_data
                self.session_expiry_times[session_id] = expires_at
        else:
            # Store in memory
            self.sessions[session_id] = session_data
            self.session_expiry_times[session_id] = expires_at

            # Persist to file if using file-based storage
            if self.use_file_persistence:
                self._persist_session_sync(session_id, session_data)

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session synchronously.

        Args:
            session_id: The session ID

        Returns:
            Session data or None if not found
        """
        # First check in-memory cache
        if session_id in self.sessions:
            # Check if expired
            if time.time() > self.session_expiry_times.get(session_id, 0):
                self.delete_session(session_id)
                return None

            return self.sessions[session_id]

        # If not in memory, try Redis
        if self.redis:
            try:
                data = self.redis.get(f"session:{session_id}")
                if not data:
                    return None

                session_data = json.loads(data)

                # Cache in memory
                self.sessions[session_id] = session_data
                self.session_expiry_times[session_id] = session_data.get("expires_at", time.time() + self.session_expiry)

                return session_data
            except Exception as e:
                logger.error(f"Failed to retrieve session from Redis: {e}")
                # Fall back to file-based retrieval if available
                if self.use_file_persistence:
                    return self._load_session_file_sync(session_id)
                return None
        elif self.use_file_persistence:
            # Try loading from file
            return self._load_session_file_sync(session_id)

        return None

    async def get_session_async(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a session asynchronously.

        Args:
            session_id: The session ID

        Returns:
            Session data or None if not found
        """
        # First check in-memory cache
        if session_id in self.sessions:
            # Check if expired
            if time.time() > self.session_expiry_times.get(session_id, 0):
                await self.delete_session_async(session_id)
                return None

            return self.sessions[session_id]

        # If using file persistence, try loading from file
        if self.use_file_persistence:
            loaded = await self._load_session_file_async(session_id)
            if loaded:
                return self.sessions[session_id]

        # If Redis is available, try Redis (use synchronous call for simplicity)
        if self.redis:
            try:
                data = self.redis.get(f"session:{session_id}")
                if not data:
                    return None

                session_data = json.loads(data)

                # Cache in memory
                self.sessions[session_id] = session_data
                self.session_expiry_times[session_id] = session_data.get("expires_at", time.time() + self.session_expiry)

                return session_data
            except Exception as e:
                logger.error(f"Failed to retrieve session from Redis: {e}")
                return None

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
        # Get existing session data
        session_data = self.get_session(session_id)
        if not session_data:
            logger.warning(f"Session {session_id} not found for update")
            return False

        # Update session data
        for key, value in data.items():
            # Handle nested dict merging for data field
            if key == "data" and isinstance(value, dict) and isinstance(session_data.get("data"), dict):
                if "data" not in session_data:
                    session_data["data"] = {}
                session_data["data"].update(value)
            else:
                # Direct replacement for other fields
                session_data[key] = value

        # Update timestamps
        session_data["updated_at"] = time.time()

        # Store updated data
        self.sessions[session_id] = session_data
        self.session_expiry_times[session_id] = time.time() + self.session_expiry

        # Update in Redis if available
        if self.redis:
            try:
                self.redis.setex(
                    f"session:{session_id}",
                    self.session_expiry,
                    json.dumps(session_data)
                )
                logger.debug(f"Updated session {session_id} in Redis")
                return True
            except Exception as e:
                logger.error(f"Failed to update session in Redis: {e}")
                # If Redis fails but we have file persistence, fall back to file
                if self.use_file_persistence:
                    return self._persist_session_sync(session_id, session_data)
                return False
        elif self.use_file_persistence:
            # Persist to file
            return self._persist_session_sync(session_id, session_data)

        return True  # Session updated in memory

    async def update_session_async(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a session asynchronously.

        Args:
            session_id: The session ID
            data: The data to update

        Returns:
            True if successful, False otherwise
        """
        # Get existing session data
        session_data = await self.get_session_async(session_id)
        if not session_data:
            logger.warning(f"Session {session_id} not found for update")
            return False

        # Update session data
        for key, value in data.items():
            # Handle nested dict merging for data field
            if key == "data" and isinstance(value, dict) and isinstance(session_data.get("data"), dict):
                if "data" not in session_data:
                    session_data["data"] = {}
                session_data["data"].update(value)
            else:
                # Direct replacement for other fields
                session_data[key] = value

        # Update timestamps
        session_data["updated_at"] = time.time()

        # Store updated data
        self.sessions[session_id] = session_data
        self.session_expiry_times[session_id] = time.time() + self.session_expiry

        # Update in Redis if available (use synchronous call for simplicity)
        if self.redis:
            try:
                self.redis.setex(
                    f"session:{session_id}",
                    self.session_expiry,
                    json.dumps(session_data)
                )
                logger.debug(f"Updated session {session_id} in Redis")
                return True
            except Exception as e:
                logger.error(f"Failed to update session in Redis: {e}")
                # If Redis fails but we have file persistence, fall back to file
                if self.use_file_persistence:
                    return await self._persist_session_async(session_id, session_data)
                return False
        elif self.use_file_persistence:
            # Persist to file
            return await self._persist_session_async(session_id, session_data)

        return True  # Session updated in memory

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: The session ID

        Returns:
            True if successful, False otherwise
        """
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]

        if session_id in self.session_expiry_times:
            del self.session_expiry_times[session_id]

        success = True

        # Remove from Redis if available
        if self.redis:
            try:
                self.redis.delete(f"session:{session_id}")
            except Exception as e:
                logger.error(f"Error deleting session from Redis: {e}")
                success = False

        # Remove from file storage if using it
        if self.use_file_persistence:
            try:
                filepath = os.path.join(self.persistence_dir, f"{session_id}.json")
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                logger.error(f"Error deleting session file: {e}")
                success = False

        return success

    async def delete_session_async(self, session_id: str) -> bool:
        """
        Delete a session asynchronously.

        Args:
            session_id: The session ID

        Returns:
            True if successful, False otherwise
        """
        # Remove from memory
        if session_id in self.sessions:
            del self.sessions[session_id]

        if session_id in self.session_expiry_times:
            del self.session_expiry_times[session_id]

        success = True

        # Remove from Redis if available (use synchronous call for simplicity)
        if self.redis:
            try:
                self.redis.delete(f"session:{session_id}")
            except Exception as e:
                logger.error(f"Error deleting session from Redis: {e}")
                success = False

        # Remove from file storage if using it
        if self.use_file_persistence:
            try:
                filepath = os.path.join(self.persistence_dir, f"{session_id}.json")
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                logger.error(f"Error deleting session file: {e}")
                success = False

        return success

    async def add_question_response(
        self,
        session_id: str,
        question_id: str,
        question_text: str,
        answer: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
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
        session = await self.get_session_async(session_id)
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

        # Update and persist the session
        return await self.update_session_async(session_id, session)

    async def get_responses(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all responses for a session.

        Args:
            session_id: The session ID

        Returns:
            List of responses
        """
        session = await self.get_session_async(session_id)
        if not session:
            logger.warning(f"Cannot get responses for non-existent session: {session_id}")
            return []

        return session.get("responses", [])

    def _load_session_file_sync(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a session from a file synchronously.

        Args:
            session_id: The session ID

        Returns:
            Session data or None if not found or error
        """
        filepath = os.path.join(self.persistence_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r') as f:
                content = f.read()
                if not content.strip():
                    logger.error(f"Empty session file: {session_id}")
                    os.remove(filepath)
                    return None

                # Parse the content
                session_data = json.loads(content)
                self.sessions[session_id] = session_data

                # Set expiry based on updated_at time + default expiry
                updated_at = session_data.get("updated_at")
                if updated_at:
                    try:
                        if isinstance(updated_at, str):
                            dt = datetime.fromisoformat(updated_at)
                            timestamp = dt.timestamp()
                        else:
                            timestamp = float(updated_at)
                        # Add expiry
                        self.session_expiry_times[session_id] = timestamp + self.session_expiry
                    except (ValueError, TypeError):
                        # If date parsing fails, use current time + expiry
                        self.session_expiry_times[session_id] = time.time() + self.session_expiry
                else:
                    # Use current time + expiry if no updated_at date
                    self.session_expiry_times[session_id] = time.time() + self.session_expiry

                logger.info(f"Session loaded from file: {session_id}")
                return session_data

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing session file {session_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error reading session file {session_id}: {str(e)}")
            return None

    async def _load_session_file_async(self, session_id: str) -> bool:
        """
        Load a session from a file asynchronously.

        Args:
            session_id: The session ID

        Returns:
            True if loaded successfully, False otherwise
        """
        if not AIOFILES_AVAILABLE:
            # Fall back to synchronous loading
            result = self._load_session_file_sync(session_id)
            return result is not None

        filepath = os.path.join(self.persistence_dir, f"{session_id}.json")
        if not os.path.exists(filepath):
            return False

        try:
            async with aiofiles.open(filepath, 'r') as f:
                content = await f.read()
                if not content.strip():
                    logger.error(f"Empty session file: {session_id}")
                    os.remove(filepath)
                    return False

                # Parse the content
                session_data = json.loads(content)
                self.sessions[session_id] = session_data

                # Set expiry based on updated_at time + default expiry
                updated_at = session_data.get("updated_at")
                if updated_at:
                    try:
                        if isinstance(updated_at, str):
                            dt = datetime.fromisoformat(updated_at)
                            timestamp = dt.timestamp()
                        else:
                            timestamp = float(updated_at)
                        # Add expiry
                        self.session_expiry_times[session_id] = timestamp + self.session_expiry
                    except (ValueError, TypeError):
                        # If date parsing fails, use current time + expiry
                        self.session_expiry_times[session_id] = time.time() + self.session_expiry
                else:
                    # Use current time + expiry if no updated_at date
                    self.session_expiry_times[session_id] = time.time() + self.session_expiry

                logger.info(f"Session loaded from file: {session_id}")
                return True

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing session file {session_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error reading session file {session_id}: {str(e)}")
            return False

    def _persist_session_sync(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Persist session data to file synchronously.

        Args:
            session_id: The session ID
            data: The session data to persist

        Returns:
            True if successful, False otherwise
        """
        # Get filepath for this session
        filepath = os.path.join(self.persistence_dir, f"{session_id}.json")

        # Process data to ensure it's JSON serializable
        try:
            # Convert data to JSON
            json_data = json.dumps(self._prepare_session_data(data), indent=2)

            # Use a temporary file to ensure atomic writes
            temp_filepath = f"{filepath}.tmp"

            # Write to temporary file first
            with open(temp_filepath, 'w') as f:
                f.write(json_data)

            # Rename the temporary file to the final name (atomic operation)
            os.replace(temp_filepath, filepath)

            logger.debug(f"Session persisted to file: {session_id}")
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

    async def _persist_session_async(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Persist session data to file asynchronously.

        Args:
            session_id: The session ID
            data: The session data to persist

        Returns:
            True if successful, False otherwise
        """
        if not AIOFILES_AVAILABLE:
            # Fall back to synchronous persistence
            return self._persist_session_sync(session_id, data)

        # Get filepath for this session
        filepath = os.path.join(self.persistence_dir, f"{session_id}.json")

        # Process data to ensure it's JSON serializable
        try:
            # Convert data to JSON
            json_data = json.dumps(self._prepare_session_data(data), indent=2)

            # Use a temporary file to ensure atomic writes
            temp_filepath = f"{filepath}.tmp"

            # Write to temporary file first
            async with aiofiles.open(temp_filepath, 'w') as f:
                await f.write(json_data)

            # Rename the temporary file to the final name (atomic operation)
            os.replace(temp_filepath, filepath)

            logger.debug(f"Session persisted to file: {session_id}")
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

    def _prepare_session_data(self, data):
        """
        Prepare session data for JSON serialization by handling non-serializable types.

        Args:
            data: The data to prepare

        Returns:
            The prepared data
        """
        if isinstance(data, dict):
            return {k: self._prepare_session_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._prepare_session_data(item) for item in data]
        elif isinstance(data, set):
            return [self._prepare_session_data(item) for item in data]
        elif isinstance(data, tuple):
            return [self._prepare_session_data(item) for item in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        else:
            # For any other types, convert to string
            return str(data)

# Singleton instance
_service_instance = None

def get_session_service() -> SessionService:
    """
    Get or create the session service singleton.

    Returns:
        SessionService: The session service instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = SessionService()
    return _service_instance
