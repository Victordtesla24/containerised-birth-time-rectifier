#!/usr/bin/env python3
"""
Integration test for the complete chart verification chain.

This test validates the entire verification process from chart calculation to OpenAI verification
and correction application, ensuring that the system meets the requirements specified in the
testing approach document.
"""

import os
import json
import pytest
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import test utilities
from tests.utils.test_helpers import get_test_sequence, update_test_sequence
from tests.utils.simple_api_client import SimpleAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_verification_chain")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)

# Load expected chart data for the Pune test case
EXPECTED_CHART_PATH = Path(__file__).parents[2] / "test_data" / "birth_rectification" / "expected_chart_1985-10-25.json"
try:
    with open(EXPECTED_CHART_PATH, "r") as f:
        EXPECTED_CHART = json.load(f)
except FileNotFoundError:
    logger.warning(f"Expected chart data file not found: {EXPECTED_CHART_PATH}")
    EXPECTED_CHART = {}


@pytest.mark.asyncio
async def test_chart_calculation_and_verification():
    """
    Test Case 4: Comprehensive Chart Calculation and Verification

    This test validates the end-to-end chart calculation and verification process:
    1. Calculate an initial chart using astronomical algorithms
    2. Verify the chart with OpenAI against Vedic astrological standards
    3. Apply any corrections based on the verification
    4. Validate the final chart against expected values

    The test uses the real-world Pune test case from testing_approach.md.
    """
    # Arrange
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
    client = SimpleAPIClient(base_url=API_BASE_URL)

    # Retrieve test sequence data from previous tests
    test_sequence = get_test_sequence()
    birth_details = test_sequence.get("birth_details", {})

    # Ensure we have the required birth details
    assert birth_details, "Birth details from previous test are required"

    birth_date = birth_details.get("date", TEST_DATA["birth_details"]["date"])
    birth_time = birth_details.get("time", TEST_DATA["birth_details"]["time"])
    latitude = birth_details.get("latitude", TEST_DATA["birth_details"]["latitude"])
    longitude = birth_details.get("longitude", TEST_DATA["birth_details"]["longitude"])
    timezone = birth_details.get("timezone", TEST_DATA["birth_details"]["timezone"])

    logger.info(f"Testing chart calculation and verification for: {birth_date} {birth_time} at {latitude}, {longitude}")

    # Act: Generate the chart with verification
    response = client.post(
        "/api/v1/chart/generate",
        {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "verify_with_openai": True
        }
    )

    # Assert: Check if the request was successful
    assert response.status_code == 200, f"Chart generation failed with status {response.status_code}: {response.text}"

    # Parse the response
    chart_data = response.json()

    # Basic chart validation
    assert "chart_id" in chart_data, "Chart ID is missing from response"
    assert "planets" in chart_data, "Planets data is missing from response"
    assert "houses" in chart_data, "Houses data is missing from response"
    assert "ascendant" in chart_data, "Ascendant data is missing from response"

    # Verification result validation
    assert "verification" in chart_data, "Verification result is missing from response"
    verification = chart_data["verification"]

    # Check verification status
    assert "status" in verification, "Verification status is missing"
    assert "verified" in verification, "Verified flag is missing"
    assert "confidence" in verification, "Confidence score is missing"

    logger.info(f"Chart verification status: {verification.get('status')}")
    logger.info(f"Verification confidence: {verification.get('confidence')}")

    # If OpenAI verification was successful, check if corrections were applied
    if verification.get("status") != "verification_error" and verification.get("verified_with_openai", False):
        logger.info("OpenAI verification was performed")
        assert "corrections_applied" in verification, "Corrections applied flag is missing"

        if verification.get("corrections_applied", False):
            logger.info("Corrections were applied to the chart")
            assert "corrections" in verification, "Corrections list is missing"

            # Log the corrections for debugging
            corrections = verification.get("corrections", [])
            for correction in corrections:
                logger.info(f"Correction applied: {correction}")
    else:
        logger.info("OpenAI verification was not performed or failed")

    # Validate chart against expected values
    validate_chart_data(chart_data)

    # Store chart ID for subsequent tests
    test_sequence.update({
        "chart_id": chart_data["chart_id"],
        "verified_chart": {
            "chart_id": chart_data["chart_id"],
            "verification_status": verification.get("status"),
            "verification_confidence": verification.get("confidence"),
            "corrections_applied": verification.get("corrections_applied", False)
        },
        "test_stage": 4
    })
    update_test_sequence(test_sequence, persist=True)

    logger.info(f"Successfully generated and verified chart: {chart_data['chart_id']}")

    # Optional: Test chart retrieval API to ensure persistence
    await test_chart_retrieval(client, chart_data["chart_id"])

    return chart_data


async def test_chart_retrieval(client: SimpleAPIClient, chart_id: str) -> Dict[str, Any]:
    """
    Test retrieving a chart by ID to ensure it was properly stored.

    Args:
        client: API client
        chart_id: Chart ID to retrieve

    Returns:
        Retrieved chart data
    """
    # Request the chart by ID
    response = client.get(f"/api/v1/chart/{chart_id}")

    # Check if the request was successful
    assert response.status_code == 200, f"Chart retrieval failed with status {response.status_code}: {response.text}"

    # Parse the response
    chart_data = response.json()

    # Basic validation
    assert chart_data["chart_id"] == chart_id, "Retrieved chart has incorrect ID"
    assert "planets" in chart_data, "Retrieved chart is missing planets data"
    assert "houses" in chart_data, "Retrieved chart is missing houses data"

    logger.info(f"Successfully retrieved chart: {chart_id}")
    return chart_data


def validate_chart_data(chart_data: Dict[str, Any]) -> None:
    """
    Validate chart data against expected values for the Pune test case.

    Args:
        chart_data: Chart data to validate
    """
    # Skip detailed validation if expected data is not available
    if not EXPECTED_CHART:
        logger.warning("Skipping detailed chart validation - expected data not available")
        return

    # Validate key planetary positions within acceptable tolerance (0.5 degrees)
    TOLERANCE = 0.5
    planets = chart_data.get("planets", {})

    # Define key planets to check
    key_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

    for planet in key_planets:
        # Check if planet exists in both actual and expected data
        if planet in planets and planet in EXPECTED_CHART.get("planets", {}):
            actual_longitude = planets[planet].get("longitude", 0)
            expected_longitude = EXPECTED_CHART["planets"][planet].get("longitude", 0)

            # Calculate difference considering 360° wrapping
            diff = min(
                abs(actual_longitude - expected_longitude),
                360 - abs(actual_longitude - expected_longitude)
            )

            # Verify within tolerance
            assert diff <= TOLERANCE, f"{planet} position differs by {diff}° (expected: {expected_longitude}, actual: {actual_longitude})"

            # Check if signs match
            actual_sign = planets[planet].get("sign")
            expected_sign = EXPECTED_CHART["planets"][planet].get("sign")

            if actual_sign and expected_sign:
                assert actual_sign == expected_sign, f"{planet} has incorrect sign (expected: {expected_sign}, actual: {actual_sign})"

            logger.info(f"Validated {planet}: {actual_sign} {actual_longitude % 30:.2f}° (within {diff:.2f}° of expected)")

    # Validate ascendant
    if "ascendant" in chart_data and "ascendant" in EXPECTED_CHART:
        actual_asc_long = chart_data["ascendant"].get("longitude", 0)
        expected_asc_long = EXPECTED_CHART["ascendant"].get("longitude", 0)

        # Calculate difference
        asc_diff = min(
            abs(actual_asc_long - expected_asc_long),
            360 - abs(actual_asc_long - expected_asc_long)
        )

        # Verify within tolerance (slightly larger tolerance for ascendant)
        assert asc_diff <= TOLERANCE * 2, f"Ascendant position differs by {asc_diff}° (expected: {expected_asc_long}, actual: {actual_asc_long})"

        # Check if signs match
        actual_asc_sign = chart_data["ascendant"].get("sign")
        expected_asc_sign = EXPECTED_CHART["ascendant"].get("sign")

        if actual_asc_sign and expected_asc_sign:
            assert actual_asc_sign == expected_asc_sign, f"Ascendant has incorrect sign (expected: {expected_asc_sign}, actual: {actual_asc_sign})"

        logger.info(f"Validated Ascendant: {actual_asc_sign} {actual_asc_long % 30:.2f}° (within {asc_diff:.2f}° of expected)")


@pytest.mark.asyncio
async def test_chart_verification_boundary_cases():
    """
    Test Chart Verification Boundary Cases

    This test validates the chart verification process with various boundary
    cases to ensure proper error handling and robustness.
    """
    # Arrange
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
    client = SimpleAPIClient(base_url=API_BASE_URL)

    # Retrieve test sequence data
    test_sequence = get_test_sequence()
    birth_details = test_sequence.get("birth_details", {})

    # Ensure we have the required birth details
    assert birth_details, "Birth details from previous test are required"

    # Original birth details
    birth_date = birth_details.get("date", TEST_DATA["birth_details"]["date"])
    birth_time = birth_details.get("time", TEST_DATA["birth_details"]["time"])
    latitude = birth_details.get("latitude", TEST_DATA["birth_details"]["latitude"])
    longitude = birth_details.get("longitude", TEST_DATA["birth_details"]["longitude"])
    timezone = birth_details.get("timezone", TEST_DATA["birth_details"]["timezone"])

    # Case 1: Test with incorrect latitude/longitude (near poles)
    logger.info("Testing verification with extreme coordinates (near poles)")
    response = client.post(
        "/api/v1/chart/generate",
        {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "latitude": 89.9,  # Near North Pole
            "longitude": longitude,
            "timezone": timezone,
            "verify_with_openai": True
        }
    )

    # The request should still succeed, but verification may have issues
    assert response.status_code == 200, f"Chart generation with extreme latitude failed: {response.text}"
    chart_data = response.json()

    # Check calculation and verification results
    assert "planets" in chart_data, "Planets data is missing from response"
    assert "verification" in chart_data, "Verification result is missing from response"

    logger.info(f"Verification with extreme coordinates: {chart_data['verification'].get('status')}")

    # Case 2: Test with incorrect date format
    logger.info("Testing with incorrect date format")
    response = client.post(
        "/api/v1/chart/generate",
        {
            "birth_date": "25/10/1985",  # Wrong format, should be YYYY-MM-DD
            "birth_time": birth_time,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "verify_with_openai": True
        }
    )

    # This should fail with a 422 validation error
    assert response.status_code in [400, 422], f"Expected validation error for incorrect date format, got: {response.status_code}"

    # Case 3: Test with verification disabled
    logger.info("Testing with verification disabled")
    response = client.post(
        "/api/v1/chart/generate",
        {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "verify_with_openai": False
        }
    )

    # The request should succeed
    assert response.status_code == 200, f"Chart generation without verification failed: {response.text}"
    chart_data = response.json()

    # Check calculation and verification results
    assert "planets" in chart_data, "Planets data is missing from response"
    assert "verification" in chart_data, "Verification result is missing from response"
    verification = chart_data["verification"]

    # Verification should be skipped
    assert verification.get("status") in ["verification_skipped", "verification_disabled"], \
        f"Expected verification to be skipped, got status: {verification.get('status')}"

    logger.info(f"Successfully tested verification boundary cases")


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_chart_calculation_and_verification())
