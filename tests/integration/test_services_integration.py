"""
Integration tests for service interactions.

This module tests the integration between different services with actual API calls.
No mocks, stubs, or fallbacks are used - all tests use real services.
"""

import pytest
import logging
import asyncio
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the services
from ai_service.api.services.openai.service import OpenAIService, get_openai_service
from ai_service.services.chart_service import ChartService, ChartVerifier
from ai_service.utils.dependency_container import get_container


@pytest.fixture(scope="function")
def reset_container():
    """Reset the dependency container before and after each test."""
    # Get the container and clear all registered mocks
    container = get_container()

    # Clear any existing mocks
    if hasattr(container, '_mocks'):
        container._mocks = {}

    # Let the test run
    yield

    # Clean up after the test
    if hasattr(container, '_mocks'):
        container._mocks = {}


@pytest.mark.asyncio
async def test_chart_service_with_openai_integration(reset_container):
    """
    Test the integration between ChartService and OpenAI API.

    This test verifies that the ChartService correctly uses the OpenAI service
    for chart verification with real API calls.
    """
    # Get a real OpenAI service instance
    openai_service = get_openai_service()

    # Create a real ChartVerifier
    chart_verifier = ChartVerifier(session_id="test_session", openai_service=openai_service)

    # Create the ChartService with real dependencies
    chart_service = ChartService(
        session_id="test_session",
        openai_service=openai_service,
        chart_verifier=chart_verifier
    )

    # Create test data
    verification_data = {
        "chart_data": {
            "ascendant": {"sign": "Aries", "degree": 15.5},
            "planets": [
                {"name": "Sun", "sign": "Capricorn", "degree": 10.5, "house": 10},
                {"name": "Moon", "sign": "Taurus", "degree": 22.3, "house": 2}
            ],
            "houses": [
                {"number": 1, "sign": "Aries", "degree": 15.5},
                {"number": 2, "sign": "Taurus", "degree": 20.1}
            ]
        },
        "birth_details": {
            "birth_date": "1990-01-01",
            "birth_time": "12:00:00",
            "latitude": 40.7128,
            "longitude": -74.0060
        }
    }

    # Verify the chart using real API
    result = await chart_verifier.verify_chart(verification_data, openai_service=openai_service)

    # Verify the result - real API should return a verification response with expected structure
    assert "verified" in result
    assert "confidence_score" in result

    # Now test the chart service's verify_chart_with_openai method using real API
    result = await chart_service.verify_chart_with_openai(
        chart_data=verification_data["chart_data"],
        birth_date=verification_data["birth_details"]["birth_date"],
        birth_time=verification_data["birth_details"]["birth_time"],
        latitude=verification_data["birth_details"]["latitude"],
        longitude=verification_data["birth_details"]["longitude"]
    )

    # Check the structure without assuming specific values that might vary with real API
    assert "verified" in result
    assert "confidence_score" in result


@pytest.mark.asyncio
async def test_openai_service_direct_call():
    """Test the OpenAI service with a direct API call."""
    # Get a real OpenAI service instance
    openai_service = get_openai_service()

    # Make a simple call to the API
    response = await openai_service.generate_completion(
        prompt="Generate a short test response with JSON: {'success': true}",
        task_type="auxiliary",
        max_tokens=50
    )

    # Verify response structure from real API
    assert "content" in response
    assert "model" in response
    assert "tokens" in response
    assert "cost" in response

    # Validate token counts are present
    assert "prompt" in response["tokens"]
    assert "completion" in response["tokens"]
    assert "total" in response["tokens"]
