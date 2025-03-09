"""
Test suite for AI model integration in the Birth Time Rectifier API.
"""

import pytest
import asyncio
import json
import os
import random
from unittest.mock import AsyncMock, patch, MagicMock

# Import the modules we want to test
from ai_service.api.services.openai_service import OpenAIService
from ai_service.models.unified_model import UnifiedRectificationModel

# Test data
TEST_BIRTH_DETAILS = {
    "birthDate": "1990-01-01",
    "birthTime": "12:00",
    "birthPlace": "New York, NY",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timezone": "America/New_York"
}

TEST_CHART_DATA = {
    "ascendant": {"sign": "Gemini", "degree": 15.5},
    "midheaven": {"sign": "Aquarius", "degree": 10.2},
    "planets": [
        {"name": "Sun", "sign": "Capricorn", "degree": 10.5, "house": 8, "longitude": 280.5, "isRetrograde": False},
        {"name": "Moon", "sign": "Leo", "degree": 5.2, "house": 3, "longitude": 125.2, "isRetrograde": False},
        {"name": "Mercury", "sign": "Sagittarius", "degree": 28.1, "house": 7, "longitude": 268.1, "isRetrograde": True}
    ],
    "houses": [
        {"number": 1, "sign": "Gemini", "startDegree": 15.5, "endDegree": 45.5},
        {"number": 10, "sign": "Aquarius", "startDegree": 280.2, "endDegree": 310.2}
    ],
    "aspects": [
        {"planet1": "Sun", "planet2": "Moon", "aspectType": "trine", "orb": 2.3, "influence": "harmonious"},
        {"planet1": "Mercury", "planet2": "Venus", "aspectType": "square", "orb": 1.5, "influence": "challenging"}
    ]
}

TEST_QUESTIONNAIRE_DATA = {
    "responses": [
        {
            "question": "Have you experienced significant career changes around age 29-30?",
            "answer": "Yes, I switched careers completely at age 29."
        },
        {
            "question": "Do you consider yourself more introverted or extroverted?",
            "answer": "Definitely introverted, I need time alone to recharge."
        }
    ]
}

# Mock OpenAI responses
MOCK_RECTIFICATION_RESPONSE = {
    "content": json.dumps({
        "adjustment_minutes": 15,
        "confidence": 85.5,
        "reasoning": "Based on analysis of Saturn transits and reported life events",
        "technique_details": {
            "tattva": "Ascendant degree correction needed",
            "nadi": "Dasha transitions align with rectified time",
            "kp": "Sub-lord positions support the adjustment"
        }
    }),
    "model_used": "o1-preview",
    "tokens": {"prompt": 500, "completion": 200, "total": 700},
    "cost": 0.035,
    "response_time": 1.5
}

MOCK_EXPLANATION_RESPONSE = {
    "content": "The birth time adjustment of 15 minutes later significantly refines your chart's accuracy. With this correction, your Ascendant degree is more precisely aligned with your reported personality traits and physical characteristics.",
    "model_used": "gpt-4-turbo",
    "tokens": {"prompt": 300, "completion": 150, "total": 450},
    "cost": 0.015,
    "response_time": 0.8
}

class TestOpenAIService:
    """Tests for the OpenAIService class"""

    @pytest.mark.asyncio
    async def test_model_selection(self):
        """Test that the correct model is selected for each task type"""
        service = OpenAIService()

        # Test with default environment values
        assert service._select_model("rectification") == "o1-preview"
        assert service._select_model("explanation") == "gpt-4-turbo"
        assert service._select_model("auxiliary") == "gpt-4o-mini"

        # Test with custom environment values
        with patch.dict(os.environ, {
            "OPENAI_MODEL_RECTIFICATION": "custom-rectification",
            "OPENAI_MODEL_EXPLANATION": "custom-explanation",
            "OPENAI_MODEL_AUXILIARY": "custom-auxiliary"
        }):
            service = OpenAIService()
            assert service._select_model("rectification") == "custom-rectification"
            assert service._select_model("explanation") == "custom-explanation"
            assert service._select_model("auxiliary") == "custom-auxiliary"

    @pytest.mark.asyncio
    async def test_cost_calculation(self):
        """Test that costs are calculated correctly"""
        service = OpenAIService()

        # Test costs for different models
        o1_cost = service._calculate_cost("o1-preview", 1000, 500)
        gpt4_cost = service._calculate_cost("gpt-4-turbo", 1000, 500)
        mini_cost = service._calculate_cost("gpt-4o-mini", 1000, 500)

        # Verify costs are in expected order
        assert o1_cost > gpt4_cost > mini_cost

        # Verify specific cost calculation
        # o1-preview: 1000 * $15/1M (input) + 500 * $75/1M (output)
        expected_o1_cost = (1000 / 1_000_000 * 15.0) + (500 / 1_000_000 * 75.0)
        assert o1_cost == pytest.approx(expected_o1_cost, abs=1e-6)

    @pytest.mark.asyncio
    async def test_mock_completion(self):
        """Test that mock completions are generated correctly when no API key is provided"""
        # Force mock mode
        service = OpenAIService()
        service.api_key = "sk-mock-key-for-testing"

        # Test rectification task
        rectification_response = await service.generate_completion(
            prompt="Test prompt",
            task_type="rectification",
            max_tokens=100
        )

        assert "adjustment_minutes" in rectification_response["content"]
        assert "confidence" in rectification_response["content"]
        assert rectification_response["model_used"] == "o1-preview"

        # Test explanation task
        explanation_response = await service.generate_completion(
            prompt="Test prompt",
            task_type="explanation",
            max_tokens=100
        )

        assert len(explanation_response["content"]) > 100
        assert explanation_response["model_used"] == "gpt-4-turbo"

        # Verify usage statistics are updated
        stats = service.get_usage_statistics()
        assert stats["calls_made"] == 2
        assert stats["total_tokens"] > 0
        assert stats["estimated_cost"] > 0


@pytest.mark.asyncio
class TestUnifiedRectificationModel:
    """Tests for the UnifiedRectificationModel class with AI integration"""

    async def test_perform_ai_rectification(self):
        """Test that AI rectification works correctly"""
        # Create a mock OpenAI service
        mock_openai_service = AsyncMock()
        mock_openai_service.generate_completion.return_value = MOCK_RECTIFICATION_RESPONSE

        # Create model with mock service
        model = UnifiedRectificationModel()
        model.openai_service = mock_openai_service

        # Perform AI rectification
        adjustment_minutes, confidence = await model._perform_ai_rectification(
            TEST_BIRTH_DETAILS,
            TEST_CHART_DATA,
            TEST_QUESTIONNAIRE_DATA
        )

        # Verify results
        assert adjustment_minutes == 15
        assert confidence == 85.5

        # Verify openai_service was called correctly
        mock_openai_service.generate_completion.assert_called_once()
        args, kwargs = mock_openai_service.generate_completion.call_args
        assert kwargs["task_type"] == "rectification"
        assert "birth time rectification" in kwargs["prompt"].lower()

    async def test_generate_explanation(self):
        """Test that explanations are generated correctly"""
        # Create a mock OpenAI service
        mock_openai_service = AsyncMock()
        mock_openai_service.generate_completion.return_value = MOCK_EXPLANATION_RESPONSE

        # Create model with mock service
        model = UnifiedRectificationModel()
        model.openai_service = mock_openai_service

        # Generate explanation
        explanation = await model._generate_explanation(
            adjustment_minutes=15,
            reliability="high",
            questionnaire_data=TEST_QUESTIONNAIRE_DATA
        )

        # Verify explanation
        assert len(explanation) > 50
        assert "birth time adjustment" in explanation.lower()

        # Verify openai_service was called correctly
        mock_openai_service.generate_completion.assert_called_once()
        args, kwargs = mock_openai_service.generate_completion.call_args
        assert kwargs["task_type"] == "explanation"

    async def test_rectify_birth_time_ai(self):
        """Test complete birth time rectification with AI"""
        # Create a model with mocked AI service
        model = UnifiedRectificationModel()

        # Mock all the relevant methods
        model._perform_ai_rectification = AsyncMock(return_value=(15, 85.5))
        model._identify_significant_events_ai = AsyncMock(return_value=[
            "Career change at age 29 - Saturn transit to 10th house"
        ])
        model._generate_explanation = AsyncMock(return_value="AI-generated explanation here")

        # Perform rectification
        result = await model.rectify_birth_time(
            birth_details=TEST_BIRTH_DETAILS,
            questionnaire_data=TEST_QUESTIONNAIRE_DATA,
            original_chart=TEST_CHART_DATA
        )

        # Verify results
        assert result["suggested_time"] != TEST_BIRTH_DETAILS["birthTime"]
        assert result["confidence"] > 80
        assert result["ai_used"] is True
        assert "explanation" in result
        assert len(result["significant_events"]) > 0
        assert "tattva" in result["techniques_used"]
        assert "nadi" in result["techniques_used"]
        assert "kp" in result["techniques_used"]

    async def test_rectify_birth_time_fallback(self):
        """Test birth time rectification fallback when AI is unavailable"""
        # Create a model without AI service
        model = UnifiedRectificationModel()
        model.openai_service = None

        # Perform rectification
        result = await model.rectify_birth_time(
            birth_details=TEST_BIRTH_DETAILS,
            questionnaire_data=TEST_QUESTIONNAIRE_DATA,
            original_chart=None
        )

        # Verify fallback results
        assert result["suggested_time"] != TEST_BIRTH_DETAILS["birthTime"]
        assert result["ai_used"] is False
        assert len(result["significant_events"]) > 0
        assert "simulation" in result["techniques_used"]
        assert "tattva" not in result["techniques_used"]


@pytest.mark.asyncio
class TestQuestionnaireEngine:
    """Tests for the AI-driven questionnaire engine"""

    async def test_generate_dynamic_question(self):
        """Test AI-driven question generation"""
        # Import questionnaire engine
        from ai_service.utils.questionnaire_engine import QuestionnaireEngine

        # Mock OpenAI service for questionnaire
        mock_openai_service = AsyncMock()
        mock_openai_service.generate_completion.return_value = {
            "content": json.dumps({
                "text": "Did you experience any significant changes in your health around age 35?",
                "type": "yes_no",
                "relevance": "high",
                "rationale": "Health changes at this age could indicate Saturn transit"
            }),
            "model_used": "gpt-4o-mini",
            "tokens": {"prompt": 300, "completion": 100, "total": 400},
            "cost": 0.01,
            "response_time": 0.5
        }

        # Create engine with mock service
        engine = QuestionnaireEngine()
        engine.openai_service = mock_openai_service

        # Generate dynamic question
        question = await engine.generate_dynamic_question(
            chart_data=TEST_CHART_DATA,
            previous_answers={"responses": TEST_QUESTIONNAIRE_DATA["responses"]},
            current_confidence=60.0
        )

        # Verify question
        assert "health" in question["text"].lower()
        assert question["type"] == "yes_no"
        assert question["relevance"] == "high"
        assert question["ai_generated"] is True
        assert "rationale" in question

        # Verify openai_service was called correctly
        mock_openai_service.generate_completion.assert_called_once()
        args, kwargs = mock_openai_service.generate_completion.call_args
        assert kwargs["task_type"] == "auxiliary"

    async def test_calculate_confidence_with_ai(self):
        """Test AI-enhanced confidence calculation"""
        # Import questionnaire engine
        from ai_service.utils.questionnaire_engine import QuestionnaireEngine

        # Mock OpenAI service for questionnaire
        mock_openai_service = AsyncMock()
        mock_openai_service.generate_completion.return_value = {
            "content": json.dumps({
                "confidence_score": 82.5,
                "reasoning": "Multiple specific life events provided with clear timing"
            }),
            "model_used": "gpt-4o-mini",
            "tokens": {"prompt": 300, "completion": 100, "total": 400},
            "cost": 0.01,
            "response_time": 0.5
        }

        # Create engine with mock service
        engine = QuestionnaireEngine()
        engine.openai_service = mock_openai_service

        # Calculate confidence with AI enhancement
        confidence = await engine.calculate_confidence(
            answers={"responses": TEST_QUESTIONNAIRE_DATA["responses"] * 3},  # Need 3+ responses for AI confidence
            chart_data=TEST_CHART_DATA
        )

        # Verify confidence
        assert confidence > 70  # Higher than base confidence for 2 questions

        # Verify openai_service was called correctly
        mock_openai_service.generate_completion.assert_called_once()
        args, kwargs = mock_openai_service.generate_completion.call_args
        assert kwargs["task_type"] == "auxiliary"
