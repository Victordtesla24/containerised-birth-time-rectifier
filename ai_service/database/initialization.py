"""
Database initialization module.

This module provides functions for initializing and verifying the application's database schema.
"""

import logging
import asyncpg
from typing import Optional, Dict, Any

from ai_service.core.config import settings
from ai_service.database.connection import acquire_pool

logger = logging.getLogger(__name__)

async def initialize_database(db_pool: Optional[asyncpg.Pool] = None) -> bool:
    """
    Initialize the database schema.

    This function creates the necessary tables if they don't exist.

    Args:
        db_pool: Optional database connection pool

    Returns:
        True if initialization succeeds

    Raises:
        RuntimeError: If database initialization fails
    """
    connection_to_close = False

    try:
        # Get database pool if not provided
        if not db_pool:
            connection_to_close = True
            db_pool = await acquire_pool()

        # Ensure we have a valid connection
        if not db_pool:
            raise RuntimeError("Failed to acquire database connection pool")

        # Create charts table
        await db_pool.execute('''
            CREATE TABLE IF NOT EXISTS charts (
                chart_id TEXT PRIMARY KEY,
                birth_date TEXT NOT NULL,
                birth_time TEXT NOT NULL,
                latitude DECIMAL NOT NULL,
                longitude DECIMAL NOT NULL,
                timezone TEXT NOT NULL,
                chart_data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')

        # Create rectifications table
        await db_pool.execute('''
            CREATE TABLE IF NOT EXISTS rectifications (
                rectification_id TEXT PRIMARY KEY,
                chart_id TEXT REFERENCES charts(chart_id),
                original_birth_time TEXT NOT NULL,
                rectified_birth_time TEXT NOT NULL,
                confidence_score DECIMAL NOT NULL,
                rectification_data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')

        # Create users table (simplified version)
        await db_pool.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')

        logger.info("Database schema initialized successfully")
        return True

    except Exception as e:
        error_msg = f"Database initialization failed: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    finally:
        # Close connection if we opened it here
        if connection_to_close and db_pool is not None:
            await db_pool.close()

async def verify_schema_integrity(db_pool: Optional[asyncpg.Pool] = None) -> bool:
    """
    Verify that the database schema is valid and complete.

    Args:
        db_pool: Optional database connection pool

    Returns:
        True if schema is valid

    Raises:
        RuntimeError: If schema verification fails
    """
    connection_to_close = False

    try:
        # Get database pool if not provided
        if not db_pool:
            connection_to_close = True
            db_pool = await acquire_pool()

        # Ensure we have a valid connection
        if not db_pool:
            raise RuntimeError("Failed to acquire database connection pool")

        # Check if required tables exist
        required_tables = ["charts", "rectifications", "users"]
        for table in required_tables:
            result = await db_pool.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                table
            )
            if not result:
                raise RuntimeError(f"Required table '{table}' does not exist")

        # Verify charts table columns
        charts_columns = await db_pool.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'charts'"
        )
        charts_column_names = [row['column_name'] for row in charts_columns]
        required_charts_columns = ["chart_id", "birth_date", "birth_time", "latitude", "longitude", "timezone", "chart_data"]

        for column in required_charts_columns:
            if column not in charts_column_names:
                raise RuntimeError(f"Required column '{column}' missing from charts table")

        logger.info("Database schema verification successful")
        return True

    except Exception as e:
        error_msg = f"Schema verification failed: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    finally:
        # Close connection if we opened it here
        if connection_to_close and db_pool is not None:
            await db_pool.close()
