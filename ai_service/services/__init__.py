"""
Service package for core business logic.

This module provides access to various services that implement the application's
core business logic, following the Unified API Gateway Architecture.
"""

import logging
from typing import Optional, Dict, Any
from importlib import import_module
import os

# Configure logging
logger = logging.getLogger(__name__)

# We'll use lazy loading pattern to avoid circular imports
def get_chart_service():
    """
    Get the chart service implementation.

    This function lazily imports the chart service implementation
    to avoid circular imports.

    Returns:
        The chart service implementation
    """
    from ai_service.services.chart_service import create_chart_service
    return create_chart_service()

def get_openai_service():
    """
    Get the OpenAI service implementation.

    This function lazily imports the OpenAI service implementation
    to avoid circular imports.

    Returns:
        The OpenAI service implementation

    Raises:
        RuntimeError: If OpenAI service is not available
    """
    try:
        from ai_service.api.services.openai.service import OpenAIService
        import os
        api_key = os.environ.get('OPENAI_API_KEY', '')
        if not api_key:
            raise ValueError("OpenAI API key is required but not provided in environment variables")
        return OpenAIService(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to get OpenAI service: {e}")
        raise RuntimeError(f"OpenAI service unavailable: {str(e)}")

# Define the service interface classes for type hinting
class ChartService:
    """
    Chart service interface.

    This class provides methods for generating and manipulating astrological charts.
    """
    pass

class OpenAIService:
    """
    OpenAI service interface.

    This class provides methods for interacting with the OpenAI API.
    """
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key

    async def verify_chart(self, chart_data):
        """
        Verify chart data using OpenAI.

        Args:
            chart_data: Chart data to verify

        Returns:
            Verification result

        Raises:
            NotImplementedError: This is an interface method that should be implemented
        """
        raise NotImplementedError("This method must be implemented by a concrete OpenAI service class")

    async def generate_text(self, prompt, **kwargs):
        """
        Generate text using OpenAI.

        Args:
            prompt: Text prompt
            **kwargs: Additional parameters

        Returns:
            Generated text

        Raises:
            NotImplementedError: This is an interface method that should be implemented
        """
        raise NotImplementedError("This method must be implemented by a concrete OpenAI service class")

    async def rectify_birth_time(self, chart_data, answers):
        """
        Rectify birth time using OpenAI.

        Args:
            chart_data: Chart data
            answers: Questionnaire answers

        Returns:
            Rectification result

        Raises:
            NotImplementedError: This is an interface method that should be implemented
        """
        raise NotImplementedError("This method must be implemented by a concrete OpenAI service class")

# Define an async chart service accessor for consistency
async def get_chart_service_async():
    """
    Get an instance of the ChartService asynchronously.

    This function exists for API consistency with other async service accessors.
    It simply returns the result of the synchronous get_chart_service function.

    Returns:
        ChartService: A chart service instance
    """
    return get_chart_service()

__all__ = [
    "ChartService",
    "OpenAIService",
    "get_chart_service",
    "get_chart_service_async",
    "get_openai_service"
]
