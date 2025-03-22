"""
Database initialization utilities for Birth Time Rectifier.

This module handles database schema creation and verification.
"""

import logging
import asyncpg
from typing import Optional, Dict, Any

from ai_service.core.config import settings

logger = logging.getLogger(__name__)

async def initialize_database(db_pool: Optional[asyncpg.Pool] = None) -> bool:
    """
    Initialize the database schema if it doesn't exist.

    Args:
        db_pool: Optional database connection pool

    Returns:
        True if initialization was successful
    """
    try:
        # Create connection if not provided
        connection_to_close = False
        if not db_pool:
            from ai_service.database.connection import acquire_pool
            try:
                db_pool = await acquire_pool()
                connection_to_close = True
            except Exception as e:
                logger.error(f"Failed to connect to database for initialization: {e}")
                return False

        if not db_pool:
            logger.error("No database pool available for initialization")
            return False

        # Create tables if they don't exist
        await db_pool.execute('''
            CREATE TABLE IF NOT EXISTS charts (
                id TEXT PRIMARY KEY,
                data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')

        await db_pool.execute('''
            CREATE TABLE IF NOT EXISTS rectifications (
                id TEXT PRIMARY KEY,
                chart_id TEXT REFERENCES charts(id),
                original_chart_id TEXT REFERENCES charts(id),
                data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')

        await db_pool.execute('''
            CREATE TABLE IF NOT EXISTS comparisons (
                id TEXT PRIMARY KEY,
                chart1_id TEXT REFERENCES charts(id),
                chart2_id TEXT REFERENCES charts(id),
                data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        ''')

        await db_pool.execute('''
            CREATE TABLE IF NOT EXISTS exports (
                id TEXT PRIMARY KEY,
                chart_id TEXT REFERENCES charts(id),
                data JSONB NOT NULL,
                file_path TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE
            )
        ''')

        logger.info("Database schema initialized successfully")

        # Close the connection if we created it
        if connection_to_close and db_pool is not None:
            await db_pool.close()

        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

async def verify_schema_integrity(db_pool: Optional[asyncpg.Pool] = None) -> bool:
    """
    Verify that the database schema is valid and complete.

    Args:
        db_pool: Optional database connection pool

    Returns:
        True if schema is valid
    """
    try:
        # Create connection if not provided
        connection_to_close = False
        if not db_pool:
            from ai_service.database.connection import acquire_pool
            try:
                db_pool = await acquire_pool()
                connection_to_close = True
            except Exception as e:
                logger.error(f"Failed to connect to database for schema verification: {e}")
                return False

        if not db_pool:
            logger.error("No database pool available for schema verification")
            return False

        # Check if required tables exist
        required_tables = ["charts", "rectifications", "comparisons", "exports"]
        for table in required_tables:
            result = await db_pool.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                table
            )
            if not result:
                logger.error(f"Required table '{table}' does not exist")
                return False

        # Verify charts table columns
        charts_columns = await db_pool.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'charts'"
        )
        charts_column_names = [row['column_name'] for row in charts_columns]
        required_charts_columns = ["id", "data", "created_at", "updated_at"]
        for column in required_charts_columns:
            if column not in charts_column_names:
                logger.error(f"Required column '{column}' missing from charts table")
                return False

        logger.info("Database schema verification successful")

        # Close the connection if we created it
        if connection_to_close and db_pool is not None:
            await db_pool.close()

        return True
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        return False
