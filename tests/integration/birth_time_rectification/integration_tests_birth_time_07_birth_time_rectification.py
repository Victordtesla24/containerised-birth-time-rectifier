import os
import json
import pytest
import logging
import asyncio
from pathlib import Path

# Import test utilities
from tests.utils.test_sequence import sequence, update_session_state, get_session_state
from tests.utils.test_unit_api_test_client import APITestClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_birth_time_rectification")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data_source" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


@pytest.mark.asyncio
@sequence(7)
async def test_birth_time_rectification():
    """
    Test Case 7: Birth Time Rectification

    Verifies that the system can generate a rectified birth time
    based on the questionnaire responses and chart analysis, and
    then create an adjusted chart with the new time.

    From testing_approach.md:
    - The system proposes a specific birth time adjustment
    - The new time is within a reasonable range of the original time
    - A rectified chart is generated with the new time
    - The rectified chart appropriately reflects the time change
    """
    # Arrange
    api_base_url = os.environ.get("API_URL", "http://localhost:9000")
    ws_base_url = os.environ.get("WS_URL", "ws://localhost:9001/ws")

    # Get test session state
    session_state = get_session_state()
    session_id = session_state["test_session_id"]
    chart_id = session_state["chart_id"]
    birth_details = session_state["birth_details"]
    original_chart = session_state["original_chart"]
    questionnaire_results = session_state.get("questionnaire_results", {})

    assert session_id, "Session ID from previous test is required"
    assert chart_id, "Chart ID from previous test is required"
    assert birth_details, "Birth details from previous test are required"
    assert original_chart, "Original chart from previous test is required"

    # Expected rectification data
    expected_rectified_time = TEST_DATA["expected_rectified_time"]
    expected_rectified_chart = TEST_DATA["expected_rectified_chart"]

    # Act - Request birth time rectification
    async with APITestClient(base_url=api_base_url, ws_url=ws_base_url) as client:
        # Set the session ID for subsequent requests
        client.set_session_id(session_id)

        # Build request payload
        request_data = {
            "sessionId": session_id,
            "chartId": chart_id,
            "birthDetails": {
                "date": birth_details["date"],
                "time": birth_details["time"],
                "latitude": birth_details["latitude"],
                "longitude": birth_details["longitude"],
                "timezone": birth_details["timezone"],
                "place": birth_details["place"]
            }
        }

        # Add questionnaire analysis if available
        if questionnaire_results and isinstance(questionnaire_results, dict):
            request_data["questionnaireResults"] = questionnaire_results

        # Request rectification
        status, response = await client.post("/api/v1/chart/rectify", request_data)

        # Assert - HTTP Response
        assert status == 200, f"Expected status 200, got {status}: {response}"

        # Check the response structure
        assert "rectificationId" in response, f"Response missing rectificationId: {response}"
        assert "rectifiedTime" in response, f"Response missing rectifiedTime: {response}"
        assert "rectifiedChart" in response, f"Response missing rectifiedChart: {response}"

        rectification_id = response["rectificationId"]
        rectified_time = response["rectifiedTime"]
        rectified_chart = response["rectifiedChart"]

        # Verify rectified time format and value
        # Check format HH:MM:SS
        time_parts = rectified_time.split(":")
        assert len(time_parts) == 3, f"Rectified time {rectified_time} not in expected format HH:MM:SS"

        # Convert times to minutes since midnight for comparison
        def time_to_minutes(time_str):
            hours, minutes, seconds = map(int, time_str.split(':'))
            return hours * 60 + minutes

        original_minutes = time_to_minutes(birth_details["time"])
        rectified_minutes = time_to_minutes(rectified_time)
        expected_minutes = time_to_minutes(expected_rectified_time)

        # Check if rectified time is different from original
        assert rectified_minutes != original_minutes, "Rectified time is identical to original time"

        # Check if rectified time is within reasonable range (e.g., 30 minutes) of expected
        time_difference = abs(rectified_minutes - expected_minutes)
        assert time_difference <= 30, f"Rectified time {rectified_time} too different from expected {expected_rectified_time}"

        # Verify rectified chart structure
        assert "ascendant" in rectified_chart, "Rectified chart missing ascendant information"
        assert "planets" in rectified_chart, "Rectified chart missing planets information"

        # Check for changes in the chart due to time change
        ascendant_changed = (
            rectified_chart["ascendant"]["sign"] != original_chart["ascendant"]["sign"] or
            abs(rectified_chart["ascendant"]["degree"] - original_chart["ascendant"]["degree"]) > 1.0
        )

        # Either the ascendant or some planet houses should change due to time rectification
        assert ascendant_changed or any(
            rectified_planet["house"] != original_planet["house"]
            for rectified_planet, original_planet in zip(
                sorted(rectified_chart["planets"], key=lambda p: p["name"]),
                sorted(original_chart["planets"], key=lambda p: p["name"])
            )
        ), "No significant changes in rectified chart"

        # Check if the ascendant matches the expected rectified chart
        assert rectified_chart["ascendant"]["sign"] == expected_rectified_chart["ascendant"]["sign"], \
            f"Rectified ascendant sign {rectified_chart['ascendant']['sign']} doesn't match expected {expected_rectified_chart['ascendant']['sign']}"

        # Store rectification data for subsequent tests
        update_session_state(
            rectification_id=rectification_id,
            rectified_time=rectified_time,
            rectified_chart=rectified_chart
        )

        logger.info(f"Successfully rectified birth time to: {rectified_time}")
        logger.info(f"Original ascendant: {original_chart['ascendant']['sign']} {original_chart['ascendant']['degree']:.2f}°")
        logger.info(f"Rectified ascendant: {rectified_chart['ascendant']['sign']} {rectified_chart['ascendant']['degree']:.2f}°")

        return {
            "rectification_id": rectification_id,
            "rectified_time": rectified_time,
            "original_time": birth_details["time"]
        }


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_birth_time_rectification())
