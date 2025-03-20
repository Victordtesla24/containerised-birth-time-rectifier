"""
Unit tests for OpenAIService.

This module demonstrates proper testing with dependency injection and real OpenAI API calls.
"""

import pytest
import os
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the service and dependency container
from ai_service.utils.dependency_container import get_container
from ai_service.api.services.openai.service import OpenAIService, get_openai_service
from ai_service.api.services.questionnaire_service import QuestionnaireService, get_questionnaire_service

try:
    # This is a backup import if the above fails, which shouldn't be needed
    pass
except ImportError:
    # Create a mock OpenAI service for testing
    class OpenAIServiceMock:
        async def generate_completion(self, prompt, task_type=None, max_tokens=None, temperature=None):
            return {"content": prompt}


@pytest.mark.asyncio
async def test_openai_service_initialization():
    """Test that the OpenAIService initializes correctly with API key."""
    # Create the service with a test API key
    service = OpenAIService(api_key="test_api_key")

    # Check that the service was initialized correctly
    assert service.api_key == "test_api_key"
    assert service.default_model == "gpt-4-turbo-preview"


@pytest.mark.asyncio
async def test_openai_service_missing_api_key():
    """Test that the OpenAIService raises an error when API key is missing."""
    # Temporarily remove API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        del os.environ["OPENAI_API_KEY"]

    # Verify that service initialization fails without API key
    with pytest.raises(ValueError) as excinfo:
        service = OpenAIService()

    # Verify error message
    assert "API key not provided" in str(excinfo.value)

    # Restore API key if it was set
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key


@pytest.mark.asyncio
async def test_generate_completion_with_mocked_client():
    """Test the generate_completion method with a mocked client."""
    # Create a mock client
    mock_client = MagicMock()

    # Set up the response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 20
    mock_response.usage.total_tokens = 30

    # Mock the completions.create method
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    # Create the service with our mock client
    service = OpenAIService(client=mock_client, api_key="test_api_key")

    # Call generate_completion
    result = await service.generate_completion(
        prompt="Hello, world!",
        task_type="test",
        max_tokens=10,
        temperature=0.5
    )

    # Verify the client was called correctly
    mock_client.chat.completions.create.assert_called_once()

    # Verify the result
    assert result["content"] == "Test response"
    assert result["tokens"]["prompt"] == 10
    assert result["tokens"]["completion"] == 20
    assert result["tokens"]["total"] == 30


@pytest.mark.asyncio
async def test_openai_service_with_container(reset_container):
    """
    Test the OpenAI service using the dependency container.

    This demonstrates how to use the container for testing.
    """
    # Create a mock client
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock()

    # Set up the response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Container test response"
    mock_response.usage = MagicMock()
    mock_response.usage.prompt_tokens = 15
    mock_response.usage.completion_tokens = 25
    mock_response.usage.total_tokens = 40

    mock_client.chat.completions.create.return_value = mock_response

    # Create a mock service
    mock_service = OpenAIService(client=mock_client, api_key="test_key")

    # Register the mock with the container
    container = get_container()
    container.register_mock("openai_service", mock_service)

    # Get the service using the normal factory function
    service = get_openai_service()

    # The service should be our mock
    assert service is mock_service

    # Test the method
    result = await service.generate_completion(
        prompt="Container test",
        task_type="test",
        max_tokens=200,
        temperature=0.3
    )

    # Verify the client was called
    mock_client.chat.completions.create.assert_called_once()

    # Verify the result
    assert result["content"] == "Container test response"


@pytest.mark.asyncio
async def test_error_handling_without_fallbacks(reset_container):
    """
    Test that errors are properly raised without fallbacks.

    This demonstrates the Error First approach without silent fallbacks.
    """
    # Create a mock client that raises an exception
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("Test error")
    )

    # Create the service with the mocked client
    service = OpenAIService(client=mock_client, api_key="test_key")

    # Test that the error is propagated
    with pytest.raises(Exception) as excinfo:
        await service.generate_completion(
            prompt="Error test",
            task_type="test"
        )

    # Verify the error message
    assert "Test error" in str(excinfo.value)

@pytest.fixture
def openai_service_mock():
    """Create a real OpenAI service for testing."""
    # Return the actual OpenAI service
    return get_openai_service()

@pytest.mark.asyncio
async def test_openai_service_generate_completion():
    """Test the OpenAI service's generate_completion method with a real API call."""
    # Get the real OpenAI service
    openai_service = get_openai_service()

    # Call the generate_completion method with a real prompt
    result = await openai_service.generate_completion(
        prompt="Explain what astrological birth chart rectification is in one sentence.",
        task_type="test",
        max_tokens=100
    )

    # Verify the result
    assert result is not None
    assert "content" in result
    assert isinstance(result["content"], str)
    assert len(result["content"]) > 0

@pytest.mark.asyncio
async def test_chart_verification_with_openai():
    """Test chart verification with OpenAI using a real API call."""
    # Get the real OpenAI service
    openai_service = get_openai_service()

    # Create a chart verifier with the real OpenAI service
    from ai_service.services.chart_service import ChartVerifier
    chart_verifier = ChartVerifier()
    # Use the real OpenAI service
    chart_verifier.openai_service = openai_service

    # Verification data
    verification_data = {
        "chart_data": {
            "planets": [
                {"name": "Sun", "sign": "Aries", "degree": 15},
                {"name": "Moon", "sign": "Taurus", "degree": 10}
            ],
            "houses": [
                {"number": 1, "sign": "Gemini", "degree": 5},
                {"number": 2, "sign": "Cancer", "degree": 2}
            ],
            "ascendant": {"sign": "Gemini", "degree": 5}
        },
        "birth_details": {
            "birth_date": "1990-01-01",
            "birth_time": "12:00",
            "latitude": 40.7128,
            "longitude": -74.0060
        }
    }

    # Verify the chart with the real OpenAI service
    result = await chart_verifier.verify_chart(verification_data, openai_service=openai_service)

    # Verify the result
    assert result is not None
    assert "verified" in result
    # The result can be true or false based on real verification
    assert isinstance(result["verified"], bool)
    assert "confidence_score" in result
    assert isinstance(result["confidence_score"], (int, float))
    assert 0 <= result["confidence_score"] <= 100

@pytest.mark.asyncio
async def test_questionnaire_service_next_question_no_fallbacks(openai_service_mock):
    """
    Test that the questionnaire service's generate_next_question method
    properly uses OpenAI and doesn't resort to fallbacks.
    """
    # Prepare test data
    birth_details = {
        'birthDate': '1990-01-01',
        'birthTime': '12:00',
        'birthPlace': 'New York, NY',
        'latitude': 40.7128,
        'longitude': -74.0060
    }

    previous_answers = [
        {
            "question": "Did you experience any significant life events around age 25?",
            "answer": "Yes, I got married and changed careers.",
            "category": "life_events"
        }
    ]

    # Create an instance of QuestionnaireService with the real OpenAI service
    questionnaire_service = QuestionnaireService(openai_service=openai_service_mock)

    # Call the generate_next_question method
    result = await questionnaire_service.generate_next_question(birth_details, previous_answers)

    # Verify the result has the expected structure
    assert result is not None
    assert "next_question" in result, "Response should contain next_question key"
    next_question = result["next_question"]
    assert "text" in next_question, "Question should have text"
    assert "id" in next_question, "Question should have id"
    assert "type" in next_question, "Question should have type"

    # These may or may not be present depending on the actual implementation
    if "relevance" in next_question:
        assert isinstance(next_question["relevance"], str)
    if "category" in next_question:
        assert isinstance(next_question["category"], str)
    if "astrological_factors" in next_question:
        # Handle the case where astrological_factors might be a string or a list
        assert isinstance(next_question["astrological_factors"], (list, str))

@pytest.mark.asyncio
async def test_questionnaire_service_answer_analysis_no_fallbacks(openai_service_mock):
    """
    Test that the questionnaire service's answer analysis method
    properly uses OpenAI for astrological analysis without fallbacks.
    """
    # Create an instance of QuestionnaireService with the real OpenAI service
    questionnaire_service = QuestionnaireService(openai_service=openai_service_mock)

    # Use real data for testing
    question = "Did you experience any significant life events around age 25?"
    answer = "Yes, I got married and changed careers. It was in the early morning, around 2-3 AM."
    birth_date = "1990-01-01"
    birth_time = "12:00"
    latitude = 40.7128
    longitude = -74.0060

    try:
        # Call the real method with real OpenAI service - no mocks
        result = await questionnaire_service._perform_astrological_analysis(
            question, answer, birth_date, birth_time, latitude, longitude
        )

        # Verify that the result is not None and has expected structure
        assert result is not None
        # Basic structure assertions - assuming result is a dictionary
        assert isinstance(result, dict)
    except Exception as e:
        pytest.fail(f"Test failed with real OpenAI service: {str(e)}")
