"""
Integration tests for the health check application mounting in the main application.

These tests verify that the health app is properly mounted in the main application
and that requests to health endpoints bypass the middleware chain.
"""

import pytest
import importlib
from fastapi.testclient import TestClient

# Dynamically import the main app to ensure we're testing what's actually running
try:
    main_module = importlib.import_module("ai_service.main")
    app = main_module.app
except ImportError:
    pytest.skip("Could not import ai_service.main module")

# Create a test client for the main application
client = TestClient(app)

# Test all mounted health paths
HEALTH_PATHS = [
    "/health",
    "/api/v1/health",
    "/system/health",
]

@pytest.mark.parametrize("path", HEALTH_PATHS)
def test_health_endpoint_mounted(path):
    """Test that all health endpoints are properly mounted and return 200 OK."""
    response = client.get(path)

    # Check status code
    assert response.status_code == 200, f"Health endpoint {path} returned {response.status_code} instead of 200"

    # Check response body
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "ai_service"
    assert data["middleware_bypassed"] is True

def test_health_endpoints_bypass_middleware():
    """
    Test that health endpoints bypass middleware.

    If middleware is properly bypassed, there should be no 500 errors
    even if the same middleware is causing errors on other endpoints.
    """
    # First, make sure health works
    response = client.get("/health")
    assert response.status_code == 200

    # We can't directly test that middleware is bypassed in an automated test,
    # but we can check that the middleware_bypassed flag is set in the response
    data = response.json()
    assert data["middleware_bypassed"] is True

def test_readiness_endpoint_mounted():
    """Test that the readiness endpoint is properly mounted and works."""
    for path in HEALTH_PATHS:
        readiness_path = f"{path}/readiness"
        response = client.get(readiness_path)

        # Check status code
        assert response.status_code == 200, f"Readiness endpoint {readiness_path} returned {response.status_code} instead of 200"

        # Check response body
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data
        assert data["service"] == "ai_service"

def test_liveness_endpoint_mounted():
    """Test that the liveness endpoint is properly mounted and works."""
    for path in HEALTH_PATHS:
        liveness_path = f"{path}/liveness"
        response = client.get(liveness_path)

        # Check status code
        assert response.status_code == 200, f"Liveness endpoint {liveness_path} returned {response.status_code} instead of 200"

        # Check response body
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert data["service"] == "ai_service"

def test_docs_available():
    """Test that API docs are available for the mounted application."""
    for path in HEALTH_PATHS:
        docs_path = f"{path}/docs"
        response = client.get(docs_path)

        # The docs endpoint should return 200 even when mounted
        assert response.status_code == 200, f"Docs endpoint {docs_path} returned {response.status_code} instead of 200"

        # The response should be HTML for the Swagger UI
        assert "text/html" in response.headers["content-type"]
        assert "swagger" in response.text.lower()

def test_openapi_schema_available():
    """Test that OpenAPI schema is available for the mounted application."""
    for path in HEALTH_PATHS:
        openapi_path = f"{path}/openapi.json"
        response = client.get(openapi_path)

        # The OpenAPI endpoint should return 200 even when mounted
        assert response.status_code == 200, f"OpenAPI endpoint {openapi_path} returned {response.status_code} instead of 200"

        # The response should be JSON for the OpenAPI schema
        assert response.headers["content-type"] == "application/json"

        # Check some keys in the schema
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

        # The schema should contain the health paths
        assert "/" in schema["paths"]
        assert "/readiness" in schema["paths"]
        assert "/liveness" in schema["paths"]

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
