"""
AI Service modules for the Birth Time Rectifier.

This package contains services that provide core functionality for the application.
"""

import logging
from typing import Optional
import os

# Configure logging
logger = logging.getLogger(__name__)

# Import chart service
from ai_service.services.chart_service import ChartService, create_chart_service

# Global instance
_chart_service_instance = None

def create_chart_service():
    """
    Factory function to create a chart service instance.

    Returns:
        ChartService: A new chart service instance
    """
    # Import here to avoid circular imports
    from ai_service.services.chart_service import create_chart_service as factory_func
    return factory_func()

async def get_chart_service_async() -> 'ChartService':
    """
    Get or create a chart service instance asynchronously.
    This ensures the instance is properly initialized with all async resources.

    Returns:
        ChartService: Initialized chart service instance
    """
    global _chart_service_instance

    if _chart_service_instance is not None and getattr(_chart_service_instance, '_initialized', False):
        logger.debug("Returning existing initialized chart service instance")
        return _chart_service_instance

    # Try to get from dependency container first
    from ai_service.utils.dependency_container import get_container
    container = get_container()

    try:
        if container.has_service("chart_service"):
            chart_service = container.get("chart_service")
            if chart_service:
                _chart_service_instance = chart_service
                logger.info("Retrieved chart service from container")
            else:
                raise ValueError("Chart service is None in container")
        else:
            # Import the real factory function
            from ai_service.services.chart_service import create_chart_service

            # Create new instance using the real factory function
            chart_service = create_chart_service()
            container.register_service("chart_service", chart_service)
            _chart_service_instance = chart_service
            logger.info("Created new chart service instance and registered with container")
    except Exception as e:
        logger.error(f"Error getting chart service: {e}")
        raise ValueError(f"Failed to get or create chart service: {e}")

    # Ensure the instance is initialized
    try:
        # Initialize if needed
        if not getattr(_chart_service_instance, '_initialized', False):
            # First, try to get the OpenAI service for initialization
            try:
                # Get OpenAI service
                from ai_service.api.services.openai import get_openai_service
                openai_service = await get_openai_service()

                # Set it on the chart service
                if openai_service:
                    _chart_service_instance.openai_service = openai_service
                    logger.info("OpenAI service set on chart service")
            except Exception as e:
                logger.warning(f"Could not get OpenAI service for chart service: {e}")

            # Now initialize the chart service
            await _chart_service_instance.initialize()
            logger.info("Chart service initialized asynchronously")
    except Exception as e:
        logger.error(f"Error initializing chart service: {e}")
        raise ValueError(f"Failed to initialize chart service: {e}")

    return _chart_service_instance

def get_chart_service() -> 'ChartService':
    """
    Get or create a chart service instance.
    Ensures the same instance is reused.

    Note: This synchronous version does not guarantee the service is fully initialized.
    In asynchronous contexts, use get_chart_service_async() instead.

    Returns:
        ChartService instance (may not be fully initialized)
    """
    global _chart_service_instance

    if _chart_service_instance is not None:
        # Check if we're in an async context
        try:
            import inspect
            current_frame = inspect.currentframe()
            if current_frame and current_frame.f_back and inspect.iscoroutinefunction(current_frame.f_back.f_code):
                logger.warning(
                    "get_chart_service() called from async context. "
                    "Use get_chart_service_async() instead to ensure proper initialization"
                )
        except Exception:
            pass

        logger.debug("Returning existing chart service instance")
        return _chart_service_instance

    # Get from dependency container
    from ai_service.utils.dependency_container import get_container
    container = get_container()

    # Try to get from container first
    try:
        if container.has_service("chart_service"):
            chart_service = container.get("chart_service")
            _chart_service_instance = chart_service
            logger.info("Retrieved chart service from dependency container")
            return chart_service
        else:
            # Create and register if not found using real factory function
            from ai_service.services.chart_service import create_chart_service
            chart_service = create_chart_service()
            container.register_service("chart_service", chart_service)
            _chart_service_instance = chart_service
            logger.info("Created new chart service instance using factory function")
            return chart_service
    except Exception as e:
        logger.error(f"Error getting chart service: {e}")
        raise ValueError(f"Failed to get or create chart service: {e}")

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
    elif name == "ChartService":
        from ai_service.services.chart_service import ChartService as _ChartService
        return _ChartService

    raise AttributeError(f"module {__name__} has no attribute {name}")

__all__ = [
    "ChartService",
    "get_chart_service",
    "get_chart_service_async",
    "OpenAIService",
    "get_openai_service"
]
