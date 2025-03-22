"""
Service layer initialization.

This module initializes service layer components for the AI service.
"""

# Import services
from ai_service.services.chart_service import ChartService

# Explicitly define get_chart_service function
def get_chart_service() -> ChartService:
    """
    Get or create a chart service instance.
    Ensures the same instance is reused.

    Returns:
        ChartService instance
    """
    from ai_service.services.chart_service import create_chart_service
    try:
        from ai_service.utils.dependency_container import get_container
        container = get_container()

        # Try to get from container
        try:
            return container.get("chart_service")
        except ValueError:
            # Register and get
            container.register("chart_service", create_chart_service)
            return container.get("chart_service")
    except Exception as e:
        # Create directly if container access fails
        return create_chart_service()
