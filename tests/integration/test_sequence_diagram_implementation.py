"""
Test file to verify the implementation of the sequence diagram.
This focuses on testing the API endpoints and flow defined in docs/architecture/sequence_diagram.md

This implementation uses real services with no mocks or fallbacks to verify:
1. Session initialization
2. Geocoding
3. Chart validation and generation
4. Chart retrieval
5. Questionnaire flow
6. Birth time rectification
7. Chart comparison
8. Chart export

Every API call and calculation is real to ensure the system works as described in the sequence diagram.
"""

import pytest
import os
import re
import json
import time
import logging
import uuid
import asyncio
from typing import Dict, Any
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required services for real implementation
from ai_service.api.services.session_service import get_session_store
from ai_service.services.chart_service import get_chart_service, ChartService
from ai_service.api.services.questionnaire_service import get_questionnaire_service, DynamicQuestionnaireService
from ai_service.api.services.openai.service import OpenAIService
from ai_service.utils.geocoding import get_coordinates
from ai_service.utils.timezone import get_timezone_for_coordinates
from ai_service.core.validators import validate_birth_details
from ai_service.core.rectification.main import comprehensive_rectification

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
    # We'll use a real database connection to ensure the test is accurate
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

# The actual test
@pytest.mark.asyncio
async def test_sequence_diagram_implementation(openai_service, session_store, chart_service, questionnaire_service):
    """
    Test the implementation of the sequence diagram.

    This test verifies that all components in the sequence diagram are properly implemented
    using real endpoints and real calculations with no mocks or fallbacks.

    The test exactly follows the flow defined in docs/architecture/sequence_diagram.md
    section "Original Sequence Diagram - Full Implementation":
    """
    logger.info("Starting sequence diagram implementation test using REAL implementations")

    # Initialize variables to track implementation status
    chart_id = None
    rectified_chart_id = None
    questionnaire_id = None
    session_id = None

    try:
        # Step 1: Initialize session
        logger.info("Step 1: Initialize session")
        session_id = str(uuid.uuid4())
        session_data = {
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        await session_store.create_session(session_id, session_data)
        logger.info(f"Session initialized with ID: {session_id}")

        # Step 2: Geocode the birth location
        logger.info("Step 2: Geocode birth location")
        birth_place = TEST_BIRTH_DETAILS["birthPlace"]
        geocode_result = await get_coordinates(birth_place)

        # Ensure we have valid geocoding results
        assert geocode_result is not None, f"Failed to geocode location: {birth_place}"

        # Extract location data
        latitude = geocode_result["latitude"]
        longitude = geocode_result["longitude"]

        # Get timezone for the coordinates
        timezone_info = await get_timezone_for_coordinates(latitude, longitude)
        assert timezone_info is not None, f"Failed to get timezone for coordinates: {latitude}, {longitude}"
        timezone = timezone_info["timezone"]

        logger.info(f"Geocoded location: {birth_place} -> {latitude}, {longitude}, {timezone}")

        # Save location data to session
        location_data = {
            "birth_place": birth_place,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone
        }
        await session_store.update_session(session_id, {"location": location_data})

        # Step 3: Validate birth details
        logger.info("Step 3: Validate birth details")
        birth_date = TEST_BIRTH_DETAILS["birthDate"]
        birth_time = TEST_BIRTH_DETAILS["birthTime"]

        validation_result = await validate_birth_details(
            birth_date=birth_date,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone
        )

        # Verify validation result
        assert validation_result.get("valid", False), f"Birth details validation failed: {validation_result.get('errors')}"
        logger.info(f"Birth details validated successfully: {birth_date} {birth_time}")

        # Step 4: Generate chart
        logger.info("Step 4: Generate chart with OpenAI verification")
        chart_result = await chart_service.generate_chart(
            birth_date=birth_date,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            location=birth_place,
            verify_with_openai=True  # Use real OpenAI verification
        )

        # Verify chart generation result
        assert "chart_id" in chart_result, "Chart generation should return a chart ID"
        chart_id = chart_result["chart_id"]

        # Check verification data
        verification = chart_result.get("verification", {})
        logger.info(f"Chart generated with ID: {chart_id}")
        if verification:
            logger.info(f"Chart verified with confidence: {verification.get('confidence')}")

        # Step 5: Retrieve chart
        logger.info("Step 5: Retrieve chart data")
        retrieved_chart = await chart_service.get_chart(chart_id)

        # Verify retrieved chart
        assert retrieved_chart is not None, f"Failed to retrieve chart with ID: {chart_id}"
        assert "planets" in retrieved_chart, "Retrieved chart should include planets data"
        assert "houses" in retrieved_chart, "Retrieved chart should include houses data"
        logger.info("Chart retrieved successfully with all required data")

        # Step 6: Start questionnaire flow
        logger.info("Step 6: Start questionnaire flow")
        questionnaire_init = await questionnaire_service.initialize_questionnaire(
            chart_id=chart_id,
            session_id=session_id
        )

        # Verify questionnaire initialization
        assert "sessionId" in questionnaire_init, "Questionnaire init should return a session ID"
        assert "question" in questionnaire_init, "Questionnaire init should return the first question"

        questionnaire_id = questionnaire_init.get("sessionId", session_id)
        current_question = questionnaire_init.get("question")

        # Process multiple questions
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

            # Submit answer
            answer_result = await questionnaire_service.submit_answer(
                session_id=session_id,
                question_id=question_id,
                answer=answer
            )

            # Store answer for later analysis
            answers.append({
                "questionId": question_id,
                "answer": answer,
                "confidence": 85  # Default confidence level
            })

            # Get next question
            next_question_result = await questionnaire_service.get_next_question(
                session_id=session_id,
                chart_id=chart_id
            )

            # Check if questionnaire is complete
            if next_question_result.get("complete", False):
                logger.info("Questionnaire marked as complete")
                break

            # Get the next question
            current_question = next_question_result.get("question") or next_question_result.get("next_question")
            if current_question:
                question_count += 1
            else:
                break

        # Complete the questionnaire
        logger.info("Completing questionnaire")
        completion_result = await questionnaire_service.complete_questionnaire(
            session_id=session_id
        )

        logger.info(f"Questionnaire completed with {len(answers)} questions answered")

        # Step 7: Birth time rectification
        logger.info("Step 7: Birth time rectification")

        # Parse birth datetime for rectification
        birth_datetime = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M:%S")

        # Use comprehensive rectification to get the final result
        rectification_result = await comprehensive_rectification(
            birth_dt=birth_datetime,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            answers=answers
        )

        # Verify rectification result
        rectified_time = rectification_result.get("rectified_time")
        assert rectified_time is not None, "Rectification should return a valid time"

        # Extract rectified chart ID
        rectified_chart_id = rectification_result.get("rectified_chart_id")
        assert rectified_chart_id is not None, "Rectification should generate a new chart ID"

        logger.info(f"Rectification completed: Original time: {birth_time}, Rectified time: {rectified_time}")

        # Step 8: Compare charts
        logger.info("Step 8: Compare charts")
        comparison_result = await chart_service.compare_charts(
            chart1_id=chart_id,  # Original chart
            chart2_id=rectified_chart_id  # Rectified chart
        )

        # Verify comparison result
        assert "comparison_id" in comparison_result, "Chart comparison should return a comparison ID"
        assert "differences" in comparison_result, "Chart comparison should include differences data"

        comparison_id = comparison_result["comparison_id"]
        logger.info(f"Charts compared successfully with ID: {comparison_id}")

        # Step 9: Export chart
        logger.info("Step 9: Export chart")
        export_result = await chart_service.export_chart(
            chart_id=rectified_chart_id,
            format="pdf"
        )

        # Verify export result
        assert "export_id" in export_result, "Chart export should return an export ID"
        assert "download_url" in export_result, "Chart export should include a download URL"

        download_url = export_result["download_url"]
        logger.info(f"Chart exported successfully with URL: {download_url}")

        # Test completed successfully
        logger.info("Sequence diagram implementation test completed successfully")

    except Exception as e:
        logger.error(f"Sequence diagram test failed: {str(e)}")
        # Clean and specific error for debugging
        logger.error(f"Error occurred at step with session_id={session_id}, chart_id={chart_id}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    # For running the test directly
    asyncio.run(pytest.main(["-xvs", __file__]))
