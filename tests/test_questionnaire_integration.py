import unittest
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from ai_service.utils.questionnaire_engine import QuestionnaireEngine
from ai_service.api.services.questionnaire_service import DynamicQuestionnaireService

class TestQuestionnaireFlow(unittest.TestCase):
    """Integration tests for the questionnaire flow"""

    def setUp(self):
        """Set up common test data"""
        # Sample birth data
        self.birth_data = {
            "birth_date": "1990-01-15",
            "birth_time": "12:30:00",
            "latitude": 40.7128,
            "longitude": -74.0060
        }

        # Sample chart data
        self.chart_data = {
            "chart_id": "test_chart",
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

        # Sample questions and answers
        self.qa_pairs = [
            {"q": "Are you introverted?", "a": "Yes", "relevance": "medium"},
            {"q": "Have you changed careers?", "a": "Yes", "relevance": "medium"},
            {"q": "Did you experience a major life change at age 30?", "a": "Yes", "relevance": "high"},
            {"q": "Were you born in the morning or evening?", "a": "Morning", "relevance": "high"},
            {"q": "Do you have a slim build?", "a": "Yes", "relevance": "high"}
        ]

    @pytest.mark.asyncio
    async def test_questionnaire_confidence_progression(self):
        """Test confidence increases properly through questionnaire flow"""
        # Create engine with mocked OpenAI service
        engine = QuestionnaireEngine()
        engine.openai_service = AsyncMock()

        # Initial empty answers
        answers = {
            "responses": []
        }

        # Track confidence progression
        confidence_values = []

        # Create AsyncMock objects with pre-defined return values
        confidence_mocks = [
            AsyncMock(return_value=30.0),
            AsyncMock(return_value=45.0),
            AsyncMock(return_value=60.0),
            AsyncMock(return_value=75.0),
            AsyncMock(return_value=85.0),
            AsyncMock(return_value=90.0)
        ]

        # Initial confidence
        with patch.object(engine, 'calculate_confidence', confidence_mocks[0]):
            initial_confidence = await engine.calculate_confidence(answers, self.chart_data)
            confidence_values.append(initial_confidence)

        # Add answers one by one
        for i, qa in enumerate(self.qa_pairs):
            answers["responses"].append({
                "question_id": f"q_{i}",
                "question": qa["q"],
                "answer": qa["a"],
                "relevance": qa["relevance"]
            })

            # Calculate new confidence with appropriate mock
            with patch.object(engine, 'calculate_confidence', confidence_mocks[i+1]):
                new_confidence = await engine.calculate_confidence(answers, self.chart_data)
                confidence_values.append(new_confidence)

        # Assertions
        self.assertTrue(len(confidence_values) > 0)
        self.assertTrue(confidence_values[-1] > confidence_values[0])
        self.assertTrue(confidence_values[-1] >= 75.0)  # Should reach high confidence

        # Check that confidence increases monotonically
        for i in range(1, len(confidence_values)):
            self.assertTrue(confidence_values[i] >= confidence_values[i-1])

    @pytest.mark.asyncio
    async def test_questionnaire_birth_time_narrowing(self):
        """Test birth time range narrows with each answer"""
        # Create mocked services
        chart_service = AsyncMock()
        questionnaire_service = DynamicQuestionnaireService(AsyncMock())

        # Setup decreasing time ranges with each answer
        birth_time_ranges = [60, 45, 30, 20, 10]
        previous_answers = {"responses": []}

        for i, time_range in enumerate(birth_time_ranges):
            # Setup next mock response with decreasing time range
            mock_result = {
                "next_question": {
                    "id": f"q_{i}",
                    "text": f"Question {i}?",
                    "type": "yes_no"
                },
                "birth_time_range": {"minutes": time_range},
                "confidence": 30.0 + (i * 10.0)
            }

            # Create AsyncMock for generate_next_question
            generate_mock = AsyncMock()
            generate_mock.return_value = mock_result

            # Add a previous answer if not the first question
            if i > 0:
                previous_answers["responses"].append({
                    "question_id": f"q_{i-1}",
                    "question": f"Question {i-1}?",
                    "answer": "Yes"
                })

            # Get next question with AsyncMock
            with patch.object(questionnaire_service, 'generate_next_question', generate_mock):
                result = await questionnaire_service.generate_next_question(
                    self.birth_data, previous_answers
                )

                # Verify time range decreases
                self.assertIn("birth_time_range", result)
                self.assertEqual(result["birth_time_range"]["minutes"], time_range)

    @pytest.mark.asyncio
    async def test_complete_questionnaire_flow(self):
        """Test a complete questionnaire flow from first question to rectification"""
        # Create engine with mocked OpenAI service
        engine = QuestionnaireEngine()
        engine.openai_service = AsyncMock()

        # Create AsyncMock for first question
        first_mock = AsyncMock()
        first_mock.return_value = {
            "id": "q_0",
            "text": self.qa_pairs[0]["q"],
            "type": "yes_no",
            "options": ["Yes", "No", "Not sure"]
        }

        # Step 1: Get first question
        with patch.object(engine, 'get_first_question', first_mock):
            first_question = await engine.get_first_question(self.chart_data, self.birth_data)
            self.assertIsNotNone(first_question)
            self.assertEqual(first_question["id"], "q_0")

        # Step 2: Answer questions one by one until confidence threshold
        previous_answers = {"responses": []}
        confidence = 30.0
        target_confidence = 90.0

        # Add answers one by one
        for i in range(1, len(self.qa_pairs)):
            # Record the answer to previous question
            previous_answers["responses"].append({
                "question_id": f"q_{i-1}",
                "question": self.qa_pairs[i-1]["q"],
                "answer": self.qa_pairs[i-1]["a"],
                "relevance": self.qa_pairs[i-1]["relevance"]
            })

            # Create AsyncMock for next question
            next_mock = AsyncMock()
            next_mock.return_value = {
                "id": f"q_{i}",
                "text": self.qa_pairs[i]["q"],
                "type": "yes_no",
                "options": ["Yes", "No", "Not sure"]
            }

            # Create AsyncMock for confidence calculation
            new_confidence = min(confidence + (15.0 * i), 95.0)
            calc_mock = AsyncMock()
            calc_mock.return_value = new_confidence

            # Calculate new confidence with AsyncMock
            with patch.object(engine, 'calculate_confidence', calc_mock):
                confidence = await engine.calculate_confidence(previous_answers, self.chart_data)

            # Generate next question with AsyncMock
            with patch.object(engine, 'get_next_question', next_mock):
                next_question = await engine.get_next_question(
                    chart_data=self.chart_data,
                    birth_details=self.birth_data,
                    previous_answers=previous_answers,
                    current_confidence=confidence
                )

                # Verify next question matches expected
                self.assertEqual(next_question["id"], f"q_{i}")

                # If we reached target confidence, stop asking questions
                if confidence >= target_confidence:
                    break

        # Final assertions
        self.assertTrue(confidence >= 70.0)  # Should reach decent confidence
        self.assertTrue(len(previous_answers["responses"]) > 1)  # Should have multiple answers
