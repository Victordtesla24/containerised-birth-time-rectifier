"""
Integration test for the questionnaire flow according to the "Consolidated API Questionnaire Flow"
section in the sequence diagram.

This test follows the exact flow specified in the sequence diagram without using any mocks
or fallbacks, ensuring all API calls, AI integrations, and database interactions are real.
"""

import pytest
import asyncio
import os
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required services for real implementation
from ai_service.api.services.questionnaire_service import DynamicQuestionnaireService
from ai_service.api.services.openai.service import OpenAIService
from ai_service.api.services.session_service import get_session_store
from ai_service.services.chart_service import ChartService
from ai_service.utils.geocoding import get_coordinates
from ai_service.core.validators import validate_birth_details

# Test data
TEST_BIRTH_DETAILS = {
    "birthDate": "1990-01-15",
    "birthTime": "08:30:00",
    "birthPlace": "Mumbai, India",
    "gender": "Female"
}

@pytest.fixture
async def openai_service():
    """Create a real OpenAI service instance."""
    return OpenAIService()

@pytest.fixture
async def session_store():
    """Create a real session store."""
    return get_session_store()

@pytest.fixture
async def chart_service(openai_service):
    """Create a real chart service with the OpenAI integration."""
    from ai_service.database.repositories import ChartRepository

    # Create a real connection to the database
    import asyncpg
    from ai_service.core.config import settings

    try:
        db_pool = await asyncpg.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        chart_repository = ChartRepository(db_pool=db_pool)
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}. Ensure the database is running.")

    # Return a real chart service with OpenAI integration
    return ChartService(
        openai_service=openai_service,
        chart_repository=chart_repository
    )

@pytest.fixture
async def questionnaire_service(openai_service):
    """Create a real questionnaire service with the OpenAI integration."""
    return DynamicQuestionnaireService(openai_service=openai_service)

@pytest.mark.asyncio
async def test_consolidated_questionnaire_flow(questionnaire_service, session_store, chart_service):
    """
    Test the consolidated API questionnaire flow as described in the sequence diagram.
    This test follows the exact flow without mocks:

    1. User starts questionnaire
    2. Backend generates initial question
    3. User answers question
    4. Backend caches answer and processes it
    5. Backend generates next question based on previous answers
    6. Process repeats until questionnaire is complete
    """
    logger.info("Starting consolidated questionnaire flow test")

    # 1. Create a session for the test
    session_id = str(uuid.uuid4())
    await session_store.create_session(session_id, {
        "created_at": datetime.now().isoformat(),
        "status": "active"
    })
    logger.info(f"Created session with ID: {session_id}")

    # 2. Geocode the birth location to get coordinates
    birth_place = TEST_BIRTH_DETAILS["birthPlace"]
    geocode_result = await get_coordinates(birth_place)

    # Ensure we have valid geocoding results
    assert geocode_result is not None, f"Failed to geocode location: {birth_place}"

    # Extract location data
    latitude = geocode_result["latitude"]
    longitude = geocode_result["longitude"]

    # Get timezone for the coordinates
    from ai_service.utils.timezone import get_timezone_for_coordinates
    timezone_info = await get_timezone_for_coordinates(latitude, longitude)

    # Ensure we have valid timezone information
    assert timezone_info is not None, f"Failed to get timezone for coordinates: {latitude}, {longitude}"

    timezone = timezone_info["timezone"]
    logger.info(f"Geocoded location: {birth_place} -> {latitude}, {longitude}, {timezone}")

    # Save birth details to session
    birth_details = {
        "birth_date": TEST_BIRTH_DETAILS["birthDate"],
        "birth_time": TEST_BIRTH_DETAILS["birthTime"],
        "birth_place": birth_place,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone
    }
    await session_store.update_session(session_id, {"birth_details": birth_details})

    # 3. Generate chart
    chart_result = await chart_service.generate_chart(
        birth_date=TEST_BIRTH_DETAILS["birthDate"],
        birth_time=TEST_BIRTH_DETAILS["birthTime"],
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        location=birth_place,
        verify_with_openai=True
    )
    chart_id = chart_result["chart_id"]
    logger.info(f"Generated chart with ID: {chart_id}")

    # 4. Initialize questionnaire - real implementation
    logger.info("Initializing questionnaire with real backend implementation")
    questionnaire_init = await questionnaire_service.initialize_questionnaire(
        chart_id=chart_id,
        session_id=session_id
    )

    # Verify initialization response structure
    assert "sessionId" in questionnaire_init, "Questionnaire init should return a session ID"
    assert "question" in questionnaire_init, "Questionnaire init should return the first question"

    # Extract question from response
    current_question = questionnaire_init["question"]
    logger.info(f"Received initial question: {current_question['text']}")

    # Process multiple questions to test the flow
    answers = []
    max_questions = 3  # Process at least 3 questions
    question_count = 0

    while current_question and question_count < max_questions:
        question_id = current_question["id"]
        question_text = current_question["text"]
        question_type = current_question["type"]

        logger.info(f"Processing question {question_count + 1}: {question_text}")

        # Generate a realistic answer based on question type
        answer = None
        if question_type == "yes_no":
            answer = "Yes"
        elif question_type == "multiple_choice" and "options" in current_question:
            # Select the first option
            answer = current_question["options"][0]["text"]
        else:
            answer = "Test answer for birth time rectification"

        logger.info(f"Submitting answer: {answer}")

        # Submit answer - real implementation
        answer_result = await questionnaire_service.submit_answer(
            session_id=session_id,
            question_id=question_id,
            answer=answer
        )

        # Verify answer submission response
        assert "status" in answer_result, "Answer submission should return a status"
        assert answer_result["status"] == "success", f"Answer should be accepted, got: {answer_result['status']}"

        # Store answer for later analysis
        answers.append({
            "questionId": question_id,
            "question": question_text,
            "answer": answer
        })

        # Get next question - real implementation
        next_question_result = await questionnaire_service.get_next_question(
            session_id=session_id,
            chart_id=chart_id
        )

        # Check if the questionnaire is complete
        if next_question_result.get("complete", False):
            logger.info("Questionnaire marked as complete")
            break

        # Get the next question
        current_question = next_question_result.get("question") or next_question_result.get("next_question")
        if current_question:
            question_count += 1
            logger.info(f"Received next question: {current_question['text']}")
        else:
            logger.warning("No next question received, ending questionnaire")
            break

    # Complete the questionnaire - real implementation
    logger.info("Completing questionnaire")
    completion_result = await questionnaire_service.complete_questionnaire(
        session_id=session_id
    )

    # Verify completion response
    assert "status" in completion_result, "Completion should return a status"
    assert completion_result["status"] in ["processing", "completed"], f"Unexpected completion status: {completion_result['status']}"

    # Verify we have analysis data
    assert "analysis" in completion_result, "Completion should include analysis"

    logger.info(f"Questionnaire completed with {len(answers)} questions answered")
    logger.info("Consolidated questionnaire flow test completed successfully")

if __name__ == "__main__":
    # Allow running the test directly
    asyncio.run(pytest.main(["-xvs", __file__]))
