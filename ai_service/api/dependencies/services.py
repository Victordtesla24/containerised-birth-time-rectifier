"""
Service Dependencies

This module provides dependency injection for services used across the API.
"""

# Import the core chart service directly
from ai_service.services.chart_service import ChartService

def get_chart_service():
    """
    Dependency function to get chart service instance.
    """
    # Create a new instance of the ChartService
    return ChartService()
