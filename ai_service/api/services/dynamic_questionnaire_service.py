"""
Dynamic questionnaire service for birth time rectification.

This service utilizes OpenAI to generate personalized questions based on
previous answers and astrological context.
"""

import logging
import json
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union, cast
from datetime import datetime, timedelta

from ai_service.api.services.questionnaire_service import QuestionnaireService
from ai_service.api.services.openai.service import OpenAIService
from ai_service.utils.dependency_container import get_container
from ai_service.api.services.session_store import SessionStore
from ai_service.core.rectification.chart_calculator import calculate_chart
from ai_service.api.services.session_service import get_session_store

logger = logging.getLogger(__name__)

class DynamicQuestionnaireService:
    """Enhanced questionnaire service that dynamically generates questions using OpenAI."""

    def __init__(self, openai_service: Optional[OpenAIService] = None):
        """
        Initialize the dynamic questionnaire service.

        Args:
            openai_service: Optional OpenAI service for AI-powered question generation
        """
        # Import at runtime to avoid circular imports
        from ai_service.api.services.questionnaire_service import QuestionnaireService
        self.questionnaire_service = QuestionnaireService(openai_service=openai_service)
        self.openai_service = openai_service
        self.session_store = get_session_store()

    async def generate_next_question(
        self,
        birth_details: Dict[str, Any],
        previous_answers: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate the next dynamic question based on previous answers.

        Args:
            birth_details: Dictionary with birth details
            previous_answers: List of previous question-answer pairs

        Returns:
            Dictionary containing the next question

        Raises:
            RuntimeError: If question generation fails
        """
        try:
            logger.info(f"Generating question #{len(previous_answers) + 1} with enhanced AI logic")

            # Get OpenAI service from container if not provided
            if not self.openai_service:
                container = get_container()
                self.openai_service = container.get("openai_service")
                if not self.openai_service:
                    raise RuntimeError("OpenAI service required for dynamic question generation")

            # Create prompt for next question
            prompt = self._create_question_generation_prompt(previous_answers, birth_details)

            # Get response from OpenAI
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.7,
                model="gpt-4"  # Use a fixed model name instead of config
            )

            if response:
                content = response.get("choices", [{}])[0].get("text", "").strip()
                if content:
                    try:
                        # Parse JSON response from OpenAI
                        question_data = self._extract_json_from_content(content)
                        if "question" in question_data:
                            return {
                                "next_question": {
                                    "id": f"dynamic_{len(previous_answers) + 1}",
                                    "text": question_data["question"],
                                    "options": question_data.get("options", []),
                                    "type": question_data.get("question_type", "multiple_choice"),
                                    "category": question_data.get("category", "personality"),
                                    "relevance": question_data.get("astrological_factor", "")
                                },
                                "confidence": 85
                            }
                    except Exception as json_error:
                        logger.error(f"Error parsing OpenAI response: {str(json_error)}")
                        raise RuntimeError(f"Failed to parse question data: {str(json_error)}")

            # If we get here, there was an issue with the OpenAI response
            raise RuntimeError("Failed to generate a valid question with AI service")

        except Exception as e:
            logger.error(f"Error generating dynamic question: {str(e)}")
            raise RuntimeError(f"Question generation failed: {str(e)}")

    async def submit_answer(
        self,
        session_id: str,
        question_id: str,
        answer: Any
    ) -> Dict[str, Any]:
        """
        Submit answer and analyze with enhanced astrological context.

        Args:
            session_id: The session ID for the questionnaire
            question_id: The ID of the question being answered
            answer: The answer data

        Returns:
            Dictionary with answer submission status and analysis metrics
        """
        try:
            # Store answer using parent method
            result = await self.questionnaire_service.submit_answer(session_id, question_id, answer)

            # Get session data
            session_data = await self.session_store.get_session(session_id)
            if not session_data:
                return {
                    "status": "error",
                    "message": f"Session {session_id} not found"
                }

            previous_answers = session_data.get("previous_answers", [])
            birth_details = session_data.get("birth_details", {})

            # Enhance answer analysis with OpenAI if available
            if self.openai_service and len(previous_answers) >= 3:
                # Only perform enhanced analysis periodically to avoid excessive API calls
                if len(previous_answers) % 3 == 0:
                    prompt = self._create_answer_analysis_prompt(previous_answers, birth_details)
                    analysis = await self.openai_service.generate_completion(
                        prompt=prompt,
                        task_type="analyze_answers"
                    )

                    if analysis and "content" in analysis:
                        # Parse the analysis
                        try:
                            analysis_data = self._extract_json_from_content(analysis["content"])

                            if "insights" in analysis_data:
                                # Store analysis results
                                await self._store_analysis_results(session_id, analysis_data)

                                # Update result with enhanced insights
                                result["enhanced_analysis"] = {
                                    "insights": analysis_data["insights"],
                                    "potential_indicators": analysis_data.get("potential_indicators", [])
                                }
                        except Exception as parse_error:
                            logger.error(f"Error parsing analysis response: {str(parse_error)}")

            return result

        except Exception as e:
            logger.error(f"Error processing answer submission: {str(e)}")
            return {
                "error": f"Failed to process answer: {str(e)}",
                "question_id": question_id
            }

    async def complete_questionnaire(self, session_id: str, chart_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete questionnaire with comprehensive analysis of answers.

        Args:
            session_id: The session ID containing questionnaire data
            chart_id: Optional chart ID for reference

        Returns:
            Dictionary with comprehensive analysis results
        """
        try:
            # Get session data
            session_data = await self.session_store.get_session(session_id)
            if not session_data:
                return {
                    "status": "error",
                    "message": f"Session {session_id} not found"
                }

            previous_answers = session_data.get("previous_answers", [])
            birth_details = session_data.get("birth_details", {})

            if not previous_answers:
                return {"error": "No answers provided", "status": "incomplete"}

            # Perform comprehensive analysis with OpenAI
            if self.openai_service:
                prompt = self._create_final_analysis_prompt(previous_answers, birth_details)
                analysis = await self.openai_service.generate_completion(
                    prompt=prompt,
                    task_type="final_analysis"
                )

                if analysis and "content" in analysis:
                    try:
                        analysis_data = self._extract_json_from_content(analysis["content"])

                        if "birth_time_indicators" in analysis_data:
                            # Store final analysis
                            await self._store_final_analysis(session_id, analysis_data)

                            return {
                                "status": "completed",
                                "answer_count": len(previous_answers),
                                "birth_time_indicators": analysis_data["birth_time_indicators"],
                                "analysis_summary": analysis_data.get("summary", ""),
                                "confidence": analysis_data.get("confidence", 0),
                                "recommendations": analysis_data.get("recommendations", [])
                            }
                    except Exception as parse_error:
                        logger.error(f"Error parsing final analysis: {str(parse_error)}")

            # Fallback to basic completion if OpenAI is unavailable
            return await self.questionnaire_service.complete_questionnaire(session_id, chart_id)

        except Exception as e:
            logger.error(f"Error completing questionnaire: {str(e)}")
            return {"error": f"Failed to complete questionnaire: {str(e)}", "status": "error"}

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
            f"Q: {a.get('question', 'Unknown question')}\nA: {a.get('answer', 'No answer')}"
            for a in previous_answers
        ])

        # Create birth details section if available
        birth_context = ""
        if birth_details:
            birth_context = f"""
Birth Date: {birth_details.get('birth_date', birth_details.get('birthDate', 'Unknown'))}
Approximate Birth Time: {birth_details.get('birth_time', birth_details.get('birthTime', 'Unknown'))}
Location: {birth_details.get('birth_place', birth_details.get('birthPlace', 'Unknown'))}
Latitude: {birth_details.get('latitude', 'Unknown')}
Longitude: {birth_details.get('longitude', 'Unknown')}
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
  "question": "Your detailed question here",
  "question_type": "multiple_choice", // or "open_ended", "yes_no", "date_time"
  "options": ["Option 1", "Option 2", "Option 3", "Option 4"], // only for multiple_choice
  "category": "one of the 5 categories above",
  "astrological_factor": "The astrological factor this question helps determine (e.g., Ascendant, MC, Moon placement, etc.)"
}}
"""

    def _create_answer_analysis_prompt(
        self,
        previous_answers: List[Dict[str, Any]],
        birth_details: Dict[str, Any]
    ) -> str:
        """
        Create prompt for answer analysis.

        Args:
            previous_answers: List of previous answers
            birth_details: Dictionary with birth details

        Returns:
            Formatted prompt string
        """
        # Format previous answers
        formatted_answers = "\n".join([
            f"Q: {a.get('question', 'Unknown question')}\nA: {a.get('answer', 'No answer')}"
            for a in previous_answers
        ])

        # Create birth details section
        birth_context = f"""
Birth Date: {birth_details.get('birth_date', birth_details.get('birthDate', 'Unknown'))}
Approximate Birth Time: {birth_details.get('birth_time', birth_details.get('birthTime', 'Unknown'))}
Location: {birth_details.get('birth_place', birth_details.get('birthPlace', 'Unknown'))}
Latitude: {birth_details.get('latitude', 'Unknown')}
Longitude: {birth_details.get('longitude', 'Unknown')}
        """

        return f"""
You are an expert astrological analyst specializing in birth time rectification. Analyze the following questions and answers to derive insights about potential birth time indicators.

{birth_context}

Questions and Answers:
{formatted_answers}

Based on these responses, provide astrological insights that could help determine the subject's birth time.
Focus on identifying patterns related to:
1. Ascendant/Rising sign indicators (personality, physical traits)
2. MC/IC axis indicators (career, home life)
3. Angular house placements
4. Potential life events that correspond to transits or progressions

Your response should be in this JSON format:
{{
  "insights": [
    "Key insight about personality traits indicating potential rising sign",
    "Key insight about career patterns indicating potential MC placement",
    "Other astrological insights from the answers..."
  ],
  "potential_indicators": [
    {{
      "factor": "Ascendant",
      "potential_signs": ["Sign1", "Sign2"],
      "confidence": 0-100,
      "reasoning": "Brief explanation"
    }},
    {{
      "factor": "MC",
      "potential_signs": ["Sign1", "Sign2"],
      "confidence": 0-100,
      "reasoning": "Brief explanation"
    }}
  ]
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
            f"Q: {a.get('question', 'Unknown question')}\nA: {a.get('answer', 'No answer')}"
            for a in answers
        ])

        # Create birth details section
        birth_context = f"""
Birth Date: {birth_details.get('birth_date', birth_details.get('birthDate', 'Unknown'))}
Approximate Birth Time: {birth_details.get('birth_time', birth_details.get('birthTime', 'Unknown'))}
Location: {birth_details.get('birth_place', birth_details.get('birthPlace', 'Unknown'))}
Latitude: {birth_details.get('latitude', 'Unknown')}
Longitude: {birth_details.get('longitude', 'Unknown')}
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

    async def _store_analysis_results(self, session_id: str, analysis_data: Dict[str, Any]) -> None:
        """
        Store analysis results in the session.

        Args:
            session_id: The session ID
            analysis_data: The analysis data to store
        """
        try:
            session = await self.session_store.get_session(session_id)
            if session:
                if "analysis_results" not in session:
                    session["analysis_results"] = []

                # Add timestamp to analysis
                analysis_data["timestamp"] = datetime.now().isoformat()
                session["analysis_results"].append(analysis_data)

                await self.session_store.update_session(session_id, session)
        except Exception as e:
            logger.error(f"Error storing analysis results: {str(e)}")

    async def _store_final_analysis(self, session_id: str, analysis_data: Dict[str, Any]) -> None:
        """
        Store final comprehensive analysis in the session.

        Args:
            session_id: The session ID
            analysis_data: The analysis data to store
        """
        try:
            session = await self.session_store.get_session(session_id)
            if session:
                # Add timestamp to analysis
                analysis_data["timestamp"] = datetime.now().isoformat()
                session["final_analysis"] = analysis_data

                # Also store birth time indicators separately for easy access
                if "birth_time_indicators" in analysis_data:
                    session["birth_time_indicators"] = analysis_data["birth_time_indicators"]

                await self.session_store.update_session(session_id, session)
        except Exception as e:
            logger.error(f"Error storing final analysis: {str(e)}")

    def _extract_json_from_content(self, content: str) -> Dict[str, Any]:
        """
        Extract JSON data from response content, handling code blocks.

        Args:
            content: Text content from the AI model

        Returns:
            Extracted JSON data as dictionary

        Raises:
            ValueError: If JSON cannot be parsed
        """
        # Clean up the content to extract JSON
        clean_content = content.strip()

        # Extract JSON from code blocks if present
        if "```" in clean_content:
            pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            matches = re.search(pattern, clean_content)
            if matches:
                clean_content = matches.group(1).strip()

        # Try to parse as JSON
        try:
            return json.loads(clean_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from content: {e}")
            logger.debug(f"Content was: {clean_content[:100]}...")
            raise ValueError(f"Invalid JSON response format: {e}")
