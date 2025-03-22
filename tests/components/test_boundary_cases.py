"""
Component test for boundary cases in the birth time rectification process.

This test verifies the system behavior with edge cases such as:
1. Incomplete or ambiguous answers
2. Very early/late birth times
3. Locations with unusual timezones
4. High-confidence contradictory answers

These cases test the robustness of the "Original Sequence Diagram - Full Implementation".
"""

import pytest
import asyncio
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required components for real implementation
from ai_service.api.services.openai.service import OpenAIService
from ai_service.core.rectification.main import comprehensive_rectification
from ai_service.core.rectification.chart_calculator import EnhancedChartCalculator
from ai_service.services.chart_service import ChartService
from ai_service.database.repositories import ChartRepository

# Define a mock AstroCalculator for testing
class AstroCalculator:
    """Mock AstroCalculator for testing purposes."""

    def __init__(self):
        """Initialize mock calculator."""
        pass

    def calculate_chart(self, *args, **kwargs):
        """Mock chart calculation method."""
        return {
            "planets": {},
            "houses": {},
            "ascendant": {"sign": "Aries", "degree": 0},
            "aspects": []
        }

# Test data - boundary cases
BOUNDARY_CASES = [
    # Case 1: Very early birth time
    {
        "name": "early_birth_time",
        "birthDate": "1990-01-15",
        "birthTime": "00:01:00",
        "birthPlace": "Mumbai, India",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "timezone": "Asia/Kolkata",
        "answers": [
            {
                "questionId": "q_early_riser",
                "answer": "Yes, always been an early riser since childhood",
                "confidence": 95
            }
        ]
    },
    # Case 2: Very late birth time
    {
        "name": "late_birth_time",
        "birthDate": "1990-01-15",
        "birthTime": "23:59:00",
        "birthPlace": "Mumbai, India",
        "latitude": 19.0760,
        "longitude": 72.8777,
        "timezone": "Asia/Kolkata",
        "answers": [
            {
                "questionId": "q_night_owl",
                "answer": "Always been a night owl",
                "confidence": 95
            }
        ]
    },
    # Case 3: International Date Line location
    {
        "name": "date_line_location",
        "birthDate": "1990-01-15",
        "birthTime": "12:00:00",
        "birthPlace": "Apia, Samoa",
        "latitude": -13.8506,
        "longitude": -171.7513,
        "timezone": "Pacific/Apia",
        "answers": [
            {
                "questionId": "q_time_perception",
                "answer": "Always felt like I was born on a different day",
                "confidence": 85
            }
        ]
    },
    # Case 4: Contradictory answers
    {
        "name": "contradictory_answers",
        "birthDate": "1990-01-15",
        "birthTime": "12:00:00",
        "birthPlace": "New York, NY, USA",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timezone": "America/New_York",
        "answers": [
            {
                "questionId": "q_morning_person",
                "answer": "Definitely a morning person",
                "confidence": 90
            },
            {
                "questionId": "q_night_owl",
                "answer": "Always been a night owl",
                "confidence": 90
            }
        ]
    }
]

@pytest.fixture
async def openai_service():
    """Create a real OpenAI service instance."""
    # Ensure API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY environment variable not set")

    return OpenAIService()

@pytest.fixture
async def chart_service(openai_service):
    """Create a real chart service with the OpenAI integration."""
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

@pytest.mark.asyncio
@pytest.mark.parametrize("case", BOUNDARY_CASES, ids=[case["name"] for case in BOUNDARY_CASES])
async def test_boundary_rectification_cases(openai_service, chart_service, case):
    """
    Test boundary cases for birth time rectification.
    Each case tests a different edge condition that the system should handle gracefully.
    """
    logger.info(f"Testing boundary case: {case['name']}")

    # 1. Generate initial chart
    logger.info(f"Generating chart for {case['name']} with birth time {case['birthTime']}")
    initial_chart_result = await chart_service.generate_chart(
        birth_date=case["birthDate"],
        birth_time=case["birthTime"],
        latitude=case["latitude"],
        longitude=case["longitude"],
        timezone=case["timezone"],
        location=case["birthPlace"],
        verify_with_openai=True
    )

    # Verify chart generation result
    assert "chart_id" in initial_chart_result, "Chart generation should return a chart ID"
    initial_chart_id = initial_chart_result["chart_id"]
    logger.info(f"Initial chart generated with ID: {initial_chart_id}")

    # 2. Perform birth time rectification
    logger.info(f"Performing rectification for {case['name']}")

    # Parse birth datetime for rectification
    birth_datetime = datetime.strptime(
        f"{case['birthDate']} {case['birthTime']}",
        "%Y-%m-%d %H:%M:%S"
    )

    # Use comprehensive rectification with real AI analysis
    rectification_result = await comprehensive_rectification(
        birth_dt=birth_datetime,
        latitude=case["latitude"],
        longitude=case["longitude"],
        timezone=case["timezone"],
        answers=case["answers"]
    )

    # Verify rectification result (all cases should return valid results)
    assert "rectified_time" in rectification_result, "Rectification should return a rectified time"
    assert "confidence_score" in rectification_result, "Rectification should include a confidence score"

    rectified_time = rectification_result["rectified_time"]
    confidence_score = rectification_result["confidence_score"]

    # Log results for analysis
    logger.info(f"Case: {case['name']}")
    logger.info(f"Original time: {case['birthTime']}")
    logger.info(f"Rectified time: {rectified_time}")
    logger.info(f"Confidence score: {confidence_score}")

    # Ensure the confidence score is reasonable
    assert 0 <= confidence_score <= 100, "Confidence score should be between 0 and 100"

    # Additional validation for specific cases
    if case["name"] == "early_birth_time":
        # For early birth time, the rectified time should still be in the early morning
        rectified_dt = datetime.strptime(str(rectified_time), "%H:%M:%S")
        assert rectified_dt.hour < 6, "Rectified time for early birth should still be early morning"

    elif case["name"] == "late_birth_time":
        # For late birth time, the rectified time should still be late evening
        rectified_dt = datetime.strptime(str(rectified_time), "%H:%M:%S")
        assert rectified_dt.hour >= 18, "Rectified time for late birth should still be late evening"

    elif case["name"] == "contradictory_answers":
        # For contradictory answers, the confidence score should be lower
        assert confidence_score < 80, "Confidence score for contradictory answers should be lower"

    # 3. Generate and compare charts for original and rectified times
    rectified_chart_id = rectification_result.get("rectified_chart_id")

    # If no rectified chart ID is provided, create one for testing
    if not rectified_chart_id:
        rectified_chart_result = await chart_service.generate_chart(
            birth_date=case["birthDate"],
            birth_time=str(rectified_time),
            latitude=case["latitude"],
            longitude=case["longitude"],
            timezone=case["timezone"],
            location=case["birthPlace"]
        )
        rectified_chart_id = rectified_chart_result["chart_id"]

    # Compare charts
    comparison_result = await chart_service.compare_charts(
        chart1_id=initial_chart_id,
        chart2_id=rectified_chart_id
    )

    # Verify comparison result
    assert "comparison_id" in comparison_result, "Chart comparison should return a comparison ID"
    assert "differences" in comparison_result, "Chart comparison should include differences"

    logger.info(f"Chart comparison completed with ID: {comparison_result.get('comparison_id')}")
    logger.info(f"Significant differences: {len(comparison_result.get('differences', []))}")

    logger.info(f"Boundary case {case['name']} tested successfully")

if __name__ == "__main__":
    # Allow running the test directly
    asyncio.run(pytest.main(["-xvs", __file__]))
