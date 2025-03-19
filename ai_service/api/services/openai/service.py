"""
Main OpenAI service implementation.
"""

import os
import logging
import json
import time
import uuid
import asyncio
from typing import Dict, Any, List, Optional, TypedDict, cast, Union, TYPE_CHECKING

# Standard OpenAI import
import openai
# Import exception classes directly from the exceptions module
from openai._exceptions import (
    APIConnectionError,
    APITimeoutError,
    APIError,
    RateLimitError,
    BadRequestError
)
from openai.types.chat import ChatCompletionMessageParam
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ai_service.api.services.openai.model_selection import select_model, get_task_category
from ai_service.api.services.openai.cost_calculator import calculate_cost
from ai_service.utils.dependency_container import get_container

# Set up logging
logger = logging.getLogger(__name__)

# Define typed dictionary for cache entries
class CacheEntry(TypedDict):
    """Type definition for cache entries."""
    timestamp: float
    response: Dict[str, Any]

class OpenAIService:
    """Service for interacting with OpenAI API."""

    def __init__(self, client=None, api_key=None):
        """
        Initialize the OpenAI service with API key and model configuration.

        Args:
            client: Optional pre-configured OpenAI client for dependency injection
            api_key: Optional API key (defaults to environment variable)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

        # Require API key - no fallbacks
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY environment variable is not set")

        # Use injected client or create a new one
        if client:
            self.client = client
            logger.info("Using provided OpenAI client")
        else:
            try:
                # Initialize the AsyncOpenAI client directly from the openai module
                # The linter may not recognize this attribute, but it exists in the runtime
                self.client = openai.AsyncOpenAI(api_key=self.api_key)  # type: ignore
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise ValueError(f"Failed to initialize OpenAI client: {e}")

        # Configuration
        self.default_model = os.environ.get("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.temperature = float(os.environ.get("OPENAI_TEMPERATURE", 0.7))

        # Configure caching settings
        self.cache_enabled = os.environ.get("ENABLE_CACHE", "true").lower() == "true"
        self.cache_ttl = int(os.environ.get("CACHE_TTL", "3600"))  # Default 1 hour
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_hits = 0
        self.cache_misses = 0

        # Usage statistics tracking
        self.usage_stats = {
            "calls_made": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost": 0.0
        }

        # Cost tracking
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.estimated_cost = 0.0

        # API call tracking
        self.api_calls = 0
        self.last_request_time = 0
        self.tokens_this_minute = 0
        self.rate_limit = 90000  # OpenAI rate limit (tokens per minute)

        logger.info(f"OpenAI service initialized with model: {self.default_model}")

    def _select_model(self, task_type: str) -> str:
        """
        Select the appropriate model based on task type.

        Args:
            task_type: Type of task (e.g., completion, chat, embedding)

        Returns:
            Model identifier string
        """
        # Define model mapping based on task type
        model_mapping = {
            "rectification": "gpt-4-turbo-preview",
            "questionnaire": "gpt-4-turbo-preview",
            "chart_verification": "gpt-4-turbo-preview",
            "explanation": "gpt-3.5-turbo",
            "auxiliary": "gpt-3.5-turbo"
        }

        # Return the specific model for the task or the default
        return model_mapping.get(task_type, self.default_model)

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate the cost of API usage.

        Args:
            model: The model used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Estimated cost in USD
        """
        return calculate_cost(model, prompt_tokens, completion_tokens)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError))
    )
    async def generate_completion(self, prompt: str, task_type: str, max_tokens: int = 500, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate a completion from OpenAI.

        Args:
            prompt: The prompt to send to the API
            task_type: Type of task to optimize model selection
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0=deterministic, 1=creative)

        Returns:
            Dictionary with content and metadata
        """
        # Select model based on task type
        model = self._select_model(task_type)

        # Create a unique key for this request for caching
        cache_key = f"{model}:{task_type}:{hash(prompt)}:{max_tokens}:{temperature}"

        # Check cache first if enabled
        if self.cache_enabled and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                self.cache_hits += 1
                logger.debug(f"Cache hit for {task_type} task")
                return cache_entry["response"]

        self.cache_misses += 1
        logger.debug(f"Cache miss for {task_type} task, generating new completion")

        # Rate limiting
        await self._apply_rate_limiting()

        # Track API call
        self.api_calls += 1
        self.last_request_time = time.time()

        # Prepare messages for the API
        messages: List[ChatCompletionMessageParam] = [
            {"role": "user", "content": prompt}
        ]

        logger.debug(f"Sending request to OpenAI API with model {model}, task_type={task_type}")

        try:
            # Call OpenAI API with real API key
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=45.0  # 45-second timeout
            )

            # Extract response
            content = response.choices[0].message.content

            # Update token tracking
            usage = response.usage
            if usage is None:
                # Instead of fallback estimation, raise an error about missing usage data
                raise ValueError("Token usage data not provided by OpenAI API. Cannot proceed without accurate tracking.")

            prompt_tokens = usage.prompt_tokens
            completion_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens

            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.total_tokens += total_tokens
            self.tokens_this_minute += total_tokens

            # Update usage statistics
            self.usage_stats["calls_made"] += 1
            self.usage_stats["prompt_tokens"] += prompt_tokens
            self.usage_stats["completion_tokens"] += completion_tokens
            self.usage_stats["total_tokens"] += total_tokens

            # Update cost tracking
            cost = self._calculate_cost(model, prompt_tokens, completion_tokens)
            self.estimated_cost += cost
            self.usage_stats["total_cost"] += cost

            # Construct result
            result = {
                "content": content,
                "model": model,
                "tokens": {
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": total_tokens
                },
                "cost": cost
            }

            # Cache the result if caching is enabled
            if self.cache_enabled:
                self.cache[cache_key] = {
                    "timestamp": time.time(),
                    "response": result
                }

            logger.debug(f"OpenAI API returned {total_tokens} tokens for {task_type} task")
            return result

        except RateLimitError as e:
            logger.error(f"OpenAI API rate limit exceeded: {e}")
            raise ValueError(f"OpenAI API rate limit exceeded: {e}")

        except APIConnectionError as e:
            logger.error(f"OpenAI API connection error: {e}")
            raise ValueError(f"OpenAI API connection error: {e}")

        except BadRequestError as e:
            logger.error(f"OpenAI API bad request error: {e}")
            raise ValueError(f"OpenAI API bad request error: {e}")

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise ValueError(f"OpenAI API error: {e}")

        except Exception as e:
            logger.error(f"Unexpected error calling OpenAI API: {e}")
            raise ValueError(f"Error generating completion: {e}")

    async def generate_questions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate dynamic questions for birth time rectification based on context.
        Analyzes chart data to generate personalized questions targeting uncertain birth time factors.

        Args:
            context: Dictionary containing birth details, previous answers, chart data, etc.

        Returns:
            Dictionary with generated questions and metadata
        """
        try:
            # Extract context information
            birth_details = context.get("birth_details", {})
            previous_answers = context.get("previous_answers", {})
            question_count = context.get("question_count", 0)
            remaining_questions = context.get("remaining_questions", 5)
            chart_data = context.get("chart_data", {})

            # Format birth details for the prompt
            birth_date = birth_details.get("birthDate", birth_details.get("birth_date", "Unknown"))
            birth_time = birth_details.get("birthTime", birth_details.get("birth_time", "Unknown"))
            birth_place = birth_details.get("birthPlace", birth_details.get("birth_place", "Unknown"))

            # Extract coordinates and timezone if available
            latitude = birth_details.get("latitude", "Unknown")
            longitude = birth_details.get("longitude", "Unknown")
            timezone = birth_details.get("timezone", "Unknown")

            # Format chart data for the prompt
            chart_summary = self._format_chart_data(chart_data)

            # Format previous answers for the prompt
            answers_text = ""

            # Handle different formats of previous_answers
            if isinstance(previous_answers, dict):
                if "responses" in previous_answers:
                    # Handle the format where previous_answers has a "responses" key
                    for resp in previous_answers.get("responses", []):
                        if isinstance(resp, dict):
                            question = resp.get("question", "Unknown question")
                            answer = resp.get("answer", "Unknown answer")
                            answers_text += f"Q: {question}\nA: {answer}\n\n"
                elif "answers" in previous_answers:
                    # Handle the format where previous_answers has an "answers" key
                    for question_id, answer_data in previous_answers.get("answers", {}).items():
                        if isinstance(answer_data, dict) and "question" in answer_data and "answer" in answer_data:
                            answers_text += f"Q: {answer_data['question']}\nA: {answer_data['answer']}\n\n"
                        else:
                            # Try to find the question text from the question ID
                            question_text = f"Question {question_id}"
                            answer_value = answer_data if not isinstance(answer_data, dict) else str(answer_data)
                            answers_text += f"Q: {question_text}\nA: {answer_value}\n\n"
                else:
                    # Handle direct key-value pairs
                    for question_id, answer in previous_answers.items():
                        if isinstance(answer, dict) and "question" in answer and "answer" in answer:
                            answers_text += f"Q: {answer['question']}\nA: {answer['answer']}\n\n"
                        else:
                            answers_text += f"Question ID: {question_id}\nAnswer: {answer}\n\n"
            elif isinstance(previous_answers, list):
                # Handle list format
                for answer in previous_answers:
                    if isinstance(answer, dict):
                        question = answer.get("question", "Unknown question")
                        answer_value = answer.get("answer", "Unknown answer")
                        answers_text += f"Q: {question}\nA: {answer_value}\n\n"

            # Track previously asked questions to avoid duplicates
            asked_questions = set()
            asked_question_ids = set()

            # Extract previously asked questions from different possible formats
            if isinstance(previous_answers, dict):
                if "responses" in previous_answers:
                    for resp in previous_answers.get("responses", []):
                        if isinstance(resp, dict):
                            if "question" in resp:
                                asked_questions.add(resp["question"])
                            if "id" in resp:
                                asked_question_ids.add(resp["id"])
                elif "answers" in previous_answers:
                    # Handle alternative format where answers are stored directly
                    for q_id, answer in previous_answers.get("answers", {}).items():
                        asked_question_ids.add(q_id)
                        if isinstance(answer, dict) and "question" in answer:
                            asked_questions.add(answer["question"])
            elif isinstance(previous_answers, list):
                for answer in previous_answers:
                    if isinstance(answer, dict):
                        if "question" in answer:
                            asked_questions.add(answer["question"])
                        if "id" in answer:
                            asked_question_ids.add(answer["id"])

            # Analyze chart data to identify uncertain birth time factors
            uncertain_factors = self._identify_uncertain_factors(chart_data, birth_time)

            # Create the prompt for question generation
            prompt = f"""
            You are an expert astrologer specializing in birth time rectification using Indian Vedic astrological principles.

            Birth Details:
            Date: {birth_date}
            Time: {birth_time}
            Place: {birth_place}
            Latitude: {latitude}
            Longitude: {longitude}
            Timezone: {timezone}

            Chart Data:
            {chart_summary}

            Previous Questions and Answers:
            {answers_text}

            Uncertain Birth Time Factors:
            {uncertain_factors}

            Generate {min(3, remaining_questions)} personalized questions that would help with birth time rectification.
            The questions should be specific, relevant to the person's life based on previous answers and chart data,
            and designed to elicit information that would help determine the exact birth time.

            Focus on areas that would be most affected by small changes in birth time:
            1. Ascendant sign and degree (especially if the birth time is near a sign change)
            2. House cusps and planetary house placements
            3. Life events that correlate with planetary transits or dashas
            4. Physical characteristics and personality traits associated with the Ascendant

            For life events, ask about specific events with dates.
            For traits, ask about distinctive characteristics that correlate with astrological positions.

            Format your response as a JSON object with the following structure:
            {{
                "questions": [
                    {{
                        "id": "unique_id_1",
                        "text": "Your question here?",
                        "type": "boolean" or "date" or "options" or "text",
                        "options": ["Option 1", "Option 2", etc.] (only for options type),
                        "relevance": "high" or "medium" or "low",
                        "rationale": "Brief explanation of why this question helps with rectification"
                    }},
                    ...
                ]
            }}

            Make sure the questions are not repeats of previous questions and are tailored to this specific individual.
            If the person has answered questions about personality traits, focus more on life events or physical characteristics.
            If contradictory answers were given, include a question that helps clarify the contradiction.

            The following questions have already been asked and should NOT be repeated:
            {", ".join(f'"{q}"' for q in asked_questions) if asked_questions else "None yet"}
            """

            # Generate questions using OpenAI
            response = await self.generate_completion(
                prompt=prompt,
                task_type="questionnaire",
                max_tokens=800,  # Increased token limit for more detailed responses
                temperature=0.7   # Slightly lower temperature for more focused questions
            )

            # Parse the response
            try:
                # Extract the content from the response
                content = response.get("content", "").strip()

                # Find JSON object in the text
                start_idx = content.find("{")
                end_idx = content.rfind("}") + 1

                if start_idx >= 0 and end_idx > start_idx:
                    json_text = content[start_idx:end_idx]
                    questions_data = json.loads(json_text)

                    # Ensure the response has the expected structure
                    if "questions" not in questions_data:
                        questions_data = {"questions": []}

                    # Safely add IDs to questions if missing
                    if "questions" in questions_data and isinstance(questions_data["questions"], list):
                        for i, question in enumerate(questions_data["questions"]):
                            if isinstance(question, dict) and "id" not in question:
                                question["id"] = f"ai_q_{i}_{uuid.uuid4().hex[:8]}"

                    # Add metadata safely with proper type checking
                    confidence_score = 0.0
                    if isinstance(questions_data, dict):
                        if "confidence_score" in questions_data:
                            try:
                                confidence_value = questions_data.get("confidence_score", 0)
                                if isinstance(confidence_value, (int, float)):
                                    model_confidence = float(confidence_value) / 100.0
                                else:
                                    model_confidence = 0.0
                            except (ValueError, TypeError):
                                model_confidence = 0.0
                        else:
                            model_confidence = 0.0

                        # Set the fields only if questions_data is a dictionary
                        questions_data["confidence_score"] = float(confidence_score)  # type: ignore
                        questions_data["is_complete"] = bool(confidence_score >= 0.9)  # type: ignore
                        questions_data["has_reached_threshold"] = bool(confidence_score >= 0.8)  # type: ignore

                    return questions_data
                else:
                    # If no valid JSON found, raise exception
                    logger.error("No valid JSON found in OpenAI response")
                    raise ValueError("Failed to parse valid JSON from AI response")

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing OpenAI response: {str(e)}")
                raise ValueError(f"Failed to parse AI response: {str(e)}")

        except Exception as e:
            logger.error(f"Error generating questions with OpenAI: {str(e)}")
            raise

    def _identify_uncertain_factors(self, chart_data: Dict[str, Any], birth_time: str) -> str:
        """
        Analyze chart data to identify factors that are most sensitive to birth time changes.
        These are the areas that should be targeted by rectification questions.

        Args:
            chart_data: The chart data including planets, houses, etc.
            birth_time: The provided birth time

        Returns:
            String describing uncertain factors for birth time rectification
        """
        uncertain_factors = []

        # Check if chart data is available
        if not chart_data:
            return "No chart data available to analyze for uncertain factors."

        # Check for ascendant near sign boundary (most sensitive to time changes)
        if "ascendant" in chart_data:
            ascendant = chart_data["ascendant"]
            if isinstance(ascendant, dict):
                degree = ascendant.get("degree", 0)
                sign = ascendant.get("sign", "Unknown")

                # If ascendant is near the beginning or end of a sign (within 3 degrees)
                if degree < 3 or degree > 27:
                    uncertain_factors.append(
                        f"Ascendant at {degree}° {sign} is near a sign boundary, making it highly sensitive to birth time changes. "
                        f"A small adjustment in birth time could change the Ascendant sign."
                    )
                elif degree < 5 or degree > 25:
                    uncertain_factors.append(
                        f"Ascendant at {degree}° {sign} is somewhat close to a sign boundary, making it moderately sensitive to birth time changes."
                    )

        # Check for planets near house cusps
        if "planets" in chart_data and "houses" in chart_data:
            planets = chart_data["planets"]
            houses = chart_data["houses"]

            # Normalize planets to list format if it's a dictionary
            planets_list = []
            if isinstance(planets, dict):
                for planet_name, planet_data in planets.items():
                    if isinstance(planet_data, dict):
                        planet_data["name"] = planet_name  # Add name field
                        planets_list.append(planet_data)
            elif isinstance(planets, list):
                planets_list = planets

            # Normalize houses to list format if it's a dictionary
            houses_list = []
            if isinstance(houses, dict):
                for house_num, house_data in houses.items():
                    if isinstance(house_data, dict):
                        try:
                            house_num_int = int(house_num)
                            house_data["number"] = house_num_int
                            houses_list.append(house_data)
                        except ValueError:
                            # Skip if house number can't be converted to int
                            pass
            elif isinstance(houses, list):
                houses_list = houses

            # Check for planets near house cusps
            for planet in planets_list:
                if isinstance(planet, dict):
                    planet_name = planet.get("name", planet.get("planet", "Unknown"))
                    planet_house = planet.get("house", 0)
                    planet_degree = planet.get("degree", 0)

                    # Check if planet is near a house cusp
                    for house in houses_list:
                        if isinstance(house, dict):
                            house_number = house.get("number", 0)
                            house_degree = house.get("degree", 0)

                            # If this is the house the planet is in or the next house
                            if house_number == planet_house or house_number == (planet_house % 12) + 1:
                                # Check if planet is within 3 degrees of the house cusp
                                if abs(planet_degree - house_degree) < 3 or abs(planet_degree - house_degree) > 27:
                                    uncertain_factors.append(
                                        f"{planet_name} is very close to the cusp of house {house_number}, "
                                        f"making its house placement sensitive to birth time changes."
                                    )

        # Check for Moon (fastest moving body) position
        moon_found = False
        for planet in planets_list:
            if isinstance(planet, dict) and (planet.get("name") == "Moon" or planet.get("planet") == "Moon"):
                moon_found = True
                moon_sign = planet.get("sign", "Unknown")
                moon_degree = planet.get("degree", 0)

                uncertain_factors.append(
                    f"Moon at {moon_degree}° {moon_sign} moves approximately 12-15 degrees per day, "
                    f"making it highly sensitive to birth time changes."
                )

                # If Moon is near a sign boundary
                if moon_degree < 3 or moon_degree > 27:
                    uncertain_factors.append(
                        f"Moon is near a sign boundary, so a small birth time adjustment could change its sign."
                    )
                break

        if not moon_found and planets_list:
            uncertain_factors.append("Moon position not found in chart data, which is a critical factor for birth time rectification.")

        # Check for Midheaven (MC) sensitivity
        mc_found = False
        if "angles" in chart_data:
            for angle in chart_data.get("angles", []):
                if isinstance(angle, dict) and angle.get("name", "") == "MC":
                    mc_found = True
                    mc_sign = angle.get("sign", "Unknown")
                    mc_degree = angle.get("degree", 0)

                    uncertain_factors.append(
                        f"Midheaven (MC) at {mc_degree}° {mc_sign} is highly sensitive to birth time changes "
                        f"and affects career and public life interpretations."
                    )
                    break

        # If no specific uncertain factors found, provide general guidance
        if not uncertain_factors:
            uncertain_factors = [
                "Ascendant degree and sign (changes approximately 1 degree every 4 minutes)",
                "House cusps and planetary house placements",
                "Moon position (moves approximately 12-15 degrees per day)",
                "Midheaven (MC) and IC axis",
                "Planets near house cusps or sign boundaries"
            ]

        # Format the uncertain factors as a string
        if isinstance(uncertain_factors, list):
            if len(uncertain_factors) == 1:
                return uncertain_factors[0]
            else:
                return "- " + "\n- ".join(uncertain_factors)
        return uncertain_factors

    def _format_chart_data(self, chart_data: Dict[str, Any]) -> str:
        """
        Format chart data into a concise summary for AI prompts.

        Args:
            chart_data: The chart data including planets, houses, etc.

        Returns:
            Formatted string summary of chart data
        """
        if not chart_data:
            return "No chart data available"

        summary_parts = []

        # Add ascendant information if available
        if "ascendant" in chart_data:
            ascendant = chart_data["ascendant"]
            if isinstance(ascendant, dict):
                sign = ascendant.get("sign", "Unknown")
                degree = ascendant.get("degree", 0)
                summary_parts.append(f"Ascendant: {sign} {degree}°")
            else:
                summary_parts.append(f"Ascendant: {ascendant}")

        # Add planetary positions
        if "planets" in chart_data:
            planets = chart_data["planets"]
            if planets:
                summary_parts.append("Planetary Positions:")
                # Handle planets as either list or dictionary
                if isinstance(planets, list):
                    for planet in planets:
                        if isinstance(planet, dict):
                            name = planet.get("name", planet.get("planet", "Unknown"))
                            sign = planet.get("sign", "Unknown")
                            degree = planet.get("degree", 0)
                            house = planet.get("house", "Unknown")
                            retrograde = " (R)" if planet.get("is_retrograde", planet.get("retrograde", False)) else ""
                            summary_parts.append(f"- {name}: {sign} {degree}°, House {house}{retrograde}")
                        else:
                            summary_parts.append(f"- {planet}")
                elif isinstance(planets, dict):
                    for planet_name, planet_data in planets.items():
                        if isinstance(planet_data, dict):
                            sign = planet_data.get("sign", "Unknown")
                            degree = planet_data.get("degree", 0)
                            house = planet_data.get("house", "Unknown")
                            retrograde = " (R)" if planet_data.get("is_retrograde", planet_data.get("retrograde", False)) else ""
                            summary_parts.append(f"- {planet_name}: {sign} {degree}°, House {house}{retrograde}")
                        else:
                            summary_parts.append(f"- {planet_name}: {planet_data}")

        # Add house cusps
        if "houses" in chart_data:
            houses = chart_data["houses"]
            if houses:
                summary_parts.append("House Cusps:")
                # Handle houses as either list or dictionary
                if isinstance(houses, list):
                    # Just include first 4 houses for brevity
                    for house in houses[:4]:
                        if isinstance(house, dict):
                            number = house.get("number", "Unknown")
                            sign = house.get("sign", "Unknown")
                            degree = house.get("degree", 0)
                            summary_parts.append(f"- House {number}: {sign} {degree}°")
                        else:
                            summary_parts.append(f"- {house}")
                elif isinstance(houses, dict):
                    # Include first 4 houses for brevity
                    house_numbers = sorted([int(k) for k in houses.keys() if k.isdigit()])[:4]
                    for house_num in house_numbers:
                        house_data = houses[str(house_num)]
                        if isinstance(house_data, dict):
                            sign = house_data.get("sign", "Unknown")
                            degree = house_data.get("degree", 0)
                            summary_parts.append(f"- House {house_num}: {sign} {degree}°")
                        else:
                            summary_parts.append(f"- House {house_num}: {house_data}")

        # Add aspects if available
        if "aspects" in chart_data:
            aspects = chart_data["aspects"]
            if aspects:
                summary_parts.append("Key Aspects:")
                # Handle aspects as list
                if isinstance(aspects, list):
                    # Just include first 5 aspects for brevity
                    for aspect in aspects[:5]:
                        if isinstance(aspect, dict):
                            planet1 = aspect.get("planet1", "Unknown")
                            planet2 = aspect.get("planet2", "Unknown")
                            aspect_type = aspect.get("type", aspect.get("aspectType", "Unknown"))
                            orb = aspect.get("orb", 0)
                            summary_parts.append(f"- {planet1} {aspect_type} {planet2} (Orb: {orb}°)")
                        else:
                            summary_parts.append(f"- {aspect}")
                # Handle aspects as dictionary
                elif isinstance(aspects, dict):
                    count = 0
                    for aspect_id, aspect_data in aspects.items():
                        if count >= 5:  # Only include 5 for brevity
                            break
                        if isinstance(aspect_data, dict):
                            planet1 = aspect_data.get("planet1", "Unknown")
                            planet2 = aspect_data.get("planet2", "Unknown")
                            aspect_type = aspect_data.get("type", aspect_data.get("aspectType", "Unknown"))
                            orb = aspect_data.get("orb", 0)
                            summary_parts.append(f"- {planet1} {aspect_type} {planet2} (Orb: {orb}°)")
                        else:
                            summary_parts.append(f"- Aspect {aspect_id}: {aspect_data}")
                        count += 1

        return "\n".join(summary_parts)

    async def verify_chart(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify an astrological chart against Vedic standards using OpenAI.

        Args:
            chart_data: Dictionary containing chart details including planets, houses, etc.

        Returns:
            Dictionary with verification results including status, confidence, and any corrections
        """
        try:
            # Extract relevant chart information
            birth_details = chart_data.get("birth_details", {})
            planets = chart_data.get("planets", [])
            houses = chart_data.get("houses", [])

            # Format birth details for the prompt
            birth_date = birth_details.get("birth_date", birth_details.get("date", "Unknown"))
            birth_time = birth_details.get("birth_time", birth_details.get("time", "Unknown"))
            location = birth_details.get("location", "Unknown")

            # Format planetary positions
            planets_text = ""

            # Handle planets as list or dictionary
            if isinstance(planets, list):
                for planet in planets:
                    if isinstance(planet, dict):
                        name = planet.get("name", planet.get("planet", "Unknown"))
                        sign = planet.get("sign", "Unknown")
                        degree = planet.get("degree", 0)
                        house = planet.get("house", "Unknown")
                        retrograde = planet.get("is_retrograde", planet.get("retrograde", False))
                        planets_text += f"{name}: {sign} {degree:.2f}° (House {house}), Retrograde: {retrograde}\n"
            elif isinstance(planets, dict):
                for planet_name, planet_data in planets.items():
                    if isinstance(planet_data, dict):
                        sign = planet_data.get("sign", "Unknown")
                        degree = planet_data.get("degree", 0)
                        house = planet_data.get("house", "Unknown")
                        retrograde = planet_data.get("is_retrograde", planet_data.get("retrograde", False))
                        planets_text += f"{planet_name}: {sign} {degree:.2f}° (House {house}), Retrograde: {retrograde}\n"
                    else:
                        planets_text += f"{planet_name}: {planet_data}\n"

            # Format house cusps
            houses_text = ""

            # Handle houses as list or dictionary
            if isinstance(houses, list):
                for i, house in enumerate(houses, 1):
                    if isinstance(house, dict):
                        number = house.get("number", i)
                        sign = house.get("sign", "Unknown")
                        degree = house.get("degree", 0)
                        houses_text += f"House {number}: {sign} {degree:.2f}°\n"
                    else:
                        houses_text += f"House {i}: {house}\n"
            elif isinstance(houses, dict):
                for house_num, house_data in houses.items():
                    if isinstance(house_data, dict):
                        sign = house_data.get("sign", "Unknown")
                        degree = house_data.get("degree", 0)
                        houses_text += f"House {house_num}: {sign} {degree:.2f}°\n"
                    else:
                        houses_text += f"House {house_num}: {house_data}\n"

            # Create the prompt for chart verification
            prompt = f"""
            You are an expert Vedic astrologer specializing in chart verification.

            Please verify the accuracy of the following birth chart calculation according to Vedic astrological standards:

            Birth Details:
            Date: {birth_date}
            Time: {birth_time}
            Location: {location}

            Planetary Positions:
            {planets_text}

            House Cusps:
            {houses_text}

            Your task is to:
            1. Verify if the planetary positions and house cusps are correctly calculated according to Vedic standards
            2. Check for any inconsistencies or errors in the chart
            3. Provide a confidence score for the chart's accuracy
            4. Suggest any corrections if needed

            Format your response as a JSON object with the following structure:
            {{
                "status": "verified" or "errors_found" or "verification_error",
                "confidence": [0-100 numerical score],
                "corrections_applied": true or false,
                "corrections": [
                    {{
                        "type": "planet_position" or "house_cusp",
                        "object": "name of planet or house number",
                        "original": "original value",
                        "corrected": "corrected value",
                        "explanation": "reason for correction"
                    }},
                    ...
                ],
                "message": "Summary of verification results"
            }}

            If the chart is completely accurate, set status to "verified" with appropriate confidence.
            If errors are found, set status to "errors_found" and list the corrections.
            If verification cannot be completed, set status to "verification_error" and explain why.
            """

            # Generate verification using OpenAI
            response = await self.generate_completion(
                prompt=prompt,
                task_type="chart_verification",
                max_tokens=800,
                temperature=0.3  # Lower temperature for more deterministic results
            )

            # Parse the response
            content = response.get("content", "")

            try:
                # If content is already JSON string, parse it
                if content.startswith("{") and content.endswith("}"):
                    verification_data = json.loads(content)
                else:
                    # Find JSON object in the text
                    start_idx = content.find("{")
                    end_idx = content.rfind("}") + 1

                    if start_idx >= 0 and end_idx > start_idx:
                        json_text = content[start_idx:end_idx]
                        verification_data = json.loads(json_text)
                    else:
                        # If no valid JSON found, raise error
                        raise ValueError("No valid JSON found in verification response")

                # Ensure the response has the expected structure
                expected_fields = ["status", "confidence", "corrections_applied", "corrections", "message"]
                for field in expected_fields:
                    if field not in verification_data:
                        if field == "status":
                            verification_data["status"] = "verification_error"
                        elif field == "confidence":
                            verification_data["confidence"] = 0
                        elif field == "corrections_applied":
                            verification_data["corrections_applied"] = False
                        elif field == "corrections":
                            verification_data["corrections"] = []
                        elif field == "message":
                            verification_data["message"] = "Verification completed"

                return verification_data

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing verification response: {str(e)}")
                raise ValueError(f"Failed to parse verification response: {str(e)}")

        except Exception as e:
            logger.error(f"Error verifying chart: {str(e)}")
            raise

    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about API usage.

        Returns:
            Usage statistics including token breakdown
        """
        return {
            "calls_made": self.api_calls,
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "estimated_cost": self.estimated_cost,
            "cache_stats": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "cache_hit_ratio": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
            }
        }

    async def _apply_rate_limiting(self):
        """
        Apply rate limiting to ensure we don't exceed the OpenAI API rate limits.
        Waits if necessary to stay under limits.
        """
        # Check if we've been making too many requests recently
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        # If it's been more than a minute since last request, reset counter
        if time_since_last_request > 60:
            self.tokens_this_minute = 0
            return

        # If we're approaching the rate limit, pause briefly
        if self.tokens_this_minute > self.rate_limit * 0.8:  # 80% of the limit
            logger.warning(f"Approaching rate limit ({self.tokens_this_minute} tokens), pausing briefly")
            # Calculate how long to wait based on how close we are to the limit
            wait_time = min(5, max(1, (self.tokens_this_minute / self.rate_limit) * 10))
            await asyncio.sleep(wait_time)

        # If we're very close to the limit, wait longer
        if self.tokens_this_minute > self.rate_limit * 0.95:  # 95% of the limit
            logger.warning(f"Very close to rate limit ({self.tokens_this_minute} tokens), waiting longer")
            await asyncio.sleep(10)  # Wait 10 seconds

def create_openai_service() -> OpenAIService:
    """
    Factory function for creating an OpenAI service.
    This is used by the dependency container.

    Returns:
        A new OpenAIService instance

    Raises:
        ValueError: If the service cannot be created
    """
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        service = OpenAIService(api_key=api_key)
        return service
    except Exception as e:
        logger.error(f"Failed to create OpenAI service: {e}")
        raise ValueError(f"Failed to create OpenAI service: {e}")

def get_openai_service() -> OpenAIService:
    """
    Get the OpenAI service instance from the dependency container or create a new one.

    Returns:
        An instance of the OpenAI service
    """
    from ai_service.utils.dependency_container import get_container

    container = get_container()
    try:
        # Try to get the service from the container
        return container.get("openai_service")
    except ValueError:
        # If not registered, create a new instance and register it
        service = OpenAIService()
        container.register_service("openai_service", service)
        return service
