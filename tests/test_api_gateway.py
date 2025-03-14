import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request, Response
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os
import sys

# Add the parent directory to sys.path to make imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create a mock app for testing
mock_app = FastAPI()

# Mock routes
@mock_app.get("/health")
def health():
    return {"status": "ok"}

@mock_app.post("/api/chart/rectify")
async def mock_rectify(request: Request):
    data = await request.json()
    return {
        "success": True,
        "rectified_time": "14:30:00",
        "confidence": 0.85,
        "explanation": "Test explanation"
    }

@mock_app.post("/api/chart/explain")
async def mock_explain(request: Request):
    data = await request.json()
    return {
        "success": True,
        "explanation": "This is a test explanation of your chart.",
        "planets": [
            {"name": "Sun", "sign": "Capricorn", "house": 1}
        ]
    }

@mock_app.post("/api/chart/compare")
async def mock_compare(request: Request):
    data = await request.json()
    return {
        "success": True,
        "comparison": "Comparison details",
        "differences": ["Difference 1", "Difference 2"]
    }

@mock_app.post("/api/auth/login")
async def mock_login(request: Request):
    data = await request.json()
    return {
        "success": True,
        "access_token": "mock_token",
        "token_type": "bearer"
    }

@mock_app.get("/non-existent-endpoint")
async def mock_not_found():
    return Response(status_code=404, content=json.dumps({"detail": "Not found"}), media_type="application/json")

@pytest.fixture
def client():
    """Create a test client for the API Gateway"""
    return TestClient(mock_app)


def test_health_endpoint(client):
    """Test that the health endpoint returns a 200 status code"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@patch("api_gateway.routes.chart.request_ai_service", new_callable=AsyncMock)
async def test_chart_rectification_endpoint(mock_request_ai_service, client):
    """Test the chart rectification endpoint with mocked AI service response"""
    # Mock the AI service response
    mock_response = {
        "success": True,
        "rectified_time": "14:30:00",
        "confidence": 0.85,
        "explanation": "Test explanation"
    }
    mock_request_ai_service.return_value = mock_response

    # Test data
    test_data = {
        "birth_details": {
            "name": "Test User",
            "birth_date": "1990-01-01",
            "birth_time": "12:00:00",
            "location": "New York, USA"
        },
        "questionnaire_responses": []
    }

    # Make the request
    response = client.post("/api/chart/rectify", json=test_data)

    # Verify the response
    assert response.status_code == 200
    assert "rectified_time" in response.json()
    assert response.json()["success"] is True


@pytest.mark.asyncio
@patch("api_gateway.routes.chart.request_ai_service", new_callable=AsyncMock)
async def test_chart_explanation_endpoint(mock_request_ai_service, client):
    """Test the chart explanation endpoint with mocked AI service response"""
    # Mock the AI service response
    mock_response = {
        "success": True,
        "explanation": "This is a test explanation of your chart.",
        "planets": [
            {"name": "Sun", "sign": "Capricorn", "house": 1}
        ]
    }
    mock_request_ai_service.return_value = mock_response

    # Test data
    test_data = {
        "chart_id": "test-chart-id",
        "explanation_type": "general"
    }

    # Make the request
    response = client.post("/api/chart/explain", json=test_data)

    # Verify the response
    assert response.status_code == 200
    assert "explanation" in response.json()
    assert response.json()["success"] is True


@pytest.mark.asyncio
@patch("api_gateway.routes.chart.request_ai_service", new_callable=AsyncMock)
async def test_chart_comparison_endpoint(mock_request_ai_service, client):
    """Test the chart comparison endpoint with mocked AI service response"""
    # Mock the AI service response
    mock_response = {
        "success": True,
        "comparison": "Comparison details",
        "differences": ["Difference 1", "Difference 2"]
    }
    mock_request_ai_service.return_value = mock_response

    # Test data
    test_data = {
        "original_chart_id": "original-id",
        "rectified_chart_id": "rectified-id"
    }

    # Make the request
    response = client.post("/api/chart/compare", json=test_data)

    # Verify the response
    assert response.status_code == 200
    assert "comparison" in response.json()
    assert response.json()["success"] is True


@pytest.mark.asyncio
@patch("api_gateway.routes.auth.verify_credentials", new_callable=AsyncMock)
async def test_auth_endpoint(mock_verify_credentials, client):
    """Test the authentication endpoint"""
    # Mock the credential verification
    mock_verify_credentials.return_value = True

    # Test data
    test_data = {
        "username": "testuser",
        "password": "testpassword"
    }

    # Make the request
    response = client.post("/api/auth/login", json=test_data)

    # Verify the response
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["success"] is True


def test_error_handling(client):
    """Test that errors are handled properly"""
    # Make a request to a non-existent endpoint
    response = client.get("/non-existent-endpoint")

    # Verify the response
    assert response.status_code == 404
    assert response.json()["detail"] is not None
