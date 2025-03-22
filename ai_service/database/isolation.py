"""
Database transaction isolation utilities for testing.
"""
import logging
import asyncio
import contextlib
from typing import Optional, AsyncContextManager, Any

logger = logging.getLogger(__name__)

class TransactionIsolation:
    """
    Class for managing database transaction isolation in tests.

    This ensures database operations execute in isolated transactions that
    are automatically rolled back at the end of tests, preventing test state
    from leaking into other tests or the real database.
    """

    def __init__(self, db_pool=None):
        """
        Initialize transaction isolation manager.

        Args:
            db_pool: Optional asyncpg connection pool. If None, one will be created when needed.
        """
        self.db_pool = db_pool
        self.connection = None
        self.transaction = None

    async def __aenter__(self) -> 'TransactionIsolation':
        """Start a transaction when used as an async context manager."""
        await self.start_transaction()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Roll back transaction when exiting the async context manager."""
        await self.rollback_transaction()

    async def start_transaction(self) -> None:
        """
        Start a new transaction.
        If a transaction is already active, this will create a savepoint instead.
        """
        if not self.db_pool:
            # Import here to avoid circular dependencies
            from ai_service.database.connection import get_db_pool
            self.db_pool = await get_db_pool()

        if not self.connection:
            # Get a connection from the pool
            self.connection = await self.db_pool.acquire()

            # Start a transaction
            self.transaction = self.connection.transaction()
            await self.transaction.start()
            logger.info("Started isolated database transaction")
        else:
            # Create a savepoint if we already have a transaction
            savepoint_name = f"sp_{id(self)}"
            await self.connection.execute(f"SAVEPOINT {savepoint_name}")
            logger.info(f"Created savepoint {savepoint_name}")

    async def rollback_transaction(self) -> None:
        """
        Roll back the current transaction.
        If savepoints are active, it will roll back to the last savepoint.
        """
        if self.transaction and self.connection:
            try:
                # Roll back the transaction
                await self.transaction.rollback()
                logger.info("Rolled back isolated transaction")
            except Exception as e:
                logger.warning(f"Error rolling back transaction: {e}")

            try:
                # Release the connection back to the pool
                if self.connection is not None and self.db_pool is not None:
                    await self.db_pool.release(self.connection)
                    logger.info("Released database connection")
            except Exception as e:
                logger.warning(f"Error releasing connection: {e}")

            # Reset the state
            self.transaction = None
            self.connection = None

    async def release(self) -> None:
        """Release connection if it exists."""
        if self.connection is not None and self.db_pool is not None:
            try:
                await self.db_pool.release(self.connection)
                logger.info("Released database connection")
            except Exception as e:
                logger.warning(f"Error releasing connection: {e}")
            self.connection = None

    async def execute(self, query: str, *args, **kwargs) -> Any:
        """
        Execute a query within the isolated transaction.

        Args:
            query: SQL query string
            *args, **kwargs: Arguments to pass to the execute method

        Returns:
            Result of the query execution
        """
        if self.connection is None:
            await self.start_transaction()

        if self.connection is not None:
            return await self.connection.execute(query, *args, **kwargs)
        else:
            logger.error("Database connection is None, cannot execute query")
            raise ValueError("Database connection is None")

    async def fetch(self, query: str, *args, **kwargs) -> Any:
        """
        Execute a query and fetch all results within the isolated transaction.

        Args:
            query: SQL query string
            *args, **kwargs: Arguments to pass to the fetch method

        Returns:
            Result rows from the query
        """
        if self.connection is None:
            await self.start_transaction()

        if self.connection is not None:
            return await self.connection.fetch(query, *args, **kwargs)
        else:
            logger.error("Database connection is None, cannot fetch query results")
            raise ValueError("Database connection is None")

    async def fetchrow(self, query: str, *args, **kwargs) -> Optional[Any]:
        """
        Execute a query and fetch a single row within the isolated transaction.

        Args:
            query: SQL query string
            *args, **kwargs: Arguments to pass to the fetchrow method

        Returns:
            Single result row or None
        """
        if self.connection is None:
            await self.start_transaction()

        if self.connection is not None:
            return await self.connection.fetchrow(query, *args, **kwargs)
        else:
            logger.error("Database connection is None, cannot fetchrow")
            raise ValueError("Database connection is None")

    async def fetchval(self, query: str, *args, **kwargs) -> Optional[Any]:
        """
        Execute a query and fetch a single value within the isolated transaction.

        Args:
            query: SQL query string
            *args, **kwargs: Arguments to pass to the fetchval method

        Returns:
            Single value or None
        """
        if self.connection is None:
            await self.start_transaction()

        if self.connection is not None:
            return await self.connection.fetchval(query, *args, **kwargs)
        else:
            logger.error("Database connection is None, cannot fetchval")
            raise ValueError("Database connection is None")

    @staticmethod
    async def get_isolation():
        """
        Factory method for creating and managing a transaction isolation instance.

        Returns:
            A TransactionIsolation instance with an active transaction

        Example:
            isolation = await TransactionIsolation.get_isolation()
            try:
                # Use isolation...
                await isolation.execute("INSERT INTO users (name) VALUES ('test')")
                result = await isolation.fetch("SELECT * FROM users")
            finally:
                # Roll back transaction when done
                await isolation.rollback_transaction()
        """
        isolation = TransactionIsolation()
        await isolation.start_transaction()
        return isolation

# Create a function to wrap tests with transaction isolation
def with_transaction_isolation(func):
    """
    Decorator for wrapping test functions with transaction isolation.

    Example:
        @pytest.mark.asyncio
        @with_transaction_isolation
        async def test_database_operations():
            # Operations will be wrapped in a transaction that gets rolled back
            result = await repository.create_item({"name": "test"})
            # No cleanup needed - transaction will be rolled back
    """
    async def wrapper(*args, **kwargs):
        isolation = await TransactionIsolation.get_isolation()
        try:
            # Add transaction to kwargs
            kwargs['txn'] = isolation
            # Run the test
            return await func(*args, **kwargs)
        finally:
            # Ensure rollback happens even on test failure
            await isolation.rollback_transaction()

    return wrapper
