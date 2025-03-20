"""
Repository classes for database access.
"""

import logging
import json
import asyncio
import asyncpg
from typing import Dict, Any, Optional, List, Union, cast
from datetime import datetime, timedelta

from ai_service.core.config import settings

logger = logging.getLogger(__name__)

class ChartRepository:
    """Repository for chart data storage and retrieval."""

    db_pool: Optional[asyncpg.Pool]

    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        """
        Initialize the repository with database connection.

        Args:
            db_pool: Optional database connection pool
        """
        self.db_pool = db_pool

        # Handle running in both test and application context
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Event loop is running, create task
                self._init_task = asyncio.create_task(self._initialize_db())
            else:
                # Event loop exists but not running, use run_until_complete
                loop.run_until_complete(self._initialize_db())
        except RuntimeError:
            # No event loop, likely in a test context
            logger.warning("No running event loop available for DB initialization. Will initialize as needed.")
            self._init_task = None

    async def _initialize_db(self) -> None:
        """Initialize database connection and create tables if needed."""
        try:
            if not self.db_pool:
                try:
                    # Create a connection pool if not provided
                    self.db_pool = await asyncpg.create_pool(
                        host=settings.DB_HOST,
                        port=settings.DB_PORT,
                        user=settings.DB_USER,
                        password=settings.DB_PASSWORD,
                        database=settings.DB_NAME,
                        min_size=3,
                        max_size=10
                    )
                    logger.info("Database connection pool created")
                except Exception as e:
                    # Log the connection error
                    logger.warning(f"Database connection failed: {e}")
                    # Return without failing - repository operations will handle missing db_pool gracefully
                    return

            # Create tables if they don't exist
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    await conn.execute('''
                        CREATE TABLE IF NOT EXISTS charts (
                            chart_id TEXT PRIMARY KEY,
                            chart_data JSONB NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')

                    await conn.execute('''
                        CREATE TABLE IF NOT EXISTS rectifications (
                            rectification_id TEXT PRIMARY KEY,
                            chart_id TEXT REFERENCES charts(chart_id),
                            original_chart_id TEXT REFERENCES charts(chart_id),
                            rectification_data JSONB NOT NULL,
                            status TEXT NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')

                    await conn.execute('''
                        CREATE TABLE IF NOT EXISTS comparisons (
                            comparison_id TEXT PRIMARY KEY,
                            chart1_id TEXT REFERENCES charts(chart_id),
                            chart2_id TEXT REFERENCES charts(chart_id),
                            comparison_data JSONB NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')

                    await conn.execute('''
                        CREATE TABLE IF NOT EXISTS exports (
                            export_id TEXT PRIMARY KEY,
                            chart_id TEXT REFERENCES charts(chart_id),
                            file_path TEXT NOT NULL,
                            format TEXT NOT NULL,
                            download_url TEXT NOT NULL,
                            generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            expires_at TIMESTAMP WITH TIME ZONE NOT NULL
                        )
                    ''')

                    logger.info("Database tables initialized")
            else:
                logger.warning("No database connection pool available - using alternative storage mechanism if provided")
        except Exception as e:
            logger.warning(f"Database initialization warning: {e}")
            # Don't raise the exception - allow the repository to continue with alternative storage

    async def store_chart(self, chart_id: str, chart_data: Dict[str, Any]) -> None:
        """
        Store chart data in the database.

        Args:
            chart_id: Chart identifier
            chart_data: Chart data to store
        """
        async def _store_operation(db_pool: asyncpg.Pool, chart_id: str, chart_data: Dict[str, Any]):
            # Store timestamp
            now = datetime.now()
            chart_data["created_at"] = chart_data.get("created_at", now.isoformat())
            chart_data["updated_at"] = now.isoformat()

            # Insert or update chart
            async with db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO charts (chart_id, chart_data, created_at, updated_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (chart_id)
                    DO UPDATE SET
                        chart_data = $2,
                        updated_at = $4
                ''', chart_id, json.dumps(chart_data), now, now)

            logger.info(f"Chart {chart_id} stored in database")
            return True

        return await self._execute_db_operation("store_chart", _store_operation, chart_id, chart_data)

    async def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve chart data from the database.

        Args:
            chart_id: Chart identifier

        Returns:
            Chart data or None if not found
        """
        async def _get_operation(db_pool: asyncpg.Pool, chart_id: str):
            # Query database
            async with db_pool.acquire() as conn:
                result = await conn.fetchrow('''
                    SELECT chart_data
                    FROM charts
                    WHERE chart_id = $1
                ''', chart_id)

                if result:
                    chart_data = json.loads(result['chart_data'])
                    logger.info(f"Chart {chart_id} retrieved from database")
                    return chart_data

                logger.info(f"Chart {chart_id} not found in database")
                return None

        return await self._execute_db_operation("get_chart", _get_operation, chart_id)

    async def update_chart(self, chart_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update specific fields in a chart.

        Args:
            chart_id: Chart identifier
            update_data: Data fields to update

        Returns:
            True if updated successfully, False if chart not found
        """
        async def _update_operation(chart_id, update_data):
            # Get existing chart data
            existing_chart = await self.get_chart(chart_id)
            if not existing_chart:
                logger.warning(f"Chart {chart_id} not found for update")
                return False

            # Update specific fields
            for key, value in update_data.items():
                if isinstance(value, dict) and key in existing_chart and isinstance(existing_chart[key], dict):
                    # Merge dictionaries
                    existing_chart[key].update(value)
                else:
                    # Replace or add value
                    existing_chart[key] = value

            # Update timestamp
            existing_chart["updated_at"] = datetime.now().isoformat()

            # Store updated chart
            await self.store_chart(chart_id, existing_chart)

            logger.info(f"Chart {chart_id} updated")
            return True

        return await self._execute_db_operation("update_chart", _update_operation, chart_id, update_data)

    async def delete_chart(self, chart_id: str) -> bool:
        """
        Delete a chart from storage.

        Args:
            chart_id: Chart identifier

        Returns:
            True if deleted, False if not found
        """
        async def _delete_operation(db_pool: asyncpg.Pool, chart_id: str):
            # Delete from database
            async with db_pool.acquire() as conn:
                result = await conn.execute('''
                    DELETE FROM charts
                    WHERE chart_id = $1
                ''', chart_id)

                if result and result.split()[-1] != '0':
                    logger.info(f"Chart {chart_id} deleted from database")
                    return True

                logger.info(f"Chart {chart_id} not found for deletion")
                return False

        return await self._execute_db_operation("delete_chart", _delete_operation, chart_id)

    async def list_charts(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List available charts with pagination.

        Args:
            limit: Maximum number of charts to return
            offset: Number of charts to skip

        Returns:
            List of chart data dictionaries
        """
        async def _list_operation(db_pool: asyncpg.Pool, limit: int, offset: int):
            # Query database
            async with db_pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT chart_id, chart_data
                    FROM charts
                    ORDER BY updated_at DESC
                    LIMIT $1 OFFSET $2
                ''', limit, offset)

                charts = []
                for row in rows:
                    chart_data = json.loads(row['chart_data'])
                    chart_data["chart_id"] = row['chart_id']
                    charts.append(chart_data)

                logger.info(f"Retrieved {len(charts)} charts")
                return charts

        return await self._execute_db_operation("list_charts", _list_operation, limit, offset)

    async def store_rectification(
        self,
        rectification_id: str,
        chart_id: str,
        original_chart_id: str,
        rectification_data: Dict[str, Any]
    ) -> None:
        """
        Store rectification data.

        Args:
            rectification_id: Rectification identifier
            chart_id: Rectified chart ID
            original_chart_id: Original chart ID
            rectification_data: Rectification data
        """
        # Validate input data
        if not rectification_id:
            raise ValueError("Rectification ID is required")

        if not chart_id:
            raise ValueError("Chart ID is required")

        if not original_chart_id:
            raise ValueError("Original chart ID is required")

        if not rectification_data:
            raise ValueError("Rectification data is required")

        async def _store_rectification_operation(db_pool: asyncpg.Pool, rectification_id: str, chart_id: str, original_chart_id: str, rectification_data: Dict[str, Any]):
            # Verify charts exist
            async with db_pool.acquire() as conn:
                chart_exists = await conn.fetchrow("SELECT 1 FROM charts WHERE chart_id = $1", chart_id)
                original_exists = await conn.fetchrow("SELECT 1 FROM charts WHERE chart_id = $1", original_chart_id)

                if not chart_exists:
                    raise ValueError(f"Chart with ID {chart_id} does not exist")

                if not original_exists:
                    raise ValueError(f"Original chart with ID {original_chart_id} does not exist")

            # Store in database
            async with db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO rectifications (
                        rectification_id, chart_id, original_chart_id,
                        rectification_data, status, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $6)
                    ON CONFLICT (rectification_id)
                    DO UPDATE SET
                        rectification_data = $4,
                        status = $5,
                        updated_at = $6
                ''',
                rectification_id, chart_id, original_chart_id,
                json.dumps(rectification_data),
                rectification_data.get("status", "complete"),
                datetime.now())

            logger.info(f"Rectification {rectification_id} stored")
            return True

        return await self._execute_db_operation(
            "store_rectification",
            _store_rectification_operation,
            rectification_id, chart_id, original_chart_id, rectification_data
        )

    async def get_rectification(self, rectification_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve rectification data.

        Args:
            rectification_id: Rectification identifier

        Returns:
            Rectification data or None if not found
        """
        if not rectification_id:
            raise ValueError("Rectification ID is required")

        async def _get_rectification_operation(db_pool: asyncpg.Pool, rectification_id: str):
            # Query database
            async with db_pool.acquire() as conn:
                result = await conn.fetchrow('''
                    SELECT rectification_data
                    FROM rectifications
                    WHERE rectification_id = $1
                ''', rectification_id)

                if result:
                    rectification_data = json.loads(result['rectification_data'])
                    logger.info(f"Rectification {rectification_id} retrieved from database")
                    return rectification_data

                logger.info(f"Rectification {rectification_id} not found in database")
                return None

        return await self._execute_db_operation("get_rectification", _get_rectification_operation, rectification_id)

    async def store_comparison(self, comparison_id: str, comparison_data: Dict[str, Any]) -> None:
        """
        Store comparison data.

        Args:
            comparison_id: Comparison identifier
            comparison_data: Comparison data
        """
        # Validate input data
        if not comparison_id:
            raise ValueError("Comparison ID is required")

        if not comparison_data:
            raise ValueError("Comparison data is required")

        # Ensure required fields are present
        chart1_id = comparison_data.get("chart1_id")
        chart2_id = comparison_data.get("chart2_id")

        if not chart1_id or not chart2_id:
            raise ValueError("Both chart IDs are required for comparison")

        async def _store_comparison_operation(db_pool: asyncpg.Pool, comparison_id: str, comparison_data: Dict[str, Any], chart1_id: str, chart2_id: str):
            # Verify charts exist first
            chart1_exists = False
            chart2_exists = False

            async with db_pool.acquire() as conn:
                # Check if charts exist
                chart1_row = await conn.fetchrow("SELECT 1 FROM charts WHERE chart_id = $1", chart1_id)
                chart2_row = await conn.fetchrow("SELECT 1 FROM charts WHERE chart_id = $1", chart2_id)

                chart1_exists = chart1_row is not None
                chart2_exists = chart2_row is not None

            if not chart1_exists:
                raise ValueError(f"Chart 1 with ID {chart1_id} does not exist")

            if not chart2_exists:
                raise ValueError(f"Chart 2 with ID {chart2_id} does not exist")

            # Store in database
            async with db_pool.acquire() as conn:
                # Use a transaction for data consistency
                async with conn.transaction():
                    # Create timestamp
                    now = datetime.now()

                    # Add metadata to comparison data
                    comparison_data["created_at"] = now.isoformat()
                    comparison_data["comparison_id"] = comparison_id

                    # Insert or update
                    await conn.execute('''
                        INSERT INTO comparisons (
                            comparison_id, chart1_id, chart2_id, comparison_data, created_at
                        )
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (comparison_id)
                        DO UPDATE SET
                            chart1_id = $2,
                            chart2_id = $3,
                            comparison_data = $4
                    ''',
                    comparison_id, chart1_id, chart2_id,
                    json.dumps(comparison_data),
                    now)

            logger.info(f"Comparison {comparison_id} stored successfully")
            return True

        return await self._execute_db_operation(
            "store_comparison",
            _store_comparison_operation,
            comparison_id, comparison_data, chart1_id, chart2_id
        )

    async def get_comparison(self, comparison_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve comparison data.

        Args:
            comparison_id: Comparison identifier

        Returns:
            Comparison data or None if not found
        """
        if not comparison_id:
            raise ValueError("Comparison ID is required")

        async def _get_comparison_operation(db_pool: asyncpg.Pool, comparison_id: str):
            # Query database
            async with db_pool.acquire() as conn:
                result = await conn.fetchrow('''
                    SELECT comparison_data
                    FROM comparisons
                    WHERE comparison_id = $1
                ''', comparison_id)

                if result:
                    comparison_data = json.loads(result['comparison_data'])
                    logger.info(f"Comparison {comparison_id} retrieved from database")
                    return comparison_data

                logger.info(f"Comparison {comparison_id} not found in database")
                return None

        return await self._execute_db_operation("get_comparison", _get_comparison_operation, comparison_id)

    async def store_export(self, export_id: str, export_data: Dict[str, Any]) -> None:
        """
        Store export data.

        Args:
            export_id: Export identifier
            export_data: Export data
        """
        # Validate input data
        if not export_id:
            raise ValueError("Export ID is required")

        if not export_data:
            raise ValueError("Export data is required")

        # Ensure required fields are present
        if not export_data.get("chart_id"):
            raise ValueError("Chart ID is required in export data")

        if not export_data.get("file_path"):
            raise ValueError("File path is required in export data")

        if not export_data.get("format"):
            raise ValueError("Format is required in export data")

        if not export_data.get("download_url"):
            raise ValueError("Download URL is required in export data")

        chart_id = export_data.get("chart_id")

        async def _store_export_operation(db_pool: asyncpg.Pool, export_id: str, export_data: Dict[str, Any], chart_id: str):
            # Verify chart exists
            async with db_pool.acquire() as conn:
                chart_exists = await conn.fetchrow("SELECT 1 FROM charts WHERE chart_id = $1", chart_id)

                if not chart_exists:
                    raise ValueError(f"Chart with ID {chart_id} does not exist")

            # Extract field values
            file_path = export_data.get("file_path")
            format = export_data.get("format")
            download_url = export_data.get("download_url")
            generated_at = export_data.get("generated_at", datetime.now().isoformat())
            expires_at = export_data.get("expires_at",
                              (datetime.now() + timedelta(days=7)).isoformat())

            # Store in database
            async with db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO exports (
                        export_id, chart_id, file_path, format,
                        download_url, generated_at, expires_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (export_id)
                    DO UPDATE SET
                        file_path = $3,
                        format = $4,
                        download_url = $5,
                        expires_at = $7
                ''',
                export_id, chart_id, file_path, format,
                download_url,
                datetime.fromisoformat(generated_at) if isinstance(generated_at, str) else generated_at,
                datetime.fromisoformat(expires_at) if isinstance(expires_at, str) else expires_at)

            logger.info(f"Export {export_id} stored")
            return True

        return await self._execute_db_operation(
            "store_export", _store_export_operation, export_id, export_data, chart_id
        )

    async def get_export(self, export_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve export data.

        Args:
            export_id: Export identifier

        Returns:
            Export data or None if not found
        """
        if not export_id:
            raise ValueError("Export ID is required")

        async def _get_export_operation(db_pool: asyncpg.Pool, export_id: str):
            # Query database
            async with db_pool.acquire() as conn:
                result = await conn.fetchrow('''
                    SELECT export_id, chart_id, file_path, format,
                           download_url, generated_at, expires_at
                    FROM exports
                    WHERE export_id = $1
                ''', export_id)

                if result:
                    # Convert to dictionary
                    export_data = {
                        "export_id": result["export_id"],
                        "chart_id": result["chart_id"],
                        "file_path": result["file_path"],
                        "format": result["format"],
                        "download_url": result["download_url"],
                        "generated_at": result["generated_at"].isoformat(),
                        "expires_at": result["expires_at"].isoformat()
                    }
                    logger.info(f"Export {export_id} retrieved from database")
                    return export_data

                logger.info(f"Export {export_id} not found in database")
                return None

        return await self._execute_db_operation("get_export", _get_export_operation, export_id)

    async def _ensure_initialized(self) -> None:
        """Ensure database is initialized before operations."""
        try:
            # Wait for initialization task if it exists
            if hasattr(self, '_init_task') and self._init_task is not None:
                await self._init_task
            elif not self.db_pool:
                # If no initialization task and no db_pool, initialize now
                await self._initialize_db()
        except Exception as e:
            logger.error(f"Error ensuring database initialization: {e}")
            raise ValueError(f"Database connection failed: {e}")

    async def _execute_db_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """
        Execute a database operation with standardized error handling.

        Args:
            operation_name: Name of the operation for logging
            operation_func: Async function to execute
            *args, **kwargs: Arguments to pass to operation_func

        Returns:
            Result of the operation

        Raises:
            ValueError: If operation fails
        """
        try:
            # Ensure DB is initialized
            await self._ensure_initialized()

            # Check if DB pool is available
            if not self.db_pool:
                raise ValueError(f"Database connection is not available for {operation_name}")

            # Execute the operation
            return await operation_func(self.db_pool, *args, **kwargs)
        except asyncpg.PostgresError as db_error:
            # Handle database-specific errors
            logger.error(f"Database error in {operation_name}: {db_error}")

            # Categorize errors for better handling
            if isinstance(db_error, asyncpg.UndefinedTableError):
                # Table doesn't exist - this should never happen with proper initialization
                logger.critical(f"Table doesn't exist in {operation_name}. Database may not be initialized properly.")
                raise ValueError(f"Database schema error: {str(db_error)}")
            elif isinstance(db_error, asyncpg.UniqueViolationError):
                # Unique constraint violation
                logger.warning(f"Unique constraint violation in {operation_name}")
                raise ValueError(f"Duplicate entry: {str(db_error)}")
            elif isinstance(db_error, asyncpg.ForeignKeyViolationError):
                # Foreign key constraint violation
                logger.warning(f"Foreign key violation in {operation_name}")
                raise ValueError(f"Referenced entity doesn't exist: {str(db_error)}")
            elif isinstance(db_error, asyncpg.InsufficientPrivilegeError):
                # Permission error
                logger.critical(f"Insufficient database privileges in {operation_name}")
                raise ValueError(f"Database permission error: {str(db_error)}")
            elif isinstance(db_error, asyncpg.DeadlockDetectedError):
                # Deadlock detected
                logger.warning(f"Deadlock detected in {operation_name}")
                raise ValueError(f"Database deadlock detected: {str(db_error)}")
            elif isinstance(db_error, asyncpg.TooManyConnectionsError):
                # Connection pool exhausted
                logger.error(f"Too many database connections in {operation_name}")
                raise ValueError(f"Database connection pool exhausted: {str(db_error)}")
            elif isinstance(db_error, asyncpg.QueryCanceledError):
                # Query timeout
                logger.warning(f"Query canceled/timeout in {operation_name}")
                raise ValueError(f"Database query timeout: {str(db_error)}")
            elif isinstance(db_error, asyncpg.InterfaceError):
                # Connection is closed
                logger.error(f"Database connection closed in {operation_name}")
                raise ValueError(f"Database connection closed: {str(db_error)}")
            else:
                # Generic database error
                raise ValueError(f"Database operation '{operation_name}' failed: {str(db_error)}")
        except Exception as e:
            # Handle non-database errors
            logger.error(f"Error in {operation_name}: {str(e)}")
            raise ValueError(f"{operation_name} failed: {str(e)}")
