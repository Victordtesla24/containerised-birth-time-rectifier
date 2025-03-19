"""
Integration test for questionnaire functionality using real API calls.

This test ensures the questionnaire service works with actual API dependencies,
real OpenAI calls, and real ephemeris data calculations.
"""

import pytest
import logging
import os
import asyncio
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required modules
from ai_service.utils.env_loader import load_env_file, get_openai_api_key
from ai_service.api.services.openai.service import OpenAIService
from ai_service.services.chart_service import ChartService
from ai_service.api.services.questionnaire_service import DynamicQuestionnaireService, get_questionnaire_service

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
    """Fixture providing standard birth details for testing."""
    return {
        'birthDate': '1990-01-01',
        'birthTime': '12:00',
        'birthPlace': 'New York, NY',
        'latitude': 40.7128,
        'longitude': -74.0060,
        'timezone': 'America/New_York'
    }

@pytest.mark.integration
@pytest.mark.asyncio
async def test_questionnaire_next_question_real_api():
    """Test generating the next question using real API services."""
    try:
        # Create real services (not mocks)
        openai_service = OpenAIService()
        questionnaire_service = DynamicQuestionnaireService(openai_service=openai_service)

        # Prepare test data
        birth_details = {
            'birthDate': '1990-01-01',
            'birthTime': '12:00',
            'birthPlace': 'New York, NY',
            'latitude': 40.7128,
            'longitude': -74.0060
        }

        # Make a real API call to generate the next question
        result = await questionnaire_service.generate_next_question(
            birth_details=birth_details,
            previous_answers={}
        )

        # Validate the response structure
        assert isinstance(result, dict)
        assert "error" not in result, f"Error in response: {result.get('error', 'Unknown error')}"
        assert "next_question" in result, "Missing next_question in response"

        # Extract and validate the question object
        next_question = result.get('next_question', {})
        assert "text" in next_question, "Missing text in next_question"
        assert "id" in next_question, "Missing question_id in next_question"
        assert "type" in next_question, "Missing question type in next_question"

        logger.info(f"Successfully generated question: {next_question.get('text')}")

    except Exception as e:
        logger.error(f"Error testing questionnaire with real API: {e}")
        raise

@pytest.mark.integration
@pytest.mark.asyncio
async def test_questionnaire_with_previous_answers_real_api():
    """Test questionnaire with previous answers using real API services."""
    try:
        # Create real services (not mocks)
        openai_service = OpenAIService()
        questionnaire_service = DynamicQuestionnaireService(openai_service=openai_service)

        # Prepare test data
        birth_details = {
            'birthDate': '1990-01-01',
            'birthTime': '12:00',
            'birthPlace': 'New York, NY',
            'latitude': 40.7128,
            'longitude': -74.0060
        }

        # Create sample previous answers
        previous_answers = {
            "responses": [
                {
                    "question_id": "q1",
                    "question": "Did you experience any significant life events around age 25?",
                    "answer": "Yes, I got married and changed careers.",
                    "topic": "life_events",
                    "quality": 0.8
                }
            ]
        }

        # Make a real API call to generate the next question
        result = await questionnaire_service.generate_next_question(
            birth_details=birth_details,
            previous_answers=previous_answers
        )

        # Validate the response structure
        assert isinstance(result, dict)
        assert "error" not in result, f"Error in response: {result.get('error', 'Unknown error')}"
        assert "next_question" in result, "Missing next_question in response"

        # Extract and validate the question object
        next_question = result.get('next_question', {})
        assert "text" in next_question, "Missing text in next_question"
        assert "id" in next_question, "Missing question_id in next_question"
        assert "type" in next_question, "Missing question type in next_question"

        # Verify the question is different from the previous one
        assert next_question.get("id") != "q1", "Should generate a different question"

        logger.info(f"Successfully generated follow-up question: {next_question.get('text')}")

    except Exception as e:
        logger.error(f"Error testing questionnaire with previous answers: {e}")
        raise

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_questionnaire_flow_real_api():
    """Test a complete questionnaire flow with multiple questions using real API services."""
    try:
        # Create real services (not mocks)
        openai_service = OpenAIService()
        questionnaire_service = DynamicQuestionnaireService(openai_service=openai_service)

        # Prepare test data
        birth_details = {
            'birthDate': '1990-01-01',
            'birthTime': '12:00',
            'birthPlace': 'New York, NY',
            'latitude': 40.7128,
            'longitude': -74.0060
        }

        # Initial empty answers
        previous_answers = {"responses": []}

        # Generate 3 questions in sequence
        for i in range(3):
            # Make a real API call to generate the next question
            result = await questionnaire_service.generate_next_question(
                birth_details=birth_details,
                previous_answers=previous_answers
            )

            # Validate the response structure
            assert isinstance(result, dict)
            assert "error" not in result, f"Error in response: {result.get('error', 'Unknown error')}"
            assert "next_question" in result, "Missing next_question in response"

            # Extract the question object
            next_question = result.get('next_question', {})
            assert "text" in next_question, "Missing text in next_question"
            assert "id" in next_question, "Missing question_id in next_question"

            # Add a simulated answer to this question
            previous_answers["responses"].append({
                "question_id": next_question.get("id"),
                "question": next_question.get("text"),
                "answer": f"Test answer for question {i+1}",
                "topic": next_question.get("astrological_factors", ["general"])[0],
                "quality": 0.7
            })

            logger.info(f"Question {i+1}: {next_question.get('text')}")
            logger.info(f"Answer {i+1}: Test answer for question {i+1}")

        # Verify we have 3 responses stored
        assert len(previous_answers["responses"]) == 3, "Should have 3 responses"

        # Check that all question IDs are different
        question_ids = [resp["question_id"] for resp in previous_answers["responses"]]
        assert len(question_ids) == len(set(question_ids)), "All question IDs should be unique"

        logger.info("Successfully completed full questionnaire flow with real API")

    except Exception as e:
        logger.error(f"Error testing full questionnaire flow: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_questionnaire_next_question_real_api())
    asyncio.run(test_questionnaire_with_previous_answers_real_api())
    asyncio.run(test_full_questionnaire_flow_real_api())
