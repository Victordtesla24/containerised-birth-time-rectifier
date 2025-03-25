"""
Main OpenAI service implementation.
"""

import os
import logging
import json
import time
import uuid
import asyncio
import importlib.util
from typing import Dict, Any, List, Optional, TypedDict, cast, Union, TYPE_CHECKING, Callable
import sys
import random
import traceback
from datetime import datetime

# Import httpx for direct API calls
import httpx

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ai_service.api.services.openai.model_selection import select_model, get_task_category
from ai_service.api.services.openai.cost_calculator import calculate_cost
from ai_service.utils.dependency_container import get_container

# Set up logging
logger = logging.getLogger(__name__)

# Global OpenAI service instance
_openai_service_instance = None

# Define typed dictionary for cache entries
class CacheEntry(TypedDict):
    """Type definition for cache entries."""
    timestamp: float
    response: Dict[str, Any]
    response_json: Optional[Dict[str, Any]]

# Custom exception
class OpenAIError(Exception):
    """Exception raised when OpenAI API requests fail"""
    pass

class OpenAIService:
    """Service for interacting with the OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI service.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.http_client = None
        self.estimated_cost = 0.0
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.api_calls = 0
        self.cache = {}
        self.cache_enabled = True
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_ttl = 3600  # 1 hour
        self.rate_limit = 100000  # 100k tokens per minute
        self.tokens_this_minute = self.rate_limit  # Start with full capacity
        self.last_request_time = time.time()
        self.usage_stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "calls_made": 0,
            "total_cost": 0.0
        }
        self.default_model = "gpt-4"
        self.batch_queue = []
        self.batch_results = {}
        self.batch_threshold = 5

        # Initialize HTTP client immediately
        self._init_http_client()

    def _init_http_client(self):
        """Initialize the HTTP client for OpenAI API requests."""
        try:
            if not self.api_key:
                logger.error("No API key provided for OpenAI service")
                return

            self.http_client = httpx.AsyncClient(
                timeout=60.0,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            logger.info("HTTP client initialized for OpenAI API access")
        except Exception as e:
            logger.error(f"Failed to initialize HTTP client: {e}")

    async def _ensure_http_client(self):
        """Ensure HTTP client is initialized before making requests."""
        if self.http_client is None:
            self._init_http_client()
            if self.http_client is None:
                raise OpenAIError("Failed to initialize HTTP client for OpenAI API")

    async def close(self):
        """
        Close the OpenAI client and release resources.

        This method should be called when the service is no longer needed.
        """
        if self.http_client:
            try:
                await self.http_client.aclose()
                logger.info("HTTP client closed successfully")
                self.http_client = None
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")

    def _select_model(self, task_type: str) -> str:
        """
        Select the most appropriate model for a given task type.

        Args:
            task_type: Type of task to perform

        Returns:
            Model identifier
        """
        return select_model(task_type)

    def _format_messages(self, prompt: Union[str, Dict, List]) -> List[Dict[str, str]]:
        """
        Format the prompt into messages for chat completions.

        Args:
            prompt: Text prompt or dict of messages

        Returns:
            List of message dictionaries
        """
        if isinstance(prompt, str):
            return [{"role": "system", "content": "You are a helpful astrological assistant."},
                    {"role": "user", "content": prompt}]
        elif isinstance(prompt, dict) and "messages" in prompt:
            return prompt["messages"]
        elif isinstance(prompt, list):
            return prompt
        else:
            return [{"role": "system", "content": "You are a helpful astrological assistant."},
                    {"role": "user", "content": str(prompt)}]

    def _track_request(self, track_data: Dict[str, Any]) -> None:
        """
        Track API request for cost calculation and usage metrics.

        Args:
            track_data: Dictionary containing usage information
        """
        # Simplified cost calculation model
        cost_per_1k_input_tokens = {
            "gpt-4-turbo": 0.01,
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.0015,
        }

        cost_per_1k_output_tokens = {
            "gpt-4-turbo": 0.03,
            "gpt-4": 0.06,
            "gpt-3.5-turbo": 0.002,
        }

        model = track_data.get("model", "gpt-3.5-turbo")
        tokens_input = track_data.get("tokens_input", 0)
        tokens_output = track_data.get("tokens_output", 0)

        input_cost = tokens_input * (cost_per_1k_input_tokens.get(model, 0.0015) / 1000)
        output_cost = tokens_output * (cost_per_1k_output_tokens.get(model, 0.002) / 1000)

        total_cost = input_cost + output_cost
        self.estimated_cost += total_cost

        logger.info(f"OpenAI request tracked: {tokens_input} input tokens, {tokens_output} output tokens, cost ${total_cost:.6f}")

    async def generate_completion(self, prompt: Union[str, Dict, List], task_type: str = "rectification",
                           max_tokens: int = 1000, temperature: float = 0.2,
                           model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a completion from OpenAI.

        Args:
            prompt: Text prompt or structured prompt
            task_type: Type of task for model selection
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            model: Override model selection

        Returns:
            Completion response dictionary

        Raises:
            ValueError: If input parameters are invalid
            OpenAIError: If OpenAI API call fails
        """
        if not self.api_key:
            error_msg = "API key is required for OpenAI integration"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Ensure http_client is initialized
        await self._ensure_http_client()

        if not self.http_client:
            error_msg = "OpenAI client is not initialized"
            logger.error(error_msg)
            raise OpenAIError(error_msg)

        # Select model if not specified
        if not model:
            model = self._select_model(task_type)

        # Track costs and tokens
        track_data = {
            "tokens_input": 0,
            "tokens_output": 0,
            "model": model,
            "task_type": task_type,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            # Format the messages based on prompt type
            messages = self._format_messages(prompt)

            # Track the request start time
            start_time = datetime.now()

            # Make the API call
            logger.info(f"Calling OpenAI API with model {model}, task_type {task_type}")

            # Use HTTP client to make the request directly instead of using client.chat.completions.create
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            response = await self.http_client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload
            )

            # Check for errors
            response.raise_for_status()

            # Parse the response JSON
            response_data = response.json()

            # Track the request duration
            duration = (datetime.now() - start_time).total_seconds()

            # Process the response
            if not response_data or not response_data.get("choices") or len(response_data["choices"]) == 0:
                error_msg = "Empty response from OpenAI API"
                logger.error(error_msg)
                raise OpenAIError(error_msg)

            # Extract response content
            completion = response_data["choices"][0]["message"]["content"]

            # Update token tracking
            if "usage" in response_data:
                track_data["tokens_input"] = response_data["usage"].get("prompt_tokens", 0)
                track_data["tokens_output"] = response_data["usage"].get("completion_tokens", 0)

            # Track the request for cost calculation
            self._track_request(track_data)

            # Construct the result
            result = {
                "content": completion,
                "model": model,
                "task_type": task_type,
                "duration": duration,
                "tokens": {
                    "input": track_data["tokens_input"],
                    "output": track_data["tokens_output"],
                    "total": track_data["tokens_input"] + track_data["tokens_output"]
                },
                "id": str(uuid.uuid4())
            }

            return result

        except Exception as e:
            error_msg = f"Error calling OpenAI API: {str(e)}"
            logger.error(error_msg)
            raise OpenAIError(error_msg) from e

    async def _generate_completion_internal(self, prompt: str, task_type: str, max_tokens: int, temperature: float, stop: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """Internal method to generate a completion from OpenAI."""
        # Select model based on task type
        model = select_model(task_type)

        # Check for extremely long prompts and truncate if necessary
        if len(prompt) > 12000:  # Roughly 3000 tokens
            logger.warning(f"Prompt is very long ({len(prompt)} chars). Truncating to reduce API timeouts.")
            prompt = prompt[:12000] + "\n...[truncated for performance]..."

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
        logger.info(f"Sending request to OpenAI API (model: {model}, task: {task_type})")

        # Track API call
        self.api_calls += 1
        self.last_request_time = time.time()

        # Prepare messages for the API - simple format for maximum compatibility
        messages = [
            {"role": "user", "content": prompt}
        ]

        # Set a default completion result in case of timeout or error
        default_response = {
            "content": f"[Error processing request]",
            "model": model,
            "task_type": task_type,
            "error": True,
            "error_type": "APITimeout",
            "error_message": "Request timed out or failed",
            "usage": {
                "prompt_tokens": len(prompt) // 4,  # Rough estimate
                "completion_tokens": 0,
                "total_tokens": len(prompt) // 4,
                "cost": 0.0
            },
            "timestamp": time.time(),
            "id": str(uuid.uuid4())
        }

        try:
            # Set a timeout for the entire operation using asyncio
            request_timeout = 60  # 60 second timeout

            # Use direct API calls with httpx
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            # Try each of the methods in sequence
            try:
                # First, try using asyncio.wait_for to enforce a timeout
                await self._ensure_http_client()

                if self.http_client is None:
                    error_msg = "HTTP client is not available"
                    logger.error(error_msg)
                    raise OpenAIError(error_msg)

                response = await asyncio.wait_for(
                    self.http_client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload
                    ),
                    timeout=request_timeout
                )

                # Log the response status for debugging
                logger.info(f"OpenAI API status code: {response.status_code}")

                # Ensure successful response
                if response.status_code != 200:
                    error_content = response.text
                    logger.error(f"OpenAI API error: {response.status_code} - {error_content}")

                    # Handle different error codes
                    if response.status_code == 401:
                        raise ConnectionError("OpenAI API authentication failed - check your API key")
                    elif response.status_code == 429:
                        raise ConnectionError("OpenAI API rate limit exceeded - slow down requests")
                    elif response.status_code >= 500:
                        raise ConnectionError(f"OpenAI API server error {response.status_code} - try again later")
                    else:
                        raise ConnectionError(f"OpenAI API error {response.status_code}: {error_content}")

                # Parse the JSON response
                try:
                    response_data = response.json()
                except Exception as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Response content: {response.text[:500]}...")
                    raise ValueError(f"Failed to parse JSON response from OpenAI API: {e}")

                # Log a small part of the response for debugging
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0].get("message", {})
                    content_preview = message.get("content", "")[:50] + "..." if message.get("content") else ""
                    logger.info(f"OpenAI API response content preview: {content_preview}")

            except (httpx.ConnectTimeout, httpx.ReadTimeout) as timeout_err:
                logger.error(f"API connection timed out: {timeout_err}")
                logger.error("This may be due to network connectivity issues or firewall restrictions.")
                raise ConnectionError(f"OpenAI API connection timed out: {timeout_err}. Check your network connectivity.")

            except httpx.ConnectError as conn_err:
                logger.error(f"API connection error: {conn_err}")
                logger.error("This may be due to network connectivity issues or firewall restrictions.")
                raise ConnectionError(f"OpenAI API connection error: {conn_err}. Check your network connectivity.")

            except asyncio.TimeoutError:
                logger.error(f"API call timed out after {request_timeout} seconds")
                raise TimeoutError(f"OpenAI API call timed out after {request_timeout} seconds")

            # Extract content from response
            content = ""
            if "choices" in response_data and len(response_data["choices"]) > 0:
                message = response_data["choices"][0].get("message", {})
                content = message.get("content", "")

            # If content is empty for o1-preview, provide a default response instead of error
            if not content:
                if model == "o1-preview":
                    logger.warning(f"o1-preview model returned empty content - using default response")
                    content = '{"status": "verification_default", "confidence": 0, "corrections_applied": false, "corrections": [], "message": "Unable to verify chart due to model limitations."}'
                else:
                    raise ValueError("OpenAI API returned empty content")

            # Extract usage data
            usage = response_data.get("usage", {})
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
            else:
                # Use approximate counts if usage data is not available
                prompt_tokens = len(prompt) // 4  # Rough estimate
                completion_tokens = len(content) // 4  # Rough estimate
                total_tokens = prompt_tokens + completion_tokens

            # Update token tracking
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.total_tokens += total_tokens
            self.tokens_this_minute += total_tokens

            # Calculate cost
            cost = calculate_cost(model, prompt_tokens, completion_tokens)
            self.estimated_cost += cost

            # Build the response
            response_obj = {
                "content": content,
                "model": model,
                "task_type": task_type,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost
                },
                "timestamp": time.time(),
                "id": str(uuid.uuid4())
            }

            # Add to cache if enabled
            if self.cache_enabled:
                self.cache[cache_key] = CacheEntry(
                    timestamp=time.time(),
                    response=response_obj,
                    response_json=None
                )

            logger.info(f"OpenAI API call successful for {task_type}")
            return response_obj

        except (ConnectionError, TimeoutError) as conn_err:
            # For connection errors, we'll log and raise to trigger retry
            logger.error(f"Connection error with OpenAI API: {type(conn_err).__name__}: {conn_err}")
            raise conn_err

        except Exception as e:
            # For other errors, log and return error response without retrying
            logger.error(f"Error during OpenAI API call: {type(e).__name__}: {e}")

            error_response = {
                "content": f"Error: {str(e)}",
                "model": model,
                "task_type": task_type,
                "error": True,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "usage": {
                    "prompt_tokens": len(prompt) // 4,  # Rough estimate
                    "completion_tokens": 0,
                    "total_tokens": len(prompt) // 4,
                    "cost": 0.0
                },
                "timestamp": time.time(),
                "id": str(uuid.uuid4())
            }

            return error_response

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
                        # If we're using o1-preview model with our default response (which should be valid JSON)
                        if response.get("model") == "o1-preview" and "verification_default" in content:
                            verification_data = {
                                "status": "verification_default",
                                "confidence": 0,
                                "corrections_applied": False,
                                "corrections": [],
                                "message": "Unable to verify chart due to model limitations."
                            }
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
        Apply rate limiting to prevent hitting OpenAI API limits.

        This implements a token bucket algorithm to limit the number of requests
        and adds request batching to reduce API calls.
        """
        # Use a token bucket algorithm for rate limiting
        current_time = time.time()
        time_passed = current_time - self.last_request_time
        self.last_request_time = current_time

        # Refill tokens based on time passed
        tokens_to_add = time_passed * (self.rate_limit / 60.0)  # tokens per second
        self.tokens_this_minute = min(self.rate_limit, self.tokens_this_minute + tokens_to_add)

        # Default cost estimate per request (adjust based on your usage patterns)
        estimated_cost = 1000  # Estimate 1000 tokens per request

        # Check if we have enough tokens
        if self.tokens_this_minute < estimated_cost:
            # Calculate wait time to have enough tokens
            wait_time = (estimated_cost - self.tokens_this_minute) / (self.rate_limit / 60.0)
            logger.info(f"Rate limiting: waiting {wait_time:.2f}s before making request")
            await asyncio.sleep(wait_time)
            self.tokens_this_minute = self.rate_limit - estimated_cost
        else:
            # Deduct tokens for this request
            self.tokens_this_minute -= estimated_cost

        # If we're in a test environment, add a short delay between requests
        # to prevent overwhelming the API during tests
        if os.environ.get("TEST_MODE") == "true":
            await asyncio.sleep(0.5)  # 500ms delay between test requests

    async def _prepare_messages(self, prompt, task_type):
        """Prepare messages for the OpenAI API request."""
        system_prompts = {
            "chart_verification": "You are an expert in Vedic astrology, helping verify and correct astrological charts.",
            "birth_time_rectification": "You are an expert astrologer specializing in birth time rectification techniques.",
            "chart_interpretation": "You are an expert astrologer providing detailed chart interpretations.",
            "questionnaire": "You are a helpful assistant answering questions about life events.",
            "general": "You are a helpful AI assistant."
        }

        system_message = system_prompts.get(task_type, system_prompts["general"])

        # Use model selection to determine the model
        model = select_model(task_type)

        # For o1-preview model, don't include system message as it's not supported
        if model == "o1-preview":
            # Handle different prompt types for o1-preview
            if isinstance(prompt, str):
                # Convert system message context into the user message
                return [
                    {"role": "user", "content": f"As an {system_message.replace('You are ', '')}: {prompt}"}
                ]
            elif isinstance(prompt, dict) and all(k in prompt for k in ["system", "user"]):
                # For o1-preview, combine system and user messages
                system_context = prompt["system"]
                user_content = prompt["user"]
                return [
                    {"role": "user", "content": f"Acting as {system_context}: {user_content}"}
                ]
            elif isinstance(prompt, list) and all(isinstance(m, dict) for m in prompt):
                # Filter out system messages for o1-preview
                filtered_messages = []
                system_content = None

                # First extract any system message content to prepend to user message
                for m in prompt:
                    if isinstance(m, dict):
                        if m.get("role") == "system":
                            system_content = m.get("content")
                        else:
                            filtered_messages.append(m.copy())

                # If we have system content and user messages, prepend to first user message
                if system_content and filtered_messages:
                    for i, msg in enumerate(filtered_messages):
                        if msg.get("role") == "user":
                            filtered_messages[i]["content"] = f"Acting as {system_content}: {msg['content']}"
                            break
            else:
                # Default to treating as user message
                return [
                    {"role": "user", "content": str(prompt)}
                ]
        else:
            # For models that support system messages
            if isinstance(prompt, str):
                return [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
            elif isinstance(prompt, dict) and all(k in prompt for k in ["system", "user"]):
                return [
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ]
            elif isinstance(prompt, list) and all(isinstance(m, dict) for m in prompt):
                return prompt  # Already in OpenAI format
            else:
                # Default to treating as user message
                return [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": str(prompt)}
                ]

    async def _send_request(self, messages, model, max_tokens, temperature):
        """
        Send a request to the OpenAI API.

        Args:
            messages: List of message objects
            model: The model to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature setting

        Returns:
            API response
        """
        base_url = "https://api.openai.com/v1/chat/completions"

        # Prepare headers and data
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Construct the request body
        data = {
            "model": model,
            "messages": messages,
            "top_p": 1,
            "presence_penalty": 0,
            "frequency_penalty": 0
        }

        # Use correct parameter name based on model
        if model == "o1-preview":
            data["max_completion_tokens"] = max_tokens
        else:
            data["max_tokens"] = max_tokens
            data["temperature"] = temperature

        try:
            # Make the API call with proper error handling
            await self._ensure_http_client()

            if self.http_client is None:
                error_msg = "HTTP client is not available"
                logger.error(error_msg)
                raise OpenAIError(error_msg)

            response = await self.http_client.post(
                base_url,
                headers=headers,
                json=data,
                timeout=90.0  # Extended timeout for potentially long completions
            )

            # Check for HTTP errors
            response.raise_for_status()

            # Parse JSON response
            result = response.json()

            # Update usage metrics
            if "usage" in result:
                self.prompt_tokens += result["usage"].get("prompt_tokens", 0)
                self.completion_tokens += result["usage"].get("completion_tokens", 0)
                self.total_tokens = self.prompt_tokens + self.completion_tokens

            return result

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        except httpx.ReadTimeout:
            error_msg = "Request timed out. The server took too long to respond."
            logger.error(error_msg)
            raise TimeoutError(error_msg)

        except httpx.ConnectTimeout:
            error_msg = "Connection timed out. Could not establish connection to the API."
            logger.error(error_msg)
            raise ConnectionError(error_msg)

        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(error_msg)
            raise ConnectionError(error_msg)

        except json.JSONDecodeError:
            error_msg = "Invalid JSON response from API"
            logger.error(error_msg)
            raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"Unexpected error in API request: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise

def get_openai_service() -> Optional[OpenAIService]:
    """
    Get the global OpenAI service instance.

    Returns:
        OpenAI service instance
    """
    global _openai_service_instance

    if _openai_service_instance is None:
        # Create a new instance
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            _openai_service_instance = OpenAIService(api_key)

    return _openai_service_instance
