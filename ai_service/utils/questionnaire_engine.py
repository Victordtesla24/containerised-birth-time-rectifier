"""
Questionnaire engine for Birth Time Rectifier API.
Handles generation and processing of questions for birth time rectification.
Uses OpenAI for verifying chart data against Indian Vedic Astrological standards.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
import random
import asyncio
import json
from datetime import datetime, timedelta
import re

# Try to import pytz properly with exception handling
try:
    import pytz
except ImportError:
    raise ImportError("The pytz module is required for timezone operations in the questionnaire engine. Please install it using 'pip install pytz'.")

# Add type checker directive to ignore FixtureFunction related errors
# pyright: reportInvalidTypeForm=false
# pyright: reportUndefinedVariable=false

# Import AI services
from ai_service.api.services.openai import get_openai_service

# Import the modularized rectification structure
from ai_service.core.rectification.chart_calculator import calculate_chart
from ai_service.core.rectification.constants import PLANETS_LIST
from ai_service.utils.constants import ZODIAC_SIGNS

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
        # Set up OpenAI service if available
        try:
            from ai_service.api.services.openai.service import OpenAIService
            self.openai_service = OpenAIService()
            logger.info("Initialized OpenAI service for questionnaire")
        except (ImportError, Exception) as e:
            logger.warning(f"Could not initialize OpenAI service: {str(e)}")
            self.openai_service = None

        # Enhanced tracking for question history and answer analysis
        self.question_history = {}  # Track questions by session ID
        self.answer_history = {}    # Track answers by session ID
        self.birth_time_indicators = {}  # Track birth time indicators by session ID

    async def get_first_question(self, chart_data: Dict[str, Any], birth_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the first question for a new questionnaire session, focusing on physical traits
        related to the Ascendant which is highly time-sensitive.
        """
        if not self.openai_service:
            raise ValueError("OpenAI service is required for dynamic question generation")

        # Format chart data to focus on Ascendant and time-sensitive factors
        chart_summary = self._format_chart_for_prompt(chart_data)

        # Create a focused prompt for the first question
        prompt = f"""
        As an expert astrologer specializing in birth time rectification, generate the FIRST question
        to ask a person to help determine their precise birth time.

        BIRTH DETAILS:
        Date: {birth_details.get("birth_date", birth_details.get("birthDate", ""))}
        Approximate Time: {birth_details.get("birth_time", birth_details.get("birthTime", ""))}
        Location: {birth_details.get("birth_place", birth_details.get("birthPlace", ""))}

        CHART INFORMATION:
        {chart_summary}

        The first question should focus on physical appearance traits related to the Ascendant (Rising Sign).
        The Ascendant changes approximately every 2 hours, making it the most critical factor for birth time rectification.

        Focus on physical traits like:
        - Face shape and features
        - Body type and build
        - Hair characteristics
        - Distinctive physical attributes
        - Overall physical appearance

        RESPONSE FORMAT:
        Return only a JSON object with these fields:
        - id: a unique identifier (use a random string)
        - text: the question text
        - type: "text" or "multiple_choice" or "yes_no"
        - options: an array of options if multiple_choice (include at least 4 options)
        - category: "physical_traits"
        - relevance_to_birth_time: explanation of how physical traits relate to birth time

        The question must be easily understandable by someone without astrological knowledge.
        PROVIDE ONLY THE JSON OBJECT AND NO OTHER TEXT.
        """

        # Get response from OpenAI
        response = await self.openai_service.generate_completion(
            prompt=prompt,
            task_type="birth_time_rectification_questionnaire",
            max_tokens=500,
            temperature=0.7
        )

        # Parse the response
        question_data = self._parse_question_response(response.get("content", ""))

        # Ensure it has a unique ID
        if "id" not in question_data:
            question_data["id"] = f"q_{uuid.uuid4().hex[:8]}"

        # Ensure category is set to physical_traits for first question
        question_data["category"] = "physical_traits"

        return question_data

    async def generate_dynamic_question(
        self,
        chart_data: Dict[str, Any],
        previous_answers: Dict[str, Any],
        current_confidence: float,
        session_id: str = "default",
        diversity_factor: float = 0.0
    ) -> Dict[str, Any]:
        """
        Generate a dynamic question based on previous answers and current chart data.

        Args:
            chart_data: The natal chart data
            previous_answers: Previous questions and answers
            current_confidence: Current confidence in birth time
            session_id: Unique session identifier
            diversity_factor: Factor to increase question diversity (0.0-1.0)

        Returns:
            Dict containing the next question

        Raises:
            RuntimeError: If question generation fails after retries
        """
        if not self.openai_service:
            raise RuntimeError("OpenAI service is required but not available")

        # Extract relevant responses
        responses = previous_answers.get("responses", [])

        # Add previous answers to history
        self.answer_history[session_id].extend(responses)

        # Identify uncertain factors related to birth time
        uncertain_factors = self._identify_uncertain_factors(chart_data)
        uncertain_factors_text = ", ".join(uncertain_factors) if uncertain_factors else "No specific uncertain factors identified"

        # Calculate question count
        question_count = len(responses)

        # Determine question category based on progression
        # Now using the new _determine_next_category method
        category = self._determine_next_category(responses)

        # Extract previously asked questions to avoid repetition
        asked_questions = [q.get("text", "").lower() for q in self.question_history.get(session_id, [])]

        # Create duplicate avoidance instructions
        duplicate_avoidance = ""
        if asked_questions:
            duplicate_avoidance = "IMPORTANT: DO NOT repeat similar questions to any of these previously asked questions:\n- " + "\n- ".join(asked_questions[:5])
            if len(asked_questions) > 5:
                duplicate_avoidance += f"\n- ... and {len(asked_questions) - 5} more questions"

        # Add diversity factor instructions
        diversity_instructions = ""
        if diversity_factor > 0:
            diversity_instructions = f"\nIMPORTANT: Ensure this question is COMPLETELY DIFFERENT from previous questions. Creativity factor: {diversity_factor:.1f}"

        # Create enhanced prompt with astrological expertise
        prompt = f"""
        As an expert astrologer specializing in birth time rectification, your task is to generate the most effective next question
        to help determine this person's precise birth time. The current confidence in the birth time is {current_confidence}%.

        CRITICAL ASTROLOGICAL CONTEXT:
        {self._format_chart_for_prompt(chart_data)}

        UNCERTAIN BIRTH TIME FACTORS REQUIRING CLARIFICATION:
        {uncertain_factors_text}

        PREVIOUS QUESTIONS AND ANSWERS:
        {self._format_answers_for_prompt(responses)}

        RECTIFICATION CONTEXT:
        - Current question count: {question_count}
        - Current birth time confidence: {current_confidence:.1f}%
        - Question category: {category}

        {duplicate_avoidance}
        {diversity_instructions}

        BIRTH TIME RECTIFICATION TECHNIQUES TO CONSIDER:
        1. Life events that correlate with angular transits or progressions
        2. Physical appearance related to Ascendant/1st house placements
        3. Personality traits correlating with Ascendant, Moon, and Mercury
        4. Major relationship events connected to 7th house or Venus transits
        5. Career developments linked to MC/10th house placements
        6. Family dynamics related to 4th house/IC placements
        7. Health matters connected to 6th house placements
        8. Spiritual experiences related to 12th house or Neptune placements

        RESPONSE FORMAT:
        Return ONLY a JSON object with these fields:
        - id: a unique identifier (use a random string)
        - text: the carefully crafted question text
        - type: "text", "multiple_choice", or "yes_no"
        - options: an array of options if multiple_choice (include at least 4 options)
        - category: "{category}"
        - relevance_to_birth_time: explanation of how this helps with rectification

        IMPORTANT: The question should be easily understandable by someone without astrological knowledge.
        PROVIDE ONLY THE JSON OBJECT AND NO OTHER TEXT.
        """

        try:
            # Call OpenAI with enhanced prompt
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="birth_time_rectification_questionnaire",
                max_tokens=800,
                temperature=0.7 + (diversity_factor * 0.3)  # Increase temperature for more diverse questions
            )

            # Parse the response
            question_data = self._parse_question_response(response.get("content", ""))

            # Ensure required fields
            if "id" not in question_data:
                question_data["id"] = f"q_{uuid.uuid4().hex[:8]}"

            if "category" not in question_data:
                question_data["category"] = category

            # Format options for multiple choice
            if question_data.get("type") == "multiple_choice" and "options" in question_data:
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

            # Add to question history
            self.question_history[session_id].append(question_data)

            return question_data

        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")
            raise RuntimeError(f"Failed to generate question: {str(e)}")

    def _identify_uncertain_factors(self, chart_data: Dict[str, Any]) -> List[str]:
        """
        Identify factors in the chart that have high uncertainty related to birth time.
        """
        uncertain_factors = []

        if not chart_data:
            return ["ascendant", "house_cusps", "moon_position"]  # Default factors if no chart

        # Check for planets near house cusps (highly sensitive to birth time)
        houses = chart_data.get("houses", [])
        planets = chart_data.get("planets", [])

        # Extract house cusps
        house_cusps = []
        for house in houses:
            if isinstance(house, dict):
                sign = house.get("sign", "")
                degree = house.get("degree", 0)
                number = house.get("number", 0)
                if sign and degree is not None and number:
                    house_cusps.append({
                        "house": number,
                        "sign": sign,
                        "degree": float(degree) if isinstance(degree, (int, float, str)) else 0,
                        "is_angular": number in [1, 4, 7, 10]
                    })

        # Check planets near cusps (especially angular houses)
        for planet in planets:
            if not isinstance(planet, dict):
                continue

            planet_name = planet.get("planet", "")
            planet_sign = planet.get("sign", "")
            planet_degree = planet.get("degree", 0)

            if not planet_name or not planet_sign:
                continue

            # Skip non-physical points for some checks
            if planet_name in ["Ascendant", "MC", "Midheaven", "IC", "Descendant", "DSC"]:
                continue

            # Check proximity to house cusps
            for cusp in house_cusps:
                if planet_sign == cusp["sign"]:
                    degree_diff = abs(float(planet_degree) - float(cusp["degree"]))
                    if degree_diff <= 3 or degree_diff >= 27:  # Within 3 degrees of cusp
                        is_angular = cusp.get("is_angular", False)
                        if is_angular:
                            uncertain_factors.append(f"{planet_name.lower()}_near_house_{cusp.get('house', 'unknown')}")

        # Ascendant is always a key uncertain factor in birth time rectification
        uncertain_factors.append("ascendant_sign_and_degree")

        # Moon position is quite sensitive to birth time (moves ~12° per day)
        uncertain_factors.append("moon_house_position")

        # Check for planets in angular houses (1, 4, 7, 10)
        planets_in_angular_houses = []
        for planet in planets:
            if not isinstance(planet, dict):
                continue

            planet_name = planet.get("planet", "")
            planet_house = planet.get("house", 0)

            if planet_name and planet_house in [1, 4, 7, 10]:
                planets_in_angular_houses.append(f"{planet_name.lower()}_in_house_{planet_house}")

        if planets_in_angular_houses:
            uncertain_factors.extend(planets_in_angular_houses)
        else:
            uncertain_factors.append("planets_in_angular_houses")

        # Return unique factors, prioritizing the most time-sensitive ones
        unique_factors = list(dict.fromkeys(uncertain_factors))
        return unique_factors[:8]  # Return top 8 uncertain factors

    def _format_chart_for_prompt(self, chart_data: Dict[str, Any]) -> str:
        """
        Format chart data into a concise summary for LLM prompts.
        """
        if not chart_data:
            return "Chart data not available."

        # Extract key chart elements
        ascendant = chart_data.get("houses", {}).get("1", {}).get("sign", "Unknown")
        planets = chart_data.get("planets", {})

        # Create a summary focusing on most relevant elements for birth time
        summary = [
            f"Ascendant (Rising Sign): {ascendant}",
            "Planet Positions:"
        ]

        # Add planet positions
        for planet in PLANETS_LIST:
            if planet in planets:
                planet_data = planets[planet]
                sign = planet_data.get("sign", "Unknown")
                house = planet_data.get("house", "Unknown")
                summary.append(f"- {planet} in {sign} (House {house})")

        return "\n".join(summary)

    def _format_answers_for_prompt(self, previous_answers: List[Dict[str, Any]]) -> str:
        """
        Format previous answers into context for the next question prompt.

        Args:
            previous_answers: List of previous question-answer pairs

        Returns:
            Formatted context string
        """
        if not previous_answers:
            return "No previous answers available."

        context_lines = ["PREVIOUS QUESTIONS AND ANSWERS:"]

        for i, qa_pair in enumerate(previous_answers):
            question = qa_pair.get("question", "")
            answer = qa_pair.get("answer", "")

            if question and answer:
                context_lines.append(f"Q{i+1}: {question}")
                context_lines.append(f"A{i+1}: {answer}")
                context_lines.append("")

        return "\n".join(context_lines)

    def _determine_next_category(self, previous_answers: List[Dict[str, Any]]) -> str:
        """
        Determine the best category for the next question based on previous answers.

        Args:
            previous_answers: List of previous question-answer pairs

        Returns:
            Category name for the next question
        """
        # Define progression of categories for comprehensive birth time rectification
        progression = [
            "physical_traits",      # First focus on physical appearance (Ascendant)
            "personality",          # Then personality traits (Moon, Mercury)
            "life_events",          # Major life events (Saturn, Jupiter transits)
            "timing_preferences",   # Daily rhythms (Sun, Mercury)
            "relationships",        # Relationship patterns (Venus, Mars, 7th house)
            "career",               # Career developments (10th house, Saturn)
            "health",               # Health patterns (6th house, Saturn/Mars)
            "spiritual"             # Spiritual experiences (9th/12th houses, Neptune)
        ]

        # Use question count to determine category
        question_count = len(previous_answers)

        # First 8 questions follow the progression
        if question_count < len(progression):
            return progression[question_count]

        # After initial progression, focus on most time-sensitive categories
        priority_categories = ["life_events", "timing_preferences", "physical_traits"]

        # Count how many times each category has been used
        category_counts = {}
        for qa_pair in previous_answers:
            category = qa_pair.get("category", "unknown")
            category_counts[category] = category_counts.get(category, 0) + 1

        # Find least-used priority category
        least_used = min(priority_categories, key=lambda c: category_counts.get(c, 0))
        return least_used

    async def _generate_question(self, category: str, chart_data: str, context: str) -> Dict[str, Any]:
        """
        Generate a question using AI based on chart data, previous context, and category.

        Args:
            category: Question category to focus on
            chart_data: Formatted chart data
            context: Previous Q&A context

        Returns:
            Structured question dictionary

        Raises:
            ValueError: If question generation fails
        """
        if not self.openai_service:
            raise ValueError("OpenAI service is required for question generation")

        # Create prompt for specific category
        category_prompts = {
            "physical_traits": "Focus on physical appearance, body type, face shape, and distinct features that relate to the Ascendant.",
            "personality": "Focus on personality traits, communication style, and emotional patterns related to Moon and Mercury positions.",
            "life_events": "Focus on major life events, transitions, and their timing which can correlate with planetary transits.",
            "timing_preferences": "Focus on daily rhythms, sleep patterns, and times of day when the person feels most/least energetic.",
            "relationships": "Focus on relationship patterns, attraction types, and significant partnerships.",
            "career": "Focus on career path, professional achievements, and public reputation.",
            "health": "Focus on health patterns, strengths, and vulnerabilities that may relate to the 6th house and Mars/Saturn.",
            "spiritual": "Focus on spiritual experiences, beliefs, and practices that may relate to the 9th and 12th houses."
        }

        category_guidance = category_prompts.get(category, "Generate a question to help determine birth time.")

        prompt = f"""
        As an expert astrologer specializing in birth time rectification, generate the next question
        to ask a person to help determine their precise birth time.

        CHART INFORMATION:
        {chart_data}

        {context}

        QUESTION CATEGORY: {category}
        {category_guidance}

        RESPONSE FORMAT:
        Return only a JSON object with these fields:
        - id: a unique identifier (use a random string)
        - text: the question text
        - type: "text" or "multiple_choice" or "yes_no"
        - options: an array of options if type is multiple_choice (include at least 4 options)
        - category: "{category}"
        - relevance_to_birth_time: brief explanation of how this relates to birth time

        The question must be easily understandable by someone without astrological knowledge.
        PROVIDE ONLY THE JSON OBJECT AND NO OTHER TEXT.
        """

        try:
            # Use generate_completion which is the correct method
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="questionnaire",
                max_tokens=1000,
                temperature=0.7
            )

            # Extract content from response
            if response and isinstance(response, dict):
                content = response.get("choices", [{}])[0].get("text", "")
                if content:
                    return self._parse_question_response(content)

            raise ValueError("Invalid or empty response from AI service")

        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")
            raise ValueError(f"Failed to generate question: {str(e)}")

    async def get_next_question(self, session_id: str, chart_data: Dict[str, Any],
                             previous_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate the next question based on previous answers and current chart data.
        Raises an exception if question generation fails.
        """
        if not self.openai_service:
            raise ValueError("OpenAI service is required for dynamic question generation")

        # Track question history for this session
        if session_id not in self.question_history:
            self.question_history[session_id] = []
            self.answer_history[session_id] = []

        # Update answer history
        self.answer_history[session_id] = previous_answers.copy()

        # Format chart data for LLM prompt
        chart_summary = self._format_chart_for_prompt(chart_data)

        # Format previous answers and questions
        context = self._format_answers_for_prompt(previous_answers)

        # Decide question category based on answered questions
        category = self._determine_next_category(previous_answers)

        # Generate next question from LLM
        next_question = await self._generate_question(
            category=category,
            chart_data=chart_summary,
            context=context
        )

        # Add to question history
        if next_question:
            self.question_history[session_id].append(next_question)

        # Ensure we have a valid question to return
        if not next_question:
            raise ValueError("Failed to generate a valid question. Please try again or check the AI service.")

        return next_question

    def _questions_are_similar(self, question1: str, question2: str) -> bool:
        """
        Check if two questions are semantically similar to avoid repetition.
        """
        # Simple token similarity approach
        q1_tokens = set(question1.lower().split())
        q2_tokens = set(question2.lower().split())
        common_tokens = q1_tokens.intersection(q2_tokens)

        # If 70% or more tokens are common, consider questions similar
        similarity = len(common_tokens) / max(len(q1_tokens), len(q2_tokens))
        return similarity > 0.7

    def _parse_question_response(self, content: str) -> Dict[str, Any]:
        """
        Parse the AI response to extract a structured question.

        Args:
            content: Raw response content from the model

        Returns:
            Structured question dictionary

        Raises:
            ValueError: If the response cannot be parsed properly
        """
        try:
            # Remove markdown code block formatting if present
            cleaned_content = content.strip()
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content[7:]
            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]

            # Parse JSON
            question_data = json.loads(cleaned_content)

            # Validate required fields
            required_fields = ["text", "type"]
            for field in required_fields:
                if field not in question_data:
                    raise ValueError(f"Required field '{field}' missing from question data")

            return question_data

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Error parsing question response: {str(e)}. Content: {content[:100]}...")
            # Raise an exception instead of providing a fallback
            raise ValueError(f"Failed to parse question response: {str(e)}")

    async def calculate_confidence(self, answers: Dict[str, Any], chart_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate confidence score based on answers, with enhanced weighting for birth time range narrowing.
        """
        # Initialize base confidence
        base_confidence = 25.0

        # Extract responses
        responses = answers.get("responses", [])
        if not responses:
            return base_confidence

        # Count answers and calculate quality-based adjustment
        num_answers = len(responses)
        quality_sum = 0

        # Track birth time range narrowing
        initial_range_minutes = 120  # Default initial range: 2 hours
        current_range_minutes = initial_range_minutes
        has_range_narrowed = False

        # Track coverage of critical time-sensitive factors
        critical_factors_covered = {
            "ascendant": False,
            "moon": False,
            "angular_houses": False,
            "physical_appearance": False,
            "timing_of_events": False,
            "life_direction_changes": False,
            "personality_traits": False
        }

        # Calculate quality and assess critical factors coverage
        for resp in responses:
            if not isinstance(resp, dict):
                continue

            # Get answer quality if available, default to medium (0.5)
            quality = resp.get("quality", 0.5)
            if isinstance(quality, str):
                quality_map = {"high": 0.8, "medium": 0.5, "low": 0.2}
                quality = quality_map.get(quality.lower(), 0.5)

            quality_sum += quality

            # Check which critical factors this response addresses
            question = resp.get("question", "").lower()
            answer = str(resp.get("answer", "")).lower()

            # Check for ascendant-related questions
            if "appearance" in question or "physical" in question or "look" in question:
                critical_factors_covered["ascendant"] = True
                critical_factors_covered["physical_appearance"] = True

            # Check for moon-related questions
            if "emotion" in question or "feel" in question or "mood" in question:
                critical_factors_covered["moon"] = True

            # Check for angular houses
            if "career" in question or "profession" in question or "work" in question:
                critical_factors_covered["angular_houses"] = True

            if "home" in question or "family" in question or "parent" in question:
                critical_factors_covered["angular_houses"] = True

            if "relationship" in question or "partner" in question or "marriage" in question:
                critical_factors_covered["angular_houses"] = True

            # Check for timing of events
            if "when" in question or "age" in question or "time" in question or "year" in question:
                critical_factors_covered["timing_of_events"] = True

            # Check for life direction changes
            if "change" in question or "turning point" in question or "shift" in question:
                critical_factors_covered["life_direction_changes"] = True

            # Check for personality traits
            if "personality" in question or "character" in question or "trait" in question:
                critical_factors_covered["personality_traits"] = True

        # Calculate average quality (0-1)
        avg_quality = quality_sum / num_answers if num_answers > 0 else 0.5

        # Calculate confidence from answer count (max 50%)
        count_confidence = min(num_answers * 5, 50)

        # Calculate quality confidence adjustment (-15% to +15%)
        quality_adjustment = (avg_quality - 0.5) * 30

        # Calculate critical factors coverage confidence boost (max 15%)
        factors_covered = sum(1 for covered in critical_factors_covered.values() if covered)
        factors_total = len(critical_factors_covered)
        factors_confidence = (factors_covered / factors_total) * 15 if factors_total > 0 else 0

        # Calculate final confidence
        total_confidence = base_confidence + count_confidence + quality_adjustment + factors_confidence

        # Ensure confidence stays within bounds (30-95%)
        return min(max(total_confidence, 30), 95)

    async def analyze_answers(self, chart_data: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze questionnaire answers to identify birth time patterns.
        """
        if not self.openai_service:
            raise ValueError("OpenAI service is required for answer analysis")

        # Format chart data
        chart_summary = self._format_chart_for_prompt(chart_data)

        # Format questions and answers
        qa_formatted = ""
        for resp in answers.get("responses", []):
            qa_formatted += f"Q: {resp.get('question', '')}\nA: {resp.get('answer', '')}\n\n"

        # Create a prompt for answer analysis
        prompt = f"""
        As an expert astrologer specializing in birth time rectification, analyze these responses
        to determine the most accurate birth time adjustment.

        ORIGINAL CHART DATA:
        {chart_summary}

        QUESTIONNAIRE RESPONSES:
        {qa_formatted}

        Based on a comprehensive analysis of the responses and their relationship to the birth chart,
        determine:
        1. Whether the birth time should be adjusted earlier or later
        2. The approximate magnitude of adjustment (in minutes)
        3. The confidence level in this recommendation
        4. Which specific responses were most valuable in making this determination

        Return your analysis in JSON format:
        {{
            "adjustment_direction": "earlier" or "later",
            "adjustment_minutes": [number of minutes],
            "confidence_score": [number between 0-100],
            "key_indicators": ["list of specific responses that influenced this decision"],
            "analysis": "Detailed explanation of your reasoning"
        }}
        """

        try:
            # Call OpenAI for comprehensive analysis
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="birth_time_rectification_analysis",
                max_tokens=600,
                temperature=0.4
            )

            # Parse the AI response
            if response and "content" in response:
                content = response["content"]
                try:
                    # Extract JSON from response
                    json_match = re.search(r'({[\s\S]*})', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        analysis_data = json.loads(json_str)

                        # Process the analysis data
                        return {
                            "analysis_result": analysis_data,
                            "raw_response": content,
                            "model_used": response.get("model_used", "unknown"),
                            "success": True
                        }
                    else:
                        raise ValueError("No JSON data found in response")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed to parse analysis response: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to parse analysis: {str(e)}",
                        "raw_response": content
                    }
            else:
                return {
                    "success": False,
                    "error": "No content in response"
                }
        except Exception as e:
            logger.error(f"Error in answer analysis: {str(e)}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}"
            }
