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
from ai_service.utils.json_encoder import DateTimeEncoder

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

        if not self.db_url:
            logger.error("Database URL not provided. Database operations will fail.")
            return

        # Create connection pool
        try:
            import asyncio
            self.db_pool = asyncio.get_event_loop().run_until_complete(
                asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Error initializing database connection pool: {e}")
            # Do not create in-memory fallback, let operations fail to surface the issue

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
            raise RuntimeError(f"Failed to reset database pool: {e}")

    async def _ensure_pool(self):
        """
        Ensure we have a valid database pool.

        Returns:
            Database pool or raises exception if initialization failed

        Raises:
            RuntimeError: If database pool cannot be initialized
        """
        if self.db_pool is None:
            if not self.db_url:
                raise RuntimeError("Database URL not provided. Configure DATABASE_URL in environment variables.")

            try:
                await self._reset_db_pool()
            except Exception as e:
                logger.error(f"Failed to ensure database pool: {e}")
                raise RuntimeError(f"Database connection failed: {e}")

        # At this point, self.db_pool should not be None
        if self.db_pool is None:
            raise RuntimeError("Database pool initialization failed")

        return self.db_pool

    async def store_chart(self, chart_data: Dict[str, Any]) -> str:
        """Store chart data in the database.

        Args:
            chart_data: Chart data to store

        Returns:
            ID of the stored chart

        Raises:
            RuntimeError: If database operations fail
        """
        # Generate chart ID if not present
        if 'chart_id' not in chart_data:
            chart_data['chart_id'] = f"chart_{uuid.uuid4().hex[:12]}"

        # Add timestamp if not present
        if 'timestamp' not in chart_data:
            chart_data['timestamp'] = datetime.now().isoformat()

        # Get pool and verify it's available
        pool = await self._ensure_pool()
        # pool cannot be None now due to _ensure_pool

        # Store in database
        try:
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
                    chart_data['chart_id'], json.dumps(chart_data, cls=DateTimeEncoder)
                )

                logger.info(f"Chart {chart_data['chart_id']} stored in database")
                return chart_data['chart_id']
        except Exception as e:
            logger.error(f"Error storing chart data: {e}")
            raise RuntimeError(f"Failed to store chart data: {e}")

    async def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """Get chart data from the database.

        Args:
            chart_id: ID of the chart to retrieve

        Returns:
            Chart data or None if not found

        Raises:
            RuntimeError: If database operations fail
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        # pool cannot be None now due to _ensure_pool

        # Query database
        try:
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
                logger.info(f"Chart {chart_id} not found in database")
                return None
        except Exception as e:
            logger.error(f"Error fetching chart data: {e}")
            raise RuntimeError(f"Failed to fetch chart data: {e}")

    async def delete_chart(self, chart_id: str) -> bool:
        """Delete chart from the database.

        Args:
            chart_id: ID of the chart to delete

        Returns:
            True if deleted, False if not found

        Raises:
            RuntimeError: If database operations fail
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        # pool cannot be None now due to _ensure_pool

        # Delete from database
        try:
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
                success = 'DELETE 1' in result
                if success:
                    logger.info(f"Chart {chart_id} deleted from database")
                else:
                    logger.info(f"Chart {chart_id} not found for deletion")
                return success
        except Exception as e:
            logger.error(f"Error deleting chart data: {e}")
            raise RuntimeError(f"Failed to delete chart data: {e}")

    async def list_charts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List charts from the database.

        Args:
            limit: Maximum number of charts to return
            offset: Offset for pagination

        Returns:
            List of chart data

        Raises:
            RuntimeError: If database operations fail
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        # pool cannot be None now due to _ensure_pool

        # Query database
        try:
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
                charts = [json.loads(row['data']) for row in rows]
                logger.info(f"Retrieved {len(charts)} charts from database")
                return charts
        except Exception as e:
            logger.error(f"Error listing chart data: {e}")
            raise RuntimeError(f"Failed to list chart data: {e}")

    async def store_rectification(self, rectification_id: str, rectification_data: Dict[str, Any]) -> str:
        """Store rectification data in the database.

        Args:
            rectification_id: Unique identifier for the rectification
            rectification_data: Rectification data to store

        Returns:
            ID of the stored rectification

        Raises:
            RuntimeError: If database operations fail
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        # pool cannot be None now due to _ensure_pool

        # Store in database
        try:
            async with pool.acquire() as conn:
                # Create rectifications table if not exists
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
                    rectification_id, json.dumps(rectification_data, cls=DateTimeEncoder)
                )

                logger.info(f"Rectification {rectification_id} stored in database")
                return rectification_id
        except Exception as e:
            logger.error(f"Error storing rectification data: {e}")
            raise RuntimeError(f"Failed to store rectification data: {e}")

    async def get_rectification(self, rectification_id: str) -> Optional[Dict[str, Any]]:
        """Get rectification data from the database.

        Args:
            rectification_id: ID of the rectification to retrieve

        Returns:
            Rectification data or None if not found

        Raises:
            RuntimeError: If database operations fail
        """
        # Get pool and verify it's available
        pool = await self._ensure_pool()
        # pool cannot be None now due to _ensure_pool

        # Query database
        try:
            async with pool.acquire() as conn:
                # Create rectifications table if not exists
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

                logger.info(f"Rectification {rectification_id} not found in database")
                return None
        except Exception as e:
            logger.error(f"Error fetching rectification data: {e}")
            raise RuntimeError(f"Failed to fetch rectification data: {e}")

class UserRepository:
    """Repository for user data."""

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
            logger.warning("Database URL not provided. Using in-memory storage as fallback.")
            # Configure in-memory storage
            self.in_memory_storage = {}
            return

        # Create connection pool
        try:
            import asyncio
            self.db_pool = asyncio.get_event_loop().run_until_complete(
                asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
            )
            logger.info("Database connection pool initialized for UserRepository")
        except Exception as e:
            logger.error(f"Error initializing database connection pool for UserRepository: {e}")
            logger.warning("Falling back to in-memory storage.")
            self.in_memory_storage = {}

    async def _reset_db_pool(self):
        """Reset database connection pool after errors."""
        import asyncpg

        try:
            # Close existing pool if any
            if self.db_pool:
                await self.db_pool.close()

            # Create new pool
            self.db_pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
            logger.info("Database connection pool reset for UserRepository")
        except Exception as e:
            logger.error(f"Error resetting database connection pool for UserRepository: {e}")
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
                logger.error(f"Failed to ensure database pool for UserRepository: {e}")
                return None

        return self.db_pool

    def store_user(self, user: Dict[str, Any]) -> bool:
        """
        Store user data in the database.

        Args:
            user: User data to store

        Returns:
            True if successful, False otherwise
        """
        # If using in-memory storage
        if not self.use_db or self.db_pool is None:
            try:
                # Store in memory
                if not hasattr(self, 'user_storage'):
                    self.user_storage = {}
                if not hasattr(self, 'user_charts'):
                    self.user_charts = {}

                user_copy = user.copy()
                # Convert datetime objects to strings if needed
                if isinstance(user_copy.get('created_at'), datetime):
                    user_copy['created_at'] = user_copy['created_at'].isoformat()
                if isinstance(user_copy.get('updated_at'), datetime):
                    user_copy['updated_at'] = user_copy['updated_at'].isoformat()

                # Store in memory
                self.user_storage[user_copy['id']] = user_copy
                # Also index by email for email lookups
                self.user_storage[f"email:{user_copy['email']}"] = user_copy['id']

                logger.debug(f"Stored user {user_copy['id']} in memory")
                return True
            except Exception as e:
                logger.error(f"Error storing user in memory: {e}")
                return False

        # Get pool and verify it's available
        try:
            pool = asyncio.get_event_loop().run_until_complete(self._ensure_pool())
            if pool is None:
                logger.error("Database connection unavailable for UserRepository.store_user")
                # Fallback to in-memory storage
                return self.store_user(user)  # Recursive call will handle in-memory storage
        except Exception as e:
            logger.error(f"Error ensuring database pool for UserRepository.store_user: {e}")
            # Fallback to in-memory storage
            return self.store_user(user)  # Recursive call will handle in-memory storage

        try:
            # Convert datetime objects to strings
            user_copy = user.copy()
            if isinstance(user_copy.get('created_at'), datetime):
                user_copy['created_at'] = user_copy['created_at'].isoformat()
            if isinstance(user_copy.get('updated_at'), datetime):
                user_copy['updated_at'] = user_copy['updated_at'].isoformat()

            # Store in database
            asyncio.get_event_loop().run_until_complete(self._store_user_async(pool, user_copy))
            return True
        except Exception as e:
            logger.error(f"Error storing user in database: {e}")
            return False

    async def _store_user_async(self, pool, user_data):
        """Async implementation of store_user."""
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    preferences JSONB NOT NULL DEFAULT '{}'::jsonb
                )
            ''')

            # Create user_charts table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_charts (
                    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    chart_id TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, chart_id)
                )
            ''')

            # Insert user data
            await conn.execute(
                '''
                INSERT INTO users(id, email, full_name, hashed_password, created_at, updated_at, preferences)
                VALUES($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT(id) DO UPDATE SET
                    email = $2,
                    full_name = $3,
                    hashed_password = $4,
                    updated_at = $6,
                    preferences = $7
                ''',
                user_data['id'],
                user_data['email'],
                user_data['full_name'],
                user_data['hashed_password'],
                user_data['created_at'],
                user_data['updated_at'],
                json.dumps(user_data['preferences'])
            )

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user data from the database.

        Args:
            user_id: User ID to retrieve

        Returns:
            User data or None if not found
        """
        # If using in-memory storage
        if not self.use_db or self.db_pool is None:
            if not hasattr(self, 'user_storage'):
                self.user_storage = {}
            return self.user_storage.get(user_id)

        # Get pool and verify it's available
        try:
            pool = asyncio.get_event_loop().run_until_complete(self._ensure_pool())
            if pool is None:
                logger.error("Database connection unavailable for UserRepository.get_user")
                # Fallback to in-memory storage
                return self.get_user(user_id)  # Recursive call will use in-memory storage
        except Exception as e:
            logger.error(f"Error ensuring database pool for UserRepository.get_user: {e}")
            # Fallback to in-memory storage
            return self.get_user(user_id)  # Recursive call will use in-memory storage

        try:
            # Get from database
            user_data = asyncio.get_event_loop().run_until_complete(self._get_user_async(pool, user_id))
            return user_data
        except Exception as e:
            logger.error(f"Error getting user from database: {e}")
            return None

    async def _get_user_async(self, pool, user_id):
        """Async implementation of get_user."""
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    preferences JSONB NOT NULL DEFAULT '{}'::jsonb
                )
            ''')

            # Query user data
            row = await conn.fetchrow(
                '''
                SELECT id, email, full_name, hashed_password, created_at, updated_at, preferences
                FROM users WHERE id = $1
                ''',
                user_id
            )

        # Return user data if found
        if row:
            return {
                'id': row['id'],
                'email': row['email'],
                'full_name': row['full_name'],
                'hashed_password': row['hashed_password'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'preferences': json.loads(row['preferences'])
            }
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user data by email from the database.

        Args:
            email: User email to retrieve

        Returns:
            User data or None if not found
        """
        # If using in-memory storage
        if not self.use_db or self.db_pool is None:
            if not hasattr(self, 'user_storage'):
                self.user_storage = {}
            # Get user ID from email index
            user_id = self.user_storage.get(f"email:{email}")
            if user_id:
                # Get user data from ID
                return self.user_storage.get(user_id)
            return None

        # Get pool and verify it's available
        try:
            pool = asyncio.get_event_loop().run_until_complete(self._ensure_pool())
            if pool is None:
                logger.error("Database connection unavailable for UserRepository.get_user_by_email")
                # Fallback to in-memory storage
                return self.get_user_by_email(email)  # Recursive call will use in-memory storage
        except Exception as e:
            logger.error(f"Error ensuring database pool for UserRepository.get_user_by_email: {e}")
            # Fallback to in-memory storage
            return self.get_user_by_email(email)  # Recursive call will use in-memory storage

        try:
            # Get from database
            user_data = asyncio.get_event_loop().run_until_complete(self._get_user_by_email_async(pool, email))
            return user_data
        except Exception as e:
            logger.error(f"Error getting user by email from database: {e}")
            return None

    async def _get_user_by_email_async(self, pool, email):
        """Async implementation of get_user_by_email."""
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    preferences JSONB NOT NULL DEFAULT '{}'::jsonb
                )
            ''')

            # Query user data
            row = await conn.fetchrow(
                '''
                SELECT id, email, full_name, hashed_password, created_at, updated_at, preferences
                FROM users WHERE email = $1
                ''',
                email
            )

        # Return user data if found
        if row:
            return {
                'id': row['id'],
                'email': row['email'],
                'full_name': row['full_name'],
                'hashed_password': row['hashed_password'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'preferences': json.loads(row['preferences'])
            }
        return None

    def user_exists(self, user_id: str) -> bool:
        """
        Check if a user exists by ID.

        Args:
            user_id: User ID

        Returns:
            True if exists, False otherwise
        """
        # Get pool and verify it's available
        pool = asyncio.get_event_loop().run_until_complete(self._ensure_pool())
        if pool is None:
            logger.error("Database connection unavailable for UserRepository.user_exists")
            return False

        try:
            # Query database
            return asyncio.get_event_loop().run_until_complete(self._user_exists_async(pool, user_id))
        except Exception as e:
            logger.error(f"Error checking user existence in database: {e}")
            return False

    async def _user_exists_async(self, pool, user_id):
        """Async implementation of user_exists."""
        async with pool.acquire() as conn:
            # Query user data
            row = await conn.fetchrow('SELECT 1 FROM users WHERE id = $1', user_id)
        return row is not None

    def user_exists_by_email(self, email: str) -> bool:
        """
        Check if a user exists by email.

        Args:
            email: User email

        Returns:
            True if exists, False otherwise
        """
        # Get pool and verify it's available
        pool = asyncio.get_event_loop().run_until_complete(self._ensure_pool())
        if pool is None:
            logger.error("Database connection unavailable for UserRepository.user_exists_by_email")
            return False

        try:
            # Query database
            return asyncio.get_event_loop().run_until_complete(self._user_exists_by_email_async(pool, email))
        except Exception as e:
            logger.error(f"Error checking user existence by email in database: {e}")
            return False

    async def _user_exists_by_email_async(self, pool, email):
        """Async implementation of user_exists_by_email."""
        async with pool.acquire() as conn:
            # Query user data
            row = await conn.fetchrow('SELECT 1 FROM users WHERE email = $1', email)
        return row is not None

    def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Update user preferences.

        Args:
            user_id: User ID
            preferences: New preferences

        Returns:
            True if successful, False otherwise
        """
        # Get pool and verify it's available
        pool = asyncio.get_event_loop().run_until_complete(self._ensure_pool())
        if pool is None:
            logger.error("Database connection unavailable for UserRepository.update_preferences")
            return False

        try:
            # Update database
            success = asyncio.get_event_loop().run_until_complete(self._update_preferences_async(pool, user_id, preferences))
            return success
        except Exception as e:
            logger.error(f"Error updating user preferences in database: {e}")
            return False

    async def _update_preferences_async(self, pool, user_id, preferences):
        """Async implementation of update_preferences."""
        async with pool.acquire() as conn:
            # Get current user
            user = await conn.fetchrow(
                '''
                SELECT preferences FROM users WHERE id = $1
                ''',
                user_id
            )

            if not user:
                return False

            # Update preferences
            current_prefs = json.loads(user['preferences'])
            current_prefs.update(preferences)

            # Update in database
            await conn.execute(
                '''
                UPDATE users SET preferences = $1, updated_at = $2 WHERE id = $3
                ''',
                json.dumps(current_prefs),
                datetime.now(),
                user_id
            )

        return True

    def get_user_charts(self, user_id: str) -> List[str]:
        """
        Get charts associated with a user.

        Args:
            user_id: User ID

        Returns:
            List of chart IDs
        """
        # Get pool and verify it's available
        pool = asyncio.get_event_loop().run_until_complete(self._ensure_pool())
        if pool is None:
            logger.error("Database connection unavailable for UserRepository.get_user_charts")
            return []

        try:
            # Query database
            return asyncio.get_event_loop().run_until_complete(self._get_user_charts_async(pool, user_id))
        except Exception as e:
            logger.error(f"Error getting user charts from database: {e}")
            return []

    async def _get_user_charts_async(self, pool, user_id):
        """Async implementation of get_user_charts."""
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_charts (
                    user_id TEXT NOT NULL,
                    chart_id TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, chart_id)
                )
            ''')

            # Query charts
            rows = await conn.fetch(
                '''
                SELECT chart_id FROM user_charts WHERE user_id = $1
                ORDER BY created_at DESC
                ''',
                user_id
            )

        # Return chart IDs
        return [row['chart_id'] for row in rows]

    def add_chart(self, user_id: str, chart_id: str) -> bool:
        """
        Associate a chart with a user.

        Args:
            user_id: User ID
            chart_id: Chart ID

        Returns:
            True if successful, False otherwise
        """
        # Get pool and verify it's available
        pool = asyncio.get_event_loop().run_until_complete(self._ensure_pool())
        if pool is None:
            logger.error("Database connection unavailable for UserRepository.add_chart")
            return False

        try:
            # Update database
            success = asyncio.get_event_loop().run_until_complete(self._add_chart_async(pool, user_id, chart_id))
            return success
        except Exception as e:
            logger.error(f"Error adding chart to user in database: {e}")
            return False

    async def _add_chart_async(self, pool, user_id, chart_id):
        """Async implementation of add_chart."""
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_charts (
                    user_id TEXT NOT NULL,
                    chart_id TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, chart_id)
                )
            ''')

            # Check if user exists
            user_exists = await conn.fetchval('SELECT 1 FROM users WHERE id = $1', user_id)
            if not user_exists:
                return False

            try:
                # Add chart
                await conn.execute(
                    '''
                    INSERT INTO user_charts(user_id, chart_id)
                    VALUES($1, $2)
                    ON CONFLICT(user_id, chart_id) DO NOTHING
                    ''',
                    user_id,
                    chart_id
                )
                return True
            except Exception:
                return False

    def remove_chart(self, user_id: str, chart_id: str) -> bool:
        """
        Remove a chart association from a user.

        Args:
            user_id: User ID
            chart_id: Chart ID

        Returns:
            True if successful, False otherwise
        """
        # Get pool and verify it's available
        pool = asyncio.get_event_loop().run_until_complete(self._ensure_pool())
        if pool is None:
            logger.error("Database connection unavailable for UserRepository.remove_chart")
            return False

        try:
            # Update database
            success = asyncio.get_event_loop().run_until_complete(self._remove_chart_async(pool, user_id, chart_id))
            return success
        except Exception as e:
            logger.error(f"Error removing chart from user in database: {e}")
            return False

    async def _remove_chart_async(self, pool, user_id, chart_id):
        """Async implementation of remove_chart."""
        async with pool.acquire() as conn:
            # Create table if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_charts (
                    user_id TEXT NOT NULL,
                    chart_id TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, chart_id)
                )
            ''')

            # Remove chart
            result = await conn.execute(
                '''
                DELETE FROM user_charts WHERE user_id = $1 AND chart_id = $2
                ''',
                user_id,
                chart_id
            )

        # Check if deleted
        return 'DELETE 1' in result
