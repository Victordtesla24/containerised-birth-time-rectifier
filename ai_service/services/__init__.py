"""
AI Service modules for the Birth Time Rectifier.

This package contains services that provide core functionality for the application.
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

    # Get from dependency container
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

# For backward compatibility, re-export OpenAIService
# but import it lazily to avoid circular dependencies
def __getattr__(name):
    """
    Lazily load attributes when accessed to avoid circular imports.

    Args:
        name: The name of the attribute to load

    Returns:
        The requested attribute

    Raises:
        AttributeError: If the attribute doesn't exist
    """
    if name == "OpenAIService":
        from ai_service.services.openai_service import OpenAIService as _OpenAIService
        return _OpenAIService
    elif name == "get_openai_service":
        from ai_service.services.openai_service import get_openai_service as _get_openai_service
        return _get_openai_service

    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = [
    "ChartService",
    "get_chart_service",
    "OpenAIService",
    "get_openai_service"
]
