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
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data_source" / "birth_rectification" / "test_data.json"
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
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://api_gateway:8000")

    # Retrieve the session ID from the previous test
    test_sequence = get_test_sequence()
    session_id = test_sequence.get("session_id")
    assert session_id, "Session ID from previous test is required"

    # Get birth place from test data
    birth_place = TEST_DATA["birth_details"]["place"]
    expected_latitude = TEST_DATA["birth_details"]["latitude"]
    expected_longitude = TEST_DATA["birth_details"]["longitude"]
    expected_timezone = TEST_DATA["birth_details"]["timezone"]

    # Act - Geocode the birth place
    api_client = SimpleAPIClient(base_url=API_BASE_URL)
    api_client.headers["X-Session-ID"] = session_id

    # Make geocoding request
    response = api_client.post(
        "/api/v1/geocode",
        json_data={"query": birth_place}
    )

    # Assert - HTTP Response
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}: {response.text}"

    # Parse response
    response_data = response.json()

    # Check that location was found
    assert isinstance(response_data, dict), f"Response is not a dictionary: {response_data}"
    assert "results" in response_data, f"Response missing 'results' field: {response_data}"
    results = response_data.get("results", [])
    assert isinstance(results, list), "Results should be a list"
    assert len(results) > 0, f"No geocoding results found for {birth_place}"

    # Get the first result (most relevant match)
    location = results[0]
    assert isinstance(location, dict), f"Location result is not a dictionary: {location}"

    # Check essential fields
    assert "latitude" in location, f"Response missing latitude: {location}"
    assert "longitude" in location, f"Response missing longitude: {location}"
    assert "timezone" in location, f"Response missing timezone: {location}"

    # Verify coordinates match expected values (within small tolerance for floating point)
    latitude = float(location.get("latitude", 0))
    longitude = float(location.get("longitude", 0))
    timezone = str(location.get("timezone", ""))

    assert abs(latitude - expected_latitude) < 0.1, \
        f"Latitude {latitude} doesn't match expected {expected_latitude}"
    assert abs(longitude - expected_longitude) < 0.1, \
        f"Longitude {longitude} doesn't match expected {expected_longitude}"

    # Verify timezone
    assert timezone == expected_timezone, \
        f"Timezone {timezone} doesn't match expected {expected_timezone}"

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
