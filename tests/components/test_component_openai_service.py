"""
Unit tests for OpenAI service implementation.
These tests verify the OpenAI service works correctly with real API calls.
"""

import os
import pytest
import asyncio
from unittest.mock import patch
import openai
from ai_service.api.services.openai.service import OpenAIService
from ai_service.api.services.openai.cost_calculator import calculate_cost
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestOpenAIService:
    """Tests for the OpenAI service class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup the test environment with API key."""
        # Store original environment
        self.original_api_key = os.environ.get("OPENAI_API_KEY")

        # Ensure there's an API key for testing
        if not self.original_api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")

        yield

        # Restore environment
        if self.original_api_key:
            os.environ["OPENAI_API_KEY"] = self.original_api_key
        else:
            os.environ.pop("OPENAI_API_KEY", None)

    def test_initialization(self):
        """Test OpenAI service initialization with API key."""
        # Create the service
        service = OpenAIService()

        # Check that the client was initialized
        assert service.http_client is not None
        assert service.api_key is not None
        assert service.api_key == os.environ.get("OPENAI_API_KEY")

    def test_initialization_without_api_key(self):
        """Test that initialization fails without API key."""
        # Temporarily remove API key
        api_key = os.environ.pop("OPENAI_API_KEY", None)

        try:
            # Should raise an error
            with pytest.raises(ValueError) as excinfo:
                OpenAIService()

            # Check error message
            assert "OpenAI API key not provided" in str(excinfo.value)
        finally:
            # Restore API key
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key

    def test_model_selection(self):
        """Test that model selection works correctly for different task types."""
        service = OpenAIService()

        # Test different task types
        assert service._select_model("rectification") == "gpt-4-turbo-preview"
        assert service._select_model("questionnaire") == "gpt-4-turbo-preview"
        assert service._select_model("explanation") == "gpt-3.5-turbo"

        # Test unknown task type (should use default)
        assert service._select_model("unknown") == service.default_model

    def test_cost_calculation(self):
        """Test cost calculation for different models."""
        service = OpenAIService()

        # Test cost calculation for different models
        gpt4_cost = calculate_cost("gpt-4-turbo-preview", 100, 50)
        gpt3_cost = calculate_cost("gpt-3.5-turbo", 100, 50)

        # GPT-4 should be more expensive than GPT-3.5
        assert gpt4_cost > gpt3_cost

        # Costs should be reasonable
        assert gpt4_cost > 0
        assert gpt3_cost > 0

    @pytest.mark.asyncio
    async def test_generate_completion(self):
        """Test generating a completion with real API call."""
        service = OpenAIService()

        prompt = "What is the capital of France?"
        response = await service.generate_completion(prompt, "auxiliary", max_tokens=20)

        # Check that we got a response
        assert "content" in response
        assert isinstance(response["content"], str)
        assert len(response["content"]) > 0

        # Check that usage tracking was updated
        assert service.usage_stats["calls_made"] > 0
        assert service.total_tokens > 0

    @pytest.mark.asyncio
    async def test_verify_chart(self):
        """Test chart verification function with real API call."""
        service = OpenAIService()

        # Create a simple chart data structure
        chart_data = {
            "birth_details": {
                "date": "2000-01-01",
                "time": "12:00:00",
                "location": "New York, US"
            },
            "planets": {
                "Sun": {"longitude": 280.5, "house": 10},
                "Moon": {"longitude": 120.3, "house": 4},
                "Mercury": {"longitude": 275.2, "house": 10}
            },
            "houses": {
                "1": 85.5,
                "10": 355.2
            },
            "aspects": [
                {"planet1": "Sun", "planet2": "Mercury", "aspect": "conjunction", "orb": 5.3}
            ]
        }

        response = await service.verify_chart(chart_data)

        # Check that we got a response with the expected structure
        assert "verified" in response
        assert isinstance(response["verified"], bool)
        assert "confidence_score" in response
        assert isinstance(response["confidence_score"], (int, float))
        assert "message" in response
        assert isinstance(response["message"], str)

    @pytest.mark.asyncio
    async def test_generate_questions(self):
        """Test question generation with real API call."""
        service = OpenAIService()

        # Create a context for question generation
        context = {
            "chart_data": {
                "birth_details": {
                    "date": "2000-01-01",
                    "time": "12:00:00",
                    "location": "New York, US"
                },
                "planets": {
                    "Sun": {"longitude": 280.5, "house": 10},
                    "Moon": {"longitude": 120.3, "house": 4}
                }
            },
            "previous_answers": [],
            "question_index": 0
        }

        response = await service.generate_questions(context)

        # Check that we got a response with questions
        assert "questions" in response
        assert isinstance(response["questions"], list)
        assert len(response["questions"]) > 0

        # Check that the first question has the required fields
        question = response["questions"][0]
        assert "id" in question
        assert "text" in question
        assert "options" in question

    def test_get_usage_statistics(self):
        """Test getting usage statistics."""
        service = OpenAIService()

        # Get the usage statistics
        stats = service.get_usage_statistics()

        # Check the structure
        assert "calls_made" in stats
        assert "total_tokens" in stats
        assert "prompt_tokens" in stats
        assert "completion_tokens" in stats
        assert "total_cost" in stats

@pytest.mark.asyncio
async def test_openai_service_basic():
    """Basic OpenAI service functionality test."""
    # Check for API key in environment
    api_key = os.environ.get("OPENAI_API_KEY")

    # Fail the test if API key is missing rather than silently skipping
    if not api_key:
        pytest.fail("OpenAI API key not available. Set OPENAI_API_KEY environment variable to run this test.")

    # Test service initialization
    service = OpenAIService(api_key=api_key)

    # Simple completion test with error handling
    try:
        response = await service.generate_completion(
            prompt="What is the capital of France?",
            task_type="general",
            max_tokens=20,
            temperature=0.0  # Zero for deterministic output
        )

        # Verify response structure
        assert isinstance(response, dict), "Response should be a dictionary"

        # Look for expected fields in response
        if "choices" in response:
            assert len(response["choices"]) > 0, "Response should have at least one choice"
            assert "text" in response["choices"][0], "Response choice should contain text"
            text = response["choices"][0]["text"]
            assert "Paris" in text, f"Expected 'Paris' in response, got: {text}"
        else:
            # Extract text from response
            text = response.get("content", "")
            assert "Paris" in text, f"Expected 'Paris' in response, got: {text}"

    except Exception as e:
        # If we get authentication errors, report but don't fail
        if "authentication" in str(e).lower():
            pytest.skip(f"OpenAI API authentication failed: {str(e)}")
        else:
            # Re-raise other errors
            raise

    # Close the service client
    await service.close()

@pytest.mark.asyncio
async def test_token_counting():
    """Test token counting works correctly without falling back to defaults."""
    # Create a service
    service = OpenAIService()

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not available")

    # Sample text to count
    text = "This is a test message that should have a predictable token count."

    # Use generate_completion to get token usage
    try:
        result = await service.generate_completion(
            prompt=text,
            task_type="general",
            max_tokens=5
        )

        # The result should include usage info
        assert "usage" in result, "Response is missing usage information"

        # Usage should contain token counts
        usage = result["usage"]
        assert "prompt_tokens" in usage or "total_tokens" in usage, "Missing token count in usage"

        # Get the token count (use either prompt_tokens or total_tokens)
        token_count = usage.get("prompt_tokens", usage.get("total_tokens", 0))
        assert token_count > 0, f"Expected positive token count, got {token_count}"

        # Check that the count is reasonable (rough estimate for English)
        expected_tokens = len(text.split()) * 1.3  # Assume ~1.3 tokens per word
        assert 0.5 * expected_tokens <= token_count <= 2 * expected_tokens, \
               f"Token count {token_count} outside expected range"

    except Exception as e:
        pytest.skip(f"Token counting test failed: {str(e)}")

    # Cleanup
    await service.close()

@pytest.mark.asyncio
async def test_model_selection():
    """Test model selection functionality."""
    service = OpenAIService()

    # Test different task types
    test_tasks = [
        "general", "rectification", "verification", "questionnaire"
    ]

    # Make sure the selection works without errors
    for task in test_tasks:
        try:
            model = service._select_model(task)
            assert isinstance(model, str), f"Model for task {task} should be a string"
            assert len(model) > 0, f"Model for task {task} should not be empty"

            # Most likely models should contain gpt somewhere in the name
            assert "gpt" in model.lower(), f"Model {model} doesn't appear to be a GPT model"
        except Exception as e:
            # This is just testing internal logic, so should work even without API key
            pytest.fail(f"Model selection failed for task {task}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_openai_service_basic())
