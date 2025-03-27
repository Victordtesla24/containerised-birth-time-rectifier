import os
import json
import pytest
import logging
import asyncio
from pathlib import Path
import base64

# Import test utilities
from tests.utils.test_sequence import sequence, update_session_state, get_session_state
from tests.utils.test_unit_api_test_client import APITestClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_chart_export")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data_source" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


@pytest.mark.asyncio
@sequence(10)
async def test_chart_export():
    """
    Test Case 10: Chart Export

    Verifies that the system can export the rectified chart in various formats
    for user download or sharing purposes.

    From testing_approach.md:
    - The system generates exportable files in multiple formats (PDF, PNG, JSON)
    - The exported chart includes all relevant information (planets, houses, aspects)
    - The exported files are properly formatted and contain accurate data
    - The system provides download links or base64-encoded data for the exported files
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
    rectified_time = session_state.get("rectified_time")
    interpretation_id = session_state.get("interpretation_id")

    assert session_id, "Session ID from previous test is required"
    assert chart_id, "Chart ID from previous test is required"
    assert rectified_chart, "Rectified chart from previous test is required"
    assert birth_details, "Birth details from previous test are required"
    assert rectified_time, "Rectified time from previous test is required"

    # Expected export formats
    export_formats = ["PDF", "PNG", "JSON"]

    # Act - Request chart export for each format
    async with APITestClient(base_url=api_base_url, ws_url=ws_base_url) as client:
        # Set the session ID for subsequent requests
        client.set_session_id(session_id)

        export_results = {}

        for export_format in export_formats:
            # Build request payload
            request_data = {
                "sessionId": session_id,
                "chartId": chart_id,
                "birthDetails": {
                    "date": birth_details["date"],
                    "time": rectified_time,
                    "latitude": birth_details["latitude"],
                    "longitude": birth_details["longitude"],
                    "timezone": birth_details["timezone"],
                    "place": birth_details["place"],
                    "name": birth_details.get("name", "Test Subject")
                },
                "chart": rectified_chart,
                "format": export_format
            }

            # Add interpretation ID if available for PDF format
            if export_format == "PDF" and interpretation_id:
                request_data["interpretationId"] = interpretation_id

            # Request export
            status, response = await client.post("/api/v1/chart/export", request_data)

            # Assert - HTTP Response
            assert status == 200, f"Export to {export_format} failed with status {status}: {response}"

            # Check the response structure
            assert "exportId" in response, f"Response missing exportId for {export_format}"
            assert "fileData" in response, f"Response missing fileData for {export_format}"

            export_id = response["exportId"]
            file_data = response["fileData"]

            # For all formats, we expect base64-encoded data
            assert file_data.startswith("data:"), f"{export_format} data does not start with 'data:'"

            # Check format-specific data structure
            if export_format == "PDF":
                assert file_data.startswith("data:application/pdf;base64,"), \
                    f"PDF data doesn't have correct mime type prefix"
            elif export_format == "PNG":
                assert file_data.startswith("data:image/png;base64,"), \
                    f"PNG data doesn't have correct mime type prefix"
            elif export_format == "JSON":
                assert file_data.startswith("data:application/json;base64,"), \
                    f"JSON data doesn't have correct mime type prefix"

            # Decode and verify base64 data
            try:
                # Extract the base64 part after the comma
                base64_part = file_data.split(",", 1)[1]
                decoded_data = base64.b64decode(base64_part)

                # Check if decoded data is not empty
                assert len(decoded_data) > 0, f"Decoded {export_format} data is empty"

                # For JSON format, verify the structure
                if export_format == "JSON":
                    json_data = json.loads(decoded_data)
                    assert "chart" in json_data, "JSON export missing chart data"
                    assert "birthDetails" in json_data, "JSON export missing birth details"

                    # Verify chart data matches rectified chart
                    assert json_data["chart"]["ascendant"]["sign"] == rectified_chart["ascendant"]["sign"], \
                        "JSON export contains incorrect ascendant sign"

                    # Verify birth details match rectified data
                    assert json_data["birthDetails"]["time"] == rectified_time, \
                        "JSON export contains incorrect birth time"

            except Exception as e:
                pytest.fail(f"Failed to decode {export_format} data: {str(e)}")

            export_results[export_format] = {
                "exportId": export_id,
                "dataSize": len(decoded_data)
            }

            logger.info(f"Successfully exported chart to {export_format} (size: {len(decoded_data)} bytes)")

        # Store export data for any subsequent processing
        update_session_state(
            export_results=export_results
        )

        return {
            "exported_formats": list(export_results.keys()),
            "export_results": export_results
        }


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_chart_export())
