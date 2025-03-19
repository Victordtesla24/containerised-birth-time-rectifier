"""
Integration test using real OpenAI API calls.

This test uses the actual OpenAI API (not mockups) and demonstrates
how to test with real API calls and proper dependency injection.
"""

import pytest
import logging
import os
from unittest.mock import MagicMock
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required modules
from ai_service.utils.env_loader import load_env_file, get_openai_api_key
from ai_service.api.services.openai.service import OpenAIService
from ai_service.services.chart_service import ChartService, ChartVerifier

# Load environment variables
load_env_file()

# Skip tests if API key is not available
api_key_available = os.environ.get("OPENAI_API_KEY") is not None
if not api_key_available:
    pytest.skip(
        "Skipping real API tests: OPENAI_API_KEY not found in environment",
        allow_module_level=True
    )

@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_openai_completion():
    """Test generating completion with the real OpenAI API."""
    try:
        # Create a real OpenAI service (no mocks)
        service = OpenAIService()

        # Use a simple prompt for testing
        prompt = "What are the key characteristics of Vedic astrology?"

        # Make a real API call
        result = await service.generate_completion(
            prompt=prompt,
            task_type="test",
            max_tokens=100,
            temperature=0.7
        )

        # Validate the response structure
        assert "content" in result
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0

        # Validate token counts
        assert "tokens" in result
        assert result["tokens"]["prompt"] > 0
        assert result["tokens"]["completion"] > 0
        assert result["tokens"]["total"] > 0

        logger.info(f"Successfully tested real OpenAI API call")

    except Exception as e:
        logger.error(f"Error testing real OpenAI API: {e}")
        raise

@pytest.mark.integration
@pytest.mark.asyncio
async def test_chart_verification_with_real_api():
    """Test chart verification with the real OpenAI API."""
    try:
        # Create real service instances (no mocks)
        openai_service = OpenAIService()
        verifier = ChartVerifier(openai_service=openai_service)

        # Create a simple chart for testing
        chart_data = {
            "ascendant": {"sign": "Aries", "degree": 15.5},
            "planets": [
                {"name": "Sun", "sign": "Capricorn", "degree": 10.5, "house": 10},
                {"name": "Moon", "sign": "Taurus", "degree": 22.3, "house": 2}
            ],
            "houses": [
                {"number": 1, "sign": "Aries", "degree": 15.5},
                {"number": 2, "sign": "Taurus", "degree": 20.1}
            ]
        }

        # Prepare verification data
        verification_data = {
            "chart_data": chart_data,
            "birth_details": {
                "birth_date": "1990-01-01",
                "birth_time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        }

        # Make a real API call for verification
        result = await verifier.verify_chart(
            verification_data=verification_data,
            openai_service=openai_service
        )

        # Validate the response structure
        assert "verified" in result
        assert "confidence_score" in result
        assert "message" in result

        logger.info(f"Successfully tested real chart verification with OpenAI API")

    except Exception as e:
        logger.error(f"Error testing chart verification with real API: {e}")
        raise
