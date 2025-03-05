"""
Test case for AI Model Integration.
This test verifies that the AI model routing logic works correctly.
"""

import pytest
import os
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# Import the app
from ai_service.main import app

# Create test client
client = TestClient(app)

# Skip tests requiring OpenAI API key if not available
skip_if_no_openai = pytest.mark.skipif(
    os.environ.get("OPENAI_API_KEY") is None and os.environ.get("OPENAI_API_KEY_DEV") is None,
    reason="OpenAI API key not available",
)

class TestAIModelIntegration:
    """Test cases for AI model integration."""

    @skip_if_no_openai
    def test_model_routing_endpoint(self):
        """Test the model routing endpoint with different task types."""

        # Test rectification task routing (should use o1-preview)
        response = client.post(
            "/api/ai/test_model_routing",
            json={"task_type": "rectification", "prompt": "Test prompt for rectification"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "o1-preview"

        # Test explanation task routing (should use gpt-4-turbo)
        response = client.post(
            "/api/ai/test_model_routing",
            json={"task_type": "explanation", "prompt": "Test prompt for explanation"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "gpt-4-turbo"

        # Test auxiliary task routing (should use gpt-4o-mini)
        response = client.post(
            "/api/ai/test_model_routing",
            json={"task_type": "auxiliary", "prompt": "Test prompt for auxiliary task"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] == "gpt-4o-mini"

    @skip_if_no_openai
    def test_usage_statistics_endpoint(self):
        """Test the usage statistics endpoint."""
        response = client.get("/api/ai/usage_statistics")
        assert response.status_code == 200
        data = response.json()
        assert "calls_made" in data
        assert "total_tokens" in data
        assert "estimated_cost" in data

    def test_model_routing_with_mock(self):
        """Test model routing with mocked OpenAI API."""

        # Create a mock response that can be awaited
        async def mock_completion(**kwargs):
            return {
                "content": "Mocked response",
                "model_used": "mock-model",
                "tokens": {"prompt": 10, "completion": 20, "total": 30},
                "cost": 0.001,
                "response_time": 0.5
            }

        # Create a mock for usage statistics
        mock_stats = {
            "calls_made": 1,
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
            "estimated_cost": 0.001
        }

        # Need to patch both in the router and at the service import level
        with patch("ai_service.api.routers.ai_integration_test.OpenAIService") as mock_router_service, \
             patch("ai_service.api.services.openai_service.OpenAIService") as mock_service:

            # Configure the router's mock
            mock_router_instance = mock_router_service.return_value
            mock_router_instance.generate_completion = AsyncMock(side_effect=mock_completion)
            mock_router_instance.get_usage_statistics.return_value = mock_stats

            # Configure the service mock
            mock_instance = mock_service.return_value
            mock_instance.generate_completion = AsyncMock(side_effect=mock_completion)
            mock_instance.get_usage_statistics.return_value = mock_stats

            # Replace the openai_service in the router with our mock
            from ai_service.api.routers import ai_integration_test
            ai_integration_test.openai_service = mock_router_instance

            # Test rectification task
            response = client.post(
                "/api/ai/test_model_routing",
                json={"task_type": "rectification", "prompt": "Test prompt"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"] == "Mocked response"

            # Verify that the model selection was called with rectification
            call_args = mock_router_instance.generate_completion.call_args
            kwargs = call_args[1]  # Get the kwargs
            assert kwargs["task_type"] == "rectification"

            # Reset the router's openai_service to None after test
            ai_integration_test.openai_service = None

if __name__ == "__main__":
    pytest.main(["-v", "test_ai_model_integration.py"])
