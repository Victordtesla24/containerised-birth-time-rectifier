"""
Rate Limiting Middleware for API Gateway

This module provides rate limiting functionality to protect the API from abuse.
It uses Redis to track request counts per client IP address and applies
configurable rate limits.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
import redis
import os
from datetime import datetime, timedelta
import asyncio
import threading
from collections import defaultdict

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_RATE_LIMIT = 60  # requests per minute
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds

class RateLimitExceeded(Exception):
    """Exception raised when a client exceeds their rate limit."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        self.message = f"Rate limit exceeded. Try again in {retry_after} seconds."
        super().__init__(self.message)

class InMemoryRateLimiter:
    """Simple in-memory rate limiter for when Redis is not available."""
    def __init__(self, rate_limit: int = 60, window: int = 60):
        self.rate_limit = rate_limit
        self.window = window  # in seconds
        self.requests = defaultdict(list)
        self.lock = threading.Lock()

    def is_rate_limited(self, key: str) -> bool:
        """Check if a key is rate limited."""
        with self.lock:
            now = datetime.now()
            # Clean old requests
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < timedelta(seconds=self.window)
            ]
            # Check if over limit
            if len(self.requests[key]) >= self.rate_limit:
                return True
            # Record this request
            self.requests[key].append(now)
            return False

    def get_remaining(self, key: str) -> int:
        """Get remaining requests for a key."""
        with self.lock:
            now = datetime.now()
            # Clean old requests
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < timedelta(seconds=self.window)
            ]
            return self.rate_limit - len(self.requests[key])

# Global in-memory rate limiter as fallback
IN_MEMORY_LIMITER = None

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests.

    Uses Redis if available, falls back to in-memory storage.
    """
    def __init__(
        self,
        app,
        redis_url: Optional[str] = None,
        rate_limit: int = 60,
        window: int = 60
    ):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.window = window
        self.redis_client = None
        self.redis_available = False
        self.redis_url = redis_url
        self.in_memory = InMemoryRateLimiter(rate_limit, window)

        # Try to setup Redis
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url)
                # Test connection only if client creation was successful
                if self.redis_client:
                    self.redis_client.ping()
                    self.redis_available = True
                    logger.info(f"Redis rate limiter connected to {redis_url}")
                else:
                    logger.warning("Failed to create Redis client, using in-memory rate limiting")
            except ImportError:
                logger.warning("Redis package not installed, using in-memory rate limiting")
            except Exception as e:
                logger.error(f"Redis error in rate limiter: {e}")
                logger.warning("Falling back to in-memory rate limiting")
        else:
            logger.info("No Redis URL provided, using in-memory rate limiting")

    async def dispatch(self, request: Request, call_next):
        """
        Rate limit requests based on client IP.

        Args:
            request: The incoming request
            call_next: The next middleware/handler

        Returns:
            The response
        """
        # Skip rate limiting for specific paths
        if self._should_skip_rate_limiting(request):
            return await call_next(request)

        # Get client IP (or other identifier)
        client_id = self._get_client_identifier(request)
        rate_limit_key = f"rate_limit:{client_id}"

        # Check if rate limited
        if self.redis_available and self.redis_client:
            try:
                # Use Redis for rate limiting
                limited = await self._check_redis_rate_limit(rate_limit_key)
                if limited:
                    retry_after = self.window
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "Too many requests",
                            "retry_after": retry_after
                        },
                        headers={"Retry-After": str(retry_after)}
                    )
            except Exception as e:
                logger.error(f"Redis error in rate limiter: {e}")
                # Fall back to in-memory rate limiting
                self.redis_available = False

        # Use in-memory rate limiting as fallback
        if not self.redis_available:
            if self.in_memory.is_rate_limited(client_id):
                retry_after = self.window
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too many requests",
                        "retry_after": retry_after
                    },
                    headers={"Retry-After": str(retry_after)}
                )

        # Request is not rate limited, proceed
        response = await call_next(request)

        # Add rate limit headers
        if self.redis_available and self.redis_client:
            try:
                remaining = await self._get_redis_remaining(rate_limit_key)
                response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Reset"] = str(self.window)
            except Exception:
                # Just don't set the headers if Redis fails
                pass
        else:
            # Set headers from in-memory limiter
            remaining = self.in_memory.get_remaining(client_id)
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(self.window)

        return response

    async def _check_redis_rate_limit(self, key: str) -> bool:
        """Check if a key is rate limited using Redis."""
        # Safety check - return False if Redis client is None
        if not self.redis_client:
            return False

        try:
            # Get current count
            count = self.redis_client.get(key)
            if count is None:
                # First request, set initial count with expiry
                pipe = self.redis_client.pipeline()
                pipe.set(key, 1)
                pipe.expire(key, self.window)
                pipe.execute()
                return False

            # Increment count
            count = int(count)
            if count >= self.rate_limit:
                return True

            # Not limited, increment counter
            self.redis_client.incr(key)
            return False
        except Exception as e:
            logger.error(f"Redis error in rate limiter: {e}")
            self.redis_available = False
            return False

    async def _get_redis_remaining(self, key: str) -> int:
        """Get remaining requests for a key using Redis."""
        # Safety check - return max limit if Redis client is None
        if not self.redis_client:
            return self.rate_limit

        try:
            count = self.redis_client.get(key)
            if count is None:
                return self.rate_limit
            return max(0, self.rate_limit - int(count))
        except Exception as e:
            logger.error(f"Redis error getting remaining limit: {e}")
            return self.rate_limit

    def _should_skip_rate_limiting(self, request: Request) -> bool:
        """Check if rate limiting should be skipped for this request."""
        # Skip rate limiting for health check and options requests
        path = request.url.path.lower()
        if path.endswith("/health") or "health" in path:
            return True
        if request.method == "OPTIONS":
            return True

        return False

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get a unique identifier for the client.

        Uses client IP or X-Forwarded-For header.
        """
        # Try to get client IP from headers first (for proxied requests)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Use the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        # Use direct client IP as fallback
        client = request.client
        if client and hasattr(client, "host"):
            return client.host

        # Last resort
        return "unknown"

def add_rate_limiter(app, redis_url: Optional[str] = None, rate_limit: int = 60, window: int = 60):
    """
    Add rate limiting middleware to the app.

    Args:
        app: The FastAPI app
        redis_url: Optional Redis URL for distributed rate limiting
        rate_limit: Number of requests allowed per window
        window: Time window in seconds
    """
    global IN_MEMORY_LIMITER

    # Create in-memory limiter if it doesn't exist
    if IN_MEMORY_LIMITER is None:
        IN_MEMORY_LIMITER = InMemoryRateLimiter(rate_limit, window)

    # Add middleware
    app.add_middleware(
        RateLimiterMiddleware,
        redis_url=redis_url,
        rate_limit=rate_limit,
        window=window
    )

    logger.info(f"Rate limiting middleware added (limit: {rate_limit} per {window}s)")
