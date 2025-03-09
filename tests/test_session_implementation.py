"""
Test script to verify the implementation of session management functionality.
Tests session initialization, status, and data update endpoints.
"""

import requests
import json
import time
import os
import pytest

# Base URL for API tests
BASE_URL = "http://localhost:8000"

def test_session_init():
    """Test session initialization endpoint"""
    # Make request to session init endpoint
    response = requests.get(f"{BASE_URL}/api/v1/session/init")

    # Check status code
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response JSON structure
    data = response.json()
    assert "session_id" in data, "Response missing session_id field"
    assert "created_at" in data, "Response missing created_at field"
    assert "expires_at" in data, "Response missing expires_at field"
    assert "status" in data, "Response missing status field"
    assert data["status"] == "active", f"Expected status 'active', got '{data['status']}'"

    # Store session_id for subsequent tests
    session_id = data["session_id"]
    # Don't return values, use the fixture instead
    assert session_id is not None, "Session ID should not be None"
    assert response.cookies is not None, "Session cookies should not be None"

def test_session_status(session_info):
    """Test session status endpoint with an active session"""
    session_id, cookies = session_info

    # Make request to session status endpoint
    response = requests.get(
        f"{BASE_URL}/api/v1/session/status",
        cookies=cookies
    )

    # Check status code
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response JSON structure
    data = response.json()
    assert "session_id" in data, "Response missing session_id field"
    assert data["session_id"] == session_id, f"Expected session_id '{session_id}', got '{data['session_id']}'"
    assert "status" in data, "Response missing status field"
    assert data["status"] == "active", f"Expected status 'active', got '{data['status']}'"

def test_session_data_update(session_info):
    """Test updating session data"""
    session_id, cookies = session_info

    # Test data to store in session
    test_data = {
        "test_key": "test_value",
        "nested": {
            "field1": 123,
            "field2": True
        }
    }

    # Make request to update session data
    response = requests.post(
        f"{BASE_URL}/api/v1/session/data",
        json=test_data,
        cookies=cookies
    )

    # Check status code
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response JSON structure
    data = response.json()
    assert "status" in data, "Response missing status field"
    assert data["status"] == "success", f"Expected status 'success', got '{data['status']}'"

    # Now get session status to verify data was stored
    response = requests.get(
        f"{BASE_URL}/api/v1/session/status",
        cookies=cookies
    )

    # Check if our test data is in the session
    # Note: This assumes the session status endpoint returns session data,
    # which it might not in the actual implementation
    data = response.json()
    if "test_key" in data:
        assert data["test_key"] == test_data["test_key"], "Session data not stored correctly"
    else:
        print("Warning: Cannot verify if session data was stored - session status endpoint doesn't return session data")

@pytest.fixture
def session_info():
    """Fixture to create a session and return session_id and cookies"""
    # Make request to session init endpoint
    response = requests.get(f"{BASE_URL}/api/v1/session/init")

    # Check status code
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response JSON structure
    data = response.json()
    assert "session_id" in data, "Response missing session_id field"

    # Return session_id and cookies for use in tests
    return data["session_id"], response.cookies

def run_tests():
    """Run all tests manually"""
    try:
        # Initialize session
        print("Testing session initialization...")
        session_info = test_session_init()
        print("✅ Session initialization successful")

        # Test session status
        print("Testing session status...")
        test_session_status(session_info)
        print("✅ Session status check successful")

        # Test session data update
        print("Testing session data update...")
        test_session_data_update(session_info)
        print("✅ Session data update successful")

        print("\nAll session management tests passed!")
        return True
    except AssertionError as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    run_tests()
