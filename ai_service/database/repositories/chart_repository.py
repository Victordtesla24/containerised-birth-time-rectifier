import json
from typing import Dict, Any, Optional
import asyncpg
from ai_service.database.connection import get_db_pool
from ai_service.utils.logger import logger

class ChartRepository:
    """Repository for chart data operations."""

    def __init__(self, db_pool=None):
        """
        Initialize the repository.

        Args:
            db_pool: Optional database connection pool
        """
        # Store the provided pool or None
        self.db_pool = db_pool

    async def _ensure_pool(self) -> Optional[asyncpg.Pool]:
        """
        Ensure we have a valid database pool.

        Returns:
            Database pool or None if initialization failed
        """
        if self.db_pool is None:
            # Initialize db_pool if not provided
            self.db_pool = await get_db_pool()

        return self.db_pool

    async def store_chart(self, chart_data: Dict[str, Any]) -> None:
        """
        Store chart data in the database.

        Args:
            chart_data: Chart data to store
        """
        chart_id = chart_data.get("chart_id")
        if not chart_id:
            logger.error("Cannot store chart: no chart_id provided")
            return

        # Get pool
        pool = await self._ensure_pool()
        if pool is None:
            logger.error("Cannot store chart: database pool not initialized")
            return

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO charts (chart_id, chart_data)
                VALUES ($1, $2)
                ON CONFLICT (chart_id)
                DO UPDATE SET chart_data = $2, updated_at = NOW()
                """,
                chart_id,
                json.dumps(chart_data)
            )
            logger.info(f"Stored chart with ID: {chart_id}")

    async def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Get chart data from the database.

        Args:
            chart_id: ID of the chart to retrieve

        Returns:
            Chart data or None if not found
        """
        # Get pool
        pool = await self._ensure_pool()
        if pool is None:
            logger.error("Cannot get chart: database pool not initialized")
            return None

        async with pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT chart_data
                FROM charts
                WHERE chart_id = $1
                """,
                chart_id
            )

            if result:
                try:
                    return json.loads(result["chart_data"])
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing chart data for {chart_id}: {e}")
                    return None

            logger.info(f"No chart found with ID: {chart_id}")
            return None
