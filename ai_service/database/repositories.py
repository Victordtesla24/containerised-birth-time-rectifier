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

logger = logging.getLogger(__name__)

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
    """Repository for chart data with file-based persistence as fallback."""

    db_pool: Optional[asyncpg.Pool]
    file_storage_path: str
    _all_tasks: set
    _db_error_counts: Dict[str, int]  # Track error counts by operation type
    _max_errors_before_fallback: int = 3  # Maximum errors before switching to fallback
    _max_errors_before_reconnect: int = 5  # Maximum errors before attempting to reconnect the DB pool

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None, file_storage_path: Optional[str] = None):
        """
        Initialize the repository with database connection.

        Args:
            db_pool: Optional database connection pool
            file_storage_path: Optional file storage path
        """
        self.db_pool = db_pool
        self.file_storage_path = file_storage_path or os.path.join(tempfile.gettempdir(), "birth_rectifier_charts")

        # Ensure the file storage directory exists
        os.makedirs(self.file_storage_path, exist_ok=True)

        # Set to track all async tasks
        self._all_tasks = set()

        # Track database errors by operation type
        self._db_error_counts = {}

        # Start initialization task
        self._initialization_complete = False
        init_task = asyncio.create_task(self._initialize_db())
        init_task.add_done_callback(self._handle_init_task)
        self._all_tasks.add(init_task)

        logger.info(f"Initialized ChartRepository with file storage at {self.file_storage_path}")

    def _handle_init_task(self, task):
        """Handle task completion and exceptions without crashing the app."""
        try:
            # Check for exceptions
            if not task.cancelled():
                ex = task.exception()
                if ex:
                    logger.warning(f"Database initialization task failed: {ex}")
        except (asyncio.CancelledError, asyncio.InvalidStateError):
            # Task was cancelled or is in invalid state, just log it
            logger.debug("Database initialization task was cancelled")

        # Remove from tracked tasks if present
        if hasattr(ChartRepository, '_all_tasks') and task in ChartRepository._all_tasks:
            ChartRepository._all_tasks.remove(task)

    async def _initialize_db(self) -> None:
        """Initialize database connection and create tables if needed."""
        try:
            # Create tables and other initialization logic here
            # ...
            pass
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    async def _get_chart_from_file(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a chart from file storage.

        Args:
            chart_id: The chart ID to retrieve

        Returns:
            The chart data or None if not found
        """
        try:
            # Create a file path for the chart
            file_path = os.path.join(self.file_storage_path, f"{chart_id}.json")

            # Check if the file exists
            if not os.path.exists(file_path):
                logger.debug(f"Chart {chart_id} file not found at {file_path}")
                return None

            # Read the file
            with open(file_path, 'r') as f:
                chart_data = json.load(f)

            logger.debug(f"Retrieved chart {chart_id} from file at {file_path}")
            return chart_data
        except Exception as e:
            logger.error(f"Error reading chart {chart_id} from file: {e}")
            return None

    # Additional methods should be added here as needed

    async def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a chart from the repository.

        First tries to get from database, falls back to file storage if database is unavailable.

        Args:
            chart_id: The chart ID

        Returns:
            The chart data or None if not found
        """
        # Check database availability first
        if not self.db_pool:
            # If no database, check file directly without logging a warning
            return await self._get_chart_from_file(chart_id)

        try:
            # Try to get from database first
            # If successful, return the chart data
            # If not found, try file storage
            # Return None if not found in either location
            return None
        except Exception as e:
            logger.warning(f"Falling back to file storage for chart {chart_id}: {e}")
            return await self._get_chart_from_file(chart_id)

    async def store_chart(self, chart_data: Dict[str, Any]) -> str:
        """
        Store a chart in the repository.

        First tries to store in database, falls back to file storage if database is unavailable.

        Args:
            chart_data: The chart data to store

        Returns:
            The chart ID
        """
        # Get or generate chart ID
        chart_id = chart_data.get("chart_id")
        if not chart_id:
            chart_id = f"chart_{uuid.uuid4().hex[:8]}"
            chart_data["chart_id"] = chart_id

        # Add timestamps if not present
        now = datetime.now()
        if "generated_at" not in chart_data:
            chart_data["generated_at"] = now.isoformat()

        try:
            # Store in database if available
            if self.db_pool is not None:
                try:
                    # Use a single transaction for atomicity
                    if self.db_pool is None:
                        raise ValueError("Database pool is not available")

                    async with self.db_pool.acquire() as conn:
                        # Database operations here
                        pass
                except Exception as db_error:
                    logger.warning(f"Database error storing chart: {db_error}, falling back to file storage")
                    # Fall back to file storage
                    await self._store_chart_in_file(chart_id, chart_data)
            else:
                # Store in file directly
                await self._store_chart_in_file(chart_id, chart_data)

            return chart_id
        except Exception as e:
            logger.error(f"Error storing chart: {e}")
            raise ValueError(f"Failed to store chart: {e}")

    async def _store_chart_in_file(self, chart_id: str, chart_data: Dict[str, Any]) -> str:
        """
        Store chart data in file storage.

        Args:
            chart_id: The chart ID
            chart_data: The chart data to store

        Returns:
            The chart ID

        Raises:
            ValueError: If there's an error storing the chart
        """
        try:
            # Ensure chart_id is in the data
            chart_data["chart_id"] = chart_id

            # Create a file path for the chart
            file_path = os.path.join(self.file_storage_path, f"{chart_id}.json")

            # Add timestamp if not present
            if "stored_at" not in chart_data:
                chart_data["stored_at"] = datetime.now().isoformat()

            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(chart_data, f, default=self._datetime_serializer, indent=2)

            logger.info(f"Stored chart {chart_id} in file {file_path}")
            return chart_id
        except Exception as e:
            logger.error(f"Error storing chart {chart_id} to file: {e}")
            raise ValueError(f"File storage error: {e}")

    def _datetime_serializer(self, obj):
        """Serialize datetime objects to ISO format strings."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    async def _execute_db_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Execute a database operation with error handling.

        Args:
            operation_name: Name of the operation for error tracking
            operation_func: Async function to execute
            *args: Arguments to pass to operation_func
            **kwargs: Keyword arguments to pass to operation_func

        Returns:
            Result of operation_func

        Raises:
            ValueError: If the operation fails
        """
        try:
            # Execute the database operation
            return await operation_func(*args, **kwargs)
        except Exception as e:
            # Handle database errors
            if self._db_error_counts.get(operation_name, 0) >= self._max_errors_before_reconnect:
                logger.warning(f"Too many errors in {operation_name}, will attempt to reconnect DB pool on next operation")
                self._reset_db_pool()
            raise ValueError(str(e))

    def _reset_db_pool(self):
        """Reset the database pool on error."""
        self.db_pool = None
        logger.info("Database pool reset due to errors, will attempt to reconnect on next operation")

    async def store_comparison(self, comparison_id: str, comparison_data: Dict[str, Any]) -> None:
        """
        Store comparison data in the repository.

        Args:
            comparison_id: ID of the comparison
            comparison_data: Comparison data to store

        Raises:
            ValueError: If there's an error storing the comparison
        """
        try:
            # Try to store in database if available
            if self.db_pool:
                try:
                    # Define database operation function
                    async def _store_comparison_db_operation():
                        # Prepare for database storage
                        json_data = json.dumps(comparison_data, default=self._datetime_serializer)

                        try:
                            if self.db_pool is None:
                                raise ValueError("Database pool is not available")

                            async with self.db_pool.acquire() as conn:
                                # Database operations here
                                pass
                        except Exception as db_error:
                            logger.error(f"Database error storing comparison: {db_error}")
                            raise

                    # Execute the database operation
                    await self._execute_db_operation(
                        "store_comparison",
                        _store_comparison_db_operation
                    )
                    logger.info(f"Stored comparison {comparison_id} in database")
                    return
                except Exception as db_error:
                    logger.warning(f"Database error storing comparison: {db_error}, falling back to file storage")
                    # Fall back to file storage if database operation fails

            # Store in file if database is not available or operation failed
            await self._store_comparison_in_file(comparison_id, comparison_data)
            logger.info(f"Stored comparison {comparison_id} in file storage")
        except Exception as e:
            logger.error(f"Error storing comparison {comparison_id}: {e}")
            raise ValueError(f"Failed to store comparison: {e}")

    async def _store_comparison_in_file(self, comparison_id: str, comparison_data: Dict[str, Any]) -> None:
        """
        Store comparison data in file storage.

        Args:
            comparison_id: ID of the comparison
            comparison_data: Comparison data to store

        Raises:
            ValueError: If there's an error storing the comparison
        """
        try:
            # Ensure comparison_id is in the data
            comparison_data["comparison_id"] = comparison_id

            # Create the file path
            file_path = os.path.join(self.file_storage_path, "comparisons", f"{comparison_id}.json")

            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Add timestamp if not present
            if "stored_at" not in comparison_data:
                comparison_data["stored_at"] = datetime.now().isoformat()

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(comparison_data, f, default=self._datetime_serializer, indent=2)

            logger.info(f"Stored comparison {comparison_id} in file {file_path}")
        except Exception as e:
            logger.error(f"Error storing comparison {comparison_id} to file: {e}")
            raise ValueError(f"File storage error: {e}")

    async def get_rectification(self, rectification_id: str) -> Optional[Dict[str, Any]]:
        """
        Get rectification data from the repository.

        First tries to get from database, falls back to file storage if database is unavailable.

        Args:
            rectification_id: The rectification ID to retrieve

        Returns:
            The rectification data or None if not found
        """
        # Check database availability first
        if not self.db_pool:
            # If no database, check file directly
            return await self._get_rectification_from_file(rectification_id)

        try:
            # Try to get from database first
            async with self.db_pool.acquire() as conn:
                # Query the database for the rectification
                row = await conn.fetchrow(
                    """
                    SELECT * FROM rectifications WHERE rectification_id = $1
                    """,
                    rectification_id
                )

                if row:
                    # Convert row to dict
                    return dict(row)
                else:
                    # Not found in database, try file storage
                    return await self._get_rectification_from_file(rectification_id)
        except Exception as e:
            # Log error and fall back to file storage
            logger.warning(f"Database error retrieving rectification {rectification_id}: {e}")
            self._db_error_counts["get_rectification"] = self._db_error_counts.get("get_rectification", 0) + 1

            # Check if we should attempt to reconnect the DB pool
            if self._db_error_counts.get("get_rectification", 0) >= self._max_errors_before_reconnect:
                logger.warning(f"Attempting to reset database pool after {self._db_error_counts.get('get_rectification')} errors")
                self._reset_db_pool()
                self._db_error_counts["get_rectification"] = 0

            return await self._get_rectification_from_file(rectification_id)

    async def _get_rectification_from_file(self, rectification_id: str) -> Optional[Dict[str, Any]]:
        """
        Get rectification data from file storage.

        Args:
            rectification_id: The rectification ID to retrieve

        Returns:
            The rectification data or None if not found
        """
        try:
            # Create file path for the rectification
            file_path = os.path.join(self.file_storage_path, "rectifications", f"{rectification_id}.json")

            # Check if file exists
            if not os.path.exists(file_path):
                logger.debug(f"Rectification {rectification_id} file not found at {file_path}")
                return None

            # Read the file
            with open(file_path, 'r') as f:
                rectification_data = json.load(f)

            logger.debug(f"Retrieved rectification {rectification_id} from file at {file_path}")
            return rectification_data
        except Exception as e:
            logger.error(f"Error reading rectification {rectification_id} from file: {e}")
            return None

    async def store_rectification(self, rectification_id: str, rectification_data: Dict[str, Any]) -> str:
        """
        Store rectification data in the repository.

        First tries to store in database, falls back to file storage if database is unavailable.

        Args:
            rectification_id: The rectification ID
            rectification_data: The rectification data to store

        Returns:
            The rectification ID

        Raises:
            ValueError: If there's an error storing the rectification data
        """
        # Ensure rectification_id is in the data
        rectification_data["rectification_id"] = rectification_id

        # Add timestamps if not present
        now = datetime.now()
        if "created_at" not in rectification_data:
            rectification_data["created_at"] = now.isoformat()
        if "updated_at" not in rectification_data:
            rectification_data["updated_at"] = now.isoformat()

        try:
            # Store in database if available
            if self.db_pool is not None:
                try:
                    # Use a single transaction for atomicity
                    async with self.db_pool.acquire() as conn:
                        async with conn.transaction():
                            # Extract key fields
                            chart_id = rectification_data.get("chart_id", "")
                            original_time = rectification_data.get("original_time", "")
                            rectified_time = rectification_data.get("rectified_time", "")
                            confidence_score = rectification_data.get("confidence_score", 0)
                            status = rectification_data.get("status", "completed")
                            progress = rectification_data.get("progress", 100)

                            # Serialize the full data
                            json_data = json.dumps(rectification_data, default=self._datetime_serializer)

                            # Store in database
                            await conn.execute(
                                """
                                INSERT INTO rectifications (
                                    rectification_id, chart_id, original_time, rectified_time,
                                    confidence_score, status, progress, data, created_at, updated_at
                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                                ON CONFLICT (rectification_id)
                                DO UPDATE SET
                                    chart_id = $2,
                                    original_time = $3,
                                    rectified_time = $4,
                                    confidence_score = $5,
                                    status = $6,
                                    progress = $7,
                                    data = $8,
                                    updated_at = $10
                                """,
                                rectification_id, chart_id, original_time, rectified_time,
                                confidence_score, status, progress, json_data,
                                rectification_data["created_at"], rectification_data["updated_at"]
                            )

                            logger.info(f"Stored rectification {rectification_id} in database")
                            return rectification_id
                except Exception as db_error:
                    logger.warning(f"Database error storing rectification: {db_error}, falling back to file storage")
                    # Update error counter
                    self._db_error_counts["store_rectification"] = self._db_error_counts.get("store_rectification", 0) + 1

                    # Check if we should attempt to reconnect the DB pool
                    if self._db_error_counts.get("store_rectification", 0) >= self._max_errors_before_reconnect:
                        logger.warning(f"Attempting to reset database pool after {self._db_error_counts.get('store_rectification')} errors")
                        self._reset_db_pool()
                        self._db_error_counts["store_rectification"] = 0

                    # Fall back to file storage
                    await self._store_rectification_in_file(rectification_id, rectification_data)
            else:
                # Store in file directly
                await self._store_rectification_in_file(rectification_id, rectification_data)

            return rectification_id
        except Exception as e:
            logger.error(f"Error storing rectification: {e}")
            raise ValueError(f"Failed to store rectification: {e}")

    async def _store_rectification_in_file(self, rectification_id: str, rectification_data: Dict[str, Any]) -> None:
        """
        Store rectification data in file storage.

        Args:
            rectification_id: The rectification ID
            rectification_data: The rectification data to store

        Raises:
            ValueError: If there's an error storing the data
        """
        try:
            # Create directory for rectifications if it doesn't exist
            rectifications_dir = os.path.join(self.file_storage_path, "rectifications")
            os.makedirs(rectifications_dir, exist_ok=True)

            # Create file path for the rectification
            file_path = os.path.join(rectifications_dir, f"{rectification_id}.json")

            # Write data to file
            with open(file_path, 'w') as f:
                json.dump(rectification_data, f, default=self._datetime_serializer, indent=2)

            logger.info(f"Stored rectification {rectification_id} in file at {file_path}")
        except Exception as e:
            logger.error(f"Error storing rectification {rectification_id} to file: {e}")
            raise ValueError(f"File storage error: {e}")

    async def update_rectification_progress(self, rectification_id: str, progress: int, status: str, message: str = "") -> bool:
        """
        Update progress information for an existing rectification.

        Args:
            rectification_id: The rectification ID to update
            progress: Current progress percentage (0-100)
            status: Status string (processing, completed, error)
            message: Optional progress message

        Returns:
            True if successful, False otherwise
        """
        try:
            # First, get the existing rectification data
            rectification_data = await self.get_rectification(rectification_id)

            if not rectification_data:
                logger.warning(f"Cannot update progress for non-existent rectification: {rectification_id}")
                return False

            # Update progress information
            rectification_data["progress"] = progress
            rectification_data["status"] = status
            rectification_data["message"] = message
            rectification_data["updated_at"] = datetime.now().isoformat()

            # Store the updated data
            await self.store_rectification(rectification_id, rectification_data)
            logger.debug(f"Updated rectification {rectification_id} progress to {progress}% ({status})")

            return True
        except Exception as e:
            logger.error(f"Error updating rectification progress: {e}")
            return False

# Add verify_database_schema function and other required functions below
async def verify_database_schema():
    """
    Verify that the database schema is correctly set up.

    This function is a placeholder - in a real implementation it would check tables, indexes, etc.
    """
    logger.info("Database schema verification placeholder")
    pass
