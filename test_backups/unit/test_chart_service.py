"""
Unit tests for ChartService.

This module demonstrates proper testing with dependency injection and test mocks.
"""

import pytest
import logging
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import dependency container
from ai_service.utils.dependency_container import get_container

# Import services to test
try:
    from ai_service.services.chart_service import ChartService, ChartVerifier
    from ai_service.api.services.openai.service import OpenAIService
except ImportError:
    logger.warning("Chart service modules not found, tests will be skipped")
    pytest.skip("Chart service modules not found", allow_module_level=True)


@pytest.mark.asyncio
async def test_generate_chart_with_full_dependency_injection(reset_container, sample_chart_data):
    """
    Test generate_chart with completely mocked dependencies.

    This demonstrates using explicit dependency injection for all dependencies.
    """
    # Create mock dependencies
    mock_openai_service = MagicMock(spec=OpenAIService)
    mock_openai_service.generate_completion = AsyncMock()
    mock_openai_service.generate_completion.return_value = {
        "content": '{"verified": true, "confidence_score": 95, "corrections": [], "message": "Chart verified"}',
        "model": "gpt-4-mock",
        "tokens": {"prompt": 10, "completion": 20, "total": 30},
        "cost": 0.0
    }

    mock_chart_verifier = MagicMock(spec=ChartVerifier)
    mock_chart_verifier.verify_chart = AsyncMock()
    mock_chart_verifier.verify_chart.return_value = {
        "verified": True,
        "confidence_score": 95,
        "corrections": [],
        "message": "Chart verified successfully"
    }

    mock_astro_calculator = MagicMock()
    mock_astro_calculator.calculate_chart = AsyncMock()
    mock_astro_calculator.calculate_chart.return_value = sample_chart_data

    mock_calculator = MagicMock()
    mock_calculator.calculate_verified_chart = AsyncMock()
    mock_calculator.calculate_verified_chart.return_value = sample_chart_data

    mock_repository = MagicMock()
    mock_repository.store_chart = AsyncMock()
    mock_repository.store_chart.return_value = "test_chart_123"

    # Create the service with all dependencies injected
    service = ChartService(
        openai_service=mock_openai_service,
        chart_verifier=mock_chart_verifier,
        calculator=mock_calculator,
        astro_calculator=mock_astro_calculator,
        chart_repository=mock_repository,
        session_id="test_session"
    )

    # Call the generate_chart method
    result = await service.generate_chart(
        birth_date="1990-01-01",
        birth_time="12:00:00",
        latitude=40.7128,
        longitude=-74.0060,
        timezone="America/New_York",
        location="New York, NY",
        verify_with_openai=True
    )

    # Verify dependencies were used correctly
    mock_astro_calculator.calculate_chart.assert_called_once()
    mock_chart_verifier.verify_chart.assert_called_once()
    mock_repository.store_chart.assert_called_once()

    # Verify result structure
    assert "chart_id" in result
    assert "verification" in result
    assert result["verification"]["verified"] is True
    assert result["verification"]["confidence_score"] == 95


@pytest.mark.asyncio
async def test_verify_chart_with_openai_using_container(reset_container, mock_openai_service):
    """
    Test verify_chart_with_openai using the dependency container.

    This demonstrates using the container to register and inject dependencies.
    """
    # Set up the mock OpenAI service response
    mock_openai_service.generate_completion.return_value = {
        "content": '{"verified": true, "confidence_score": 90, "corrections": [], "message": "Chart verified with container"}',
        "model": "gpt-4-mock",
        "tokens": {"prompt": 15, "completion": 25, "total": 40},
        "cost": 0.0
    }

    # Create mock repository
    mock_repository = MagicMock()
    mock_repository.store_chart = AsyncMock()
    mock_repository.store_chart.return_value = "test_chart_123"

    # Create a chart verifier with dependency injection
    chart_verifier = ChartVerifier(session_id="test_session", openai_service=mock_openai_service)

    # Create the service with partial dependency injection
    service = ChartService(
        chart_verifier=chart_verifier,
        openai_service=mock_openai_service,
        chart_repository=mock_repository,
        session_id="test_session"
    )

    # Sample chart data
    chart_data = {
        "ascendant": {"sign": "Aries", "degree": 15.5},
        "planets": [
            {"name": "Sun", "sign": "Capricorn", "degree": 10.5, "house": 10},
            {"name": "Moon", "sign": "Taurus", "degree": 22.3, "house": 2}
        ],
        "houses": [
            {"number": 1, "sign": "Aries", "degree": 15.5},
            {"number": 2, "sign": "Taurus", "degree": 20.1}
        ]
    }

    # Call the verify_chart_with_openai method
    result = await service.verify_chart_with_openai(
        chart_data=chart_data,
        birth_date="1990-01-01",
        birth_time="12:00:00",
        latitude=40.7128,
        longitude=-74.0060
    )

    # Verify dependencies were used correctly
    mock_openai_service.generate_completion.assert_called_once()

    # Verify result structure
    assert result["verified"] is True
    assert result["confidence_score"] == 90
    assert "message" in result


@pytest.mark.asyncio
async def test_error_handling_in_verification(reset_container):
    """
    Test error handling in verification without fallbacks.

    This demonstrates the Error First approach rather than using fallbacks.
    """
    # Create a mock OpenAI service that raises an exception
    mock_openai_service = MagicMock(spec=OpenAIService)
    mock_openai_service.generate_completion = AsyncMock(
        side_effect=Exception("Test API error")
    )

    # Create the chart verifier with the failing service
    chart_verifier = ChartVerifier(
        session_id="test_session",
        openai_service=mock_openai_service
    )

    # Create the chart service
    service = ChartService(
        openai_service=mock_openai_service,
        chart_verifier=chart_verifier,
        session_id="test_session"
    )

    # Sample chart data
    chart_data = {
        "ascendant": {"sign": "Aries", "degree": 15.5},
        "planets": [{"name": "Sun", "sign": "Capricorn", "degree": 10.5}]
    }

    # Verify that an error is raised instead of using a fallback
    with pytest.raises(Exception) as excinfo:
        await service.verify_chart_with_openai(
            chart_data=chart_data,
            birth_date="1990-01-01",
            birth_time="12:00:00",
            latitude=40.7128,
            longitude=-74.0060
        )

    # Verify the error message
    assert "Test API error" in str(excinfo.value)

    # Verify the OpenAI service was called
    mock_openai_service.generate_completion.assert_called_once()
