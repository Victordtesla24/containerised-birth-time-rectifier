"""
Integration test for the full sequence flow using real API calls.

This test verifies that the complete sequence flow works with real API calls,
without any mocks or fallbacks.
"""

import pytest
import asyncio
import json
import os
import uuid
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required modules
from ai_service.utils.env_loader import load_env_file, get_openai_api_key
from ai_service.api.services.openai.service import OpenAIService
from ai_service.services.chart_service import ChartService
from ai_service.api.services.questionnaire_service import DynamicQuestionnaireService

# Load environment variables
load_env_file()

# Skip tests if API key is not available
api_key_available = os.environ.get("OPENAI_API_KEY") is not None
if not api_key_available:
    pytest.skip(
        "Skipping real API tests: OPENAI_API_KEY not found in environment",
        allow_module_level=True
    )

@pytest.fixture
def birth_details() -> Dict[str, Any]:
    """Provide standard birth details for testing."""
    return {
        'birthDate': '1990-01-15',
        'birthTime': '14:30:00',
        'birthPlace': 'New York, NY',
        'latitude': 40.7128,
        'longitude': -74.0060,
        'timezone': 'America/New_York'
    }

@pytest.fixture
def openai_service() -> OpenAIService:
    """Create a real OpenAI service for testing."""
    return OpenAIService()

@pytest.fixture
def chart_service(openai_service) -> ChartService:
    """Create a real chart service for testing."""
    return ChartService(openai_service=openai_service)

@pytest.fixture
def questionnaire_service(openai_service) -> DynamicQuestionnaireService:
    """Create a real questionnaire service for testing."""
    return DynamicQuestionnaireService(openai_service=openai_service)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_sequence_flow_real_api(
    birth_details: Dict[str, Any],
    chart_service: ChartService,
    questionnaire_service: DynamicQuestionnaireService
):
    """
    Test the full sequence flow using real API calls.

    This test verifies that the complete flow from chart generation to
    rectification works with real API calls, no mocks or stubs.
    """
    try:
        logger.info("Starting full sequence flow test with real API calls")

        # Step 1: Generate birth chart
        logger.info("Step 1: Generating birth chart")

        chart_result = await chart_service.generate_chart(
            birth_date=birth_details['birthDate'],
            birth_time=birth_details['birthTime'],
            latitude=birth_details['latitude'],
            longitude=birth_details['longitude'],
            location=birth_details['birthPlace'],
            timezone=birth_details['timezone'],
            verify_with_openai=True  # Use real OpenAI verification
        )

        assert chart_result is not None, "Failed to generate chart"
        assert "chart_id" in chart_result, "Missing chart_id in chart result"
        chart_id = chart_result["chart_id"]

        logger.info(f"Chart generated successfully with ID: {chart_id}")

        # Step 2: Start questionnaire
        logger.info("Step 2: Starting questionnaire")

        questionnaire_id = f"test-questionnaire-{uuid.uuid4()}"

        # Initialize questionnaire
        questionnaire_result = await questionnaire_service.initialize_questionnaire(
            chart_id=chart_id,
            session_id=questionnaire_id
        )

        assert questionnaire_result is not None, "Failed to initialize questionnaire"
        assert "id" in questionnaire_result or "sessionId" in questionnaire_result, "Missing questionnaire ID"

        questionnaire_id = questionnaire_result.get("id") or questionnaire_result.get("sessionId", questionnaire_id)
        logger.info(f"Questionnaire initialized with ID: {questionnaire_id}")

        # Step 3: Get and answer questions
        logger.info("Step 3: Answering questionnaire questions")

        # Track questions and answers
        questions_and_answers = []

        # Answer 3 questions (or fewer if questionnaire completes early)
        for question_num in range(3):
            # Get next question
            next_question = await questionnaire_service.get_next_question(
                session_id=questionnaire_id,
                chart_id=chart_id
            )

            # Check if questionnaire is already complete
            if not next_question or next_question.get("complete", False) or "next_question" not in next_question:
                logger.info(f"Questionnaire completed after {question_num} questions")
                break

            # Extract question details
            question = next_question.get("next_question", {})
            question_id = question.get("id")
            question_text = question.get("text")

            assert question_id, f"Missing question ID in question {question_num+1}"
            assert question_text, f"Missing question text in question {question_num+1}"

            logger.info(f"Question {question_num+1}: {question_text} (ID: {question_id})")

            # Generate a test answer
            test_answer = f"Test answer for question {question_num+1}"

            # Record question and answer
            questions_and_answers.append({
                "question_id": question_id,
                "question": question_text,
                "answer": test_answer
            })

            # Submit answer
            answer_result = await questionnaire_service.submit_answer(
                session_id=questionnaire_id,
                question_id=question_id,
                answer=test_answer
            )

            assert answer_result is not None, f"Failed to submit answer for question {question_num+1}"
            logger.info(f"Answer submitted successfully for question {question_num+1}")

        # Step 4: Complete questionnaire
        logger.info("Step 4: Completing questionnaire")

        completion_result = await questionnaire_service.complete_questionnaire(
            session_id=questionnaire_id
        )

        assert completion_result is not None, "Failed to complete questionnaire"
        assert "status" in completion_result, "Missing status in completion result"

        logger.info(f"Questionnaire completed with status: {completion_result.get('status')}")

        # Step 5: Rectify chart
        logger.info("Step 5: Rectifying chart")

        rectify_result = await chart_service.rectify_chart(
            chart_id=chart_id,
            questionnaire_id=questionnaire_id,
            answers=questions_and_answers,
            include_details=True
        )

        assert rectify_result is not None, "Failed to rectify chart"

        # The result could contain either a rectified_chart_id directly or a pending status
        rectified_chart_id = rectify_result.get("rectified_chart_id")

        # If the result doesn't have a rectified_chart_id, check for rectification_id and poll
        if not rectified_chart_id and "rectification_id" in rectify_result:
            logger.info("Rectification started asynchronously, polling for result...")

            rectification_id = rectify_result["rectification_id"]
            for _ in range(10):  # Poll up to 10 times (with 2-second delays)
                await asyncio.sleep(2)

                status_result = await chart_service.get_rectification_status(
                    rectification_id=rectification_id
                )

                if status_result and status_result.get("status") == "complete":
                    rectified_chart_id = status_result.get("rectified_chart_id")
                    break

        assert rectified_chart_id, "Failed to get rectified chart ID"
        logger.info(f"Chart rectified successfully with new ID: {rectified_chart_id}")

        # Step 6: Compare charts
        logger.info("Step 6: Comparing charts")

        compare_result = await chart_service.compare_charts(
            chart1_id=chart_id,
            chart2_id=rectified_chart_id
        )

        assert compare_result is not None, "Failed to compare charts"
        assert "chart1_id" in compare_result, "Missing chart1_id in comparison result"
        assert compare_result["chart1_id"] == chart_id, "Chart 1 ID mismatch"
        assert "chart2_id" in compare_result, "Missing chart2_id in comparison result"
        assert compare_result["chart2_id"] == rectified_chart_id, "Chart 2 ID mismatch"

        logger.info("Charts compared successfully")

        # Step 7: Export chart
        logger.info("Step 7: Exporting chart")

        export_result = await chart_service.export_chart(
            chart_id=rectified_chart_id,
            format="pdf"
        )

        assert export_result is not None, "Failed to export chart"
        assert "download_url" in export_result, "Missing download URL in export result"

        logger.info(f"Chart exported successfully with download URL: {export_result.get('download_url')}")

        # Test completed successfully
        logger.info("Full sequence flow test completed successfully with real API calls")

    except Exception as e:
        logger.error(f"Full sequence flow test failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_full_sequence_flow_real_api(
        birth_details={
            'birthDate': '1990-01-15',
            'birthTime': '14:30:00',
            'birthPlace': 'New York, NY',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'timezone': 'America/New_York'
        },
        chart_service=ChartService(openai_service=OpenAIService()),
        questionnaire_service=DynamicQuestionnaireService(openai_service=OpenAIService())
    ))
