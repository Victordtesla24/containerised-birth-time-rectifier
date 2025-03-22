"""
Unit tests for chart verification with OpenAI integration.

These tests verify the implementation of the "Vedic Chart Verification Flow - OpenAI Integration"
section in the sequence diagram, where OpenAI is used to verify and potentially correct astrological charts.
"""

import pytest
import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import OpenAI service for real API calls
from ai_service.api.services.openai.service import OpenAIService
from ai_service.services.chart_service import ChartService
from ai_service.core.astro_calculator import AstroCalculator

# Test birth details for chart generation
TEST_BIRTH_DETAILS = {
    "birthDate": "1990-01-15",
    "birthTime": "08:30:00",
    "birthPlace": "Mumbai, India",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "timezone": "Asia/Kolkata"
}

@pytest.fixture
async def openai_service():
    """Create a real OpenAI service instance."""
    # Ensure API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY environment variable not set")

    return OpenAIService()

@pytest.fixture
async def chart_data():
    """Generate real chart data for verification tests."""
    calculator = AstroCalculator()

    # Parse birth date and time
    birth_datetime = datetime.strptime(
        f"{TEST_BIRTH_DETAILS['birthDate']} {TEST_BIRTH_DETAILS['birthTime']}",
        "%Y-%m-%d %H:%M:%S"
    )

    # Calculate chart - fix parameters to match method signature
    chart = await calculator.calculate_chart(
        birth_date=TEST_BIRTH_DETAILS["birthDate"],
        birth_time=TEST_BIRTH_DETAILS["birthTime"],
        latitude=TEST_BIRTH_DETAILS["latitude"],
        longitude=TEST_BIRTH_DETAILS["longitude"],
        timezone=TEST_BIRTH_DETAILS["timezone"],
        house_system="W"  # Whole sign houses
    )

    return chart

@pytest.mark.asyncio
async def test_verify_chart_with_openai(openai_service, chart_data):
    """
    Test the verification of chart data with OpenAI according to Vedic standards.
    This follows the "Vedic Chart Verification Flow" in the sequence diagram.
    """
    logger.info("Testing chart verification with OpenAI")

    # Ensure we have valid chart data
    assert chart_data is not None, "Chart calculation failed"
    assert "planets" in chart_data, "Chart data should include planets"
    assert "houses" in chart_data, "Chart data should include houses"

    # Verify chart with OpenAI integration
    verification_result = await openai_service.verify_chart(chart_data)

    # Verify the result structure
    assert "verified" in verification_result, "Verification result should include 'verified' status"
    assert "confidence_score" in verification_result, "Verification result should include confidence score"
    assert "message" in verification_result, "Verification result should include explanatory message"

    # Verification should be successful
    assert verification_result["verified"] is True, "Chart verification should be successful"

    # Confidence score should be reasonable
    assert 0 <= verification_result["confidence_score"] <= 100, "Confidence score should be between 0 and 100"

    logger.info(f"Chart verification result: {verification_result}")
    logger.info(f"Confidence score: {verification_result['confidence_score']}")
    logger.info(f"Verification message: {verification_result['message']}")

@pytest.mark.asyncio
async def test_chart_service_with_verification(openai_service):
    """
    Test the complete chart generation and verification flow through the ChartService.
    This follows the "Vedic Chart Verification Flow" in the sequence diagram.
    """
    logger.info("Testing complete chart generation and verification flow")

    # Create a chart service with database connection
    try:
        import asyncpg
        from ai_service.core.config import settings
        from ai_service.database.repositories import ChartRepository

        # Create a real connection to the database
        db_pool = await asyncpg.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )

        chart_repository = ChartRepository(db_pool=db_pool)
        chart_service = ChartService(
            openai_service=openai_service,
            chart_repository=chart_repository
        )
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}. Ensure the database is running.")

    # Generate chart with OpenAI verification
    chart_result = await chart_service.generate_chart(
        birth_date=TEST_BIRTH_DETAILS["birthDate"],
        birth_time=TEST_BIRTH_DETAILS["birthTime"],
        latitude=TEST_BIRTH_DETAILS["latitude"],
        longitude=TEST_BIRTH_DETAILS["longitude"],
        timezone=TEST_BIRTH_DETAILS["timezone"],
        location=TEST_BIRTH_DETAILS["birthPlace"],
        verify_with_openai=True  # Enable OpenAI verification
    )

    # Verify chart generation result
    assert "chart_id" in chart_result, "Chart generation should return a chart ID"
    assert "verification" in chart_result, "Chart result should include verification data"

    # Verify the verification data
    verification = chart_result["verification"]
    assert "verified" in verification, "Verification data should include 'verified' status"
    assert "confidence_score" in verification, "Verification data should include confidence score"
    assert "message" in verification, "Verification data should include explanatory message"

    logger.info(f"Chart generated with ID: {chart_result['chart_id']}")
    logger.info(f"Verification data: {verification}")

    # Test retrieving the stored chart
    chart_id = chart_result["chart_id"]
    retrieved_chart = await chart_service.get_chart(chart_id)

    # Verify retrieved chart has verification data
    assert retrieved_chart is not None, f"Failed to retrieve chart with ID: {chart_id}"
    assert "verification" in retrieved_chart, "Retrieved chart should include verification data"

    # Verification data should match
    assert retrieved_chart["verification"]["verified"] == verification["verified"]
    assert retrieved_chart["verification"]["confidence_score"] == verification["confidence_score"]

if __name__ == "__main__":
    # Allow running the test directly
    asyncio.run(pytest.main(["-xvs", __file__]))
