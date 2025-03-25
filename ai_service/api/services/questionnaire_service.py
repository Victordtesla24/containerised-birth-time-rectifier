"""
Questionnaire service for birth time rectification.

This module provides a service for generating, processing, and analyzing
astrologically-relevant questions used for birth time rectification.
"""

import logging
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import random

# Import service dependencies
from ai_service.api.services.openai import get_openai_service
from ai_service.api.services.openai.service import OpenAIService
from ai_service.utils.dependency_container import get_container
from ai_service.api.services.session_service import get_session_store

# Configure logging
logger = logging.getLogger(__name__)

# Define exports (only actual classes in this module)
__all__ = ["QuestionnaireService", "get_questionnaire_service"]

# Constants for questions
QUESTION_CATEGORIES = [
    "life_events",
    "personality",
    "relationships",
    "career",
    "health",
    "spirituality",
    "physical_appearance"
]

# Constants for question templates
QUESTION_TEMPLATES = {
    "ascendant": "Based on personality traits {traits}, which ascendant sign seems most likely?",
    "life_events": "What major life events occurred around age {age}?",
    "physical": "Is there any distinctive physical trait related to {planet} in {sign}?",
    "relationships": "How would you describe your relationship dynamics in terms of {aspect}?",
    "career": "Have you experienced career changes or developments when {planet} transited your {house} house?",
    "health": "Have you experienced any health issues related to {body_part}, which is governed by {sign}?"
}

class QuestionnaireService:
    """
    Service for managing birth time rectification questionnaires.

    This service handles the generation, processing, and analysis of questions
    used for birth time rectification.
    """

    def __init__(self, openai_service: Optional[OpenAIService] = None):
        """
        Initialize the questionnaire service.

        Args:
            openai_service: Optional OpenAI service for AI-powered question generation
        """
        self.openai_service = openai_service
        self.session_store = get_session_store()

        logger.info("QuestionnaireService initialized")

    async def get_initial_questions(self, chart_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get initial set of questions for the rectification process.

        Args:
            chart_data: Optional chart data to personalize questions

        Returns:
            List of question dictionaries
        """
        try:
            # Generate initial questions based on chart data
            user_id = str(uuid.uuid4())
            rectification_type = "general"

            # Use chart data as client data if available
            client_data = {"birth_details": chart_data.get("birth_details", {})} if chart_data else None

            # Import the questionnaire generation module dynamically to avoid circular imports
            from ai_service.api.services.questionnaire_service_generation import generate_questionnaire

            # Generate personalized questionnaire
            questions = await generate_questionnaire(
                user_id=user_id,
                rectification_type=rectification_type,
                client_data=client_data
            )

            return questions

        except Exception as e:
            logger.error(f"Error getting initial questions: {e}")
            # Return a minimal set of questions if generation fails
            return [
                {
                    "id": f"q_birth_{uuid.uuid4().hex[:8]}",
                    "text": "Do you know if you were born closer to sunrise, midday, sunset, or during the night?",
                    "type": "multiple_choice",
                    "options": [
                        {"value": "sunrise", "text": "Around sunrise (early morning)"},
                        {"value": "midday", "text": "Around midday"},
                        {"value": "sunset", "text": "Around sunset (early evening)"},
                        {"value": "night", "text": "During the night (late evening/early morning)"},
                        {"value": "unknown", "text": "I don't know"}
                    ],
                    "category": "birth_circumstances"
                }
            ]

    async def generate_next_question(self,
                               chart_data: Dict[str, Any],
                               previous_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate the next question based on chart data and previous answers.

        Args:
            chart_data: Chart data to use for personalization
            previous_answers: Previous question-answer pairs

        Returns:
            Dictionary with the next question
        """
        # If no previous answers, get an initial question
        if not previous_answers:
            initial_questions = await self.get_initial_questions(chart_data)
            if initial_questions:
                return initial_questions[0]

        # Use astrological relevance to determine next question
        return await self._generate_astrologically_relevant_question(chart_data, previous_answers)

    async def submit_answer(self,
                      question_id: str,
                      answer: Any,
                      session_id: str,
                      chart_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit an answer to a question and process it.

        Args:
            question_id: ID of the question being answered
            answer: The answer content
            session_id: Session ID for tracking
            chart_id: Optional chart ID for reference

        Returns:
            Dictionary with the result of processing the answer
        """
        # Implement basic answer processing
        if not session_id:
            raise ValueError("Session ID is required")

        # Store the answer
        await self.session_store.add_question_response(
            session_id=session_id,
            question_id=question_id,
            question_text=f"Question {question_id}",  # Simplified for now
            answer=answer
        )

        # Return a success response
        return {
            "success": True,
            "session_id": session_id,
            "question_id": question_id
        }

    async def complete_questionnaire(self, session_id: str, chart_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete the questionnaire and provide analysis results.

        Args:
            session_id: Session ID with the collected answers
            chart_id: Optional chart ID for reference

        Returns:
            Dictionary with analysis results
        """
        # Implement basic completion logic
        responses = await self.session_store.get_responses(session_id)

        # Calculate confidence based on number of answers
        confidence = min(30 + (len(responses) * 10), 90)

        # Return a simple analysis
        return {
            "complete": True,
            "session_id": session_id,
            "confidence": confidence,
            "answers_count": len(responses),
            "analysis": f"Analysis based on {len(responses)} answers with {confidence}% confidence"
        }

    async def _generate_astrologically_relevant_question(self,
                                                   chart_data: Dict[str, Any],
                                                   previous_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an astrologically relevant question based on chart data.

        Args:
            chart_data: Chart data to use for question generation
            previous_answers: Previous answers to avoid repetition

        Returns:
            Dictionary with the question details

        Raises:
            ValueError: If OpenAI service is not available and required
        """
        # Get OpenAI service if not already set
        if not self.openai_service:
            self.openai_service = get_openai_service()

        if not self.openai_service:
            raise ValueError("OpenAI service is required for dynamic question generation")

        try:
            # Generate a question using OpenAI
            prompt = self._create_question_generation_prompt(chart_data, previous_answers)

            messages = [
                {"role": "system", "content": "You are an expert astrologer generating questions for birth time rectification."},
                {"role": "user", "content": prompt}
            ]

            response = await self.openai_service.generate_completion(
                prompt=messages,
                task_type="questionnaire",
                temperature=0.7
            )

            # Extract the generated question
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            question_data = self._extract_json_from_content(content)

            if not question_data or "text" not in question_data:
                raise ValueError("Failed to generate a valid question")

            # Ensure the question has required fields
            question_id = f"q_{uuid.uuid4().hex[:8]}"
            question_type = question_data.get("type", "text")

            question = {
                "id": question_id,
                "text": question_data["text"],
                "type": question_type,
                "category": question_data.get("category", "general")
            }

            # Add options if it's a multiple choice question
            if question_type == "multiple_choice" and "options" in question_data:
                question["options"] = question_data["options"]

            return question

        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")

            # Generate an alternative question based on chart data
            return self._generate_alternative_question(chart_data, previous_answers)

    def _create_question_generation_prompt(self, chart_data: Dict[str, Any], previous_answers: List[Dict[str, Any]]) -> str:
        """Create a prompt for generating an astrological question."""
        # Implement a basic prompt creation
        planets = chart_data.get("planets", {})
        houses = chart_data.get("houses", {})

        # Format chart highlights
        highlights = []
        for planet, data in planets.items():
            sign = data.get("sign", "")
            house = data.get("house", "")
            if sign and house:
                highlights.append(f"{planet} in {sign} in house {house}")

        chart_summary = "\n".join(highlights[:5])  # Limit to 5 highlights

        # Format previous questions to avoid repetition
        previous_questions = "\n".join([
            f"- {a.get('question_text', 'Unknown question')}"
            for a in previous_answers[-3:] if 'question_text' in a
        ])

        prompt = f"""
        Generate an astrologically relevant question for birth time rectification.

        Chart highlights:
        {chart_summary}

        Previous questions (avoid similarity):
        {previous_questions}

        Provide the question in JSON format with these fields:
        - text: The question text
        - type: "text" or "multiple_choice"
        - category: One of {', '.join(QUESTION_CATEGORIES)}
        - options: [For multiple_choice only] Array of option objects with "value" and "text"
        """

        return prompt

    def _extract_json_from_content(self, content: str) -> Dict[str, Any]:
        """Extract JSON from OpenAI response content."""
        try:
            # Find JSON block using regex
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find anything that looks like JSON
                json_match = re.search(r'(\{[\s\S]*\})', content)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # No JSON found
                    return {}

            # Parse the JSON
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Error extracting JSON from content: {str(e)}")
            return {}

    def _generate_alternative_question(self, chart_data: Dict[str, Any], previous_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an alternative question when OpenAI generation fails.

        Args:
            chart_data: Chart data to use for personalization
            previous_answers: Previous answers to avoid repetition

        Returns:
            Dictionary with question details
        """
        # Extract basic birth details
        birth_details = chart_data.get("birth_details", {})
        birth_year = None

        if birth_details and "date" in birth_details:
            try:
                birth_year = int(birth_details["date"].split("-")[0])
            except (ValueError, IndexError):
                pass

        # Get question categories that haven't been asked yet
        asked_categories = set(a.get("category", "unknown") for a in previous_answers if "category" in a)
        available_categories = ["life_events", "relationships", "career", "health", "spirituality", "education"]
        unused_categories = [c for c in available_categories if c not in asked_categories]

        # If all categories used, pick a random one
        category = random.choice(unused_categories) if unused_categories else random.choice(available_categories)

        # Generate question based on category
        question_id = f"q_{uuid.uuid4().hex[:8]}"

        if category == "life_events":
            return {
                "id": question_id,
                "text": "Describe any significant life events that occurred at ages 7, 14, 21, or 28.",
                "type": "text",
                "category": "life_events"
            }
        elif category == "relationships":
            return {
                "id": question_id,
                "text": "When did you meet your current partner or experience a significant relationship milestone?",
                "type": "text",
                "category": "relationships"
            }
        elif category == "career":
            return {
                "id": question_id,
                "text": "What age or date did you start your most significant job or career path?",
                "type": "text",
                "category": "career"
            }
        elif category == "health":
            return {
                "id": question_id,
                "text": "Have you experienced any significant health events? If so, when did they occur?",
                "type": "text",
                "category": "health"
            }
        elif category == "spirituality":
            return {
                "id": question_id,
                "text": "Have you had any spiritual awakening or transformation? When did this occur?",
                "type": "text",
                "category": "spirituality"
            }
        else:  # education or default
            return {
                "id": question_id,
                "text": "When did you complete your education or training for your profession?",
                "type": "text",
                "category": "education"
            }

def get_questionnaire_service() -> QuestionnaireService:
    """
    Get or create a QuestionnaireService instance.

    Returns:
        A QuestionnaireService instance
    """
    container = get_container()

    # Check if service already exists in container
    service = container.get('questionnaire_service')
    if service:
        return service

    # Create new service
    openai_service = get_openai_service()
    service = QuestionnaireService(openai_service=openai_service)

    # Register in container
    container.register_instance('questionnaire_service', service)

    return service
