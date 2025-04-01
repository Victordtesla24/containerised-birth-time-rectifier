"""
Questionnaire engine for Birth Time Rectifier API.
Handles generation and processing of questions for birth time rectification.
Uses OpenAI for verifying chart data against Indian Vedic Astrological standards.
"""

import logging
import uuid
import json
import re
import random
import traceback
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Import AI services
from ai_service.api.services.openai import get_openai_service

# Import constants and calculators if available
try:
    # Import the modularized rectification structure
    from ai_service.core.rectification.constants import PLANETS_LIST
except ImportError:
    # Define fallback constants if imports fail
    PLANETS_LIST = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

# Configure logging
logger = logging.getLogger(__name__)

class QuestionnaireEngine:
    """
    Engine for generating and processing questionnaire questions for birth time rectification.
    Implements AI-driven question generation with adaptation based on previous answers.
    """

    def __init__(self):
        """
        Initialize the questionnaire engine.
        """
        # Dictionary to track question history by session
        self.question_history = {}

        # Dictionary to track answer history by session
        self.answer_history = {}

        # Initialize OpenAI service to None, will be fetched when needed
        self.openai_service = None

        # Define a getter function for async OpenAI service initialization
        self._openai_service_getter = None
        try:
            # Import the getter function at init time
            from ai_service.api.services.openai import get_openai_service
            self._openai_service_getter = get_openai_service
        except ImportError:
            # Log an error but don't crash - we'll try again when needed
            logger.warning("Could not import OpenAI service at initialization time. Will try again when needed.")

        # Enhanced tracking for question history and answer analysis
        self.birth_time_indicators = {}  # Track birth time indicators by session ID

        # Questions for fallback mode
        self.fallback_questions = [
            {
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
            },
            {
                "id": "q_major_life_events",
                "text": "Please list any major life events with their dates (e.g., graduations, career changes, marriages, moves)",
                "type": "text",
                "category": "life_events"
            },
            {
                "id": "q_personality_traits",
                "text": "Which personality traits describe you best?",
                "type": "multiple_choice",
                "options": [
                    {"id": "opt_analytical", "text": "Analytical and precise"},
                    {"id": "opt_creative", "text": "Creative and intuitive"},
                    {"id": "opt_outgoing", "text": "Outgoing and social"},
                    {"id": "opt_reserved", "text": "Reserved and thoughtful"}
                ],
                "category": "personality"
            },
            {
                "id": "q_daily_rhythm",
                "text": "What is your natural energy rhythm during the day?",
                "type": "multiple_choice",
                "options": [
                    {"id": "opt_morning", "text": "Morning person - most productive early in the day"},
                    {"id": "opt_afternoon", "text": "Afternoon person - most productive midday"},
                    {"id": "opt_evening", "text": "Evening person - most productive in the evening"},
                    {"id": "opt_night", "text": "Night owl - most productive late at night"}
                ],
                "category": "timing_preferences"
            },
            {
                "id": "q_significant_relationships",
                "text": "Describe significant relationships in your life and when they began",
                "type": "text",
                "category": "relationships"
            }
        ]

    async def get_first_question(self, chart_data: Optional[Dict[str, Any]] = None, birth_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate the first question for a new questionnaire session.

        Args:
            chart_data: Chart data to use for personalized questions (optional)
            birth_details: Birth details for context (optional)

        Returns:
            First question as a dictionary

        Raises:
            Exception: If question generation fails
        """
        logger.info("Generating first question for questionnaire")

        try:
            # Log birth details for diagnostics if available
            if birth_details:
                birth_date = birth_details.get("birth_date", "Not provided")
                logger.info("Generating question for birth date: %s", birth_date)

            # If chart data is available, use it to personalize the question
            if chart_data and isinstance(chart_data, dict):
                logger.info("Using chart data to personalize question")
                # Chart data is available, could influence the question later

            # Get the OpenAI service if it's available
            openai_service = None
            if self._openai_service_getter:
                try:
                    openai_service = await self._openai_service_getter()
                except Exception as e:
                    logger.error(f"Error getting OpenAI service: {e}")
                    raise Exception(f"Failed to get OpenAI service: {e}")

            # We MUST use OpenAI for question generation - no fallbacks allowed
            if not openai_service:
                raise Exception("OpenAI service is not available - cannot generate personalized questions")

                try:
                    logger.info("Using OpenAI to generate personalized first question")

                    # Create a Vedic-focused prompt
                    vedic_prompt = {
                        "task": "generate_initial_vedic_question",
                        "birth_details": birth_details or {},
                        "chart_data": chart_data or {},
                        "instructions": """
                        Create the first question for a Vedic astrological birth time rectification questionnaire.
                        This initial question should establish a baseline for assessing the person's birth time knowledge and confidence.

                        REQUIREMENTS:
                        1. Focus specifically on determining birth time precision and reliability
                        2. Use clear Vedic terminology (like Lagna/Rising sign) but ensure it's accessible to beginners
                        3. Format as multiple-choice with 4 distinct options covering different levels of birth time certainty
                        4. Be conversational but precise, avoiding technical jargon that might confuse non-astrologers
                        5. DO NOT ask about personality traits or life events in this first question

                        FORMAT REQUIREMENTS:
                        Respond with a JSON object containing:
                        {
                          "id": "q_vedic_initial_[unique_id]",
                          "text": "The question text (make it detailed and specific)",
                          "type": "multiple_choice",
                          "options": [
                            {"id": "opt_exact", "text": "I have an exact birth time"},
                            {"id": "opt_approximate", "text": "I have an approximate time"},
                            {"id": "opt_window", "text": "I know a general timeframe (morning, afternoon, etc.)"},
                            {"id": "opt_unknown", "text": "I don't know my birth time at all"}
                          ],
                          "category": "vedic_birth_time"
                        }

                        RETURN ONLY THE JSON OBJECT. Do not include additional text, explanations, or markdown formatting.
                        """
                    }

                    # Call OpenAI for the initial question
                        question_response = await openai_service.chat_completion(
                            messages=[
                                {"role": "system", "content": "You are an expert Vedic astrologer specializing in birth time rectification."},
                                {"role": "user", "content": json.dumps(vedic_prompt)}
                            ],
                            model="gpt-4o-mini",
                            temperature=0.3,
                            max_tokens=600
                        )

                        # Process the response
                        if question_response and isinstance(question_response, dict) and "choices" in question_response:
                            content = question_response["choices"][0]["message"]["content"]

                            # Parse the JSON response
                            try:
                                parsed_question = json.loads(content)
                                if isinstance(parsed_question, dict) and "text" in parsed_question:
                                    logger.info(f"Successfully parsed personalized question: {parsed_question['text']}")
                                    return parsed_question
                                else:
                                    raise Exception("Invalid question format returned from AI model")
                            except json.JSONDecodeError:
                                logger.warning("Failed to parse OpenAI response as JSON")
                                raise Exception("Failed to parse AI response as valid JSON")
                        else:
                            raise Exception("Invalid response format from AI model")
                except Exception as e:
                    logger.error("Error generating first question with OpenAI: %s", str(e))
                    logger.error(traceback.format_exc())
                    raise Exception(f"Failed to generate first question: {str(e)}")
        except Exception as e:
            # Log the error and rethrow it to the caller
            logger.error("Failed to generate question: %s", str(e))
            logger.error(traceback.format_exc())
            raise Exception(f"Failed to generate first question: {str(e)}")

    async def get_next_question(self, session_id: str, answers: List[Dict], chart_data: Dict, response_override: Optional[Dict] = None) -> Dict:
        """Get the next question for the questionnaire."""
        logger.info(f"Getting next question for session {session_id}")

        # Initialize OpenAI service if needed
        if not self.openai_service:
            try:
                self.openai_service = await get_openai_service()
                logger.info("OpenAI service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI service: {e}")
                raise Exception(f"OpenAI service unavailable - cannot generate real-time questions: {e}")

        # Get the previously asked question categories and IDs to avoid repetition
        asked_categories = []
        asked_question_ids = []
        asked_questions_content = []

        # Log the answers received
        logger.info(f"Received {len(answers)} previous answers")

        for answer in answers:
            question = answer.get("question", {})
            category = question.get("category")
            question_id = question.get("id")
            question_text = question.get("text", "")

            if category:
                asked_categories.append(category)
            if question_id:
                asked_question_ids.append(question_id)
            if question_text:
                asked_questions_content.append(question_text)

        logger.info(f"Asked categories: {asked_categories}")
        logger.info(f"Asked question IDs: {asked_question_ids}")

        # Create a context for generating a new question
        chart_summary = self._summarize_chart_data(chart_data)

        # We MUST use OpenAI for all question generation - no fallbacks to templates
        if not self.openai_service:
            raise Exception("OpenAI service is unavailable - cannot generate real-time personalized questions")

        try:
            # Create a detailed prompt for OpenAI
            prompt = self._create_openai_prompt(
                asked_categories=asked_categories,
                asked_questions_content=asked_questions_content,
                answers=answers,
                chart_data=chart_data,
                chart_summary=chart_summary
            )

            # Get response from OpenAI using chat_completion
            openai_response = await self.openai_service.chat_completion(
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ],
                model="gpt-4o",
                temperature=0.7,
                max_tokens=500
            )

            # Check response format and handle different types
            if (isinstance(openai_response, dict) and
                "choices" in openai_response and
                isinstance(openai_response["choices"], list) and
                len(openai_response["choices"]) > 0):
                try:
                    # Extract the question from the response
                    question_data = self._extract_question_from_openai(openai_response)

                    if question_data is None:
                        logger.warning("Failed to extract question data from OpenAI response")
                        raise ValueError("Invalid question data from OpenAI")

                    # Ensure the question has a unique ID
                    if "id" not in question_data or not question_data["id"]:
                        question_data["id"] = f"q_vedic_{str(uuid.uuid4())[:8]}"

                    # Ensure the question has a category
                    if "category" not in question_data or not question_data["category"]:
                        # Assign a category that hasn't been asked much
                        question_data["category"] = self._get_least_used_category(asked_categories)

                    # Validate that this question is not a repeat
                    if (question_data.get("text") and
                        not any(self._is_similar_question(question_data["text"], prev_question)
                               for prev_question in asked_questions_content)):
                        question_text = question_data.get("text", "")
                        log_text = question_text[:100] + "..." if len(question_text) > 100 else question_text
                        logger.info(f"Generated unique question via OpenAI: {log_text}")
                        return question_data
                else:
                        logger.warning("OpenAI generated a similar question to one already asked, retrying...")
                except Exception as e:
                    logger.error(f"Error extracting question from OpenAI response: {e}")
                    raise Exception(f"Failed to extract valid question from OpenAI response: {e}")
            else:
                logger.warning(f"Invalid OpenAI response format: {str(openai_response)[:100]}")
                raise Exception("Invalid response format from OpenAI")

            # Try again with a stronger instruction to avoid repeats
            try:
                # Create a more specific prompt emphasizing uniqueness
                prompt = self._create_openai_prompt(
                    asked_categories=asked_categories,
                    asked_questions_content=asked_questions_content,
                    answers=answers,
                    chart_data=chart_data,
                    chart_summary=chart_summary,
                    emphasize_uniqueness=True
                )

                # Get response from OpenAI again using chat_completion
                    openai_response = await self.openai_service.chat_completion(
                        messages=[
                        {"role": "system", "content": prompt["system"]},
                        {"role": "user", "content": prompt["user"]}
                    ],
                    model="gpt-4o",
                    temperature=0.7,
                    max_tokens=500
                )

                # Check response format and handle different types
                    if (isinstance(openai_response, dict) and
                        "choices" in openai_response and
                        isinstance(openai_response["choices"], list) and
                        len(openai_response["choices"]) > 0):

                    question_data = self._extract_question_from_openai(openai_response)

                    if question_data is None:
                        logger.warning("Failed to extract question data from second OpenAI attempt")
                        raise ValueError("Failed to generate valid question after multiple attempts")

                    # Ensure the question has a unique ID
                    if "id" not in question_data or not question_data["id"]:
                        question_data["id"] = f"q_vedic_{str(uuid.uuid4())[:8]}"

                    # Ensure the question has a category
                    if "category" not in question_data or not question_data["category"]:
                        question_data["category"] = self._get_least_used_category(asked_categories)

                    question_text = question_data.get("text", "")
                    log_text = question_text[:100] + "..." if len(question_text) > 100 else question_text
                    logger.info(f"Generated question on second attempt via OpenAI: {log_text}")
                    return question_data
                            else:
                    logger.warning(f"Invalid OpenAI response format on retry: {str(openai_response)[:100]}")
                    raise Exception("Failed to generate valid question after multiple attempts")
            except Exception as e:
                logger.error(f"Error on second attempt with OpenAI: {e}")
                raise Exception(f"Failed to generate question after multiple attempts: {e}")
        except Exception as e:
            logger.error(f"Error generating question with OpenAI: {e}")
            raise Exception(f"Failed to generate personalized question: {e}")

    def _is_similar_question(self, new_question: str, previous_question: str) -> bool:
        """Check if a new question is semantically similar to a previously asked question."""
        # Basic similarity check - normalize and compare
        new_norm = new_question.lower().strip()
        prev_norm = previous_question.lower().strip()

        # Direct substring check
        if new_norm in prev_norm or prev_norm in new_norm:
            return True

        # Check if they share significant words
        new_words = set(re.findall(r'\b\w+\b', new_norm))
        prev_words = set(re.findall(r'\b\w+\b', prev_norm))

        # If they share more than 70% of words, consider them similar
        if len(new_words) > 0 and len(prev_words) > 0:
            common_words = new_words.intersection(prev_words)
            similarity_ratio = len(common_words) / min(len(new_words), len(prev_words))
            return similarity_ratio > 0.7

        return False

    def _get_least_used_category(self, asked_categories: List[str]) -> str:
        """Return a category that has been used the least."""
        all_categories = [
            "childhood", "life_events", "personality", "physical_traits",
            "health", "career", "relationships", "spiritual", "timing"
        ]

        # Count occurrences of each category
        category_counts = {}
        for category in all_categories:
            category_counts[category] = asked_categories.count(category)

        # Find the least used categories
        min_count = min(category_counts.values())
        least_used = [cat for cat, count in category_counts.items() if count == min_count]

        return random.choice(least_used)

    def _create_openai_prompt(self, asked_categories: List[str], asked_questions_content: List[str],
                           answers: List[Dict], chart_data: Dict, chart_summary: str,
                           emphasize_uniqueness: bool = False) -> Dict[str, str]:
        """Create a detailed prompt for OpenAI to generate a unique question."""

        # Base system prompt
        system_prompt = """You are an expert Vedic astrologer specialized in birth time rectification.
Generate a single, specific question that will help determine a person's precise birth time based on their chart data and previous responses.
Your question must be unique and different from any previously asked questions.
Focus on practical, experiential details that can be correlated with planetary positions.

Guidelines:
1. Create ONE concise, clear question (1-2 sentences maximum)
2. Make the question specific to this person's chart
3. Do NOT ask generic questions
4. NEVER repeat previous questions or ask slight variations of them
5. Return your response in JSON format: {"id": "unique_id", "text": "your question", "category": "relevant_category", "type": "text"}
6. Valid categories: childhood, life_events, personality, physical_traits, health, career, relationships, spiritual, timing
"""

        if emphasize_uniqueness:
            system_prompt += """
7. CRITICAL: This is a second attempt because your previous question was too similar to one already asked.
   Your question MUST be COMPLETELY DIFFERENT in both wording and topic from all previous questions.
   Choose a category that hasn't been frequently covered yet.
"""

        # User prompt with context
        user_prompt = f"""
Chart Data Summary: {chart_summary}

Previously Asked Questions:
{json.dumps(asked_questions_content, indent=2)}

Previous Response Categories:
{json.dumps(asked_categories, indent=2)}

Previous Answers:
{json.dumps([(a.get('question', {}).get('text', ''), a.get('answer', '')) for a in answers], indent=2)}

I need a SINGLE, UNIQUE Vedic astrological question for birth time rectification that:
1. Is specific to this chart
2. Is NOT similar to any previous question
3. Helps identify life events or personality traits linked to planetary positions
4. Focuses on a category that hasn't been extensively covered yet

Return ONLY a JSON object with the question details.
"""

        return {"system": system_prompt, "user": user_prompt}

    def _extract_question_from_openai(self, response: Union[Dict[str, Any], Any]) -> Optional[Dict[str, Any]]:
        """
        Extract and validate the question from OpenAI's response.

        Args:
            response: The response from OpenAI, which could be a dict, string, or other type

        Returns:
            Dict with question data or None if extraction failed
        """
        try:
            # Check if the response is already in JSON format with question text
            if isinstance(response, dict):
                if "text" in response:
                    return response

                # Handle OpenAI API response format
                if "choices" in response and isinstance(response["choices"], list) and response["choices"]:
                    if "message" in response["choices"][0] and isinstance(response["choices"][0]["message"], dict):
                        content = response["choices"][0]["message"].get("content", "")
                        if content:
                            # Try to extract JSON from the content
                            json_match = re.search(r'\{.*\}', content, re.DOTALL)
                            if json_match:
                                json_str = json_match.group(0)
                                try:
                                    question_data = json.loads(json_str)
                                    if isinstance(question_data, dict) and "text" in question_data:
                                        return question_data
                                except json.JSONDecodeError:
                                    logger.warning("Failed to parse JSON from OpenAI response content")

            # If it's a string response, try to extract JSON
            if isinstance(response, str):
                # Extract JSON using regex if needed
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        question_data = json.loads(json_str)
                        if isinstance(question_data, dict) and "text" in question_data:
                            return question_data
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON from string response")

            # If we couldn't parse JSON, create a basic question
            logger.warning("Could not extract JSON from OpenAI response, creating basic question")
            return {
                "id": str(uuid.uuid4()),
                "text": str(response)[:200] if response is not None else "Please describe any significant life events.",
                "category": "general",
                "type": "text"
            }
        except Exception as e:
            logger.error(f"Error extracting question from OpenAI response: {e}")
            return {
                "id": str(uuid.uuid4()),
                "text": "Please describe any significant life events that might correlate with your birth time.",
                "category": "life_events",
                "type": "text"
            }

    def _summarize_chart_data(self, chart_data: Dict) -> str:
        """Summarize chart data for inclusion in the OpenAI prompt."""
        summary_parts = []

        # Extract key elements from chart data
        if "birth_data" in chart_data:
            birth_data = chart_data["birth_data"]
            if birth_data:
                date_str = birth_data.get("date", "Unknown date")
                time_str = birth_data.get("time", "Unknown time")
                location_str = birth_data.get("location", "Unknown location")
                summary_parts.append(f"Birth Details: {date_str} at {time_str} in {location_str}")

        # Extract planetary positions
        if "planets" in chart_data:
            planets = chart_data["planets"]
            if planets:
                planet_positions = []
                for planet, data in planets.items():
                    sign = data.get("sign", "")
                    house = data.get("house", "")
                    if sign and house:
                        planet_positions.append(f"{planet} in {sign} (House {house})")

                if planet_positions:
                    summary_parts.append("Planetary Positions: " + "; ".join(planet_positions))

        # Extract ascendant/rising sign
        if "ascendant" in chart_data:
            ascendant = chart_data["ascendant"]
            if ascendant:
                summary_parts.append(f"Ascendant/Rising: {ascendant}")

        # Extract dashas if available
        if "dashas" in chart_data:
            dashas = chart_data["dashas"]
            if dashas:
                dasha_str = f"Current Dasha: {dashas.get('current_maha_dasha', '')}, Sub-dasha: {dashas.get('current_antar_dasha', '')}"
                summary_parts.append(dasha_str)

        # Join all parts with newlines
        return "\n".join(summary_parts)

    async def calculate_confidence(self, answers: Dict[str, Any], chart_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate confidence score based on answers using Vedic astrological principles.

        Args:
            answers: Dictionary with answer data
            chart_data: Optional chart data (used to adjust confidence based on chart quality)

        Returns:
            Confidence score (0-100)
        """
        # Extract responses
        responses = answers.get("responses", [])
        if not responses:
            return 40.0  # Base confidence for questionnaires with no answers

        # Count the number of responses - this is a key factor
        num_answers = len(responses)

        # Track Vedic astrological indicators with expanded categories
        vedic_indicators = {
            "birth_time_precision": 0.0,     # 0-10 scale - highest priority
            "life_events_correlation": 0.0,  # 0-10 scale - high priority
            "dasha_alignment": 0.0,          # 0-10 scale - high priority
            "personality_house_alignment": 0.0, # 0-10 scale
            "timing_preferences_alignment": 0.0, # 0-10 scale
            "physical_traits_correlation": 0.0, # 0-10 scale
            "nakshatra_alignment": 0.0,      # 0-10 scale
            "relationship_patterns": 0.0,    # 0-10 scale
            "career_developments": 0.0,      # 0-10 scale
            "spiritual_inclinations": 0.0    # 0-10 scale
        }

        # More gradual base confidence scaling - requires more questions to reach higher levels
        # Set a lower cap to ensure we don't reach high confidence too easily
        base_confidence = min(40.0 + (num_answers * 3.5), 70.0)  # 40-70 range, requires 8+ questions

        # Answer quality bonus - more conservative and requires true quality
        answer_quality_bonus = 0.0
        for response in responses:
            answer = str(response.get("answer", ""))
            # Only give bonuses for truly detailed answers
            if len(answer) > 150:  # Very detailed answer
                answer_quality_bonus += 2.5  # Reduced bonus
            elif len(answer) > 80:  # Detailed answer
                answer_quality_bonus += 1.5  # Reduced bonus
            elif len(answer) > 40:  # Moderately detailed
                answer_quality_bonus += 1.0  # Reduced bonus

        # Cap answer quality bonus at a more reasonable level
        answer_quality_bonus = min(answer_quality_bonus, 15.0)  # Lower cap

        # Parse responses for Vedic indicators - more balanced scoring
        for response in responses:
            question_id = response.get("question_id", "")
            question_text = str(response.get("question", "")).lower()
            answer_text = str(response.get("answer", "")).lower()

            # Birth time precision indicators - critical for rectification
            if "birth time" in question_text or "birth_time" in question_id or "lagna" in question_text or "rising sign" in question_text:
                if "exact" in answer_text or "precise" in answer_text:
                    vedic_indicators["birth_time_precision"] += 6.0  # Reduced from higher values
                elif "approximate" in answer_text:
                    vedic_indicators["birth_time_precision"] += 4.0  # Reduced from higher values
                elif "window" in answer_text or "morning" in answer_text or "afternoon" in answer_text:
                    vedic_indicators["birth_time_precision"] += 3.0  # Reduced from higher values
                elif "earlier" in answer_text or "later" in answer_text:
                    vedic_indicators["birth_time_precision"] += 5.0  # Reduced from higher values

            # Life events correlation - critical for accurate birth time
            if ("life events" in question_text or "major" in question_text or
                "significant" in question_text or "changes" in question_text):

                # More realistic scoring based on actual content
                import re

                # Basic scoring based on length
                detail_level = min(len(answer_text) / 40, 4.0)  # Reduced multiplier

                # Count specific dates and years
                specific_years = len(re.findall(r'\b(19|20)\d{2}\b', answer_text)) * 1.5  # Reduced multiplier
                months = len(re.findall(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december)\b', answer_text, re.I)) * 0.5

                # Life transitions keywords
                transitions = len(re.findall(r'\b(graduate|marriage|divorce|birth|death|move|career|job|relationship|breakup|promotion|started|ended|change)\b', answer_text, re.I)) * 0.7

                vedic_indicators["life_events_correlation"] += min(detail_level + specific_years + months * 0.4 + transitions, 8.0)  # Cap at 8.0

            # Other Vedic indicators - more conservative scoring
            # Only analyze other indicators if we have substantial content
            if len(answer_text) > 30:
                # Personality traits
                if "personality" in question_text or "traits" in question_text:
                    # Calculate score based on traits mentioned, more conservative
                    traits_score = 0.0
                    if any(trait in answer_text for trait in ["confident", "leader", "authoritative", "strong", "proud"]):
                        traits_score += 1.0
                    if any(trait in answer_text for trait in ["emotional", "intuitive", "nurturing", "caring", "sensitive"]):
                        traits_score += 1.0
                    if any(trait in answer_text for trait in ["analytical", "precise", "communicative", "logical", "intelligent"]):
                        traits_score += 1.0

                    vedic_indicators["personality_house_alignment"] += min(traits_score, 6.0)

                # Time of day preferences - important for birth time
                if "rhythm" in question_text or "energy" in question_text or "time of day" in question_text:
                    # More conservative scoring based on specificity
                    time_score = 0.0
                    if any(word in answer_text for word in ["morning", "sunrise", "dawn", "evening", "sunset", "night", "midnight"]):
                        time_score += 3.0
                    if any(word in answer_text for word in ["specific", "exactly", "always", "consistent"]):
                        time_score += 2.0

                    vedic_indicators["timing_preferences_alignment"] += min(time_score, 5.0)

        # Calculate Vedic score as sum of indicators, weighted appropriately
        # Higher weight for birth time precision and life events correlation
        vedic_score = (
            vedic_indicators["birth_time_precision"] * 1.2 +  # Weight: 1.2
            vedic_indicators["life_events_correlation"] * 1.1 +  # Weight: 1.1
            vedic_indicators["dasha_alignment"] * 0.8 +  # Weight: 0.8
            vedic_indicators["personality_house_alignment"] * 0.7 +  # Weight: 0.7
            vedic_indicators["timing_preferences_alignment"] * 0.9 +  # Weight: 0.9
            vedic_indicators["physical_traits_correlation"] * 0.6 +  # Weight: 0.6
            vedic_indicators["nakshatra_alignment"] * 0.5 +  # Weight: 0.5
            vedic_indicators["relationship_patterns"] * 0.6 +  # Weight: 0.6
            vedic_indicators["career_developments"] * 0.7 +  # Weight: 0.7
            vedic_indicators["spiritual_inclinations"] * 0.4  # Weight: 0.4
        )

        # Calculate Vedic confidence as percentage of maximum possible score (100)
        # More conservative scaling that doesn't inflate scores
        vedic_confidence = min(vedic_score * 0.75, 70.0)  # Reduced multiplier, cap at 70

        # Combine base confidence and Vedic confidence with answer quality
        total_confidence = base_confidence + answer_quality_bonus + vedic_confidence

        # Cap total confidence
        # - Requires ≤5 questions: max 70%
        # - Requires 6-9 questions: max 85%
        # - Requires 10+ questions: max 95%
        if num_answers <= 5:
            total_confidence = min(total_confidence, 70.0)
        elif num_answers <= 9:
            total_confidence = min(total_confidence, 85.0)
        else:
            total_confidence = min(total_confidence, 95.0)

        # Log all components for debugging
        logger.info(f"Base confidence: {base_confidence}, Answer quality bonus: {answer_quality_bonus}")
        logger.info(f"Vedic indicators: {vedic_indicators}")
        logger.info(f"Vedic score: {vedic_score}, Vedic confidence: {vedic_confidence}")
        logger.info(f"Total confidence: {total_confidence}")

        return total_confidence

    def _format_chart_for_prompt(self, chart_data: Dict[str, Any]) -> str:
        """
        Format chart data into a comprehensive Vedic astrological summary for prompts.
        """
        if not chart_data:
            return "Chart data not available."

        # Extract key chart elements with focus on Vedic astrology
        ascendant = chart_data.get("houses", {}).get("1", {}).get("sign", "Unknown")
        planets = chart_data.get("planets", {})
        birth_details = chart_data.get("birth_details", {})

        # Create a detailed summary focusing on Vedic astrological elements
        summary = [
            f"Ascendant (Lagna/Rising Sign): {ascendant}",
            f"Birth Date: {birth_details.get('birth_date', 'Unknown')}",
            f"Birth Time: {birth_details.get('birth_time', 'Unknown')}",
            f"Location: Latitude {birth_details.get('latitude', 'Unknown')}, Longitude {birth_details.get('longitude', 'Unknown')}",
            "\nPlanet Positions (Vedic/Sidereal):"
        ]

        # Add planet positions with houses and nakshatras if available
        for planet in PLANETS_LIST:
            if planet in planets:
                planet_data = planets[planet]
                sign = planet_data.get("sign", "Unknown")
                house = planet_data.get("house", "Unknown")
                degree = planet_data.get("degree", "Unknown")
                nakshatra = planet_data.get("nakshatra", "Unknown")
                summary.append(f"- {planet} in {sign} {degree}° (House {house}, Nakshatra: {nakshatra})")

        # Add special Vedic elements if available
        if "dashas" in chart_data:
            dashas = chart_data.get("dashas", {})
            summary.append("\nDasha Information:")
            if "current_maha_dasha" in dashas:
                summary.append(f"- Current Maha Dasha: {dashas.get('current_maha_dasha', {}).get('planet', 'Unknown')}")
            if "current_antar_dasha" in dashas:
                summary.append(f"- Current Antar Dasha: {dashas.get('current_antar_dasha', {}).get('planet', 'Unknown')}")

        return "\n".join(summary)

    async def analyze_answers(self, chart_data: Optional[Dict[str, Any]], answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze questionnaire answers to identify birth time patterns using OpenAI and Vedic astrology.

        Args:
            chart_data: Optional chart data (used for correlation with answers)
            answers: Dictionary with answer data (used to extract time indicators)

        Returns:
            Analysis results with potential birth time adjustment
        """
        responses = answers.get("responses", [])
        if not responses:
            return {
                "success": False,
                "message": "No responses to analyze",
                "analysis_result": {
                    "confidence_score": 0.0,
                    "adjustment_direction": "none",
                    "adjustment_minutes": 0
                }
            }

        # Initialize variables with defaults to avoid 'used before assignment' errors
        adjustment_direction = "none"
        adjustment_minutes = 0
        analysis_explanation = "Analysis based on questionnaire answers and Vedic chart data."

        # Calculate initial confidence score using Vedic principles
        confidence_score = await self.calculate_confidence(answers, chart_data)
        logger.info(f"Initial Vedic confidence score: {confidence_score}")

        # Get the OpenAI service if it's available
        openai_service = None
        if self._openai_service_getter:
            try:
                openai_service = await self._openai_service_getter()
            except Exception as e:
                logger.error(f"Error getting OpenAI service: {e}")
                openai_service = None

        # Format responses for better analysis
        formatted_responses = []
        for response in responses:
            question = response.get("question", "")
            answer = response.get("answer", "")
            if question and answer:
                formatted_responses.append(f"Q: {question}\nA: {answer}")

        responses_text = "\n\n".join(formatted_responses)

        # Create birth details text from chart data
        birth_details_text = "Birth details not available."
        original_birth_time = None
        if chart_data:
            birth_details = chart_data.get("birth_details", {})
            if birth_details:
                birth_date = birth_details.get("birth_date", "Unknown")
                birth_time = birth_details.get("birth_time", "Unknown")
                original_birth_time = birth_time
                latitude = birth_details.get("latitude", "Unknown")
                longitude = birth_details.get("longitude", "Unknown")
                timezone = birth_details.get("timezone", "Unknown")

                birth_details_text = f"""
                Birth Date: {birth_date}
                Birth Time: {birth_time}
                Location: {latitude}, {longitude}
                Timezone: {timezone}
                """

        # Try to use OpenAI for advanced Vedic astrological analysis
        if openai_service:
            try:
                # Create a specialized prompt for Vedic birth time rectification
                prompt = {
                    "task": "vedic_birth_time_rectification",
                    "birth_details": birth_details_text,
                    "questionnaire_responses": responses_text,
                    "instructions": """
                    Based on the questionnaire responses and birth details provided, analyze the birth time
                    from a Vedic astrological perspective. Provide a comprehensive birth time rectification analysis.

                    ANALYSIS REQUIREMENTS:
                    1. Determine if the birth time needs adjustment (earlier/later) based on Vedic principles
                    2. Calculate the precise minutes of adjustment needed (0-60 minutes)
                    3. Assess confidence level in this determination (0-100%)
                    4. Identify specific Vedic indicators that inform your rectification
                    5. Consider these key factors:
                       - Ascendant (Lagna) alignment with personality traits described
                       - Moon nakshatra correlation with emotional patterns
                       - Alignment of significant life events with dasha periods
                       - House placements and aspects relevant to questionnaire responses
                       - Natural timing preferences mentioned by the individual

                    DECISION CRITERIA:
                    - Recommend NO adjustment if confidence is below 70% or indicators are contradictory
                    - For confidence 70-85%, recommend minor adjustments (5-15 minutes) if indicators agree
                    - For confidence 85%+, recommend precise adjustments based on strongest indicators
                    - Adjustment direction (forward/backward) must be supported by multiple indicators

                    RESPONSE FORMAT:
                    Respond with a JSON object containing:
                    {
                      "analysis": "Detailed explanation of birth time rectification reasoning with specific Vedic principles cited",
                      "adjustment_direction": "forward", "backward", or "none",
                      "adjustment_minutes": integer (0-60),
                      "confidence_score": float (0-100),
                      "vedic_indicators": ["List", "of", "specific", "indicators", "observed"],
                      "original_birth_time": "The original birth time",
                      "adjusted_birth_time": "The adjusted birth time in same format" (only if adjustment needed)
                    }

                    RETURN ONLY THE JSON OBJECT. Do not include additional explanations or markdown.
                    """
                }

                # Call OpenAI for Vedic birth time analysis
                try:
                    analysis_response = await openai_service.chat_completion(
                        messages=[
                            {"role": "system", "content": "You are an expert Vedic astrologer specializing in birth time rectification."},
                            {"role": "user", "content": json.dumps(prompt)}
                        ],
                        model="gpt-4o-mini",  # Use available model
                        temperature=0.3,
                        max_tokens=1000
                    )

                    # Process OpenAI response with proper type checking
                    if (isinstance(analysis_response, dict) and
                        "choices" in analysis_response and
                        isinstance(analysis_response["choices"], list) and
                        len(analysis_response["choices"]) > 0):

                        content = analysis_response["choices"][0]["message"]["content"]
                        logger.info(f"Received Vedic analysis from OpenAI: {content[:200]}...")

                        # Try to parse as JSON
                        try:
                            parsed_result = json.loads(content)
                            if isinstance(parsed_result, dict):
                                # Extract results
                                adjustment_direction = parsed_result.get("adjustment_direction", "none")
                                adjustment_minutes = int(parsed_result.get("adjustment_minutes", 0))

                                # Get confidence score from OpenAI or use our calculated value
                                api_confidence = parsed_result.get("confidence_score")
                                if api_confidence is not None:
                                    api_confidence = float(api_confidence)
                                    # Only use OpenAI confidence if higher than our calculation
                                    if api_confidence > confidence_score:
                                        confidence_score = api_confidence

                                analysis_explanation = parsed_result.get("analysis", "Analysis based on questionnaire answers and Vedic chart data.")
                                logger.info(f"Successfully parsed OpenAI Vedic response: adjustment={adjustment_direction}, minutes={adjustment_minutes}")
                        except json.JSONDecodeError:
                            # If JSON parsing fails, try to extract key information from the response text
                            content_lines = content.split('\n')
                            adjustment_line = next((line for line in content_lines if "adjustment" in line.lower()), "")
                            if "forward" in adjustment_line.lower():
                                adjustment_direction = "forward"
                            elif "backward" in adjustment_line.lower():
                                adjustment_direction = "backward"

                            # Try to extract minutes
                            minutes_match = re.search(r'(\d+)\s*minutes?', content)
                            if minutes_match:
                                adjustment_minutes = int(minutes_match.group(1))

                            # Extract explanation paragraphs
                            paragraphs = [line for line in content_lines if line.strip()]
                            if paragraphs:
                                analysis_explanation = paragraphs[-1].strip()
                except Exception as e:
                    logger.error(f"Error during OpenAI chat completion: {e}")
                    logger.error(traceback.format_exc())
            except Exception as e:
                logger.error(f"Error during OpenAI Vedic analysis: {e}")
                logger.error(traceback.format_exc())

        # If OpenAI failed or is not available, use Vedic astrological principles for calculation
        if adjustment_direction == "none" and chart_data and confidence_score >= 80:
            logger.info("Using Vedic astrological calculation for timing adjustment")

            # Get ascendant sign and degree
            ascendant_sign = chart_data.get("ascendant", {}).get("sign", "")
            ascendant_degree = chart_data.get("ascendant", {}).get("degree", 0)

            # Apply Vedic birth time rectification principles based on ascendant
            if ascendant_sign in ["Aries", "Libra"]:
                # Usually accurate timing, minimal adjustment needed
                if ascendant_degree < 3 or ascendant_degree > 27:
                    adjustment_direction = "forward" if ascendant_degree < 3 else "backward"
                    adjustment_minutes = 5
                    logger.info(f"Aries/Libra ascendant at {ascendant_degree}° suggests {adjustment_direction} adjustment")

            elif ascendant_sign in ["Gemini", "Sagittarius"]:
                # Often earlier birth than recorded
                adjustment_direction = "backward"
                adjustment_minutes = min(int(10 + ascendant_degree/3), 20)
                logger.info(f"Gemini/Sagittarius ascendant suggests birth time was earlier: {adjustment_minutes} minutes {adjustment_direction}")

            elif ascendant_sign in ["Cancer", "Capricorn"]:
                # Often later birth than recorded
                adjustment_direction = "forward"
                adjustment_minutes = min(int(10 + (30-ascendant_degree)/3), 20)
                logger.info(f"Cancer/Capricorn ascendant suggests birth time was later: {adjustment_minutes} minutes {adjustment_direction}")

            elif ascendant_sign in ["Leo", "Aquarius"]:
                # Adjust based on degree
                if ascendant_degree < 15:
                    adjustment_direction = "forward"
                    adjustment_minutes = min(int(15 - ascendant_degree), 15)
                else:
                    adjustment_direction = "backward"
                    adjustment_minutes = min(int(ascendant_degree - 15), 15)
                logger.info(f"Leo/Aquarius ascendant at {ascendant_degree}° suggests {adjustment_direction} adjustment of {adjustment_minutes} minutes")

            elif ascendant_sign in ["Virgo", "Pisces"]:
                # Usually small adjustment
                adjustment_direction = "backward" if ascendant_degree > 15 else "forward"
                adjustment_minutes = min(abs(int(15 - ascendant_degree)/3), 10)
                logger.info(f"Virgo/Pisces ascendant suggests {adjustment_direction} adjustment of {adjustment_minutes} minutes")

            # Check Moon nakshatra for further refinement
            moon_data = None
            planets = chart_data.get("planets", {})
            for planet_key, planet_data in planets.items():
                if isinstance(planet_data, dict) and planet_data.get("name") == "Moon":
                    moon_data = planet_data
                    break

            if moon_data:
                moon_nakshatra = moon_data.get("nakshatra", "")
                # Apply Vedic nakshatra principles
                if moon_nakshatra in ["Ashwini", "Magha", "Mula"]:
                    # Fire nakshatras - tends to indicate earlier birth
                    if adjustment_direction == "none":
                        adjustment_direction = "backward"
                        adjustment_minutes = 10
                    elif adjustment_direction == "backward":
                        adjustment_minutes = min(adjustment_minutes + 5, 30)
                    logger.info(f"Moon in fire nakshatra {moon_nakshatra} refines adjustment: {adjustment_direction} {adjustment_minutes} min")

                elif moon_nakshatra in ["Rohini", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada"]:
                    # Fixed nakshatras - suggests accurate recording
                    adjustment_minutes = max(adjustment_minutes - 5, 0)
                    if adjustment_minutes == 0:
                        adjustment_direction = "none"
                    logger.info(f"Moon in fixed nakshatra {moon_nakshatra} suggests more accurate recording, reducing adjustment")

            # Add Vedic explanation
            analysis_explanation = (
                f"Based on Vedic astrological principles, with {ascendant_sign} ascendant at {ascendant_degree}°, "
                f"a {adjustment_direction} adjustment of {adjustment_minutes} minutes is indicated. "
            )
            if moon_data:
                analysis_explanation += f"Moon in {moon_data.get('nakshatra', 'unknown')} nakshatra "
                analysis_explanation += "confirms this assessment." if adjustment_direction != "none" else "suggests minimal adjustment needed."

        # Apply the adjustment to get the adjusted birth time
        adjusted_birth_time = None
        original_birth_time = None

        if chart_data and "birth_details" in chart_data:
            birth_details = chart_data.get("birth_details", {})
            original_birth_time = birth_details.get("birth_time") or birth_details.get("time")

            if original_birth_time and adjustment_direction != "none" and adjustment_minutes > 0:
                try:
                    # Parse the time
                    time_parts = original_birth_time.split(":")
                    hours = int(time_parts[0])
                    minutes = int(time_parts[1])
                    seconds = int(time_parts[2]) if len(time_parts) > 2 else 0

                    # Calculate adjustment
                    adjustment_factor = 1 if adjustment_direction == "forward" else -1
                    total_minutes = hours * 60 + minutes
                    new_total_minutes = total_minutes + (adjustment_factor * int(adjustment_minutes))

                    # Ensure total minutes is within valid range
                    while new_total_minutes < 0:
                        new_total_minutes += 1440  # Add a day
                    while new_total_minutes >= 1440:
                        new_total_minutes -= 1440  # Subtract a day

                    # Convert back to hours and minutes
                    new_hours = new_total_minutes // 60
                    new_minutes = new_total_minutes % 60

                    # Format the new time
                    adjusted_birth_time = f"{new_hours:02d}:{new_minutes:02d}:{seconds:02d}"
                    logger.info(f"Adjusted birth time using Vedic principles: {original_birth_time} → {adjusted_birth_time} ({adjustment_direction} by {adjustment_minutes} min)")
                except Exception as e:
                    logger.error(f"Error calculating adjusted birth time: {e}")

        # Return the final analysis result with Vedic details
        analysis_result = {
            "adjustment_direction": adjustment_direction,
            "adjustment_minutes": adjustment_minutes,
            "confidence_score": confidence_score,
            "key_indicators": [],
            "analysis": analysis_explanation,
            "original_birth_time": original_birth_time,
            "adjusted_birth_time": adjusted_birth_time,
            "vedic_assessment": True
        }

        logger.info(f"Final Vedic analysis result: {adjustment_direction=}, {adjustment_minutes=}, {confidence_score=}")

        return {
            "success": True,
            "analysis_result": analysis_result
        }

    def _get_template_questions(self) -> List[Dict[str, Any]]:
        """Raise an exception to prevent falling back to static template questions."""
        logger.error("Attempted to use template questions, which is not allowed")
        raise Exception("Real-time question generation is required - no template questions permitted")
