"""
Service layer initialization.

This module initializes service layer components for the AI service.
"""

import logging
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# Import chart service
from ai_service.services.chart_service import ChartService, create_chart_service

# Singleton instance for chart service
_chart_service_instance: Optional[ChartService] = None

def get_chart_service() -> ChartService:
    """
    Get or create a chart service instance.
    Ensures the same instance is reused.

    Returns:
        ChartService instance
    """
    global _chart_service_instance

    if _chart_service_instance is not None:
        logger.debug("Returning existing chart service instance")
        return _chart_service_instance

    try:
        # Try to get from dependency container
        from ai_service.utils.dependency_container import get_container
        container = get_container()

        # Try to get from container first
        try:
            chart_service = container.get("chart_service")
            _chart_service_instance = chart_service
            logger.info("Retrieved chart service from dependency container")
            return chart_service
        except ValueError:
            # Create and register if not found
            logger.info("Creating new chart service instance and registering with container")
            chart_service = create_chart_service()
            container.register_service("chart_service", chart_service)
            _chart_service_instance = chart_service
            return chart_service
    except Exception as e:
        # Create directly as fallback
        logger.warning(f"Error accessing dependency container: {e}. Creating direct chart service instance.")
        chart_service = create_chart_service()
        _chart_service_instance = chart_service
        return chart_service
