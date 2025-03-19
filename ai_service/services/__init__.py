"""
Service layer initialization.

This module initializes service layer components for the AI service.
"""

# Import services
from ai_service.services.chart_service import ChartService, ChartVerifier

# Global service instances
_chart_service = None

def get_chart_service() -> ChartService:
    """
    Get or create a chart service instance.
    Ensures the same instance is reused.

    Returns:
        ChartService instance
    """
    global _chart_service
    if _chart_service is None:
        _chart_service = ChartService()
    return _chart_service
