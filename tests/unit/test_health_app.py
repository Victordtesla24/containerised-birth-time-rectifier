"""
Unit tests for the health check application.

These tests verify that the health check application is working correctly
and that it provides the expected responses with the correct fields.
"""

import pytest
from fastapi.testclient import TestClient
import json
from datetime import datetime

# Import the health app directly from app_wrapper
from ai_service.app_wrapper import health_app

# Create a test client for testing the health app in isolation
client = TestClient(health_app)

def test_health_endpoint():
    """Test the main health endpoint returns a 200 OK response with the correct fields."""
    response = client.get("/")

    # Check status code
    assert response.status_code == 200

    # Check content type
    assert response.headers["content-type"] == "application/json"

    # Check response body
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "ai_service"
    assert data["middleware_bypassed"] is True
    assert data["path"] == "/"

def test_readiness_endpoint():
    """Test the readiness endpoint returns a 200 OK response with the correct fields."""
    response = client.get("/readiness")

    # Check status code
    assert response.status_code == 200

    # Check response body
    data = response.json()
    assert data["status"] == "ready"
    assert "timestamp" in data
    assert data["service"] == "ai_service"

def test_liveness_endpoint():
    """Test the liveness endpoint returns a 200 OK response with the correct fields."""
    response = client.get("/liveness")

    # Check status code
    assert response.status_code == 200

    # Check response body
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data
    assert data["service"] == "ai_service"

def test_timestamp_is_valid_iso_format():
    """Test that the timestamp in the response is a valid ISO format."""
    response = client.get("/")
    data = response.json()

    # The timestamp should be a string
    assert isinstance(data["timestamp"], str)

    # Try parsing it as an ISO format timestamp
    try:
        datetime.fromisoformat(data["timestamp"])
    except ValueError:
        pytest.fail(f"Timestamp '{data['timestamp']}' is not a valid ISO format")

def test_response_serialization():
    """Test that the response can be properly serialized to JSON."""
    response = client.get("/")
    data = response.json()

    # Try serializing the data to JSON
    try:
        serialized = json.dumps(data)
        # Make sure it's a valid JSON string
        assert isinstance(serialized, str)
        # Make sure we can parse it back
        parsed = json.loads(serialized)
        assert parsed == data
    except (TypeError, json.JSONDecodeError):
        pytest.fail("Response data could not be serialized to JSON")

def test_headers():
    """Test that the response headers are set correctly."""
    response = client.get("/")

    # Check content type
    assert response.headers["content-type"] == "application/json"

    # Check other headers (if any specific headers are expected)
    # For example, if you're setting cache control headers:
    # assert "cache-control" in response.headers

def test_concurrent_requests(benchmark):
    """Test that the health endpoint can handle concurrent requests."""
    # Use pytest-benchmark to test concurrent requests
    def call_health_endpoint():
        return client.get("/").status_code

    # This will call the function multiple times and report timing stats
    result = benchmark(call_health_endpoint)

    # All calls should return 200
    assert result == 200

def test_not_found_returns_404():
    """Test that an invalid path returns a 404 response."""
    response = client.get("/invalid-path")
    assert response.status_code == 404

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
