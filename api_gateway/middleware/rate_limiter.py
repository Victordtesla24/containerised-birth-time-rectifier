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

class RateLimiter:
    """Rate limiter implementation for FastAPI."""

    def __init__(
        self,
        redis_url: str,
        rate_limit: int = DEFAULT_RATE_LIMIT,
        window: int = DEFAULT_RATE_LIMIT_WINDOW,
        whitelist_paths: Optional[List[str]] = None,
        whitelist_ips: Optional[List[str]] = None,
    ):
        """
        Initialize the rate limiter.

        Args:
            redis_url: Redis URL for storing rate limit data
            rate_limit: Maximum requests per window
            window: Time window in seconds
            whitelist_paths: List of path prefixes to exclude from rate limiting
            whitelist_ips: List of IP addresses to exclude from rate limiting
        """
        self.redis_url = redis_url
        self.rate_limit = rate_limit
        self.window = window
        self.whitelist_paths = whitelist_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.whitelist_ips = set(whitelist_ips or [])

        # Initialize Redis client
        try:
            self.redis = redis.from_url(redis_url)
            self.redis_available = True
            logger.info(f"Rate limiter connected to Redis at {redis_url}")
            logger.info(f"Rate limit: {rate_limit} requests per {window} seconds")
        except Exception as e:
            self.redis_available = False
            logger.warning(f"Rate limiter couldn't connect to Redis: {e}")
            logger.warning("Rate limiting will be disabled")

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process the request with rate limiting.

        Args:
            request: The incoming request
            call_next: Function to call the next middleware or handler

        Returns:
            The response
        """
        # Skip rate limiting if Redis is not available
        if not self.redis_available:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Skip rate limiting for whitelisted paths or IPs
        path = request.url.path
        if self._is_whitelisted(path, client_ip):
            return await call_next(request)

        # Check rate limit
        try:
            self._check_rate_limit(client_ip)
            response = await call_next(request)
            return response
        except RateLimitExceeded as e:
            # Return rate limit exceeded error
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": e.message,
                },
                headers={"Retry-After": str(e.retry_after)},
            )
        except Exception as e:
            # Log error and continue processing the request
            logger.error(f"Error in rate limiter: {e}")
            return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """
        Get the client's IP address from the request.

        Args:
            request: The incoming request

        Returns:
            The client's IP address
        """
        # Check X-Forwarded-For header first (for clients behind proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the chain (client IP)
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            # Fall back to the direct client address
            client_ip = request.client.host if request.client else "unknown"

        return client_ip

    def _is_whitelisted(self, path: str, client_ip: str) -> bool:
        """
        Check if the path or IP is whitelisted.

        Args:
            path: The request path
            client_ip: The client's IP address

        Returns:
            True if whitelisted, False otherwise
        """
        # Check path whitelist
        for whitelist_path in self.whitelist_paths:
            if path.startswith(whitelist_path):
                return True

        # Check IP whitelist
        if client_ip in self.whitelist_ips:
            return True

        return False

    def _check_rate_limit(self, client_ip: str) -> None:
        """
        Check if the client has exceeded their rate limit.

        Args:
            client_ip: The client's IP address

        Raises:
            RateLimitExceeded: If the rate limit is exceeded
        """
        try:
            # Generate key for this client
            key = f"rate_limit:{client_ip}"
            current_time = int(time.time())
            window_start = current_time - self.window

            # Use Redis pipeline for atomic operations
            with self.redis.pipeline() as pipe:
                # Remove old requests outside the current window
                pipe.zremrangebyscore(key, 0, window_start)
                # Count requests in the current window
                pipe.zcount(key, window_start, current_time)
                # Add current request with timestamp as score
                pipe.zadd(key, {str(current_time): current_time})
                # Set expiration to ensure cleanup
                pipe.expire(key, self.window * 2)  # 2x window to ensure cleanup
                # Execute pipeline
                _, request_count, _, _ = pipe.execute()

            # Check if rate limit exceeded
            if request_count >= self.rate_limit:
                # Calculate when the client can try again
                retry_after = self.window - (current_time - window_start)
                retry_after = max(1, retry_after)  # Ensure at least 1 second
                logger.warning(f"Rate limit exceeded for {client_ip}. Retry after {retry_after}s")
                raise RateLimitExceeded(retry_after=retry_after)

        except redis.RedisError as e:
            # Log error but allow request to proceed
            logger.error(f"Redis error in rate limiter: {e}")
            logger.warning("Allowing request due to rate limiter error")

def add_rate_limiter(
    app: FastAPI,
    redis_url: str,
    rate_limit: int = DEFAULT_RATE_LIMIT,
    window: int = DEFAULT_RATE_LIMIT_WINDOW,
    whitelist_paths: Optional[List[str]] = None,
    whitelist_ips: Optional[List[str]] = None,
) -> None:
    """
    Add rate limiter middleware to the FastAPI application.

    Args:
        app: The FastAPI application
        redis_url: Redis URL for storing rate limit data
        rate_limit: Maximum requests per window
        window: Time window in seconds
        whitelist_paths: List of path prefixes to exclude from rate limiting
        whitelist_ips: List of IP addresses to exclude from rate limiting
    """
    # Create the rate limiter instance
    rate_limiter = RateLimiter(
        redis_url=redis_url,
        rate_limit=rate_limit,
        window=window,
        whitelist_paths=whitelist_paths,
        whitelist_ips=whitelist_ips
    )

    # Add the middleware using the instance's __call__ method
    app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limiter.__call__)

    logger.info("Rate limiter middleware added to application")
