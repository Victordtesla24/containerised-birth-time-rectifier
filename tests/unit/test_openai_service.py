"""
Unit tests for OpenAIService.

This module demonstrates proper testing with dependency injection.
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
try:
    from ai_service.api.services.openai.service import OpenAIService, get_openai_service
except ImportError:
    logger.warning("OpenAI service module not found, tests will be skipped")
    pytest.skip("OpenAI service module not found", allow_module_level=True)


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
    with pytest.raises(ValueError) as excinfo:
        await service.generate_completion(
            prompt="Error test",
            task_type="test"
        )

    # Verify the error message
    assert "Error generating completion" in str(excinfo.value)
    assert "Test error" in str(excinfo.value)
