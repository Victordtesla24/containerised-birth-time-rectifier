"""
Database connection module.

This module provides utilities for connecting to the database.
"""

import logging
import asyncpg
import traceback
import asyncio
import os
import json
import sqlite3
from typing import Optional, Dict, Any, List, Union

from ai_service.core.config import settings

logger = logging.getLogger(__name__)

# Global connection pool
_pool = None

# SQLite connection info
_sqlite_path = None
_using_sqlite = False

class SQLiteConnectionPool:
    """
    A simple SQLite connection pool that mimics the asyncpg Pool API.
    This allows us to use SQLite for development and testing while maintaining
    API compatibility with PostgreSQL for production.
    """
    def __init__(self, db_path):
        self.db_path = db_path
        logger.info(f"Initialized SQLite connection pool with path: {db_path}")

        # Create tables if they don't exist
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables in SQLite database if they don't exist"""
        required_tables = {
            "charts": """
                CREATE TABLE IF NOT EXISTS charts (
                    chart_id TEXT PRIMARY KEY,
                    birth_date TEXT NOT NULL,
                    birth_time TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    timezone TEXT NOT NULL,
                    chart_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "rectifications": """
                CREATE TABLE IF NOT EXISTS rectifications (
                    rectification_id TEXT PRIMARY KEY,
                    chart_id TEXT REFERENCES charts(chart_id),
                    original_birth_time TEXT NOT NULL,
                    rectified_birth_time TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    rectification_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "sessions": """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            """,
            "questionnaires": """
                CREATE TABLE IF NOT EXISTS questionnaires (
                    questionnaire_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    chart_id TEXT REFERENCES charts(chart_id),
                    questions TEXT NOT NULL,
                    answers TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """
        }

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for table_name, create_sql in required_tables.items():
                cursor.execute(create_sql)

            conn.commit()
            conn.close()
            logger.info("Created SQLite tables successfully")
        except Exception as e:
            logger.error(f"Error creating SQLite tables: {e}")

    def acquire(self):
        """Create and return a SQLiteConnection"""
        # Return a connection directly, not an awaitable
        connection = SQLiteConnection(self.db_path)
        connection._connect()  # Initialize the connection immediately
        return connection

    async def close(self):
        """Mimics asyncpg pool.close()"""
        # No-op for SQLite
        pass


class SQLiteConnection:
    """A connection wrapper that mimics asyncpg Connection API"""
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    def _connect(self):
        """Establish the connection immediately"""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row

    async def __aenter__(self):
        """Initialize connection when entering the context manager"""
        if not self.conn:
            self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close connection when exiting the context manager"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def close(self):
        """Close the connection manually"""
        if self.conn:
            self.conn.close()
            self.conn = None

    async def execute(self, query, *args, **kwargs):
        """Execute a query and return affected row count"""
        try:
            # Convert asyncpg $1, $2 style params to ? style
            query = self._convert_query_params(query)

            # Ensure connection is established
            if not self.conn:
                self._connect()

            # Check again to make sure connection is not None
            if self.conn is None:
                raise RuntimeError("SQLite connection could not be established")

            cursor = self.conn.cursor()
            cursor.execute(query, args)
            self.conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"SQLite execute error: {e}")
            if self.conn:
                self.conn.rollback()
            raise

    async def fetchval(self, query, *args, **kwargs):
        """Fetch a single value from the first row"""
        try:
            query = self._convert_query_params(query)

            # Ensure connection is established
            if not self.conn:
                self._connect()

            # Check again to make sure connection is not None
            if self.conn is None:
                raise RuntimeError("SQLite connection could not be established")

            cursor = self.conn.cursor()
            cursor.execute(query, args)
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"SQLite fetchval error: {e}")
            raise

    async def fetchrow(self, query, *args, **kwargs):
        """Fetch a single row as a dictionary"""
        try:
            query = self._convert_query_params(query)

            # Ensure connection is established
            if not self.conn:
                self._connect()

            # Check again to make sure connection is not None
            if self.conn is None:
                raise RuntimeError("SQLite connection could not be established")

            cursor = self.conn.cursor()
            cursor.execute(query, args)
            row = cursor.fetchone()
            if not row:
                return None

            # Convert to dict to match asyncpg behavior
            result = {}
            for idx, column in enumerate(cursor.description):
                result[column[0]] = row[idx]

            # Handle special case for JSON data
            if 'chart_data' in result and isinstance(result['chart_data'], str):
                try:
                    result['chart_data'] = json.loads(result['chart_data'])
                except json.JSONDecodeError:
                    pass

            return result
        except Exception as e:
            logger.error(f"SQLite fetchrow error: {e}")
            raise

    async def fetch(self, query, *args, **kwargs):
        """Fetch multiple rows as a list of dictionaries"""
        try:
            query = self._convert_query_params(query)

            # Ensure connection is established
            if not self.conn:
                self._connect()

            # Check again to make sure connection is not None
            if self.conn is None:
                raise RuntimeError("SQLite connection could not be established")

            cursor = self.conn.cursor()
            cursor.execute(query, args)
            rows = cursor.fetchall()

            # Convert to dict list to match asyncpg behavior
            result = []
            for row in rows:
                row_dict = {}
                for idx, column in enumerate(cursor.description):
                    row_dict[column[0]] = row[idx]
                result.append(row_dict)

            return result
        except Exception as e:
            logger.error(f"SQLite fetch error: {e}")
            raise

    def _convert_query_params(self, query):
        """Convert PostgreSQL $1, $2 style params to SQLite ? style"""
        # Replace $1, $2, etc. with ?
        for i in range(1, 100):  # Support up to 99 parameters
            query = query.replace(f"${i}", "?")
        return query

async def get_db_pool() -> Optional[Union[asyncpg.Pool, SQLiteConnectionPool]]:
    """
    Get the database connection pool with retries.

    This function creates a database connection pool if one doesn't already exist.
    It implements an exponential backoff retry mechanism for reliable connection.

    Returns:
        asyncpg.Pool or SQLiteConnectionPool: The database connection pool or None if connection failed
    """
    global _pool, _sqlite_path, _using_sqlite

    # Return existing pool if already initialized
    if _pool is not None:
        return _pool

    try:
        # Connection retry settings
        max_retries = 5
        retry_count = 0

        # Check if DATABASE_URL is set and valid
        if not settings.DATABASE_URL:
            # Build connection string from individual parameters
            db_user = settings.DB_USER or os.environ.get("DB_USER", "postgres")
            db_password = settings.DB_PASSWORD or os.environ.get("DB_PASSWORD", "postgres")
            db_host = settings.DB_HOST or os.environ.get("DB_HOST", "localhost")
            db_port = settings.DB_PORT or os.environ.get("DB_PORT", "5432")
            db_name = settings.DB_NAME or os.environ.get("DB_NAME", "birth_time_rectifier")

            connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            connection_string = settings.DATABASE_URL

        # Handle SQLite connection string
        if connection_string and connection_string.startswith('sqlite:///'):
            _using_sqlite = True
            # Extract SQLite database path
            _sqlite_path = connection_string.replace('sqlite:///', '')

            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(_sqlite_path)), exist_ok=True)

            logger.info(f"Using SQLite database at {_sqlite_path}")
            _pool = SQLiteConnectionPool(_sqlite_path)

            # Test connection with SQLite
            try:
                # Get a connection directly without async context manager
                conn = _pool.acquire()
                try:
                    # Execute a simple query
                    await conn.execute("SELECT 1")
                    logger.info("SQLite connection test successful")
                    return _pool
                finally:
                    # Close the connection manually
                    conn.close()
            except Exception as e:
                logger.error(f"SQLite connection test failed: {e}")
                _pool = None
                return None

        elif not connection_string or not connection_string.startswith('postgresql'):
            logger.error("Invalid database connection string. Please check your configuration.")
            return None

        # Try to connect to PostgreSQL multiple times with exponential backoff
        while retry_count < max_retries:
            try:
                # Create connection pool with optimized settings
                _pool = await asyncpg.create_pool(
                    dsn=connection_string,
                    min_size=5,
                    max_size=20,
                    command_timeout=60,
                    ssl=settings.DB_SSL,
                    server_settings={
                        'application_name': 'birth_time_rectifier',
                        'statement_timeout': '60s',
                        'idle_in_transaction_session_timeout': '60s'
                    }
                )

                # Test connection with a simple query
                if _pool:
                    async with _pool.acquire() as conn:
                        version = await conn.fetchval("SELECT version();")
                        logger.info(f"Connected to PostgreSQL: {version}")

                    # Verify database schema
                    await verify_database_schema()

                    logger.info("Database pool created and initialized successfully")
                    return _pool
            except (asyncpg.PostgresConnectionError, asyncpg.exceptions.PostgresConnectionError) as e:
                retry_count += 1
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.warning(f"Database connection attempt {retry_count} failed: {e}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(f"Unexpected error during database pool creation: {e}")
                logger.error(traceback.format_exc())
                return None

        # If we've exhausted retries, log error and return None
        if retry_count >= max_retries:
            logger.error(f"Failed to connect to PostgreSQL database after {max_retries} attempts.")
            logger.error(f"Last connection string tried (sensitive data redacted): postgresql://[user]:[pass]@{db_host}:{db_port}/{db_name}")

        return None
    except Exception as e:
        logger.error(f"Critical error initializing database pool: {e}")
        logger.error(traceback.format_exc())
        return None

async def verify_database_schema() -> bool:
    """
    Verify that the database schema is valid and complete.
    Creates necessary tables if they don't exist.

    Returns:
        bool: True if schema is validated successfully
    """
    global _pool, _using_sqlite

    # SQLite tables are created in the SQLiteConnectionPool constructor
    if _using_sqlite:
        return True

    required_tables = {
        "charts": """
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
        """,
        "rectifications": """
            CREATE TABLE IF NOT EXISTS rectifications (
                rectification_id TEXT PRIMARY KEY,
                chart_id TEXT REFERENCES charts(chart_id),
                original_birth_time TEXT NOT NULL,
                rectified_birth_time TEXT NOT NULL,
                confidence_score DECIMAL NOT NULL,
                rectification_data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """,
        "sessions": """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                data JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """,
        "questionnaires": """
            CREATE TABLE IF NOT EXISTS questionnaires (
                questionnaire_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                chart_id TEXT REFERENCES charts(chart_id),
                questions JSONB NOT NULL,
                answers JSONB NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                completed_at TIMESTAMP WITH TIME ZONE
            )
        """
    }

    if _pool is None:
        logger.error("Cannot verify schema without database connection")
        return False

    try:
        async with _pool.acquire() as conn:
            # Check and create tables in order
            for table_name, create_sql in required_tables.items():
                exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = $1)",
                    table_name
                )

                if not exists:
                    logger.info(f"Creating table {table_name}")
                    await conn.execute(create_sql)
                else:
                    logger.debug(f"Table {table_name} already exists")

            logger.info("Database schema verification successful")
            return True
    except Exception as e:
        logger.error(f"Schema verification failed: {e}")
        logger.error(traceback.format_exc())
        return False

async def close_pool() -> None:
    """
    Close the database connection pool.

    This releases all acquired connections and closes the pool.
    """
    global _pool

    if _pool:
        try:
            await _pool.close()
            logger.info("Database connection pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing database pool: {e}")
            logger.error(traceback.format_exc())

    _pool = None

async def acquire_connection():
    """
    Acquire a database connection from the pool.

    Returns:
        Connection object or None if pool is not available

    Usage:
        async with acquire_connection() as conn:
            # Use connection
    """
    pool = await get_db_pool()
    if pool is None:
        logger.error("Database pool is not available")
        raise RuntimeError("Database connection pool is not available")

    if _using_sqlite:
        # For SQLite, return the connection that works without async context manager
        return pool.acquire()
    else:
        # For PostgreSQL, return the async context manager
        return pool.acquire()

async def execute_query(query: str, *args, **kwargs) -> Any:
    """
    Execute a database query.

    Args:
        query: SQL query to execute
        *args: Query parameters
        **kwargs: Additional options

    Returns:
        Query result

    Raises:
        RuntimeError: If database query fails
    """
    pool = await get_db_pool()
    if pool is None:
        raise RuntimeError("Database connection pool is not available")

    try:
        async with pool.acquire() as conn:
            return await conn.execute(query, *args, **kwargs)
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Database query failed: {e}")

async def fetch_one(query: str, *args, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Fetch a single row from the database.

    Args:
        query: SQL query
        *args: Query parameters
        **kwargs: Additional options

    Returns:
        Row as dictionary or None if not found

    Raises:
        RuntimeError: If database query fails
    """
    pool = await get_db_pool()
    if pool is None:
        raise RuntimeError("Database connection pool is not available")

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *args, **kwargs)
            if row:
                return dict(row)
            return None
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Database query failed: {e}")

async def fetch_all(query: str, *args, **kwargs) -> list:
    """
    Fetch multiple rows from the database.

    Args:
        query: SQL query
        *args: Query parameters
        **kwargs: Additional options

    Returns:
        List of rows as dictionaries

    Raises:
        RuntimeError: If database query fails
    """
    pool = await get_db_pool()
    if pool is None:
        raise RuntimeError("Database connection pool is not available")

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args, **kwargs)
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Database query failed: {e}")

async def fetch_val(query: str, *args, **kwargs) -> Any:
    """
    Fetch a single value from the database.

    Args:
        query: SQL query
        *args: Query parameters
        **kwargs: Additional options

    Returns:
        Single value or None if not found

    Raises:
        RuntimeError: If database query fails
    """
    pool = await get_db_pool()
    if pool is None:
        raise RuntimeError("Database connection pool is not available")

    try:
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args, **kwargs)
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        logger.error(f"Query: {query}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Database query failed: {e}")

async def ping_database() -> bool:
    """
    Check if database connection is working.

    Returns:
        True if database is reachable, False otherwise
    """
    try:
        pool = await get_db_pool()
        if pool is None:
            return False

        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error(f"Database ping failed: {e}")
        return False
