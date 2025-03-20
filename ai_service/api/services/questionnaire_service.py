"""
Questionnaire service for Birth Time Rectifier API.

This service handles the generation and processing of questions for birth time rectification.
"""

import logging
import asyncio
import json
import uuid
import random
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple, Union, TypedDict
import re

from ai_service.api.services.openai import get_openai_service
from ai_service.api.services.openai.service import OpenAIService
from ai_service.api.services.session_service import get_session_store
from ai_service.core.config import settings

logger = logging.getLogger(__name__)

# Define question types
QUESTION_TYPES = [
    "yes_no",
    "multiple_choice",
    "open_text",
    "time_event",
    "date_event",
    "slider"
]

# Define question templates by category
QUESTION_TEMPLATES = {
    "childhood": [
        "Do you remember any significant events from when you were {age} years old?",
        "Were there any major changes in your family when you were around {age}?",
        "Did you experience any health issues or accidents as a child?",
        "At what age did you first attend school?",
        "Did you move homes during your childhood? If so, at what age?"
    ],
    "personality": [
        "Would you describe yourself as more introverted or extroverted?",
        "Do you tend to be more logical or intuitive in your decision making?",
        "How would you describe your temperament as a child?",
        "Are you naturally more organized or spontaneous?",
        "Do you prefer working in groups or independently?"
    ],
    "life_events": [
        "Have you experienced a significant career change? When did this occur?",
        "Have you relocated to a different city or country? When?",
        "When did you experience your first significant relationship?",
        "Have you had any major health challenges? When did they occur?",
        "What was the most significant achievement in your life and when did it happen?"
    ],
    "specifics": [
        "Were you born during the day or at night, according to family accounts?",
        "Did your birth have any unusual circumstances or complications?",
        "Was your birth early, late, or on the expected due date?",
        "Do you know if there were any notable weather conditions on your birth day?",
        "Has anyone in your family mentioned specific details about the timing of your birth?"
    ]
}

# Define types for questionnaire structures
class QuestionOption(TypedDict):
    id: str
    text: str

class Question(TypedDict, total=False):
    id: str
    type: str
    text: str
    category: str
    relevance: str
    options: Optional[List[QuestionOption]]

# Create a custom JSON encoder to handle date and datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

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

        # No automatic fetching of OpenAI service - must be provided by caller
        # This ensures tests can explicitly create instances without OpenAI service

        # If openai_service is None, operations that require it will raise an error
        # when they are called, as required by the tests

        self.session_store = get_session_store()

    async def get_initial_questions(self, birth_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate initial questions based on birth details.

        Args:
            birth_details: Dictionary with birth date, time, location

        Returns:
            List of question dictionaries
        """
        logger.info("Generating initial questions based on birth details")

        # Extract birth data
        birth_date = birth_details.get("birthDate") or birth_details.get("birth_date", "")
        birth_time = birth_details.get("birthTime") or birth_details.get("birth_time", "")
        birth_place = birth_details.get("birthPlace") or birth_details.get("birth_place", "")
        latitude = birth_details.get("latitude", 0.0)
        longitude = birth_details.get("longitude", 0.0)
        timezone = birth_details.get("timezone", "UTC")

        # Create comprehensive prompt for OpenAI
        initial_questions_request = {
            "task": "generate_astrological_initial_questions",
            "birth_details": {
                "date": birth_date,
                "time": birth_time,
                "place": birth_place,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone
            },
            "requirements": [
                "Generate 5-7 astrologically relevant questions for birth time rectification",
                "Include questions about personality traits (for Ascendant determination)",
                "Include questions about early childhood and home life (for IC/4th house determination)",
                "Include questions about career and public life (for MC/10th house determination)",
                "Include questions about relationships (for Descendant/7th house determination)",
                "Include at least one direct question about known birth time information",
                "Ensure questions are astrologically meaningful and help determine the correct birth time",
                "Format as a proper JSON array with all required properties"
            ],
            "question_structure": {
                "id": "Unique identifier (will be generated automatically)",
                "type": "Question type (open_text, multiple_choice, yes_no, slider, time_event, date_event)",
                "text": "The actual question text",
                "category": "Astrological category (ascendant, midheaven, ic, descendant, life_events, etc.)",
                "relevance": "How this question helps with birth time rectification",
                "options": "For multiple_choice or yes_no questions, include possible answers"
            }
        }

        # Get initial questions from OpenAI
        if not self.openai_service:
            raise ValueError("OpenAI service is required for generating initial questions")

        response = await self.openai_service.generate_completion(
            prompt=json.dumps(initial_questions_request),
            task_type="generate_questionnaire",
            max_tokens=1500
        )

        if not response or "content" not in response:
            raise ValueError("Failed to generate initial questions from OpenAI")

        try:
            # Parse the OpenAI response
            questions_data = json.loads(response["content"])

            # Ensure we have a valid list of questions
            if not isinstance(questions_data, list) or len(questions_data) == 0:
                raise ValueError("OpenAI response did not contain a valid list of questions")

            # Process and enhance the questions
            for i, question in enumerate(questions_data):
                # Add unique IDs to questions if missing
                if "id" not in question:
                    question["id"] = f"q_{uuid.uuid4().hex[:8]}"

                # Ensure question has a type
                if "type" not in question:
                    question["type"] = "open_text"

                # Process options for multiple choice questions
                if "options" in question and question["options"]:
                    processed_options = []
                    for j, option in enumerate(question["options"]):
                        if isinstance(option, str):
                            processed_options.append({
                                "id": f"opt_{i}_{j}_{uuid.uuid4().hex[:4]}",
                                "text": option
                            })
                        elif isinstance(option, dict) and "text" in option:
                            if "id" not in option:
                                option["id"] = f"opt_{i}_{j}_{uuid.uuid4().hex[:4]}"
                            processed_options.append(option)
                    question["options"] = processed_options

            return questions_data

        except json.JSONDecodeError as e:
            # Handle the case where the response isn't proper JSON
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")

            # Try to extract questions from the text response
            content = response["content"]
            questions_data = []

            # Extract questions using regex pattern matching
            question_matches = re.findall(r'[0-9]+\.\s+(.*?)(?=(?:[0-9]+\.)|$)', content, re.DOTALL)
            if question_matches:
                for i, match in enumerate(question_matches):
                    question_text = match.strip()
                    if question_text:
                        question_data = {
                            "id": f"q_{uuid.uuid4().hex[:8]}",
                            "type": "open_text",
                            "text": question_text,
                            "category": "general",
                            "relevance": "Helps with birth time rectification"
                        }
                        questions_data.append(question_data)

            if not questions_data:
                raise ValueError("Failed to generate initial questions from OpenAI response")

            return questions_data

    def _generate_template_questions(self, birth_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate questions using templates.

        Args:
            birth_details: Dictionary with birth date, time, location

        Returns:
            List of question dictionaries
        """
        questions = []

        # Get basic birth year to calculate ages
        birth_year = 2000
        birth_date = birth_details.get("birthDate") or birth_details.get("birth_date", "")
        if birth_date and "-" in birth_date:
            try:
                birth_year = int(birth_date.split("-")[0])
            except (ValueError, IndexError):
                pass

        current_year = datetime.now().year
        max_age = current_year - birth_year

        # Generate questions from each category
        categories = list(QUESTION_TEMPLATES.keys())
        for category in categories:
            templates = QUESTION_TEMPLATES[category]
            selected_template = random.choice(templates)

            # Format template with random age if needed
            if "{age}" in selected_template:
                random_age = random.randint(5, min(max_age - 5, 25))
                formatted_question = selected_template.format(age=random_age)
            else:
                formatted_question = selected_template

            question_type = "open_text"
            options = []

            # Determine question type based on category and content
            if "yes_no" in formatted_question.lower() or "would you" in formatted_question.lower():
                question_type = "yes_no"
                options = [
                    {"id": f"opt_yes_{uuid.uuid4().hex[:4]}", "text": "Yes"},
                    {"id": f"opt_no_{uuid.uuid4().hex[:4]}", "text": "No"}
                ]
            elif "which" in formatted_question.lower() or category == "personality":
                question_type = "multiple_choice"
                if "introverted or extroverted" in formatted_question:
                    options = [
                        {"id": f"opt_intro_{uuid.uuid4().hex[:4]}", "text": "Introverted"},
                        {"id": f"opt_extro_{uuid.uuid4().hex[:4]}", "text": "Extroverted"},
                        {"id": f"opt_both_{uuid.uuid4().hex[:4]}", "text": "Balanced/Both"}
                    ]
                elif "logical or intuitive" in formatted_question:
                    options = [
                        {"id": f"opt_logical_{uuid.uuid4().hex[:4]}", "text": "Logical"},
                        {"id": f"opt_intuitive_{uuid.uuid4().hex[:4]}", "text": "Intuitive"},
                        {"id": f"opt_both_{uuid.uuid4().hex[:4]}", "text": "Balanced/Both"}
                    ]
                elif "organized or spontaneous" in formatted_question:
                    options = [
                        {"id": f"opt_org_{uuid.uuid4().hex[:4]}", "text": "Organized"},
                        {"id": f"opt_spont_{uuid.uuid4().hex[:4]}", "text": "Spontaneous"},
                        {"id": f"opt_both_{uuid.uuid4().hex[:4]}", "text": "Balanced/Both"}
                    ]
                elif "groups or independently" in formatted_question:
                    options = [
                        {"id": f"opt_groups_{uuid.uuid4().hex[:4]}", "text": "Groups"},
                        {"id": f"opt_indep_{uuid.uuid4().hex[:4]}", "text": "Independently"},
                        {"id": f"opt_depends_{uuid.uuid4().hex[:4]}", "text": "Depends on situation"}
                    ]
                elif "day or at night" in formatted_question:
                    options = [
                        {"id": f"opt_day_{uuid.uuid4().hex[:4]}", "text": "Day"},
                        {"id": f"opt_night_{uuid.uuid4().hex[:4]}", "text": "Night"},
                        {"id": f"opt_unknown_{uuid.uuid4().hex[:4]}", "text": "Unknown"}
                    ]
                elif "early, late, or on" in formatted_question:
                    options = [
                        {"id": f"opt_early_{uuid.uuid4().hex[:4]}", "text": "Early"},
                        {"id": f"opt_late_{uuid.uuid4().hex[:4]}", "text": "Late"},
                        {"id": f"opt_on_time_{uuid.uuid4().hex[:4]}", "text": "On time"},
                        {"id": f"opt_unknown_{uuid.uuid4().hex[:4]}", "text": "Unknown"}
                    ]
            elif "when" in formatted_question.lower() and "?" in formatted_question:
                question_type = "date_event"

            questions.append({
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "type": question_type,
                "text": formatted_question,
                "category": category,
                "options": options if options else None,
                "relevance": "high" if category in ["specifics", "life_events"] else "medium"
            })

        # Add specific questions for birth time rectification
        birth_time_questions = [
            {
                "id": f"q_birth_{uuid.uuid4().hex[:8]}",
                "type": "multiple_choice",
                "text": "How confident are you about your recorded birth time?",
                "category": "specifics",
                "options": [
                    {"id": f"opt_certain_{uuid.uuid4().hex[:4]}", "text": "Very certain (official record)"},
                    {"id": f"opt_confident_{uuid.uuid4().hex[:4]}", "text": "Fairly confident (family recollection)"},
                    {"id": f"opt_unsure_{uuid.uuid4().hex[:4]}", "text": "Somewhat unsure (heard different times)"},
                    {"id": f"opt_guess_{uuid.uuid4().hex[:4]}", "text": "Just a rough estimate"}
                ],
                "relevance": "high"
            },
            {
                "id": f"q_time_{uuid.uuid4().hex[:8]}",
                "type": "time_event",
                "text": "If you had to estimate your likely birth time, what time would you guess?",
                "category": "specifics",
                "relevance": "high"
            }
        ]

        questions.extend(birth_time_questions)

        # Randomize the order
        random.shuffle(questions)

        return questions[:5]  # Limit to 5 questions initially

    async def generate_next_question(
        self,
        birth_details: Dict[str, Any],
        previous_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate the next most relevant question based on birth details and previous answers.
        This implementation uses OpenAI to generate astrologically significant questions
        for birth time rectification without fallbacks.

        Args:
            birth_details: Dictionary containing birth date, time, location
            previous_answers: List of previous question-answer pairs

        Returns:
            Dictionary containing the next question and metadata

        Raises:
            ValueError: If OpenAI service is not available or fails
        """
        logger.info(f"Generating next question after {len(previous_answers)} previous answers")

        if not self.openai_service:
            raise ValueError("OpenAI service is required for generating astrologically relevant questions")

        # Extract key astrological factors from birth details to provide context
        birth_date = birth_details.get("birthDate", birth_details.get("birth_date", ""))
        birth_time = birth_details.get("birthTime", birth_details.get("birth_time", ""))
        latitude = birth_details.get("latitude", 0.0)
        longitude = birth_details.get("longitude", 0.0)
        timezone = birth_details.get("timezone", "UTC")
        location_name = birth_details.get("location", "")

        # Extract planetary positions if available
        chart_data = birth_details.get("chart_data", {})
        planetary_positions = []
        if chart_data:
            planets = chart_data.get("planets", [])
            if isinstance(planets, list):
                planetary_positions = planets
            elif isinstance(planets, dict):
                for planet_name, planet_data in planets.items():
                    if isinstance(planet_data, dict):
                        planetary_positions.append({
                            "name": planet_name,
                            "sign": planet_data.get("sign", ""),
                            "house": planet_data.get("house", 0),
                            "degree": planet_data.get("degree", 0)
                        })

        # Create enhanced context for better question generation
        astrological_context = {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "location": location_name,
            "current_question_number": len(previous_answers) + 1,
            "birth_time_rectification_focus": True,
            "planetary_positions": planetary_positions,
            "ascendant": chart_data.get("ascendant", {}),
            "question_purpose": "Gathering detailed information to accurately rectify birth time"
        }

        # Analyze previous answers to determine what information we already have
        categories_asked = set()
        topics_covered = {
            "childhood": False,
            "personality": False,
            "career": False,
            "relationships": False,
            "health": False,
            "time_specific_events": False,
            "day_night_preference": False,
            "morning_evening_energy": False,
            "sleep_patterns": False,
            "major_life_events": False,
            "transit_related_events": False
        }

        response_insights = []

        for answer in previous_answers:
            q_text = answer.get("question", "").lower()
            a_text = answer.get("answer", "").lower()
            category = answer.get("category", "")

            if category:
                categories_asked.add(category)

            # Analyze each question/answer for topic coverage
            if any(word in q_text for word in ["childhood", "growing up", "young", "early years"]):
                topics_covered["childhood"] = True
            if any(word in q_text for word in ["personality", "describe yourself", "trait", "temperament"]):
                topics_covered["personality"] = True
            if any(word in q_text for word in ["career", "job", "work", "profession", "vocation"]):
                topics_covered["career"] = True
            if any(word in q_text for word in ["relationship", "partner", "marriage", "spouse", "romantic"]):
                topics_covered["relationships"] = True
            if any(word in q_text for word in ["health", "illness", "medical", "disease", "condition"]):
                topics_covered["health"] = True
            if any(word in q_text for word in ["time", "hour", "when", "clock", "moment"]):
                topics_covered["time_specific_events"] = True
            if any(word in q_text for word in ["day", "night", "daytime", "nighttime"]):
                topics_covered["day_night_preference"] = True
            if any(word in q_text for word in ["morning", "evening", "energy", "alert", "active"]):
                topics_covered["morning_evening_energy"] = True
            if any(word in q_text for word in ["sleep", "wake", "insomnia", "rest", "dream"]):
                topics_covered["sleep_patterns"] = True
            if any(word in q_text for word in ["major event", "significant", "important", "life-changing"]):
                topics_covered["major_life_events"] = True

            # Extract key insights from previous answers
            if answer.get("answer"):
                response_insights.append({
                    "question": answer.get("question", ""),
                    "answer": answer.get("answer", ""),
                    "category": category,
                    "question_number": previous_answers.index(answer) + 1
                })

        # Create a comprehensive prompt for astrological question generation
        prompt_data = {
            "task": "generate_next_astrological_question",
            "birth_details": {
                "date": birth_date,
                "time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "location": location_name
            },
            "astrological_context": astrological_context,
            "previous_answers": response_insights,
            "topics_covered": topics_covered,
            "categories_asked": list(categories_asked),
            "question_number": len(previous_answers) + 1,
            "astrological_requirements": [
                "The question should be specifically designed to help determine the correct birth time",
                "Focus on events that correlate with planetary transits and progressions sensitive to birth time",
                "Include references to astrological houses, angles, or planetary placements when appropriate",
                "Consider current progressions and transits based on the provided birth data",
                "Prioritize questions about pivotal life moments that would correlate with major transits to angles",
                "Emphasize topics related to the Ascendant, Midheaven, IC, and Descendant as these angles are most sensitive to birth time",
                "Include Vedic astrological principles alongside Western techniques for comprehensive analysis",
                "Consider dasha periods and important planetary yogas in question formulation",
                "Include specific astrological relevance with each question to show why this helps with rectification"
            ],
            "response_format": {
                "id": "Unique identifier (will be automatically generated)",
                "type": "Question type (e.g., open_text, multiple_choice, yes_no, slider, date_event, time_event)",
                "text": "The actual question text",
                "category": "Astrological category (e.g., ascendant, midheaven, relationships, career)",
                "relevance": "Explanation of how this question helps determine birth time from an astrological perspective",
                "options": "For multiple choice questions, array of possible answer options",
                "astrological_factors": "Key astrological factors this question is targeting"
            }
        }

        # Call the OpenAI service to generate a question
        question_response = await self.openai_service.generate_completion(
            prompt=json.dumps(prompt_data, cls=DateTimeEncoder),
            task_type="astrological_question_generation",
            max_tokens=800,
            temperature=0.7
        )

        if not question_response or "content" not in question_response:
            raise ValueError("Failed to generate question from OpenAI service")

        try:
            # Parse the OpenAI response
            content = question_response["content"]

            # Try direct JSON parsing first
            try:
                question_data = json.loads(content)
            except json.JSONDecodeError:
                # Extract JSON if embedded in text
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    question_data = json.loads(json_match.group(0))
                else:
                    # Try to extract from code blocks
                    code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
                    code_matches = re.findall(code_block_pattern, content, re.DOTALL)
                    if code_matches:
                        for code_match in code_matches:
                            try:
                                question_data = json.loads(code_match.strip())
                                break
                            except json.JSONDecodeError:
                                continue
                        else:
                            # If none of the code blocks parsed, use text parsing
                            question_data = self._parse_text_response(content)
                    else:
                        # No JSON found, parse the text response
                        question_data = self._parse_text_response(content)

            # Ensure the question has required fields
            if not isinstance(question_data, dict) or "text" not in question_data:
                raise ValueError("OpenAI response did not contain a valid question with text field")

            # Add ID if missing
            if "id" not in question_data:
                question_data["id"] = f"q_{uuid.uuid4().hex[:8]}"

            # Ensure question type
            if "type" not in question_data:
                question_data["type"] = "open_text"

            # Process options for multiple choice questions
            if "options" in question_data and question_data["options"]:
                processed_options = []
                for i, option in enumerate(question_data["options"]):
                    if isinstance(option, str):
                        processed_options.append({
                            "id": f"opt_{i}_{uuid.uuid4().hex[:4]}",
                            "text": option
                        })
                    elif isinstance(option, dict) and "text" in option:
                        if "id" not in option:
                            option["id"] = f"opt_{i}_{uuid.uuid4().hex[:4]}"
                        processed_options.append(option)
                question_data["options"] = processed_options

            # Calculate confidence based on question number and quality
            confidence = 30.0 + (len(previous_answers) * 5)
            if "relevance" in question_data and len(question_data["relevance"]) > 20:
                confidence += 10.0  # Bonus for well-explained relevance
            if "astrological_factors" in question_data:
                confidence += 10.0  # Bonus for including astrological factors

            # Cap maximum confidence
            confidence = min(90.0, confidence)

            return {
                "next_question": question_data,
                "confidence": confidence
            }
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to process OpenAI response: {e}")
            raise ValueError(f"Failed to generate valid astrological question: {str(e)}")

    async def _generate_astrologically_relevant_question(
        self,
        birth_details: Dict[str, Any],
        previous_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a question based on astrological calculations and previous answers.

        Args:
            birth_details: Dictionary containing birth date, time, location
            previous_answers: List of previous question-answer pairs

        Returns:
            Dictionary containing the next question and metadata
        """
        # Extract birth details
        birth_date_str = birth_details.get("birthDate", birth_details.get("birth_date", ""))
        birth_time_str = birth_details.get("birthTime", birth_details.get("birth_time", ""))
        latitude = birth_details.get("latitude", 0.0)
        longitude = birth_details.get("longitude", 0.0)
        timezone = birth_details.get("timezone", "UTC")

        # Generate a unique ID for the question
        question_id = f"q_{uuid.uuid4().hex[:8]}"

        # Create enhanced astrological context
        astrological_context = {
            "birth_date": birth_date_str,
            "birth_time": birth_time_str,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "current_question_number": len(previous_answers) + 1,
            "previous_answers_count": len(previous_answers),
            "birth_time_rectification_focus": True
        }

        # Add analyzed categories from previous answers
        if previous_answers:
            categories_asked = set()
            response_patterns = {
                "has_childhood_info": False,
                "has_personality_info": False,
                "has_career_info": False,
                "has_relationship_info": False,
                "has_health_info": False,
                "has_time_specific_info": False,
                "has_day_night_info": False
            }

            for answer in previous_answers:
                q_text = answer.get("question", "").lower()
                category = answer.get("category", "")

                if category:
                    categories_asked.add(category)

                # Check response patterns
                if "childhood" in q_text or "growing up" in q_text:
                    response_patterns["has_childhood_info"] = True
                if "personality" in q_text or "describe yourself" in q_text:
                    response_patterns["has_personality_info"] = True
                if "career" in q_text or "job" in q_text or "work" in q_text:
                    response_patterns["has_career_info"] = True
                if "relationship" in q_text or "partner" in q_text or "marriage" in q_text:
                    response_patterns["has_relationship_info"] = True
                if "health" in q_text or "illness" in q_text or "medical" in q_text:
                    response_patterns["has_health_info"] = True
                if "time" in q_text or "hour" in q_text or "when" in q_text:
                    response_patterns["has_time_specific_info"] = True
                if "day" in q_text or "night" in q_text or "morning" in q_text or "evening" in q_text:
                    response_patterns["has_day_night_info"] = True

            astrological_context["categories_asked"] = list(categories_asked)
            astrological_context["response_patterns"] = response_patterns

        # Create a comprehensive prompt for OpenAI with deep astrological context
        prompt_data = {
            "task": "generate_astrologically_meaningful_question",
            "birth_details": {
                "date": birth_date_str,
                "time": birth_time_str,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone
            },
            "astrological_context": astrological_context,
            "previous_answers": previous_answers,
            "question_number": len(previous_answers) + 1,
            "astrological_requirements": [
                "The question should be specifically designed to help determine the correct birth time",
                "Focus on events that correlate with planetary transits and progressions sensitive to birth time",
                "Include references to astrological houses, angles, or planetary placements when appropriate",
                "Consider current progressions and transits based on the provided birth data",
                "Prioritize questions about pivotal life moments that would correlate with major transits to angles",
                "Emphasize topics related to the Ascendant, Midheaven, IC, and Descendant as these angles are most sensitive to birth time",
                "Include specific astrological relevance with each question to show why this helps with rectification"
            ],
            "response_format": {
                "id": "Unique identifier (will be automatically generated)",
                "type": "Question type (e.g., open_text, multiple_choice, yes_no, slider, date_event, time_event)",
                "text": "The actual question text",
                "category": "Astrological category (e.g., ascendant, midheaven, relationships, career)",
                "relevance": "Explanation of how this question helps determine birth time from an astrological perspective",
                "options": "For multiple choice questions, array of possible answer options"
            }
        }

        # Get astrologically meaningful question from OpenAI
        if not self.openai_service:
            raise ValueError("OpenAI service is required for generating astrologically relevant questions")

        response = await self.openai_service.generate_completion(
            prompt=json.dumps(prompt_data),
            task_type="generate_next_question",
            max_tokens=1000
        )

        if not response or "content" not in response:
            raise ValueError("Failed to generate question from OpenAI service")

        try:
            # Parse the OpenAI response
            question_data = json.loads(response["content"])
        except json.JSONDecodeError:
            # Extract structured data from text response if not in JSON format
            content = response["content"]
            question_match = re.search(r'text[":\s]+(.+?)(?:,|\n|"|$)', content)
            category_match = re.search(r'category[":\s]+(.+?)(?:,|\n|"|$)', content)
            relevance_match = re.search(r'relevance[":\s]+(.+?)(?:,|\n|"|$)', content)
            type_match = re.search(r'type[":\s]+(.+?)(?:,|\n|"|$)', content)

            question_data = {
                "id": question_id,
                "text": question_match.group(1) if question_match else "Please describe an important life event that might help determine your birth time.",
                "category": category_match.group(1) if category_match else "life_events",
                "relevance": relevance_match.group(1) if relevance_match else "Helps correlate life events with planetary transits to angles",
                "type": type_match.group(1) if type_match else "open_text"
            }

        # Ensure question has all required fields
        if "id" not in question_data:
            question_data["id"] = question_id

        if "type" not in question_data:
            question_data["type"] = "open_text"

        # Format options if present
        if "options" in question_data and question_data["options"]:
            processed_options = []
            for i, option in enumerate(question_data["options"]):
                if isinstance(option, str):
                    processed_options.append({
                        "id": f"opt_{i}_{uuid.uuid4().hex[:4]}",
                        "text": option
                    })
                elif isinstance(option, dict) and "text" in option:
                    if "id" not in option:
                        option["id"] = f"opt_{i}_{uuid.uuid4().hex[:4]}"
                    processed_options.append(option)
            question_data["options"] = processed_options

        # Calculate confidence based on question number and available data
        base_confidence = 60.0
        additional_confidence = min(30.0, len(previous_answers) * 5)
        confidence = base_confidence + additional_confidence

        return {
            "next_question": question_data,
            "confidence": confidence
        }

    async def submit_answer(
        self,
        session_id: str,
        question_id: str,
        answer: Any
    ) -> Dict[str, Any]:
        """
        Submit an answer to a question in the questionnaire.

        Args:
            session_id: The session ID for the questionnaire
            question_id: The ID of the question being answered
            answer: The answer data

        Returns:
            Dictionary with answer submission status
        """
        logger.info(f"Submitting answer for question {question_id} in session {session_id}")

        try:
            # Validate session exists before proceeding
            session = await self.session_store.get_session(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found")
                return {
                    "status": "error",
                    "message": f"Session {session_id} not found"
                }

            # Get the question text if available in the session
            question_text = ""
            question_category = ""
            question_relevance = ""
            if "questions" in session:
                for q in session["questions"]:
                    if q.get("id") == question_id:
                        question_text = q.get("text", "")
                        question_category = q.get("category", "")
                        question_relevance = q.get("relevance", "")
                        break

            # Store the answer in the session
            await self.session_store.add_question_response(
                session_id=session_id,
                question_id=question_id,
                question_text=question_text,
                answer=answer,
                metadata={
                    "category": question_category,
                    "relevance": question_relevance
                }
            )

            return {
                "status": "success",
                "message": "Answer submitted successfully",
                "session_id": session_id,
                "question_id": question_id
            }

        except Exception as e:
            logger.error(f"Error submitting answer: {e}")
            return {
                "status": "error",
                "message": f"Failed to submit answer: {str(e)}"
            }

    async def _perform_astrological_analysis(
        self,
        question: str,
        answer: Any,
        birth_date: str,
        birth_time: str,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Perform deep astrological analysis of question and answer using AI integration.
        This implementation uses OpenAI to provide comprehensive astrological insights
        without fallbacks or simplifications.

        Args:
            question: Question text
            answer: Answer provided by the user
            birth_date: Birth date string
            birth_time: Birth time string
            latitude: Birth latitude
            longitude: Birth longitude

        Returns:
            Dictionary with detailed astrological insights

        Raises:
            ValueError: If OpenAI service is not available or fails
        """
        # Convert answer to string if needed
        answer_text = str(answer) if not isinstance(answer, str) else answer

        if not self.openai_service:
            raise ValueError("OpenAI service is required for comprehensive astrological analysis")

        if not question or not answer_text:
            raise ValueError("Question and answer are required for astrological analysis")

        # Prepare comprehensive astrological analysis request for OpenAI
        analysis_request = {
            "task": "astrological_birth_time_analysis",
            "question": question,
            "answer": answer_text,
            "birth_details": {
                "date": birth_date,
                "time": birth_time,
                "latitude": latitude,
                "longitude": longitude
            },
            "astrological_requirements": [
                "Analyze the response for connections to all 12 astrological houses and their rulerships",
                "Determine which houses and planets are most affected by the described experiences",
                "Identify potential aspects and configurations indicated by the response",
                "Assess how strongly the answer correlates with birth time sensitivity",
                "Extract key astrological significators from the response",
                "Determine the relevance of the answer for birth time rectification",
                "Provide confidence level for the astrological correlations identified",
                "Include analysis based on Vedic astrological principles",
                "Consider nakshatra positions in your analysis",
                "Analyze planetary yogas that might be indicated by the response",
                "Consider dasha periods that align with described life events",
                "Analyze how planetary periods might correlate with the answer"
            ],
            "response_format": {
                "houses_affected": ["List of house numbers (1-12) affected by the response"],
                "planets_affected": ["List of planets affected by the response"],
                "possible_aspects": ["List of possible aspects indicated"],
                "astrological_significators": ["Key astrological significators extracted"],
                "birth_time_relevance": "Float 0.0-1.0 indicating relevance to birth time determination",
                "analysis_confidence": "Float 0.0-100.0 indicating confidence in the analysis",
                "interpretation_summary": "Brief summary of astrological interpretation",
                "vedic_factors": {
                    "nakshatras": ["Relevant nakshatras"],
                    "dashas": ["Relevant dashas"],
                    "yogas": ["Relevant yogas"]
                },
                "birth_time_indicators": {
                    "day_night": "Indication if day or night birth is suggested",
                    "time_range": "Potential time range suggested by answer",
                    "rising_sign_possibilities": ["Possible rising signs based on answer"]
                }
            }
        }

        # Use OpenAI for deep astrological analysis
        response = await self.openai_service.generate_completion(
            prompt=json.dumps(analysis_request),
            task_type="astrological_analysis",
            max_tokens=1500
        )

        if not response or "content" not in response:
            raise ValueError("Failed to generate astrological analysis from OpenAI")

        # Parse the OpenAI analysis response with improved handling
        try:
            # Try direct JSON parsing first
            content = response["content"]
            try:
                analysis_result = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON if embedded in text
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        analysis_result = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        logger.warning(f"Found JSON-like structure but couldn't parse it")
                        # Fall back to structured text parsing
                        analysis_result = self._parse_text_response(content)
                else:
                    # Try to extract from code blocks
                    code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
                    code_matches = re.findall(code_block_pattern, content, re.DOTALL)
                    if code_matches:
                        for code_match in code_matches:
                            try:
                                analysis_result = json.loads(code_match.strip())
                                break
                            except json.JSONDecodeError:
                                continue
                        else:
                            # If none of the code blocks parsed, use text parsing
                            analysis_result = self._parse_text_response(content)
                    else:
                        # No JSON found, parse the text response
                        analysis_result = self._parse_text_response(content)

            # Process the analysis_result
            if isinstance(analysis_result, dict):
                return analysis_result
            else:
                logger.warning("Unexpected analysis result format, using text parsing")
                return self._parse_text_response(content)

        except Exception as e:
            logger.error(f"Error processing astrological analysis: {e}")
            raise ValueError(f"Failed to process astrological analysis: {str(e)}")

    def _parse_text_response(self, content: str) -> Dict[str, Any]:
        """
        Parse a free-form text response into a structured format.
        This is used when OpenAI doesn't return valid JSON.

        Args:
            content: Text content from OpenAI

        Returns:
            Structured dictionary with analysis data
        """
        # Initialize empty result
        result = {
            "houses_affected": [],
            "planets_affected": [],
            "possible_aspects": [],
            "astrological_significators": [],
            "birth_time_relevance": 0.5,  # Default middle value
            "analysis_confidence": 50.0,  # Default middle value
            "interpretation_summary": "",
            "vedic_factors": {
                "nakshatras": [],
                "dashas": [],
                "yogas": []
            },
            "birth_time_indicators": {
                "day_night": "",
                "time_range": "",
                "rising_sign_possibilities": []
            }
        }

        # Extract interpretation summary - use the first paragraph if available
        paragraphs = content.split('\n\n')
        if paragraphs:
            result["interpretation_summary"] = paragraphs[0].strip()

        # Extract houses affected
        house_pattern = r'(?:house|houses)[^\d]*(\d+(?:,\s*\d+)*)'
        house_matches = re.findall(house_pattern, content, re.IGNORECASE)
        if house_matches:
            for match in house_matches:
                for house_num in re.findall(r'\d+', match):
                    if int(house_num) <= 12:  # Valid house number
                        result["houses_affected"].append(int(house_num))

        # Extract planets
        planet_names = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
                        "Saturn", "Uranus", "Neptune", "Pluto", "Rahu", "Ketu"]
        for planet in planet_names:
            if re.search(r'\b' + planet + r'\b', content, re.IGNORECASE):
                result["planets_affected"].append(planet)

        # Try to extract time indicators
        if "early morning" in content.lower() or "2-3 AM" in content or "dawn" in content.lower():
            result["birth_time_indicators"]["day_night"] = "Night/Early Morning"
            result["birth_time_indicators"]["time_range"] = "2:00 AM - 4:00 AM"
        elif "night" in content.lower() or "evening" in content.lower():
            result["birth_time_indicators"]["day_night"] = "Night"
        elif "morning" in content.lower() or "day" in content.lower():
            result["birth_time_indicators"]["day_night"] = "Day"

        # Look for confidence indicators
        confidence_pattern = r'confidence[^.]*?(\d+)'
        confidence_matches = re.findall(confidence_pattern, content, re.IGNORECASE)
        if confidence_matches:
            try:
                confidence = float(confidence_matches[0])
                result["analysis_confidence"] = min(100.0, max(0.0, confidence))
            except (ValueError, IndexError):
                pass

        return result

    async def _extract_birth_time_indicators(self, question: str, answer: Any) -> Optional[Dict[str, Any]]:
        """
        Extract birth time indicators from a question and answer.

        Args:
            question: Question text
            answer: Answer text or data

        Returns:
            Dictionary with birth time indicators if found, None otherwise
        """
        if not question or not answer:
            return None

        # Convert answer to string for analysis
        answer_text = str(answer) if not isinstance(answer, str) else answer

        # Create indicator extraction request for OpenAI
        extraction_request = {
            "task": "extract_birth_time_indicators",
            "question": question,
            "answer": answer_text,
            "requirements": [
                "Extract explicit birth time information (e.g., 'born at 3pm')",
                "Identify day/night indicators",
                "Identify early/late indicators",
                "Extract astrological significators that might indicate birth time",
                "Determine relevant house cusps based on the response",
                "Identify specific planetary positions mentioned",
                "Look for transit correlations that could help with birth time rectification"
            ],
            "response_format": {
                "has_time_indicator": "Boolean indicating if birth time information is present",
                "explicit_time": "Direct time information if mentioned",
                "day_night_indicator": "Whether birth was during day or night",
                "early_late_indicator": "Whether birth was early or late",
                "astrological_factors": {
                    "houses": "List of houses relevant to the answer",
                    "planets": "List of planets relevant to the answer",
                    "angles": "List of angles (ASC, MC, IC, DSC) relevant to the answer"
                },
                "confidence": "Float 0-100 indicating confidence in the extraction",
                "reasoning": "Brief explanation of the extraction logic"
            }
        }

        # Use OpenAI for extraction
        if not self.openai_service:
            raise ValueError("OpenAI service is required for birth time indicator extraction")

        response = await self.openai_service.generate_completion(
            prompt=json.dumps(extraction_request),
            task_type="birth_time_extraction",
            max_tokens=800
        )

        if not response or "content" not in response:
            raise ValueError("Failed to generate birth time indicator extraction from OpenAI")

        # Process the extraction response
        try:
            # Parse the OpenAI response
            extraction_result = json.loads(response["content"])

            # Check if we have any indicators
            if not extraction_result.get("has_time_indicator", False):
                return None

            # Create standardized indicator structure
            indicators = {
                "has_time_indicator": extraction_result.get("has_time_indicator", False),
                "explicit_time": extraction_result.get("explicit_time"),
                "day_night_indicator": extraction_result.get("day_night_indicator"),
                "early_late_indicator": extraction_result.get("early_late_indicator"),
                "astrological_factors": extraction_result.get("astrological_factors", {}),
                "confidence": extraction_result.get("confidence", 0.0),
                "reasoning": extraction_result.get("reasoning", ""),
                "extracted_at": datetime.now().isoformat()
            }

            # Only return if we have actual indicators
            if (indicators["explicit_time"] or indicators["day_night_indicator"] or
                indicators["early_late_indicator"] or
                any(factors for factor_type, factors in indicators["astrological_factors"].items())):
                return indicators

            return None

        except json.JSONDecodeError:
            # Extract information from non-JSON response
            content = response["content"]

            # Check for key indicators in the text
            has_indicator = False
            explicit_time = None
            day_night = None
            early_late = None
            confidence = 0.0
            reasoning = ""

            # Try to extract specific time
            time_match = re.search(r'explicit_time[":\s]+"?([0-9]{1,2}:[0-9]{2}(?:\s*[APMapm]{2})?)', content)
            if time_match:
                explicit_time = time_match.group(1)
                has_indicator = True
                confidence += 30.0

            # Extract day/night indicator
            day_night_match = re.search(r'day_night_indicator[":\s]+"?(day|night|morning|evening|afternoon)', content, re.IGNORECASE)
            if day_night_match:
                day_night = day_night_match.group(1).lower()
                has_indicator = True
                confidence += 20.0

            # Extract early/late indicator
            early_late_match = re.search(r'early_late_indicator[":\s]+"?(early|late|on time)', content, re.IGNORECASE)
            if early_late_match:
                early_late = early_late_match.group(1).lower()
                has_indicator = True
                confidence += 20.0

            # Extract confidence
            confidence_match = re.search(r'confidence[":\s]+([0-9.]+)', content)
            if confidence_match:
                try:
                    confidence = float(confidence_match.group(1))
                except ValueError:
                    pass

            # Extract reasoning
            reasoning_match = re.search(r'reasoning[":\s]+"([^"]+)"', content)
            if reasoning_match:
                reasoning = reasoning_match.group(1)

            # Extract astrological factors
            houses = []
            planets = []
            angles = []

            houses_match = re.search(r'houses[":\s]+\[(.*?)\]', content, re.DOTALL)
            if houses_match:
                houses_text = houses_match.group(1)
                houses = [h.strip(' "\'') for h in houses_text.split(',') if h.strip(' "\'')]
                if houses:
                    has_indicator = True

            planets_match = re.search(r'planets[":\s]+\[(.*?)\]', content, re.DOTALL)
            if planets_match:
                planets_text = planets_match.group(1)
                planets = [p.strip(' "\'') for p in planets_text.split(',') if p.strip(' "\'')]
                if planets:
                    has_indicator = True

            angles_match = re.search(r'angles[":\s]+\[(.*?)\]', content, re.DOTALL)
            if angles_match:
                angles_text = angles_match.group(1)
                angles = [a.strip(' "\'') for a in angles_text.split(',') if a.strip(' "\'')]
                if angles:
                    has_indicator = True

            if has_indicator:
                return {
                    "has_time_indicator": True,
                    "explicit_time": explicit_time,
                    "day_night_indicator": day_night,
                    "early_late_indicator": early_late,
                    "astrological_factors": {
                        "houses": houses,
                        "planets": planets,
                        "angles": angles
                    },
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "extracted_at": datetime.now().isoformat()
                }

            return None

    async def _analyze_responses_for_time_range(
        self,
        responses: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze responses to estimate a birth time range.

        Args:
            responses: List of question responses

        Returns:
            Dictionary with estimated time range or None
        """
        # Use AI to analyze responses if available
        if self.openai_service:
            try:
                # Prepare data for OpenAI
                request_data = {
                    "responses": responses,
                    "task": "estimate_birth_time_range",
                    "require_detailed_analysis": True,
                    "analysis_goal": "Determine the most likely birth time range based on responses"
                }

                # Generate analysis with OpenAI
                response = await self.openai_service.generate_completion(
                    prompt=json.dumps(request_data),
                    task_type="analyze_questionnaire",
                    max_tokens=400
                )

                if response and "content" in response:
                    try:
                        # Parse the OpenAI response
                        analysis = json.loads(response["content"])

                        if isinstance(analysis, dict) and "start_time" in analysis and "end_time" in analysis:
                            # Add detailed reasoning if available
                            reasoning = analysis.get("reasoning", "Based on analysis of your questionnaire responses")
                            return {
                                "start_time": analysis["start_time"],
                                "end_time": analysis["end_time"],
                                "confidence": analysis.get("confidence", 70.0),
                                "explanation": analysis.get("explanation", "Based on questionnaire responses"),
                                "reasoning": reasoning,
                                "indicator_count": sum(1 for r in responses if self._is_time_related_response(r))
                            }
                    except json.JSONDecodeError:
                        logger.error("Failed to parse OpenAI response as JSON")
            except Exception as e:
                logger.error(f"Error analyzing responses with OpenAI: {e}")

        # Extract birth time indicators from responses
        birth_time_indicators = {}

        # First, identify explicit time mentions
        explicit_time = self._extract_explicit_time(responses)
        if explicit_time:
            birth_time_indicators["explicit_time"] = explicit_time

        # Identify day/night preference
        day_night = self._extract_day_night_preference(responses)
        if day_night:
            birth_time_indicators["day_night"] = day_night

        # Identify early/late indicators
        early_late = self._extract_early_late_indicator(responses)
        if early_late:
            birth_time_indicators["early_late"] = early_late

        # Extract confidence in recorded time
        confidence_level = self._extract_confidence_level(responses)
        if confidence_level:
            birth_time_indicators["confidence"] = confidence_level

        # If no indicators found, return None
        if not birth_time_indicators:
            return None

        # Generate time range based on indicators
        time_range = self._generate_time_range(birth_time_indicators)
        if time_range:
            return time_range

        # If we have only a day/night indicator, create a broad window
        if "day_night" in birth_time_indicators:
            if birth_time_indicators["day_night"] == "day":
                return {
                    "start_time": "06:00",
                    "end_time": "18:00",
                    "confidence": 50.0,
                    "explanation": "Based on your indication of being born during the day",
                    "reasoning": "You mentioned being born during daylight hours"
                }
            else:  # night
                return {
                    "start_time": "18:00",
                    "end_time": "06:00",
                    "confidence": 50.0,
                    "explanation": "Based on your indication of being born during the night",
                    "reasoning": "You mentioned being born during nighttime hours"
                }

        # Default to entire day if we can't narrow it down
        return None

    def _extract_explicit_time(self, responses: List[Dict[str, Any]]) -> Optional[str]:
        """Extract explicit time mentions from responses."""
        for response in responses:
            question = response.get("question", "").lower()
            answer = response.get("answer", "")

            if not isinstance(answer, str):
                continue

            # Check for direct time mentions
            time_pattern = re.compile(r'(\d{1,2}):(\d{2})\s*(am|pm)?', re.IGNORECASE)
            time_match = time_pattern.search(answer)

            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                period = time_match.group(3)

                # Convert to 24-hour format if am/pm specified
                if period and period.lower() == 'pm' and hour < 12:
                    hour += 12
                elif period and period.lower() == 'am' and hour == 12:
                    hour = 0

                return f"{hour:02d}:{minute:02d}"

        return None

    def _extract_day_night_preference(self, responses: List[Dict[str, Any]]) -> Optional[str]:
        """Extract day/night preference from responses."""
        for response in responses:
            question = response.get("question", "").lower()
            answer = response.get("answer", "")

            if not isinstance(answer, str):
                continue

            answer_lower = answer.lower()

            # Check for day/night indicators in both question and answer
            if ("day or night" in question or "during the day" in question or
                "at night" in question):
                if "day" in answer_lower:
                    return "day"
                elif "night" in answer_lower:
                    return "night"

        return None

    def _extract_early_late_indicator(self, responses: List[Dict[str, Any]]) -> Optional[str]:
        """Extract early/late indicators from responses."""
        for response in responses:
            question = response.get("question", "").lower()
            answer = response.get("answer", "")

            if not isinstance(answer, str):
                continue

            answer_lower = answer.lower()

            # Check for early/late indicators
            if "early" in question or "late" in question or "on time" in question:
                if "early" in answer_lower:
                    return "early"
                elif "late" in answer_lower:
                    return "late"
                elif "on time" in answer_lower:
                    return "on time"

        return None

    def _extract_confidence_level(self, responses: List[Dict[str, Any]]) -> Optional[str]:
        """Extract confidence level in recorded birth time."""
        for response in responses:
            question = response.get("question", "").lower()
            answer = response.get("answer", "")

            if not isinstance(answer, str):
                continue

            answer_lower = answer.lower()

            # Check for confidence indicators
            if "confident" in question and "birth time" in question:
                if "very" in answer_lower or "certain" in answer_lower or "official" in answer_lower:
                    return "high"
                elif "fairly" in answer_lower or "confident" in answer_lower:
                    return "medium"
                elif "unsure" in answer_lower or "not sure" in answer_lower:
                    return "low"
                elif "guess" in answer_lower or "estimate" in answer_lower:
                    return "very_low"

        return None

    def _generate_time_range(self, indicators: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Generate time range based on indicators."""
        # If we have an explicit time, use it with a window
        if "explicit_time" in indicators:
            try:
                time_str = indicators["explicit_time"]
                hour, minute = map(int, time_str.split(":"))

                # Window size based on confidence
                if indicators.get("confidence") == "high":
                    window_minutes = 15
                elif indicators.get("confidence") == "medium":
                    window_minutes = 30
                elif indicators.get("confidence") == "low":
                    window_minutes = 60
                else:  # very low or not specified
                    window_minutes = 90

                # Create time objects for start and end
                base_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                start_time = (base_time - timedelta(minutes=window_minutes)).strftime("%H:%M")
                end_time = (base_time + timedelta(minutes=window_minutes)).strftime("%H:%M")

                return {
                    "start_time": start_time,
                    "end_time": end_time,
                    "confidence": 70.0,
                    "explanation": f"Based on your estimated birth time with a {window_minutes}-minute window",
                    "reasoning": "You provided a specific birth time estimate"
                }
            except (ValueError, IndexError):
                pass

        return None

    def _is_time_related_response(self, response: Dict[str, Any]) -> bool:
        """Check if a response is related to birth time."""
        if not response:
            return False

        question = response.get("question", "").lower()
        return any(keyword in question for keyword in
                   ["birth time", "born", "day or night", "early", "late",
                    "time of birth", "birth hour"])

    async def complete_questionnaire(self, session_id: str, chart_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete a questionnaire session and prepare for birth time rectification.

        Args:
            session_id: Session identifier
            chart_id: Optional chart ID (can be retrieved from session if not provided)

        Returns:
            Dictionary with completion status and summary
        """
        logger.info(f"Completing questionnaire for session {session_id}")

        try:
            # Get session data
            session = await self.session_store.get_session(session_id)
            if not session:
                return {
                    "status": "error",
                    "message": f"Session {session_id} not found"
                }

            # Get the chart ID from parameters or session
            chart_id = chart_id or session.get("chart_id")
            if not chart_id:
                return {
                    "status": "error",
                    "message": "Chart ID not found in session or parameters"
                }

            # Get responses from session
            responses = await self.session_store.get_responses(session_id)
            if not responses:
                return {
                    "status": "error",
                    "message": "No responses found in session"
                }

            # Mark session as complete
            session["status"] = "complete"
            session["completed_at"] = datetime.now().isoformat()
            await self.session_store.update_session(session_id, session)

            # Return completion status with minimal data
            return {
                "status": "complete",
                "message": "Questionnaire completed successfully",
                "session_id": session_id,
                "chart_id": chart_id,
                "questions_answered": len(responses),
                "completed_at": session["completed_at"],
                "rectification_status": "processing",
                "rectification_id": f"rect_{uuid.uuid4().hex[:8]}"
            }

        except Exception as e:
            logger.error(f"Error completing questionnaire: {e}")
            return {
                "status": "error",
                "message": f"Error completing questionnaire: {str(e)}"
            }

    async def _perform_comprehensive_analysis(
        self,
        responses: List[Dict[str, Any]],
        birth_details: Dict[str, Any],
        birth_time_indicators: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive astrological analysis of all questionnaire answers collectively.

        Args:
            responses: List of question/answer pairs
            birth_details: Dictionary containing birth details
            birth_time_indicators: List of birth time indicators extracted from answers

        Returns:
            Dictionary with comprehensive astrological analysis
        """
        # Default analysis structure
        analysis = {
            "summary": "Analysis based on questionnaire responses",
            "astrological_factors": {
                "houses": {},
                "planets": {},
                "aspects": []
            },
            "identified_patterns": [],
            "confidence": 70.0
        }

        # Get birth time range from responses if available
        birth_time_range = None
        for response in responses:
            if response.get("birth_time_range"):
                birth_time_range = response.get("birth_time_range")
                break

        # Use OpenAI for comprehensive analysis if available
        if self.openai_service:
            try:
                # Prepare data for analysis
                analysis_data = {
                    "responses": responses,
                    "birth_details": birth_details,
                    "birth_time_indicators": birth_time_indicators,
                    "task": "comprehensive_astrological_analysis_for_birth_time_rectification"
                }

                # Get analysis from OpenAI
                response = await self.openai_service.generate_completion(
                    prompt=json.dumps(analysis_data),
                    task_type="comprehensive_astrological_analysis",
                    max_tokens=1000
                )

                if response and "content" in response:
                    try:
                        # Parse the response
                        ai_analysis = json.loads(response["content"])
                        if isinstance(ai_analysis, dict):
                            # Merge with our analysis structure
                            if "summary" in ai_analysis:
                                analysis["summary"] = ai_analysis["summary"]

                            if "astrological_factors" in ai_analysis:
                                analysis["astrological_factors"] = ai_analysis["astrological_factors"]

                            if "identified_patterns" in ai_analysis:
                                analysis["identified_patterns"] = ai_analysis["identified_patterns"]

                            if "confidence" in ai_analysis:
                                analysis["confidence"] = ai_analysis["confidence"]

                            return analysis
                    except json.JSONDecodeError:
                        logger.warning("Could not parse OpenAI comprehensive analysis as JSON")
            except Exception as e:
                logger.error(f"Error performing AI-assisted comprehensive analysis: {e}")

        # If OpenAI is not available or fails, use rule-based analysis

        # First, gather all keywords from responses to identify patterns
        all_text = " ".join([
            f"{r.get('question', '')} {r.get('answer', '')}"
            for r in responses if isinstance(r.get('answer', ''), str)
        ]).lower()

        # Analyze for house emphasis
        house_keywords = {
            "1st house": ["self", "identity", "appearance", "personality", "how I am seen", "first impression"],
            "2nd house": ["money", "possessions", "values", "finances", "resources", "income"],
            "3rd house": ["communication", "siblings", "neighbors", "short trips", "learning", "writing"],
            "4th house": ["home", "family", "roots", "mother", "foundation", "childhood", "private life"],
            "5th house": ["creativity", "children", "romance", "pleasure", "hobbies", "entertainment"],
            "6th house": ["work", "service", "health", "daily routine", "skills", "pets"],
            "7th house": ["partnerships", "marriage", "relationships", "contracts", "agreements", "open enemies"],
            "8th house": ["transformation", "sex", "joint resources", "inheritances", "death", "taxes"],
            "9th house": ["higher education", "philosophy", "travel", "beliefs", "religion", "law"],
            "10th house": ["career", "reputation", "public image", "authority", "father", "achievements"],
            "11th house": ["friends", "groups", "hopes", "wishes", "social causes", "networks"],
            "12th house": ["secrets", "hidden things", "isolation", "spiritual", "unconscious", "service"]
        }

        # Count house emphasis
        house_emphasis = {}
        for house, keywords in house_keywords.items():
            count = sum(1 for keyword in keywords if keyword in all_text)
            if count > 0:
                house_emphasis[house] = count

        # Sort houses by emphasis
        sorted_houses = sorted(house_emphasis.items(), key=lambda x: x[1], reverse=True)

        # Add top 3 houses to analysis
        for i, (house, count) in enumerate(sorted_houses[:3]):
            analysis["astrological_factors"]["houses"][house] = {
                "emphasis": count,
                "rank": i + 1,
                "keywords": house_keywords[house][:3]  # Top 3 keywords for this house
            }

        # Analyze for planetary emphasis
        planet_keywords = {
            "Sun": ["father", "ego", "self", "identity", "leadership", "vitality", "pride", "confidence"],
            "Moon": ["mother", "emotions", "feelings", "nurturing", "home", "moods", "intuition", "care"],
            "Mercury": ["communication", "thinking", "learning", "writing", "speaking", "siblings", "travel", "information"],
            "Venus": ["love", "beauty", "art", "harmony", "relationships", "values", "pleasure", "attraction"],
            "Mars": ["action", "energy", "drive", "courage", "conflict", "competition", "desire", "assertiveness"],
            "Jupiter": ["expansion", "growth", "optimism", "opportunity", "travel", "philosophy", "education", "abundance"],
            "Saturn": ["responsibility", "discipline", "structure", "time", "boundaries", "limitation", "authority", "ambition"],
            "Uranus": ["change", "innovation", "rebellion", "originality", "freedom", "technology", "disruption", "awakening"],
            "Neptune": ["dreams", "spirituality", "intuition", "illusion", "compassion", "mysticism", "confusion", "idealism"],
            "Pluto": ["transformation", "power", "rebirth", "death", "control", "intensity", "obsession", "regeneration"]
        }

        # Count planet emphasis
        planet_emphasis = {}
        for planet, keywords in planet_keywords.items():
            count = sum(1 for keyword in keywords if keyword in all_text)
            if count > 0:
                planet_emphasis[planet] = count

        # Sort planets by emphasis
        sorted_planets = sorted(planet_emphasis.items(), key=lambda x: x[1], reverse=True)

        # Add top 5 planets to analysis
        for i, (planet, count) in enumerate(sorted_planets[:5]):
            analysis["astrological_factors"]["planets"][planet] = {
                "emphasis": count,
                "rank": i + 1,
                "keywords": planet_keywords[planet][:3]  # Top 3 keywords for this planet
            }

        # Identify astrological patterns
        patterns = []

        # Check for angular emphasis (1st, 4th, 7th, 10th houses)
        angular_houses = ["1st house", "4th house", "7th house", "10th house"]
        angular_emphasis = sum(house_emphasis.get(h, 0) for h in angular_houses)
        total_emphasis = sum(house_emphasis.values())

        if angular_emphasis > 0 and total_emphasis > 0:
            angular_ratio = angular_emphasis / total_emphasis
            if angular_ratio > 0.5:
                patterns.append({
                    "pattern": "Angular House Emphasis",
                    "description": "Strong emphasis on angular houses suggests accurate birth time is crucial, as these houses are most sensitive to birth time changes.",
                    "significance": "high"
                })

        # Check for outer planet emphasis
        outer_planets = ["Saturn", "Uranus", "Neptune", "Pluto"]
        outer_emphasis = sum(planet_emphasis.get(p, 0) for p in outer_planets)
        total_planet_emphasis = sum(planet_emphasis.values())

        if outer_emphasis > 0 and total_planet_emphasis > 0:
            outer_ratio = outer_emphasis / total_planet_emphasis
            if outer_ratio > 0.4:
                patterns.append({
                    "pattern": "Outer Planet Emphasis",
                    "description": "Emphasis on outer planets suggests key life transitions and generational influences are important for this individual.",
                    "significance": "medium"
                })

        # Check for personal planet emphasis
        personal_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars"]
        personal_emphasis = sum(planet_emphasis.get(p, 0) for p in personal_planets)

        if personal_emphasis > 0 and total_planet_emphasis > 0:
            personal_ratio = personal_emphasis / total_planet_emphasis
            if personal_ratio > 0.6:
                patterns.append({
                    "pattern": "Personal Planet Emphasis",
                    "description": "Strong emphasis on personal planets suggests focus on individual personality, daily life, and immediate environment.",
                    "significance": "medium"
                })

        # Add identified patterns to analysis
        analysis["identified_patterns"] = patterns

        # Calculate confidence based on the amount of astrological data identified
        analysis_points = (
            len(analysis["astrological_factors"]["houses"]) * 5 +
            len(analysis["astrological_factors"]["planets"]) * 5 +
            len(analysis["identified_patterns"]) * 10
        )

        analysis["confidence"] = min(90.0, 50.0 + analysis_points / 2)

        # Generate summary based on analysis
        top_houses = [house for house, _ in sorted_houses[:2]]
        top_planets = [planet for planet, _ in sorted_planets[:3]]

        summary = f"Analysis reveals emphasis on {', '.join(top_houses)} and strong influence of {', '.join(top_planets)}. "

        if patterns:
            pattern_names = [p["pattern"] for p in patterns]
            summary += f"Key astrological patterns include: {', '.join(pattern_names)}. "

        if birth_time_indicators:
            summary += "Birth time indicators from responses suggest "
            if birth_time_range:
                start = birth_time_range.get("start_time", "")
                end = birth_time_range.get("end_time", "")
                if start and end:
                    summary += f"a likely birth time between {start} and {end}. "
                else:
                    summary += "potential timeframes for birth. "
            else:
                summary += "various potential birth times. "

        analysis["summary"] = summary

        return analysis

    def _extract_astrological_life_events(self, responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract astrologically significant life events from questionnaire responses.

        Args:
            responses: List of question/answer pairs

        Returns:
            List of identified life events with astrological significance
        """
        life_events = []

        for response in responses:
            question = response.get("question", "")
            answer = response.get("answer", "")

            if not isinstance(answer, str) or not answer.strip():
                continue

            answer_lower = answer.lower()

            # Look for age mentions
            age_pattern = re.compile(r'(at|when I was|around|about|age)\s+(\d{1,2})', re.IGNORECASE)
            age_matches = age_pattern.finditer(answer_lower)

            # Look for year mentions
            year_pattern = re.compile(r'in\s+(\d{4})', re.IGNORECASE)
            year_matches = year_pattern.finditer(answer_lower)

            # Process age references
            for match in age_matches:
                try:
                    age = int(match.group(2))

                    # Extract context before and after the age mention
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(answer_lower), match.end() + 100)
                    context = answer_lower[start_pos:end_pos]

                    # Determine event type based on context
                    event_type = self._determine_event_type(context, question)

                    # Determine astrological significance
                    astro_significance = self._determine_astrological_significance(age, event_type)

                    if event_type and astro_significance:
                        life_events.append({
                            "age": age,
                            "event_type": event_type,
                            "context": context,
                            "astrological_significance": astro_significance
                        })
                except (ValueError, IndexError):
                    continue

            # Process year references
            for match in year_matches:
                try:
                    year = int(match.group(1))

                    # Extract context around the year mention
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(answer_lower), match.end() + 100)
                    context = answer_lower[start_pos:end_pos]

                    # Determine event type based on context
                    event_type = self._determine_event_type(context, question)

                    if event_type:
                        life_events.append({
                            "year": year,
                            "event_type": event_type,
                            "context": context
                        })
                except (ValueError, IndexError):
                    continue

        return life_events

    def _determine_event_type(self, context: str, question: str) -> Optional[str]:
        """Determine the type of life event based on context."""
        event_keywords = {
            "career_change": ["job", "career", "promotion", "hired", "fired", "profession", "work", "employment"],
            "relationship": ["marriage", "wedding", "divorce", "partner", "engaged", "relationship", "separated"],
            "education": ["school", "college", "university", "degree", "graduated", "education", "study"],
            "relocation": ["moved", "moving", "relocation", "city", "country", "abroad", "relocated"],
            "family": ["child", "birth", "pregnant", "baby", "son", "daughter", "family", "parent"],
            "health": ["illness", "sick", "disease", "diagnosis", "health", "hospital", "recovery", "accident"],
            "loss": ["death", "passed away", "lost", "grief", "funeral", "died"],
            "spiritual": ["spiritual", "awakening", "religion", "meditation", "faith", "belief"],
            "financial": ["money", "financial", "investment", "debt", "purchased", "bought", "sold"]
        }

        # First check the question for clues
        question_lower = question.lower()
        for event_type, keywords in event_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return event_type

        # Then check the context
        context_lower = context.lower()
        matched_types = {}

        for event_type, keywords in event_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in context_lower)
            if matches > 0:
                matched_types[event_type] = matches

        # Return the event type with the most keyword matches, if any
        if matched_types:
            return max(matched_types.items(), key=lambda x: x[1])[0]

        return None

    def _determine_astrological_significance(self, age: int, event_type: Optional[str]) -> Optional[Dict[str, Any]]:
        """Determine the astrological significance of a life event at a specific age."""

        # Map ages to significant transits
        transit_ages = {
            # Saturn transits
            29: {"transit": "Saturn Return", "planet": "Saturn", "aspect": "conjunction", "significance": "high"},
            30: {"transit": "Saturn Return", "planet": "Saturn", "aspect": "conjunction", "significance": "high"},
            44: {"transit": "Saturn Opposition", "planet": "Saturn", "aspect": "opposition", "significance": "high"},
            7: {"transit": "Saturn Square", "planet": "Saturn", "aspect": "square", "significance": "medium"},
            14: {"transit": "Saturn Square", "planet": "Saturn", "aspect": "square", "significance": "medium"},
            21: {"transit": "Saturn Square", "planet": "Saturn", "aspect": "square", "significance": "medium"},
            36: {"transit": "Saturn Square", "planet": "Saturn", "aspect": "square", "significance": "medium"},
            51: {"transit": "Saturn Square", "planet": "Saturn", "aspect": "square", "significance": "medium"},

            # Jupiter transits
            12: {"transit": "Jupiter Return", "planet": "Jupiter", "aspect": "conjunction", "significance": "medium"},
            24: {"transit": "Jupiter Return", "planet": "Jupiter", "aspect": "conjunction", "significance": "medium"},
            36: {"transit": "Jupiter Return", "planet": "Jupiter", "aspect": "conjunction", "significance": "medium"},
            48: {"transit": "Jupiter Return", "planet": "Jupiter", "aspect": "conjunction", "significance": "medium"},

            # Uranus transits
            21: {"transit": "Uranus Square", "planet": "Uranus", "aspect": "square", "significance": "medium"},
            42: {"transit": "Uranus Opposition", "planet": "Uranus", "aspect": "opposition", "significance": "high"},
            63: {"transit": "Uranus Square", "planet": "Uranus", "aspect": "square", "significance": "medium"},

            # Nodal transits
            19: {"transit": "Nodal Return", "planet": "North Node", "aspect": "conjunction", "significance": "medium"},
            38: {"transit": "Nodal Return", "planet": "North Node", "aspect": "conjunction", "significance": "medium"},

            # Pluto significant ages (approximations)
            38: {"transit": "Pluto Square", "planet": "Pluto", "aspect": "square", "significance": "high"},
            40: {"transit": "Pluto Square", "planet": "Pluto", "aspect": "square", "significance": "high"}
        }

        # Check for exact matches
        if age in transit_ages:
            significance = transit_ages[age].copy()

            # Add house and event type correlations if available
            if event_type:
                house_correlations = {
                    "career_change": "10th house",
                    "relationship": "7th house",
                    "education": "9th house",
                    "relocation": "4th house",
                    "family": "4th house",
                    "health": "6th house",
                    "loss": "8th house",
                    "spiritual": "9th house",
                    "financial": "2nd house"
                }

                if event_type in house_correlations:
                    significance["house"] = house_correlations[event_type]

            return significance

        # Check for near matches (±1 year)
        for transit_age in transit_ages:
            if abs(age - transit_age) <= 1:
                significance = transit_ages[transit_age].copy()
                significance["approximate"] = "yes"  # Use string instead of boolean
                return significance

        # No significant transit found
        return None

    def _assess_birth_time_quality(self, comprehensive_analysis: Dict[str, Any], birth_time_indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Assess the quality of birth time information for rectification.

        Args:
            comprehensive_analysis: Comprehensive analysis of questionnaire responses
            birth_time_indicators: List of birth time indicators from responses

        Returns:
            Dictionary with birth time quality assessment
        """
        # Default assessment
        assessment = {
            "quality": "medium",
            "confidence": 60.0,
            "explanation": "Birth time quality assessed based on questionnaire responses.",
            "critical_factors": []
        }

        # Extract factors that increase confidence
        critical_factors = []
        confidence_points = 60.0

        # Check for direct birth time mentions
        explicit_times = [
            indicator for indicator in birth_time_indicators
            if "indicators" in indicator and "explicit_time" in indicator["indicators"]
        ]

        if explicit_times:
            critical_factors.append({
                "factor": "Explicit Birth Time",
                "impact": "high",
                "description": "Direct mention of birth time in responses."
            })
            confidence_points += 20.0

        # Check for day/night indicators
        day_night_indicators = [
            indicator for indicator in birth_time_indicators
            if "indicators" in indicator and "day_night" in indicator["indicators"]
        ]

        if day_night_indicators:
            critical_factors.append({
                "factor": "Day/Night Indicator",
                "impact": "medium",
                "description": "Indication of birth during day or night hours."
            })
            confidence_points += 10.0

        # Check for emphasis on angular houses
        angular_houses = ["1st house", "4th house", "7th house", "10th house"]
        houses = comprehensive_analysis.get("astrological_factors", {}).get("houses", {})

        angular_emphasis = any(house in houses for house in angular_houses)
        if angular_emphasis:
            critical_factors.append({
                "factor": "Angular House Emphasis",
                "impact": "high",
                "description": "Strong emphasis on houses that are highly sensitive to birth time."
            })
            confidence_points += 15.0

        # Check for identification of major life events correlating with transits
        if "identified_patterns" in comprehensive_analysis:
            transit_patterns = [
                pattern for pattern in comprehensive_analysis["identified_patterns"]
                if "transit" in pattern.get("pattern", "").lower()
            ]

            if transit_patterns:
                critical_factors.append({
                    "factor": "Transit Correlations",
                    "impact": "high",
                    "description": "Life events correlate with significant planetary transits."
                })
                confidence_points += 15.0

        # Determine quality based on confidence points
        quality = "low"
        if confidence_points >= 85:
            quality = "high"
        elif confidence_points >= 65:
            quality = "medium"

        # Cap confidence at 95
        confidence_points = min(95.0, confidence_points)

        # Update assessment
        assessment["quality"] = quality
        assessment["confidence"] = confidence_points
        assessment["critical_factors"] = critical_factors

        # Generate explanation
        if quality == "high":
            assessment["explanation"] = "High quality birth time information available for accurate rectification."
        elif quality == "medium":
            assessment["explanation"] = "Moderate quality birth time information, rectification should be reliable."
        else:
            assessment["explanation"] = "Limited birth time information, rectification will have lower confidence."

        return assessment

    def _calculate_significant_periods(self, birth_date: str, birth_time: str, timezone: str) -> List[Dict[str, Any]]:
        """
        Calculate astrologically significant upcoming periods for the native.

        Args:
            birth_date: Birth date string
            birth_time: Birth time string
            timezone: Timezone string

        Returns:
            List of significant upcoming astrological periods
        """
        significant_periods = []

        try:
            # Parse birth date
            if birth_date:
                birth_dt = datetime.fromisoformat(f"{birth_date}T{birth_time}" if birth_time else f"{birth_date}T12:00:00")
            else:
                return significant_periods

            # Calculate current age
            current_dt = datetime.now()
            age = current_dt.year - birth_dt.year
            if (current_dt.month, current_dt.day) < (birth_dt.month, birth_dt.day):
                age -= 1

            # Identify upcoming significant transits based on age

            # Saturn Return (around age 29-30)
            if 27 <= age < 29:
                years_to_transit = 29 - age
                significant_periods.append({
                    "transit": "Saturn Return",
                    "planet": "Saturn",
                    "aspect": "conjunction",
                    "timing": f"In approximately {years_to_transit} years",
                    "description": "A time of maturity, responsibility, and major life restructuring. Often marks a significant transition into full adulthood.",
                    "significance": "high"
                })

            # Second Saturn Return (around age 58-59)
            elif 56 <= age < 58:
                years_to_transit = 58 - age
                significant_periods.append({
                    "transit": "Second Saturn Return",
                    "planet": "Saturn",
                    "aspect": "conjunction",
                    "timing": f"In approximately {years_to_transit} years",
                    "description": "A period of reassessment of life accomplishments and shifting priorities. Often marks transition to later life stage.",
                    "significance": "high"
                })

            # Uranus Opposition (around age 40-42)
            elif 38 <= age < 40:
                years_to_transit = 41 - age
                significant_periods.append({
                    "transit": "Uranus Opposition",
                    "planet": "Uranus",
                    "aspect": "opposition",
                    "timing": f"In approximately {years_to_transit} years",
                    "description": "Often called the 'mid-life crisis' transit. A time of reassessment, sudden changes, and breaking free from restrictions.",
                    "significance": "high"
                })

            # Jupiter Return (every 12 years)
            next_jupiter_return_age = ((age // 12) + 1) * 12
            years_to_jupiter = next_jupiter_return_age - age
            if years_to_jupiter <= 3:
                significant_periods.append({
                    "transit": "Jupiter Return",
                    "planet": "Jupiter",
                    "aspect": "conjunction",
                    "timing": f"In approximately {years_to_jupiter} years",
                    "description": "A period of growth, opportunity, and expansion. Often brings positive developments in the areas of career, education, or travel.",
                    "significance": "medium"
                })

            # Pluto square (midpoints vary by generation)
            # Approximation for most people born in latter 20th century
            if 35 <= age < 38:
                years_to_transit = 38 - age
                significant_periods.append({
                    "transit": "Pluto Square",
                    "planet": "Pluto",
                    "aspect": "square",
                    "timing": f"In approximately {years_to_transit} years",
                    "description": "A powerful time of transformation, letting go of the old, and deep psychological change.",
                    "significance": "high"
                })

            # Add current transits if applicable

            # Current Saturn transit
            if 29 <= age <= 30:
                significant_periods.append({
                    "transit": "Saturn Return",
                    "planet": "Saturn",
                    "aspect": "conjunction",
                    "timing": "Currently active",
                    "description": "You are currently in your Saturn Return period. This is a time of maturity, responsibility, and major life restructuring.",
                    "significance": "high"
                })

            # Current Uranus Opposition
            elif 40 <= age <= 42:
                significant_periods.append({
                    "transit": "Uranus Opposition",
                    "planet": "Uranus",
                    "aspect": "opposition",
                    "timing": "Currently active",
                    "description": "You are currently in your Uranus Opposition period. This often brings significant changes, reassessment of life direction, and breaking free from restrictions.",
                    "significance": "high"
                })
        except Exception as e:
            logger.error(f"Error calculating significant periods: {e}")

        return significant_periods

    def _categorize_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Categorize responses by topic for better analysis.

        Args:
            responses: List of question/answer pairs

        Returns:
            Dictionary with responses grouped by category
        """
        categories = {}

        for response in responses:
            question = response.get("question", "")
            answer = response.get("answer", "")

            # Try to determine category from metadata first
            if "metadata" in response and "category" in response["metadata"]:
                category = response["metadata"]["category"]
            else:
                # Otherwise categorize based on question content
                category = self._determine_response_category(question)

            # Initialize category list if not present
            if category not in categories:
                categories[category] = []

            # Add response to category
            categories[category].append(response)

        return categories

    def _determine_response_category(self, question: str) -> str:
        """Determine the category of a question based on its content."""
        question_lower = question.lower()

        # Define category keywords
        category_keywords = {
            "personality": ["personality", "describe yourself", "temperament", "character"],
            "childhood": ["childhood", "growing up", "as a child", "young age"],
            "life_events": ["significant event", "major change", "important moment", "milestone"],
            "birth_time": ["birth time", "born", "time of birth", "early", "late", "on time"],
            "career": ["career", "profession", "job", "work", "employment"],
            "relationships": ["relationship", "partner", "marriage", "friend"],
            "health": ["health", "illness", "medical", "condition"],
            "education": ["education", "school", "college", "university", "learning"]
        }

        # Check for category matches
        for category, keywords in category_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return category

        # Default category
        return "general"

    def _extract_key_indicators(self, birth_time_indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract key indicators from birth time indicator list for summary.

        Args:
            birth_time_indicators: List of birth time indicators

        Returns:
            Dictionary with key indicators
        """
        # Initialize key indicators
        key_indicators = {
            "explicit_time": None,
            "day_night": None,
            "timing": None,
            "personality_traits": [],
            "significant_ages": []
        }

        # Process each indicator
        for indicator_data in birth_time_indicators:
            if not isinstance(indicator_data, dict) or "indicators" not in indicator_data:
                continue

            indicators = indicator_data["indicators"]

            # Extract explicit time if available
            if "explicit_time" in indicators and not key_indicators["explicit_time"]:
                key_indicators["explicit_time"] = indicators["explicit_time"]

            # Extract day/night preference
            if "day_night" in indicators and not key_indicators["day_night"]:
                key_indicators["day_night"] = indicators["day_night"]

            # Extract timing information
            if "timing" in indicators and not key_indicators["timing"]:
                key_indicators["timing"] = indicators["timing"]

            # Extract personality traits
            if "personality_traits" in indicators:
                traits = indicators["personality_traits"]
                if isinstance(traits, list):
                    key_indicators["personality_traits"].extend(traits)

            # Extract significant ages
            if "significant_age" in indicators:
                age = indicators["significant_age"]
                if age not in key_indicators["significant_ages"]:
                    key_indicators["significant_ages"].append(age)

        # Remove duplicates and ensure consistent formatting
        key_indicators["personality_traits"] = list(set(key_indicators["personality_traits"]))
        key_indicators["significant_ages"] = sorted(key_indicators["significant_ages"])

        return key_indicators

    async def initialize_questionnaire(self, chart_id: str, session_id: str) -> Dict[str, Any]:
        """
        Initialize a new questionnaire for birth time rectification.

        Args:
            chart_id: The ID of the chart to associate with this questionnaire
            session_id: The session ID for the questionnaire

        Returns:
            Dictionary with questionnaire initialization status
        """
        logger.info(f"Initializing questionnaire for chart {chart_id} in session {session_id}")

        try:
            # Create a new session if it doesn't exist
            session = await self.session_store.get_session(session_id)
            if not session:
                session = {
                    "id": session_id,
                    "chart_id": chart_id,
                    "created_at": datetime.now().isoformat(),
                    "status": "initialized",
                    "questions": [],
                    "responses": [],
                    "birth_time_indicators": []
                }
                await self.session_store.create_session(session_id, session)
            else:
                # Update existing session with chart ID
                session["chart_id"] = chart_id
                session["status"] = "initialized"
                await self.session_store.update_session(session_id, session)

            # Return initialization status
            return {
                "id": session_id,
                "chart_id": chart_id,
                "status": "initialized",
                "created_at": session.get("created_at", datetime.now().isoformat())
            }

        except Exception as e:
            logger.error(f"Error initializing questionnaire: {e}")
            return {
                "status": "error",
                "message": f"Failed to initialize questionnaire: {str(e)}"
            }

    async def get_next_question(self, session_id: str, chart_id: str) -> Dict[str, Any]:
        """
        Get the next question in the questionnaire sequence.

        Args:
            session_id: The session ID for the questionnaire
            chart_id: The chart ID associated with this questionnaire

        Returns:
            Dictionary with the next question or completion status
        """
        logger.info(f"Getting next question for session {session_id}, chart {chart_id}")

        try:
            # Get session data
            session = await self.session_store.get_session(session_id)
            if not session:
                return {
                    "status": "error",
                    "message": f"Session {session_id} not found"
                }

            # Check if the questionnaire is already complete
            if session.get("status") == "complete":
                return {
                    "status": "complete",
                    "message": "Questionnaire already completed",
                    "complete": True
                }

            # Get the previous answers from the session
            responses = await self.session_store.get_responses(session_id)

            # Get birth details from session or fetch from chart service
            birth_details = session.get("birth_details", {})
            if not birth_details and chart_id:
                # Fetch actual chart data from chart service
                from ai_service.services.chart_service import get_chart_service
                chart_service = get_chart_service()
                chart_data = await chart_service.get_chart(chart_id=chart_id)

                if not chart_data:
                    return {
                        "status": "error",
                        "message": f"Failed to fetch chart data for chart {chart_id}"
                    }

                # Extract birth details from chart data
                birth_details = {
                    "birthDate": chart_data.get("birth_date", ""),
                    "birthTime": chart_data.get("birth_time", ""),
                    "birthPlace": chart_data.get("location", ""),
                    "latitude": chart_data.get("latitude", 0.0),
                    "longitude": chart_data.get("longitude", 0.0),
                    "timezone": chart_data.get("timezone", "UTC"),
                    "chart_data": chart_data  # Include full chart data for astrological context
                }

                # Store birth details in session for future use
                session["birth_details"] = birth_details
                await self.session_store.update_session(session_id, session)

            # Generate the next question using the real API
            question_result = await self.generate_next_question(birth_details, responses)

            # Check if we have a valid question
            if not question_result or "next_question" not in question_result:
                return {
                    "status": "error",
                    "message": "Failed to generate next question"
                }

            next_question = question_result.get("next_question", {})

            # If we've gone through enough questions (e.g., 10+), mark as complete
            question_limit = 12
            if len(responses) >= question_limit:
                session["status"] = "complete"
                await self.session_store.update_session(session_id, session)
                return {
                    "status": "complete",
                    "message": f"Questionnaire completed after {len(responses)} questions",
                    "complete": True
                }

            # Store the question in the session
            if "questions" not in session:
                session["questions"] = []

            session["questions"].append(next_question)
            await self.session_store.update_session(session_id, session)

            # Return the next question
            return {
                "status": "success",
                "session_id": session_id,
                "next_question": next_question,
                "questions_answered": len(responses),
                "progress": (len(responses) / question_limit) * 100
            }

        except Exception as e:
            logger.error(f"Error getting next question: {e}")
            return {
                "status": "error",
                "message": f"Failed to get next question: {str(e)}"
            }

# Add this class after the QuestionnaireService class and before the get_questionnaire_service function

class DynamicQuestionnaireService(QuestionnaireService):
    """
    Dynamic version of the questionnaire service for backwards compatibility.

    This class inherits all functionality from QuestionnaireService but can be
    imported with a different name for compatibility with existing tests.
    """
    pass  # All functionality inherited from parent class

# Singleton pattern
_questionnaire_service = None

def get_questionnaire_service() -> QuestionnaireService:
    """
    Get the singleton instance of the QuestionnaireService.

    Returns:
        QuestionnaireService instance
    """
    global _questionnaire_service

    # Try to get from dependency container first
    try:
        from ai_service.utils.dependency_container import get_container
        container = get_container()

        # Check if already registered
        try:
            return container.get("questionnaire_service")
        except ValueError:
            # Not registered yet, register it
            def create_questionnaire_service():
                return QuestionnaireService()

            container.register("questionnaire_service", create_questionnaire_service)
            return container.get("questionnaire_service")
    except Exception as e:
        # Fallback to module-level singleton if dependency container is not available
        logger.info(f"Using module-level singleton for QuestionnaireService: {e}")

        if _questionnaire_service is None:
            _questionnaire_service = QuestionnaireService()

        return _questionnaire_service
