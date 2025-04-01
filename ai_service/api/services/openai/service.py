from typing import Optional, Dict, Any, List, Union, Callable
import os
import json
import logging
import time
import asyncio
import traceback
from datetime import datetime, timedelta

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Global instance
_openai_service_instance = None

# OpenAI service implementation
class OpenAIService:
    def __init__(self, api_key: str):
        """
        Initialize the OpenAI service with an API key.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self._http_client = None
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://api.openai.com/v1"
        self.default_model = os.environ.get("OPENAI_MODEL", "gpt-4-turbo-preview")
        self.organization_id = os.environ.get("OPENAI_ORG_ID", "")
        self.max_retries = 3
        self.retry_delay = 1.0

    async def _ensure_http_client(self):
        """Ensure HTTP client is initialized."""
        if self._http_client is None and AIOHTTP_AVAILABLE:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Add organization header if available
            if self.organization_id:
                headers["OpenAI-Organization"] = self.organization_id

            self._http_client = aiohttp.ClientSession(headers=headers)
        return self._http_client is not None

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], aiohttp.ClientResponse]:
        """
        Send a chat completion request to the OpenAI API.

        Args:
            messages: List of message objects with role and content
            model: Model to use for completion (defaults to environment variable or gpt-4-turbo-preview)
            temperature: Sampling temperature (0-2), higher is more random
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalty for token frequency (-2.0 to 2.0)
            presence_penalty: Penalty for token presence (-2.0 to 2.0)
            stop: Sequences where the API will stop generating further tokens
            stream: Whether to stream the response

        Returns:
            API response as a dictionary or aiohttp.ClientResponse for streaming

        Raises:
            RuntimeError: If API call fails after retries
        """
        # Ensure HTTP client is available
        if not await self._ensure_http_client() or self._http_client is None:
            raise RuntimeError("HTTP client not available for OpenAI API calls")

        # Use specified model or default
        model_to_use = model or self.default_model

        # Prepare request data
        request_data = {
            "model": model_to_use,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "stream": stream
        }

        # Add optional parameters if provided
        if max_tokens is not None:
            request_data["max_tokens"] = max_tokens

        if stop is not None:
            request_data["stop"] = stop

        # URL for the chat completions endpoint
        url = f"{self.base_url}/chat/completions"

        # Implement retry logic
        for attempt in range(self.max_retries):
            try:
                async with self._http_client.post(url, json=request_data) as response:
                    if response.status == 200:
                        if stream:
                            # For streaming responses, wrap in a dictionary structure
                            return {"type": "stream", "response": response}
                        else:
                            # For regular responses, parse the JSON
                            return await response.json()
                    else:
                        # Handle error responses
                        error_data = await response.text()
                        self.logger.error(f"OpenAI API error (status {response.status}): {error_data}")

                        # Check for specific error types
                        if response.status == 429:
                            # Rate limit error, retry after delay
                            retry_after = int(response.headers.get("Retry-After", self.retry_delay * (2 ** attempt)))
                            self.logger.warning(f"Rate limited by OpenAI API. Retrying after {retry_after} seconds.")
                            await asyncio.sleep(retry_after)
                            continue

                        elif response.status == 500:
                            # Server error, retry after delay
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                            continue

                        # For other errors, raise exception
                        raise RuntimeError(f"OpenAI API error: {error_data} (status {response.status})")

            except aiohttp.ClientError as e:
                self.logger.error(f"HTTP error during OpenAI API call: {str(e)}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff for network errors
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise RuntimeError(f"Failed to connect to OpenAI API after {self.max_retries} attempts: {str(e)}")

        raise RuntimeError(f"OpenAI API call failed after {self.max_retries} attempts")

    async def text_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 150,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: Optional[Union[str, List[str]]] = None
    ) -> Union[Dict[str, Any], aiohttp.ClientResponse]:
        """
        Send a text completion request to the OpenAI API.

        This is a wrapper around chat_completion for backward compatibility.

        Args:
            prompt: Text prompt for completion
            model: Model to use for completion
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Penalty for token frequency
            presence_penalty: Penalty for token presence
            stop: Sequences where the API will stop generating

        Returns:
            API response as a dictionary or client response for streaming
        """
        # Convert text prompt to chat format
        messages = [{"role": "user", "content": prompt}]

        # Call chat completion
        response = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            stop=stop
        )

        # Return the response
        return response

    async def close(self):
        """Close the HTTP client session."""
        if self._http_client:
            await self._http_client.close()
            self._http_client = None

    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics for the OpenAI API.

        Returns:
            Dictionary with usage statistics or empty dict if unavailable
        """
        try:
            # Check if we have an API key
            if not self.api_key:
                self.logger.warning("Cannot get usage statistics: No API key")
                return {}

            # For now, return basic information
            return {
                "models": [self.default_model],
                "available": True,
                "last_check": datetime.now().isoformat(),
                "status": "operational"
            }
        except Exception as e:
            self.logger.error(f"Error getting OpenAI usage statistics: {str(e)}")
            return {}

    async def verify_chart(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify astrological chart data for accuracy using OpenAI.

        This method analyzes a birth chart to:
        1. Verify planetary positions and house cusps
        2. Check for potential birth time issues
        3. Provide confidence score and possible adjustments

        Args:
            chart_data: Complete chart data dictionary with planets, houses, etc.

        Returns:
            Dictionary with verification results including confidence score,
            suggested adjustments, and detailed analysis

        Raises:
            RuntimeError: If verification fails due to API issues
        """
        self.logger.info(f"Verifying chart with ID: {chart_data.get('chart_id', 'unknown')}")

        # Create structured verification prompt
        system_prompt = """You are an expert Vedic astrologer with extensive knowledge of astronomical calculations, birth chart interpretation, and astrological principles.

Your task is to analyze the birth chart data to:
1. Verify that planetary positions and house cusps are calculated correctly according to Vedic astrological principles
2. Determine if there's evidence the birth time might be slightly off based on planetary positions
3. Provide a confidence score between 0 and 1 for the chart's accuracy (1 = completely confident)
4. Suggest any necessary time adjustment (e.g., "+5 minutes" or "-3 minutes")
5. Explain your reasoning in astrological terms

Format your response using these exact headings:
CONFIDENCE: [score between 0-1]
SUGGESTED_ADJUSTMENT: [time adjustment or "No adjustment needed"]
SUGGESTED_TIME: [corrected time in HH:MM:SS format]
ADJUSTMENT_REASON: [brief reason for the adjustment]
VERIFICATION_RESULT: [detailed analysis]
"""

        # Extract data for user prompt
        birth_details = chart_data.get("birth_details", {})
        planets = chart_data.get("planets", {})
        houses = chart_data.get("houses", {})
        aspects = chart_data.get("aspects", [])
        ascendant = chart_data.get("ascendant", {})

        # Create user prompt with chart data
        user_prompt = "Please verify this astrological chart data:\n\n"

        # Add birth details
        user_prompt += "BIRTH DETAILS:\n"
        birth_date = birth_details.get("date", birth_details.get("birth_date", "Unknown"))
        birth_time = birth_details.get("time", birth_details.get("birth_time", "Unknown"))
        user_prompt += f"Date: {birth_date}\n"
        user_prompt += f"Time: {birth_time}\n"
        user_prompt += f"Latitude: {birth_details.get('latitude', 'Unknown')}\n"
        user_prompt += f"Longitude: {birth_details.get('longitude', 'Unknown')}\n"
        user_prompt += f"Timezone: {birth_details.get('timezone', 'Unknown')}\n\n"

        # Add ascendant information
        if ascendant:
            user_prompt += "ASCENDANT:\n"
            asc_sign = ascendant.get("sign", "Unknown")
            asc_degree = ascendant.get("degree", 0)
            asc_longitude = ascendant.get("longitude", 0)
            user_prompt += f"Sign: {asc_sign}, Degree: {asc_degree}°, Longitude: {asc_longitude}°\n\n"

        # Add planetary positions
        user_prompt += "PLANETARY POSITIONS:\n"
        for planet_name, planet_data in planets.items():
            if isinstance(planet_data, dict):
                sign = planet_data.get("sign", "Unknown")
                degree = planet_data.get("degree", 0)
                house = planet_data.get("house", "Unknown")
                longitude = planet_data.get("longitude", 0)
                retrograde = planet_data.get("is_retrograde", False)
                retrograde_str = " (Retrograde)" if retrograde else ""
                user_prompt += f"{planet_name}: {sign} {degree}° (House {house}), Longitude: {longitude}°{retrograde_str}\n"

        user_prompt += "\nHOUSE CUSPS:\n"
        # Handle houses in both dictionary and list format
        if isinstance(houses, dict):
            for house_num, house_data in houses.items():
                if isinstance(house_data, dict):
                    sign = house_data.get("sign", "Unknown")
                    degree = house_data.get("degree", 0)
                    longitude = house_data.get("longitude", 0)
                    user_prompt += f"House {house_num}: {sign} {degree}°, Longitude: {longitude}°\n"
                else:
                    # If house_data is just a longitude value
                    user_prompt += f"House {house_num}: Longitude: {house_data}°\n"
        elif isinstance(houses, list):
            for house in houses:
                house_num = house.get("number", "Unknown")
                sign = house.get("sign", "Unknown")
                degree = house.get("degree", 0)
                longitude = house.get("longitude", 0)
                user_prompt += f"House {house_num}: {sign} {degree}°, Longitude: {longitude}°\n"

        # Add aspects if available
        if aspects:
            user_prompt += "\nMAJOR ASPECTS:\n"
            for aspect in aspects[:10]:  # Limit to first 10 aspects to keep prompt size reasonable
                planet1 = aspect.get("planet1", "Unknown")
                planet2 = aspect.get("planet2", "Unknown")
                aspect_type = aspect.get("type", "Unknown")
                orb = aspect.get("orb", 0)
                user_prompt += f"{planet1} {aspect_type} {planet2} (Orb: {orb}°)\n"

        user_prompt += "\nPlease analyze this chart data carefully and verify its accuracy. Look for any inconsistencies or errors that might indicate the birth time needs adjustment."

        # Select appropriate model
        from ai_service.api.services.openai.model_selection import select_model
        model = select_model("verification")

        # Call OpenAI API
        try:
            response = await self.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=model,
                temperature=0.3,  # Lower temperature for more consistent results
                max_tokens=2000
            )

            # Extract and parse the response content
            response_content = ""
            # Check if response is a dict (standard response) or if it's a streaming response
            if isinstance(response, dict):
                if "choices" in response and len(response["choices"]) > 0:
                    if "message" in response["choices"][0] and "content" in response["choices"][0]["message"]:
                        response_content = response["choices"][0]["message"]["content"]
            # No need to handle streaming response here since we don't use stream=True for this function

            if not response_content:
                raise ValueError("Empty response from OpenAI API")

            # Parse the structured response
            import re

            # Initialize result dictionary with defaults
            verification_result = {
                "verified_with_openai": True,
                "status": "verification_completed",
                "verification_result": response_content,
                "timestamp": datetime.now().isoformat()
            }

            # Extract confidence score
            confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", response_content)
            if confidence_match:
                try:
                    verification_result["confidence"] = float(confidence_match.group(1))
                except ValueError:
                    self.logger.warning("Failed to parse confidence score")
                    verification_result["confidence"] = 0.5  # Default confidence
            else:
                verification_result["confidence"] = 0.5

            # Extract suggested adjustment
            adjustment_match = re.search(r"SUGGESTED_ADJUSTMENT:\s*([^\n]+)", response_content)
            if adjustment_match:
                adjustment = adjustment_match.group(1).strip()
                verification_result["suggested_adjustment"] = adjustment
                verification_result["corrections_applied"] = "No adjustment needed" not in adjustment
            else:
                verification_result["suggested_adjustment"] = "No adjustment needed"
                verification_result["corrections_applied"] = False

            # Extract suggested time
            time_match = re.search(r"SUGGESTED_TIME:\s*([^\n]+)", response_content)
            if time_match:
                verification_result["suggested_time"] = time_match.group(1).strip()
            else:
                # Use original time if available
                verification_result["suggested_time"] = birth_time

            # Extract adjustment reason
            reason_match = re.search(r"ADJUSTMENT_REASON:\s*([^\n]+)", response_content)
            if reason_match:
                verification_result["adjustment_reason"] = reason_match.group(1).strip()

            # Determine verification success based on confidence
            if verification_result.get("confidence", 0) >= 0.8:
                verification_result["message"] = "Chart verified with high confidence"
            elif verification_result.get("confidence", 0) >= 0.5:
                verification_result["message"] = "Chart verified with moderate confidence"
            else:
                verification_result["message"] = "Chart verification completed with low confidence"

            # Add chart ID if available
            if "chart_id" in chart_data:
                verification_result["chart_id"] = chart_data["chart_id"]

            self.logger.info(f"Chart verification completed with confidence: {verification_result.get('confidence', 'unknown')}")
            return verification_result

        except Exception as e:
            self.logger.error(f"Chart verification failed: {str(e)}")
            error_result = {
                "verified_with_openai": False,
                "status": "verification_error",
                "message": f"Verification failed: {str(e)}",
                "confidence": 0.0,
                "corrections_applied": False,
                "timestamp": datetime.now().isoformat()
            }

            # Add chart ID if available
            if "chart_id" in chart_data:
                error_result["chart_id"] = chart_data["chart_id"]

            return error_result

async def get_openai_service() -> Optional[OpenAIService]:
    """
    Get the global OpenAI service instance asynchronously.

    Returns:
        OpenAI service instance
    """
    global _openai_service_instance

    if _openai_service_instance is None:
        # Create a new instance
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            _openai_service_instance = OpenAIService(api_key)
            # Ensure the HTTP client is initialized
            await _openai_service_instance._ensure_http_client()

    return _openai_service_instance
