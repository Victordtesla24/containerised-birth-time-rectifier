"""
Session middleware for FastAPI.

This module provides middleware for session management in FastAPI applications.
"""

import json
import logging
import uuid
import time
import asyncio
import random
import os
import string
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timedelta
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send
from fastapi import FastAPI, Response, Request

from ai_service.core.config import settings

# Try to import Redis
try:
    import redis  # type: ignore
    from redis import Redis  # type: ignore
    HAS_REDIS = True
except ImportError:
    redis = None  # Define redis as None to allow for type checking
    Redis = Any  # For type annotations
    HAS_REDIS = False

# Setup logging
logger = logging.getLogger(__name__)

# Redis connection pool and retry configuration
REDIS_CONNECTION_POOL = None
REDIS_MAX_RETRIES = 3
REDIS_RETRY_DELAY = 0.5  # seconds

# Flag for test mode - only set to True in testing environments
IS_TESTING = os.environ.get("TESTING", "false").lower() == "true"

# In-memory store for testing only
SESSION_STORE: Dict[str, Dict] = {}
SESSION_TTL = 3600  # 1 hour in seconds

# Paths that should not use sessions
EXCLUDED_PATHS = [
    "/static/",
    "/favicon.ico",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/health/basic",  # Skip session for basic health check
    "/health",  # Skip all root health endpoints
    "/api/v1/health",  # Skip all v1 health endpoints
    "/api/v1/health/",  # Skip all v1 health sub-endpoints
    "/api/v1/health/ping",  # Skip ping endpoint
    "/api/v1/health/basic",  # Skip basic endpoint
    "/debug/routes",  # Skip debug endpoints
]

# Session cookie settings
SESSION_COOKIE_NAME = "session_id"
SESSION_EXPIRY = 86400  # 24 hours in seconds

# Custom exception for session-related errors
class SessionError(Exception):
    """Exception raised for session-related errors."""
    pass

def enable_test_mode():
    """Enable test mode for session management (uses in-memory store)."""
    global IS_TESTING
    IS_TESTING = True
    logger.info("Session test mode enabled - using in-memory store")

def get_redis_client():
    """
    Get Redis client for session storage with improved reliability.

    Returns:
        Redis client or None if not available (will use file-based storage as fallback)
    """
    global REDIS_CONNECTION_POOL

    # If in testing mode, return None to use in-memory store
    if IS_TESTING:
        return None

    try:
        from ai_service.core.config import settings

        # Skip Redis if explicitly disabled in settings
        if not getattr(settings, "USE_REDIS", False):
            logger.info("Redis usage is disabled in settings, using file-based storage")
            return None

        import redis  # type: ignore

        # Create connection pool if not already created
        if REDIS_CONNECTION_POOL is None:
            # Skip if REDIS_URL is empty
            if not settings.REDIS_URL:
                logger.info("REDIS_URL is empty, using file-based storage")
                return None

            REDIS_CONNECTION_POOL = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=1.0,  # Reduced timeout to fail faster
                socket_connect_timeout=1.0,
                retry_on_timeout=True,
                health_check_interval=30
            )

        # Get client from pool
        redis_client = redis.Redis(connection_pool=REDIS_CONNECTION_POOL)

        # Test connection with retry
        for attempt in range(REDIS_MAX_RETRIES):
            try:
                redis_client.ping()
                return redis_client
            except (redis.ConnectionError, redis.TimeoutError) as e:
                if attempt < REDIS_MAX_RETRIES - 1:
                    time.sleep(REDIS_RETRY_DELAY * (attempt + 1))  # Exponential backoff
                else:
                    # On final attempt, just log and return None for fallback
                    logger.warning(f"Redis connection failed after {REDIS_MAX_RETRIES} attempts: {e}")
                    return None

        return redis_client
    except (ImportError, Exception) as e:
        error_msg = f"Redis not available for session storage: {e}"
        logger.warning(error_msg)  # Changed from error to warning since we have a fallback
        # Always return None to allow for file-based fallback
        return None

def get_current_redis_client():
    """
    Get the current Redis client or None if not available

    Returns:
        Redis client or None for fallback storage
    """
    # First check if we're in test mode
    if IS_TESTING:
        logger.debug("In test mode - returning None for Redis client")
        return None

    try:
        client = get_redis_client()
        # Test the client
        if client:
            try:
                client.ping()  # Use ping to check if Redis is actually working
                return client
            except Exception as e:
                logger.warning(f"Redis ping failed: {e}")
                return None
        return None
    except Exception as e:
        logger.warning(f"Could not get Redis client: {e}")
        return None

def retrieve_session(session_id: str) -> Optional[Dict]:
    """
    Get session data by ID with improved error handling

    Args:
        session_id: The session ID to retrieve

    Returns:
        Session data or None if not found
    """
    # Get Redis client
    redis_client = get_current_redis_client()

    # If Redis is available, use it
    if redis_client:
        try:
            data = redis_client.get(f"session:{session_id}")
            if not data:
                return None

            # Parse data if it exists
            if isinstance(data, dict):
                return data
            elif isinstance(data, bytes):
                return json.loads(data.decode('utf-8'))
            elif isinstance(data, str):
                return json.loads(data)
            else:
                logger.error(f"Unexpected data type from Redis: {type(data)}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving session from Redis: {e}")
            # Continue to file-based fallback

    # Try file-based storage
    try:
        # Check for session in file storage
        session_dir = os.environ.get("SESSION_DIR", "sessions")
        if not os.path.exists(session_dir):
            os.makedirs(session_dir, exist_ok=True)

        session_file = os.path.join(session_dir, f"{session_id}.json")
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                data = json.load(f)
                # Check session expiry
                if data.get("expires_at", 0) > time.time():
                    return data

        # No valid session found
        return None
    except Exception as e:
        logger.error(f"Error retrieving session from file: {e}")
        return None

def cleanup_expired_sessions():
    """Clean up expired sessions from in-memory store (testing only)"""
    if not IS_TESTING:
        return  # Only clean up in-memory sessions in test mode

    current_time = time.time()
    expired = [sid for sid, session in SESSION_STORE.items()
               if session.get("expires_at", 0) < current_time]

    # Remove expired sessions
    for session_id in expired:
        SESSION_STORE.pop(session_id, None)

    if expired:
        logger.debug(f"Cleaned up {len(expired)} expired in-memory sessions")

def persist_session(session_id: str, data: Dict, ttl: int = SESSION_TTL) -> bool:
    """
    Save session data with TTL and improved reliability

    Args:
        session_id: The session ID to save
        data: The session data to save
        ttl: Time to live in seconds

    Returns:
        True if successful, False otherwise
    """
    # Get Redis client
    redis_client = get_current_redis_client()

    # If Redis is available, use it
    if redis_client:
        try:
            # Handle both sync and async Redis clients
            if hasattr(redis_client, 'setex') and callable(redis_client.setex):
                if asyncio.iscoroutinefunction(redis_client.setex):
                    # This is an async function but persist_session is sync,
                    # so we need to run it in the event loop
                    loop = asyncio.get_event_loop()
                    result = loop.run_until_complete(
                        redis_client.setex(
                            f"session:{session_id}",
                            ttl,
                            json.dumps(data)
                        )
                    )
                else:
                    # Synchronous Redis client
                    result = redis_client.setex(
                        f"session:{session_id}",
                        ttl,
                        json.dumps(data)
                    )
                return bool(result)
            else:
                logger.error("Redis client doesn't have setex method")
                # Continue to file-based fallback
        except Exception as e:
            logger.error(f"Error saving session to Redis: {e}")
            # Continue to file-based fallback

    # Use file-based storage as fallback
    try:
        # Ensure data has expiry time
        data_copy = data.copy()
        data_copy["expires_at"] = time.time() + ttl

        # Ensure session directory exists
        session_dir = os.environ.get("SESSION_DIR", "sessions")
        if not os.path.exists(session_dir):
            os.makedirs(session_dir, exist_ok=True)

        # Save session to file
        session_file = os.path.join(session_dir, f"{session_id}.json")
        with open(session_file, 'w') as f:
            json.dump(data_copy, f)

        logger.info(f"Saved session {session_id} to file")
        return True
    except Exception as e:
        logger.error(f"Error saving session to file: {e}")
        return False

class SessionStorage:
    """Abstract base class for session storage implementations."""

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get a session by ID."""
        raise NotImplementedError("Subclasses must implement get_session")

    async def set_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Set session data for a session ID."""
        raise NotImplementedError("Subclasses must implement set_session")

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID."""
        raise NotImplementedError("Subclasses must implement delete_session")

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        raise NotImplementedError("Subclasses must implement cleanup_expired_sessions")

class RedisSessionStorage(SessionStorage):
    """Redis-based session storage implementation."""

    def __init__(self):
        """Initialize Redis connection using application settings."""
        self.initialized = False
        self.redis_client = None
        self.prefix = getattr(settings.redis, "prefix", "birth_time_rectifier:") if hasattr(settings, "redis") else "birth_time_rectifier:"
        self.is_connected = False

        # Initialize Redis with retry logic
        self._initialize_redis()

    def _initialize_redis(self) -> None:
        """Initialize Redis with retry logic."""
        if not hasattr(settings, "redis") or not getattr(settings.redis, "use_redis", False):
            logger.info("Redis usage is disabled in settings")
            return

        try:
            # Import redis module
            import redis

            # Create Redis client with connection pool
            self.redis_client = redis.Redis(
                host=getattr(settings.redis, "host", "localhost"),
                port=getattr(settings.redis, "port", 6379),
                db=getattr(settings.redis, "db", 0),
                password=getattr(settings.redis, "password", None),
                socket_timeout=getattr(settings.redis, "connection_timeout", 5),
                socket_connect_timeout=getattr(settings.redis, "connection_timeout", 5),
                health_check_interval=30,
                retry_on_timeout=True
            )

            # Test connection
            self.redis_client.ping()

            # Connection successful
            self.is_connected = True
            self.initialized = True
            logger.info(f"Successfully connected to Redis at {getattr(settings.redis, 'host', 'localhost')}:{getattr(settings.redis, 'port', 6379)}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {str(e)}")
            self.redis_client = None
            self.is_connected = False
            logger.warning("Redis connection failed. Will fall back to file-based storage.")

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis."""
        if not self.is_connected or not self.redis_client:
            return None

        try:
            key = f"{self.prefix}session:{session_id}"
            data = self.redis_client.get(key)

            if data:
                try:
                    # Convert bytes to string if needed
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')

                    # Parse JSON data
                    session_data = json.loads(data)

                    # Check expiration if stored in session
                    if "expires_at" in session_data:
                        expires_at = datetime.fromisoformat(session_data["expires_at"])
                        if expires_at < datetime.now():
                            logger.debug(f"Session {session_id} has expired")
                            if self.redis_client:
                                self.redis_client.delete(key)
                            return None

                    logger.debug(f"Retrieved session {session_id} from Redis")
                    return session_data
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in Redis for session {session_id}")
                    return None
            else:
                logger.debug(f"No session found in Redis for {session_id}")
                return None

        except Exception as e:
            logger.error(f"Error retrieving session from Redis: {e}")
            return None

    async def set_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Set session data in Redis."""
        if not self.is_connected or not self.redis_client:
            return False

        try:
            key = f"{self.prefix}session:{session_id}"

            # Add expiration timestamp if not present
            if "expires_at" not in data:
                expiry_days = 30  # Default to 30 days
                expires_at = datetime.now() + timedelta(days=expiry_days)
                data["expires_at"] = expires_at.isoformat()

            # Calculate seconds until expiration
            expires_at = datetime.fromisoformat(data["expires_at"])
            ttl = int((expires_at - datetime.now()).total_seconds())

            # Ensure ttl is positive
            if ttl < 0:
                ttl = 3600  # Default to 1 hour if expiration is in the past

            # Store in Redis with expiration
            if self.redis_client:
                self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(data)
                )

            logger.debug(f"Saved session {session_id} to Redis with TTL {ttl} seconds")
            return True

        except Exception as e:
            logger.error(f"Error saving session to Redis: {e}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis."""
        if not self.is_connected:
            return False

        try:
            key = f"{self.prefix}session:{session_id}"
            self.redis_client.delete(key)
            logger.debug(f"Deleted session {session_id} from Redis")
            return True

        except Exception as e:
            logger.error(f"Error deleting session from Redis: {e}")
            return False

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions from Redis."""
        # Redis automatically expires keys based on TTL, so this is a no-op
        return 0

class FileSessionStorage(SessionStorage):
    """File-based session storage implementation."""

    def __init__(self):
        """Initialize file-based session storage."""
        self.session_dir = settings.session.session_dir

        # Ensure session directory exists
        os.makedirs(self.session_dir, exist_ok=True)
        logger.info(f"Using file-based session storage in {self.session_dir}")

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from file."""
        try:
            file_path = os.path.join(self.session_dir, f"{session_id}.json")

            if not os.path.exists(file_path):
                logger.debug(f"No session file found for {session_id}")
                return None

            with open(file_path, 'r') as f:
                session_data = json.load(f)

            # Check expiration
            if "expires_at" in session_data:
                expires_at = datetime.fromisoformat(session_data["expires_at"])
                if expires_at < datetime.now():
                    logger.debug(f"Session {session_id} has expired")
                    os.unlink(file_path)
                    return None

            logger.debug(f"Retrieved session {session_id} from file")
            return session_data

        except Exception as e:
            logger.error(f"Error retrieving session from file: {e}")
            return None

    async def set_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Set session data in file."""
        try:
            file_path = os.path.join(self.session_dir, f"{session_id}.json")

            # Add expiration timestamp if not present
            if "expires_at" not in data:
                expiry_days = 30  # Default to 30 days
                expires_at = datetime.now() + timedelta(days=expiry_days)
                data["expires_at"] = expires_at.isoformat()

            with open(file_path, 'w') as f:
                json.dump(data, f)

            logger.info(f"Saved session {session_id} to file")
            return True

        except Exception as e:
            logger.error(f"Error saving session to file: {e}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete session file."""
        try:
            file_path = os.path.join(self.session_dir, f"{session_id}.json")

            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"Deleted session {session_id} file")

            return True

        except Exception as e:
            logger.error(f"Error deleting session file: {e}")
            return False

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired session files."""
        try:
            count = 0
            for filename in os.listdir(self.session_dir):
                if not filename.endswith('.json'):
                    continue

                file_path = os.path.join(self.session_dir, filename)

                try:
                    with open(file_path, 'r') as f:
                        session_data = json.load(f)

                    if "expires_at" in session_data:
                        expires_at = datetime.fromisoformat(session_data["expires_at"])
                        if expires_at < datetime.now():
                            os.unlink(file_path)
                            count += 1

                except (json.JSONDecodeError, IOError):
                    # Remove invalid session files
                    os.unlink(file_path)
                    count += 1

            logger.info(f"Cleaned up {count} expired session files")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0

class SimpleSessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for session management with dual Redis/file-based storage.

    This middleware provides session management functionality with Redis as the primary
    storage and file-based storage as a fallback, ensuring the application remains
    functional even if Redis is unavailable.
    """

    def __init__(self, app: ASGIApp):
        """Initialize the session middleware."""
        super().__init__(app)

        # Try to initialize Redis storage first
        self.redis_storage = RedisSessionStorage()

        # Always initialize file storage as fallback
        self.file_storage = FileSessionStorage()

        # Session cookie settings
        self.cookie_name = settings.session.cookie_name
        self.cookie_secure = settings.session.cookie_secure
        self.cookie_httponly = settings.session.cookie_httponly
        self.cookie_samesite = settings.session.cookie_samesite
        self.cookie_max_age = settings.session.cookie_max_age

        # Start background cleanup task
        self.cleanup_task = None
        self.start_cleanup_task()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process the request, adding session handling."""
        # Get or create session ID from cookie
        session_id = request.cookies.get(self.cookie_name)

        # If no session ID, create one
        if not session_id:
            session_id = self._generate_session_id()

        # Store session ID in request state
        request.state.session_id = session_id

        # Create session data accessor for request
        request.state.session_data = {}

        # Load session data - try Redis first, then file storage
        if self.redis_storage and self.redis_storage.is_connected:
            session_data = await self.redis_storage.get_session(session_id)
            if session_data:
                request.state.session_data = session_data
            else:
                # Try file storage as fallback
                session_data = await self.file_storage.get_session(session_id)
                if session_data:
                    request.state.session_data = session_data
        else:
            # Redis not available, use file storage directly
            session_data = await self.file_storage.get_session(session_id)
            if session_data:
                request.state.session_data = session_data

        # Register session management methods in request
        request.state.get_session = self.get_session
        request.state.save_session = self.save_session
        request.state.clear_session = self.clear_session

        # Process the request
        response = await call_next(request)

        # Set session cookie if it's not already set
        if session_id and self.cookie_name not in response.headers.get("set-cookie", ""):
            # Convert string to literal for samesite
            samesite_value = None
            if self.cookie_samesite.lower() == "lax":
                samesite_value = "lax"
            elif self.cookie_samesite.lower() == "strict":
                samesite_value = "strict"
            elif self.cookie_samesite.lower() == "none":
                samesite_value = "none"

            response.set_cookie(
                key=self.cookie_name,
                value=session_id,
                max_age=self.cookie_max_age,
                secure=self.cookie_secure,
                httponly=self.cookie_httponly,
                samesite=samesite_value
            )

        # Save session data
        await self.save_session(request, request.state.session_data)

        return response

    def _generate_session_id(self) -> str:
        """Generate a new unique session ID."""
        timestamp = int(time.time())
        random_part = secrets.token_hex(16)
        return f"{timestamp}_{random_part}"

    async def get_session(self, request: Request) -> Dict[str, Any]:
        """Get the current session data."""
        return request.state.session_data

    async def save_session(self, request: Request, data: Dict[str, Any]) -> bool:
        """Save the session data."""
        session_id = request.state.session_id

        # Try Redis first if available
        if self.redis_storage.is_connected:
            success = await self.redis_storage.set_session(session_id, data)
            if success:
                return True

        # Fall back to file storage
        return await self.file_storage.set_session(session_id, data)

    async def clear_session(self, request: Request) -> bool:
        """Clear the current session."""
        session_id = request.state.session_id
        request.state.session_data = {}

        # Try to delete from both storage mechanisms
        redis_success = True
        if self.redis_storage.is_connected:
            redis_success = await self.redis_storage.delete_session(session_id)

        file_success = await self.file_storage.delete_session(session_id)

        return redis_success and file_success

    def start_cleanup_task(self) -> None:
        """Start background task to clean up expired sessions."""
        try:
            loop = asyncio.get_event_loop()
            self.cleanup_task = loop.create_task(self._periodic_cleanup())
        except Exception as e:
            logger.error(f"Failed to start session cleanup task: {e}")

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up expired sessions."""
        try:
            while True:
                # Run cleanup every day
                await asyncio.sleep(24 * 60 * 60)

                try:
                    # Clean up file storage
                    file_count = await self.file_storage.cleanup_expired_sessions()
                    logger.info(f"Cleaned up {file_count} expired session files")

                    # Clean up Redis storage (if connected)
                    if self.redis_storage.is_connected:
                        redis_count = await self.redis_storage.cleanup_expired_sessions()
                        if redis_count > 0:
                            logger.info(f"Cleaned up {redis_count} expired Redis sessions")

                except Exception as e:
                    logger.error(f"Error during session cleanup: {e}")

        except asyncio.CancelledError:
            logger.info("Session cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in session cleanup task: {e}")

# Helper function to get session service
def get_session_service():
    """Get the session service."""
    # Direct access to session middleware is not supported
    # Return a lightweight session service interface instead
    return SessionService()

class SessionService:
    """
    Session service interface for accessing session data.

    This service provides simplified access to session functionality,
    without requiring direct access to the middleware.
    """

    def __init__(self):
        """Initialize the session service."""
        # Initialize storages
        self.redis_storage = None
        self.file_storage = None

        # Flag to track initialization
        self.initialized = False

    def _init_if_needed(self):
        """Initialize storage if not already done."""
        if not self.initialized:
            self.redis_storage = RedisSessionStorage()
            self.file_storage = FileSessionStorage()
            self.initialized = True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data for a session ID."""
        self._init_if_needed()

        # Try Redis first if available
        if (self.redis_storage is not None and
            hasattr(self.redis_storage, "is_connected") and
            self.redis_storage.is_connected):
            try:
                data = asyncio.run(self.redis_storage.get_session(session_id))
                if data:
                    return data
            except Exception as e:
                logger.error(f"Error getting session from Redis: {e}")

        # Fall back to file storage
        try:
            if self.file_storage is not None:
                return asyncio.run(self.file_storage.get_session(session_id))
        except Exception as e:
            logger.error(f"Error getting session from file: {e}")
            return None

    def create_session(self, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
        """Create a new session."""
        self._init_if_needed()

        # Generate session ID if not provided
        if not session_id:
            timestamp = int(time.time())
            random_part = secrets.token_hex(16)
            session_id = f"{timestamp}_{random_part}"

        # Initialize empty data if not provided
        if data is None:
            data = {}

        # Add creation timestamp
        data["created_at"] = datetime.now().isoformat()

        # Add expiration timestamp
        expiry_days = 30  # Default to 30 days
        expires_at = datetime.now() + timedelta(days=expiry_days)
        data["expires_at"] = expires_at.isoformat()

        # Try to save session - Redis first if available
        if (self.redis_storage is not None and
            hasattr(self.redis_storage, "is_connected") and
            self.redis_storage.is_connected):
            try:
                success = asyncio.run(self.redis_storage.set_session(session_id, data))
                if success:
                    logger.info(f"Created session {session_id} in Redis")
                    return session_id
            except Exception as e:
                logger.error(f"Error creating session in Redis: {e}")

        # Fall back to file storage
        if self.file_storage is not None:
            try:
                success = asyncio.run(self.file_storage.set_session(session_id, data))
                if success:
                    logger.info(f"Created session {session_id} in file storage")
                    return session_id
            except Exception as e:
                logger.error(f"Error creating session in file: {e}")

        # Return session ID even if storage failed
        return session_id

    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update an existing session."""
        self._init_if_needed()

        # Get existing session first
        existing_data = self.get_session(session_id)
        if not existing_data:
            logger.warning(f"Cannot update non-existent session {session_id}")
            return False

        # Merge new data with existing data
        existing_data.update(data)

        # Update last accessed timestamp
        existing_data["last_accessed"] = datetime.now().isoformat()

        # Try to save session
        if self.redis_storage.is_connected:
            # Try Redis first
            try:
                success = asyncio.run(self.redis_storage.set_session(session_id, existing_data))
                if success:
                    return True
            except Exception as e:
                logger.error(f"Error updating session in Redis: {e}")

        # Fall back to file storage
        try:
            success = asyncio.run(self.file_storage.set_session(session_id, existing_data))
            return success
        except Exception as e:
            logger.error(f"Error updating session in file: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        self._init_if_needed()

        redis_success = True
        if self.redis_storage.is_connected:
            # Try Redis first
            try:
                redis_success = asyncio.run(self.redis_storage.delete_session(session_id))
            except Exception as e:
                logger.error(f"Error deleting session from Redis: {e}")
                redis_success = False

        # Always try file storage as well
        try:
            file_success = asyncio.run(self.file_storage.delete_session(session_id))
            return redis_success and file_success
        except Exception as e:
            logger.error(f"Error deleting session from file: {e}")
            return False
