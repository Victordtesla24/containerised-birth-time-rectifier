"""
Service Dependencies

This module provides dependency injection for services used across the API.
"""

from ai_service.services.chart_service import ChartService

def get_chart_service() -> ChartService:
    """Dependency function to get chart service instance"""
    return ChartService()
