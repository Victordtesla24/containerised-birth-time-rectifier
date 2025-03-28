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
import asyncio

# Import service dependencies
from ai_service.api.services.openai import get_openai_service, OpenAIService
from ai_service.api.services.session_service import get_session_store
from ai_service.utils.dependency_container import get_container
from ai_service.core.rectification.chart_calculator import calculate_chart

# Import question generation and analysis modules
from ai_service.api.services.questionnaire_service_generation import generate_question
from ai_service.api.services.questionnaire_service_analysis import submit_answer
from ai_service.api.services.questionnaire_service_completion import complete_questionnaire
from ai_service.api.services.questionnaire_service_time_indicators import extract_time_indicators

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
        self.session_service = get_session_store()

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
            session_data = self.session_service.get_session(session_id)
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
            self.session_service.update_session(session_id, session_data)

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
            logger.error(f"Error submitting answer: {e}")
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
            session_data = self.session_service.get_session(session_id)
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
                logger.error(f"Error calculating confidence: {conf_error}")
                confidence = 0.5  # Default to medium confidence

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
            self.session_service.update_session(session_id, session_update)

            # Return analysis data with completed status
            return {
                "completed": True,
                "chart_id": chart_id,
                "confidence": confidence,
                "session_id": session_id,
                "analysis": analysis_data
            }
        except Exception as e:
            logger.error(f"Error completing questionnaire: {e}")
            return {
                "completed": False,
                "error": str(e)
            }

    async def _calculate_confidence(self, answers: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence score based on answer quality and quantity.

        Args:
            answers: List of answered questions with their answers

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Basic implementation - more questions means higher confidence
        if not answers:
            return 0.0

        # Start with base confidence of 0.3
        base_confidence = 0.3

        # Add confidence based on number of questions (up to 0.5 max)
        question_factor = min(0.5, len(answers) * 0.05)

        # Add confidence for completeness and quality (simplified)
        quality_factor = 0.1

        # Calculate final confidence (cap at 0.95)
        confidence = min(0.95, base_confidence + question_factor + quality_factor)

        return confidence

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

    async def initialize_questionnaire(
        self,
        chart_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Initialize a new questionnaire for birth time rectification.

        Args:
            chart_id: The chart ID to associate with this questionnaire
            session_id: The session ID to use for this questionnaire

        Returns:
            Dictionary with first question and questionnaire metadata
        """
        try:
            # Get session data
            session_data = self.session_service.get_session(session_id)
            if not session_data:
                # Create new session if it doesn't exist
                session_data = {
                    "chart_id": chart_id,
                    "started_at": datetime.now().isoformat(),
                    "answers": [],
                    "current_question_index": 0,
                    "status": "active"
                }
                self.session_service.create_session(session_id, session_data)
            else:
                # Update existing session
                session_data["chart_id"] = chart_id
                session_data["status"] = "active"
                self.session_service.update_session(session_id, session_data)

            # Get chart data if not in session
            chart_data = session_data.get("data", {}).get("chart_data")
            if not chart_data:
                # Import chart service
                from ai_service.services import get_chart_service
                chart_service = get_chart_service()

                # Get chart data
                chart_data = await chart_service.get_chart(chart_id)
                if not chart_data:
                    raise ValueError(f"Chart not found: {chart_id}")

                # Store chart data in session
                if "data" not in session_data:
                    session_data["data"] = {}
                session_data["data"]["chart_data"] = chart_data
                self.session_service.update_session(session_id, session_data)

            # Extract birth details
            birth_details = chart_data.get("birth_details", {})

            # Get initial questions
            questions = await self.get_initial_questions(chart_data)
            if not questions or len(questions) == 0:
                raise ValueError("Failed to generate initial questions")

            # Store questions in session
            if "data" not in session_data:
                session_data["data"] = {}
            session_data["data"]["questions"] = questions
            self.session_service.update_session(session_id, session_data)

            # Return first question
            return {
                "question": questions[0],
                "total_questions": len(questions),
                "progress": {
                    "current": 1,
                    "total": len(questions)
                }
            }
        except Exception as e:
            logger.error(f"Error initializing questionnaire: {e}")
            raise

    async def process_answer_and_get_next_question(
        self,
        session_id: str,
        question_id: str,
        answer: Any
    ) -> Dict[str, Any]:
        """
        Process an answer and get the next question.

        Args:
            session_id: The session ID for this questionnaire
            question_id: The ID of the question being answered
            answer: The answer to the question

        Returns:
            Dictionary with next question and progress information
        """
        try:
            # Get session data
            session_data = self.session_service.get_session(session_id)
            if not session_data:
                raise ValueError(f"Invalid session ID: {session_id}")

            # Process answer using the submit_answer method
            submission_result = await self.submit_answer(session_id, question_id, answer)

            # Get updated session data safely handling potential None
            updated_session = None
            if self.session_service is not None:
                updated_session = self.session_service.get_session(session_id)

            # Default to empty dict if updated_session is None
            session_data = {}
            if updated_session is not None:
                session_data = updated_session.get("data", {})

            # Check if we have more questions
            questions = session_data.get("questions", [])
            answers = session_data.get("answers", [])
            current_index = session_data.get("current_question_index", 0)

            # Calculate progress
            total_questions = len(questions)
            questions_completed = len(answers)
            questions_remaining = max(0, total_questions - questions_completed)

            # Check if questionnaire is complete
            if current_index >= total_questions or questions_remaining == 0:
                return {
                    "complete": True,
                    "confidence": submission_result.get("confidence", 0.0),
                    "progress": {
                        "current": questions_completed,
                        "total_estimated": total_questions,
                        "percentage": min(100, int(questions_completed / max(1, total_questions) * 100))
                    }
                }

            # Get next question
            next_question = questions[current_index] if current_index < len(questions) else None

            # Build response
            response = {
                "question": next_question,
                "confidence": submission_result.get("confidence", 0.0),
                "progress": {
                    "current": questions_completed,
                    "total_estimated": total_questions,
                    "percentage": min(100, int(questions_completed / max(1, total_questions) * 100))
                }
            }

            return response
        except Exception as e:
            logger.error(f"Error processing answer: {e}")
            raise

# Singleton instance
_questionnaire_service = None

async def get_questionnaire_service() -> QuestionnaireService:
    """
    Get or create a QuestionnaireService instance.

    Returns:
        A QuestionnaireService instance

    Raises:
        RuntimeError: If OpenAI service is unavailable
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
        # Await the openai_service coroutine properly
        openai_service = await get_openai_service()
        if not openai_service:
            raise ValueError("OpenAI service is required for questionnaire service but is unavailable")

        service = QuestionnaireService(openai_service=openai_service)

        # Register in container
        container.register_instance('questionnaire_service', service)
        _questionnaire_service = service

        return service
    except Exception as e:
        logger.error(f"Error creating questionnaire service: {e}")
        # No fallback - propagate the error
        raise RuntimeError(f"Failed to create questionnaire service: {str(e)}")
