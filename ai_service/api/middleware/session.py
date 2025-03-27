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

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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
        import redis  # type: ignore
        from ai_service.core.config import settings

        # Create connection pool if not already created
        if REDIS_CONNECTION_POOL is None:
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
        logger.error(error_msg)
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

class SimpleSessionMiddleware(BaseHTTPMiddleware):
    """Middleware for handling sessions in FastAPI."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Main middleware function to process requests.

        Args:
            request: The FastAPI request
            call_next: The next middleware/handler in the chain

        Returns:
            FastAPI response
        """
        # Skip session handling for excluded paths
        path = request.url.path
        for excluded_path in EXCLUDED_PATHS:
            if path.startswith(excluded_path):
                return await call_next(request)

        # Get or create session ID
        session_id = _get_session_id_from_cookie(request) or _generate_session_id()

        # Initialize empty session
        session = {"session_id": session_id}

        # Try to load session data (from Redis or file)
        try:
            session_data = await load_session(session_id)
            if session_data:
                session = session_data
        except Exception as e:
            logger.warning(f"Failed to load session {session_id}: {e}")
            # Continue with empty session

        # Add session to request state
        request.state.session = session
        request.state.session_id = session_id

        # Call next middleware/handler to get response
        response = await call_next(request)

        # Save session to storage (redis or file)
        try:
            await save_session(request, response, session)
        except Exception as e:
            logger.warning(f"Failed to save session {session_id}: {e}")
            # Continue without saving session

        return response

# Utility functions for session management
def get_session_id(request: Request) -> Optional[str]:
    """Get session ID from request state or headers."""
    # Check if session ID is in request state
    if hasattr(request.state, "session_id"):
        return request.state.session_id

    # Check if session ID is in headers
    return request.headers.get("X-Session-ID")

def persist_session_data(session_id: str, session_data: Dict) -> bool:
    """
    Save session data for a given session ID.

    Args:
        session_id: The session ID to save
        session_data: The session data to save

    Returns:
        True if successful, False otherwise

    Raises:
        RuntimeError: If Redis is not available in production
    """
    try:
        # Store session data and delegate to the full implementation
        return persist_session(session_id, session_data)
    except Exception as e:
        logger.error(f"Error saving session {session_id}: {e}")
        if not IS_TESTING:
            raise RuntimeError(f"Error saving session: {e}")
        return False

async def create_session(session_id: Optional[str] = None) -> str:
    """
    Create a new session.

    Args:
        session_id: Optional session ID to use

    Returns:
        The session ID

    Raises:
        RuntimeError: If Redis is not available in production
    """
    # Generate a new session ID if none provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Create session data
    session_data = {
        "created_at": time.time(),
        "expires_at": time.time() + SESSION_TTL,
        "status": "active"
    }

    # Save session
    persist_session_data(session_id, session_data)

    return session_id

# Export the middleware class directly
session_middleware = SimpleSessionMiddleware

async def get_session(request: Request) -> Dict[str, Any]:
    """
    Get the session data for the request.

    Args:
        request: The FastAPI request

    Returns:
        Session data dictionary

    Raises:
        SessionError: If session cannot be retrieved
    """
    # Import in function to avoid circular imports
    from ai_service.core.config import settings

    # Try to get session ID from cookie, header, or query param
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = request.headers.get("X-Session-ID")
    if not session_id:
        query_params = request.query_params
        session_id = query_params.get("session_id")

    # If no session ID found, create a new session
    if not session_id:
        # Generate a new session ID if not present
        session_id = str(uuid.uuid4())
        request.state.new_session = True
        request.state.session_id = session_id
        return {}

    # Store session ID in request state
    request.state.session_id = session_id
    request.state.new_session = False

    # Try to load the session
    try:
        session_data = await load_session(session_id)
        return session_data or {}
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}")
        # Return empty session but don't raise error to allow app to continue
        return {}

async def save_session(request: Request, response: Response, session_data: Dict[str, Any]) -> None:
    """Save session data to storage (Redis or file)."""
    try:
        # Try to get Redis client
        redis_client = None
        try:
            redis_client = getattr(request.app.state, "redis", None) or get_current_redis_client()
        except Exception as redis_error:
            logger.warning(f"Could not use Redis for session: {str(redis_error)}")
            redis_client = None

        # If Redis client is available and properly configured, use it
        if redis_client and hasattr(redis_client, 'set') and callable(redis_client.set):
            try:
                await redis_save_session(redis_client, session_data)
                return
            except Exception as redis_save_error:
                logger.warning(f"Failed to save session to Redis: {str(redis_save_error)}")
                # Continue with file storage fallback
        else:
            logger.debug("Redis client not available or not properly configured, using file storage instead")

        # Use file storage as fallback
        file_storage_path = os.environ.get("SESSION_FILE_PATH",
                                        os.path.join(os.getcwd(), "ai_service", "sessions"))
        # Ensure directory exists
        os.makedirs(file_storage_path, exist_ok=True)

        # Save to file
        file_path = os.path.join(file_storage_path, f"{session_data['session_id']}.json")
        with open(file_path, "w") as f:
            json.dump(session_data, f)

        logger.info(f"Saved session {session_data['session_id']} to file")

    except Exception as e:
        # Don't crash - just log the error
        logger.error(f"Failed to save session {session_data.get('session_id', 'unknown')}: {str(e)}")

async def redis_save_session(redis_client, session_data: Dict[str, Any]) -> None:
    """Save session data to Redis.

    Args:
        redis_client: Redis client instance
        session_data: Session data to save
    """
    # First check if redis_client is None
    if redis_client is None:
        logger.warning("Redis client is None, cannot save session to Redis")
        raise RuntimeError("Redis client is not available")

    session_id = session_data.get('session_id')
    if not session_id:
        logger.error("Cannot save session without session_id")
        return

    # Get session expiry time from configuration
    session_expiry = 3600  # Default 1 hour
    try:
        from ai_service.core.config import settings
        session_expiry = getattr(settings, "SESSION_EXPIRY", 3600)
    except ImportError:
        logger.warning("Could not import settings, using default session expiry")

    # Serialize session data
    session_data_json = json.dumps(session_data)

    # Handle both sync and async Redis clients
    if hasattr(redis_client, 'set') and callable(redis_client.set):
        if asyncio.iscoroutinefunction(redis_client.set):
            # Async Redis client
            await redis_client.set(
                f"session:{session_id}",
                session_data_json,
                ex=session_expiry
            )
        else:
            # Sync Redis client
            redis_client.set(
                f"session:{session_id}",
                session_data_json,
                ex=session_expiry
            )
    else:
        logger.error("Redis client doesn't have set method")
        raise RuntimeError("Invalid Redis client configuration")

def _generate_session_id() -> str:
    """Generate a random session ID."""
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    timestamp = int(time.time())
    return f"{timestamp}_{random_part}"

def _get_session_id_from_cookie(request: Request) -> Optional[str]:
    """Get session ID from cookies."""
    if SESSION_COOKIE_NAME in request.cookies:
        return request.cookies[SESSION_COOKIE_NAME]
    return None

async def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Load session data from Redis or file storage."""
    # Try Redis first
    redis_client = None
    try:
        redis_client = get_current_redis_client()
    except Exception as e:
        logger.warning(f"Failed to get Redis client: {e}")
        redis_client = None

    if redis_client:
        try:
            # Handle both async and sync Redis clients
            if hasattr(redis_client, 'get') and callable(redis_client.get):
                if asyncio.iscoroutinefunction(redis_client.get):
                    # Async Redis client
                    session_data = await redis_client.get(f"session:{session_id}")
                else:
                    # Sync Redis client
                    session_data = redis_client.get(f"session:{session_id}")

                # Parse JSON if we got data
                if session_data:
                    if isinstance(session_data, bytes):
                        return json.loads(session_data.decode('utf-8'))
                    elif isinstance(session_data, str):
                        return json.loads(session_data)
                    elif isinstance(session_data, dict):
                        return session_data
        except Exception as e:
            logger.warning(f"Redis error when loading session: {e}")
            # Fall back to file storage

    # Try file storage as fallback
    try:
        file_storage_path = os.environ.get("SESSION_FILE_PATH",
                                         os.path.join(os.getcwd(), "ai_service", "sessions"))
        file_path = os.path.join(file_storage_path, f"{session_id}.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()
                if content.strip():  # Check if file is not empty
                    return json.loads(content)
                else:
                    logger.warning(f"Empty session file found for {session_id}")
    except json.JSONDecodeError as e:
        logger.warning(f"File storage JSON error when loading session: {e}")
    except Exception as e:
        logger.warning(f"File storage error when loading session: {e}")

    # Return None if no session found
    return None
