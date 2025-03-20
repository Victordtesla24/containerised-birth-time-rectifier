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
        assert service.client is not None
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
        gpt4_cost = service._calculate_cost("gpt-4-turbo-preview", 100, 50)
        gpt3_cost = service._calculate_cost("gpt-3.5-turbo", 100, 50)

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
