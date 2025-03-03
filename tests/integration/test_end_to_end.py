"""
End-to-end tests for the Birth Time Rectifier application.
Validates the complete flow from frontend to backend.
"""

import os
import sys
import pytest
import json
import logging
from fastapi.testclient import TestClient
from datetime import datetime

# Add the root directory to the path so we can import from the ai_service module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the FastAPI app
from ai_service.main import app

# Set up logging
logger = logging.getLogger(__name__)

class TestEndToEndFlow:
    """Test suite for end-to-end application flow."""

    @pytest.fixture(scope="class")
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_chart_generation_flow(self, client):
        """Test the complete chart generation flow."""
        # Step 1: Create a new chart
        new_chart_data = {
            "birthDate": "1990-01-01",
            "birthTime": "12:00",
            "birthPlace": "New York, NY",
            "name": "Test User",
            "notes": "Test chart for end-to-end testing"
        }

        response = client.post("/api/charts", json=new_chart_data)
        assert response.status_code == 200
        result = response.json()
        assert "id" in result
        chart_id = result["id"]

        # Step 2: Get the chart details
        response = client.get(f"/api/charts/{chart_id}")
        assert response.status_code == 200
        chart_data = response.json()
        assert chart_data["id"] == chart_id
        assert "planets" in chart_data
        assert "houses" in chart_data

        # Step 3: Update the chart with additional information
        update_data = {
            "notes": "Updated test chart notes",
            "tags": ["test", "end-to-end"]
        }

        response = client.put(f"/api/charts/{chart_id}", json=update_data)
        assert response.status_code == 200
        updated_chart = response.json()
        assert updated_chart["notes"] == update_data["notes"]

        # Step 4: Delete the chart
        response = client.delete(f"/api/charts/{chart_id}")
        assert response.status_code == 200

        # Step 5: Verify deletion
        response = client.get(f"/api/charts/{chart_id}")
        assert response.status_code == 404

    def test_questionnaire_flow(self, client):
        """Test the questionnaire and birth time rectification flow."""
        # Step 1: Initialize questionnaire
        init_data = {
            "birthDate": "1990-01-01",
            "birthTime": "12:00",
            "birthPlace": "New York, NY",
            "latitude": 40.7128,
            "longitude": -74.0060
        }

        response = client.post("/api/questionnaire/initialize", json=init_data)
        assert response.status_code == 200
        init_result = response.json()
        assert "sessionId" in init_result
        assert "question" in init_result
        session_id = init_result["sessionId"]

        # Step 2: Answer first question
        answer_data = {
            "sessionId": session_id,
            "questionId": init_result["question"]["id"],
            "answer": "Yes"
        }

        response = client.post("/api/questionnaire/answer", json=answer_data)
        assert response.status_code == 200
        answer_result = response.json()
        assert "nextQuestion" in answer_result

        # Step 3: Answer second question
        answer_data = {
            "sessionId": session_id,
            "questionId": answer_result["nextQuestion"]["id"],
            "answer": "No"
        }

        response = client.post("/api/questionnaire/answer", json=answer_data)
        assert response.status_code == 200
        answer_result = response.json()

        # Step 4: Submit questionnaire for analysis
        submit_data = {
            "sessionId": session_id
        }

        response = client.post("/api/questionnaire/analyze", json=submit_data)
        assert response.status_code == 200
        analysis_result = response.json()
        assert "rectifiedTime" in analysis_result
        assert "confidence" in analysis_result
        assert "reliability" in analysis_result

    def test_geocoding_flow(self, client):
        """Test the geocoding flow."""
        # Test geocoding endpoint
        response = client.get("/api/geocoding/geocode?query=New York")
        assert response.status_code == 200
        result = response.json()
        assert "latitude" in result
        assert "longitude" in result
        assert "timezone" in result

        # Validate coordinates
        assert 40 < result["latitude"] < 41  # New York latitude
        assert -75 < result["longitude"] < -73  # New York longitude

    def test_api_documentation(self, client):
        """Test that the API documentation is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        response = client.get("/openapi.json")
        assert response.status_code == 200
        api_spec = response.json()
        assert "paths" in api_spec
        assert "/api/charts" in api_spec["paths"]
        assert "/api/questionnaire" in api_spec["paths"]
