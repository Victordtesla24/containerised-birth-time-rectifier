"""
Test script to verify the implementation of session management functionality.
Tests session initialization, status, and data update endpoints.
"""

import requests
import json
import time
import os
import pytest
import uuid
from typing import Dict, Any

# Base URL for API tests
BASE_URL = "http://localhost:8000"

def test_session_initialization():
    """Test that the session initialization endpoint returns a valid session ID."""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/session/init")
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

        data = response.json()
        assert "session_id" in data, "Response does not contain session_id"
        assert isinstance(data["session_id"], str), "session_id is not a string"
        assert len(data["session_id"]) > 0, "session_id is empty"

        # Check for other expected fields
        assert "created_at" in data, "Response does not contain created_at"
        assert "expires_at" in data, "Response does not contain expires_at"
        assert "status" in data, "Response does not contain status"
        assert data["status"] == "active", f"Expected status to be 'active', got '{data['status']}'"

        # Verify that the session ID is a valid UUID
        try:
            uuid_obj = uuid.UUID(data["session_id"])
            assert str(uuid_obj) == data["session_id"], "session_id is not a valid UUID"
        except ValueError:
            pytest.fail("session_id is not a valid UUID format")

        # Verify that created_at is a valid timestamp
        assert isinstance(data["created_at"], (int, float)), "created_at is not a number"
        assert data["created_at"] <= time.time(), "created_at is in the future"

        # Verify that expires_at is a valid timestamp in the future
        assert isinstance(data["expires_at"], (int, float)), "expires_at is not a number"
        assert data["expires_at"] > time.time(), "expires_at is not in the future"

        print(f"Session initialized with ID: {data['session_id']}")
        # Store the session ID for other tests
        global session_id
        session_id = data["session_id"]
    except Exception as e:
        pytest.fail(f"Session initialization failed: {str(e)}")

def test_session_status():
    """Test that the session status endpoint returns the correct status for a valid session."""
    # First, initialize a session if not already done
    if not 'session_id' in globals():
        test_session_initialization()

    try:
        # Now check the session status
        response = requests.get(f"{BASE_URL}/api/v1/session/status", headers={"X-Session-ID": session_id})
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

        data = response.json()
        assert "session_id" in data, "Response does not contain session_id"
        assert data["session_id"] == session_id, f"Expected session_id {session_id}, got {data['session_id']}"
        assert "status" in data, "Response does not contain status"
        assert data["status"] == "active", f"Expected status to be 'active', got '{data['status']}'"

        print(f"Session status checked for ID: {session_id}")
    except Exception as e:
        pytest.fail(f"Session status check failed: {str(e)}")

def test_session_data_update():
    """Test that the session data update endpoint correctly updates session data."""
    # First, initialize a session if not already done
    if not 'session_id' in globals():
        test_session_initialization()

    try:
        # Update session data
        test_data = {
            "test_key": "test_value",
            "test_number": 42,
            "test_bool": True
        }

        response = requests.post(
            f"{BASE_URL}/api/v1/session/data",
            headers={"X-Session-ID": session_id},
            json=test_data
        )
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

        data = response.json()
        assert "status" in data, "Response does not contain status"
        assert data["status"] == "success", f"Expected status to be 'success', got '{data['status']}'"

        print(f"Session data updated for ID: {session_id}")

        # Now check that the data was actually updated
        response = requests.get(f"{BASE_URL}/api/v1/session/data", headers={"X-Session-ID": session_id})
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

        data = response.json()
        for key, value in test_data.items():
            assert key in data, f"Response does not contain {key}"
            assert data[key] == value, f"Expected {key} to be {value}, got {data[key]}"

        print(f"Session data verified for ID: {session_id}")
    except Exception as e:
        pytest.fail(f"Session data update failed: {str(e)}")

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
        test_session_initialization()
        print("✅ Session initialization successful")

        # Test session status
        print("Testing session status...")
        test_session_status()
        print("✅ Session status check successful")

        # Test session data update
        print("Testing session data update...")
        test_session_data_update()
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
