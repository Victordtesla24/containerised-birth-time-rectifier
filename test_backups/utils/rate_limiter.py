"""
Rate limiter implementation for OpenAI API calls during testing.

This module provides rate limiting to prevent exceeding OpenAI API quotas during
testing. It implements a token bucket algorithm that allows for bursts while
maintaining a sustainable long-term rate.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Callable, Any, Union, Protocol

logger = logging.getLogger(__name__)

@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter"""
    requests_per_minute: int = 20  # Default: 20 requests per minute
    max_tokens: int = 40  # Maximum token burst capacity
    redis_key_prefix: str = "test_rate_limiter"
    distributed: bool = False  # Whether to use Redis for distributed rate limiting


class LocalRateLimiter:
    """Token bucket rate limiter implementation for local use"""

    def __init__(self, config: RateLimiterConfig):
        self.requests_per_minute = config.requests_per_minute
        self.max_tokens = config.max_tokens
        self.tokens = self.max_tokens  # Start with full bucket
        self.last_refill_time = time.time()
        self.refill_rate = self.requests_per_minute / 60.0  # Tokens per second

    async def acquire(self) -> bool:
        """
        Acquire a token if available, returns True if acquired, False otherwise.
        """
        await self._refill()

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    async def _refill(self):
        """Refill tokens based on elapsed time since last refill"""
        now = time.time()
        elapsed = now - self.last_refill_time

        # Calculate new tokens based on elapsed time
        new_tokens = elapsed * self.refill_rate
        if new_tokens > 0:
            self.tokens = min(self.max_tokens, self.tokens + new_tokens)
            self.last_refill_time = now

    async def reset(self):
        """Reset the rate limiter to initial state"""
        self.tokens = self.max_tokens
        self.last_refill_time = time.time()


# Use a Protocol for compatibility with different Redis clients
class AsyncRedisInterface(Protocol):
    """Protocol for async Redis client functionality we need"""
    async def eval(self, script: str, keys_count: int, *args: Any) -> Any:
        """Evaluate a Lua script"""
        ...

    async def delete(self, *keys: str) -> Any:
        """Delete keys"""
        ...


class RedisRateLimiter:
    """Distributed rate limiter using Redis"""

    def __init__(self, config: RateLimiterConfig, redis_client: Any):
        self.redis = redis_client
        self.requests_per_minute = config.requests_per_minute
        self.max_tokens = config.max_tokens
        self.refill_rate = self.requests_per_minute / 60.0  # Tokens per second
        self.key_prefix = config.redis_key_prefix
        self.tokens_key = f"{self.key_prefix}:tokens"
        self.timestamp_key = f"{self.key_prefix}:timestamp"

    async def acquire(self) -> bool:
        """
        Acquire a token if available, returns True if acquired, False otherwise.
        Uses Redis for distributed rate limiting.
        """
        try:
            # Simplified version that doesn't rely on Redis Lua script
            # This is more compatible with different Redis clients
            # Get current tokens
            tokens_bytes = await self.redis.get(self.tokens_key)
            if tokens_bytes:
                tokens = float(tokens_bytes.decode('utf-8'))
            else:
                tokens = self.max_tokens

            # Get timestamp
            timestamp_bytes = await self.redis.get(self.timestamp_key)
            if timestamp_bytes:
                last_timestamp = float(timestamp_bytes.decode('utf-8'))
            else:
                last_timestamp = 0

            # Calculate new tokens based on elapsed time
            now = time.time()
            elapsed = max(0, now - last_timestamp)
            new_tokens = min(self.max_tokens, tokens + (elapsed * self.refill_rate))

            # Try to acquire token
            if new_tokens >= 1:
                new_tokens -= 1
                acquired = True
            else:
                acquired = False

            # Update Redis
            await self.redis.set(self.tokens_key, str(new_tokens))
            await self.redis.set(self.timestamp_key, str(now))

            return acquired
        except Exception as e:
            logger.warning(f"Redis error in rate limiter: {e}. Falling back to local rate limiting.")
            return True  # Allow the request in case of Redis failure

    async def reset(self):
        """Reset the rate limiter state"""
        try:
            # Use a more compatible approach that works with different Redis clients
            await self.redis.set(self.tokens_key, str(self.max_tokens))
            await self.redis.set(self.timestamp_key, str(time.time()))
        except Exception as e:
            logger.warning(f"Failed to reset rate limiter: {e}")


class RateLimiter:
    """Rate limiter factory that handles both local and distributed implementations"""

    def __init__(self, config: RateLimiterConfig, redis_client: Optional[Any] = None):
        self.config = config

        # Choose implementation based on configuration and available Redis
        if config.distributed and redis_client:
            self.implementation = RedisRateLimiter(config, redis_client)
            logger.info(f"Using distributed rate limiting with {config.requests_per_minute} requests/minute")
        else:
            self.implementation = LocalRateLimiter(config)
            logger.info(f"Using local rate limiting with {config.requests_per_minute} requests/minute")

    async def acquire(self) -> bool:
        """Acquire a token from the rate limiter"""
        return await self.implementation.acquire()

    async def wait(self):
        """Wait until a token becomes available"""
        while not await self.acquire():
            await asyncio.sleep(0.05)  # Small delay to prevent CPU spinning

    async def reset(self):
        """Reset the rate limiter if possible"""
        await self.implementation.reset()


# Async decorator for rate-limited functions
def rate_limited(limiter: Any):
    """
    Decorator that applies rate limiting to an async function.

    Args:
        limiter: The rate limiter instance to use

    Returns:
        Decorated function that applies rate limiting
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs) -> Any:
            if hasattr(limiter, 'wait'):
                await limiter.wait()
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_openai_rate_limiter(
    requests_per_minute: int = 20,
    redis_url: Optional[str] = None
) -> RateLimiter:
    """
    Create and return a configured rate limiter for OpenAI API calls.

    Args:
        requests_per_minute: Maximum requests allowed per minute
        redis_url: Optional Redis URL for distributed rate limiting

    Returns:
        Configured rate limiter instance
    """
    config = RateLimiterConfig(
        requests_per_minute=requests_per_minute,
        redis_key_prefix="openai_test_rate_limiter"
    )

    redis_client = None
    if redis_url:
        try:
            # Rather than importing redis.asyncio, we'll create a helper function to connect
            # when needed. This avoids import errors when Redis isn't available.
            def get_redis_client(url):
                try:
                    # Try to import redis directly first
                    import redis.asyncio
                    return redis.asyncio.from_url(url, decode_responses=True)
                except (ImportError, Exception):
                    try:
                        # Fall back to aioredis if available
                        import aioredis
                        return aioredis.from_url(url, decode_responses=True)
                    except (ImportError, Exception):
                        return None

            redis_client = get_redis_client(redis_url)
            if redis_client:
                config.distributed = True
        except Exception as e:
            logger.warning(f"Failed to initialize Redis for rate limiting: {e}")
            config.distributed = False

    return RateLimiter(
        config=config,
        redis_client=redis_client
    )

# Global instance - uses local rate limiting by default (no Redis)
openai_rate_limiter = get_openai_rate_limiter()
