"""
Database initialization and utilities for the Birth Time Rectifier API.
"""

import logging
import os
import asyncpg
from typing import Optional

logger = logging.getLogger(__name__)

# Create schema SQL statements
SCHEMA_SQL = {
    "charts": """
    CREATE TABLE IF NOT EXISTS charts (
        chart_id VARCHAR(255) PRIMARY KEY,
        chart_data JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "sessions": """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id VARCHAR(255) PRIMARY KEY,
        data JSONB NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "users": """
    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR(255) PRIMARY KEY,
        username VARCHAR(255) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        preferences JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "user_charts": """
    CREATE TABLE IF NOT EXISTS user_charts (
        user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
        chart_id VARCHAR(255) REFERENCES charts(chart_id) ON DELETE CASCADE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, chart_id)
    );
    """,
    "rectifications": """
    CREATE TABLE IF NOT EXISTS rectifications (
        id SERIAL PRIMARY KEY,
        chart_id VARCHAR(255) REFERENCES charts(chart_id),
        session_id VARCHAR(255) REFERENCES sessions(session_id),
        original_birth_time VARCHAR(50) NOT NULL,
        adjusted_birth_time VARCHAR(50) NOT NULL,
        confidence FLOAT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
}

async def initialize_database_connections() -> Optional[asyncpg.Pool]:
    """
    Initialize database connections and create connection pool.

    Returns:
        Connection pool or None if database is not available
    """
    # Import database connection utilities
    from ai_service.database.connection import get_db_pool
    from ai_service.core.config import settings

    # Skip if explicitly told to skip
    if settings.DB_SKIP_INIT:
        logger.info("Skipping database initialization as per configuration")
        return None

    # Get database connection pool
    try:
        pool = await get_db_pool()
        if pool is not None:
            logger.info("Database connection initialized successfully")
            return pool
        else:
            logger.warning("Database connection pool is None")
            return None
    except Exception as e:
        logger.error(f"Error initializing database connection: {e}")
        # Don't re-raise in development environment to avoid crashing
        env = os.environ.get("ENVIRONMENT", "development").lower()
        if env in ["production"]:
            raise  # Only re-raise in production
        return None

async def verify_database_schema() -> bool:
    """
    Verify and create database schema if it doesn't exist.

    Returns:
        True if schema is verified/created successfully, False otherwise
    """
    # Import database connection utilities
    from ai_service.database.connection import get_db_pool
    from ai_service.core.config import settings

    # Skip if explicitly told to skip
    if settings.DB_SKIP_INIT:
        logger.info("Skipping schema verification as per configuration")
        return False

    # Get database connection pool
    pool = await get_db_pool()
    if pool is None:
        logger.warning("Cannot verify schema without database connection")
        return False

    try:
        # Using assert to confirm pool is not None for the type checker
        assert pool is not None

        # Check and create tables
        async with pool.acquire() as conn:
            # Create schemas in correct order (tables with foreign keys last)
            table_order = ["charts", "sessions", "users", "user_charts", "rectifications"]

            for table in table_order:
                # Check if table exists first
                exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )

                if not exists:
                    logger.info(f"Creating table {table}")
                    await conn.execute(SCHEMA_SQL[table])
                else:
                    logger.info(f"Table {table} already exists")

            logger.info("Database schema verification completed successfully")
            return True
    except Exception as e:
        logger.error(f"Error verifying/creating database schema: {e}")
        # Don't re-raise in development environment to avoid crashing
        env = os.environ.get("ENVIRONMENT", "development").lower()
        if env in ["production"]:
            raise  # Only re-raise in production
        return False

# Additional database utility functions
async def check_database_connection() -> bool:
    """
    Check if the database connection is active.

    Returns:
        bool: True if connected, False otherwise
    """
    try:
        from ai_service.database.connection import get_db_pool
        pool = await get_db_pool()

        # Check if pool is None before trying to access acquire method
        if pool is None:
            logger.warning("Database connection check failed: Connection pool is None")
            return False

        # Assert to help the type checker
        assert pool is not None

        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False
