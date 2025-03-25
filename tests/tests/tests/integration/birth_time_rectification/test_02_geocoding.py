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
import httpx
from datetime import datetime

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
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

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
    api_client = SimpleAPIClient(base_url=API_BASE_URL, timeout=60.0)  # Increase timeout for geocoding
    api_client.headers["X-Session-ID"] = session_id

    logger.info(f"Testing geocoding for birth place: {birth_place}")

    # Make geocoding request
    try:
        response = api_client.post(
            "/api/v1/geocode",
            json_data={"query": birth_place}
        )
    except httpx.TimeoutException:
        pytest.fail(f"Geocoding request timed out for '{birth_place}'. The geocoding service may be unreachable or overloaded.")
    except Exception as e:
        pytest.fail(f"Geocoding request failed: {str(e)}")

    # Assert - HTTP Response
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}: {response.text}"

    # Parse response
    response_data = response.json()

    # Log the geocoding response for debugging
    logger.info(f"Geocoding response for {birth_place}: {json.dumps(response_data, indent=2)}")

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

    # Get timezone for the coordinates
    try:
        timezone_response = api_client.post(
            "/api/v1/geocode/timezone",
            json_data={
                "latitude": location["latitude"],
                "longitude": location["longitude"]
            }
        )

        assert timezone_response.status_code == 200, f"Failed to get timezone: {timezone_response.text}"
        timezone_data = timezone_response.json()
        timezone = timezone_data.get("timezone", {}).get("timezone_id", "UTC")
    except Exception as e:
        logger.warning(f"Failed to get timezone for coordinates, using UTC: {e}")
        timezone = "UTC"

    # Verify coordinates match expected values (within reasonable tolerance)
    # Using 0.5 degree tolerance since different geocoding providers may give slightly different coordinates
    latitude = float(location["latitude"])
    longitude = float(location["longitude"])

    assert abs(latitude - expected_latitude) < 0.5, \
        f"Latitude {latitude} doesn't match expected {expected_latitude} (within 0.5 degree tolerance)"
    assert abs(longitude - expected_longitude) < 0.5, \
        f"Longitude {longitude} doesn't match expected {expected_longitude} (within 0.5 degree tolerance)"

    # Verify timezone (allow for different timezone strings that represent the same timezone)
    # For example, "Asia/Calcutta" and "Asia/Kolkata" are the same timezone
    import pytz
    try:
        actual_tz = pytz.timezone(timezone)
        expected_tz = pytz.timezone(expected_timezone)
        # Check if they have same UTC offset (currently)
        now = datetime.now()
        actual_offset = actual_tz.utcoffset(now)
        expected_offset = expected_tz.utcoffset(now)
        assert actual_offset == expected_offset, \
            f"Timezone {timezone} doesn't match expected {expected_timezone} (different UTC offset)"
    except pytz.exceptions.UnknownTimeZoneError as e:
        logger.warning(f"Unknown timezone: {e}")
        # For unknown timezones, we can't validate offsets, so we rely on string comparison
        assert timezone == expected_timezone, \
            f"Timezone {timezone} doesn't match expected {expected_timezone}"
    except Exception as e:
        logger.warning(f"Timezone validation error: {e}")
        # Fall back to string comparison if validation fails
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
