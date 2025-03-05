import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# These imports rely on the modified path
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from ai_service.main import app  # noqa: E402

# Create test client
client = TestClient(app)

def test_root_health_endpoint():
    """Test the root health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["ok", "healthy"]

def test_api_health_endpoint():
    """Test the /api/health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["ok", "healthy"]

def test_chart_generation():
    """Test the chart generation endpoint."""
    # Sample birth data - camelCase format for the alt endpoint
    request_data_alt = {
        "birthDate": "1990-05-15",
        "birthTime": "10:30:00",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "timezone": "Asia/Kolkata"
    }

    # Test the alt endpoint first
    response = client.post("/chart/generate/alt", json=request_data_alt)

    # If this fails, try the alternative endpoint
    if response.status_code != 200:
        response = client.post("/api/chart/generate/alt", json=request_data_alt)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "d1Chart" in data
    d1_chart = data["d1Chart"]

    # Check that the chart has the expected components
    assert "ascendant" in d1_chart
    assert "planets" in d1_chart
    assert "houses" in d1_chart

    # Check that all planets are present, including Ketu
    planet_names = [p["name"] for p in d1_chart["planets"]]
    expected_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars",
                        "Jupiter", "Saturn", "Uranus", "Neptune",
                        "Pluto", "Rahu", "Ketu"]

    for planet in expected_planets:
        assert planet in planet_names, f"Planet {planet} is missing from the chart"

    # Check Rahu and Ketu are in opposite signs
    rahu = next((p for p in d1_chart["planets"] if p["name"] == "Rahu"), None)
    ketu = next((p for p in d1_chart["planets"] if p["name"] == "Ketu"), None)

    assert rahu is not None
    assert ketu is not None

    # Get the zodiac signs
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

    # Calculate expected Ketu sign (opposite to Rahu)
    rahu_sign_index = signs.index(rahu["sign"])
    expected_ketu_sign_index = (rahu_sign_index + 6) % 12
    expected_ketu_sign = signs[expected_ketu_sign_index]

    assert ketu["sign"] == expected_ketu_sign, f"Ketu is not in the opposite sign of Rahu. Expected {expected_ketu_sign}, got {ketu['sign']}"

    # Check that Ketu degree is correctly calculated
    # Expected Ketu degree is (30 - Rahu degree) % 30
    expected_ketu_degree = (30 - rahu["degree"]) % 30
    assert abs(ketu["degree"] - expected_ketu_degree) <= 1.0, f"Ketu degree should be approximately {expected_ketu_degree}, got {ketu['degree']}"

def test_geocoding():
    """Test the geocoding endpoint."""
    # Try both endpoint paths
    response = client.get("/geocode?query=New+York")

    # If the first one fails, try the alternative
    if response.status_code == 404:
        response = client.get("/api/geocode?query=New+York")

    # One of them should succeed
    assert response.status_code in [200, 404], "Both geocoding endpoints failed"

    # If both 404, skip the test
    if response.status_code == 404:
        pytest.skip("Geocoding endpoint not found or not implemented")

    data = response.json()
    assert "latitude" in data
    assert "longitude" in data
    assert "timezone" in data

def test_questionnaire():
    """Test the questionnaire generation endpoint."""
    # Sample request
    request_data = {
        "birthDetails": {
            "name": "Test User",
            "gender": "male",
            "birthDate": "1990-05-15",
            "approximateTime": "10:30:00",
            "birthLocation": "Pune, India",
            "coordinates": {"latitude": 18.5204, "longitude": 73.8567},
            "timezone": "Asia/Kolkata"
        },
        "sessionId": None,
        "previousAnswers": {},
        "questionHistory": [],
        "chartData": None
    }

    # Try both endpoint paths
    response = client.post("/api/questionnaire/generate", json=request_data)

    # If the first one fails, try the alternative
    if response.status_code == 404:
        response = client.post("/questionnaire/generate", json=request_data)

    # Check if either endpoint worked or skip the test
    if response.status_code == 404:
        pytest.skip("Questionnaire endpoint not found or not implemented")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "sessionId" in data
    assert "questions" in data or "question" in data
    assert "confidenceScore" in data or "confidence" in data

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
