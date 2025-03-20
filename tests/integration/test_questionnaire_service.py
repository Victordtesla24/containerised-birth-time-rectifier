"""
Integration tests for QuestionnaireService.

These tests validate the questionnaire service against the "Consolidated API Questionnaire Flow"
sequence diagram, using real API calls without mocks.
"""

import pytest
import asyncio
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List

from ai_service.api.services.questionnaire_service import QuestionnaireService
from ai_service.api.services.openai.service import OpenAIService
from ai_service.api.services.session_service import SessionService
from ai_service.services.chart_service import ChartService

@pytest.fixture
async def openai_service():
    """Create a real OpenAI service instance."""
    # Skip if no API key is available
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OpenAI API key not available")

    # Create and return a real OpenAI service
    return OpenAIService()

@pytest.fixture
async def session_service():
    """Create a real session service instance."""
    return SessionService()

@pytest.fixture
async def questionnaire_service(openai_service, session_service):
    """Create a real questionnaire service instance."""
    return QuestionnaireService(openai_service=openai_service)

@pytest.fixture
async def chart_service(openai_service):
    """Create a real chart service instance."""
    return ChartService(openai_service=openai_service)

@pytest.mark.asyncio
async def test_questionnaire_flow(questionnaire_service, session_service, chart_service):
    """
    Test the complete questionnaire flow as defined in the sequence diagram.

    This test follows the "Consolidated API Questionnaire Flow" sequence:
    1. Start questionnaire
    2. Get initial question
    3. Answer question
    4. Get next question
    5. Complete questionnaire
    """
    # 1. Create session
    session_id = str(uuid.uuid4())
    await session_service.create_session(session_id)

    # Create birth details
    birth_details = {
        "birthDate": "1990-01-01",
        "birthTime": "12:00:00",
        "birthPlace": "New York, NY, USA",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York"
    }

    # Store birth details in session
    await session_service.update_session_data(session_id, {"birth_details": birth_details})

    # 2. Generate a chart first
    chart = await chart_service.generate_chart(
        birth_date=birth_details["birthDate"],
        birth_time=birth_details["birthTime"],
        latitude=birth_details["latitude"],
        longitude=birth_details["longitude"],
        timezone=birth_details["timezone"],
        verify_with_openai=False
    )

    # Save the chart
    saved_chart = await chart_service.save_chart(chart)
    chart_id = saved_chart.get("chart_id")

    # 3. Initialize questionnaire
    questionnaire = await questionnaire_service.initialize_questionnaire(chart_id, session_id)

    # Verify initialization response
    assert "questionnaire_id" in questionnaire
    questionnaire_id = questionnaire["questionnaire_id"]

    # 4. Get initial question
    initial_question = await questionnaire_service.get_next_question(session_id, chart_id)

    # Verify question structure
    assert "question" in initial_question
    question = initial_question["question"]
    assert "id" in question
    assert "text" in question
    assert "type" in question

    question_id = question["id"]

    # 5. Submit an answer
    answer_value = "Yes" if question["type"] == "yes_no" else "This is a test answer"
    answer_result = await questionnaire_service.submit_answer(
        session_id=session_id,
        question_id=question_id,
        answer=answer_value
    )

    # Verify answer submission response
    assert "status" in answer_result
    assert answer_result["status"] == "success"
    assert "next_question" in answer_result

    # 6. Get next question
    next_question = await questionnaire_service.get_next_question(session_id, chart_id)

    # Verify next question structure
    assert "question" in next_question
    question = next_question["question"]
    assert "id" in question
    assert "text" in question
    assert "type" in question

    # Submit another answer
    question_id = question["id"]
    answer_value = "No" if question["type"] == "yes_no" else "Another test answer"
    answer_result = await questionnaire_service.submit_answer(
        session_id=session_id,
        question_id=question_id,
        answer=answer_value
    )

    # 7. Complete the questionnaire
    completion_result = await questionnaire_service.complete_questionnaire(session_id, chart_id)

    # Verify completion response
    assert "status" in completion_result
    assert completion_result["status"] in ["processing", "completed"]
    assert "analysis" in completion_result

    # Verify analysis data
    analysis = completion_result["analysis"]
    assert "birth_time_indicators" in analysis
    assert isinstance(analysis["birth_time_indicators"], list)
    assert "comprehensive_analysis" in analysis
    assert isinstance(analysis["comprehensive_analysis"], dict)

@pytest.mark.asyncio
async def test_get_initial_questions(questionnaire_service):
    """Test getting initial questions based on birth details."""
    # Test birth details
    birth_details = {
        "birthDate": "1990-01-01",
        "birthTime": "12:00:00",
        "birthPlace": "New York, NY, USA",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York"
    }

    # Get initial questions
    questions = await questionnaire_service.get_initial_questions(birth_details)

    # Verify questions structure
    assert isinstance(questions, list)
    assert len(questions) > 0

    # Check first question
    question = questions[0]
    assert "id" in question
    assert "text" in question
    assert "type" in question

    # Verify question types are valid
    for question in questions:
        assert "type" in question
        assert question["type"] in [
            "yes_no", "multiple_choice", "open_text",
            "time_event", "date_event", "slider"
        ]

@pytest.mark.asyncio
async def test_generate_next_question(questionnaire_service):
    """Test generating the next question based on previous answers."""
    # Test birth details
    birth_details = {
        "birthDate": "1990-01-01",
        "birthTime": "12:00:00",
        "birthPlace": "New York, NY, USA",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York"
    }

    # Create previous answers
    previous_answers = [
        {
            "question_id": "q_1",
            "question": "Were you born during the day or at night?",
            "answer": "Day",
            "type": "multiple_choice",
            "timestamp": datetime.now().isoformat()
        }
    ]

    # Generate next question
    next_question = await questionnaire_service.generate_next_question(
        birth_details=birth_details,
        previous_answers=previous_answers
    )

    # Verify question structure
    assert isinstance(next_question, dict)
    assert "id" in next_question
    assert "text" in next_question
    assert "type" in next_question

    # Verify the question is relevant
    assert "category" in next_question
    assert "relevance" in next_question

@pytest.mark.asyncio
async def test_submit_answer(questionnaire_service, session_service):
    """Test submitting an answer to a question."""
    # Create session
    session_id = str(uuid.uuid4())
    await session_service.create_session(session_id)

    # Create a question
    question = {
        "id": f"q_{uuid.uuid4().hex[:8]}",
        "text": "Were you born during the day or at night?",
        "type": "multiple_choice",
        "category": "birth_time",
        "relevance": "Helps determine general time of birth",
        "options": [
            {"id": "opt_1", "text": "Day"},
            {"id": "opt_2", "text": "Night"},
            {"id": "opt_3", "text": "Unknown"}
        ]
    }

    # Store question in session
    await session_service.update_session_data(
        session_id,
        {
            "current_question": question,
            "birth_details": {
                "birthDate": "1990-01-01",
                "birthTime": "12:00:00",
                "timezone": "America/New_York"
            }
        }
    )

    # Submit an answer
    answer_result = await questionnaire_service.submit_answer(
        session_id=session_id,
        question_id=question["id"],
        answer="Day"
    )

    # Verify answer submission response
    assert "status" in answer_result
    assert answer_result["status"] == "success"
    assert "next_question" in answer_result

    # Get updated session data
    session_data = await session_service.get_session_data(session_id)

    # Verify the answer was stored
    assert "answers" in session_data
    assert len(session_data["answers"]) > 0

    # Check the stored answer
    stored_answer = session_data["answers"][0]
    assert stored_answer["question_id"] == question["id"]
    assert stored_answer["answer"] == "Day"

@pytest.mark.asyncio
async def test_complete_questionnaire(questionnaire_service, session_service, chart_service):
    """Test completing a questionnaire with analysis."""
    # Create session
    session_id = str(uuid.uuid4())
    await session_service.create_session(session_id)

    # Birth details
    birth_details = {
        "birthDate": "1990-01-01",
        "birthTime": "12:00:00",
        "birthPlace": "New York, NY, USA",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York"
    }

    # Store birth details in session
    await session_service.update_session_data(session_id, {"birth_details": birth_details})

    # Generate a chart
    chart = await chart_service.generate_chart(
        birth_date=birth_details["birthDate"],
        birth_time=birth_details["birthTime"],
        latitude=birth_details["latitude"],
        longitude=birth_details["longitude"],
        timezone=birth_details["timezone"],
        verify_with_openai=False
    )

    # Save the chart
    saved_chart = await chart_service.save_chart(chart)
    chart_id = saved_chart.get("chart_id")

    # Create answers
    answers = [
        {
            "question_id": "q_1",
            "question": "Were you born during the day or at night?",
            "answer": "Day",
            "type": "multiple_choice",
            "timestamp": datetime.now().isoformat()
        },
        {
            "question_id": "q_2",
            "question": "According to family accounts, was your birth early, on time, or late?",
            "answer": "On time",
            "type": "multiple_choice",
            "timestamp": datetime.now().isoformat()
        },
        {
            "question_id": "q_3",
            "question": "Have you been told any specific details about the timing of your birth?",
            "answer": "Born around noon according to my mother",
            "type": "open_text",
            "timestamp": datetime.now().isoformat()
        }
    ]

    # Store answers in session
    await session_service.update_session_data(session_id, {"answers": answers})

    # Complete the questionnaire
    completion_result = await questionnaire_service.complete_questionnaire(session_id, chart_id)

    # Verify completion response
    assert "status" in completion_result
    assert completion_result["status"] in ["processing", "completed"]
    assert "analysis" in completion_result

    # Verify analysis data
    analysis = completion_result["analysis"]
    assert "birth_time_indicators" in analysis
    assert isinstance(analysis["birth_time_indicators"], list)
    assert "comprehensive_analysis" in analysis
    assert isinstance(analysis["comprehensive_analysis"], dict)
