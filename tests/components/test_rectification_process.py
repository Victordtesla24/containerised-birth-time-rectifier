"""
Component test for the birth time rectification process as described in the sequence diagram.

This test verifies the complete rectification process from the "Original Sequence Diagram - Full Implementation"
section, ensuring all calculations and AI integrations work together properly.
"""

import pytest
import asyncio
import os
import uuid
import logging
from datetime import datetime
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

# Test data
TEST_BIRTH_DETAILS = {
    "birthDate": "1990-01-15",
    "birthTime": "08:30:00",
    "birthPlace": "Mumbai, India",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "timezone": "Asia/Kolkata"
}

# Sample questionnaire answers for testing
SAMPLE_ANSWERS = [
    {
        "questionId": "q_career_1",
        "answer": "Yes, I had a significant career change",
        "confidence": 90
    },
    {
        "questionId": "q_relationship_1",
        "answer": "Got married in 2015",
        "confidence": 85
    },
    {
        "questionId": "q_health_1",
        "answer": "Had a major health issue in 2010",
        "confidence": 95
    }
]

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
async def test_birth_time_rectification_process(openai_service, chart_service):
    """
    Test the complete birth time rectification process with real implementations.
    This follows the sequence diagram and uses real AI integrations.
    """
    logger.info("Starting birth time rectification process test")

    # 1. Generate initial chart
    logger.info("Step 1: Generate initial chart")
    initial_chart_result = await chart_service.generate_chart(
        birth_date=TEST_BIRTH_DETAILS["birthDate"],
        birth_time=TEST_BIRTH_DETAILS["birthTime"],
        latitude=TEST_BIRTH_DETAILS["latitude"],
        longitude=TEST_BIRTH_DETAILS["longitude"],
        timezone=TEST_BIRTH_DETAILS["timezone"],
        location=TEST_BIRTH_DETAILS["birthPlace"],
        verify_with_openai=True
    )

    # Verify chart generation result
    assert "chart_id" in initial_chart_result, "Chart generation should return a chart ID"
    initial_chart_id = initial_chart_result["chart_id"]
    logger.info(f"Initial chart generated with ID: {initial_chart_id}")

    # 2. Perform birth time rectification
    logger.info("Step 2: Perform birth time rectification with AI analysis")

    # Parse birth datetime for rectification
    birth_datetime = datetime.strptime(
        f"{TEST_BIRTH_DETAILS['birthDate']} {TEST_BIRTH_DETAILS['birthTime']}",
        "%Y-%m-%d %H:%M:%S"
    )

    # Use comprehensive rectification with real AI analysis
    rectification_result = await comprehensive_rectification(
        birth_dt=birth_datetime,
        latitude=TEST_BIRTH_DETAILS["latitude"],
        longitude=TEST_BIRTH_DETAILS["longitude"],
        timezone=TEST_BIRTH_DETAILS["timezone"],
        answers=SAMPLE_ANSWERS
    )

    # Verify rectification result
    assert "rectified_time" in rectification_result, "Rectification should return a rectified time"
    assert "confidence_score" in rectification_result, "Rectification should include a confidence score"
    assert "explanation" in rectification_result, "Rectification should include an explanation"

    rectified_time = rectification_result["rectified_time"]
    confidence_score = rectification_result["confidence_score"]
    explanation = rectification_result.get("explanation", "No explanation provided")
    rectified_chart_id = rectification_result.get("rectified_chart_id")

    logger.info(f"Original time: {TEST_BIRTH_DETAILS['birthTime']}")
    logger.info(f"Rectified time: {rectified_time}")
    logger.info(f"Confidence score: {confidence_score}")
    logger.info(f"Explanation: {explanation[:100]}...")

    # 3. Compare original and rectified charts
    logger.info("Step 3: Compare original and rectified charts")
    if rectified_chart_id:
        comparison_result = await chart_service.compare_charts(
            chart1_id=initial_chart_id,
            chart2_id=rectified_chart_id
        )

        # Verify comparison result
        assert "comparison_id" in comparison_result, "Chart comparison should return a comparison ID"
        assert "differences" in comparison_result, "Chart comparison should include differences"

        logger.info(f"Chart comparison completed with ID: {comparison_result.get('comparison_id')}")
        logger.info(f"Significant differences: {len(comparison_result.get('differences', []))}")
    else:
        # If rectification didn't provide a new chart ID, create one for testing
        rectified_chart_result = await chart_service.generate_chart(
            birth_date=TEST_BIRTH_DETAILS["birthDate"],
            birth_time=str(rectified_time),
            latitude=TEST_BIRTH_DETAILS["latitude"],
            longitude=TEST_BIRTH_DETAILS["longitude"],
            timezone=TEST_BIRTH_DETAILS["timezone"],
            location=TEST_BIRTH_DETAILS["birthPlace"]
        )

        rectified_chart_id = rectified_chart_result["chart_id"]

        # Now compare the charts
        comparison_result = await chart_service.compare_charts(
            chart1_id=initial_chart_id,
            chart2_id=rectified_chart_id
        )

        logger.info(f"Chart comparison completed with ID: {comparison_result.get('comparison_id')}")

    # 4. Export rectified chart
    logger.info("Step 4: Export rectified chart")
    export_result = await chart_service.export_chart(
        chart_id=rectified_chart_id,
        format="pdf"
    )

    # Verify export result
    assert "export_id" in export_result, "Chart export should return an export ID"
    assert "download_url" in export_result, "Chart export should include a download URL"

    logger.info(f"Chart exported with URL: {export_result.get('download_url')}")
    logger.info("Birth time rectification process test completed successfully")

if __name__ == "__main__":
    # Allow running the test directly
    asyncio.run(pytest.main(["-xvs", __file__]))
