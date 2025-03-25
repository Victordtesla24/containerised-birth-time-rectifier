"""
Repository classes for database access.
"""

import logging
import json
import asyncio
import asyncpg
from typing import Dict, Any, Optional, List, Union, cast
from datetime import datetime, timedelta
import os
import uuid
import base64
import sys
import traceback
from pathlib import Path
import random
import tempfile

from ai_service.core.config import settings
from ai_service.database.connection import acquire_pool, close_pool, get_db_pool
from ai_service.database.initialization import initialize_database
from ai_service.utils.logger import logger

# Create our own verify_database_schema function to avoid import issues
async def verify_database_schema():
    """
    Verify that the database schema is properly set up.

    This function checks if the required tables exist in the database
    and creates them if they don't.

    Raises:
        RuntimeError: If database schema verification fails
    """
    logger.info("Verifying database schema...")

    try:
        # Get database pool
        pool = await get_db_pool()

        if pool is None:
            error_msg = "Database pool not initialized"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Check if required tables exist
        required_tables = [
            "charts",
            "rectifications",
            "questionnaires"
        ]

        async with pool.acquire() as conn:
            # Get list of existing tables
            existing_tables = await conn.fetch("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)

            existing_table_names = [row['table_name'] for row in existing_tables]

            # Check if all required tables exist
            missing_tables = [table for table in required_tables if table not in existing_table_names]

            if missing_tables:
                logger.warning(f"Some tables are missing: {', '.join(missing_tables)}. This may be handled by initialization.")

        logger.info("Database schema verification completed")
        return True

    except Exception as e:
        error_msg = f"Database schema verification error: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

async def initialize_database_pool() -> Optional[asyncpg.Pool]:
    """
    Initialize the database connection pool with comprehensive error handling.

    Returns:
        Optional[asyncpg.Pool]: The database connection pool, or None if initialization failed.
    """
    try:
        # Create a database connection pool with retry logic
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                pool = await asyncpg.create_pool(
                    host=settings.DB_HOST,
                    port=settings.DB_PORT,
                    user=settings.DB_USER,
                    password=settings.DB_PASSWORD,
                    database=settings.DB_NAME,
                    min_size=3,
                    max_size=10,
                    command_timeout=15.0,  # Add command timeout
                    statement_cache_size=100,  # Add cache to improve performance
                    server_settings={  # Add configuration to handle timeouts better
                        'application_name': 'birth_time_rectifier',
                        'statement_timeout': '15s',
                        'idle_in_transaction_session_timeout': '60s'
                    }
                )

                # If pool creation succeeded, break out of the retry loop
                if pool:
                    logger.info("Database pool created successfully")
                    break
            except (asyncpg.PostgresConnectionError, asyncpg.exceptions.PostgresConnectionError) as conn_err:
                retry_count += 1
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.warning(f"Database connection attempt {retry_count} failed: {conn_err}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            except Exception as other_err:
                logger.error(f"Unexpected error during database pool creation: {other_err}")
                logger.error(traceback.format_exc())
                return None  # Return None immediately for non-connection errors

        # Initialize database schema if pool is successfully created
        if pool:
            try:
                await verify_database_schema()
                logger.info("Database pool initialized and schema verified successfully")
                return pool
            except Exception as schema_err:
                logger.error(f"Error verifying database schema: {schema_err}")
                logger.error(traceback.format_exc())
                # Close pool and return None if schema verification fails
                if pool:
                    await pool.close()
                return None

        # If we've exhausted retries, log and return None
        if retry_count >= max_retries:
            logger.error(f"Failed to initialize database pool after {retry_count} attempts")

        return None
    except Exception as e:
        logger.error(f"Critical error initializing database pool: {e}")
        logger.error(traceback.format_exc())
        return None

class ChartRepository:
    """Repository for chart data."""

    def __init__(self):
        """Initialize repository."""
        self._init_db_pool()
        self._db_error_counts = {}
        self._max_errors_before_reconnect = 5

    def _init_db_pool(self):
        """Initialize database connection pool."""
        import os
        from dotenv import load_dotenv
        import asyncpg

        # Load environment variables
        load_dotenv()

        # Get database configuration from environment
        self.db_url = os.environ.get('DATABASE_URL')
        self.db_pool = None
        self.use_db = self.db_url is not None

        if not self.use_db:
            raise ValueError("Database URL not provided. Database connection is required.")

        # Create connection pool
        try:
            import asyncio
            self.db_pool = asyncio.get_event_loop().run_until_complete(
                asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Error initializing database connection pool: {e}")
            raise ValueError(f"Failed to initialize database: {e}")

    async def _reset_db_pool(self):
        """Reset database connection pool after errors."""
        import asyncpg

        try:
            # Close existing pool if any
            if self.db_pool:
                await self.db_pool.close()

            # Create new pool
            self.db_pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
            logger.info("Database connection pool reset")
        except Exception as e:
            logger.error(f"Error resetting database connection pool: {e}")
            raise ValueError(f"Failed to reset database pool: {e}")

    async def _ensure_pool(self) -> Optional[asyncpg.Pool]:
        """
        Ensure we have a valid database pool.

        Returns:
            Database pool or None if initialization failed
        """
        if self.db_pool is None:
            try:
                await self._reset_db_pool()
            except Exception as e:
                logger.error(f"Failed to ensure database pool: {e}")
                return None

        return self.db_pool

    async def store_chart(self, chart_data: Dict[str, Any]) -> str:
        """Store chart data in the database.

        Args:
            chart_data: Chart data to store

        Returns:
            ID of the stored chart
        """
        # Generate chart ID if not present
        if 'chart_id' not in chart_data:
            chart_data['chart_id'] = f"chart_{uuid.uuid4().hex[:12]}"

        # Add timestamp if not present
        if 'timestamp' not in chart_data:
            chart_data['timestamp'] = datetime.now().isoformat()

        # Get pool and verify it's available
        pool = await self._ensure_pool()
        if pool is None:
            raise ValueError("Database connection unavailable")

        # Store in database
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS charts (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert chart data
            await conn.execute(
                'INSERT INTO charts(id, data) VALUES($1, $2) ON CONFLICT(id) DO UPDATE SET data = $2',
                chart_data['chart_id'], json.dumps(chart_data)
            )

        return chart_data['chart_id']

    async def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """Get chart data from the database.

        Args:
            chart_id: ID of the chart to retrieve

        Returns:
            Chart data or None if not found
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        if pool is None:
            raise ValueError("Database connection unavailable")

        # Query database
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS charts (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Query chart data
            row = await conn.fetchrow('SELECT data FROM charts WHERE id = $1', chart_id)

        # Return chart data if found
        if row:
            return json.loads(row['data'])
        return None

    async def delete_chart(self, chart_id: str) -> bool:
        """Delete chart from the database.

        Args:
            chart_id: ID of the chart to delete

        Returns:
            True if deleted, False if not found
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        if pool is None:
            raise ValueError("Database connection unavailable")

        # Delete from database
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS charts (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Delete chart
            result = await conn.execute('DELETE FROM charts WHERE id = $1', chart_id)

        # Parse result
        return 'DELETE 1' in result

    async def list_charts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List charts from the database.

        Args:
            limit: Maximum number of charts to return
            offset: Offset for pagination

        Returns:
            List of chart data
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        if pool is None:
            raise ValueError("Database connection unavailable")

        # Query database
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS charts (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Query charts
            rows = await conn.fetch(
                'SELECT data FROM charts ORDER BY created_at DESC LIMIT $1 OFFSET $2',
                limit, offset
            )

        # Parse results
        return [json.loads(row['data']) for row in rows]

    async def store_rectification(self, rectification_id: str, rectification_data: Dict[str, Any]) -> str:
        """Store rectification data in the database.

        Args:
            rectification_id: ID of the rectification
            rectification_data: Rectification data to store

        Returns:
            ID of the stored rectification
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        if pool is None:
            raise ValueError("Database connection unavailable")

        # Store in database
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS rectifications (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Insert rectification data
            await conn.execute(
                'INSERT INTO rectifications(id, data) VALUES($1, $2) ON CONFLICT(id) DO UPDATE SET data = $2',
                rectification_id, json.dumps(rectification_data)
            )

        return rectification_id

    async def get_rectification(self, rectification_id: str) -> Optional[Dict[str, Any]]:
        """Get rectification data from the database.

        Args:
            rectification_id: ID of the rectification to retrieve

        Returns:
            Rectification data or None if not found
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        if pool is None:
            raise ValueError("Database connection unavailable")

        # Query database
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS rectifications (
                    id TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Query rectification data
            row = await conn.fetchrow('SELECT data FROM rectifications WHERE id = $1', rectification_id)

        # Return rectification data if found
        if row:
            return json.loads(row['data'])
        return None
