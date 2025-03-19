import pytest
import requests
import os
import logging
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API URL from environment or use default
API_URL = os.environ.get("API_URL", "http://localhost:9000")

def get_url(path):
    """Helper to build URLs with proper joining"""
    return urljoin(API_URL, path)

@pytest.fixture
def session_id():
    """Create a session for testing"""
    try:
        response = requests.get(get_url("/api/v1/session/init"))
        if response.status_code == 200:
            data = response.json()
            return data.get("session_id")
        else:
            logger.warning(f"Failed to initialize session: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error initializing session: {str(e)}")
        return None

def test_api_gateway_health():
    """Test the health endpoint"""
    response = requests.get(get_url("/health"))
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") in ["ok", "healthy"], f"Expected status to be 'ok' or 'healthy', got '{data.get('status')}'"

def test_api_gateway_routing():
    """Test API gateway routing to underlying services"""
    # Test routing to AI service health
    response = requests.get(get_url("/api/v1/health"))
    assert response.status_code == 200

    # Test routing to nonexistent endpoint (should return 404)
    response = requests.get(get_url("/api/v1/nonexistent-endpoint"))
    assert response.status_code == 404

def test_session_initialization():
    """Test session initialization endpoint"""
    response = requests.get(get_url("/api/v1/session/init"))
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data.get("status") == "active"

def test_api_gateway_error_handling(session_id):
    """Test API gateway error handling"""
    if not session_id:
        pytest.skip("Session ID not available")

    # Test with malformed JSON
    headers = {"X-Session-ID": session_id, "Content-Type": "application/json"}
    response = requests.post(
        get_url("/api/v1/chart/generate"),
        data="invalid json",
        headers=headers
    )
    assert response.status_code in [400, 422]  # Either 400 Bad Request or 422 Unprocessable Entity

if __name__ == "__main__":
    # For running the test directly
    test_api_gateway_health()
    test_api_gateway_routing()
    test_session_initialization()
    session = session_id()
    if session:
        test_api_gateway_error_handling(session)
    print("All tests completed successfully!")
