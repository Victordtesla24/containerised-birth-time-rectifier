"""
Database connection utilities for Birth Time Rectifier.

This module provides connection pooling and management functions for database operations.
"""

import logging
import asyncpg
import os
import asyncio
from typing import Optional, Dict, Any

from ai_service.core.config import settings

logger = logging.getLogger(__name__)

# Global connection pool
_DB_POOL = None

async def acquire_pool() -> asyncpg.Pool:
    """
    Acquire a connection pool (create if it doesn't exist).

    Returns:
        Connection pool instance

    Raises:
        RuntimeError: If pool cannot be created
    """
    global _DB_POOL

    if _DB_POOL is None:
        logger.info("Creating new database connection pool")
        try:
            _DB_POOL = await asyncpg.create_pool(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                min_size=3,
                max_size=10
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise RuntimeError(f"Failed to create database connection pool: {e}")

    if _DB_POOL is None:
        # This should never happen due to the exception above, but to satisfy type checker
        raise RuntimeError("Failed to create database connection pool: Unexpected error")

    return _DB_POOL

async def close_pool() -> None:
    """Close the global connection pool."""
    global _DB_POOL

    if _DB_POOL is not None:
        logger.info("Closing database connection pool")
        await _DB_POOL.close()
        _DB_POOL = None
        logger.info("Database connection pool closed")

async def get_db_pool() -> asyncpg.Pool:
    """
    Get the current database connection pool or create a new one.

    Returns:
        Database connection pool

    Raises:
        RuntimeError: If pool cannot be created or acquired
    """
    global _DB_POOL

    if _DB_POOL is None:
        try:
            return await acquire_pool()
        except Exception as e:
            error_msg = f"Failed to get database pool: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    return _DB_POOL
