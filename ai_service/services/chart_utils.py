"""
Chart utilities for retrieving and processing chart data.

This module provides utility functions for working with astrological charts,
consolidating functionality that was previously spread across different modules.
"""

import logging
from typing import Dict, Any, Optional, List, Union
import json

from ai_service.services import get_chart_service

# Configure logging
logger = logging.getLogger(__name__)

async def retrieve_chart(chart_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a chart by ID using the chart service.

    This function consolidates chart retrieval logic that was previously
    scattered across different modules.

    Args:
        chart_id: The chart ID to retrieve

    Returns:
        The chart data or None if not found
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get chart data
        chart_data = await chart_service.get_chart(chart_id)
        return chart_data
    except Exception as e:
        logger.error(f"Error retrieving chart {chart_id}: {e}")
        return None
