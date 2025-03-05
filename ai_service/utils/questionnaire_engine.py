"""
Questionnaire engine for Birth Time Rectifier API.
Handles generation and processing of questions for birth time rectification.
"""

import logging
import uuid
from typing import Dict, List, Any
import random

# Configure logging
logger = logging.getLogger(__name__)

class QuestionnaireEngine:
    """
    Engine for generating and processing questionnaire questions for birth time rectification.
    """

    def __init__(self):
        """Initialize the questionnaire engine"""
        # Set maximum number of questions
        self.max_questions = 10

        # Define question templates by category
        self.question_templates = {
            "personality": [
                {
                    "text": "Does your personality align with your sun sign traits?",
                    "type": "yes_no",
                    "relevance": "high"
                },
                {
                    "text": "Do you consider yourself more introverted than extroverted?",
                    "type": "yes_no",
                    "relevance": "medium"
                },
                {
                    "text": "Which of these personality traits best describes you?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "analytical", "text": "Analytical and logical"},
                        {"id": "creative", "text": "Creative and intuitive"},
                        {"id": "practical", "text": "Practical and grounded"},
                        {"id": "emotional", "text": "Emotional and sensitive"}
                    ],
                    "relevance": "high"
                }
            ],
            "life_events": [
                {
                    "text": "Which area of your life has seen the most significant changes in the past year?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "career", "text": "Career/Work"},
                        {"id": "relationships", "text": "Relationships"},
                        {"id": "health", "text": "Health/Wellbeing"},
                        {"id": "home", "text": "Home/Living situation"},
                        {"id": "none", "text": "No significant changes"}
                    ],
                    "relevance": "medium"
                },
                {
                    "text": "Have you experienced major life transitions at times when Saturn formed aspects to your natal planets?",
                    "type": "yes_no",
                    "relevance": "high"
                }
            ],
            "career": [
                {
                    "text": "Which of these career areas have you felt most drawn to?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "creative", "text": "Creative/Artistic"},
                        {"id": "analytical", "text": "Analytical/Scientific"},
                        {"id": "social", "text": "Social/Humanitarian"},
                        {"id": "business", "text": "Business/Leadership"}
                    ],
                    "relevance": "high"
                },
                {
                    "text": "Have your career changes aligned with Jupiter transits?",
                    "type": "yes_no",
                    "relevance": "medium"
                }
            ],
            "relationships": [
                {
                    "text": "Do you tend to be attracted to people with strong placements in your 7th house?",
                    "type": "yes_no",
                    "relevance": "high"
                },
                {
                    "text": "Which planet's energy do you feel most strongly in your relationships?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "venus", "text": "Venus (harmony, beauty)"},
                        {"id": "mars", "text": "Mars (passion, conflict)"},
                        {"id": "jupiter", "text": "Jupiter (growth, optimism)"},
                        {"id": "saturn", "text": "Saturn (commitment, restriction)"}
                    ],
                    "relevance": "medium"
                }
            ]
        }

    def get_first_question(self, chart_data: Dict[str, Any], birth_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the first question for a new questionnaire session.

        Args:
            chart_data: The natal chart data
            birth_details: Birth details provided by the user

        Returns:
            Dictionary containing the first question
        """
        # In a real implementation, we would analyze the chart to determine
        # the most relevant first question. For now, we'll use a standard first question.

        # Use a personality question as the first question
        template = self.question_templates["personality"][0]

        # Create a unique ID for this question
        question_id = f"q_{uuid.uuid4()}"

        # Format options if multiple choice
        options = None
        if template.get("type") == "multiple_choice" and "options" in template:
            options = template["options"]
        elif template.get("type") == "yes_no":
            options = [
                {"id": "yes", "text": "Yes, definitely"},
                {"id": "somewhat", "text": "Somewhat"},
                {"id": "no", "text": "No, not at all"}
            ]

        # Create question
        question = {
            "id": question_id,
            "type": template.get("type", "yes_no"),
            "text": template["text"],
            "options": options,
            "relevance": template.get("relevance", "medium")
        }

        return question

    def get_next_question(self, chart_data: Dict[str, Any], birth_details: Dict[str, Any],
                         previous_answers: Dict[str, Any], current_confidence: float) -> Dict[str, Any]:
        """
        Generate the next question based on previous answers and chart data.

        Args:
            chart_data: The natal chart data
            birth_details: Birth details provided by the user
            previous_answers: Dictionary of answers to previous questions
            current_confidence: Current confidence level (0-100)

        Returns:
            Dictionary containing the next question
        """
        # In a real implementation, we would analyze previous answers and the chart
        # to determine the most relevant next question.

        # Choose a category based on what hasn't been asked yet
        all_categories = list(self.question_templates.keys())

        # Filter out categories we've already asked about
        used_categories = set()
        for q_id, answer in previous_answers.items():
            # In a real implementation, we would store the category with each question
            # For now, we just rotate through categories
            if len(used_categories) < len(all_categories):
                used_categories.add(all_categories[len(used_categories)])

        available_categories = [c for c in all_categories if c not in used_categories]

        # If all categories used, pick a random one
        if not available_categories:
            available_categories = all_categories

        category = random.choice(available_categories)

        # Choose a random question from that category
        template = random.choice(self.question_templates[category])

        # Create a unique ID for this question
        question_id = f"q_{uuid.uuid4()}"

        # Format options if multiple choice
        options = None
        if template.get("type") == "multiple_choice" and "options" in template:
            options = template["options"]
        elif template.get("type") == "yes_no":
            options = [
                {"id": "yes", "text": "Yes, definitely"},
                {"id": "somewhat", "text": "Somewhat"},
                {"id": "no", "text": "No, not at all"}
            ]

        # Create question
        question = {
            "id": question_id,
            "type": template.get("type", "yes_no"),
            "text": template["text"],
            "options": options,
            "relevance": template.get("relevance", "medium")
        }

        return question

    def calculate_confidence(self, answers: Dict[str, Any]) -> float:
        """
        Calculate the confidence level based on answers provided.

        Args:
            answers: Dictionary of answers to previous questions

        Returns:
            Confidence level (0-100)
        """
        # In a real implementation, we would use a sophisticated algorithm
        # to calculate confidence based on answer quality, consistency, etc.

        # For now, we'll use a simple formula based on number of questions answered
        base_confidence = 30  # Start with some base confidence
        question_value = 10   # Each question contributes this much
        max_confidence = 95   # Cap at this level

        confidence = min(base_confidence + (len(answers) * question_value), max_confidence)

        return confidence

    def analyze_answers(self, chart_data: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze answers to determine birth time adjustment.

        Args:
            chart_data: Original chart data
            answers: Dictionary of answers to questions

        Returns:
            Analysis results including suggested birth time adjustment
        """
        # In a real implementation, this would use sophisticated analysis
        # based on the answers and chart data.

        # For now, return a simple mock result
        return {
            "confidence": self.calculate_confidence(answers),
            "suggested_adjustment_minutes": random.randint(-30, 30),
            "reliability": "moderate",
            "suggested_houses_to_review": [1, 10, 7],  # Ascendant, MC, Descendant
            "critical_time_markers": ["Mars-Saturn aspects", "Moon house placement"]
        }
