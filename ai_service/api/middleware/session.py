"""
Session management middleware for the Birth Time Rectifier API.
Provides session tracking and persistence for all API endpoints.
"""

from fastapi import Request, Response
import logging
import uuid
import json
import random
import os
from typing import Dict, Optional, Any, Callable
import time
import sys
from starlette.middleware.base import BaseHTTPMiddleware
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
logger = logging.getLogger("birth-time-rectifier.session")

# In-memory session store for development/testing
# In production, this would be replaced with Redis
SESSION_STORE: Dict[str, Dict] = {}
SESSION_TTL = 3600  # 1 hour in seconds

# Redis connection pool and retry configuration
REDIS_CONNECTION_POOL = None
REDIS_MAX_RETRIES = 3
REDIS_RETRY_DELAY = 0.5  # seconds
REDIS_FALLBACK_NOTIFICATIONS = 0  # Counter to avoid excessive logging

# Custom exception for session-related errors
class SessionError(Exception):
    """Exception raised for session-related errors."""
    pass

def get_redis_client():
    """
    Get Redis client for session storage with improved reliability.
    Falls back to in-memory storage if Redis is not available.
    Uses connection pooling for better performance and reliability.
    """
    global REDIS_CONNECTION_POOL, REDIS_FALLBACK_NOTIFICATIONS

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
                # Reset notification counter if connection succeeds
                if REDIS_FALLBACK_NOTIFICATIONS > 0:
                    logger.info("Redis connection re-established after previous failures")
                    REDIS_FALLBACK_NOTIFICATIONS = 0
                return redis_client
            except (redis.ConnectionError, redis.TimeoutError) as e:
                if attempt < REDIS_MAX_RETRIES - 1:
                    time.sleep(REDIS_RETRY_DELAY * (attempt + 1))  # Exponential backoff
                else:
                    raise e

        return redis_client
    except (ImportError, Exception) as e:
        # Limit log spam by only logging every 10th failure
        REDIS_FALLBACK_NOTIFICATIONS += 1
        if REDIS_FALLBACK_NOTIFICATIONS <= 1 or REDIS_FALLBACK_NOTIFICATIONS % 10 == 0:
            logger.warning(f"Redis not available for session storage: {e}. Using in-memory store. (Alert {REDIS_FALLBACK_NOTIFICATIONS})")
        return None

# Try to get Redis client lazily for each request instead of at module level
# This allows recovery if Redis becomes available after app startup
def get_current_redis_client():
    """Get the current Redis client or None if unavailable"""
    try:
        client = get_redis_client()
        return client
    except Exception:
        return None

def retrieve_session(session_id: str) -> Optional[Dict]:
    """Get session data by ID with improved error handling"""
    # Try Redis first
    redis_client = get_current_redis_client()

    if redis_client:
        try:
            # Get data from Redis with retry mechanism
            for attempt in range(REDIS_MAX_RETRIES):
                try:
                    # Get data from Redis
                    data = redis_client.get(f"session:{session_id}")

                    if not data:
                        # Fall back to in-memory store if not in Redis
                        break

                    # Handle data based on its type
                    if isinstance(data, dict):
                        # Already a dict, no need to parse
                        return data
                    elif isinstance(data, bytes):
                        # Convert bytes to string and parse
                        return json.loads(data.decode('utf-8'))
                    elif isinstance(data, str):
                        # Parse string
                        return json.loads(data)
                    else:
                        # Last resort - try to convert to string and parse
                        try:
                            return json.loads(str(data))
                        except:
                            logger.error(f"Unsupported Redis response type: {type(data)}")
                            break  # Try in-memory store
                except ((redis.ConnectionError, redis.TimeoutError) if redis else Exception) as e:
                    if attempt < REDIS_MAX_RETRIES - 1:
                        time.sleep(REDIS_RETRY_DELAY * (attempt + 1))
                    else:
                        logger.warning(f"Redis connection failed after {REDIS_MAX_RETRIES} attempts: {e}")
                        break  # Try in-memory store
                except Exception as e:
                    logger.error(f"Error processing session data for {session_id}: {e}")
                    break  # Try in-memory store
        except Exception as e:
            logger.error(f"Unexpected error retrieving session from Redis: {e}")
            # Continue to in-memory store

    # Use in-memory store as fallback
    session = SESSION_STORE.get(session_id)
    if session and session.get("expires_at", 0) > time.time():
        return session

    # Cleanup expired sessions periodically (1% chance on each request)
    if random.random() < 0.01:
        cleanup_expired_sessions()

    return None

def cleanup_expired_sessions():
    """Clean up expired sessions from in-memory store"""
    current_time = time.time()
    expired = []

    # Find expired sessions
    for session_id, session in SESSION_STORE.items():
        if session.get("expires_at", 0) < current_time:
            expired.append(session_id)

    # Remove expired sessions
    for session_id in expired:
        SESSION_STORE.pop(session_id, None)

    if expired:
        logger.debug(f"Cleaned up {len(expired)} expired in-memory sessions")

def persist_session(session_id: str, data: Dict, ttl: int = SESSION_TTL) -> bool:
    """Save session data with TTL and improved reliability"""
    # Always update in-memory store as a fallback
    data_copy = data.copy()
    data_copy["expires_at"] = time.time() + ttl
    SESSION_STORE[session_id] = data_copy

    # Try Redis if available
    redis_client = get_current_redis_client()
    if redis_client:
        try:
            # With retry mechanism
            for attempt in range(REDIS_MAX_RETRIES):
                try:
                    result = redis_client.setex(
                        f"session:{session_id}",
                        ttl,
                        json.dumps(data)
                    )
                    # Handle different Redis client return types
                    return bool(result)
                except ((redis.ConnectionError, redis.TimeoutError) if redis else Exception) as e:
                    if attempt < REDIS_MAX_RETRIES - 1:
                        time.sleep(REDIS_RETRY_DELAY * (attempt + 1))
                    else:
                        logger.warning(f"Redis write failed after {REDIS_MAX_RETRIES} attempts: {e}")
                        return True  # Return True because in-memory store was updated
        except Exception as e:
            logger.error(f"Error saving session to Redis: {e}")
            return True  # Return True because in-memory store was updated

    return True  # In-memory store update succeeded

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
    """Save session data for a given session ID."""
    try:
        # Store session data in memory store and delegate to the full implementation
        return persist_session(session_id, session_data)
    except Exception as e:
        logger.error(f"Error saving session {session_id}: {e}")
        return False

async def create_session(session_id: Optional[str] = None) -> str:
    """Create a new session."""
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

# Export the middleware class directly - SIMPLIFIED VERSION FOR FASTAPI COMPATIBILITY
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

    # Get session from Redis
    redis_client = request.app.state.redis
    if not redis_client:
        error_msg = "Redis client is not available"
        logger.error(error_msg)
        raise SessionError(error_msg)

    try:
        # Get session data from Redis
        session_data_json = await redis_client.get(f"session:{session_id}")

        if not session_data_json:
            # Session expired or doesn't exist
            request.state.new_session = True
            return {}

        # Parse session data
        return json.loads(session_data_json)

    except json.JSONDecodeError as e:
        error_msg = f"Failed to decode session data: {str(e)}"
        logger.error(error_msg)
        raise SessionError(error_msg)

    except Exception as e:
        error_msg = f"Failed to retrieve session: {str(e)}"
        logger.error(error_msg)
        raise SessionError(error_msg)

async def save_session(request: Request, response: Response, session_data: Dict[str, Any]) -> None:
    """
    Save session data for the request.

    Args:
        request: The FastAPI request
        response: The FastAPI response
        session_data: Session data to save

    Raises:
        SessionError: If session cannot be saved
    """
    session_id = request.state.session_id

    # Set session cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=settings.SECURE_COOKIES,
        samesite="lax",
        max_age=settings.SESSION_EXPIRY
    )

    # Save to Redis
    redis_client = request.app.state.redis
    if not redis_client:
        error_msg = "Redis client is not available"
        logger.error(error_msg)
        raise SessionError(error_msg)

    try:
        # Serialize session data
        session_data_json = json.dumps(session_data)

        # Save to Redis with expiry
        await redis_client.set(
            f"session:{session_id}",
            session_data_json,
            expire=settings.SESSION_EXPIRY
        )

    except Exception as e:
        error_msg = f"Failed to save session: {str(e)}"
        logger.error(error_msg)
        raise SessionError(error_msg)
