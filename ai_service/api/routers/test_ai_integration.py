import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any
import json

# Import the router to test
from ai_service.api.routers.ai_integration_test import router

# Configure client for testing
client = TestClient(router)

@pytest.fixture
def model_routing_data():
    """Fixture to provide sample data for model routing tests."""
    return {
        "task_type": "explanation",
        "prompt": "This is a test prompt for model routing.",
        "temperature": 0.7,
        "max_tokens": 50
    }

@pytest.fixture
def explanation_data():
    """Fixture to provide sample data for explanation generation tests."""
    return {
        "adjustment_minutes": 15,
        "reliability": "medium",
        "questionnaire_data": {"responses": []}
    }

@pytest.fixture
def rectification_data():
    """Fixture to provide sample data for rectification tests."""
    return {
        "birth_details": {
            "birth_date": "1990-01-01",
            "birth_time": "12:00:00",
            "location": "New York, USA",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timezone": "America/New_York"
        },
        "questionnaire_data": {"responses": []},
        "chart_data": None
    }

# Mock the OpenAI service for testing
@pytest.fixture(autouse=True)
def mock_openai_service(monkeypatch):
    """Mock the OpenAI service for testing."""
    class MockOpenAIService:
        async def generate_completion(self, **kwargs):
            return {
                "model_used": "gpt-4-mock",
                "content": "This is a mock response from the OpenAI service.",
                "tokens": 10,
                "cost": 0.0,
                "response_time": 0.1
            }

        def get_usage_statistics(self):
            return {
                "calls_made": 1,
                "total_tokens": 10,
                "estimated_cost": 0.0
            }

    # Apply the mock
    monkeypatch.setattr("ai_service.api.routers.ai_integration_test.openai_service", MockOpenAIService())

# Mock the Rectification model for testing
@pytest.fixture(autouse=True)
def mock_rectification_model(monkeypatch):
    """Mock the Rectification model for testing."""
    class MockRectificationModel:
        async def _generate_explanation(self, **kwargs):
            return "This is a mock explanation from the rectification model."

        async def rectify_birth_time(self, **kwargs):
            return {
                "original_time": "12:00:00",
                "rectified_time": "12:15:00",
                "adjustment_minutes": 15,
                "confidence": 85,
                "explanation": "This is a mock rectification explanation."
            }

    # Apply the mock
    monkeypatch.setattr("ai_service.api.routers.ai_integration_test.rectification_model", MockRectificationModel())

# Test functions
def test_model_routing(model_routing_data):
    """Test the model routing endpoint."""
    # Convert pytest fixture to JSON
    response = client.post("/test_model_routing", json=model_routing_data)

    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "model_used" in result
    assert "result" in result
    assert "token_usage" in result
    assert "cost" in result

def test_explanation_generation(explanation_data):
    """Test the explanation generation endpoint."""
    # Convert pytest fixture to JSON
    response = client.post("/test_explanation", json=explanation_data)

    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "explanation" in result
    assert "parameters" in result
    assert "adjustment_minutes" in result["parameters"]
    assert "reliability" in result["parameters"]

def test_rectification(rectification_data):
    """Test the rectification endpoint."""
    # Convert pytest fixture to JSON
    response = client.post("/test_rectification", json=rectification_data)

    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "original_time" in result
    assert "rectified_time" in result
    assert "adjustment_minutes" in result
    assert "confidence" in result
    assert "explanation" in result

def test_usage_statistics():
    """Test the usage statistics endpoint."""
    response = client.get("/usage_statistics")

    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "calls_made" in result
    assert "total_tokens" in result
    assert "estimated_cost" in result
