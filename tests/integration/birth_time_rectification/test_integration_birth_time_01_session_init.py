"""
Integration test for session initialization.
Tests the session initialization endpoint to ensure it returns a valid session ID.
"""

import os
import json
import pytest
import logging
from pathlib import Path
from tests.utils.test_helpers import get_test_sequence, update_test_sequence, reset_test_sequence
from tests.utils.simple_api_client import SimpleAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_session_init")

# Test configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

@pytest.fixture(scope="module", autouse=True)
def initialize_test_sequence():
    """Initialize the test sequence for the session initialization test."""
    # Always reset the test sequence at the beginning of this test
    reset_test_sequence()
    logger.info("Test sequence reset")
    yield

def test_session_initialization():
    """Test that a session can be initialized correctly."""
    # Get the fresh test sequence
    test_sequence = get_test_sequence()

    # Reset the test sequence
    reset_test_sequence()
    logger.info("Test sequence reset")

    # Initialize a new test sequence
    test_sequence = {}

    logger.info("Starting session initialization test")

    # Create API client - Use the localhost address when running in the same container
    api_client = SimpleAPIClient(base_url=API_BASE_URL)

    # Call the session initialization endpoint
    response = api_client.get("/api/v1/session/init")

    # Verify response
    assert response.status_code == 200, f"Session initialization failed with status {response.status_code}: {response.text}"

    # Parse response JSON
    session_data = response.json()

    # Verify response has required fields
    assert "session_id" in session_data, "Session initialization response missing session_id"
    assert "status" in session_data, "Session initialization response missing status"
    assert session_data["status"] == "success", f"Session initialization status not 'success': {session_data['status']}"

    session_id = session_data["session_id"]
    logger.info(f"Session initialized with ID: {session_id}")

    # Update test sequence with session info and persist to disk
    test_sequence.update({
        "session_id": session_id,
        "test_stage": 1
    })
    update_test_sequence(test_sequence)

    # Verify test sequence was updated
    updated_sequence = get_test_sequence()
    assert updated_sequence["session_id"] == session_id, "Session ID not correctly stored in test sequence"
    assert updated_sequence["test_stage"] == 1, "Test stage not correctly updated in test sequence"

    logger.info(f"Session initialization test completed successfully")

if __name__ == "__main__":
    # Run this test standalone for debugging
    initialize_test_sequence()
    test_session_initialization()
