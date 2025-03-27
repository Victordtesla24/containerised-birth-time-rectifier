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
logger = logging.getLogger("test_chart_interpretation")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data_source" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


@pytest.mark.asyncio
@sequence(9)
async def test_chart_interpretation():
    """
    Test Case 9: Chart Interpretation

    Verifies that the system can generate a comprehensive interpretation
    of the rectified birth chart with personalized insights.

    From testing_approach.md:
    - The system generates a detailed interpretation of the rectified chart
    - The interpretation covers all major chart components (planets, houses, aspects)
    - The interpretation provides personal insights relevant to the native
    - The interpretation is coherent, well-structured, and astrologically accurate
    """
    # Arrange
    api_base_url = os.environ.get("API_URL", "http://localhost:9000")
    ws_base_url = os.environ.get("WS_URL", "ws://localhost:9001/ws")

    # Get test session state
    session_state = get_session_state()
    session_id = session_state["test_session_id"]
    chart_id = session_state["chart_id"]
    rectified_chart = session_state.get("rectified_chart")
    birth_details = session_state["birth_details"]
    rectification_id = session_state.get("rectification_id")

    assert session_id, "Session ID from previous test is required"
    assert chart_id, "Chart ID from previous test is required"
    assert rectified_chart, "Rectified chart from previous test is required"
    assert birth_details, "Birth details from previous test are required"
    assert rectification_id, "Rectification ID from previous test is required"

    # Expected interpretation data
    expected_interpretation = TEST_DATA.get("expected_interpretation", {})
    expected_sections = expected_interpretation.get("expected_sections", [
        "introduction", "sun_sign", "moon_sign", "ascendant", "planetary_placements",
        "house_placements", "major_aspects", "conclusion"
    ])

    # Act - Request chart interpretation
    async with APITestClient(base_url=api_base_url, ws_url=ws_base_url) as client:
        # Set the session ID for subsequent requests
        client.set_session_id(session_id)

        # Build request payload
        request_data = {
            "sessionId": session_id,
            "chartId": chart_id,
            "rectificationId": rectification_id,
            "birthDetails": {
                "date": birth_details["date"],
                "time": session_state.get("rectified_time", birth_details["time"]),
                "latitude": birth_details["latitude"],
                "longitude": birth_details["longitude"],
                "timezone": birth_details["timezone"],
                "place": birth_details["place"],
                "name": birth_details.get("name", "Test Subject")
            },
            "chart": rectified_chart
        }

        # Request interpretation
        status, response = await client.post("/api/v1/chart/interpret", request_data)

        # Assert - HTTP Response
        assert status == 200, f"Expected status 200, got {status}: {response}"

        # Check the response structure
        assert "interpretationId" in response, f"Response missing interpretationId: {response}"
        assert "interpretation" in response, f"Response missing interpretation: {response}"

        interpretation_id = response["interpretationId"]
        interpretation = response["interpretation"]

        # Verify interpretation structure
        assert "sections" in interpretation, "Interpretation missing sections"
        assert "summary" in interpretation, "Interpretation missing summary"

        sections = interpretation["sections"]
        summary = interpretation["summary"]

        # Verify sections list structure
        assert isinstance(sections, list), "Sections should be a list"
        assert len(sections) > 0, "Interpretation has no sections"

        # Verify each section has required fields
        for section in sections:
            assert "title" in section, f"Section missing title: {section}"
            assert "content" in section, f"Section missing content: {section}"
            assert len(section["content"].strip()) > 100, f"Section content too short: {section['title']}"

        # Verify all expected sections are present
        section_titles = [section["title"].lower() for section in sections]
        for expected_section in expected_sections:
            assert any(expected_section.lower() in title for title in section_titles), \
                f"Expected section '{expected_section}' not found in interpretation"

        # Verify the interpretation mentions key components of the chart
        all_content = " ".join([section["content"] for section in sections])

        # Check for sun sign
        sun = next((p for p in rectified_chart["planets"] if p["name"] == "Sun"), None)
        assert sun, "Sun not found in rectified chart"
        assert sun["sign"] in all_content, f"Interpretation doesn't mention Sun sign ({sun['sign']})"

        # Check for moon sign
        moon = next((p for p in rectified_chart["planets"] if p["name"] == "Moon"), None)
        assert moon, "Moon not found in rectified chart"
        assert moon["sign"] in all_content, f"Interpretation doesn't mention Moon sign ({moon['sign']})"

        # Check for ascendant
        ascendant = rectified_chart["ascendant"]["sign"]
        assert ascendant in all_content, f"Interpretation doesn't mention Ascendant sign ({ascendant})"

        # Verify the summary contains meaningful information
        assert len(summary.strip()) > 100, "Summary is too short"
        assert birth_details.get("name", "").lower() in summary.lower() or "your" in summary.lower(), \
            "Summary doesn't personalize the interpretation"

        # Store interpretation data for subsequent tests
        update_session_state(
            interpretation_id=interpretation_id,
            chart_interpretation=interpretation
        )

        logger.info(f"Successfully generated chart interpretation with ID: {interpretation_id}")
        logger.info(f"Interpretation contains {len(sections)} sections")

        return {
            "interpretation_id": interpretation_id,
            "section_count": len(sections)
        }


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_chart_interpretation())
