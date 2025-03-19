"""
Repository classes for database access.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class ChartRepository:
    """Repository for chart data storage and retrieval."""

    def __init__(self):
        """Initialize the repository with an in-memory store for testing."""
        self.charts = {}

    async def store_chart(self, chart_id: str, chart_data: Dict[str, Any]) -> str:
        """
        Store chart data in the repository.

        Args:
            chart_id: ID for the chart
            chart_data: Dictionary containing chart data

        Returns:
            Chart ID
        """
        self.charts[chart_id] = chart_data
        logger.info(f"Stored chart with ID: {chart_id}")
        return chart_id

    async def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve chart data by ID.

        Args:
            chart_id: ID of the chart to retrieve

        Returns:
            Chart data dictionary or None if not found
        """
        chart_data = self.charts.get(chart_id)
        if not chart_data:
            logger.warning(f"Chart with ID {chart_id} not found")
            return None

        logger.info(f"Retrieved chart with ID: {chart_id}")
        return chart_data

    async def update_chart(self, chart_id: str, chart_data: Dict[str, Any]) -> bool:
        """
        Update chart data.

        Args:
            chart_id: ID of the chart to update
            chart_data: Updated chart data

        Returns:
            True if update was successful, False otherwise
        """
        if chart_id not in self.charts:
            logger.warning(f"Cannot update chart {chart_id} - not found")
            return False

        self.charts[chart_id] = chart_data
        logger.info(f"Updated chart with ID: {chart_id}")
        return True

    async def list_charts(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all charts, optionally filtered by user ID.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            List of chart data dictionaries
        """
        if user_id:
            charts = [chart for chart in self.charts.values()
                     if chart.get("user_id") == user_id]
        else:
            charts = list(self.charts.values())

        logger.info(f"Listed {len(charts)} charts")
        return charts

    async def save_chart(self, chart_id: str, chart_data: Dict[str, Any]) -> str:
        """
        Alias for store_chart for compatibility.

        Args:
            chart_id: ID for the chart
            chart_data: Dictionary containing chart data

        Returns:
            Chart ID
        """
        return await self.store_chart(chart_id, chart_data)

    async def store_chart_with_id(self, chart_id: str, chart_data: Dict[str, Any]) -> str:
        """
        Store chart data with explicit ID.

        Args:
            chart_id: Explicit chart ID to use
            chart_data: Dictionary containing chart data

        Returns:
            Chart ID
        """
        self.charts[chart_id] = chart_data
        logger.info(f"Stored chart with ID: {chart_id}")
        return chart_id

    async def store_comparison(self, comparison_id: str, comparison_data: Dict[str, Any]) -> str:
        """
        Store chart comparison data.

        Args:
            comparison_id: ID for the comparison
            comparison_data: Dictionary containing comparison data

        Returns:
            Comparison ID
        """
        # Store in a separate collection/key for comparisons
        if not hasattr(self, 'comparisons'):
            self.comparisons = {}

        self.comparisons[comparison_id] = comparison_data
        logger.info(f"Stored comparison with ID: {comparison_id}")
        return comparison_id

    async def delete_chart(self, chart_id: str) -> bool:
        """
        Delete a chart by ID.

        Args:
            chart_id: ID of the chart to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        if chart_id not in self.charts:
            logger.warning(f"Cannot delete chart {chart_id} - not found")
            return False

        del self.charts[chart_id]
        logger.info(f"Deleted chart with ID: {chart_id}")
        return True
