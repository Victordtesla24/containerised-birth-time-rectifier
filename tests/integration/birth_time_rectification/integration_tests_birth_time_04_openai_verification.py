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
logger = logging.getLogger("test_openai_verification")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data_source" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


@pytest.mark.asyncio
@sequence(4)
async def test_openai_chart_verification():
    """
    Test Case 4: OpenAI-Assisted Verification

    Verifies that the system can utilize OpenAI to analyze the birth chart
    and provide intelligent verification of birth time accuracy, possibly
    suggesting adjustments based on chart indicators.

    From testing_approach.md:
    - OpenAI API receives the birth chart and provides meaningful analysis
    - The system extracts potential birth time corrections from the AI response
    - Results include a confidence score and specific time adjustment suggestion
    """
    # Arrange
    api_base_url = os.environ.get("API_URL", "http://localhost:9000")
    ws_base_url = os.environ.get("WS_URL", "ws://localhost:9001/ws")

    # Get test session state
    session_state = get_session_state()
    session_id = session_state["test_session_id"]
    chart_id = session_state["chart_id"]

    assert session_id, "Session ID from previous test is required"
    assert chart_id, "Chart ID from previous test is required"

    # Expected verification data
    expected_verification = TEST_DATA["expected_verification_result"]

    # Act - Request OpenAI verification of the chart
    async with APITestClient(base_url=api_base_url, ws_url=ws_base_url) as client:
        # Set the session ID for subsequent requests
        client.set_session_id(session_id)

        # Build request payload
        request_data = {
            "sessionId": session_id,
            "chartId": chart_id
        }

        # Make the verification request
        status, response = await client.post("/api/v1/chart/verify", request_data)

        # Assert - HTTP Response
        assert status == 200, f"Expected status 200, got {status}: {response}"

        # Check the response structure
        assert "verificationId" in response, f"Response missing verificationId: {response}"
        assert "result" in response, f"Response missing verification result: {response}"

        verification_id = response["verificationId"]
        verification_result = response["result"]

        # Verify essential fields
        assert "confidence" in verification_result, "Verification result missing confidence score"
        assert "suggestedCorrection" in verification_result, "Verification result missing suggested correction"

        # Check confidence score (allow some variation as AI responses may vary)
        confidence = verification_result["confidence"]
        assert isinstance(confidence, (int, float)), f"Confidence should be a number, got {type(confidence)}"
        assert 0 <= confidence <= 1.0, f"Confidence should be between 0 and 1, got {confidence}"

        # Check suggested correction
        suggested_correction = verification_result["suggestedCorrection"]
        assert "adjustment" in suggested_correction, "Suggested correction missing adjustment information"
        assert "newTime" in suggested_correction, "Suggested correction missing new time information"

        # Verify the adjustment direction and magnitude
        # We're mainly checking that the system provides some kind of adjustment
        # The exact values may vary based on OpenAI's analysis
        adjustment = suggested_correction["adjustment"]
        new_time = suggested_correction["newTime"]

        # Log the suggested adjustment
        logger.info(f"OpenAI suggested adjustment: {adjustment}, new time: {new_time}")

        # Verify the suggested new time matches the expected new time (or is close)
        # Allow for minor variations in the exact suggestion
        expected_time = expected_verification["suggested_correction"]["newTime"]

        # Convert times to minutes since midnight for easier comparison
        def time_to_minutes(time_str):
            hours, minutes, seconds = map(int, time_str.split(':'))
            return hours * 60 + minutes

        expected_minutes = time_to_minutes(expected_time)
        actual_minutes = time_to_minutes(new_time)

        # Allow up to 10 minutes difference from expected correction
        time_difference = abs(expected_minutes - actual_minutes)
        assert time_difference <= 10, f"Suggested time {new_time} too different from expected {expected_time}"

        # Check that there's analysis content
        assert "analysis" in verification_result, "Verification result missing analysis content"
        analysis = verification_result["analysis"]
        assert len(analysis) > 50, "Analysis content too short or empty"

        # Store verification result for subsequent tests
        update_session_state(
            verification_id=verification_id,
            verification_result=verification_result
        )

        logger.info(f"Successfully verified chart with confidence: {confidence}")
        logger.info(f"Suggested correction: {adjustment}")

        return verification_result


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_openai_chart_verification())
