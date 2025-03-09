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

from ai_service.api.services.openai_service import OpenAIService

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
            "spiritual_experiences"
        ]

        # Sample questions for each category (fallback if AI generation fails)
        self.sample_questions = {
            "life_events": [
                "When did you get married or enter a significant relationship?",
                "When was your first child born?",
                "When did you start your current job or career?",
                "When did you move to your current location?",
                "When did you experience a major health issue or accident?"
            ],
            "physical_traits": [
                "How would you describe your physical appearance?",
                "What is your body type (thin, medium, heavy)?",
                "What is your hair type and color?",
                "What is your eye color?",
                "Do you have any distinctive physical features?"
            ],
            "personality_traits": [
                "Would you describe yourself as introverted or extroverted?",
                "How do you handle stress or difficult situations?",
                "Are you more analytical or intuitive in your thinking?",
                "How would your close friends describe your personality?",
                "What are your dominant personality traits?"
            ],
            "career": [
                "What is your profession or career field?",
                "When did you make a significant career change?",
                "Have you experienced any major professional achievements?",
                "What are your natural talents related to work?",
                "Have you faced any significant challenges in your career?"
            ],
            "relationships": [
                "How would you describe your relationship patterns?",
                "When did you meet your spouse or significant partner?",
                "How many serious relationships have you had?",
                "How do you typically relate to family members?",
                "Do you make friends easily or prefer few close relationships?"
            ],
            "health": [
                "Have you experienced any chronic health conditions?",
                "When did you have any surgeries or major medical procedures?",
                "Do you have any recurring health patterns?",
                "How would you describe your overall energy level?",
                "Have you experienced any significant mental health challenges?"
            ],
            "education": [
                "When did you complete your highest level of education?",
                "What subjects were you naturally good at in school?",
                "Did you face any learning challenges?",
                "When did you make important educational decisions?",
                "What motivated your educational choices?"
            ],
            "spiritual_experiences": [
                "Have you had any significant spiritual experiences?",
                "When did you experience a major shift in beliefs or worldview?",
                "Do you practice any spiritual or religious traditions?",
                "Have you experienced any unexplainable coincidences or synchronicities?",
                "How would you describe your connection to spirituality?"
            ]
        }

    async def generate_next_question(self,
                                   birth_details: Dict[str, Any],
                                   previous_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate the next most relevant question based on birth details and previous answers.

        Args:
            birth_details: Dictionary containing birth date, time, location
            previous_answers: List of previous question-answer pairs

        Returns:
            Dictionary containing the next question and metadata
        """
        try:
            # Determine which category to focus on based on previous answers
            next_category = await self._determine_next_category(birth_details, previous_answers)

            # Generate a personalized question using OpenAI
            question = await self._generate_personalized_question(birth_details, previous_answers, next_category)

            return {
                "question": question["text"],
                "category": next_category,
                "type": question.get("type", "text"),
                "options": question.get("options", [])
            }
        except Exception as e:
            logger.error(f"Error generating next question: {str(e)}")

            # Fallback to a sample question if AI generation fails
            return self._get_fallback_question(previous_answers)

    async def _determine_next_category(self,
                                     birth_details: Dict[str, Any],
                                     previous_answers: List[Dict[str, Any]]) -> str:
        """
        Determine the most valuable question category for birth time rectification.

        Args:
            birth_details: Dictionary containing birth date, time, location
            previous_answers: List of previous question-answer pairs

        Returns:
            Category name string
        """
        # Count questions per category
        category_counts = {category: 0 for category in self.question_categories}

        for answer in previous_answers:
            if "category" in answer:
                category = answer["category"]
                if category in category_counts:
                    category_counts[category] += 1

        # If we have fewer than 3 answers, prioritize life events
        if len(previous_answers) < 3:
            return "life_events"

        # If we have 3+ life events, focus on physical and personality traits
        life_event_count = category_counts.get("life_events", 0)
        if life_event_count >= 3:
            # Check if we've asked about physical traits
            if category_counts.get("physical_traits", 0) < 2:
                return "physical_traits"
            # Check if we've asked about personality traits
            elif category_counts.get("personality_traits", 0) < 2:
                return "personality_traits"

        # Use OpenAI to determine the most valuable category
        try:
            # Create a prompt for category selection
            prompt = self._create_category_selection_prompt(birth_details, previous_answers)

            # Get response from OpenAI
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="questionnaire",
                max_tokens=50,
                temperature=0.7
            )

            # Extract category from response
            category_text = response["text"].strip().lower()

            # Map to closest category
            for category in self.question_categories:
                if category.replace("_", "") in category_text.replace(" ", ""):
                    return category

            # Default to least asked category if no match
            least_asked = min(category_counts.items(), key=lambda x: x[1])[0]
            return least_asked

        except Exception as e:
            logger.warning(f"Error determining next category: {str(e)}")

            # Fallback to least asked category
            least_asked = min(category_counts.items(), key=lambda x: x[1])[0]
            return least_asked

    async def _generate_personalized_question(self,
                                           birth_details: Dict[str, Any],
                                           previous_answers: List[Dict[str, Any]],
                                           category: str) -> Dict[str, Any]:
        """
        Generate a personalized question using OpenAI.

        Args:
            birth_details: Dictionary containing birth date, time, location
            previous_answers: List of previous question-answer pairs
            category: Question category to focus on

        Returns:
            Dictionary with question text and metadata
        """
        # Create a prompt for question generation
        prompt = self._create_question_generation_prompt(birth_details, previous_answers, category)

        # Get response from OpenAI
        response = await self.openai_service.generate_completion(
            prompt=prompt,
            task_type="questionnaire",
            max_tokens=200,
            temperature=0.8
        )

        # Try to parse the response as JSON
        try:
            # Check if the response contains a JSON object
            text = response["text"].strip()
            if text.startswith("{") and text.endswith("}"):
                question_data = json.loads(text)
                return question_data
            else:
                # If not JSON, use the text as the question
                return {"text": text, "type": "text"}
        except json.JSONDecodeError:
            # If JSON parsing fails, use the text as is
            return {"text": response["text"].strip(), "type": "text"}

    def _create_category_selection_prompt(self,
                                        birth_details: Dict[str, Any],
                                        previous_answers: List[Dict[str, Any]]) -> str:
        """Create a prompt for selecting the next question category"""

        # Format birth details
        birth_date = birth_details.get("birth_date", "Unknown")
        birth_time = birth_details.get("birth_time", "Unknown")

        # Format previous answers
        answers_text = ""
        for i, answer in enumerate(previous_answers):
            answers_text += f"Q{i+1}: {answer.get('question', 'Unknown')}\n"
            answers_text += f"A{i+1}: {answer.get('answer', 'Unknown')}\n\n"

        # Create the prompt
        prompt = f"""
        You are an expert astrologer specializing in birth time rectification.

        Birth Details:
        Date: {birth_date}
        Time: {birth_time}

        Previous Questions and Answers:
        {answers_text}

        Based on the information above, which category of question would provide the most valuable information for birth time rectification?

        Available categories:
        - Life Events (significant events with dates)
        - Physical Traits (appearance, body type)
        - Personality Traits (temperament, behavior)
        - Career (work history, talents)
        - Relationships (patterns, significant relationships)
        - Health (medical history, energy levels)
        - Education (learning patterns, educational timeline)
        - Spiritual Experiences (beliefs, significant experiences)

        Respond with just the category name.
        """

        return prompt

    def _create_question_generation_prompt(self,
                                         birth_details: Dict[str, Any],
                                         previous_answers: List[Dict[str, Any]],
                                         category: str) -> str:
        """Create a prompt for generating a personalized question"""

        # Format birth details
        birth_date = birth_details.get("birth_date", "Unknown")
        birth_time = birth_details.get("birth_time", "Unknown")

        # Format previous answers
        answers_text = ""
        for i, answer in enumerate(previous_answers):
            answers_text += f"Q{i+1}: {answer.get('question', 'Unknown')}\n"
            answers_text += f"A{i+1}: {answer.get('answer', 'Unknown')}\n\n"

        # Get category description
        category_desc = category.replace("_", " ").title()

        # Create the prompt
        prompt = f"""
        You are an expert astrologer specializing in birth time rectification.

        Birth Details:
        Date: {birth_date}
        Time: {birth_time}

        Previous Questions and Answers:
        {answers_text}

        Create a personalized question in the category of "{category_desc}" that would help with birth time rectification.
        The question should be specific, relevant to the person's life based on previous answers, and designed to elicit information that would help determine the exact birth time.

        For life events, ask about specific events with dates.
        For traits, ask about distinctive characteristics that correlate with astrological positions.

        Format your response as a JSON object with the following structure:
        {{
            "text": "Your question here?",
            "type": "text" or "multiple_choice" or "yes_no",
            "options": ["Option 1", "Option 2", etc.] (only for multiple_choice type)
        }}

        Make sure the question is not a repeat of previous questions and is tailored to this specific individual.
        """

        return prompt

    def _get_fallback_question(self, previous_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get a fallback question if AI generation fails"""

        # Determine which categories have been asked the least
        category_counts = {category: 0 for category in self.question_categories}

        for answer in previous_answers:
            if "category" in answer:
                category = answer["category"]
                if category in category_counts:
                    category_counts[category] += 1

        # Get the least asked category
        least_asked = min(category_counts.items(), key=lambda x: x[1])[0]

        # Get questions for this category
        category_questions = self.sample_questions.get(least_asked, [])

        # Find a question that hasn't been asked yet
        previous_questions = [a.get("question", "") for a in previous_answers]

        for question in category_questions:
            if question not in previous_questions:
                return {
                    "question": question,
                    "category": least_asked,
                    "type": "text",
                    "options": []
                }

        # If all questions have been asked, return a generic one
        return {
            "question": f"Please describe any significant events or experiences related to your {least_asked.replace('_', ' ')}.",
            "category": least_asked,
            "type": "text",
            "options": []
        }

# Singleton instance
_instance = None

def get_questionnaire_service(openai_service: Optional[Any] = None) -> Any:
    """Get or create the questionnaire service singleton"""
    global _instance
    if _instance is None:
        _instance = DynamicQuestionnaireService(openai_service)
    return _instance
