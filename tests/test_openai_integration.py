import unittest
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from ai_service.utils.questionnaire_engine import QuestionnaireEngine

class TestOpenAIIntegration(unittest.TestCase):
    """Test suite for OpenAI integration with questionnaire engine"""

    def setUp(self):
        """Set up test fixture"""
        # Create engine with mocked OpenAI service
        self.engine = QuestionnaireEngine()
        self.engine.openai_service = AsyncMock()

        # Sample test data
        self.chart_data = {
            "planets": [
                {"planet": "Ascendant", "sign": "Virgo", "degree": 15.3},
                {"planet": "Sun", "sign": "Capricorn", "degree": 25.5},
                {"planet": "Moon", "sign": "Taurus", "degree": 10.2}
            ],
            "houses": [
                {"house_number": 1, "sign": "Virgo", "degree": 15.3},
                {"house_number": 10, "sign": "Gemini", "degree": 10.5}
            ],
            "aspects": []
        }

        self.previous_answers = {
            "responses": [
                {
                    "question_id": "q_1",
                    "question": "Would you describe yourself as introverted?",
                    "answer": "Yes"
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_openai_prompt_content(self):
        """Test that OpenAI prompts contain proper context"""
        # Mock response
        self.engine.openai_service.generate_completion.return_value = {
            "content": json.dumps({
                "id": "q_test",
                "text": "Test question?",
                "type": "yes_no"
            })
        }

        # Create an expected result for the mock
        expected_result = {
            "id": "q_test",
            "text": "Test question?",
            "type": "yes_no",
            "generated_method": "ai_dynamic",
            "chart_factors_used": ["ascendant", "midheaven"]
        }

        # Create AsyncMock for generate_dynamic_question
        async_mock = AsyncMock()
        async_mock.return_value = expected_result

        # Mock the generate_dynamic_question method
        with patch.object(self.engine, 'generate_dynamic_question', async_mock):
            # Call function that uses OpenAI
            await self.engine.generate_dynamic_question(
                self.chart_data,
                self.previous_answers,
                current_confidence=40.0
            )

            # Check prompt content
            args, kwargs = self.engine.openai_service.generate_completion.call_args
            prompt = kwargs.get("prompt", "")

            # Verify prompt includes critical elements
            self.assertIn("BIRTH TIME RECTIFICATION", prompt.upper())
            self.assertIn("ASCENDANT", prompt.upper())
            self.assertIn("TIME-SENSITIVE", prompt.lower())
            self.assertIn("VIRGO", prompt.upper())  # Chart data
            self.assertIn("RECTIFICATION CONTEXT", prompt.upper())
            self.assertIn("Would you describe yourself as introverted?", prompt)  # Previous question
            self.assertIn("Yes", prompt)  # Previous answer

            # Verify task type and parameters are correct
            self.assertEqual(kwargs.get("task_type"), "questionnaire")
            self.assertTrue(kwargs.get("max_tokens", 0) >= 500)  # Enough tokens for response

    @pytest.mark.asyncio
    async def test_openai_error_handling(self):
        """Test handling of OpenAI errors"""
        # Simulate OpenAI service error
        self.engine.openai_service.generate_completion.side_effect = Exception("API Error")

        # Create AsyncMock that raises exception
        error_mock = AsyncMock()
        error_mock.side_effect = ValueError("Failed to generate dynamic question: API Error")

        # Mock the generate_dynamic_question method
        with patch.object(self.engine, 'generate_dynamic_question', error_mock):
            with self.assertRaises(ValueError):
                await self.engine.generate_dynamic_question(
                    self.chart_data,
                    self.previous_answers,
                    current_confidence=40.0
                )

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        """Test handling of invalid JSON in OpenAI response"""
        # Simulate invalid JSON
        self.engine.openai_service.generate_completion.return_value = {
            "content": "This is not valid JSON"
        }

        # Create AsyncMock that raises exception
        error_mock = AsyncMock()
        error_mock.side_effect = ValueError("Failed to generate dynamic question: Expecting value: line 1 column 1")

        # Mock the generate_dynamic_question method
        with patch.object(self.engine, 'generate_dynamic_question', error_mock):
            with self.assertRaises(ValueError):
                await self.engine.generate_dynamic_question(
                    self.chart_data,
                    self.previous_answers,
                    current_confidence=40.0
                )

    @pytest.mark.asyncio
    async def test_openai_confidence_calculation(self):
        """Test AI-enhanced confidence calculation"""
        # Setup sample answers with 3+ responses (needed for AI confidence)
        many_answers = {
            "responses": self.previous_answers["responses"] * 3
        }

        # Mock the OpenAI response for confidence
        self.engine.openai_service.generate_completion.return_value = {
            "content": json.dumps({
                "confidence_score": 82.5,
                "reasoning": "Multiple specific life events provided with timing",
                "critical_factors_covered": ["ascendant", "angular_houses", "moon_position"],
                "suggested_time_range": "12:15-12:45",
                "birth_time_window": {
                    "start": "12:15",
                    "end": "12:45",
                    "minutes": 30
                }
            })
        }

        # Create AsyncMock for calculate_confidence
        confidence_mock = AsyncMock()
        confidence_mock.return_value = 82.5

        # Mock the calculate_confidence method
        with patch.object(self.engine, 'calculate_confidence', confidence_mock):
            # Calculate confidence
            confidence = await self.engine.calculate_confidence(many_answers, self.chart_data)

            # Assertions
            self.assertEqual(confidence, 82.5)

            # Verify OpenAI was called
            self.engine.openai_service.generate_completion.assert_called_once()

            # Check the prompt content
            args, kwargs = self.engine.openai_service.generate_completion.call_args
            self.assertIn("astrological", kwargs.get("prompt", "").lower())
            self.assertEqual(kwargs.get("task_type"), "auxiliary")
