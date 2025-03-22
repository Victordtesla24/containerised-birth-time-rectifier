"""
Unit tests for API endpoints to ensure they comply with the "Original Sequence Diagram - Full Implementation"
as defined in docs/architecture/sequence_diagram.md.

These tests validate that all required endpoints exist and follow the correct structure.
"""

import pytest
import os
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required modules
from ai_service.app_wrapper import app_wrapper
from ai_service.main import app
from fastapi.testclient import TestClient

# Test data
TEST_BIRTH_DETAILS = {
    "birthDate": "1990-01-15",
    "birthTime": "08:30:00",
    "birthPlace": "Mumbai, India",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "timezone": "Asia/Kolkata"
}

@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    return TestClient(app_wrapper)

def test_session_init_endpoint(test_client):
    """
    Test the session initialization endpoint from the sequence diagram:
    'GET /api/session/init' - Create Session In Redis
    """
    response = test_client.get("/api/session/init")

    # Check response status
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response structure
    data = response.json()
    assert "session_id" in data, "Response should include a session_id"
    assert isinstance(data["session_id"], str), "session_id should be a string"

    logger.info(f"Session initialized with ID: {data['session_id']}")

def test_geocode_endpoint(test_client):
    """
    Test the geocoding endpoint from the sequence diagram:
    'POST /api/geocode' - Location DB Coordinates Timezone
    """
    # Create a test session
    session_response = test_client.get("/api/session/init")
    session_id = session_response.json()["session_id"]

    # Test geocoding endpoint
    payload = {
        "query": TEST_BIRTH_DETAILS["birthPlace"],
        "session_id": session_id
    }

    headers = {"X-Session-ID": session_id}
    response = test_client.post("/api/geocode", json=payload, headers=headers)

    # Check response status
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response structure
    data = response.json()
    assert "results" in data, "Response should include results"
    assert len(data["results"]) > 0, "Results should not be empty"

    # Check first result structure
    result = data["results"][0]
    assert "latitude" in result, "Result should include latitude"
    assert "longitude" in result, "Result should include longitude"
    assert "display_name" in result, "Result should include display_name"

    logger.info(f"Geocoded location: {result['display_name']} -> {result['latitude']}, {result['longitude']}")

def test_chart_validate_endpoint(test_client):
    """
    Test the chart validation endpoint from the sequence diagram:
    'POST /api/chart/validate' - Format Check Date/Time Verification
    """
    # Create a test session
    session_response = test_client.get("/api/session/init")
    session_id = session_response.json()["session_id"]

    # Test validation endpoint
    payload = {
        "birth_date": TEST_BIRTH_DETAILS["birthDate"],
        "birth_time": TEST_BIRTH_DETAILS["birthTime"],
        "latitude": TEST_BIRTH_DETAILS["latitude"],
        "longitude": TEST_BIRTH_DETAILS["longitude"],
        "timezone": TEST_BIRTH_DETAILS["timezone"],
        "session_id": session_id
    }

    headers = {"X-Session-ID": session_id}
    response = test_client.post("/api/chart/validate", json=payload, headers=headers)

    # Check response status
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response structure
    data = response.json()
    assert "valid" in data, "Response should include valid status"
    assert isinstance(data["valid"], bool), "valid should be a boolean"

    if not data["valid"]:
        assert "errors" in data, "Invalid response should include errors"

    logger.info(f"Chart validation result: {data['valid']}")

def test_chart_generate_endpoint(test_client):
    """
    Test the chart generation endpoint from the sequence diagram:
    'POST /api/chart/generate' - Calculate Initial Chart
    """
    # Create a test session
    session_response = test_client.get("/api/session/init")
    session_id = session_response.json()["session_id"]

    # Test chart generation endpoint
    payload = {
        "birth_date": TEST_BIRTH_DETAILS["birthDate"],
        "birth_time": TEST_BIRTH_DETAILS["birthTime"],
        "latitude": TEST_BIRTH_DETAILS["latitude"],
        "longitude": TEST_BIRTH_DETAILS["longitude"],
        "timezone": TEST_BIRTH_DETAILS["timezone"],
        "location": TEST_BIRTH_DETAILS["birthPlace"],
        "verify_with_openai": True,
        "session_id": session_id
    }

    headers = {"X-Session-ID": session_id}
    response = test_client.post("/api/chart/generate", json=payload, headers=headers)

    # Check response status
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response structure
    data = response.json()
    assert "chart_id" in data, "Response should include chart_id"
    assert isinstance(data["chart_id"], str), "chart_id should be a string"

    # Check verification data
    assert "verification" in data, "Response should include verification data"
    verification = data["verification"]
    assert "verified" in verification, "Verification should include verified status"
    assert "confidence_score" in verification, "Verification should include confidence_score"

    logger.info(f"Chart generated with ID: {data['chart_id']}")

    return data["chart_id"]  # Return chart_id for use in other tests

def test_chart_get_endpoint(test_client):
    """
    Test the chart retrieval endpoint from the sequence diagram:
    'GET /api/chart/{chart_id}' - Query DB Return Chart Data
    """
    # First generate a chart
    chart_id = test_chart_generate_endpoint(test_client)

    # Test chart retrieval endpoint
    response = test_client.get(f"/api/chart/{chart_id}")

    # Check response status
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response structure
    data = response.json()
    assert "planets" in data, "Response should include planets data"
    assert "houses" in data, "Response should include houses data"
    assert "aspects" in data, "Response should include aspects data"

    logger.info(f"Retrieved chart with ID: {chart_id}")

def test_questionnaire_endpoint(test_client):
    """
    Test the questionnaire endpoints from the sequence diagram:
    'GET /questionnaire' - Generate Questions
    'POST /questionnaire/{id}/answer' - Process Answer
    """
    # Create a test session
    session_response = test_client.get("/api/session/init")
    session_id = session_response.json()["session_id"]

    # First generate a chart
    chart_id = test_chart_generate_endpoint(test_client)

    # Test questionnaire initialization endpoint
    init_payload = {
        "chart_id": chart_id,
        "session_id": session_id
    }

    headers = {"X-Session-ID": session_id}
    init_response = test_client.post("/api/questionnaire/init", json=init_payload, headers=headers)

    # Check response status
    assert init_response.status_code == 200, f"Expected status code 200, got {init_response.status_code}"

    # Check response structure
    init_data = init_response.json()
    assert "question" in init_data, "Response should include initial question"
    assert "sessionId" in init_data, "Response should include sessionId"

    question = init_data["question"]
    assert "id" in question, "Question should include id"
    assert "text" in question, "Question should include text"
    assert "type" in question, "Question should include type"

    logger.info(f"Received initial question: {question['text']}")

    # Test answer submission endpoint
    answer_payload = {
        "question_id": question["id"],
        "answer": "Yes" if question["type"] == "yes_no" else "Test answer"
    }

    answer_response = test_client.post("/api/questionnaire/answer", json=answer_payload, headers=headers)

    # Check response status
    assert answer_response.status_code == 200, f"Expected status code 200, got {answer_response.status_code}"

    # Check response structure
    answer_data = answer_response.json()
    assert "status" in answer_data, "Response should include status"
    assert answer_data["status"] == "success", f"Expected status 'success', got '{answer_data['status']}'"

    # Test getting next question
    next_response = test_client.get(f"/api/questionnaire/next?session_id={session_id}&chart_id={chart_id}", headers=headers)

    # Check response status
    assert next_response.status_code == 200, f"Expected status code 200, got {next_response.status_code}"

    # Check response structure
    next_data = next_response.json()
    assert "question" in next_data or "next_question" in next_data, "Response should include next question"

    logger.info("Questionnaire flow tested successfully")

def test_chart_rectify_endpoint(test_client):
    """
    Test the chart rectification endpoint from the sequence diagram:
    'POST /api/chart/rectify' - AI Analysis Algorithm Calculate Time
    """
    # Create a test session
    session_response = test_client.get("/api/session/init")
    session_id = session_response.json()["session_id"]

    # First generate a chart
    chart_id = test_chart_generate_endpoint(test_client)

    # Create sample answers for rectification
    answers = [
        {
            "questionId": "q_career_1",
            "answer": "Yes, I had a significant career change",
            "confidence": 90
        },
        {
            "questionId": "q_relationship_1",
            "answer": "Got married in 2015",
            "confidence": 85
        }
    ]

    # Test rectification endpoint
    payload = {
        "chart_id": chart_id,
        "questionnaire_id": session_id,
        "answers": answers
    }

    headers = {"X-Session-ID": session_id}
    response = test_client.post("/api/chart/rectify", json=payload, headers=headers)

    # Check response status
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response structure
    data = response.json()
    assert "rectified_time" in data, "Response should include rectified_time"
    assert "confidence_score" in data, "Response should include confidence_score"
    assert "rectified_chart_id" in data, "Response should include rectified_chart_id"

    logger.info(f"Rectified time: {data['rectified_time']}")
    logger.info(f"Confidence score: {data['confidence_score']}")

    return data["rectified_chart_id"]  # Return rectified chart ID for use in other tests

def test_chart_compare_endpoint(test_client):
    """
    Test the chart comparison endpoint from the sequence diagram:
    'GET /api/chart/compare' - Analyze Differences
    """
    # Create a test session
    session_response = test_client.get("/api/session/init")
    session_id = session_response.json()["session_id"]

    # First generate a regular chart
    original_chart_id = test_chart_generate_endpoint(test_client)

    # Then generate a rectified chart
    rectified_chart_id = test_chart_rectify_endpoint(test_client)

    # Test comparison endpoint
    response = test_client.get(f"/api/chart/compare?chart1={original_chart_id}&chart2={rectified_chart_id}")

    # Check response status
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response structure
    data = response.json()
    assert "comparison_id" in data, "Response should include comparison_id"
    assert "differences" in data, "Response should include differences data"

    logger.info(f"Compared charts. Found {len(data['differences'])} differences")

def test_chart_export_endpoint(test_client):
    """
    Test the chart export endpoint from the sequence diagram:
    'POST /api/chart/export' - Generate PDF Download File
    """
    # First generate a chart
    chart_id = test_chart_generate_endpoint(test_client)

    # Test export endpoint
    payload = {
        "chart_id": chart_id,
        "format": "pdf"
    }

    response = test_client.post("/api/chart/export", json=payload)

    # Check response status
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    # Check response structure
    data = response.json()
    assert "export_id" in data, "Response should include export_id"
    assert "download_url" in data, "Response should include download_url"

    logger.info(f"Chart exported with URL: {data['download_url']}")

if __name__ == "__main__":
    # Allow running the test directly
    pytest.main(["-xvs", __file__])
