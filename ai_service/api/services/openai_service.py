"""
OpenAI service for interacting with OpenAI API.
Provides optimized, fault-tolerant access to various OpenAI models.
"""

import os
import time
from typing import Dict, Any, List, Optional
import logging
import openai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Set up logging
logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Service for interacting with OpenAI API.
    Provides optimized, fault-tolerant access to various OpenAI models.
    """

    def __init__(self):
        """Initialize the OpenAI service with configuration"""
        # Load API key from environment variables
        self.api_key = os.environ.get("OPENAI_API_KEY")

        # Fallback to development configuration if not in production
        if not self.api_key and os.environ.get("APP_ENV") != "production":
            self.api_key = os.environ.get("OPENAI_API_KEY_DEV")
            logger.warning("Using development API key. Not recommended for production.")

        # Verify API key is available
        if not self.api_key:
            raise EnvironmentError(
                "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable. "
                "You can set this in a .env file or directly in your environment."
            )

        self.client = openai.OpenAI(api_key=self.api_key)

        # Configure request parameters
        self.timeout = int(os.environ.get("API_TIMEOUT", "30"))  # Timeout in seconds
        self.cache_expiry = int(os.environ.get("CACHE_EXPIRY", "3600"))  # Cache expiry in seconds

        # Track API usage for cost management
        self.usage_stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "calls_made": 0,
        }

        logger.info("OpenAI service initialized")

    @retry(
        retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying OpenAI API call: attempt {retry_state.attempt_number} after error: {retry_state.outcome.exception()}"
        )
    )
    async def generate_completion(
        self,
        prompt: str,
        task_type: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a completion using the appropriate OpenAI model for the task.

        Args:
            prompt: The user prompt
            task_type: Type of task ("rectification", "explanation", or other)
            max_tokens: Maximum tokens for the completion
            temperature: Temperature for response generation
            system_message: Optional system message to set context

        Returns:
            Dictionary with response and usage statistics
        """
        try:
            start_time = time.time()

            # Select appropriate model
            model = self._select_model(task_type)

            # Prepare messages
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            else:
                default_system_message = "You are an expert in Vedic astrology specializing in birth time rectification."
                messages.append({"role": "system", "content": default_system_message})

            messages.append({"role": "user", "content": prompt})

            # Make API call with timeout protection
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=self.timeout
            )

            # Update usage statistics
            self.usage_stats["calls_made"] += 1
            self.usage_stats["prompt_tokens"] += response.usage.prompt_tokens
            self.usage_stats["completion_tokens"] += response.usage.completion_tokens
            self.usage_stats["total_tokens"] += response.usage.total_tokens

            # Calculate cost - for tracking purposes
            cost = self._calculate_cost(model, response.usage.prompt_tokens, response.usage.completion_tokens)

            # Prepare response
            completion_response = {
                "content": response.choices[0].message.content,
                "model_used": model,
                "tokens": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                },
                "cost": cost,
                "response_time": round(time.time() - start_time, 2)
            }

            # Log usage (but not content for privacy)
            logger.info(
                f"OpenAI API call completed: model={model}, tokens={completion_response['tokens']['total']}, "
                f"cost=${cost:.4f}, time={completion_response['response_time']}s"
            )

            return completion_response

        except Exception as e:
            logger.error(f"Error generating OpenAI completion: {str(e)}")
            raise

    def _select_model(self, task_type: str) -> str:
        """
        Select the appropriate model based on task type.

        Args:
            task_type: The type of task

        Returns:
            Model identifier string
        """
        if "rectification" in task_type.lower():
            return "o1-preview"  # High-accuracy astronomical calculations
        elif "explanation" in task_type.lower():
            return "gpt-4-turbo"  # Cost-efficient user interactions
        else:
            return "gpt-4o-mini"  # Lightweight auxiliary tasks

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate the cost of an API call based on the model and token usage.

        Args:
            model: The model used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Estimated cost in USD
        """
        # Set rate per 1M tokens (in USD)
        rates = {
            "o1-preview": {"input": 15.0, "output": 75.0},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-4o-mini": {"input": 5.0, "output": 15.0}
        }

        # Default to GPT-4 Turbo rates if model not found
        rate = rates.get(model, rates["gpt-4-turbo"])

        # Calculate cost (convert to per-token rate from per-million rate)
        input_cost = (prompt_tokens / 1_000_000) * rate["input"]
        output_cost = (completion_tokens / 1_000_000) * rate["output"]

        return round(input_cost + output_cost, 6)

    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get current API usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        return {
            **self.usage_stats,
            "estimated_cost": self._calculate_total_cost()
        }

    def _calculate_total_cost(self) -> float:
        """
        Calculate the total estimated cost of all API calls made.

        Returns:
            Total estimated cost in USD
        """
        # This is a simplification - in production you would track per-model usage
        # For now we'll use an average rate
        avg_input_rate = 10.0  # $10 per 1M tokens
        avg_output_rate = 30.0  # $30 per 1M tokens

        input_cost = (self.usage_stats["prompt_tokens"] / 1_000_000) * avg_input_rate
        output_cost = (self.usage_stats["completion_tokens"] / 1_000_000) * avg_output_rate

        return round(input_cost + output_cost, 4)
