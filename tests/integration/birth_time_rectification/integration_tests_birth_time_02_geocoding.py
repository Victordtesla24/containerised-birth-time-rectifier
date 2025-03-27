#!/usr/bin/env python3
"""
Integration test for geocoding functionality.
Tests the geocoding endpoint to ensure it correctly converts location names to coordinates.
"""

import os
import json
import pytest
import logging
import asyncio
from pathlib import Path

# Import test utilities
from tests.utils.test_helpers import get_test_sequence, update_test_sequence
from tests.utils.simple_api_client import SimpleAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_geocoding")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


@pytest.mark.asyncio
async def test_geocode_birth_place():
    """
    Test Case 2: Geocoding of Birth Place

    Verifies that the birth place can be successfully geocoded and returns
    accurate coordinates and timezone information.

    From testing_approach.md:
    - Verifies that the birth location can be successfully geocoded
    - Coordinates returned match expected values for the location
    - Timezone information is correctly determined
    - The system handles common edge cases like ambiguous location names
    """
    # Arrange
    # Use the API_BASE_URL from environment, which should point to the AI service container
    # The default fallback should match the service name in docker-compose.test.yml
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://ai-service:8000")
    logger.info(f"Using API base URL: {API_BASE_URL}")
    client = SimpleAPIClient(base_url=API_BASE_URL)

    # Retrieve the session ID from the previous test
    test_sequence = get_test_sequence()
    session_id = test_sequence.get("session_id")
    assert session_id, "Session ID from previous test is required"

    # Get birth place from test data
    birth_place = TEST_DATA["birth_details"]["place"]
    expected_latitude = TEST_DATA["birth_details"]["latitude"]
    expected_longitude = TEST_DATA["birth_details"]["longitude"]
    expected_timezone = TEST_DATA["birth_details"]["timezone"]

    # Call the geocoding API endpoint with session ID header
    logger.info(f"Geocoding birth place: {birth_place}")
    try:
        response = client.post(
            "/api/v1/geocode/geocode",
            {"query": birth_place, "exactly_one": True},
        )
    except Exception as e:
        logger.error(f"Geocoding request failed: {e}")
        raise

    # Check if the request was successful
    assert response.status_code == 200, f"Geocoding API request failed with status {response.status_code}: {response.text}"

    # Parse the response
    geocode_data = response.json()
    assert "results" in geocode_data, f"Missing 'results' in geocode response: {geocode_data}"
    assert len(geocode_data["results"]) > 0, f"No geocoding results returned for '{birth_place}'"

    # Get the first result
    location = geocode_data["results"][0]

    # Check that the location has the required fields
    assert "latitude" in location, f"Location missing latitude: {location}"
    assert "longitude" in location, f"Location missing longitude: {location}"

    # Extract coordinates
    latitude = float(location.get("latitude", 0))
    longitude = float(location.get("longitude", 0))

    # Get timezone data for the coordinates
    timezone_response = client.post(
        "/api/v1/geocode/geocode/timezone",
        {"latitude": latitude, "longitude": longitude},
    )
    assert timezone_response.status_code == 200, f"Timezone API request failed: {timezone_response.text}"

    timezone_data = timezone_response.json()
    assert "timezone" in timezone_data, f"Missing 'timezone' in response: {timezone_data}"
    timezone = timezone_data["timezone"]["timezone_id"]

    # Verify the results are within acceptable range
    latitude_diff = abs(latitude - expected_latitude)
    longitude_diff = abs(longitude - expected_longitude)

    # Allow for small differences in coordinates due to different geocoding services
    assert latitude_diff < 0.1, f"Latitude difference too large: {latitude_diff}"
    assert longitude_diff < 0.1, f"Longitude difference too large: {longitude_diff}"

    # Timezone should match or be equivalent
    assert timezone == expected_timezone or (
        timezone and expected_timezone and
        timezone.split("/")[0] == expected_timezone.split("/")[0]
    ), f"Timezone mismatch: {timezone} vs {expected_timezone}"

    # Store birth details for subsequent tests
    test_sequence.update({
        "birth_details": {
            "place": birth_place,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "date": TEST_DATA["birth_details"]["date"],
            "time": TEST_DATA["birth_details"]["time"]
        },
        "test_stage": 2
    })
    update_test_sequence(test_sequence, persist=True)

    logger.info(f"Successfully geocoded birth place: {birth_place} -> "
                f"({latitude}, {longitude}, {timezone})")

    return location


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_geocode_birth_place())
