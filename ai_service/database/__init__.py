"""
Database module for Birth Time Rectifier.

This module provides database functions and connections for the application.
"""

import os
import logging
from typing import Dict, Any, Optional

# Import functions from submodules
from ai_service.database.initialization import initialize_database as initialize_database_internal
from ai_service.database.initialization import verify_schema_integrity

# Setup logging
logger = logging.getLogger(__name__)

# Re-export the initialize_database function with the expected name
async def initialize_database_connections() -> bool:
    """
    Initialize database connections for the application.

    This is a production-ready implementation that sets up all necessary
    database connections for the application.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Initializing database connections")

        # Get database configuration from environment variables
        db_host = os.environ.get("DB_HOST", "postgres")
        db_port = os.environ.get("DB_PORT", "5432")
        db_user = os.environ.get("DB_USER", "postgres")
        db_password = os.environ.get("DB_PASSWORD", "postgres")
        db_name = os.environ.get("DB_NAME", "birth_time_rectifier")

        # Log database connection details (without credentials)
        logger.info(f"Database configuration: {db_host}:{db_port}/{db_name}")

        # Initialize database connection
        from ai_service.database.connection import acquire_pool
        pool = await acquire_pool()
        if pool:
            # Initialize database schema
            success = await initialize_database_internal(pool)
            if success:
                logger.info("Database connections and schema initialized successfully")
                return True
            else:
                logger.error("Failed to initialize database schema")
                return False
        else:
            logger.error("Failed to initialize database connections: pool is None")
            return False
    except Exception as e:
        logger.error(f"Failed to initialize database connections: {str(e)}")
        return False

async def verify_database_schema() -> bool:
    """
    Verify that the database schema exists and is correctly set up.

    Returns:
        bool: True if verification is successful, False otherwise
    """
    try:
        logger.info("Verifying database schema")
        from ai_service.database.connection import acquire_pool
        pool = await acquire_pool()

        if pool:
            success = await verify_schema_integrity(pool)
            if success:
                logger.info("Database schema verification completed successfully")
                return True
            else:
                logger.error("Database schema verification failed")
                return False
        else:
            logger.error("Failed to acquire database pool for schema verification")
            return False
    except Exception as e:
        logger.error(f"Database schema verification failed: {str(e)}")
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
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False
