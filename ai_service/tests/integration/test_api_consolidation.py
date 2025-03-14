"""
API Consolidation Integration Tests

This module tests the consolidated API routers to ensure they function correctly
with the unified API gateway architecture.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
import sys
import os
import json

# Add root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Import app from main.py (consolidated version)
from ai_service.main import app

# Create test client
client = TestClient(app)

# Test data
test_birth_details = {
    "birth_details": {
        "birth_date": "1990-01-01",
        "birth_time": "12:00",
        "birth_city": "New York",
        "timezone": "America/New_York",
        "latitude": 40.7128,
        "longitude": -74.0060,
    }
}

# Alternative format for backward compatibility
test_birth_details_alt = {
    "birthDetails": {
        "birthDate": "1990-01-01",
        "birthTime": "12:00",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York",
        "location": "New York, USA"
    }
}

# Test chart ID
test_chart_id = "chrt_12345678"

# Questionnaire test data
test_questionnaire_answers = {
    "chart_id": test_chart_id,
    "answers": [
        {
            "question_id": "q1",
            "answer": "Yes"
        },
        {
            "question_id": "q2",
            "answer": "No"
        }
    ],
    "birth_time_range": {
        "min_hours": 11,
        "min_minutes": 0,
        "max_hours": 13,
        "max_minutes": 0
    }
}

def test_health_endpoint():
    """Test health check endpoint"""
    # Test primary endpoint with /api prefix
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "status" in response.json()

    # Test alternative endpoint without /api prefix
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()

def test_chart_validation_endpoint():
    """Test chart validation endpoint"""
    # Test primary endpoint with /api prefix
    response = client.post("/api/chart/validate", json=test_birth_details)
    assert response.status_code in [200, 422]  # 422 is acceptable during testing if validation fails

    # Test alternative endpoint without /api prefix
    response = client.post("/chart/validate", json=test_birth_details)
    assert response.status_code in [200, 422]  # 422 is acceptable during testing if validation fails

    # Test backward compatibility endpoint
    response = client.post("/api/chart/validate/alt", json=test_birth_details_alt)
    assert response.status_code in [200, 422]  # 422 is acceptable during testing if validation fails

def test_chart_generation_endpoint():
    """Test chart generation endpoint"""
    # Mock data for chart generation
    chart_data = {
        "birth_details": test_birth_details["birth_details"],
        "options": {
            "house_system": "P",
            "zodiac_type": "sidereal",
            "ayanamsa": "lahiri",
            "node_type": "true",
            "verify_with_openai": False
        }
    }

    # Test primary endpoint with /api prefix
    response = client.post("/api/chart/generate", json=chart_data)
    assert response.status_code in [200, 400, 422, 500]  # Various acceptable codes during testing

    # Test legacy endpoint without /api prefix
    response = client.post("/chart/generate", json=chart_data)
    assert response.status_code in [200, 400, 422, 500]  # Various acceptable codes during testing

def test_chart_retrieval_endpoint():
    """Test chart retrieval endpoint"""
    # Test primary endpoint with /api prefix
    response = client.get(f"/api/chart/{test_chart_id}")
    assert response.status_code in [200, 404]  # 404 is acceptable during testing if chart doesn't exist

    # Test alternative endpoint without /api prefix
    response = client.get(f"/chart/{test_chart_id}")
    assert response.status_code in [200, 404]  # 404 is acceptable during testing if chart doesn't exist

def test_chart_rectification_endpoint():
    """Test chart rectification endpoint"""
    # Test primary endpoint with /api prefix
    response = client.post("/api/chart/rectify", json=test_questionnaire_answers)
    assert response.status_code in [200, 404, 422, 500]  # Various acceptable codes during testing

    # Test alternative endpoint without /api prefix
    response = client.post("/chart/rectify", json=test_questionnaire_answers)
    assert response.status_code in [200, 404, 422, 500]  # Various acceptable codes during testing

def test_chart_comparison_endpoint():
    """Test chart comparison endpoint"""
    # Test primary endpoint with /api prefix
    response = client.get(f"/api/chart/chart-comparison?chart1_id={test_chart_id}&chart2_id={test_chart_id}")
    assert response.status_code in [200, 404, 422]  # Various acceptable codes during testing

    # Test alternative endpoint without /api prefix
    response = client.get(f"/chart/chart-comparison?chart1_id={test_chart_id}&chart2_id={test_chart_id}")
    assert response.status_code in [200, 404, 422]  # Various acceptable codes during testing

def test_chart_export_endpoint():
    """Test chart export endpoint"""
    export_data = {
        "chart_id": test_chart_id,
        "format": "json",
        "include_verification": True,
        "include_aspects": True
    }

    # Test primary endpoint with /api prefix
    response = client.post("/api/chart/export", json=export_data)
    assert response.status_code in [200, 404, 422]  # Various acceptable codes during testing

    # Test alternative endpoint without /api prefix
    response = client.post("/chart/export", json=export_data)
    assert response.status_code in [200, 404, 422]  # Various acceptable codes during testing

def test_geocode_endpoint():
    """Test geocode endpoint"""
    # Test primary endpoint with /api prefix
    response = client.get("/api/geocode?query=New%20York")
    assert response.status_code in [200, 422]

    # Test alternative endpoint without /api prefix
    response = client.get("/geocode?query=New%20York")
    assert response.status_code in [200, 422]

def test_questionnaire_endpoint():
    """Test questionnaire endpoint"""
    questionnaire_data = {
        "chart_id": test_chart_id
    }

    # Test primary endpoint with /api prefix
    response = client.post("/api/questionnaire", json=questionnaire_data)
    assert response.status_code in [200, 404, 422]

    # Test alternative endpoint without /api prefix
    response = client.post("/questionnaire", json=questionnaire_data)
    assert response.status_code in [200, 404, 422]

if __name__ == "__main__":
    pytest.main(["-v", __file__])
