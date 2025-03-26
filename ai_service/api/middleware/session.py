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
IS_TESTING = False

# In-memory store for testing only
SESSION_STORE: Dict[str, Dict] = {}
SESSION_TTL = 3600  # 1 hour in seconds

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
        Redis client or raises an exception if Redis is not available in production

    Raises:
        RuntimeError: If Redis is not available in production
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
                socket_timeout=3.0,
                socket_connect_timeout=3.0,
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
                    raise e

        return redis_client
    except (ImportError, Exception) as e:
        error_msg = f"Redis not available for session storage: {e}"
        logger.error(error_msg)
        if not IS_TESTING:
            raise RuntimeError(error_msg)
        return None

# Try to get Redis client lazily for each request instead of at module level
def get_current_redis_client():
    """
    Get the current Redis client or None if in testing mode

    Raises:
        RuntimeError: If Redis is not available in production
    """
    try:
        return get_redis_client()
    except Exception as e:
        if not IS_TESTING:
            raise RuntimeError(f"Failed to get Redis client: {e}")
        return None

def retrieve_session(session_id: str) -> Optional[Dict]:
    """
    Get session data by ID with improved error handling

    Args:
        session_id: The session ID to retrieve

    Returns:
        Session data or None if not found

    Raises:
        RuntimeError: If Redis is not available in production
    """
    # Get Redis client or raise error if not available in production
    redis_client = get_current_redis_client()

    # In production, Redis client must be available
    if not redis_client and not IS_TESTING:
        error_msg = "Redis client not available for session retrieval in production environment"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

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
            if not IS_TESTING:
                raise RuntimeError(f"Redis error: {e}")
            return None

    # In test mode only, use in-memory store
    if IS_TESTING:
        session = SESSION_STORE.get(session_id)
        if session and session.get("expires_at", 0) > time.time():
            return session

        # Cleanup expired sessions periodically
        if random.random() < 0.01:
            cleanup_expired_sessions()

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

    Raises:
        RuntimeError: If Redis is not available in production
    """
    # Get Redis client or raise error if not available in production
    redis_client = get_current_redis_client()

    # In production, Redis client must be available
    if not redis_client and not IS_TESTING:
        error_msg = "Redis client not available for session persistence in production environment"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

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
                if not IS_TESTING:
                    raise RuntimeError("Invalid Redis client configuration")
                return False
        except Exception as e:
            logger.error(f"Error saving session to Redis: {e}")
            if not IS_TESTING:
                raise RuntimeError(f"Redis error: {e}")
            return False

    # In test mode only, use in-memory store
    if IS_TESTING:
        data_copy = data.copy()
        data_copy["expires_at"] = time.time() + ttl
        SESSION_STORE[session_id] = data_copy
        return True

    return False

class SimpleSessionMiddleware(BaseHTTPMiddleware):
    """Middleware for handling sessions in FastAPI."""

    async def dispatch(self, request: Request, call_next):
        """Process request, handling session state."""
        # Initialize session state
        request.state.session = {}
        request.state.session_id = None
        request.state.new_session = True

        # Get or create session
        try:
            session_data = await get_session(request)
            request.state.session = session_data
        except SessionError as e:
            logger.error(f"Failed to get session: {e}")
            # Initialize empty session on error
            request.state.session = {}

        # Process the request
        response = await call_next(request)

        # Save session after request
        try:
            await save_session(request, response, request.state.session)
        except SessionError as e:
            logger.error(f"Failed to save session: {e}")

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
        RuntimeError: If Redis is not available in production
    """
    # Import in function to avoid circular imports
    from ai_service.core.config import settings

    session_id = request.cookies.get("session_id")

    if not session_id:
        # Generate a new session ID if not present
        session_id = str(uuid.uuid4())
        request.state.new_session = True
        request.state.session_id = session_id
        return {}

    # Store session ID in request state
    request.state.session_id = session_id
    request.state.new_session = False

    # Get Redis client (or None in testing mode)
    redis_client = getattr(request.app.state, "redis", None) or get_current_redis_client()

    # In production, Redis client must be available
    if not redis_client and not IS_TESTING:
        error_msg = "Redis client not available for session retrieval in production environment"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # If Redis is available, use it
    if redis_client:
        try:
            # Handle both sync and async Redis clients
            if hasattr(redis_client, 'get') and callable(redis_client.get):
                if asyncio.iscoroutinefunction(redis_client.get):
                    # Async Redis client
                    session_data_json = await redis_client.get(f"session:{session_id}")
                else:
                    # Sync Redis client
                    session_data_json = redis_client.get(f"session:{session_id}")

                if session_data_json:
                    # Parse session data
                    return json.loads(session_data_json)

                # Session not found
                request.state.new_session = True
                return {}
            else:
                logger.error("Redis client doesn't have get method")
                if not IS_TESTING:
                    raise RuntimeError("Invalid Redis client configuration")
                request.state.new_session = True
                return {}
        except json.JSONDecodeError as e:
            error_msg = f"Failed to decode session data: {str(e)}"
            logger.error(error_msg)
            raise SessionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to retrieve session from Redis: {str(e)}"
            logger.error(error_msg)
            if not IS_TESTING:
                raise RuntimeError(f"Redis error: {e}")
            request.state.new_session = True
            return {}

    # In test mode only, use in-memory store
    if IS_TESTING:
        session = SESSION_STORE.get(session_id)
        if session and session.get("expires_at", 0) > time.time():
            return session.copy()

        # Session not found or expired
        request.state.new_session = True
        return {}

    # This should not happen - Redis is required in production
    error_msg = "Redis is required for session management in production"
    logger.error(error_msg)
    raise RuntimeError(error_msg)

async def save_session(request: Request, response: Response, session_data: Dict[str, Any]) -> None:
    """
    Save session data for the request.

    Args:
        request: The FastAPI request
        response: The FastAPI response
        session_data: Session data to save

    Raises:
        SessionError: If session cannot be saved
        RuntimeError: If Redis is not available in production
    """
    # Import in function to avoid circular imports
    from ai_service.core.config import settings

    session_id = request.state.session_id

    # Set session cookie
    secure_cookies = getattr(settings, "SECURE_COOKIES", False)
    cookie_domain = getattr(settings, "COOKIE_DOMAIN", None)

    cookie_args = {
        "key": "session_id",
        "value": session_id,
        "httponly": True,
        "secure": secure_cookies,
        "samesite": "lax",
        "max_age": settings.SESSION_EXPIRY
    }

    # Add domain if specified
    if cookie_domain:
        cookie_args["domain"] = cookie_domain

    response.set_cookie(**cookie_args)

    # Get Redis client (or None in testing mode)
    redis_client = getattr(request.app.state, "redis", None) or get_current_redis_client()

    # In production, Redis client must be available
    if not redis_client and not IS_TESTING:
        error_msg = "Redis client not available for session saving in production environment"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # If Redis is available, use it
    if redis_client:
        try:
            # Serialize session data
            session_data_json = json.dumps(session_data)

            # Handle both sync and async Redis clients
            if hasattr(redis_client, 'set') and callable(redis_client.set):
                if asyncio.iscoroutinefunction(redis_client.set):
                    # Async Redis client
                    await redis_client.set(
                        f"session:{session_id}",
                        session_data_json,
                        ex=settings.SESSION_EXPIRY
                    )
                else:
                    # Sync Redis client
                    redis_client.set(
                        f"session:{session_id}",
                        session_data_json,
                        ex=settings.SESSION_EXPIRY
                    )
                return
            else:
                logger.error("Redis client doesn't have set method")
                if not IS_TESTING:
                    raise RuntimeError("Invalid Redis client configuration")
        except Exception as e:
            error_msg = f"Failed to save session to Redis: {str(e)}"
            logger.error(error_msg)
            if not IS_TESTING:
                raise RuntimeError(f"Redis error: {e}")

    # In test mode only, use in-memory store
    if IS_TESTING:
        data_copy = session_data.copy()
        data_copy["expires_at"] = time.time() + settings.SESSION_EXPIRY
        SESSION_STORE[session_id] = data_copy
        return

    # This should not happen - Redis is required in production
    if not redis_client:
        error_msg = "Redis is required for session management in production"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
