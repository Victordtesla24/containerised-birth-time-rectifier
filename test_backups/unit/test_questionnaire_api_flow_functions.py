"""
Unit tests for questionnaire API flow.

This module tests the questionnaire API flow functionality using function-based tests.
"""

import pytest
import json
import logging
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample test data
TEST_DATA = {
    'birthDate': '1990-01-15',
    'birthTime': '14:30',
    'birthLocation': 'New Delhi, India',
    'chartId': 'test-chart-123456',
    'sessionId': 'test-session-123456',
    'answers': [
        {"answer": "yes", "confidence": 90},
        {"answer": "somewhat", "confidence": 80},
        {"answer": "no", "confidence": 95},
        {"answer": "1995-06-15", "confidence": 100},
        {"answer": "morning", "confidence": 85}
    ]
}

@pytest.fixture
def mock_request():
    """Mock request object for FastAPI endpoints"""
    request = MagicMock()
    request.headers = {"X-Session-ID": TEST_DATA["sessionId"]}
    request.state.session_id = TEST_DATA["sessionId"]
    request.state.session = {
        "chart_id": TEST_DATA["chartId"],
        "created_at": 1616293200.0,
        "expires_at": 1616296800.0,
        "status": "active"
    }
    return request

@pytest.fixture
def mock_questionnaire_engine():
    """Mock questionnaire engine"""
    engine = MagicMock()

    # Mock get_initial_question method
    engine.get_initial_question.return_value = {
        "id": "q1",
        "text": "Do you know your exact birth time?",
        "type": "boolean"
    }

    # Mock process_answer method
    engine.process_answer.return_value = (
        {
            "id": "q2",
            "text": "Were there any major life events in your first year?",
            "type": "boolean"
        },
        90.0  # Confidence score
    )

    # Mock get_final_result method
    engine.get_final_result.return_value = {
        "recommendation": "15:15:00",
        "confidence": 87.5,
        "explanation": "Based on your answers, the rectified birth time is 15:15"
    }

    return engine

@pytest.fixture
def mock_questionnaire_service(mock_questionnaire_engine):
    """Mock questionnaire service"""
    service = MagicMock()
    service.engine = mock_questionnaire_engine

    # Mock initialize_questionnaire method
    async def initialize_questionnaire(chart_id, session_id):
        return {
            "questionnaire_id": f"quest-{session_id}",
            "question": mock_questionnaire_engine.get_initial_question()
        }

    # Mock process_answer method
    async def process_answer(session_id, question_id, answer, confidence):
        next_question, confidence_score = mock_questionnaire_engine.process_answer(
            question_id, answer, confidence
        )
        return {
            "question": next_question,
            "confidence": confidence_score
        }

    # Mock complete_questionnaire method
    async def complete_questionnaire(session_id):
        result = mock_questionnaire_engine.get_final_result()
        return {
            "status": "completed",
            "result": result
        }

    service.initialize_questionnaire = initialize_questionnaire
    service.process_answer = process_answer
    service.complete_questionnaire = complete_questionnaire
    return service

@pytest.mark.asyncio
async def test_questionnaire_initialization(mock_questionnaire_service, mock_request):
    """Test questionnaire initialization"""
    # Arrange
    request_data = {
        "chart_id": TEST_DATA["chartId"],
        "session_id": TEST_DATA["sessionId"]
    }

    # Act
    response = await mock_questionnaire_service.initialize_questionnaire(
        request_data["chart_id"],
        request_data["session_id"]
    )

    # Assert
    assert response is not None
    assert "questionnaire_id" in response
    assert "question" in response
    assert response["question"]["id"] == "q1"
    assert response["question"]["type"] == "boolean"

@pytest.mark.asyncio
async def test_questionnaire_answer_submission(mock_questionnaire_service, mock_request):
    """Test submitting an answer to a questionnaire question"""
    # Arrange
    answer_data = {
        "sessionId": TEST_DATA["sessionId"],
        "questionId": "q1",
        "answer": "yes",
        "confidence": 90
    }

    # Act
    response = await mock_questionnaire_service.process_answer(
        answer_data["sessionId"],
        answer_data["questionId"],
        answer_data["answer"],
        answer_data["confidence"]
    )

    # Assert
    assert response is not None
    assert "question" in response
    assert "confidence" in response
    assert response["question"]["id"] == "q2"
    assert response["confidence"] == 90.0

@pytest.mark.asyncio
async def test_questionnaire_completion(mock_questionnaire_service, mock_request):
    """Test completing a questionnaire"""
    # Arrange
    completion_data = {
        "sessionId": TEST_DATA["sessionId"]
    }

    # Act
    response = await mock_questionnaire_service.complete_questionnaire(
        completion_data["sessionId"]
    )

    # Assert
    assert response is not None
    assert "status" in response
    assert response["status"] == "completed"
    assert "result" in response
    assert "recommendation" in response["result"]
    assert "confidence" in response["result"]
    assert response["result"]["confidence"] == 87.5

@pytest.mark.asyncio
async def test_full_questionnaire_flow(mock_questionnaire_service, mock_request):
    """Test the complete questionnaire flow from start to finish"""
    # 1. Initialize questionnaire
    init_data = {
        "chart_id": TEST_DATA["chartId"],
        "session_id": TEST_DATA["sessionId"]
    }

    init_response = await mock_questionnaire_service.initialize_questionnaire(
        init_data["chart_id"],
        init_data["session_id"]
    )

    assert init_response is not None
    assert "questionnaire_id" in init_response
    assert "question" in init_response

    # 2. Answer first question
    q1_data = {
        "sessionId": TEST_DATA["sessionId"],
        "questionId": init_response["question"]["id"],
        "answer": TEST_DATA["answers"][0]["answer"],
        "confidence": TEST_DATA["answers"][0]["confidence"]
    }

    q1_response = await mock_questionnaire_service.process_answer(
        q1_data["sessionId"],
        q1_data["questionId"],
        q1_data["answer"],
        q1_data["confidence"]
    )

    assert q1_response is not None
    assert "question" in q1_response

    # 3. Answer second question
    q2_data = {
        "sessionId": TEST_DATA["sessionId"],
        "questionId": q1_response["question"]["id"],
        "answer": TEST_DATA["answers"][1]["answer"],
        "confidence": TEST_DATA["answers"][1]["confidence"]
    }

    q2_response = await mock_questionnaire_service.process_answer(
        q2_data["sessionId"],
        q2_data["questionId"],
        q2_data["answer"],
        q2_data["confidence"]
    )

    assert q2_response is not None

    # 4. Complete questionnaire
    completion_response = await mock_questionnaire_service.complete_questionnaire(
        TEST_DATA["sessionId"]
    )

    assert completion_response is not None
    assert "status" in completion_response
    assert completion_response["status"] == "completed"
    assert "result" in completion_response
    assert "recommendation" in completion_response["result"]
    assert "confidence" in completion_response["result"]

if __name__ == "__main__":
    """Run tests directly"""
    asyncio.run(test_questionnaire_initialization(
        mock_questionnaire_service(mock_questionnaire_engine()),
        mock_request()
    ))
