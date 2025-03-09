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
from typing import Dict, Optional
import time

# Try to import Redis
try:
    import redis
except ImportError:
    redis = None  # Define redis as None to allow for type checking

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

def get_redis_client():
    """
    Get Redis client for session storage with improved reliability.
    Falls back to in-memory storage if Redis is not available.
    Uses connection pooling for better performance and reliability.
    """
    global REDIS_CONNECTION_POOL, REDIS_FALLBACK_NOTIFICATIONS

    try:
        import redis
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

def get_session(session_id: str) -> Optional[Dict]:
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

def save_session(session_id: str, data: Dict, ttl: int = SESSION_TTL) -> bool:
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

async def session_middleware(request: Request, call_next):
    """
    Enhanced middleware to handle session management with improved reliability.
    Retrieves session from cookie or header and makes it available in request state.
    """
    session_id = None
    start_time = time.time()

    try:
        # Try to get session ID from cookie or header with a fallback order
        session_id = (
            request.cookies.get("session_id") or
            request.headers.get("X-Session-ID") or
            request.headers.get("x-session-id")  # Case-insensitive fallback
        )

        # Create new session if needed for session/init endpoint
        new_session_created = False
        if request.url.path.endswith("/session/init"):
            session_id = str(uuid.uuid4())
            request.state.new_session_id = session_id
            session_data = {
                "created_at": time.time(),
                "last_accessed": time.time(),
                "expires_at": time.time() + SESSION_TTL
            }
            save_session(session_id, session_data)
            new_session_created = True

        # Add session to request state if it exists
        if session_id:
            session_data = get_session(session_id)
            if session_data:
                # Update last accessed time
                session_data["last_accessed"] = time.time()
                request.state.session = session_data
                request.state.session_id = session_id

                # If not a new session, update the access time in the background
                # This reduces latency impact of write operations
                if not new_session_created and random.random() < 0.2:  # 20% chance to avoid excessive writes
                    save_session(session_id, session_data)

        # Process the request
        response = await call_next(request)

        # If a new session was created, add session cookie
        if hasattr(request.state, "new_session_id"):
            # Set a more secure cookie
            response.set_cookie(
                key="session_id",
                value=request.state.new_session_id,
                httponly=True,
                secure=request.url.scheme == "https",
                max_age=SESSION_TTL,
                samesite="lax"
            )

            # Also set header for API clients
            response.headers["X-Session-ID"] = request.state.new_session_id

        return response
    except Exception as e:
        logger.error(f"Error in session middleware: {e}")
        # Ensure we return the response even if session handling fails
        try:
            return await call_next(request)
        except Exception as call_error:
            logger.critical(f"Failed to process request after session error: {call_error}")
            # Last resort fallback
            return Response(
                content=json.dumps({"detail": "Server error processing your request"}),
                status_code=500,
                media_type="application/json"
            )
    finally:
        # Log long session operations for optimization opportunities
        duration = time.time() - start_time
        if duration > 0.1:  # Log if session handling takes more than 100ms
            # Use debug level logging in test environments to avoid warnings in test output
            if os.environ.get("APP_ENV") == "test" or os.environ.get("TESTING") == "true":
                logger.debug(f"Test environment: Slow session processing: {duration:.3f}s for {request.url.path}")
            else:
                logger.info(f"Slow session processing: {duration:.3f}s for {request.url.path}")
