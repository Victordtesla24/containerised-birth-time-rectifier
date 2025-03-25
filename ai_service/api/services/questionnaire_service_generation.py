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
from types import SimpleNamespace

# logger initialization
logger = logging.getLogger(__name__)

from ai_service.api.services.openai.service import OpenAIService
from ai_service.api.services.questionnaire_service_types import Question, QuestionOption, QUESTION_TYPES
from ai_service.api.services.questionnaire_service_chart_calculator import chart_calculator

def _format_chart_data_for_prompt(chart_data: Dict[str, Any]) -> str:
    """
    Format chart data for inclusion in an AI prompt.

    Args:
        chart_data: Dictionary with chart data

    Returns:
        Formatted string with chart data
    """
    if not chart_data:
        return "No chart data available."

    formatted_text = []

    # Add ascendant information
    ascendant = chart_data.get("ascendant", {})
    if ascendant:
        asc_sign = ascendant.get("sign", "Unknown")
        asc_degree = ascendant.get("degree", 0)
        formatted_text.append(f"Ascendant: {asc_sign} {asc_degree}°")

    # Add planet information
    planets = chart_data.get("planets", {})
    if planets:
        formatted_text.append("\nPlanets:")
        for planet, data in planets.items():
            sign = data.get("sign", "Unknown")
            degree = data.get("degree", 0)
            formatted_text.append(f"- {planet}: {sign} {degree}°")

    # Add house information
    houses = chart_data.get("houses", [])
    if houses:
        formatted_text.append("\nHouses:")
        for i, house in enumerate(houses, 1):
            sign = house.get("sign", "Unknown")
            formatted_text.append(f"- House {i}: {sign}")

    return "\n".join(formatted_text)



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

    Raises:
        ValueError: When an error occurs during question generation or OpenAI service is unavailable
    """
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

async def _generate_astrologically_relevant_question(
    self,
    birth_details: Dict[str, Any],
    previous_questions: Optional[List[Dict[str, Any]]] = None,
    previous_answers: Optional[List[Dict[str, Any]]] = None,
    question_index: int = 0
) -> Dict[str, Any]:
    """
    Generate an astrologically relevant question based on the user's birth chart.

    Args:
        birth_details: Dictionary with birth details
        previous_questions: Previously asked questions
        previous_answers: Previous answers provided by the user
        question_index: Current question index

    Returns:
        Dictionary with question data

    Raises:
        ValueError: When OpenAI service is not available or generation fails
    """
    # Ensure OpenAI service is available
    openai_service = self.openai_service
    if not openai_service:
        from ai_service.api.services.openai import get_openai_service
        openai_service = get_openai_service()

    if not openai_service:
        error_msg = "OpenAI service is required for astrological question generation but is not available"
        logger.error(error_msg)
        raise ValueError(error_msg)


    try:
        # Format previous Q&A for the prompt
        previous_qa = ""
        if previous_questions and previous_answers:
            for i, (q, a) in enumerate(zip(previous_questions, previous_answers)):
                q_text = q.get("text", "")
                a_text = a.get("answer", "")
                previous_qa += f"Q{i+1}: {q_text}\nA{i+1}: {a_text}\n\n"

        # Try to calculate birth chart data for more targeted questions
        try:
            # Extract the necessary data from birth_details dictionary
            birth_datetime = datetime.fromisoformat(birth_details.get('birth_date', '') + 'T' + birth_details.get('birth_time', '00:00:00'))
            geo_pos = SimpleNamespace(
                lat=float(birth_details.get('latitude', 0)),
                lon=float(birth_details.get('longitude', 0))
            )
            chart_data = chart_calculator.create_chart(birth_datetime, geo_pos)
            chart_prompt = _format_chart_data_for_prompt(chart_data)
        except Exception as e:
            logger.error(f"Failed to calculate chart data for question generation: {e}")
            chart_prompt = "Chart data is currently unavailable."

        # Create prompt for OpenAI
        system_prompt = """
        You are an expert Vedic astrologer specializing in birth time rectification.

        Generate ONE question that will help determine a person's accurate birth time.
        Focus on life events, physical characteristics, or personality traits that are
        strongly influenced by birth time (primarily ascendant/lagna and Moon position).

        Format your response as a structured JSON object with these fields:
        - id: A unique identifier for the question
        - text: The actual question text
        - type: The question type (multiple_choice, yes_no, date, time, or text)
        - options: For multiple_choice questions, an array of option objects with id and text fields
        - relevance: Brief explanation of how this helps determine birth time
        - astrological_significance: Which chart factors this question helps determine
        """

        user_prompt = f"""
        BIRTH DETAILS:
        Date: {birth_details.get('birth_date', '')}
        Approximate Time: {birth_details.get('birth_time', '')}
        Location: {birth_details.get('birth_place', '')} (Lat: {birth_details.get('latitude', '')}, Lon: {birth_details.get('longitude', '')})

        BIRTH CHART DATA:
        {chart_prompt}

        PREVIOUS QUESTIONS AND ANSWERS:
        {previous_qa}

        QUESTION INDEX: {question_index + 1}

        Generate ONE question that would be most helpful for rectifying this person's birth time.
        Focus on distinct life events or characteristics that change with different birth times.
        If this is question #{question_index + 1}, it should be more specific than earlier questions.
        """

        # Call OpenAI service
        response = await openai_service.generate_completion(
            prompt={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            },
            task_type="questionnaire",
            max_tokens=1000,
            temperature=0.4
        )

        # Extract JSON content
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")

        try:
            # Parse the content as JSON
            question_data = self._extract_json_from_content(content)

            # Ensure the question has the required fields
            if not question_data or not isinstance(question_data, dict):
                error_msg = "Failed to generate a valid question"
                logger.error(error_msg)
                raise ValueError(error_msg)

            if "text" not in question_data:
                error_msg = "Generated question is missing text field"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Assign a unique ID if not present
            if "id" not in question_data:
                question_data["id"] = f"q_{str(uuid.uuid4())[:8]}"

            # Assign a type if not present
            if "type" not in question_data:
                question_data["type"] = "text"

            return question_data

        except Exception as e:
            error_msg = f"Failed to parse question data from OpenAI response: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    except Exception as e:
        error_msg = f"Failed to generate astrologically relevant question: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def _extract_json_from_content(self, content: str) -> Dict[str, Any]:
    """
    Extract JSON data from a string that might contain additional text.

    Args:
        content: String that may contain JSON

    Returns:
        Extracted JSON data as a dictionary

    Raises:
        ValueError: If JSON cannot be extracted or parsed
    """
    if not content or not isinstance(content, str):
        raise ValueError("Invalid content provided for JSON extraction")

    # Try direct JSON parsing first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON using regex patterns
    import re

    # Try to find JSON between triple backticks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find anything that looks like a JSON object
    json_match = re.search(r'(\{[\s\S]*\})', content)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Final attempt - try to clean up the content
    cleaned = re.sub(r'[^\{\}\[\]"\':\d,\.\w\s_-]', '', content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError(f"Failed to extract valid JSON from content: {content[:100]}...")



async def generate_questionnaire(
    user_id: str,
    rectification_type: str,
    client_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Generate a complete questionnaire for birth time rectification.

    Args:
        user_id: User ID to generate questionnaire for
        rectification_type: Type of rectification
        client_data: Optional client data for personalization

    Returns:
        List of question dictionaries
    """
    try:
        # Log the request
        logger.info(f"Generating questionnaire for user {user_id}, type: {rectification_type}")

        # Define standard questions based on rectification type
        questions = []

        # Add universal questions that apply to all rectification types
        questions.append({
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
        })

        questions.append({
            "id": f"q_life_{uuid.uuid4().hex[:8]}",
            "text": "What significant life events have occurred that had a major impact on your life path?",
            "type": "text",
            "category": "life_events"
        })

        # Add specialized questions based on rectification type
        if rectification_type == "precise":
            questions.append({
                "id": f"q_precise_{uuid.uuid4().hex[:8]}",
                "text": "Can you list 3-5 major life events with their exact dates (marriage, career change, etc.)?",
                "type": "text",
                "category": "life_events"
            })

            questions.append({
                "id": f"q_health_{uuid.uuid4().hex[:8]}",
                "text": "Have you experienced any significant health events? If so, please provide dates.",
                "type": "text",
                "category": "health"
            })

        elif rectification_type == "general":
            questions.append({
                "id": f"q_general_{uuid.uuid4().hex[:8]}",
                "text": "In which period of your life did you experience the most significant changes?",
                "type": "multiple_choice",
                "options": [
                    {"value": "childhood", "text": "Childhood (0-12 years)"},
                    {"value": "teens", "text": "Teenage years (13-19)"},
                    {"value": "early_adulthood", "text": "Early adulthood (20-29)"},
                    {"value": "adulthood", "text": "Adulthood (30-45)"},
                    {"value": "mid_life", "text": "Mid-life (46-60)"},
                    {"value": "senior", "text": "Senior years (61+)"}
                ],
                "category": "life_phases"
            })

        # Personalize questions if client data is available
        if client_data:
            birth_details = client_data.get("birth_details", {})
            if birth_details and "date" in birth_details:
                birth_year = int(birth_details["date"].split("-")[0])
                current_year = datetime.now().year
                age = current_year - birth_year

                # Add age-specific questions
                if age > 30:
                    questions.append({
                        "id": f"q_age30_{uuid.uuid4().hex[:8]}",
                        "text": "What major life changes occurred around your 30th birthday?",
                        "type": "text",
                        "category": "life_events"
                    })

                if age > 40:
                    questions.append({
                        "id": f"q_age40_{uuid.uuid4().hex[:8]}",
                        "text": "What significant transitions or events occurred in your late 30s or early 40s?",
                        "type": "text",
                        "category": "life_events"
                    })

        return questions

    except Exception as e:
        logger.error(f"Error generating questionnaire: {e}")
        # Return empty list instead of None to match return type
        return []
