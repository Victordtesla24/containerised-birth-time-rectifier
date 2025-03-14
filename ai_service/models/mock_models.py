"""
Mock models for testing and development environments.
This module provides mock implementations of AI service models.
"""

from typing import Dict, List, Any, Optional
import logging
import json
import os
import random
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

class MockOpenAIService:
    """Mock implementation of the OpenAI service for testing."""

    def __init__(self):
        """Initialize the mock OpenAI service."""
        logger.debug("Initializing mock OpenAI service")

    async def generate_completion(self, prompt: str, task_type: str, max_tokens: int = 500,
                               temperature: float = 0.7, system_message: Optional[str] = None) -> Dict[str, Any]:
        """Generate a mock completion response."""
        logger.debug(f"Mock generating completion for task: {task_type}")

        # Return different mock responses based on task type
        if "rectif" in task_type.lower():
            return self._mock_rectification_response()
        elif "quest" in task_type.lower():
            return self._mock_questionnaire_response()
        else:
            return self._mock_general_response()

    def _mock_rectification_response(self) -> Dict[str, Any]:
        """Generate a mock rectification response."""
        return {
            "text": json.dumps({
                "adjustment_minutes": 15,
                "confidence": 85.5,
                "reasoning": "Based on the analysis of planetary positions and life events."
            }),
            "model": "mock-gpt-4",
            "usage": {
                "prompt_tokens": 250,
                "completion_tokens": 100,
                "total_tokens": 350
            },
            "finish_reason": "stop"
        }

    def _mock_questionnaire_response(self) -> Dict[str, Any]:
        """Generate a mock questionnaire response."""
        return {
            "text": json.dumps({
                "text": "When did you experience a significant career change?",
                "type": "date",
                "options": []
            }),
            "model": "mock-gpt-4",
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 50,
                "total_tokens": 250
            },
            "finish_reason": "stop"
        }

    def _mock_general_response(self) -> Dict[str, Any]:
        """Generate a mock general response."""
        return {
            "text": "This is a mock response for testing purposes.",
            "model": "mock-gpt-4",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120
            },
            "finish_reason": "stop"
        }

    async def generate_questions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mock questions for birth time rectification based on context.

        Args:
            context: Dictionary containing birth details, previous answers, etc.

        Returns:
            Dictionary with generated questions and metadata
        """
        logger.debug("Mock generating questions for birth time rectification")

        # Extract context information for more realistic mock responses
        question_count = context.get("question_count", 0)
        previous_answers = context.get("previous_answers", {})

        # Calculate mock confidence score based on number of previous answers
        confidence_score = 0.2 + (question_count * 0.1)
        confidence_score = min(confidence_score, 0.95)

        # Generate different questions based on how many have been asked
        if question_count < 2:
            # Initial questions about life events
            questions = [
                {
                    "id": f"mock_q_{question_count+1}",
                    "text": "Did you experience any significant career changes in your life?",
                    "type": "boolean",
                    "relevance": "high"
                },
                {
                    "id": f"mock_q_{question_count+2}",
                    "text": "When did you get married or enter a significant relationship?",
                    "type": "date",
                    "relevance": "high"
                },
                {
                    "id": f"mock_q_{question_count+3}",
                    "text": "How would you describe your personality?",
                    "type": "options",
                    "options": ["Introverted", "Extroverted", "Balanced"],
                    "relevance": "medium"
                }
            ]
        elif question_count < 5:
            # Follow-up questions about health and family
            questions = [
                {
                    "id": f"mock_q_{question_count+1}",
                    "text": "Have you experienced any significant health issues?",
                    "type": "boolean",
                    "relevance": "high"
                },
                {
                    "id": f"mock_q_{question_count+2}",
                    "text": "When was your first child born?",
                    "type": "date",
                    "relevance": "high"
                },
                {
                    "id": f"mock_q_{question_count+3}",
                    "text": "How would you describe your relationship with your parents?",
                    "type": "options",
                    "options": ["Very close", "Somewhat close", "Distant", "Complicated"],
                    "relevance": "medium"
                }
            ]
        else:
            # Final clarifying questions
            questions = [
                {
                    "id": f"mock_q_{question_count+1}",
                    "text": "Did you move to a different city or country at any point in your life?",
                    "type": "boolean",
                    "relevance": "high"
                },
                {
                    "id": f"mock_q_{question_count+2}",
                    "text": "When did this move occur?",
                    "type": "date",
                    "relevance": "high"
                }
            ]

        # Check for contradictions in previous answers and add a clarifying question if needed
        if len(previous_answers) >= 2:
            # Simulate finding a contradiction (in a real implementation, this would check actual answers)
            questions.append({
                "id": f"mock_q_clarify_{question_count}",
                "text": "You mentioned different dates for significant life events. Could you clarify when your career change occurred?",
                "type": "date",
                "relevance": "high"
            })

        return {
            "questions": questions,
            "confidence_score": confidence_score,
            "is_complete": confidence_score >= 0.9,
            "has_reached_threshold": confidence_score >= 0.8
        }

class MockUnifiedRectificationModel:
    """Mock implementation of the UnifiedRectificationModel for testing."""

    def __init__(self):
        """Initialize the mock unified rectification model."""
        logger.debug("Initializing mock unified rectification model")

    async def rectify_birth_time(self, birth_details: Dict[str, Any],
                            answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a mock birth time rectification."""
        # Parse original time
        original_time = birth_details.get("birthTime", "12:00")
        time_parts = original_time.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1])

        # Make a simple adjustment for testing purposes
        adjusted_minute = (minute + random.randint(1, 15)) % 60
        adjusted_hour = (hour + (1 if adjusted_minute < minute else 0)) % 24

        rectified_time = f"{adjusted_hour:02d}:{adjusted_minute:02d}"

        return {
            "originalTime": original_time,
            "rectifiedTime": rectified_time,
            "confidence": 85.0,
            "reliability": "moderate",
            "explanation": "Mock birth time rectification for testing."
        }
