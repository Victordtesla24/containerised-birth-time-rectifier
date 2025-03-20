"""
Questionnaire service for Birth Time Rectifier API.

This service handles the generation and processing of questions for birth time rectification.
"""

import logging
import asyncio
import json
import uuid
import random
from datetime import datetime, timedelta
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
        if openai_service:
            self.openai_service = openai_service
        else:
            try:
                self.openai_service = get_openai_service()
                logger.info("QuestionnaireService initialized with OpenAI service")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI service: {e}")
                self.openai_service = None

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

        # Generate questions using AI
        if self.openai_service:
            try:
                # Prepare birth data for OpenAI
                birth_data = {
                    "birth_date": birth_date,
                    "birth_time": birth_time,
                    "birth_place": birth_place
                }

                # Generate questions with OpenAI
                response = await self.openai_service.generate_completion(
                    prompt=json.dumps(birth_data),
                    task_type="generate_questionnaire",
                    max_tokens=1000
                )

                if response and "content" in response:
                    try:
                        # Parse the OpenAI response
                        questions_data = json.loads(response["content"])
                        if isinstance(questions_data, list) and len(questions_data) > 0:
                            # Add unique IDs to questions
                            for i, question in enumerate(questions_data):
                                if "id" not in question:
                                    question["id"] = f"q_{uuid.uuid4().hex[:8]}"
                                if "options" in question and question["options"]:
                                    for j, option in enumerate(question["options"]):
                                        if isinstance(option, str):
                                            question["options"][j] = {
                                                "id": f"opt_{i}_{j}_{uuid.uuid4().hex[:4]}",
                                                "text": option
                                            }
                                        elif isinstance(option, dict) and "id" not in option:
                                            option["id"] = f"opt_{i}_{j}_{uuid.uuid4().hex[:4]}"

                            return questions_data
                    except json.JSONDecodeError:
                        logger.error("Failed to parse OpenAI response as JSON")
            except Exception as e:
                logger.error(f"Error generating questions with OpenAI: {e}")

        # Fallback: Generate questions using templates
        return self._generate_template_questions(birth_details)

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

        Args:
            birth_details: Dictionary containing birth date, time, location
            previous_answers: List of previous question-answer pairs

        Returns:
            Dictionary containing the next question and metadata
        """
        logger.info(f"Generating next question after {len(previous_answers)} previous answers")

        # Generate question using OpenAI if available
        if self.openai_service:
            try:
                # Extract key astrological factors from birth details to provide context
                birth_date = birth_details.get("birthDate", birth_details.get("birth_date", ""))
                birth_time = birth_details.get("birthTime", birth_details.get("birth_time", ""))
                latitude = birth_details.get("latitude", 0.0)
                longitude = birth_details.get("longitude", 0.0)
                timezone = birth_details.get("timezone", "UTC")

                # Create enhanced context for better question generation
                astrological_context = {
                    "birth_date": birth_date,
                    "birth_time": birth_time,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": timezone,
                    "current_question_number": len(previous_answers) + 1,
                    "birth_time_rectification_focus": True,
                    "question_purpose": "Gathering information to accurately rectify birth time"
                }

                # Prepare data for OpenAI with enhanced context
                request_data = {
                    "birth_details": birth_details,
                    "previous_answers": previous_answers,
                    "confidence": 30.0 + (len(previous_answers) * 10),
                    "question_count": len(previous_answers) + 1,
                    "astrological_context": astrological_context
                }

                # Generate question with OpenAI
                response = await self.openai_service.generate_completion(
                    prompt=json.dumps(request_data),
                    task_type="generate_next_question",
                    max_tokens=500
                )

                if response and "content" in response:
                    try:
                        # Parse the OpenAI response
                        question_data = json.loads(response["content"])

                        # Ensure the question has required fields
                        if isinstance(question_data, dict) and "text" in question_data:
                            if "id" not in question_data:
                                question_data["id"] = f"q_{uuid.uuid4().hex[:8]}"

                            if "type" not in question_data:
                                question_data["type"] = "open_text"

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

                            # Calculate birth time range suggestion based on previous answers if available
                            if len(previous_answers) >= 2:
                                try:
                                    # Analyze previous answers for birth time indications
                                    day_night_indicators = any(
                                        "day" in a.get("question", "").lower() or "night" in a.get("question", "").lower()
                                        for a in previous_answers
                                    )
                                    if day_night_indicators:
                                        question_data["birth_time_range_hint"] = True
                                except Exception as range_error:
                                    logger.warning(f"Error calculating birth time range hint: {range_error}")

                            # Set confidence level
                            confidence = 30.0 + (len(previous_answers) * 10)
                            if confidence > 90:
                                confidence = 90.0

                            return {
                                "next_question": question_data,
                                "confidence": confidence
                            }
                    except json.JSONDecodeError:
                        logger.error("Failed to parse OpenAI response as JSON")
            except Exception as e:
                logger.error(f"Error generating next question with OpenAI: {e}")

        # If OpenAI is not available, use astrological calculations to generate relevant questions
        try:
            # Calculate astrological factors
            return await self._generate_astrologically_relevant_question(birth_details, previous_answers)
        except Exception as e:
            logger.error(f"Error generating astrological question: {e}")
            # Ultimate fallback with a generic but still useful question
            question_id = f"q_{uuid.uuid4().hex[:8]}"
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "Please describe any significant life events that occurred when you were between 28-30 years old.",
                    "category": "life_events",
                    "relevance": "Saturn Return period is astrologically significant for birth time rectification."
                },
                "confidence": 50.0
            }

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
        question_id = f"q_{uuid.uuid4().hex[:8]}"

        # Extract birth details
        birth_date_str = birth_details.get("birthDate", birth_details.get("birth_date", ""))
        birth_time_str = birth_details.get("birthTime", birth_details.get("birth_time", ""))
        latitude = birth_details.get("latitude", 0.0)
        longitude = birth_details.get("longitude", 0.0)
        timezone = birth_details.get("timezone", "UTC")

        # Try to parse the birth date and time
        try:
            if birth_date_str and birth_time_str:
                birth_dt = datetime.fromisoformat(f"{birth_date_str}T{birth_time_str}")
            elif birth_date_str:
                # If only date is provided, use noon as default time
                birth_dt = datetime.fromisoformat(f"{birth_date_str}T12:00:00")
            else:
                # Default to current date and time if parsing fails
                birth_dt = datetime.now()
        except ValueError:
            birth_dt = datetime.now()

        # Analyze previous answers to determine what aspects have been covered
        answered_categories = set()
        personality_asked = False
        childhood_asked = False
        life_events_asked = False

        for answer in previous_answers:
            if answer.get("category"):
                answered_categories.add(answer.get("category"))

            question_text = answer.get("question", "").lower()
            if "personality" in question_text or "describe yourself" in question_text:
                personality_asked = True
            elif "childhood" in question_text or "growing up" in question_text:
                childhood_asked = True
            elif "significant event" in question_text or "major change" in question_text:
                life_events_asked = True

        # Calculate current age based on birth date
        current_year = datetime.now().year
        birth_year = birth_dt.year
        approx_age = current_year - birth_year

        # Determine which astrological factors to focus on based on what hasn't been covered

        # If we haven't asked about personality yet (helps determine rising sign)
        if not personality_asked:
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "How would you describe your personality and physical appearance? Include both strengths and challenges.",
                    "category": "personality",
                    "relevance": "Helps determine potential rising sign and ascendant placement."
                },
                "confidence": 70.0
            }

        # If we haven't asked about early childhood (helps determine 4th house and moon placement)
        if not childhood_asked:
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "Describe your early home life and relationship with your mother or primary caregiver.",
                    "category": "childhood",
                    "relevance": "Helps determine 4th house and moon placement which are sensitive to birth time."
                },
                "confidence": 75.0
            }

        # Check if we've already asked about astrologically significant transit periods
        saturn_return_asked = False
        uranus_opposition_asked = False
        jupiter_return_asked = False

        for answer in previous_answers:
            question_text = answer.get("question", "").lower()
            if "28" in question_text or "29" in question_text or "30" in question_text:
                saturn_return_asked = True
            elif "40" in question_text or "41" in question_text or "42" in question_text:
                uranus_opposition_asked = True
            elif "12" in question_text or "24" in question_text:
                jupiter_return_asked = True

        # Ask about astrologically significant ages if the person is old enough
        if approx_age > 30 and not saturn_return_asked:
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "What significant life changes or events occurred when you were around age 28-30?",
                    "category": "life_events",
                    "relevance": "Saturn Return period is highly sensitive to birth time and helps with rectification."
                },
                "confidence": 85.0
            }

        if approx_age > 42 and not uranus_opposition_asked:
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "Describe any major changes or transformations that happened in your life around age 40-42.",
                    "category": "life_events",
                    "relevance": "Uranus opposition is sensitive to birth time and helps with rectification."
                },
                "confidence": 80.0
            }

        if approx_age > 12 and not jupiter_return_asked:
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "What significant events or changes occurred when you were around 12 years old?",
                    "category": "life_events",
                    "relevance": "Jupiter return at age 12 is sensitive to birth time and helps with rectification."
                },
                "confidence": 75.0
            }

        # Direct questions about the birth time if we haven't covered that
        birth_time_asked = any("birth time" in a.get("question", "").lower() for a in previous_answers)
        if not birth_time_asked:
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "What do you know about the time of your birth? Was it morning, afternoon, evening, or night?",
                    "category": "birth_time",
                    "relevance": "Direct information about birth time provides foundation for rectification."
                },
                "confidence": 90.0
            }

        # Questions related to career (10th house, sensitive to MC)
        career_asked = any("career" in a.get("question", "").lower() or "profession" in a.get("question", "").lower() for a in previous_answers)
        if not career_asked:
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "Describe your career path and how you chose your profession. Were there any major shifts in your career direction?",
                    "category": "career",
                    "relevance": "Career information helps determine 10th house and Midheaven placement, which are highly sensitive to birth time."
                },
                "confidence": 80.0
            }

        # Questions about relationships (7th house)
        relationships_asked = any("relationship" in a.get("question", "").lower() or "partner" in a.get("question", "").lower() for a in previous_answers)
        if not relationships_asked:
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "Describe your approach to significant relationships. What patterns have you noticed in your partnerships?",
                    "category": "relationships",
                    "relevance": "Relationship patterns help determine 7th house and descendant, which are sensitive to birth time."
                },
                "confidence": 75.0
            }

        # Health-related questions (6th house)
        health_asked = any("health" in a.get("question", "").lower() or "illness" in a.get("question", "").lower() for a in previous_answers)
        if not health_asked:
            return {
                "next_question": {
                    "id": question_id,
                    "type": "open_text",
                    "text": "Have you experienced any significant health challenges in your life? At what ages did these occur?",
                    "category": "health",
                    "relevance": "Health issues can correlate with 6th house and 8th house placements, which help with birth time rectification."
                },
                "confidence": 70.0
            }

        # Default fallback - ask about major life transitions
        return {
            "next_question": {
                "id": question_id,
                "type": "open_text",
                "text": "Describe the most significant turning points or transitions in your life. When did they occur and how did they change you?",
                "category": "life_events",
                "relevance": "Major transitions often correlate with outer planet transits to angles, which are highly sensitive to birth time."
            },
            "confidence": 65.0
        }

    async def submit_answer(
        self,
        session_id: str,
        question_id: str,
        answer: Any
    ) -> Dict[str, Any]:
        """
        Submit an answer to a question with deep astrological analysis.

        Args:
            session_id: Session identifier
            question_id: Question identifier
            answer: The answer data

        Returns:
            Dictionary with processing status and astrological insights
        """
        logger.info(f"Processing answer for question {question_id} in session {session_id}")

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

            # Get existing answers for context
            responses = await self.session_store.get_responses(session_id)

            # Get birth details from session for astrological context
            birth_details = session.get("birth_details", {})
            birth_date = birth_details.get("birth_date", "")
            birth_time = birth_details.get("birth_time", "")
            latitude = birth_details.get("latitude", 0.0)
            longitude = birth_details.get("longitude", 0.0)

            # Perform deep astrological analysis of the answer
            astrological_insights = await self._perform_astrological_analysis(
                question_text,
                answer,
                birth_date,
                birth_time,
                latitude,
                longitude
            )

            # Extract birth time indicators with enhanced astrological context
            birth_time_indicators = await self._extract_birth_time_indicators(question_text, answer)

            # Enhanced response object with astrological context
            response_analysis = {
                "answer_processed": True,
                "astrological_insights": astrological_insights
            }

            if birth_time_indicators:
                # Add the insights to our response
                response_analysis["birth_time_indicators"] = birth_time_indicators

                # Store the time indicators in the session
                session["birth_time_indicators"] = session.get("birth_time_indicators", []) + [birth_time_indicators]
                await self.session_store.update_session(session_id, session)

            # Calculate new confidence level with astrological weighting
            # Answers that provide clear time indicators get more weight
            base_confidence = 30.0
            answer_count_factor = len(responses) * 7.0
            astrological_factor = 0.0

            if birth_time_indicators and "astrological_factors" in birth_time_indicators:
                # Weight by the number of astrological factors identified
                factor_count = sum(len(factors) for factors in birth_time_indicators["astrological_factors"].values())
                astrological_factor = min(factor_count * 3.0, 15.0)

            confidence = min(95.0, base_confidence + answer_count_factor + astrological_factor)

            # Update session confidence
            await self.session_store.update_confidence(session_id, confidence)

            # Perform more sophisticated analysis for time range using all available answers
            if len(responses) >= 2:
                birth_time_range = await self._analyze_responses_for_time_range(responses)
                if birth_time_range:
                    # Update the session with the time range
                    session_data = await self.session_store.get_session(session_id)
                    if session_data is not None:
                        session_data["birth_time_range"] = birth_time_range
                        await self.session_store.update_session(session_id, session_data)

                        # Include range in response
                        response_analysis["birth_time_range"] = birth_time_range

            # Return enhanced response with astrological insights
            return {
                "status": "success",
                "session_id": session_id,
                "confidence": confidence,
                "message": "Answer processed successfully with astrological analysis",
                "analysis": response_analysis
            }
        except Exception as e:
            logger.error(f"Error processing answer with astrological analysis: {e}")
            return {
                "status": "error",
                "message": f"Failed to process answer: {str(e)}"
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
        Perform deep astrological analysis of an answer.

        Args:
            question: The question text
            answer: The answer provided
            birth_date: Birth date string
            birth_time: Birth time string
            latitude: Birth latitude
            longitude: Birth longitude

        Returns:
            Dictionary with astrological insights
        """
        # Default insights
        insights = {
            "houses_affected": [],
            "planets_affected": [],
            "possible_aspects": [],
            "analysis_confidence": 50.0
        }

        if not question or not answer:
            return insights

        # Convert answer to string if needed
        answer_text = str(answer) if not isinstance(answer, str) else answer
        question_lower = question.lower()
        answer_lower = answer_text.lower()

        # Use OpenAI for deeper analysis if available
        if self.openai_service:
            try:
                # Prepare data for analysis
                analysis_data = {
                    "question": question,
                    "answer": answer_text,
                    "birth_details": {
                        "date": birth_date,
                        "time": birth_time,
                        "latitude": latitude,
                        "longitude": longitude
                    },
                    "task": "analyze_for_birth_time_rectification"
                }

                # Get analysis from OpenAI
                response = await self.openai_service.generate_completion(
                    prompt=json.dumps(analysis_data),
                    task_type="astrological_analysis",
                    max_tokens=500
                )

                if response and "content" in response:
                    try:
                        # Parse the response
                        analysis_result = json.loads(response["content"])
                        if isinstance(analysis_result, dict):
                            # Merge with our insights
                            for key, value in analysis_result.items():
                                insights[key] = value

                            # Set higher confidence since we used AI
                            insights["analysis_confidence"] = 85.0
                            return insights
                    except json.JSONDecodeError:
                        logger.warning("Could not parse OpenAI astrological analysis as JSON")
            except Exception as e:
                logger.error(f"Error performing AI-assisted astrological analysis: {e}")

        # If OpenAI is not available or fails, use rule-based analysis

        # Map question categories to astrological houses
        house_keywords = {
            "personality": ["1st house", "Ascendant"],
            "childhood": ["4th house", "IC", "Moon"],
            "career": ["10th house", "Midheaven", "MC"],
            "relationships": ["7th house", "Descendant"],
            "health": ["6th house", "8th house"],
            "siblings": ["3rd house"],
            "education": ["9th house"],
            "finances": ["2nd house", "8th house"],
            "creativity": ["5th house"],
            "spirituality": ["12th house", "9th house"],
            "friends": ["11th house"]
        }

        # Map specific keywords to houses for deeper analysis
        keyword_house_mapping = {
            # 1st house / Ascendant keywords
            "appearance": "1st house",
            "identity": "1st house",
            "self-image": "1st house",
            "how others see me": "1st house",
            "first impression": "1st house",

            # 4th house / IC keywords
            "home": "4th house",
            "family": "4th house",
            "mother": "4th house",
            "roots": "4th house",
            "foundation": "4th house",
            "childhood home": "4th house",

            # 7th house / Descendant keywords
            "partner": "7th house",
            "marriage": "7th house",
            "relationship": "7th house",
            "spouse": "7th house",
            "collaboration": "7th house",

            # 10th house / Midheaven keywords
            "career": "10th house",
            "profession": "10th house",
            "job": "10th house",
            "vocation": "10th house",
            "public image": "10th house",
            "reputation": "10th house",
            "achievement": "10th house"
        }

        # Check for house-related keywords in the answer
        affected_houses = set()

        # Check category-based house associations
        for category, houses in house_keywords.items():
            if category in question_lower:
                affected_houses.update(houses)

        # Check specific keyword matches
        for keyword, house in keyword_house_mapping.items():
            if keyword in question_lower or keyword in answer_lower:
                affected_houses.add(house)

        # Check for planet-related keywords
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

        affected_planets = set()

        for planet, keywords in planet_keywords.items():
            if any(keyword in question_lower or keyword in answer_lower for keyword in keywords):
                affected_planets.add(planet)

        # Check for aspect-related patterns in the answer
        aspect_patterns = {
            "conjunction": ["together", "combined", "merged", "united", "joined"],
            "opposition": ["against", "opposite", "facing", "confrontation", "polarizing"],
            "trine": ["flowing", "ease", "effortless", "natural talent", "gift"],
            "square": ["challenge", "struggle", "tension", "obstacle", "difficulty"],
            "sextile": ["opportunity", "advantage", "help", "support", "chance"]
        }

        possible_aspects = []

        for aspect, patterns in aspect_patterns.items():
            if any(pattern in answer_lower for pattern in patterns):
                # If we've identified affected planets, suggest possible aspects between them
                if len(affected_planets) >= 2:
                    planets_list = list(affected_planets)
                    for i in range(len(planets_list)):
                        for j in range(i+1, len(planets_list)):
                            possible_aspects.append(f"{planets_list[i]} {aspect} {planets_list[j]}")
                else:
                    # Just note the aspect type
                    possible_aspects.append(aspect)

        # Update insights
        insights["houses_affected"] = list(affected_houses)
        insights["planets_affected"] = list(affected_planets)
        insights["possible_aspects"] = possible_aspects

        # Calculate confidence based on the number of identifications
        insight_points = len(affected_houses) + len(affected_planets) + len(possible_aspects)
        insights["analysis_confidence"] = min(80.0, 50.0 + (insight_points * 5.0))

        return insights

    async def _extract_birth_time_indicators(self, question: str, answer: Any) -> Optional[Dict[str, Any]]:
        """
        Extract indicators about birth time from the answer using astrological principles.

        Args:
            question: The question text
            answer: The answer provided by the user

        Returns:
            Dictionary with extracted indicators linked to astrological factors or None
        """
        # Skip processing if question or answer is invalid
        if not question or not answer:
            return None

        # Convert answer to string if needed
        answer_text = str(answer) if not isinstance(answer, str) else answer
        question_lower = question.lower()

        indicators = {}
        astrological_factors = {}

        # Extract explicit time mentions first
        time_pattern = re.compile(r'(\d{1,2}):(\d{2})\s*(am|pm)?', re.IGNORECASE)
        time_match = time_pattern.search(answer_text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            period = time_match.group(3)

            # Convert to 24-hour format if am/pm specified
            if period and period.lower() == 'pm' and hour < 12:
                hour += 12
            elif period and period.lower() == 'am' and hour == 12:
                hour = 0

            indicators["explicit_time"] = f"{hour:02d}:{minute:02d}"

            # Link to astrological houses
            if 5 <= hour < 8:
                astrological_factors["houses"] = ["12th house", "1st house"]
                astrological_factors["rising_signs"] = ["Pisces", "Aries"]
            elif 8 <= hour < 11:
                astrological_factors["houses"] = ["1st house", "2nd house"]
                astrological_factors["rising_signs"] = ["Aries", "Taurus"]
            elif 11 <= hour < 14:
                astrological_factors["houses"] = ["3rd house", "4th house"]
                astrological_factors["rising_signs"] = ["Gemini", "Cancer"]
            elif 14 <= hour < 17:
                astrological_factors["houses"] = ["5th house", "6th house"]
                astrological_factors["rising_signs"] = ["Leo", "Virgo"]
            elif 17 <= hour < 20:
                astrological_factors["houses"] = ["7th house", "8th house"]
                astrological_factors["rising_signs"] = ["Libra", "Scorpio"]
            elif 20 <= hour < 23:
                astrological_factors["houses"] = ["9th house", "10th house"]
                astrological_factors["rising_signs"] = ["Sagittarius", "Capricorn"]
            else:  # 23-5
                astrological_factors["houses"] = ["11th house", "12th house"]
                astrological_factors["rising_signs"] = ["Aquarius", "Pisces"]

        # Check for day/night indicators
        day_night_keywords = {
            "day": ["morning", "daylight", "afternoon", "daytime", "sunrise", "noon", "midday"],
            "night": ["evening", "night", "nighttime", "darkness", "sunset", "midnight", "late"]
        }

        for indicator, keywords in day_night_keywords.items():
            if any(keyword in answer_text.lower() for keyword in keywords):
                indicators["day_night"] = indicator

                # Link to astrological factors
                if indicator == "day":
                    astrological_factors["planets"] = ["Sun", "Jupiter", "Mercury"]
                    astrological_factors["houses"] = ["1st house", "9th house", "10th house"]
                else:  # night
                    astrological_factors["planets"] = ["Moon", "Venus", "Saturn"]
                    astrological_factors["houses"] = ["4th house", "12th house", "8th house"]

                break

        # Check personality traits that correlate with rising signs
        rising_sign_traits = {
            "Aries": ["assertive", "impulsive", "independent", "competitive", "direct", "leader"],
            "Taurus": ["patient", "reliable", "stubborn", "practical", "sensual", "persistent"],
            "Gemini": ["curious", "talkative", "adaptable", "versatile", "restless", "communicative"],
            "Cancer": ["emotional", "nurturing", "moody", "intuitive", "protective", "sensitive"],
            "Leo": ["confident", "proud", "dramatic", "loyal", "creative", "generous"],
            "Virgo": ["analytical", "critical", "precise", "practical", "methodical", "detail-oriented"],
            "Libra": ["diplomatic", "harmonious", "fair", "indecisive", "balanced", "social"],
            "Scorpio": ["intense", "secretive", "passionate", "mysterious", "powerful", "strategic"],
            "Sagittarius": ["optimistic", "philosophical", "adventurous", "blunt", "freedom-loving", "expansive"],
            "Capricorn": ["ambitious", "disciplined", "responsible", "cautious", "practical", "patient"],
            "Aquarius": ["innovative", "independent", "humanitarian", "detached", "inventive", "unique"],
            "Pisces": ["compassionate", "spiritual", "artistic", "intuitive", "dreamy", "empathetic"]
        }

        # Check for personality questions
        if "personality" in question_lower or "describe yourself" in question_lower:
            matched_signs = {}
            answer_lower = answer_text.lower()

            for sign, traits in rising_sign_traits.items():
                matched_traits = [trait for trait in traits if trait in answer_lower]
                if matched_traits:
                    matched_signs[sign] = len(matched_traits)

            # If we found matches, add the top 2 matches
            if matched_signs:
                sorted_signs = sorted(matched_signs.items(), key=lambda x: x[1], reverse=True)
                top_signs = [sign for sign, count in sorted_signs[:2]]
                indicators["personality_traits"] = top_signs
                astrological_factors["rising_signs"] = top_signs

        # Check for timeline events that correlate with transits and progressions
        age_pattern = re.compile(r'(at|when I was|around|about|age)\s+(\d{1,2})', re.IGNORECASE)
        age_match = age_pattern.search(answer_text)

        if age_match:
            try:
                age = int(age_match.group(2))
                indicators["significant_age"] = age

                # Convert age to astrological factors (Saturn return, Jupiter cycle, etc.)
                if 27 <= age <= 30:
                    astrological_factors["transits"] = ["Saturn return"]
                elif 11 <= age <= 13:
                    astrological_factors["transits"] = ["Jupiter return"]
                elif 18 <= age <= 19:
                    astrological_factors["transits"] = ["Nodal return"]
                elif 7 <= age <= 8:
                    astrological_factors["transits"] = ["Saturn square"]
                elif 14 <= age <= 16:
                    astrological_factors["transits"] = ["Saturn opposition"]
                elif 35 <= age <= 37:
                    astrological_factors["transits"] = ["Uranus square"]
                elif 38 <= age <= 42:
                    astrological_factors["transits"] = ["Uranus opposition"]
                elif 21 <= age <= 22:
                    astrological_factors["transits"] = ["Jupiter square"]
            except (ValueError, IndexError):
                pass

        # Check for early/late indicators
        early_late_keywords = {
            "early": ["ahead of schedule", "early", "before expected", "premature", "sooner than"],
            "on time": ["on time", "as expected", "right on schedule", "punctual"],
            "late": ["delayed", "late", "after expected", "overdue", "longer than"]
        }

        for indicator, keywords in early_late_keywords.items():
            if any(keyword in answer_text.lower() for keyword in keywords):
                indicators["timing"] = indicator

                # Link to astrological factors
                if indicator == "early":
                    astrological_factors["planets"] = ["Mercury", "Uranus", "Mars"]
                elif indicator == "on time":
                    astrological_factors["planets"] = ["Saturn", "Mercury", "Sun"]
                else:  # late
                    astrological_factors["planets"] = ["Neptune", "Saturn", "Venus"]

                break

        # If we found indicators and have astrological factors, include them
        if indicators and astrological_factors:
            result = {
                "indicators": indicators,
                "astrological_factors": astrological_factors,
                "question": question,
                "answer": answer_text,
                "extracted_at": datetime.now().isoformat()
            }
            return result

        # If we have indicators but no astrological factors, return basic result
        if indicators:
            return {
                "indicators": indicators,
                "question": question,
                "answer": answer_text,
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

    async def complete_questionnaire(
        self,
        session_id: str,
        chart_id: str
    ) -> Dict[str, Any]:
        """
        Complete a questionnaire and initiate birth time rectification with comprehensive astrological analysis.

        Args:
            session_id: Session identifier
            chart_id: Chart identifier

        Returns:
            Dictionary with detailed astrological analysis and rectification status
        """
        logger.info(f"Completing questionnaire for session {session_id}, chart {chart_id}")

        try:
            # Verify session exists
            session = await self.session_store.get_session(session_id)
            if not session:
                return {
                    "status": "error",
                    "message": f"Session {session_id} not found"
                }

            # Get responses
            responses = await self.session_store.get_responses(session_id)
            if not responses or len(responses) == 0:
                return {
                    "status": "error",
                    "message": "No responses found in session"
                }

            # Get birth details for astrological context
            birth_details = session.get("birth_details", {})
            birth_date = birth_details.get("birth_date", "")
            birth_time = birth_details.get("birth_time", "")
            latitude = birth_details.get("latitude", 0.0)
            longitude = birth_details.get("longitude", 0.0)
            timezone = birth_details.get("timezone", "UTC")

            # Get confidence score
            confidence = await self.session_store.get_confidence(session_id)

            # Get any birth time indicators extracted from responses
            birth_time_indicators = session.get("birth_time_indicators", [])

            # Get birth time range if available
            birth_time_range = session.get("birth_time_range")

            # Categorize responses by topic for comprehensive analysis
            categorized_responses = self._categorize_responses(responses)

            # Perform comprehensive analysis of all answers collectively
            comprehensive_analysis = await self._perform_comprehensive_analysis(
                responses=responses,
                birth_details=birth_details,
                birth_time_indicators=birth_time_indicators
            )

            # Extract astrologically significant life events
            life_events = self._extract_astrological_life_events(responses)

            # Calculate overall birth time quality assessment
            time_quality = self._assess_birth_time_quality(comprehensive_analysis, birth_time_indicators)

            # Determine astrologically significant periods for the native
            significant_periods = self._calculate_significant_periods(birth_date, birth_time, timezone)

            # Prepare summary data for rectification with enhanced astrological context
            summary_data = {
                "session_id": session_id,
                "chart_id": chart_id,
                "confidence": confidence,
                "birth_time_indicators": birth_time_indicators,
                "birth_time_range": birth_time_range,
                "response_categories": list(categorized_responses.keys()),
                "response_count": len(responses),
                "comprehensive_analysis": comprehensive_analysis,
                "identified_life_events": life_events,
                "birth_time_quality": time_quality,
                "significant_periods": significant_periods
            }

            # Mark session as complete with enhanced data
            session["status"] = "complete"
            session["completed_at"] = datetime.now().isoformat()
            session["summary"] = summary_data
            await self.session_store.update_session(session_id, session)

            # Initiate rectification process with enhanced context
            from ai_service.api.routers.questionnaire import process_rectification
            rectification_task = asyncio.create_task(process_rectification(chart_id, session_id, responses))

            # Monitor task creation
            if rectification_task:
                logger.info(f"Enhanced rectification process started for chart {chart_id}, session {session_id}")
            else:
                logger.warning(f"May have failed to start rectification process for chart {chart_id}")

            # Return success with detailed astrological analysis
            return {
                "status": "success",
                "session_id": session_id,
                "chart_id": chart_id,
                "confidence": confidence,
                "response_count": len(responses),
                "key_indicators": self._extract_key_indicators(birth_time_indicators),
                "comprehensive_analysis": {
                    "summary": comprehensive_analysis["summary"],
                    "birth_time_quality": time_quality,
                    "astrological_factors": comprehensive_analysis["astrological_factors"],
                    "identified_patterns": comprehensive_analysis["identified_patterns"]
                },
                "birth_time_range": birth_time_range,
                "significant_life_events": life_events[:5] if len(life_events) > 5 else life_events,
                "significant_periods": significant_periods[:3] if len(significant_periods) > 3 else significant_periods,
                "message": "Questionnaire completed with comprehensive astrological analysis. Birth time rectification has been started.",
                "estimated_completion_time": "30-60 seconds",
                "next_steps": [
                    "The rectification process is now analyzing your answers using multiple astrological techniques",
                    "Transit analysis is being performed on your identified life events",
                    "The system is calculating potential birth time candidates based on house cusps and planetary positions",
                    "You can check the status using the /api/questionnaire/check-rectification endpoint",
                    "When complete, you will have access to your rectified birth chart with detailed analysis"
                ]
            }
        except Exception as e:
            logger.error(f"Error completing questionnaire: {e}")
            return {
                "status": "error",
                "message": f"Failed to complete questionnaire: {str(e)}"
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
