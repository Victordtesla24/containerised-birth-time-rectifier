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
logger = logging.getLogger("test_chart_comparison")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data_source" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


@pytest.mark.asyncio
@sequence(8)
async def test_chart_comparison():
    """
    Test Case 8: Chart Comparison

    Verifies that the system can compare original and rectified birth charts
    and identify significant differences between them.

    From testing_approach.md:
    - The system generates a detailed comparison between original and rectified charts
    - The comparison highlights shifted houses, planetary positions, and aspects
    - The comparison explains the astrological significance of these changes
    - The comparison focuses on areas that align with user questionnaire responses
    """
    # Arrange
    api_base_url = os.environ.get("API_URL", "http://localhost:9000")
    ws_base_url = os.environ.get("WS_URL", "ws://localhost:9001/ws")

    # Get test session state
    session_state = get_session_state()
    session_id = session_state["test_session_id"]
    chart_id = session_state["chart_id"]
    original_chart = session_state["original_chart"]
    rectified_chart = session_state.get("rectified_chart")
    rectification_id = session_state.get("rectification_id")

    assert session_id, "Session ID from previous test is required"
    assert chart_id, "Chart ID from previous test is required"
    assert original_chart, "Original chart from previous test is required"
    assert rectified_chart, "Rectified chart from previous test is required"
    assert rectification_id, "Rectification ID from previous test is required"

    # Expected comparison data
    expected_comparison = TEST_DATA.get("expected_chart_comparison", {})

    # Act - Request chart comparison
    async with APITestClient(base_url=api_base_url, ws_url=ws_base_url) as client:
        # Set the session ID for subsequent requests
        client.set_session_id(session_id)

        # Build request payload
        request_data = {
            "sessionId": session_id,
            "chartId": chart_id,
            "rectificationId": rectification_id,
            "originalChart": original_chart,
            "rectifiedChart": rectified_chart
        }

        # Request comparison
        status, response = await client.post("/api/v1/chart/compare", request_data)

        # Assert - HTTP Response
        assert status == 200, f"Expected status 200, got {status}: {response}"

        # Check the response structure
        assert "comparisonId" in response, f"Response missing comparisonId: {response}"
        assert "comparison" in response, f"Response missing comparison: {response}"

        comparison_id = response["comparisonId"]
        comparison = response["comparison"]

        # Verify comparison structure
        assert "ascendantChanges" in comparison, "Comparison missing ascendant changes"
        assert "planetaryChanges" in comparison, "Comparison missing planetary changes"
        assert "houseChanges" in comparison, "Comparison missing house changes"
        assert "aspectChanges" in comparison, "Comparison missing aspect changes"
        assert "summary" in comparison, "Comparison missing summary"

        # Check if the comparison identifies at least some differences
        assert len(comparison["ascendantChanges"]) > 0 or \
               len(comparison["planetaryChanges"]) > 0 or \
               len(comparison["houseChanges"]) > 0 or \
               len(comparison["aspectChanges"]) > 0, \
            "Comparison didn't identify any differences between charts"

        # Verify specific changes if expected data is provided
        if "ascendantChanges" in expected_comparison:
            expected_asc_change = expected_comparison["ascendantChanges"]
            actual_asc_change = comparison["ascendantChanges"]

            # Check if ascendant sign change is detected correctly
            if original_chart["ascendant"]["sign"] != rectified_chart["ascendant"]["sign"]:
                assert "signChange" in actual_asc_change, "Ascendant sign change not detected"
                assert actual_asc_change["signChange"]["from"] == original_chart["ascendant"]["sign"], \
                    "Incorrect original ascendant sign in comparison"
                assert actual_asc_change["signChange"]["to"] == rectified_chart["ascendant"]["sign"], \
                    "Incorrect rectified ascendant sign in comparison"

            # Check if ascendant degree change is detected correctly
            original_degree = original_chart["ascendant"]["degree"]
            rectified_degree = rectified_chart["ascendant"]["degree"]
            if abs(original_degree - rectified_degree) > 1.0:
                assert "degreeChange" in actual_asc_change, "Significant ascendant degree change not detected"

        # Verify planetary changes
        for planet_change in comparison["planetaryChanges"]:
            planet_name = planet_change["planet"]

            # Find the planet in both charts
            original_planet = next((p for p in original_chart["planets"] if p["name"] == planet_name), None)
            rectified_planet = next((p for p in rectified_chart["planets"] if p["name"] == planet_name), None)

            assert original_planet, f"Original planet {planet_name} not found"
            assert rectified_planet, f"Rectified planet {planet_name} not found"

            # Verify house changes are correctly identified
            if "houseChange" in planet_change and original_planet["house"] != rectified_planet["house"]:
                assert planet_change["houseChange"]["from"] == original_planet["house"], \
                    f"Incorrect original house for {planet_name}"
                assert planet_change["houseChange"]["to"] == rectified_planet["house"], \
                    f"Incorrect rectified house for {planet_name}"

        # Verify the summary contains meaningful information
        summary = comparison["summary"]
        assert len(summary.strip()) > 50, "Summary is too short"
        assert any(planet["name"] in summary for planet in original_chart["planets"]), \
            "Summary doesn't mention any planets"

        # Store comparison data for subsequent tests
        update_session_state(
            comparison_id=comparison_id,
            chart_comparison=comparison
        )

        logger.info(f"Successfully generated chart comparison with ID: {comparison_id}")
        logger.info(f"Comparison identified {len(comparison['planetaryChanges'])} planetary changes")
        logger.info(f"Comparison identified {len(comparison['houseChanges'])} house changes")
        logger.info(f"Comparison identified {len(comparison['aspectChanges'])} aspect changes")

        return {
            "comparison_id": comparison_id,
            "significant_changes": len(comparison["planetaryChanges"]) + len(comparison["houseChanges"]) + len(comparison["aspectChanges"])
        }


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_chart_comparison())
