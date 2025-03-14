"""
Dynamic Questionnaire Service

This service generates personalized questions for birth time rectification
based on previous answers and birth details.
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import random

from ai_service.api.services.openai import OpenAIService

# Set up logging
logger = logging.getLogger(__name__)

class DynamicQuestionnaireService:
    """
    Service for generating dynamic, personalized questionnaires
    for birth time rectification.
    """

    def __init__(self, openai_service: Optional[Any] = None):
        """
        Initialize the questionnaire service.

        Args:
            openai_service: Optional OpenAI service instance
        """
        # Use mock service in test environments
        if os.environ.get("APP_ENV") == "test" or os.environ.get("TESTING") == "true":
            try:
                from ai_service.models.mock_models import MockOpenAIService
                self.openai_service = MockOpenAIService()
                logging.debug("Using mock OpenAI service for tests")
            except ImportError:
                logging.debug("Mock models not available, using standard OpenAI service")
                self.openai_service = openai_service or OpenAIService()
        else:
            self.openai_service = openai_service or OpenAIService()

        # Base question categories
        self.question_categories = [
            "life_events",
            "physical_traits",
            "personality_traits",
            "career",
            "relationships",
            "health",
            "education",
            "travel",
            "spiritual_experiences"
        ]

        # Load question templates
        self.question_templates = self._load_question_templates()

        # Threshold for confidence score
        self.confidence_threshold = 0.8

        # Maximum number of questions
        self.max_questions = 10

    async def generate_questions(self, birth_details: Dict[str, Any], previous_answers: Dict[str, Any], current_confidence: float) -> Dict[str, Any]:
        """
        Generate dynamic questions based on birth details and previous answers.

        Args:
            birth_details: Birth details including date, time, place, coordinates
            previous_answers: Previous answers to questions
            current_confidence: Current confidence score (0-100)

        Returns:
            Dictionary with questions, confidence score, and completion status
        """
        try:
            # Normalize confidence score to 0-1 range
            current_confidence = current_confidence / 100 if current_confidence > 1 else current_confidence

            # Check if we've reached the confidence threshold
            if current_confidence >= self.confidence_threshold:
                return {
                    "questions": [],
                    "confidence_score": current_confidence,
                    "is_complete": True,
                    "has_reached_threshold": True
                }

            # Check if we've reached the maximum number of questions
            if len(previous_answers) >= self.max_questions:
                return {
                    "questions": [],
                    "confidence_score": current_confidence,
                    "is_complete": True,
                    "has_reached_threshold": current_confidence >= self.confidence_threshold
                }

            # Check for contradictory answers
            contradictions = self._check_for_contradictions(previous_answers)

            # If contradictions found, generate clarifying questions
            if contradictions and len(contradictions) > 0:
                clarifying_questions = self._generate_clarifying_questions(contradictions)

                # Return clarifying questions with unchanged confidence
                return {
                    "questions": clarifying_questions,
                    "confidence_score": current_confidence,
                    "is_complete": False,
                    "has_reached_threshold": False,
                    "contradictions_found": True
                }

            # Try to use AI to generate personalized questions
            try:
                if self.openai_service:
                    # Generate questions using OpenAI
                    ai_questions = await self._generate_ai_questions(birth_details, previous_answers)

                    if ai_questions and len(ai_questions) > 0:
                        # Calculate new confidence score
                        new_confidence = self._calculate_confidence_score(current_confidence, previous_answers)

                        return {
                            "questions": ai_questions,
                            "confidence_score": new_confidence,
                            "is_complete": new_confidence >= self.confidence_threshold,
                            "has_reached_threshold": new_confidence >= self.confidence_threshold
                        }
            except Exception as e:
                logging.warning(f"Failed to generate AI questions: {str(e)}")

            # Fall back to template-based questions if AI fails
            template_questions = self._generate_template_questions(birth_details, previous_answers)

            # Calculate new confidence score
            new_confidence = self._calculate_confidence_score(current_confidence, previous_answers)

            return {
                "questions": template_questions,
                "confidence_score": new_confidence,
                "is_complete": new_confidence >= self.confidence_threshold,
                "has_reached_threshold": new_confidence >= self.confidence_threshold
            }

        except Exception as e:
            logging.error(f"Error generating questions: {str(e)}")
            # Return fallback questions in case of error
            return {
                "questions": self._get_fallback_questions(),
                "confidence_score": current_confidence,
                "is_complete": False,
                "has_reached_threshold": False,
                "error": str(e)
            }

    def _check_for_contradictions(self, previous_answers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictory answers in previous responses.

        Args:
            previous_answers: Dictionary of previous answers

        Returns:
            List of contradiction details
        """
        contradictions = []

        # Define contradiction rules
        contradiction_rules = [
            # Example: Introvert/Extrovert contradiction
            {
                "questions": ["personality_introvert", "personality_extrovert"],
                "contradictory_values": [
                    {"q1_value": "yes", "q2_value": "yes"},
                    {"q1_value": "strongly_agree", "q2_value": "strongly_agree"}
                ]
            },
            # Example: Career change timing contradiction
            {
                "questions": ["career_change_recent", "career_stable"],
                "contradictory_values": [
                    {"q1_value": "yes", "q2_value": "yes"}
                ]
            }
        ]

        # Check each contradiction rule
        for rule in contradiction_rules:
            q1, q2 = rule["questions"]

            # Skip if either question hasn't been answered
            if q1 not in previous_answers or q2 not in previous_answers:
                continue

            # Check for contradictory values
            for contradiction in rule["contradictory_values"]:
                if (previous_answers[q1] == contradiction["q1_value"] and
                    previous_answers[q2] == contradiction["q2_value"]):
                    contradictions.append({
                        "questions": [q1, q2],
                        "values": [previous_answers[q1], previous_answers[q2]]
                    })

        return contradictions

    def _generate_clarifying_questions(self, contradictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate clarifying questions for contradictory answers.

        Args:
            contradictions: List of contradiction details

        Returns:
            List of clarifying questions
        """
        clarifying_questions = []

        for i, contradiction in enumerate(contradictions):
            q1, q2 = contradiction["questions"]
            v1, v2 = contradiction["values"]

            # Generate a clarifying question
            question = {
                "id": f"clarify_{i}_{uuid.uuid4().hex[:8]}",
                "text": f"Earlier you indicated both '{q1}' and '{q2}', which seem contradictory. Which feels more accurate most of the time?",
                "type": "options",
                "options": [
                    f"Mostly {q1.replace('_', ' ')}",
                    f"Mostly {q2.replace('_', ' ')}",
                    "It varies significantly",
                    "Neither is accurate"
                ],
                "is_clarification": True,
                "related_questions": [q1, q2]
            }

            clarifying_questions.append(question)

        return clarifying_questions

    async def _generate_ai_questions(self, birth_details: Dict[str, Any], previous_answers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate questions using AI based on birth details and previous answers.

        Args:
            birth_details: Birth details
            previous_answers: Previous answers

        Returns:
            List of AI-generated questions
        """
        if not self.openai_service:
            return []

        try:
            # Prepare context for AI
            context = {
                "birth_details": birth_details,
                "previous_answers": previous_answers,
                "question_count": len(previous_answers),
                "remaining_questions": self.max_questions - len(previous_answers)
            }

            # Call OpenAI service to generate questions
            response = await self.openai_service.generate_questions(context)

            # Process and format AI-generated questions
            questions = []

            for i, q in enumerate(response.get("questions", [])):
                question_id = q.get("id", f"ai_q_{i}_{uuid.uuid4().hex[:8]}")

                question = {
                    "id": question_id,
                    "text": q.get("text", ""),
                    "type": q.get("type", "boolean"),
                    "options": q.get("options", ["Yes", "No"]),
                    "relevance": q.get("relevance", "medium")
                }

                questions.append(question)

            return questions

        except Exception as e:
            logging.error(f"Error generating AI questions: {str(e)}")
            return []

    def _generate_template_questions(self, birth_details: Dict[str, Any], previous_answers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate questions from templates based on birth details and previous answers.

        Args:
            birth_details: Birth details
            previous_answers: Previous answers

        Returns:
            List of template-based questions
        """
        # Determine which categories to focus on
        used_categories = set()
        for answer_key in previous_answers.keys():
            for category in self.question_categories:
                if category in answer_key:
                    used_categories.add(category)

        # Prioritize unused categories
        available_categories = [c for c in self.question_categories if c not in used_categories]

        # If all categories used, pick random ones
        if not available_categories:
            available_categories = self.question_categories

        # Select categories to use for this batch
        selected_categories = random.sample(
            available_categories,
            min(3, len(available_categories))
        )

        # Generate questions from selected categories
        questions = []

        for category in selected_categories:
            # Get templates for this category
            templates = self.question_templates.get(category, [])

            if templates:
                # Select a random template
                template = random.choice(templates)

                # Generate a unique ID
                question_id = f"{category}_{uuid.uuid4().hex[:8]}"

                # Create question from template
                question = {
                    "id": question_id,
                    "text": template.get("text", ""),
                    "type": template.get("type", "boolean"),
                    "options": template.get("options", ["Yes", "No"]),
                    "relevance": template.get("relevance", "medium")
                }

                questions.append(question)

        return questions

    def _calculate_confidence_score(self, current_confidence: float, previous_answers: Dict[str, Any]) -> float:
        """
        Calculate new confidence score based on current confidence and previous answers.

        Args:
            current_confidence: Current confidence score (0-1)
            previous_answers: Previous answers

        Returns:
            New confidence score (0-1)
        """
        # Start with base confidence
        if current_confidence <= 0:
            base_confidence = 0.2  # Start at 20%
        else:
            base_confidence = current_confidence

        # Add confidence based on number of answers
        answer_count = len(previous_answers)

        # Calculate increment based on diminishing returns
        if answer_count <= 3:
            increment = 0.1  # First 3 questions add 10% each
        elif answer_count <= 6:
            increment = 0.08  # Next 3 questions add 8% each
        elif answer_count <= 9:
            increment = 0.05  # Next 3 questions add 5% each
        else:
            increment = 0.02  # Additional questions add 2% each

        # Calculate new confidence
        new_confidence = base_confidence + increment

        # Cap at 95% (never 100% certain)
        return min(new_confidence, 0.95)

    def _get_fallback_questions(self) -> List[Dict[str, Any]]:
        """
        Get fallback questions in case of errors.

        Returns:
            List of fallback questions
        """
        return [
            {
                "id": f"fallback_1_{uuid.uuid4().hex[:8]}",
                "text": "Have you experienced any major career changes?",
                "type": "boolean",
                "options": ["Yes", "No"],
                "relevance": "high"
            },
            {
                "id": f"fallback_2_{uuid.uuid4().hex[:8]}",
                "text": "When did you get married or enter a significant relationship?",
                "type": "date",
                "relevance": "high"
            },
            {
                "id": f"fallback_3_{uuid.uuid4().hex[:8]}",
                "text": "Would you describe your body type as slim or stocky?",
                "type": "options",
                "options": ["Slim", "Average", "Stocky"],
                "relevance": "medium"
            }
        ]

    def _load_question_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load question templates for each category.

        Returns:
            Dictionary of question templates by category
        """
        return {
            "life_events": [
                {
                    "text": "Have you experienced a major life change around age 30?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "high"
                },
                {
                    "text": "Did you move to a different city or country between ages 25-35?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "medium"
                }
            ],
            "physical_traits": [
                {
                    "text": "Would you describe your body type as slim or stocky?",
                    "type": "options",
                    "options": ["Slim", "Average", "Stocky"],
                    "relevance": "medium"
                },
                {
                    "text": "Do you have any distinctive physical features?",
                    "type": "text",
                    "relevance": "medium"
                }
            ],
            "personality_traits": [
                {
                    "text": "Do you consider yourself more introverted or extroverted?",
                    "type": "options",
                    "options": ["Strongly Introverted", "Somewhat Introverted", "Balanced", "Somewhat Extroverted", "Strongly Extroverted"],
                    "relevance": "high"
                },
                {
                    "text": "Are you more analytical or creative in your thinking?",
                    "type": "options",
                    "options": ["Very Analytical", "Somewhat Analytical", "Balanced", "Somewhat Creative", "Very Creative"],
                    "relevance": "high"
                }
            ],
            "career": [
                {
                    "text": "Have you experienced any major career changes?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "high"
                },
                {
                    "text": "Did you get married or start a significant long-term relationship around June 2015?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "high"
                }
            ],
            "relationships": [
                {
                    "text": "When did you get married or enter a significant relationship?",
                    "type": "date",
                    "relevance": "high"
                },
                {
                    "text": "Have you experienced any significant relationship changes in the last 5 years?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "medium"
                }
            ],
            "health": [
                {
                    "text": "Have you experienced any significant health events?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "medium"
                },
                {
                    "text": "At what age did you experience your most significant health challenge?",
                    "type": "number",
                    "relevance": "medium"
                }
            ],
            "education": [
                {
                    "text": "Did you change your educational focus or major during your studies?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "medium"
                },
                {
                    "text": "At what age did you complete your highest level of education?",
                    "type": "number",
                    "relevance": "medium"
                }
            ],
            "travel": [
                {
                    "text": "Have you lived in multiple countries or cities?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "low"
                },
                {
                    "text": "Did you travel extensively during your 20s?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "low"
                }
            ],
            "spiritual_experiences": [
                {
                    "text": "Have you had any spiritual or transformative experiences? If so, at what age?",
                    "type": "text",
                    "relevance": "medium"
                },
                {
                    "text": "What's the most significant life event you've experienced and at what age?",
                    "type": "text",
                    "relevance": "high"
                }
            ]
        }

# Singleton instance
_instance = None

def get_questionnaire_service(openai_service: Optional[Any] = None) -> Any:
    """Get or create the questionnaire service singleton"""
    global _instance
    if _instance is None:
        _instance = DynamicQuestionnaireService(openai_service)
    return _instance
