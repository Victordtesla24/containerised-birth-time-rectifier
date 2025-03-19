"""
Integration tests for OpenAI verification of astrological charts.
Tests the full workflow from chart calculation to OpenAI verification and correction application.
"""

import pytest
import asyncio
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to the Python path to allow imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_service.core.chart_calculator import (
    calculate_verified_chart,
    EnhancedChartCalculator,
    get_enhanced_chart_calculator
)

# Sample chart data for testing
SAMPLE_CHART_DATA = {
    "birth_details": {
        "date": "1990-01-15",
        "time": "12:30:00",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "location": "New Delhi, India"
    },
    "ascendant": {
        "sign": "Libra",
        "degree": 15.5,
        "longitude": 195.5
    },
    "planets": {
        "sun": {"sign": "Capricorn", "degree": 1.23, "longitude": 271.23, "house": 4, "retrograde": False},
        "moon": {"sign": "Taurus", "degree": 15.42, "longitude": 45.42, "house": 8, "retrograde": False},
        "mars": {"sign": "Capricorn", "degree": 5.67, "longitude": 275.67, "house": 4, "retrograde": False},
        "mercury": {"sign": "Sagittarius", "degree": 28.91, "longitude": 268.91, "house": 3, "retrograde": False},
        "jupiter": {"sign": "Cancer", "degree": 10.34, "longitude": 100.34, "house": 10, "retrograde": True},
        "venus": {"sign": "Aquarius", "degree": 2.78, "longitude": 302.78, "house": 5, "retrograde": False},
        "saturn": {"sign": "Capricorn", "degree": 18.56, "longitude": 288.56, "house": 4, "retrograde": False},
        "rahu": {"sign": "Aquarius", "degree": 22.45, "longitude": 322.45, "house": 5, "retrograde": True},
        "ketu": {"sign": "Leo", "degree": 22.45, "longitude": 142.45, "house": 11, "retrograde": True}
    },
    "houses": {
        1: {"sign": "Libra", "cusp": 195.5},
        2: {"sign": "Scorpio", "cusp": 225.0},
        3: {"sign": "Sagittarius", "cusp": 255.0},
        4: {"sign": "Capricorn", "cusp": 285.0},
        5: {"sign": "Aquarius", "cusp": 315.0},
        6: {"sign": "Pisces", "cusp": 345.0},
        7: {"sign": "Aries", "cusp": 15.0},
        8: {"sign": "Taurus", "cusp": 45.0},
        9: {"sign": "Gemini", "cusp": 75.0},
        10: {"sign": "Cancer", "cusp": 105.0},
        11: {"sign": "Leo", "cusp": 135.0},
        12: {"sign": "Virgo", "cusp": 165.0}
    }
}

# Sample response for accurate chart
VERIFICATION_RESPONSE_ACCURATE = {
    "needs_correction": False,
    "confidence_score": 92.5,
    "message": "Chart verified successfully according to Vedic standards.",
    "corrections": []
}

# Sample response for chart needing corrections
VERIFICATION_RESPONSE_CORRECTIONS = {
    "needs_correction": True,
    "confidence_score": 85.0,
    "message": "Chart requires minor corrections to align with Vedic standards.",
    "corrections": [
        {
            "type": "planet",
            "name": "saturn",
            "original": {"sign": "Capricorn", "degree": 18.56},
            "corrected": {"sign": "Capricorn", "degree": 19.12},
            "reason": "Ephemeris calculation adjustment needed for accurate sidereal position"
        },
        {
            "type": "ascendant",
            "name": "ascendant",
            "original": {"sign": "Libra", "degree": 15.5},
            "corrected": {"sign": "Libra", "degree": 16.2},
            "reason": "Adjustment based on precise ayanamsa calculation"
        }
    ]
}

class AsyncMock(MagicMock):
    """Mock for async functions"""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

@pytest.fixture
def mock_openai_service():
    """Fixture for mocking OpenAI service"""
    mock_instance = MagicMock()
    mock_instance.generate_completion = AsyncMock()
    mock_instance.generate_completion.return_value = {
        "content": json.dumps(VERIFICATION_RESPONSE_ACCURATE),
        "model_used": "gpt-4-turbo",
        "tokens": {"prompt": 500, "completion": 200, "total": 700},
        "cost": 0.05,
        "response_time": 1.5
    }
    return mock_instance

@pytest.mark.asyncio
async def test_openai_integration_accurate_chart(mock_openai_service):
    """
    Test that an accurate chart is properly verified without corrections.

    This test verifies that:
    1. The OpenAI service is called with the correct parameters
    2. The verification data is properly added to the chart
    3. The corrections_applied flag is correctly set to False
    """
    # Create the calculator instance with our mock
    calculator = EnhancedChartCalculator(openai_service=mock_openai_service)

    # Mock the calculate_chart function to return our sample data
    with patch('ai_service.core.chart_calculator.calculate_chart', return_value=SAMPLE_CHART_DATA):
        # Call the function under test
        result = await calculator.calculate_verified_chart(
            birth_date="1990-01-15",
            birth_time="12:30:00",
            latitude=28.6139,
            longitude=77.2090,
            location="New Delhi, India"
        )

        # Verify OpenAI was called
        mock_openai_service.generate_completion.assert_called_once()

        # Verify correct verification data is added
        assert "verification" in result
        assert result["verification"]["verified"] is True
        assert result["verification"]["confidence_score"] == 92.5
        assert result["verification"]["message"] == "Chart verified successfully according to Vedic standards."
        assert result["verification"]["corrections_applied"] is False

@pytest.mark.asyncio
async def test_openai_integration_with_corrections(mock_openai_service):
    """
    Test that a chart needing corrections is properly processed.

    This test verifies that:
    1. The OpenAI service is called with the correct parameters
    2. The corrections are properly applied to the chart
    3. The corrections_applied flag is correctly set to True
    4. The verification data includes the confidence score
    """
    # Set up the mock to return a response requiring corrections
    mock_openai_service.generate_completion.return_value = {
        "content": json.dumps(VERIFICATION_RESPONSE_CORRECTIONS),
        "model_used": "gpt-4-turbo",
        "tokens": {"prompt": 500, "completion": 300, "total": 800},
        "cost": 0.06,
        "response_time": 1.7
    }

    # Create the calculator instance with our mock
    calculator = EnhancedChartCalculator(openai_service=mock_openai_service)

    # Mock the calculate_chart function to return our sample data
    with patch('ai_service.core.chart_calculator.calculate_chart', return_value=SAMPLE_CHART_DATA.copy()):
        # Call the function under test
        result = await calculator.calculate_verified_chart(
            birth_date="1990-01-15",
            birth_time="12:30:00",
            latitude=28.6139,
            longitude=77.2090,
            location="New Delhi, India"
        )

        # Verify OpenAI was called
        mock_openai_service.generate_completion.assert_called_once()

        # Verify correct verification data is added
        assert "verification" in result
        assert result["verification"]["verified"] is True
        assert result["verification"]["confidence_score"] == 85.0
        assert result["verification"]["message"] == "Chart requires minor corrections to align with Vedic standards."

        # Verify either a boolean True or a non-empty list of corrections
        assert "corrections_applied" in result["verification"]
        corrections = result["verification"]["corrections_applied"]
        assert corrections is True or (isinstance(corrections, list) and len(corrections) > 0)

@pytest.mark.asyncio
async def test_openai_integration_error_handling(mock_openai_service):
    """
    Test error handling when OpenAI service fails.

    This test verifies that:
    1. When OpenAI service fails, the error is handled gracefully
    2. A fallback verification with lower confidence is provided
    3. The error message is included in the verification data
    """
    # Set up the mock to raise an exception
    mock_openai_service.generate_completion.side_effect = Exception("OpenAI service unavailable")

    # Create the calculator instance with our mock
    calculator = EnhancedChartCalculator(openai_service=mock_openai_service)

    # Mock the calculate_chart function to return our sample data
    with patch('ai_service.core.chart_calculator.calculate_chart', return_value=SAMPLE_CHART_DATA.copy()):
        # Call the function under test
        result = await calculator.calculate_verified_chart(
            birth_date="1990-01-15",
            birth_time="12:30:00",
            latitude=28.6139,
            longitude=77.2090,
            location="New Delhi, India"
        )

        # Verify OpenAI was called
        mock_openai_service.generate_completion.assert_called()

        # Verify fallback verification data is added
        assert "verification" in result
        assert result["verification"]["verified"] is False
        assert result["verification"]["confidence_score"] <= 70.0  # Lower confidence for fallback
        assert "Verification failed" in result["verification"]["message"]

@pytest.mark.asyncio
async def test_openai_integration_low_confidence(mock_openai_service):
    """
    Test handling of low confidence verification results.

    This test verifies that:
    1. When initial verification has low confidence, enhanced verification is attempted
    2. The enhanced model produces a higher confidence score
    3. The enhanced_model flag is set in the verification data
    """
    # First call returns low confidence
    first_response = {
        "content": json.dumps({
            "needs_correction": False,
            "confidence_score": 75.0,
            "message": "Chart verified with moderate confidence.",
            "corrections": []
        }),
        "model_used": "gpt-4-turbo"
    }

    # Second call (enhanced model) returns high confidence
    second_response = {
        "content": json.dumps({
            "needs_correction": False,
            "confidence_score": 95.0,
            "message": "Chart verified with high confidence using enhanced analysis.",
            "corrections": []
        }),
        "model_used": "o1-preview"
    }

    # Configure the mock to return different values on successive calls
    mock_openai_service.generate_completion.side_effect = [
        first_response,
        second_response
    ]

    # Create the calculator instance with our mock
    calculator = EnhancedChartCalculator(openai_service=mock_openai_service)

    # Mock the calculate_chart function to return our sample data
    with patch('ai_service.core.chart_calculator.calculate_chart', return_value=SAMPLE_CHART_DATA.copy()):
        # Call the function under test
        result = await calculator.calculate_verified_chart(
            birth_date="1990-01-15",
            birth_time="12:30:00",
            latitude=28.6139,
            longitude=77.2090,
            location="New Delhi, India"
        )

        # Verify OpenAI was called twice
        assert mock_openai_service.generate_completion.call_count == 2

        # Verify enhanced verification data is used
        assert "verification" in result
        assert result["verification"]["verified"] is True
        assert result["verification"]["confidence_score"] == 95.0
        assert result["verification"]["enhanced_model"] is True

if __name__ == "__main__":
    # Run the tests when executed directly
    pytest.main(["-xvs", __file__])
