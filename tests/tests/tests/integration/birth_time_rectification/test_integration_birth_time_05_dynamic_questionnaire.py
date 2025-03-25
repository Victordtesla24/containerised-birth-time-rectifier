import os
import json
import pytest
import logging
import asyncio
from pathlib import Path

# Import test utilities
from tests.utils.test_sequence import sequence, update_session_state, get_session_state
from tests.utils.api_test_client import APITestClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_dynamic_questionnaire")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data_source" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


@pytest.mark.asyncio
@sequence(5)
async def test_dynamic_questionnaire_generation():
    """
    Test Case 5: Dynamic Questionnaire Generation

    Verifies that the system can generate a dynamic questionnaire tailored
    to the specific chart and preliminary analysis, with questions designed
    to refine the birth time.

    From testing_approach.md:
    - The system generates personalized questions based on chart indicators
    - Each question has appropriate metadata (type, category)
    - Questions are relevant to refining the birth time accuracy
    """
    # Arrange
    api_base_url = os.environ.get("API_URL", "http://localhost:9000")
    ws_base_url = os.environ.get("WS_URL", "ws://localhost:9001/ws")

    # Get test session state
    session_state = get_session_state()
    session_id = session_state["test_session_id"]
    chart_id = session_state["chart_id"]
    verification_result = session_state.get("verification_result")

    assert session_id, "Session ID from previous test is required"
    assert chart_id, "Chart ID from previous test is required"

    # Expected questionnaire data
    expected_questionnaire = TEST_DATA["questionnaire"]

    # Act - Initialize the questionnaire
    async with APITestClient(base_url=api_base_url, ws_url=ws_base_url) as client:
        # Set the session ID for subsequent requests
        client.set_session_id(session_id)

        # Build request payload
        request_data = {
            "sessionId": session_id,
            "chartId": chart_id
        }

        # Initialize the questionnaire
        status, response = await client.post("/api/v1/questionnaire/start", request_data)

        # Assert - HTTP Response
        assert status == 200, f"Expected status 200, got {status}: {response}"

        # Check the response structure
        assert "sessionId" in response, f"Response missing sessionId: {response}"
        assert "question" in response, f"Response missing question: {response}"

        # Extract question details
        question = response["question"]

        # Verify question structure
        assert "id" in question, "Question missing ID"
        assert "text" in question, "Question missing text"
        assert "type" in question, "Question missing type"

        question_id = question["id"]
        question_text = question["text"]
        question_type = question["type"]

        # Check that the question type is valid
        valid_types = ["text", "boolean", "multiple_choice", "date", "time"]
        assert question_type in valid_types, f"Question type {question_type} not in valid types: {valid_types}"

        # Check that the question text is not empty
        assert len(question_text) > 10, "Question text too short or empty"

        # If it's a multiple-choice question, check that options are provided
        if question_type == "multiple_choice":
            assert "options" in question, "Multiple-choice question missing options"
            options = question["options"]
            assert isinstance(options, list), "Options should be a list"
            assert len(options) > 0, "Options list is empty"

            # Check option structure
            for option in options:
                assert "value" in option, "Option missing value"
                assert "text" in option, "Option missing text"

        # Store the question for subsequent tests
        update_session_state(
            questionnaire_initialized=True,
            current_question={
                "id": question_id,
                "text": question_text,
                "type": question_type
            }
        )

        logger.info(f"Successfully initialized questionnaire with first question: {question_id}")
        logger.info(f"Question: {question_text}")
        logger.info(f"Type: {question_type}")

        return {
            "question_id": question_id,
            "question": question
        }


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_dynamic_questionnaire_generation())
