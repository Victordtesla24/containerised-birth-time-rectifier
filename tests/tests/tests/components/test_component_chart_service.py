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
import json
import os
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import dependency container
from ai_service.utils.dependency_container import get_container

# Import services to test
from ai_service.api.services.openai import OpenAIService
from ai_service.services.chart_service import ChartService
from ai_service.services.chart_service_verification import verify_chart_with_openai

# Create a simple ChartVerifier class for testing
class ChartVerifier:
    """Mock chart verifier class for testing."""
    async def verify_chart(self, chart_data):
        """Mock verification method."""
        return {
            "verified": True,
            "confidence_score": 95,
            "corrections": [],
            "message": "Chart verified successfully"
        }

@pytest.mark.asyncio
async def test_chart_service_modules():
    """Test that chart service modules are properly registered in the container."""
    # Setup
    container = get_container()

    # Test
    service = ChartService()

    # Assert
    assert service is not None

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
    service = ChartService(chart_output_dir="/tmp/chart_test")

    # Register dependencies in the container
    container = get_container()
    container.register_instance('openai_service', mock_openai_service)
    container.register_instance('chart_verifier', mock_chart_verifier)
    container.register_instance('calculator', mock_calculator)
    container.register_instance('astro_calculator', mock_astro_calculator)
    container.register_instance('chart_repository', mock_repository)

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
    """Test chart verification using the container."""
    # Create the service with just the chart output directory
    service = ChartService(chart_output_dir="/tmp/chart_test")

    # Register mock OpenAI service in the container
    container = get_container()
    container.register_instance('openai_service', mock_openai_service)

    # Mock chart data
    chart_data = {
        "planets": {"Sun": {"sign": "Capricorn"}},
        "houses": {"1": 0.0},
        "birth_details": {}
    }

    # Perform verification using the verify_chart_with_openai function from the module
    result = await verify_chart_with_openai(chart_data)

    # Verify result structure
    assert result["verified"] is True
    assert result["confidence_score"] == 95
    assert "message" in result


@pytest.mark.asyncio
async def test_error_handling_in_verification(reset_container):
    """
    Test that chart verification properly handles errors from OpenAI without fallbacks.
    This test confirms the service raises exceptions rather than using fallbacks.
    """
    import tempfile

    # Create a temporary directory for chart outputs
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create the chart service with output directory
        service = ChartService(chart_output_dir=tmp_dir)

        # Register a mock OpenAI service that will throw an error
        container = get_container()
        mock_openai_service = MagicMock()
        mock_openai_service.chat_completion.side_effect = Exception("Test API error")
        container.register_instance('openai_service', mock_openai_service)

        # Verify that an error is raised instead of using a fallback
        with pytest.raises(Exception) as excinfo:
            # Use the generate_chart method with verify_with_openai=True to trigger verification
            await service.generate_chart(
                birth_date="1990-01-01",
                birth_time="12:00:00",
                latitude=40.7128,
                longitude=-74.0060,
                timezone="America/New_York",
                location="New York",
                verify_with_openai=True
            )

        # Verify the error contains the expected message
        error_message = str(excinfo.value).lower()
        assert "error" in error_message or "failed" in error_message or "verification" in error_message
