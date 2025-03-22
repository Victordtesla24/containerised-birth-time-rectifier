"""
Integration test to ensure that all astrological calculations use real methods (no fallbacks).

This test ensures that the rectification process uses actual astrological calculations
rather than relying on fallback mechanisms or mock data.
"""

import pytest
import json
import asyncio
import uuid
import logging
from typing import Dict, Any
from datetime import datetime
import warnings
from unittest.mock import MagicMock, AsyncMock, patch
import importlib
import os
import sys

# Configure logging
logger = logging.getLogger(__name__)

# Ignore deprecation warnings about astro_calculator
warnings.filterwarnings("ignore", message=".*astro_calculator is deprecated.*", category=DeprecationWarning)

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the database repositories
from ai_service.database.repositories import ChartRepository

# Create a temporary database connection for testing
from ai_service.database.connection import create_db_pool

# Import the actual rectification components
# Update imports to use modularized paths
from ai_service.core.rectification.main import comprehensive_rectification
from ai_service.core.rectification.methods.ai_rectification import ai_assisted_rectification
from ai_service.core.rectification.chart_calculator import calculate_chart

# Import services to test
from ai_service.api.services.questionnaire_service import QuestionnaireService
from ai_service.utils.dependency_container import DependencyContainer

@pytest.mark.asyncio
async def test_questionnaire_service_no_fallbacks():
    """Test that QuestionnaireService raises errors instead of using fallbacks."""
    # Create a QuestionnaireService without OpenAI service
    questionnaire_service = QuestionnaireService(openai_service=None)

    # Prepare test data
    birth_details = {
        'birthDate': '1990-01-01',
        'birthTime': '12:00',
        'birthPlace': 'New York, NY',
        'latitude': 40.7128,
        'longitude': -74.0060
    }

    previous_answers = [
        {
            "question": "Did you experience any significant life events around age 25?",
            "answer": "Yes, I got married and changed careers.",
            "category": "life_events"
        }
    ]

    # The service should raise an error instead of using fallbacks
    with pytest.raises(ValueError) as exc_info:
        await questionnaire_service.generate_next_question(birth_details, previous_answers)

    # Check that the error message mentions OpenAI is required
    assert "OpenAI service is required" in str(exc_info.value)

@pytest.mark.asyncio
async def test_astrological_analysis_no_fallbacks():
    """Test that astrological analysis raises errors instead of using fallbacks."""
    # Create a QuestionnaireService without OpenAI service
    questionnaire_service = QuestionnaireService(openai_service=None)

    # The service should raise an error instead of using fallbacks
    with pytest.raises(ValueError) as exc_info:
        await questionnaire_service._perform_astrological_analysis(
            "Did you experience any significant life events around age 25?",
            "Yes, I got married and changed careers.",
            "1990-01-01",
            "12:00",
            40.7128,
            -74.0060
        )

    # Check that the error message mentions OpenAI is required
    assert "OpenAI service is required" in str(exc_info.value)

@pytest.mark.asyncio
async def test_comprehensive_rectification_no_fallbacks():
    """Test that comprehensive_rectification requires OpenAI and doesn't use fallbacks."""
    from datetime import datetime
    import pytz
    from unittest.mock import patch
    from ai_service.utils.dependency_container import DependencyContainer

    # Create a mock container that returns None for openai_service
    mock_container = DependencyContainer()

    # Create test data
    birth_dt = datetime(1990, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
    latitude = 40.7128
    longitude = -74.0060
    timezone = "UTC"
    answers = [
        {
            "question": "Did you experience any significant life events around age 25?",
            "answer": "Yes, I got married and changed careers.",
            "category": "life_events"
        }
    ]

    # Mock the get_container function to return our mock container
    with patch('ai_service.utils.dependency_container.get_container', return_value=mock_container):
        # The function should raise an error instead of using fallbacks
        with pytest.raises(ValueError) as exc_info:
            await comprehensive_rectification(birth_dt, latitude, longitude, timezone, answers)

        # Check that the error message mentions OpenAI is required
        assert "OpenAI service is required" in str(exc_info.value) or "service is not available" in str(exc_info.value)

@pytest.mark.asyncio
async def test_ai_assisted_rectification_no_fallbacks():
    """Test that ai_assisted_rectification requires OpenAI and doesn't use fallbacks."""
    from datetime import datetime
    import pytz
    from ai_service.core.rectification.methods.ai_rectification import ai_assisted_rectification

    # Create test data
    birth_dt = datetime(1990, 1, 1, 12, 0, 0, tzinfo=pytz.UTC)
    latitude = 40.7128
    longitude = -74.0060
    timezone = "UTC"

    # The function should raise an error instead of using fallbacks
    with pytest.raises(ValueError) as exc_info:
        await ai_assisted_rectification(birth_dt, latitude, longitude, timezone, None)

    # Check that the error message mentions OpenAI service is required
    assert "OpenAI service is required" in str(exc_info.value)
