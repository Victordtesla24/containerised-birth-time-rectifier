"""
Unified Questionnaire Service for Birth Time Rectification.

This module provides a comprehensive service for generating, processing, and analyzing
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
from ai_service.services.session_service import get_session_service
from ai_service.utils.dependency_container import get_container
from ai_service.core.rectification.chart_calculator import calculate_chart

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

class QuestionnaireService:
    """
    Unified service for managing birth time rectification questionnaires.

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
        self.session_service = get_session_service()

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
            logger.error(f"Error getting initial questions: {e}")
            # Return a minimal set of questions if generation fails
            return [
                {
                    "id": f"q_birth_{uuid.uuid4().hex[:8]}",
                    "text": "Do you know if you were born closer to sunrise, midday, sunset, or during the night?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "sunrise", "text": "Around sunrise (early morning)"},
                        {"id": "midday", "text": "Around midday"},
                        {"id": "sunset", "text": "Around sunset (early evening)"},
                        {"id": "night", "text": "During the night (late evening/early morning)"},
                        {"id": "unknown", "text": "I don't know"}
                    ],
                    "category": "birth_circumstances",
                    "relevance": "high"
                }
            ]

    async def generate_next_question(
        self,
        birth_details: Dict[str, Any],
        previous_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate the next question based on chart data and previous answers.

        Args:
            birth_details: Birth details data
            previous_answers: Previous question-answer pairs

        Returns:
            Dictionary with the next question
        """
        # If no previous answers, get an initial question
        if not previous_answers:
            initial_questions = await self.get_initial_questions({"birth_details": birth_details})
            if initial_questions:
                return initial_questions[0]

        # Use astrological relevance to determine next question
        return await self._generate_astrologically_relevant_question(birth_details, previous_answers)

    async def submit_answer(
        self,
        session_id: str,
        question_id: str,
        answer: Any
    ) -> Dict[str, Any]:
        """
        Submit an answer to a question and process it.

        Args:
            session_id: Session ID for tracking
            question_id: ID of the question being answered
            answer: The answer content

        Returns:
            Dictionary with the result of processing the answer
        """
        # Get session data
        session_data = await self.session_service.get_session_async(session_id)
        if not session_data:
            raise ValueError(f"Invalid session ID: {session_id}")

        # Get the question text from the session
        previous_answers = session_data.get("responses", [])
        last_question = None

        for previous_answer in previous_answers:
            if previous_answer.get("question_id") == question_id:
                last_question = previous_answer.get("question", "")
                break

        # Store the answer
        await self.session_service.add_question_response(
            session_id=session_id,
            question_id=question_id,
            question_text=last_question or f"Question {question_id}",
            answer=answer
        )

        # Get birth details from session
        birth_details = session_data.get("birth_details", {})

        # Generate the next question if birth details are available
        if birth_details:
            # Update previous answers for next question generation
            session_data = await self.session_service.get_session_async(session_id)
            if session_data:
                next_question = await self.generate_next_question(
                    birth_details=birth_details,
                    previous_answers=session_data.get("responses", [])
                )

                return {
                    "success": True,
                    "session_id": session_id,
                    "question_id": question_id,
                    "next_question": next_question
                }

        # Return a basic success response if we can't generate a next question
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
        # Get OpenAI service - required for questionnaire completion
        if not self.openai_service:
            self.openai_service = await get_openai_service()
            if not self.openai_service:
                raise RuntimeError("OpenAI service is required for questionnaire completion but is not available")

        try:
            # Get session data to retrieve previous answers
            session_data = await self.session_service.get_session_async(session_id)
            if not session_data:
                raise ValueError(f"Invalid session ID: {session_id}")

            # Get previous answers from session
            previous_answers = session_data.get("responses", [])
            if not previous_answers:
                raise ValueError("No answers found in session, cannot complete questionnaire")

            # Get birth details from session
            birth_details = session_data.get("birth_details", {})
            if not birth_details:
                raise ValueError("Birth details not found in session")

            # Calculate time indicators from answers
            time_indicators = self._extract_time_indicators(previous_answers)

            # Create final analysis prompt
            final_analysis_prompt = self._create_final_analysis_prompt(previous_answers, birth_details)

            # Call OpenAI to get final analysis
            response = await self.openai_service.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert astrologer analyzing questionnaire responses to determine the most likely birth time."},
                    {"role": "user", "content": final_analysis_prompt}
                ],
                model="gpt-4",
                temperature=0.2
            )

            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not content:
                raise ValueError("Empty response from OpenAI")

            # Extract structured data from the response
            analysis_data = self._extract_json_from_content(content)

            # If no structured data could be extracted, create a minimal structure
            if not analysis_data:
                raise ValueError("Failed to extract structured data from OpenAI response")

            # Add time indicators to analysis
            analysis_data["time_indicators"] = time_indicators

            # Calculate confidence based on answers and analysis
            confidence = analysis_data.get("confidence", 0)
            if isinstance(confidence, str):
                # Convert string percentage to float
                confidence = float(confidence.strip("%")) / 100 if confidence.strip("%").isdigit() else 0.5
            else:
                # Normalize to 0-1 range
                confidence = min(1.0, max(0.0, confidence / 100)) if confidence > 1 else confidence

            # Store analysis results in session
            await self.session_service.update_session_async(session_id, {
                "final_analysis": analysis_data,
                "questionnaire_status": "completed",
                "confidence": confidence
            })

            return {
                "status": "completed",
                "message": "Questionnaire completed successfully",
                "analysis": analysis_data,
                "confidence": confidence
            }

        except Exception as e:
            logger.error(f"Error completing questionnaire: {e}")
            raise ValueError(f"Failed to complete questionnaire: {str(e)}")

    async def _generate_astrologically_relevant_question(
        self,
        birth_details: Dict[str, Any],
        previous_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an astrologically relevant question based on chart data.

        Args:
            birth_details: Birth details to use for question generation
            previous_answers: Previous answers to avoid repetition

        Returns:
            Dictionary with the question details

        Raises:
            ValueError: If OpenAI service is not available and required
        """
        # Get OpenAI service if not already set
        if not self.openai_service:
            self.openai_service = await get_openai_service()

        if not self.openai_service:
            raise ValueError("OpenAI service is required for dynamic question generation")

        try:
            # Generate a question using OpenAI
            prompt = self._create_question_generation_prompt(previous_answers, birth_details)

            messages = [
                {"role": "system", "content": "You are an expert astrologer generating questions for birth time rectification."},
                {"role": "user", "content": prompt}
            ]

            response = await self.openai_service.chat_completion(
                messages=messages,
                model="gpt-4",
                temperature=0.7
            )

            # Extract the generated question
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            question_data = self._extract_json_from_content(content)

            if not question_data or "text" not in question_data and "question" not in question_data:
                raise ValueError("Failed to generate a valid question")

            # Normalize the question data structure
            question_text = question_data.get("text", question_data.get("question", ""))
            question_type = question_data.get("type", question_data.get("question_type", "text"))
            category = question_data.get("category", "general")

            # Ensure the question has required fields
            question_id = f"q_{uuid.uuid4().hex[:8]}"

            question = {
                "id": question_id,
                "text": question_text,
                "type": question_type,
                "category": category,
                "relevance": question_data.get("relevance", question_data.get("astrological_factor", "medium"))
            }

            # Add options if it's a multiple choice question
            if question_type == "multiple_choice" and "options" in question_data:
                options = question_data["options"]
                # Normalize options format
                formatted_options = []
                for opt in options:
                    if isinstance(opt, str):
                        formatted_options.append({"id": f"opt_{len(formatted_options)}", "text": opt})
                    elif isinstance(opt, dict):
                        if "id" not in opt and "value" in opt:
                            opt["id"] = opt["value"]
                        if "id" not in opt:
                            opt["id"] = f"opt_{len(formatted_options)}"
                        if "text" not in opt and "label" in opt:
                            opt["text"] = opt["label"]
                        formatted_options.append(opt)

                question["options"] = formatted_options

            return question

        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")

            # Generate an alternative question based on birth details
            return self._generate_alternative_question(birth_details, previous_answers)

    def _create_question_generation_prompt(
        self,
        previous_answers: List[Dict[str, Any]],
        birth_details: Dict[str, Any]
    ) -> str:
        """
        Create prompt for dynamic question generation.

        Args:
            previous_answers: List of previous answers
            birth_details: Dictionary with birth details

        Returns:
            Formatted prompt string
        """
        # Format previous answers
        formatted_answers = "\n".join([
            f"Q: {a.get('question', a.get('question_text', 'Unknown question'))}\nA: {a.get('answer', 'No answer')}"
            for a in previous_answers
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

        # Generate the prompt
        return f"""
You are an expert astrological birth time rectification assistant. Generate the next question to ask based on the previous answers and birth details.

{birth_context}

Previous Questions and Answers:
{formatted_answers}

Generate a new question that will help determine the subject's birth time more accurately.
The question should be related to one of these categories:
1. Major life events and their timing
2. Personality traits and physical characteristics
3. Career and work patterns
4. Relationship patterns
5. Health experiences and patterns

Your response should be in this JSON format:
{{
  "text": "Your detailed question here",
  "type": "multiple_choice", // or "text", "yes_no", "date_time"
  "options": [
    {{
      "id": "option1",
      "text": "Option 1"
    }},
    {{
      "id": "option2",
      "text": "Option 2"
    }}
  ], // only for multiple_choice
  "category": "one of the 5 categories above",
  "relevance": "The astrological factor this question helps determine (e.g., Ascendant, MC, Moon placement, etc.)"
}}
"""

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
            question = answer.get("question", answer.get("question_text", ""))
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

    def _extract_json_from_content(self, content: str) -> Dict[str, Any]:
        """
        Extract JSON from OpenAI response content.

        Args:
            content: Text content from OpenAI

        Returns:
            Extracted JSON data
        """
        try:
            # Try direct JSON parsing first
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
        # Extract basic birth details
        birth_year = None
        birth_date = birth_details.get("birth_date", birth_details.get("birthDate", ""))

        if birth_date:
            try:
                birth_year = int(birth_date.split("-")[0])
            except (ValueError, IndexError):
                pass

        # Get question categories that haven't been asked yet
        asked_categories = set(a.get("category", "unknown") for a in previous_answers if "category" in a)
        available_categories = ["life_events", "relationships", "career", "health", "spirituality", "education", "personality"]
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
                "category": "life_events",
                "relevance": "high"
            }
        elif category == "relationships":
            return {
                "id": question_id,
                "text": "When did you meet your current partner or experience a significant relationship milestone?",
                "type": "text",
                "category": "relationships",
                "relevance": "medium"
            }
        elif category == "career":
            return {
                "id": question_id,
                "text": "What age or date did you start your most significant job or career path?",
                "type": "text",
                "category": "career",
                "relevance": "medium"
            }
        elif category == "health":
            return {
                "id": question_id,
                "text": "Have you experienced any significant health events? If so, when did they occur?",
                "type": "text",
                "category": "health",
                "relevance": "high"
            }
        elif category == "spirituality":
            return {
                "id": question_id,
                "text": "Have you had any spiritual awakening or transformation? When did this occur?",
                "type": "text",
                "category": "spirituality",
                "relevance": "medium"
            }
        elif category == "personality":
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
        else:  # education or default
            return {
                "id": question_id,
                "text": "When did you complete your education or training for your profession?",
                "type": "text",
                "category": "education",
                "relevance": "medium"
            }

# Singleton instance
_questionnaire_service = None

def get_questionnaire_service() -> QuestionnaireService:
    """
    Get or create a QuestionnaireService instance.

    Returns:
        A QuestionnaireService instance
    """
    global _questionnaire_service

    if _questionnaire_service is not None:
        return _questionnaire_service

    # Check container first
    container = get_container()
    if container.has_service('questionnaire_service'):
        service = container.get('questionnaire_service')
        if service:
            _questionnaire_service = service
            return service

    # Create new service
    try:
        openai_service = get_openai_service()
        service = QuestionnaireService(openai_service=openai_service)

        # Register in container
        container.register_instance('questionnaire_service', service)
        _questionnaire_service = service

        return service
    except Exception as e:
        logger.error(f"Error creating questionnaire service: {e}")
        # Create a service without OpenAI as fallback
        service = QuestionnaireService()
        _questionnaire_service = service
        return service
