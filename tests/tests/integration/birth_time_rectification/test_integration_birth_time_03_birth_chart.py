import os
import json
import pytest
import logging
import asyncio
from pathlib import Path

# Import test utilities
from tests.utils.test_sequence import sequence, update_session_state, get_session_state
from tests.utils.api_test_client import APIClient
from tests.utils.test_config import setup_test_environment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_birth_chart")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data_source" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


@pytest.mark.asyncio
@sequence(3)
async def test_birth_chart_generation():
    """
    Test Case 3: Birth Chart Generation

    Verifies that the system can generate an accurate Vedic birth chart
    from the provided birth details (date, time, location). This chart
    forms the foundation for the entire rectification process.

    From testing_approach.md:
    - Confirms that the system correctly calculates the astrological chart
    - Validates that all planets, houses, and the ascendant are properly computed
    - Ensures the chart configuration matches expected values for the given birth data
    """
    # Arrange
    api_base_url = setup_test_environment()
    ws_base_url = os.environ.get("WS_URL", "ws://localhost:9001/ws")

    # Get test session state
    session_state = get_session_state()
    session_id = session_state["test_session_id"]
    birth_details = session_state["birth_details"]

    assert session_id, "Session ID from previous test is required"
    assert birth_details, "Birth details from previous test are required"

    # Expected chart data
    expected_chart = TEST_DATA["expected_original_chart"]

    # Act - Generate the birth chart
    async with APIClient(base_url=api_base_url, ws_url=ws_base_url) as client:
        # Set the session ID for subsequent requests
        client.set_session_id(session_id)

        # Build request payload
        request_data = {
            "sessionId": session_id,
            "birthDetails": {
                "date": birth_details["date"],
                "time": birth_details["time"],
                "latitude": birth_details["latitude"],
                "longitude": birth_details["longitude"],
                "timezone": birth_details["timezone"],
                "place": birth_details["place"]
            }
        }

        # Make the chart generation request
        status, response = await client.post("/api/v1/chart/generate", request_data)

        # Assert - HTTP Response
        assert status == 200, f"Expected status 200, got {status}: {response}"

        # Check the response structure
        assert "chartId" in response, f"Response missing chartId: {response}"
        assert "chart" in response, f"Response missing chart data: {response}"

        chart_id = response["chartId"]
        chart_data = response["chart"]

        # Verify chart data - essential structure
        assert "ascendant" in chart_data, "Chart missing ascendant information"
        assert "planets" in chart_data, "Chart missing planets information"

        # Check ascendant sign
        assert chart_data["ascendant"]["sign"] == expected_chart["ascendant"]["sign"], \
            f"Ascendant sign {chart_data['ascendant']['sign']} doesn't match expected {expected_chart['ascendant']['sign']}"

        # Verify ascendant degree is within tolerance
        assert abs(chart_data["ascendant"]["degree"] - expected_chart["ascendant"]["degree"]) < 1.0, \
            f"Ascendant degree {chart_data['ascendant']['degree']} not close to expected {expected_chart['ascendant']['degree']}"

        # Check planets
        for expected_planet in expected_chart["planets"]:
            planet_name = expected_planet["name"]

            # Find the matching planet in the response
            actual_planet = next((p for p in chart_data["planets"] if p["name"] == planet_name), None)
            assert actual_planet is not None, f"Planet {planet_name} not found in chart response"

            # Check sign
            assert actual_planet["sign"] == expected_planet["sign"], \
                f"Planet {planet_name} sign {actual_planet['sign']} doesn't match expected {expected_planet['sign']}"

            # Check degree (within tolerance)
            assert abs(actual_planet["degree"] - expected_planet["degree"]) < 1.0, \
                f"Planet {planet_name} degree {actual_planet['degree']} not close to expected {expected_planet['degree']}"

            # Check house placement
            assert actual_planet["house"] == expected_planet["house"], \
                f"Planet {planet_name} house {actual_planet['house']} doesn't match expected {expected_planet['house']}"

        # Store chart data for subsequent tests
        update_session_state(
            chart_id=chart_id,
            original_chart=chart_data
        )

        logger.info(f"Successfully generated birth chart with ID: {chart_id}")
        logger.info(f"Ascendant: {chart_data['ascendant']['sign']} {chart_data['ascendant']['degree']:.2f}°")

        return chart_data


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_birth_chart_generation())
