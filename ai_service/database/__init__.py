"""
Database module for Birth Time Rectifier.
"""

# Import important modules here
import logging
import asyncpg
from typing import Optional

logger = logging.getLogger(__name__)

async def verify_database_schema(db_pool: Optional[asyncpg.Pool] = None):
    """
    Verify required database tables and columns exist before testing.

    Args:
        db_pool: Optional database connection pool. If not provided, will attempt to create one.

    Returns:
        True if verification succeeds

    Raises:
        ValueError if database schema doesn't match requirements
    """
    try:
        # Create a database connection if one wasn't provided
        connection_to_close = False
        if not db_pool:
            from ai_service.core.config import settings
            try:
                db_pool = await asyncpg.create_pool(
                    host=settings.DB_HOST,
                    port=settings.DB_PORT,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    database=settings.DB_NAME
                )
                connection_to_close = True
            except Exception as e:
                logger.error(f"Failed to connect to database for schema verification: {e}")
                raise ValueError(f"Database connection failed: {e}")

        # Check if required tables exist
        required_tables = ["charts", "rectifications", "comparisons", "exports"]
        for table in required_tables:
            if db_pool is not None:
                result = await db_pool.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                    table
                )
                if not result:
                    logger.error(f"Database table '{table}' does not exist")
                    raise ValueError(f"Database table '{table}' does not exist")
            else:
                logger.warning(f"Skipping table check for '{table}' because db_pool is None")

        logger.info("Database schema verification completed successfully")

        # Close the connection if we created it
        if connection_to_close and db_pool is not None:
            await db_pool.close()

        return True
    except Exception as e:
        logger.error(f"Database schema verification failed: {e}")
        if "connection" not in str(e).lower():
            # If it's not a connection error, it's likely a schema issue
            raise ValueError(f"Database schema verification failed: {e}")
        # For connection errors, we will just log and let the application continue
        # This prevents blocking tests when DB isn't available
        logger.warning("Database connection unavailable, tests will use file storage fallback")
        return False
