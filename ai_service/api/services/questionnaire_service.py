"""
Unified Questionnaire Service for Birth Time Rectification.

This module provides a comprehensive service for generating, processing, and analyzing
astrologically-relevant questions used for birth time rectification.
"""

import logging
import json
import uuid
import re
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, cast
import traceback

# Import service dependencies
from ai_service.api.services.openai import get_openai_service
from ai_service.api.services.session_service import get_session_store, SessionStore
from ai_service.utils.dependency_container import get_container

# Configure logging
logger = logging.getLogger(__name__)

# Define exports
__all__ = ["QuestionnaireService", "get_questionnaire_service"]

# Constants for questions
QUESTION_CATEGORIES = [
    "life_events",
    "personality",
    "relationships",
    "career",
    "health",
    "spirituality",
    "physical_appearance",
    "education"
]

def get_chart_service():
    """Get the chart service instance."""
    logger.warning("Using placeholder chart service")
    # Return a placeholder service that returns empty data
    class ChartServicePlaceholder:
        async def get_chart(self, chart_id: str) -> Dict[str, Any]:
            logger.warning(f"Using placeholder chart service for ID: {chart_id}")
            # Return a minimal chart data structure with some placeholder planets and houses
            return {
                "planets": {
                    "Sun": {"sign": "Aries", "house": 1},
                    "Moon": {"sign": "Taurus", "house": 2},
                    "Mercury": {"sign": "Gemini", "house": 3}
                },
                "houses": {
                    "1": {"sign": "Aries"},
                    "7": {"sign": "Libra"},
                    "10": {"sign": "Capricorn"}
                },
                "aspects": [
                    {"aspect_type": "conjunction", "planet1": "Sun", "planet2": "Mercury"}
                ]
            }
    return ChartServicePlaceholder()

class QuestionnaireService:
    """
    Unified service for managing birth time rectification questionnaires.

    This service handles the generation, processing, and analysis of questions
    used for birth time rectification.
    """

    def __init__(self, openai_service: Optional[Any] = None):
        """
        Initialize the questionnaire service.

        Args:
            openai_service: Optional OpenAI service for AI-powered question generation
        """
        self.openai_service = openai_service
        self.session_service = cast(SessionStore, get_session_store())

        logger.info("QuestionnaireService initialized")

    async def get_initial_questions(self, chart_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get initial set of questions for the rectification process.

        Args:
            chart_data: Optional chart data to personalize questions

        Returns:
            List of question dictionaries

        Raises:
            RuntimeError: If real-time question generation fails
        """
        try:
            # Generate initial questions based on chart data
            birth_details = None
            if chart_data and "birth_details" in chart_data:
                birth_details = chart_data.get("birth_details", {})

            # Generate an initial question
            question = await self._generate_astrologically_relevant_question(
                birth_details=birth_details or {},
                previous_answers=[]
            )

            # Return as a list for backward compatibility
            return [question]

        except Exception as e:
            logger.error("Error getting initial questions: %s", e)
            logger.error(traceback.format_exc())
            # Do not provide fallback questions - real-time generation is required
            raise RuntimeError(f"Failed to generate real-time personalized question: {str(e)}") from e

    async def generate_next_question(
        self,
        birth_details: Dict[str, Any],
        previous_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate the next question based on birth details and previous answers.

        Args:
            birth_details: Birth details dictionary
            previous_answers: List of previous answers

        Returns:
            A dictionary containing the next question
        """
        logger.info(f"Generating next question with {len(previous_answers)} previous answers")

        # Get chart data if available
        chart_id = birth_details.get("chart_id")
        chart_data = {}

        if chart_id:
            # Get chart service
            chart_service = get_chart_service()
            try:
                chart_data = await chart_service.get_chart(chart_id)
                logger.info(f"Retrieved chart data for chart ID {chart_id}")
            except Exception as e:
                logger.error(f"Error retrieving chart data: {str(e)}")
                # Continue with empty chart data

        # Use session_id if available, otherwise generate a temporary one
        session_id = birth_details.get("session_id", f"temp_{uuid.uuid4().hex[:8]}")

        try:
            if not previous_answers:
                # For the first question, use a standard birth time question
                return {
                    "id": f"q_first_{uuid.uuid4().hex[:8]}",
                    "text": "Do you know your approximate birth time?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "opt_exact", "text": "Yes, I have an exact time"},
                        {"id": "opt_approximate", "text": "I have an approximate time"},
                        {"id": "opt_window", "text": "I know a time window (e.g., morning, afternoon)"},
                        {"id": "opt_unknown", "text": "I don't know my birth time"}
                    ],
                    "category": "birth_time"
                }
            else:
                # For subsequent questions, generate a question based on the API integration
                # Try to get the OpenAI service for AI-driven question generation
                try:
                    openai_service = await get_openai_service()
                    if openai_service:
                        # Generate a question with OpenAI
                        return await self._generate_astrologically_relevant_question(birth_details, previous_answers)
                except Exception as e:
                    logger.error(f"Error with OpenAI service: {e}")

                # Fallback questions if OpenAI fails
                fallback_questions = [
                    {
                        "id": f"q_fallback_{uuid.uuid4().hex[:8]}",
                        "text": "Please describe any major life events that occurred during your childhood.",
                        "type": "text",
                        "category": "life_events"
                    },
                    {
                        "id": f"q_fallback_{uuid.uuid4().hex[:8]}",
                        "text": "What time of day do you feel most energetic?",
                        "type": "multiple_choice",
                        "options": [
                            {"id": "opt_morning", "text": "Morning"},
                            {"id": "opt_afternoon", "text": "Afternoon"},
                            {"id": "opt_evening", "text": "Evening"},
                            {"id": "opt_night", "text": "Night"}
                        ],
                        "category": "timing_preferences"
                    }
                ]

                # Return a random fallback question
                question = random.choice(fallback_questions)
                logger.info(f"Using fallback question: {question['text']}")
                return question

        except Exception as e:
            logger.error(f"Error generating next question: {str(e)}")
            raise RuntimeError(f"Failed to generate personalized question: {str(e)}") from e

    async def submit_answer(
        self,
        session_id: str,
        question_id: str,
        answer: Any
    ) -> Dict[str, Any]:
        """
        Submit an answer for a questionnaire question.

        Args:
            session_id: The session ID
            question_id: The ID of the question being answered
            answer: The answer to the question

        Returns:
            Dictionary with answer submission results
        """
        try:
            # Get session data
            session_data = await self.session_service.get_session(session_id)
            if not session_data:
                raise ValueError(f"Invalid session ID: {session_id}")

            # Find the question text for context
            if "data" not in session_data:
                session_data["data"] = {}

            questions = session_data["data"].get("questions", [])
            last_question = next((q.get("text") for q in questions if q.get("id") == question_id), None)

            # Create or get answers list
            if "answers" not in session_data["data"]:
                session_data["data"]["answers"] = []

            # Add the answer
            session_data["data"]["answers"].append({
                "question_id": question_id,
                "question_text": last_question or f"Question {question_id}",
                "answer": answer,
                "timestamp": datetime.now().isoformat()
            })

            # Update current question index
            current_index = session_data["data"].get("current_question_index", 0)
            session_data["data"]["current_question_index"] = current_index + 1

            # Save the session
            await self.session_service.update_session(session_id, session_data)

            # Extract birth details for next question generation
            chart_data = session_data["data"].get("chart_data", {})
            birth_details = chart_data.get("birth_details", {})

            # Calculate confidence
            answers = session_data["data"].get("answers", [])
            confidence = await self._calculate_confidence(answers)

            return {
                "success": True,
                "confidence": confidence,
                "question_index": current_index + 1,
                "birth_details": birth_details
            }
        except Exception as e:
            logger.error("Error submitting answer: %s", e)
            raise

    async def complete_questionnaire(self, session_id: str, chart_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete the current questionnaire and generate rectification analysis.

        Args:
            session_id: The session ID
            chart_id: Optional chart ID (will use one from session if not provided)

        Returns:
            Dictionary with completion results
        """
        try:
            # Get session data to retrieve previous answers
            session_data = await self.session_service.get_session(session_id)
            if not session_data:
                raise ValueError(f"Invalid session ID: {session_id}")

            # Use provided chart_id or get from session
            chart_id = chart_id or session_data.get("data", {}).get("chart_id")
            if not chart_id:
                raise ValueError("No chart ID available for rectification")

            # Extract answers from session
            session_content = session_data.get("data", {})
            answers = session_content.get("answers", [])
            if not answers:
                raise ValueError("No answers available for analysis")

            # Calculate rectification confidence based on answers
            try:
                confidence = await self._calculate_confidence(answers)
            except Exception as conf_error:
                # Log error but continue with default confidence
                logger.error("Error calculating confidence: %s", conf_error)
                confidence = 50.0

            # Generate final analysis
            analysis_data = {
                "session_id": session_id,
                "chart_id": chart_id,
                "completed_at": datetime.now().isoformat(),
                "confidence": confidence,
                "answers_count": len(answers),
                "analysis": "Questionnaire completed successfully"
            }

            # Store analysis results in session
            session_update = {
                "final_analysis": analysis_data,
                "questionnaire_status": "completed",
                "confidence": confidence
            }

            # Non-awaitable update_session
            await self.session_service.update_session(session_id, session_update)

            # Return analysis data with completed status
            return {
                "completed": True,
                "chart_id": chart_id,
                "confidence": confidence,
                "session_id": session_id,
                "analysis": analysis_data
            }
        except Exception as e:
            logger.error("Error completing questionnaire: %s", e)

            # Provide a meaningful error response
            return {
                "session_id": session_id,
                "chart_id": chart_id,
                "status": "error",
                "message": f"Failed to complete questionnaire: {str(e)}",
                "confidence": 0.0
            }

    async def _calculate_confidence(self, answers: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence based on answers provided.

        Args:
            answers: List of answers

        Returns:
            Confidence score (0-100)
        """
        try:
            # Base confidence starts at 10%
            base_confidence = 10.0

            # Each answer increases confidence up to a cap
            answer_count = len(answers)
            answer_contribution = min(60.0, answer_count * 5.0)

            # Questions about exact times contribute more
            time_related_answers = 0
            for answer in answers:
                question_text = answer.get("question_text", "").lower()
                if "time" in question_text or "hour" in question_text or "morning" in question_text or "evening" in question_text:
                    time_related_answers += 1

            time_contribution = min(30.0, time_related_answers * 7.5)

            # Calculate and return total confidence, never exceeding 100%
            total_confidence = min(100.0, base_confidence + answer_contribution + time_contribution)
            return total_confidence
        except Exception as conf_error:
            logger.error("Error calculating confidence: %s", conf_error)
            return 10.0  # Default minimal confidence

    async def _generate_astrologically_relevant_question(
        self,
        birth_details: Dict[str, Any],
        previous_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an astrologically relevant question based on birth details.

        Args:
            birth_details: Birth details including chart data
            previous_answers: Previous answers to questions

        Returns:
            Question data

        Raises:
            Exception: If question generation fails
        """
        # Get chart data if available
        chart_id = birth_details.get("chart_id")
        chart_data = birth_details.get("chart_data", {})

        if chart_id and not chart_data:
            # Get chart service
            chart_service = get_chart_service()
            try:
                chart_data = await chart_service.get_chart(chart_id)
                logger.info(f"Retrieved chart data for chart ID {chart_id}")
                # Update birth_details with chart data
                birth_details["chart_data"] = chart_data
            except Exception as e:
                logger.error(f"Error retrieving chart data: {str(e)}")
                # Cannot proceed without chart data
                raise ValueError(f"Chart not found: {chart_id}") from e

        try:
            # Create a prompt for OpenAI
            prompt = self._create_question_generation_prompt(
                previous_answers=previous_answers,
                birth_details=birth_details
            )

            # Call OpenAI to generate a question
            logger.info("Calling OpenAI to generate real-time personalized question")
            if not self.openai_service:
                self.openai_service = await get_openai_service()
                if not self.openai_service:
                    raise ValueError("OpenAI service is not available")

            response = await self.openai_service.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert Vedic astrologer specializing in birth time rectification."},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-4o",
                temperature=0.7,
                max_tokens=300
            )

            # Make sure we have a valid response
            if not response:
                raise ValueError("Empty response from OpenAI")

            # Extract content from the response
            if isinstance(response, dict) and "choices" in response and response["choices"]:
                content = response["choices"][0]["message"]["content"]
            else:
                raise ValueError("Invalid response format from OpenAI")

            # Extract JSON from the response
            question_data = self._extract_json_from_content(content)

            # Validate question data
            if not question_data or "text" not in question_data:
                logger.error("OpenAI response did not contain a valid question")
                raise ValueError("Failed to generate a valid question from OpenAI response")

            # Ensure question has an ID
            if "id" not in question_data:
                question_data["id"] = f"q_openai_{uuid.uuid4().hex[:8]}"

            # Ensure question has a type
            if "type" not in question_data:
                question_data["type"] = "text"

            if question_data and "text" in question_data:
                logger.info(f"Successfully generated personalized question: {question_data['text'][:50]}...")
            else:
                logger.info("Generated question data without text field")

            return question_data

        except Exception as e:
            logger.error("Error generating astrological question: %s", e)
            logger.error(traceback.format_exc())

            # No fallback questions - raise an exception to ensure real-time generation
            raise RuntimeError(f"Failed to generate real-time personalized question: {str(e)}") from e

    def _create_question_generation_prompt(
        self,
        previous_answers: List[Dict[str, Any]],
        birth_details: Dict[str, Any]
    ) -> str:
        """
        Create prompt for dynamic question generation.

        Args:
            previous_answers: Previous answers
            birth_details: Birth details including chart data

        Returns:
            Formatted prompt
        """
        # Extract chart data for astrological context
        chart_data = birth_details.get("chart_data", {})

        # Format chart data for the prompt
        chart_summary = ""
        if chart_data:
            # Extract planets
            planets = chart_data.get("planets", {})
            if planets:
                chart_summary += "PLANETS:\n"
                for planet, data in planets.items():
                    if isinstance(data, dict):
                        sign = data.get("sign", "Unknown")
                        house = data.get("house", "Unknown")
                        degree = data.get("longitude", 0) % 30
                        chart_summary += f"- {planet} in {sign} {degree:.1f}° (House {house})\n"

            # Extract houses
            houses = chart_data.get("houses", {})
            if houses:
                chart_summary += "\nHOUSES:\n"
                for house_num, data in houses.items():
                    if isinstance(data, dict):
                        sign = data.get("sign", "Unknown")
                        degree = data.get("cusp", 0)
                        chart_summary += f"- House {house_num}: {sign} {degree:.1f}°\n"

            # Extract aspects
            aspects = chart_data.get("aspects", [])
            if aspects:
                chart_summary += "\nKEY ASPECTS:\n"
                for aspect in aspects[:5]:  # Limit to 5 most significant aspects
                    if isinstance(aspect, dict):
                        p1 = aspect.get("planet1", "Unknown")
                        p2 = aspect.get("planet2", "Unknown")
                        type = aspect.get("type", "Unknown")
                        chart_summary += f"- {p1} {type} {p2}\n"

            # Extract ascendant and midheaven
            asc = chart_data.get("ascendant", {})
            if asc:
                chart_summary += f"\nASCENDANT: {asc.get('sign', 'Unknown')} {asc.get('degree', 0):.1f}°\n"

            mc = chart_data.get("midheaven", {})
            if mc:
                chart_summary += f"MIDHEAVEN: {mc.get('sign', 'Unknown')} {mc.get('degree', 0):.1f}°\n"

        # Add basic birth info
        if "birth_date" in birth_details:
            chart_summary += f"\nBIRTH DATE: {birth_details.get('birth_date')}\n"
        if "birth_time" in birth_details:
            chart_summary += f"BIRTH TIME: {birth_details.get('birth_time')}\n"
        if "place_name" in birth_details:
            chart_summary += f"BIRTH PLACE: {birth_details.get('place_name')}\n"

        # Format previous answers
        qa_history = ""
        if previous_answers:
            qa_history = "PREVIOUS QUESTIONS AND ANSWERS:\n"
            for i, answer in enumerate(previous_answers):
                q_text = answer.get("question", "Unknown question")
                a_text = answer.get("answer", "Unknown answer")
                qa_history += f"Q{i+1}: {q_text}\nA{i+1}: {a_text}\n\n"

        # Track categories already covered
        categories_covered = set()
        for answer in previous_answers:
            category = answer.get("category")
            if category:
                categories_covered.add(category)

        # Create system prompt
        system_prompt = """You are an expert Vedic astrologer specializing in birth time rectification.
Generate a question to help determine the exact birth time based on the individual's birth chart and previous responses.

Your question should follow these requirements:
1. It must be personalized to this individual's specific birth chart (not generic)
2. It must relate to astrological indicators present in their chart
3. It must be different from all previous questions
4. It should help pinpoint one of these areas to assist with birth time rectification:
   - Physical appearance or characteristics connected to Ascendant
   - Personality traits linked to Ascendant, Sun, Moon positions
   - Major life events and their timing
   - Career/profession resonant with the 10th house/Midheaven
   - Relationship patterns affected by 7th house, Venus, Moon
   - Health patterns related to the 6th house, Mars, Saturn

Return ONLY a JSON object with the question formatted like this:
{
  "id": "q_unique_id",
  "text": "Your unique, personalized question here based on their chart",
  "type": "multiple_choice",
  "options": [
     {"id": "opt_1", "text": "Option 1"},
     {"id": "opt_2", "text": "Option 2"},
     {"id": "opt_3", "text": "Option 3"},
     {"id": "opt_4", "text": "Option 4"}
  ],
  "category": "relevant_category"
}

OR, for open-ended questions:
{
  "id": "q_unique_id",
  "text": "Your unique, personalized question here based on their chart",
  "type": "text",
  "category": "relevant_category"
}"""

        # Build the actual prompt for the user
        prompt = f"""BIRTH CHART DATA:
{chart_summary}

{qa_history}

Categories already covered: {", ".join(categories_covered) if categories_covered else "None yet"}

Generate a single, highly personalized question based on this individual's birth chart that will help determine their exact birth time.
Make the question specific to the placements in their chart, not generic.
Focus particularly on aspects that would change with small shifts in birth time (Ascendant, house cusps, Midheaven).

Return ONLY a valid JSON object with the question.
"""

        return f"{system_prompt}\n\n{prompt}"

    def _create_final_analysis_prompt(
        self,
        answers: List[Dict[str, Any]],
        birth_details: Dict[str, Any]
    ) -> str:
        """
        Create prompt for final comprehensive analysis.

        Args:
            answers: List of all questionnaire answers
            birth_details: Dictionary with birth details

        Returns:
            Formatted prompt string
        """
        # Format all answers
        formatted_answers = "\n".join([
            f"Q: {a.get('question', a.get('question_text', 'Unknown question'))}\nA: {a.get('answer', 'No answer')}"
            for a in answers
        ])

        # Create birth details section
        birth_date = birth_details.get('birth_date', birth_details.get('birthDate', 'Unknown'))
        birth_time = birth_details.get('birth_time', birth_details.get('birthTime', 'Unknown'))
        birth_place = birth_details.get('birth_place', birth_details.get('birthPlace', 'Unknown'))
        latitude = birth_details.get('latitude', 'Unknown')
        longitude = birth_details.get('longitude', 'Unknown')

        birth_context = f"""
Birth Date: {birth_date}
Approximate Birth Time: {birth_time}
Location: {birth_place}
Latitude: {latitude}
Longitude: {longitude}
        """

        return f"""
You are an expert astrologer specializing in birth time rectification. Perform a comprehensive analysis of all questionnaire responses to determine the most likely birth time.

{birth_context}

All Questions and Answers:
{formatted_answers}

Provide a comprehensive birth time rectification analysis with the following elements:
1. Identify all birth time indicators from the responses
2. Determine the most likely ascendant/rising sign
3. Determine the most likely MC/10th house placement
4. Estimate the most likely birth time or time range
5. Assign a confidence level to your rectification (0-100)

Your response should be in this JSON format:
{{
  "birth_time_indicators": [
    {{
      "indicator": "Description of indicator",
      "astrological_factor": "Related astrological factor (Ascendant, MC, etc.)",
      "potential_time_range": "Potential birth time range",
      "confidence": 0-100
    }}
  ],
  "summary": "Overall summary of birth time analysis",
  "confidence": 0-100,
  "estimated_time": "HH:MM",
  "estimated_time_range": "HH:MM-HH:MM",
  "recommendations": [
    "Specific recommendations for further verification",
    "Additional questions that might help clarify birth time"
  ]
}}
"""

    def _extract_time_indicators(self, previous_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract birth time indicators from questionnaire answers.

        Args:
            previous_answers: List of previous answers

        Returns:
            Dictionary of time indicators
        """
        time_indicators = {
            "morning": 0,
            "afternoon": 0,
            "evening": 0,
            "night": 0,
            "specific_time_mentions": [],
            "confidence": 0.0,
            "narrowed_range": None
        }

        # Process each answer for time indicators
        for answer in previous_answers:
            answer_text = answer.get("answer", "")

            if isinstance(answer_text, dict):
                answer_text = json.dumps(answer_text)
            elif not isinstance(answer_text, str):
                answer_text = str(answer_text)

            # Look for time of day mentions
            if "morning" in answer_text.lower():
                time_indicators["morning"] += 1
            if "afternoon" in answer_text.lower():
                time_indicators["afternoon"] += 1
            if "evening" in answer_text.lower():
                time_indicators["evening"] += 1
            if "night" in answer_text.lower() or "midnight" in answer_text.lower():
                time_indicators["night"] += 1

            # Look for specific time mentions (HH:MM or X o'clock)
            time_patterns = [
                r'(\d{1,2})\s*:\s*(\d{2})\s*(am|pm)?',
                r'(\d{1,2})\s*o\'?clock\s*(am|pm)?'
            ]

            for pattern in time_patterns:
                matches = re.finditer(pattern, answer_text.lower())
                for match in matches:
                    time_indicators["specific_time_mentions"].append(match.group(0))

        # Calculate confidence based on indicators
        total_time_mentions = (
            time_indicators["morning"] +
            time_indicators["afternoon"] +
            time_indicators["evening"] +
            time_indicators["night"] +
            len(time_indicators["specific_time_mentions"])
        )

        # Set confidence level
        if total_time_mentions > 5:
            time_indicators["confidence"] = 0.8
        elif total_time_mentions > 3:
            time_indicators["confidence"] = 0.6
        elif total_time_mentions > 1:
            time_indicators["confidence"] = 0.4
        else:
            time_indicators["confidence"] = 0.2

        # Determine narrowed time range if possible
        if time_indicators["morning"] > time_indicators["afternoon"] and time_indicators["morning"] > time_indicators["evening"] and time_indicators["morning"] > time_indicators["night"]:
            time_indicators["narrowed_range"] = "06:00-12:00"
        elif time_indicators["afternoon"] > time_indicators["morning"] and time_indicators["afternoon"] > time_indicators["evening"] and time_indicators["afternoon"] > time_indicators["night"]:
            time_indicators["narrowed_range"] = "12:00-18:00"
        elif time_indicators["evening"] > time_indicators["morning"] and time_indicators["evening"] > time_indicators["afternoon"] and time_indicators["evening"] > time_indicators["night"]:
            time_indicators["narrowed_range"] = "18:00-22:00"
        elif time_indicators["night"] > time_indicators["morning"] and time_indicators["night"] > time_indicators["afternoon"] and time_indicators["night"] > time_indicators["evening"]:
            time_indicators["narrowed_range"] = "22:00-06:00"

        # Use specific time mentions to further narrow the range if available
        if time_indicators["specific_time_mentions"]:
            # Future enhancement: Implement more sophisticated time range narrowing
            pass

        return time_indicators

    def _extract_json_from_content(self, content: Optional[str]) -> Dict[str, Any]:
        """
        Extract JSON from OpenAI response content.

        Args:
            content: Text content from OpenAI (may be None)

        Returns:
            Extracted JSON data
        """
        try:
            # Handle None content
            if content is None:
                logger.warning("Received None content to extract JSON from")
                return {}

            # Try direct JSON parsing first
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON using regex patterns
                patterns = [
                    r'```json\s*([\s\S]*?)\s*```',  # JSON in code block
                    r'```\s*([\s\S]*?)\s*```',      # Any code block
                    r'(\{[\s\S]*\})'                # Any JSON-like structure
                ]

                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        json_str = match.group(1)
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            # Continue trying other patterns
                            continue

            # No successful JSON extraction, return empty dict
            logger.warning("Could not extract JSON from OpenAI response")
            return {}

        except Exception as e:
            logger.error(f"Error extracting JSON from content: {str(e)}")
            return {}

    def _generate_alternative_question(
        self,
        birth_details: Dict[str, Any],
        previous_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an alternative question when OpenAI generation fails.

        Args:
            birth_details: Birth details to use for personalization
            previous_answers: Previous answers to avoid repetition

        Returns:
            Dictionary with question details
        """
        # Get question categories that haven't been asked yet
        asked_categories = set(a.get("category", "unknown") for a in previous_answers if "category" in a)
        available_categories = ["life_events", "relationships", "career", "health", "spirituality", "education", "personality"]
        unused_categories = [c for c in available_categories if c not in asked_categories]

        # If all categories used, pick a random one
        category = random.choice(unused_categories) if unused_categories else random.choice(available_categories)

        # Generate question based on category
        question_id = f"q_{uuid.uuid4().hex[:8]}"

        # Personalize question if birth details are available
        birth_year = None
        if birth_details and "birth_date" in birth_details:
            try:
                birth_year = int(birth_details["birth_date"].split("-")[0])
            except (ValueError, IndexError, AttributeError, KeyError):
                pass

        if category == "life_events":
            if birth_year:
                ages = [7, 14, 21, 28]
                years = [str(birth_year + age) for age in ages]
                return {
                    "id": question_id,
                    "text": f"Describe any significant life events that occurred around ages 7, 14, 21, or 28 (years {', '.join(years)}).",
                    "type": "text",
                    "category": "life_events",
                    "relevance": "high"
                }

            return {
                "id": question_id,
                "text": "Describe any significant life events that occurred at ages 7, 14, 21, or 28.",
                "type": "text",
                "category": "life_events",
                "relevance": "high"
            }

        if category == "relationships":
            return {
                "id": question_id,
                "text": "When did you meet your current partner or experience a significant relationship milestone?",
                "type": "text",
                "category": "relationships",
                "relevance": "medium"
            }

        if category == "career":
            return {
                "id": question_id,
                "text": "What age or date did you start your most significant job or career path?",
                "type": "text",
                "category": "career",
                "relevance": "medium"
            }

        if category == "health":
            return {
                "id": question_id,
                "text": "Have you experienced any significant health events? If so, when did they occur?",
                "type": "text",
                "category": "health",
                "relevance": "high"
            }

        if category == "spirituality":
            return {
                "id": question_id,
                "text": "Have you had any spiritual awakening or transformation? When did this occur?",
                "type": "text",
                "category": "spirituality",
                "relevance": "medium"
            }

        if category == "personality":
            return {
                "id": question_id,
                "text": "Would you describe yourself as more introverted or extroverted? How has this manifested in your life?",
                "type": "multiple_choice",
                "options": [
                    {"id": "introvert", "text": "Definitely introverted"},
                    {"id": "somewhat_introvert", "text": "Somewhat introverted"},
                    {"id": "balanced", "text": "Balanced between both"},
                    {"id": "somewhat_extrovert", "text": "Somewhat extroverted"},
                    {"id": "extrovert", "text": "Definitely extroverted"}
                ],
                "category": "personality",
                "relevance": "Ascendant"
            }

        # education or default
        return {
            "id": question_id,
            "text": "When did you complete your education or training for your profession?",
            "type": "text",
            "category": "education",
            "relevance": "medium"
        }

    async def initialize_questionnaire(
        self,
        chart_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Initialize a new questionnaire session.

        Args:
            chart_id: The chart ID to associate with the questionnaire
            session_id: The session ID for tracking

        Returns:
            Dictionary with questionnaire initialization data
        """
        try:
            # Get session data
            session_data = await self.session_service.get_session(session_id)
            if not session_data:
                session_data = {"data": {}}

            # Store the chart ID in the session
            session_data["data"]["chart_id"] = chart_id

            # Store questionnaire data in session
            session_data["data"]["questionnaire"] = {
                "chart_id": chart_id,
                "questions_asked": [],
                "answers": {},
                "confidence": 0.0,
                "progress": 0.0,
                "status": "initialized",
                "initialized_at": datetime.now().isoformat()
            }

            # Save session data
            await self.session_service.update_session(session_id, session_data)

            # Get the first question
            first_question = await self._get_first_question({"chart_id": chart_id})

            # Store the current question
            session_data["data"]["questionnaire"]["current_question"] = first_question
            await self.session_service.update_session(session_id, session_data)

            # Return the session information with first question
            return {
                "session_id": session_id,
                "chart_id": chart_id,
                "question": first_question,
                "confidence": 0.0,
                "progress": 0.1  # Starting progress
            }

        except Exception as e:
            logger.error("Error in initialize_questionnaire: %s", e)
            logger.error(traceback.format_exc())
            raise ValueError(f"Failed to initialize questionnaire: {str(e)}") from e

    async def _get_first_question(self, birth_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the first question for the questionnaire.

        Args:
            birth_details: Birth details including date, time, and location

        Returns:
            Dict containing question details
        """
        try:
            # Always start with a question about birth time confidence
            return {
                "id": "q_birth_time_general",
                "text": "Do you know your approximate birth time?",
                "type": "multiple_choice",
                "options": [
                    {"id": "opt_exact", "text": "Yes, I have an exact time"},
                    {"id": "opt_approximate", "text": "I have an approximate time"},
                    {"id": "opt_window", "text": "I know a time window (e.g., morning, afternoon)"},
                    {"id": "opt_unknown", "text": "I don't know my birth time"}
                ],
                "category": "physical_traits"
            }
        except Exception as e:
            logger.error("Error in _get_first_question: %s", e)
            raise ValueError(f"Failed to get first question: {str(e)}") from e

    async def _should_complete_questionnaire(
        self,
        answers: List[Dict[str, Any]],
        min_answers: int = 10
    ) -> bool:
        """
        Determine if the questionnaire has enough information to be completed.

        Args:
            answers: List of question-answer pairs
            min_answers: Minimum number of answers required before considering completion

        Returns:
            Boolean indicating if questionnaire can be completed
        """
        # Set a higher minimum threshold for completion
        enhanced_min_answers = 10  # This enforces at least 10 questions regardless of what's passed in
        actual_min = max(min_answers, enhanced_min_answers)

        logger.info(f"Checking if questionnaire should be completed: {len(answers)} answers collected so far, minimum required: {actual_min}")

        # STRICT REQUIREMENT: If we don't have the minimum number of answers, always return False
        if len(answers) < actual_min:
            logger.debug("Not enough answers to complete questionnaire (%d/%d)", len(answers), actual_min)
            return False

        # Check if the last question was marked as final
        last_answer = answers[-1] if answers else None
        if last_answer and last_answer.get("is_final", False):
            logger.info("Final question answered, completing questionnaire")
            return True

        # Calculate completion confidence based on answer quality and quantity
        confidence = self._calculate_completion_confidence(answers)
        logger.info(f"Calculated completion confidence: {confidence:.2f}")

        # Track answered categories for more sophisticated completion logic
        categories_covered = self._count_categories_covered(answers)
        logger.info(f"Categories covered: {categories_covered}")

        # ENHANCED REQUIREMENT: Ensure diverse category coverage
        # Don't complete until we have answers in at least 6 different categories
        if categories_covered < 6:
            logger.debug("Only %d categories covered, need at least 6", categories_covered)
            return False

        # Check for critical categories that must be covered for accurate rectification
        critical_categories = ["birth_circumstances", "personality_traits", "life_events",
                              "timing_preferences", "vedic_birth_time", "physical_traits"]

        # Count how many critical categories are covered
        covered_critical_count = sum(1 for cat in critical_categories
                                   if any(self._category_match(a.get("category", ""), cat) for a in answers))

        # Require at least 4 of the 6 critical categories
        if covered_critical_count < 4:
            logger.debug("Only %d of %d critical categories covered",
                        covered_critical_count, len(critical_categories))
            return False

        # Check for detailed life event information, which is crucial for birth time rectification
        life_event_answers = [a.get("answer", "") for a in answers
                             if self._category_match(a.get("category", ""), "life_event")]

        has_detailed_life_events = False
        for answer in life_event_answers:
            # Check for detailed life event descriptions with years/dates
            if isinstance(answer, str) and len(answer) > 50:
                # Look for year patterns (19xx or 20xx) or age indicators
                import re
                year_patterns = re.findall(r'\b(19\d{2}|20\d{2})\b', answer)
                age_patterns = re.findall(r'\b(\d{1,2})\s*(years|yrs|year|yr)\b', answer, re.IGNORECASE)

                if year_patterns or age_patterns:
                    has_detailed_life_events = True
                    break

        # If no detailed life events but we haven't asked enough questions, continue
        if not has_detailed_life_events and len(answers) < 15:
            logger.debug("No detailed life event information yet, continuing questionnaire")
            return False

        # Verify we have information about the birth time precision
        birth_time_answers = [a for a in answers
                             if self._category_match(a.get("category", ""), "birth_time") or
                             "birth time" in str(a.get("question", "")).lower()]

        has_birth_time_info = len(birth_time_answers) > 0
        if not has_birth_time_info and len(answers) < 12:
            logger.debug("No birth time information yet, continuing questionnaire")
            return False

        # For very extensive and high-quality questionnaires, allow completion
        # This requires BOTH high answer count AND high confidence
        if confidence > 0.85 and len(answers) >= actual_min + 3 and categories_covered >= 7:
            logger.info("Extensive questionnaire with high confidence and diverse categories, completing")
            return True

        # For extremely long questionnaires, be more lenient
        if len(answers) >= actual_min + 10:
            logger.info("Extended questionnaire with %d answers, completing", len(answers))
            return True

        # Default: if confidence is not high enough, require more questions
        if confidence < 0.75 and len(answers) < 15:
            logger.debug("Confidence too low (%.2f), continuing questionnaire", confidence)
            return False

        logger.debug("Questionnaire continuing - confidence: %.2f, answers: %d, categories: %d",
                    confidence, len(answers), categories_covered)
        return False

    def _category_match(self, category: str, target: str) -> bool:
        """Helper method to match categories even when they're partial or different case"""
        if not category or not target:
            return False

        category = category.lower()
        target = target.lower()

        # Direct match
        if category == target:
            return True

        # Category contains target or target contains category
        if target in category or category in target:
            return True

        # Special case handling for related categories
        if target == "birth_time" and any(t in category for t in ["birth", "lagna", "ascendant"]):
            return True
        if target == "life_event" and any(t in category for t in ["life", "event", "transition", "change"]):
            return True
        if target == "personality_traits" and any(t in category for t in ["personality", "trait", "character"]):
            return True

        return False

    def _count_categories_covered(self, answers: List[Dict[str, Any]]) -> int:
        """Count the number of unique categories covered by answers"""
        categories = set()
        for answer in answers:
            category = answer.get("category")
            if category:
                categories.add(category)
        return len(categories)

    def _calculate_completion_confidence(self, answers: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence that we have enough information to complete questionnaire

        Args:
            answers: List of answers

        Returns:
            Confidence score between 0-1
        """
        if not answers:
            return 0.0

        # Start with a lower base confidence that grows more gradually
        # Maximum of 0.4 from answer count alone (at 20+ answers)
        answer_count = len(answers)
        base_confidence = min(0.4, answer_count * 0.02)

        # Count answer types for better confidence calculation
        text_answers = 0
        multiple_choice_answers = 0
        high_value_categories = 0

        # Track categories covered for confidence calculation
        covered_categories = set()

        # Category weights for confidence scoring
        category_weights = {
            "birth_circumstances": 0.08,
            "life_events": 0.10,
            "personality_traits": 0.07,
            "timing_preferences": 0.06,
            "physical_traits": 0.05,
            "vedic_birth_time": 0.09,
            "spiritual_inclinations": 0.05,
            "health_challenges": 0.06,
            "relationships": 0.07,
            "career_developments": 0.07
        }

        # Analyze each answer for quality indicators
        answer_quality_bonus = 0.0
        for answer in answers:
            answer_type = answer.get("type", "")
            category = answer.get("category", "")
            answer_content = answer.get("answer", "")

            # Add category to tracked set
            if category:
                covered_categories.add(category)

            # Track answer types
            if answer_type == "text" and isinstance(answer_content, str) and len(answer_content) > 10:
                text_answers += 1
                # Give more weight to detailed text answers
                if len(answer_content) > 50:
                    answer_quality_bonus += 0.02
            elif answer_type == "multiple_choice":
                multiple_choice_answers += 1

            # Add category-based bonus if it's a high-value category
            if category in category_weights:
                # Only add the weight once per category
                if category not in covered_categories or len([a for a in answers if a.get("category") == category]) <= 1:
                    answer_quality_bonus += category_weights[category]

        # Add bonus for text answers (which contain more information)
        text_bonus = min(0.2, text_answers * 0.04)

        # Add bonus for category diversity
        category_diversity_bonus = min(0.2, len(covered_categories) * 0.025)

        # Combine all factors for the final confidence score
        total_confidence = base_confidence + answer_quality_bonus + text_bonus + category_diversity_bonus

        # Ensure the confidence never exceeds 0.9 to avoid premature completion
        # This is crucial to prevent artificial boosting
        return min(0.9, total_confidence)

async def get_questionnaire_service() -> QuestionnaireService:
    """
    Get or create a shared instance of the QuestionnaireService.

    Returns:
        A QuestionnaireService instance

    Raises:
        RuntimeError: If OpenAI service is unavailable
    """
    # Check container first
    container = get_container()
    if container.has_service('questionnaire_service'):
        service = container.get('questionnaire_service')
        if service:
            return service

    # Create new service
    try:
        # Await the openai_service coroutine properly
        openai_service = await get_openai_service()
        if not openai_service:
            raise ValueError("OpenAI service is required for questionnaire service but is unavailable")

        service = QuestionnaireService(openai_service=openai_service)

        # Register in container
        container.register_instance('questionnaire_service', service)

        return service
    except Exception as e:
        logger.error("Error creating questionnaire service: %s", e)
        # Use the 'from' clause to properly chain the exception
        raise RuntimeError(f"Failed to create questionnaire service: {str(e)}") from e
