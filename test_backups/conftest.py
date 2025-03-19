"""
Configuration fixtures for pytest.

This module provides fixtures for dependency injection and mocking in tests.
"""

import pytest
import os
import logging
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional, Type, cast

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import dependency container
from ai_service.utils.dependency_container import get_container

# Define base classes for mocks
class BaseOpenAIService:
    """Base class for OpenAI service mocks."""
    pass

class BaseChartService:
    """Base class for chart service mocks."""
    pass

class BaseChartVerifier:
    """Base class for chart verifier mocks."""
    pass

# Import services we want to mock - handle import errors gracefully
try:
    from ai_service.api.services.openai.service import OpenAIService
    from ai_service.services.chart_service import ChartService, ChartVerifier
    # Use the actual classes for mocking
    ServiceClass = OpenAIService
    ChartServiceClass = ChartService
    VerifierClass = ChartVerifier
except ImportError:
    logger.warning("Service modules not available, using base classes for mocks")
    # Use the base classes if imports fail
    ServiceClass = BaseOpenAIService  # type: ignore
    ChartServiceClass = BaseChartService  # type: ignore
    VerifierClass = BaseChartVerifier  # type: ignore


@pytest.fixture(scope="function")
def reset_container():
    """Reset the dependency container before and after each test."""
    # Get the container and clear all registered mocks
    container = get_container()
    container.clear_mocks()

    # Let the test run
    yield

    # Clean up after the test
    container.clear_mocks()


@pytest.fixture
def mock_openai_service():
    """Create a mock OpenAI service for testing."""
    mock_service = MagicMock(spec=ServiceClass)

    # Set up the generate_completion method as an AsyncMock
    mock_service.generate_completion = AsyncMock()
    mock_service.generate_completion.return_value = {
        "content": "This is a mock response from OpenAI",
        "model": "gpt-4-mock",
        "tokens": {
            "prompt": 10,
            "completion": 20,
            "total": 30
        },
        "cost": 0.0
    }

    # Set up other potentially used methods
    mock_service.verify_chart = AsyncMock()
    mock_service.generate_questions = AsyncMock()

    # Register mock with container
    container = get_container()
    container.register_mock("openai_service", mock_service)

    return mock_service


@pytest.fixture
def mock_chart_verifier():
    """Create a mock chart verifier for testing."""
    mock_verifier = MagicMock(spec=VerifierClass)

    # Set up async methods
    mock_verifier.verify_chart = AsyncMock()
    mock_verifier.verify_chart.return_value = {
        "verified": True,
        "confidence_score": 90,
        "corrections": [],
        "message": "Chart verified successfully (mock)"
    }

    # Register mock with container
    container = get_container()
    container.register_mock("chart_verifier", mock_verifier)

    return mock_verifier


@pytest.fixture
def mock_chart_service(mock_openai_service, mock_chart_verifier):
    """Create a mock chart service for testing."""
    mock_service = MagicMock(spec=ChartServiceClass)

    # Set up async methods
    mock_service.generate_chart = AsyncMock()
    mock_service.verify_chart_with_openai = AsyncMock()
    mock_service.get_chart = AsyncMock()
    mock_service.compare_charts = AsyncMock()
    mock_service.save_chart = AsyncMock()
    mock_service.delete_chart = AsyncMock()

    # Set default return values
    mock_service.generate_chart.return_value = {
        "chart_id": "test_chart_123",
        "generated_at": "2023-01-01T00:00:00Z",
        "verification": {
            "verified": True,
            "confidence_score": 85,
            "message": "Chart generated successfully (mock)"
        }
    }

    # Set up dependencies
    mock_service.openai_service = mock_openai_service
    mock_service.chart_verifier = mock_chart_verifier

    # Register mock with container
    container = get_container()
    container.register_mock("chart_service", mock_service)

    return mock_service


@pytest.fixture
def sample_chart_data():
    """Provide sample chart data for testing."""
    return {
        "chart_id": "test_chart_123",
        "birth_details": {
            "birth_date": "1990-01-01",
            "birth_time": "12:00:00",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timezone": "America/New_York",
            "location": "New York, NY"
        },
        "ascendant": {
            "sign": "Aries",
            "degree": 15.5
        },
        "planets": [
            {"name": "Sun", "sign": "Capricorn", "degree": 10.5, "house": 10},
            {"name": "Moon", "sign": "Taurus", "degree": 22.3, "house": 2},
            {"name": "Mercury", "sign": "Capricorn", "degree": 5.6, "house": 10}
        ],
        "houses": [
            {"number": 1, "sign": "Aries", "degree": 15.5},
            {"number": 2, "sign": "Taurus", "degree": 20.1},
            {"number": 3, "sign": "Gemini", "degree": 25.3}
        ],
        "generated_at": "2023-01-01T00:00:00Z"
    }
