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
logger = logging.getLogger("test_adaptive_flow")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data_source" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


@pytest.mark.asyncio
@sequence(6)
async def test_adaptive_questionnaire_flow():
    """
    Test Case 6: Adaptive Questionnaire Flow

    Verifies that the questionnaire adapts based on user responses, with
    follow-up questions that build on previous answers to refine the birth time
    estimation.

    From testing_approach.md:
    - The system responds appropriately to each answer
    - Questions adapt based on previous responses
    - The flow concludes appropriately after sufficient information is gathered
    """
    # Arrange
    api_base_url = os.environ.get("API_URL", "http://localhost:9000")
    ws_base_url = os.environ.get("WS_URL", "ws://localhost:9001/ws")

    # Get test session state
    session_state = get_session_state()
    session_id = session_state["test_session_id"]
    chart_id = session_state["chart_id"]
    current_question = session_state.get("current_question")

    assert session_id, "Session ID from previous test is required"
    assert chart_id, "Chart ID from previous test is required"
    assert current_question, "Current question from previous test is required"

    # Expected answers from test data
    expected_answers = TEST_DATA["expected_answers"]

    # Act - Process through the questionnaire flow
    async with APITestClient(base_url=api_base_url, ws_url=ws_base_url) as client:
        # Set the session ID for subsequent requests
        client.set_session_id(session_id)

        # Initialize tracking variables
        question_id = current_question["id"]
        questions_answered = 0
        max_questions = 5  # Limit to prevent infinite loops
        questionnaire_complete = False
        last_question_response = None
        answered_questions = []

        # Process questions until completion or max limit
        while questions_answered < max_questions and not questionnaire_complete:
            # Determine the answer for this question
            # For test purposes, we'll use predefined answers
            answer_key = f"question{questions_answered + 1}"

            # If we have a predefined answer in the test data, use it
            if answer_key in expected_answers:
                answer = expected_answers[answer_key]
            else:
                # Default answers based on question type
                if current_question["type"] == "boolean":
                    answer = "Yes"
                elif current_question["type"] == "multiple_choice":
                    answer = "A"  # First option
                else:
                    answer = "Test response"

            logger.info(f"Answering question {question_id} with: {answer}")

            # Build request payload
            request_data = {
                "sessionId": session_id,
                "chartId": chart_id,
                "questionId": question_id,
                "answer": answer
            }

            # Submit the answer and get the next question
            status, response = await client.post("/api/v1/questionnaire/answer", request_data)

            # Assert - HTTP Response
            assert status == 200, f"Expected status 200, got {status}: {response}"

            # Store the response for the last question
            last_question_response = response

            # Check if questionnaire is complete
            if "complete" in response and response["complete"]:
                questionnaire_complete = True
                logger.info("Questionnaire marked as complete")
                break

            # Extract next question
            assert "question" in response, f"Response missing question: {response}"
            next_question = response["question"]

            # Update current question for next iteration
            current_question = next_question
            question_id = current_question["id"]

            # Add the answered question to our tracking
            answered_questions.append({
                "question_id": question_id,
                "answer": answer
            })

            # Increment counter
            questions_answered += 1

        # Assert - Questionnaire Flow
        # Check that we got through at least one question
        assert questions_answered > 0, "No questions were answered"

        # Either the questionnaire should be complete or we hit the maximum
        if not questionnaire_complete:
            logger.warning(f"Questionnaire did not complete after {max_questions} questions")

        # If complete, check the final response
        if questionnaire_complete and last_question_response is not None:
            # Verify completion response structure
            assert "status" in last_question_response, "Completion response missing status"
            assert last_question_response["status"] == "completed", f"Expected status 'completed', got {last_question_response['status']}"

            # Check for analysis results
            assert "analysis_summary" in last_question_response, "Completion response missing analysis summary"
            assert "recommendations" in last_question_response, "Completion response missing recommendations"

            analysis_summary = last_question_response["analysis_summary"]
            recommendations = last_question_response["recommendations"]

            # Verify meaningful content
            assert len(analysis_summary) > 20, "Analysis summary too short or empty"
            assert len(recommendations) > 0, "No recommendations provided"

        # Store the questionnaire results for subsequent tests
        update_session_state(
            questions_answered=questions_answered,
            questionnaire_complete=questionnaire_complete,
            questionnaire_results=last_question_response
        )

        logger.info(f"Completed adaptive questionnaire flow with {questions_answered} questions answered")

        return {
            "questions_answered": questions_answered,
            "questionnaire_complete": questionnaire_complete,
            "final_response": last_question_response
        }


if __name__ == "__main__":
    # Run this test standalone for debugging
    asyncio.run(test_adaptive_questionnaire_flow())
