"""
Tests for the AI birth time rectification model.
Validates the functionality of the unified model.
"""

import os
import sys
import pytest
import logging
import asyncio
from unittest.mock import patch, AsyncMock

# Add the root directory to the path so we can import from the ai_service module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the AI rectification model
from ai_service.models.unified_model import UnifiedRectificationModel

# Set up logging
logger = logging.getLogger(__name__)

class TestAIRectificationModel:
    """Test suite for the AI rectification model."""

    @pytest.fixture
    def model(self):
        """Create a test instance of the unified model."""
        return UnifiedRectificationModel()

    @pytest.fixture
    def sample_birth_details(self):
        """Sample birth details for testing."""
        return {
            "birthDate": "1990-01-01",
            "birthTime": "12:00",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "timezone": "America/New_York"
        }

    @pytest.fixture
    def sample_questionnaire_data(self):
        """Sample questionnaire data for testing."""
        return {
            "responses": [
                {
                    "question": "What time were you born?",
                    "answer": "Around noon, but I'm not sure of the exact time."
                },
                {
                    "question": "Have you experienced any major life events?",
                    "answer": "I got married in 2015 and changed careers in 2018."
                }
            ]
        }

    @pytest.fixture
    def sample_chart_data(self):
        """Sample chart data for testing."""
        return {
            "ascendant": {"sign": "Taurus", "degree": 15.5},
            "planets": [
                {
                    "name": "Sun",
                    "sign": "Capricorn",
                    "longitude": 10.5,
                    "house": 9
                },
                {
                    "name": "Moon",
                    "sign": "Virgo",
                    "longitude": 155.3,
                    "house": 5
                }
            ]
        }

    def test_model_initialization(self, model):
        """Test that the model initializes correctly."""
        assert model is not None
        assert isinstance(model, UnifiedRectificationModel)
        assert model.is_initialized
        assert model.model_version == "1.0.0"
        assert hasattr(model, 'technique_weights')

    @pytest.mark.asyncio
    async def test_rectify_birth_time_with_simulation(self, model, sample_birth_details, sample_questionnaire_data):
        """Test birth time rectification using the simulation method."""

        # Mock the AI service to be None so it uses simulation
        with patch.object(model, 'openai_service', None):
            # Call rectify_birth_time
            result = await model.rectify_birth_time(
                birth_details=sample_birth_details,
                questionnaire_data=sample_questionnaire_data
            )

            # Check the result structure
            assert "suggested_time" in result
            assert "confidence" in result
            assert "reliability" in result
            assert "task_predictions" in result
            assert "explanation" in result
            assert "significant_events" in result
            assert "ai_used" in result
            assert not result["ai_used"]  # AI should not be used in simulation

            # Check specific fields
            assert "time_accuracy" in result["task_predictions"]
            assert "ascendant_accuracy" in result["task_predictions"]
            assert "houses_accuracy" in result["task_predictions"]
            assert result["reliability"] in ["low", "moderate", "high", "very high"]

    @pytest.mark.asyncio
    async def test_perform_ai_rectification(self, model, sample_birth_details, sample_chart_data, sample_questionnaire_data):
        """Test AI-based rectification."""

        # Create a mock response
        mock_response = {
            "content": '{"adjustment_minutes": 15, "confidence": 80, "reasoning": "test"}'
        }

        # Mock the OpenAI service
        mock_openai = AsyncMock()
        mock_openai.generate_completion.return_value = mock_response

        with patch.object(model, 'openai_service', mock_openai):
            # Call _perform_ai_rectification
            adjustment_minutes, confidence = await model._perform_ai_rectification(
                birth_details=sample_birth_details,
                chart_data=sample_chart_data,
                questionnaire_data=sample_questionnaire_data
            )

            # Check the result
            assert adjustment_minutes == 15
            assert confidence == 80

            # Verify the mock was called with the right parameters
            mock_openai.generate_completion.assert_called_once()
            args, kwargs = mock_openai.generate_completion.call_args
            assert kwargs["task_type"] == "rectification"

    def test_calculate_confidence(self, model, sample_questionnaire_data):
        """Test confidence calculation based on questionnaire responses."""
        confidence = model._calculate_confidence(sample_questionnaire_data)

        # Check the result
        assert isinstance(confidence, float)
        assert 50 <= confidence <= 95

    def test_determine_reliability(self, model, sample_questionnaire_data):
        """Test reliability level determination."""
        reliability = model._determine_reliability(75, sample_questionnaire_data)

        # Check the result
        assert reliability in ["low", "moderate", "high", "very high"]

    @pytest.mark.asyncio
    async def test_generate_explanation(self, model, sample_questionnaire_data):
        """Test explanation generation."""

        # Mock the OpenAI service
        mock_openai = AsyncMock()
        mock_openai.generate_completion.return_value = {
            "content": "This is a test explanation for birth time rectification.",
            "tokens": {"total": 12},
        }

        with patch.object(model, 'openai_service', mock_openai):
            # Generate explanation
            explanation = await model._generate_explanation(
                adjustment_minutes=15,
                reliability="high",
                questionnaire_data=sample_questionnaire_data
            )

            # Check the result
            assert isinstance(explanation, str)
            assert explanation == "This is a test explanation for birth time rectification."

            # Verify the mock was called with the right parameters
            mock_openai.generate_completion.assert_called_once()
            args, kwargs = mock_openai.generate_completion.call_args
            assert kwargs["task_type"] == "explanation"

    @pytest.mark.asyncio
    async def test_identify_significant_events_ai(self, model, sample_questionnaire_data):
        """Test identifying significant events with AI."""

        # Mock the OpenAI service
        mock_openai = AsyncMock()
        mock_openai.generate_completion.return_value = {
            "content": "Event 1 - Astrological explanation\nEvent 2 - Another explanation"
        }

        with patch.object(model, 'openai_service', mock_openai):
            # Identify significant events
            events = await model._identify_significant_events_ai(
                questionnaire_data=sample_questionnaire_data,
                adjustment_minutes=15
            )

            # Check the result
            assert isinstance(events, list)
            assert len(events) == 2
            assert events[0] == "Event 1 - Astrological explanation"
            assert events[1] == "Event 2 - Another explanation"

            # Verify the mock was called with the right parameters
            mock_openai.generate_completion.assert_called_once()
            args, kwargs = mock_openai.generate_completion.call_args
            assert kwargs["task_type"] == "auxiliary"

    def test_identify_significant_events_fallback(self, model, sample_questionnaire_data):
        """Test identifying significant events with fallback method."""
        events = model._identify_significant_events_fallback(sample_questionnaire_data)

        # Check the result
        assert isinstance(events, list)
        assert 2 <= len(events) <= 4

        # Verify the format of the events
        for event in events:
            assert isinstance(event, str)
            assert " during " in event  # Events should mention astrological conditions
