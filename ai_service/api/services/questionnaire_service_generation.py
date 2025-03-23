"""
Question generation module for the questionnaire service.

This module contains functions for generating questions for birth time rectification.
"""

import logging
import json
import uuid
import random
from typing import Dict, List, Any, Optional
from datetime import datetime

# logger initialization
logger = logging.getLogger(__name__)

from ai_service.api.services.openai.service import OpenAIService
from ai_service.api.services.questionnaire_service_types import Question, QuestionOption, QUESTION_TYPES

# Question template categories
QUESTION_TEMPLATES = {
    "early_life_events": [
        {
            "id": "early_life_1",
            "type": "open_text",
            "text": "Please describe any significant events from your early childhood that you can recall or that were told to you by family members.",
            "relevance": "high",
            "category": "early_life_events"
        },
        {
            "id": "early_life_2",
            "type": "yes_no",
            "text": "Were there any health issues or emergencies in your first few years of life?",
            "relevance": "high",
            "category": "early_life_events"
        }
    ],
    "personality_traits": [
        {
            "id": "personality_1",
            "type": "multiple_choice",
            "text": "Which of these traits best describes your personality?",
            "options": [
                {"id": "p1_1", "text": "Logical and analytical"},
                {"id": "p1_2", "text": "Emotional and intuitive"},
                {"id": "p1_3", "text": "Practical and detail-oriented"},
                {"id": "p1_4", "text": "Creative and imaginative"}
            ],
            "relevance": "medium",
            "category": "personality_traits"
        }
    ],
    "life_direction": [
        {
            "id": "direction_1",
            "type": "open_text",
            "text": "What major changes in life direction have you experienced, and at what ages did they occur?",
            "relevance": "high",
            "category": "life_direction"
        }
    ],
    "time_of_birth": [
        {
            "id": "birth_time_1",
            "type": "time_event",
            "text": "If you know your birth time approximately, please specify what time of day you were born.",
            "relevance": "high",
            "category": "time_of_birth"
        }
    ],
    "physical_characteristics": [
        {
            "id": "physical_1",
            "type": "multiple_choice",
            "text": "Which of these best describes your physical appearance?",
            "options": [
                {"id": "ph1_1", "text": "Tall and lean"},
                {"id": "ph1_2", "text": "Medium height with balanced features"},
                {"id": "ph1_3", "text": "Athletic build"},
                {"id": "ph1_4", "text": "Shorter with sturdy build"}
            ],
            "relevance": "medium",
            "category": "physical_characteristics"
        }
    ]
}

async def get_initial_questions(birth_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get initial questions for birth time rectification.

    Args:
        birth_details: Dictionary containing birth date, time, and location

    Returns:
        List of initial questions
    """
    # Generate template questions based on birth details
    template_questions = _generate_template_questions(birth_details)

    # Add unique IDs to each question if not already present
    for q in template_questions:
        if "id" not in q:
            q["id"] = f"q_{uuid.uuid4().hex[:8]}"

    return template_questions

def _generate_template_questions(birth_details: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate template questions based on birth details.

    Args:
        birth_details: Dictionary containing birth date, time, and location

    Returns:
        List of questions
    """
    # Get birth date components
    try:
        if isinstance(birth_details.get("birth_date"), str):
            birth_date_str = birth_details.get("birth_date", "")
            birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d").date() if birth_date_str else None
        else:
            birth_date = birth_details.get("birth_date")
    except (ValueError, TypeError):
        birth_date = None

    # Determine question set based on how much information we have
    has_time = birth_details.get("birth_time") is not None and birth_details.get("birth_time") != ""

    questions = []

    # Always include time of birth question if no time provided
    if not has_time:
        time_questions = QUESTION_TEMPLATES.get("time_of_birth", [])
        questions.extend(time_questions)

    # Add early life events questions
    early_life_questions = QUESTION_TEMPLATES.get("early_life_events", [])
    questions.extend(early_life_questions[:2])  # Limit to 2 questions

    # Add personality questions
    personality_questions = QUESTION_TEMPLATES.get("personality_traits", [])
    questions.extend(personality_questions[:1])  # Limit to 1 question

    # Add life direction questions
    direction_questions = QUESTION_TEMPLATES.get("life_direction", [])
    questions.extend(direction_questions[:1])  # Limit to 1 question

    # Add physical characteristics questions
    physical_questions = QUESTION_TEMPLATES.get("physical_characteristics", [])
    questions.extend(physical_questions[:1])  # Limit to 1 question

    # Make sure we have a limited, manageable set to start with
    return questions[:5]  # Return maximum 5 initial questions

async def generate_next_question(
    self,
    birth_details: Dict[str, Any],
    previous_answers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate the next question based on previous answers and birth details.

    Args:
        birth_details: Dictionary containing birth details
        previous_answers: List of previous answers

    Returns:
        Next question
    """
    try:
        # Check if we have enough questions for meaningful rectification
        if len(previous_answers) >= 10:
            return {
                "question": None,
                "complete": True,
                "message": "Enough information collected for birth time rectification"
            }

        # Generate an astrologically relevant question
        next_question = await self._generate_astrologically_relevant_question(
            birth_details,
            previous_answers
        )

        return {
            "question": next_question,
            "complete": False,
            "progress": {
                "current": len(previous_answers) + 1,
                "total_estimated": 10
            }
        }

    except Exception as e:
        logger.error(f"Error generating next question: {e}")

        # Fallback to a template question if AI generation fails
        fallback_categories = ["life_direction", "personality_traits", "early_life_events"]
        available_categories = [cat for cat in fallback_categories if cat in QUESTION_TEMPLATES]

        if available_categories:
            # Choose a random category and get a question
            category = random.choice(available_categories)
            template_questions = QUESTION_TEMPLATES.get(category, [])

            if template_questions:
                question = random.choice(template_questions).copy()
                # Add a unique ID
                question["id"] = f"q_{uuid.uuid4().hex[:8]}"

                return {
                    "question": question,
                    "complete": False,
                    "progress": {
                        "current": len(previous_answers) + 1,
                        "total_estimated": 10
                    }
                }

        # If all else fails, return a generic question
        generic_question = {
            "id": f"q_{uuid.uuid4().hex[:8]}",
            "type": "open_text",
            "text": "Please describe any significant life events that might be connected to your astrological chart.",
            "category": "general",
            "relevance": "medium"
        }

        return {
            "question": generic_question,
            "complete": False,
            "progress": {
                "current": len(previous_answers) + 1,
                "total_estimated": 10
            }
        }

async def _generate_astrologically_relevant_question(
    self,
    birth_details: Dict[str, Any],
    previous_answers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate an astrologically relevant question based on birth details and previous answers.

    Args:
        birth_details: Dictionary containing birth details
        previous_answers: List of previous answers

    Returns:
        Astrologically relevant question
    """
    # Try to get OpenAI service first
    openai_service = self.openai_service
    if not openai_service:
        from ai_service.api.services.openai import get_openai_service
        openai_service = get_openai_service()

    if not openai_service:
        # Fallback to template if no OpenAI service available
        logger.warning("OpenAI service not available for astrological question generation")
        return self._generate_fallback_question(previous_answers)

    # Extract key information from birth details
    birth_date = birth_details.get("birth_date", "")
    birth_time = birth_details.get("birth_time", "Unknown")
    latitude = birth_details.get("latitude", 0)
    longitude = birth_details.get("longitude", 0)

    # Prepare previous questions and answers for context
    qa_context = ""
    if previous_answers:
        qa_list = []
        for idx, ans in enumerate(previous_answers):
            q_text = ans.get("question", "")
            a_text = str(ans.get("answer", ""))
            qa_list.append(f"Q{idx+1}: {q_text}\nA{idx+1}: {a_text}")

        qa_context = "\n\n".join(qa_list)

    # Create system message with astrological knowledge
    system_message = """
    You are an expert Vedic astrologer specialized in birth time rectification.
    Your task is to generate the next astrologically relevant question that will
    help determine a person's accurate birth time based on their life events,
    personality traits, and physical characteristics.

    Based on the birth details and previous answers, create a targeted question that would
    provide information useful for birth time rectification. Focus on aspects
    that might be influenced by:
    1. Ascendant sign (physical appearance, personal traits)
    2. Moon position (emotional patterns)
    3. House cusps (life areas and timing of events)
    4. Planetary positions in houses (specific talents and challenges)

    The question should be directly useful for birth time rectification.
    """

    # Create user message with context
    user_message = f"""
    BIRTH DETAILS:
    Date: {birth_date}
    Time: {birth_time}
    Coordinates: {latitude}, {longitude}

    PREVIOUS QUESTIONS AND ANSWERS:
    {qa_context if qa_context else "No previous questions yet."}

    Based on this information, generate the NEXT single most useful question for birth time rectification.
    Return your response as a JSON object with the following structure:
    {{
      "id": "unique_question_id",
      "type": "question_type", (one of: yes_no, multiple_choice, open_text, time_event, date_event, slider)
      "text": "question_text",
      "category": "question_category",
      "relevance": "high/medium/low",
      "options": [
        {{"id": "option_id", "text": "option_text"}} (include only for multiple_choice questions)
      ]
    }}
    """

    try:
        # Call OpenAI API
        response = await openai_service.generate_completion(
            prompt={
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ]
            },
            task_type="question_generation",
            max_tokens=500,
            temperature=0.7
        )

        # Extract and parse the response
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        result = json.loads(content)

        # Validate the required fields
        if not all(key in result for key in ["id", "type", "text"]):
            logger.warning("OpenAI response missing required fields for question")
            return self._generate_fallback_question(previous_answers)

        # Validate question type
        if result.get("type") not in QUESTION_TYPES:
            result["type"] = "open_text"  # Default to open text if invalid type

        # Ensure options are present for multiple choice
        if result.get("type") == "multiple_choice" and not result.get("options"):
            result["options"] = [
                {"id": f"opt_{uuid.uuid4().hex[:8]}", "text": "Yes, significantly"},
                {"id": f"opt_{uuid.uuid4().hex[:8]}", "text": "Somewhat"},
                {"id": f"opt_{uuid.uuid4().hex[:8]}", "text": "No, not at all"}
            ]

        return result

    except Exception as e:
        logger.error(f"Error generating question with OpenAI: {e}")
        return self._generate_fallback_question(previous_answers)

def _generate_fallback_question(self, previous_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a fallback question when AI generation fails.

    Args:
        previous_answers: List of previous answers

    Returns:
        Fallback question
    """
    # Track which categories we've already used
    used_categories = set()
    for ans in previous_answers:
        question = ans.get("question", {})
        if isinstance(question, dict):
            category = question.get("category", "")
            if category:
                used_categories.add(category)

    # Find unused categories
    all_categories = set(QUESTION_TEMPLATES.keys())
    unused_categories = all_categories - used_categories

    if unused_categories:
        # Use an unused category
        category = random.choice(list(unused_categories))
    else:
        # All categories used, pick a random one
        category = random.choice(list(all_categories))

    # Get questions from this category
    category_questions = QUESTION_TEMPLATES.get(category, [])

    if category_questions:
        # Pick a random question from the category
        question = random.choice(category_questions).copy()
        # Add a unique ID
        question["id"] = f"q_{uuid.uuid4().hex[:8]}"
        return question

    # If all else fails, return a generic question
    return {
        "id": f"q_{uuid.uuid4().hex[:8]}",
        "type": "open_text",
        "text": "Please describe any significant life events that might be connected to your astrological chart.",
        "category": "general",
        "relevance": "medium"
    }
