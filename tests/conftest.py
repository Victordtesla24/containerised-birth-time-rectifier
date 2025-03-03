"""
Pytest configuration for Birth Time Rectifier tests.
Contains fixtures and setup for all test suites.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
import logging
from datetime import datetime

# Add the root directory to the path so we can import from the ai_service module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the FastAPI app
from ai_service.main import app

# Set up logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test-birth-time-rectifier")

# Create fixtures for testing
@pytest.fixture(scope="module")
def test_client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="session")
def sample_birth_data():
    """Provide sample birth data for testing."""
    return {
        "birthDate": "1990-01-01",
        "birthTime": "12:00",
        "birthPlace": "New York, NY",
        "latitude": 40.7128,
        "longitude": -74.0060
    }

@pytest.fixture(scope="session")
def sample_chart_data():
    """Provide sample chart data for testing."""
    return {
        "ascendant": {"sign": "Taurus", "degree": 15.5},
        "planets": [
            {
                "planet": "Sun",
                "sign": "Capricorn",
                "degree": "10.5",
                "house": 9
            },
            {
                "planet": "Moon",
                "sign": "Virgo",
                "degree": "25.3",
                "house": 5
            }
        ],
        "houses": [
            {
                "number": 1,
                "sign": "Taurus",
                "startDegree": 15.5,
                "endDegree": 45.5
            }
        ]
    }

@pytest.fixture(scope="function")
def test_session_id():
    """Generate a unique session ID for testing."""
    return f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}"
