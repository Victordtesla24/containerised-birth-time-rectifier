"""
OpenAI integration for chart verification and astrological analysis.

This module provides the core OpenAI integration service for verifying
astrological chart calculations and performing birth time rectification.
"""

import os
import logging
import json
import re
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import openai
import backoff

# Configure logging
logger = logging.getLogger(__name__)

def __getattr__(name):
    """
    Lazy loading for OpenAIService to avoid circular imports.

    Args:
        name: Attribute name to load

    Returns:
        The requested attribute
    """
    if name == "get_openai_service":
        from ai_service.api.services.openai import get_openai_service as fn
        return fn
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

class OpenAIService:
    """
    Complete OpenAI service implementation for chart verification and rectification.
    """
    def __init__(self, api_key=None):
        """
        Initialize the OpenAI service with API key.

        Args:
            api_key: Optional OpenAI API key (defaults to environment variable)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OpenAI API key not provided! Verification features will not work.")

        self.client = openai.Client(api_key=self.api_key)
        self.usage_statistics = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost": 0.0,
            "calls": 0,
            "model_usage": {},
            "last_updated": datetime.now().isoformat()
        }

    def select_model(self, task_type: str) -> str:
        """
        Select the appropriate model based on task type.
        Uses environment variables for model selection to allow flexible configuration.

        Args:
            task_type: Type of task to select model for

        Returns:
            Name of the selected model
        """
        # Determine the task category
        task_category = self._get_task_category(task_type)

        # Get models from environment variables with defaults
        model_env_vars = {
            "rectification": os.environ.get("OPENAI_MODEL_RECTIFICATION", "o1-preview"),
            "calculation": os.environ.get("OPENAI_MODEL_CALCULATION", "o1-preview"),
            "visualization": os.environ.get("OPENAI_MODEL_VISUALIZATION", "gpt-4-turbo"),
            "questionnaire": os.environ.get("OPENAI_MODEL_QUESTIONNAIRE", "gpt-4-turbo"),
            "explanation": os.environ.get("OPENAI_MODEL_EXPLANATION", "gpt-4-turbo"),
            "auxiliary": os.environ.get("OPENAI_MODEL_AUXILIARY", "gpt-4o-mini")
        }

        model = model_env_vars.get(task_category, model_env_vars["auxiliary"])
        logger.info(f"Selected model {model} for task type {task_type}")
        return model

    def _get_task_category(self, task_type: str) -> str:
        """
        Categorize task types into high-level categories for key selection.

        Args:
            task_type: The specific task type string

        Returns:
            Category string: "rectification", "calculation", etc.
        """
        task_lower = task_type.lower()

        # Detailed categorization
        if "rectif" in task_lower or "birth time" in task_lower:
            return "rectification"
        elif "verif" in task_lower or "validate" in task_lower or "check" in task_lower:
            return "verification"
        elif "chart" in task_lower or "planet" in task_lower or "posit" in task_lower or "calculate" in task_lower:
            return "calculation"
        elif "visual" in task_lower or "render" in task_lower or "3d" in task_lower:
            return "visualization"
        elif "quest" in task_lower or "survey" in task_lower or "form" in task_lower:
            return "questionnaire"
        elif "explain" in task_lower or "interpret" in task_lower or "describe" in task_lower:
            return "explanation"
        else:
            return "auxiliary"

    @backoff.on_exception(backoff.expo,
                         (openai.RateLimitError, openai.InternalServerError, openai.APIConnectionError),
                         max_tries=3)
    async def chat_completion(self, messages, model=None, temperature=0.7, max_tokens=None,
                             stream=False, response_format=None):
        """
        Send a chat completion request to OpenAI with backoff retry logic.

        Args:
            messages: List of message dictionaries
            model: Model to use (if None, uses gpt-4-turbo)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
            response_format: Response format specification

        Returns:
            OpenAI chat completion response
        """
        if not model:
            model = "gpt-4-turbo"

        try:
            # Prepare parameters
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            if response_format:
                params["response_format"] = response_format

            # Make the API call
            start_time = time.time()
            response = await self.client.chat.completions.create(**params)
            elapsed = time.time() - start_time

            # Update usage statistics
            if not stream and hasattr(response, "usage") and response.usage:
                self._update_usage_statistics(
                    model=model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    elapsed_time=elapsed
                )

            return response
        except Exception as e:
            logger.error(f"OpenAI chat completion error: {str(e)}")
            raise

    def _update_usage_statistics(self, model, prompt_tokens, completion_tokens, elapsed_time):
        """Update internal usage statistics after an API call."""
        from ai_service.api.services.openai.cost_calculator import calculate_cost

        self.usage_statistics["total_tokens"] += prompt_tokens + completion_tokens
        self.usage_statistics["prompt_tokens"] += prompt_tokens
        self.usage_statistics["completion_tokens"] += completion_tokens
        self.usage_statistics["calls"] += 1
        self.usage_statistics["last_updated"] = datetime.now().isoformat()

        # Update model-specific usage
        if model not in self.usage_statistics["model_usage"]:
            self.usage_statistics["model_usage"][model] = {
                "calls": 0,
                "tokens": 0,
                "cost": 0.0
            }

        model_cost = calculate_cost(model, prompt_tokens, completion_tokens)
        self.usage_statistics["model_usage"][model]["calls"] += 1
        self.usage_statistics["model_usage"][model]["tokens"] += prompt_tokens + completion_tokens
        self.usage_statistics["model_usage"][model]["cost"] += model_cost
        self.usage_statistics["total_cost"] += model_cost

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get current usage statistics for monitoring."""
        return self.usage_statistics

    def verify_chart(self, chart_data: dict) -> dict:
        """
        Verify chart calculations against Vedic astrological standards using OpenAI.

        Args:
            chart_data: Chart data to verify

        Returns:
            Dictionary with verification results and corrected chart data
        """
        try:
            model = self.select_model("calculation")

            # Prepare the prompt with structured chart data
            prompt = self._prepare_verification_prompt(chart_data)

            # Send to OpenAI for verification
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a Vedic astrology expert verifying chart calculations."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            # Parse the verification result
            verification_result = self._parse_verification_result(response.choices[0].message.content)

            # Apply corrections if needed
            corrected_chart = chart_data.copy()
            if verification_result["corrections_needed"]:
                corrected_chart = self._apply_corrections(chart_data, verification_result["corrections"])

            return {
                "chart_data": corrected_chart,
                "verification": {
                    "verified": True,
                    "confidence_score": verification_result["confidence_score"],
                    "corrections_applied": verification_result["corrections_needed"],
                    "message": verification_result["message"],
                    "verified_at": datetime.now().isoformat(),
                    "verification_method": "openai_" + model
                }
            }
        except Exception as e:
            logger.error(f"OpenAI verification failed: {e}")
            # Return the original chart data with verification failure information
            return {
                "chart_data": chart_data,
                "verification": {
                    "verified": False,
                    "confidence_score": 0,
                    "corrections_applied": False,
                    "message": f"Verification failed: {str(e)}",
                    "verified_at": datetime.now().isoformat(),
                    "verification_method": "failed"
                }
            }

    def _prepare_verification_prompt(self, chart_data: Dict[str, Any]) -> str:
        """
        Prepare a prompt for chart verification.

        Args:
            chart_data: Chart data to verify

        Returns:
            Formatted verification prompt
        """
        # Extract relevant data for verification
        birth_details = chart_data.get("birth_details", {})
        planets = chart_data.get("planets", {})
        houses = chart_data.get("houses", [])

        # Format birth details
        birth_date = birth_details.get("birth_date", "Unknown")
        birth_time = birth_details.get("birth_time", "Unknown")
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)

        # Format the prompt
        prompt = f"""Please verify this Vedic astrological chart for technical accuracy.

Birth Information:
- Date: {birth_date}
- Time: {birth_time}
- Latitude: {latitude}
- Longitude: {longitude}

Planetary Positions:
"""

        # Add planetary positions
        if isinstance(planets, dict):
            for planet, data in planets.items():
                sign = data.get("sign", "Unknown")
                degree = data.get("degree", 0)
                longitude = data.get("longitude", 0)
                house = data.get("house", "Unknown")
                prompt += f"- {planet}: {sign} {degree}° (Longitude: {longitude}°, House: {house})\n"
        elif isinstance(planets, list):
            for planet_data in planets:
                planet = planet_data.get("name", "Unknown")
                sign = planet_data.get("sign", "Unknown")
                degree = planet_data.get("degree", 0)
                longitude = planet_data.get("longitude", 0)
                house = planet_data.get("house", "Unknown")
                prompt += f"- {planet}: {sign} {degree}° (Longitude: {longitude}°, House: {house})\n"

        # Add house data if available
        if houses:
            prompt += "\nHouse Cusps:\n"
            for i, house_data in enumerate(houses, 1):
                if isinstance(house_data, dict):
                    sign = house_data.get("sign", "Unknown")
                    degree = house_data.get("degree", 0)
                    prompt += f"- House {i}: {sign} {degree}°\n"
                else:
                    # If houses are just longitudes
                    prompt += f"- House {i}: {house_data}°\n"

        # Add verification instructions
        prompt += """
Please verify this chart according to Vedic astrological standards and provide your analysis in the following JSON format:

```json
{
  "verified": true/false,
  "confidence_score": 0-100,
  "corrections_needed": true/false,
  "message": "Summary of verification result",
  "corrections": [
    {
      "type": "planet_position/house_cusp/ascendant",
      "object": "name of planet or house",
      "current": "current value",
      "correct": "corrected value",
      "explanation": "reason for correction"
    }
  ]
}
```

If the chart is accurate, set "corrections_needed" to false and provide an empty corrections array.
Focus on these key verification points:
1. Correct planetary positions for the given date/time/location
2. Correct house cusps and ascendant calculation
3. Proper house placement of planets
4. Any contradictions or impossibilities in the chart

Please be detailed and specific with any corrections needed.
"""
        return prompt

    def _parse_verification_result(self, content: str) -> Dict[str, Any]:
        """
        Parse the OpenAI verification response.

        Args:
            content: OpenAI response content

        Returns:
            Parsed verification result
        """
        try:
            # Try to parse as JSON
            if isinstance(content, str):
                result = json.loads(content)
            else:
                result = content

            # Ensure required fields
            required_fields = ["verified", "confidence_score", "corrections_needed", "message"]
            for field in required_fields:
                if field not in result:
                    if field == "verified":
                        result[field] = False
                    elif field == "confidence_score":
                        result[field] = 0
                    elif field == "corrections_needed":
                        result[field] = False
                    elif field == "message":
                        result[field] = "Verification result incomplete"

            # Ensure corrections field exists
            if "corrections" not in result:
                result["corrections"] = []

            return result
        except Exception as e:
            logger.error(f"Error parsing verification result: {str(e)}")
            # Return default result on parsing error
            return {
                "verified": False,
                "confidence_score": 0,
                "corrections_needed": False,
                "message": f"Failed to parse verification result: {str(e)}",
                "corrections": []
            }

    def _apply_corrections(self, chart_data: Dict[str, Any], corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Apply corrections to chart data.

        Args:
            chart_data: Original chart data
            corrections: List of corrections to apply

        Returns:
            Corrected chart data
        """
        # Make a deep copy to avoid modifying the original
        corrected_chart = chart_data.copy()

        # Process each correction
        for correction in corrections:
            try:
                correction_type = correction.get("type")
                if not correction_type:
                    continue

                # Extract correction details
                object_name = correction.get("object")
                correct_value = correction.get("correct")

                if not object_name or correct_value is None:
                    continue

                # Apply correction based on type
                if correction_type == "planet_position":
                    # Handle different chart data structures
                    if "planets" in corrected_chart:
                        planets = corrected_chart["planets"]

                        if isinstance(planets, dict) and object_name in planets:
                            # Update planet data
                            self._update_planet_position(planets[object_name], correct_value)
                        elif isinstance(planets, list):
                            # Find and update planet in list
                            for planet in planets:
                                if planet.get("name") == object_name:
                                    self._update_planet_position(planet, correct_value)
                                    break

                elif correction_type == "house_cusp":
                    # Handle house cusp corrections
                    house_num = None
                    if object_name.startswith("House "):
                        try:
                            house_num = int(object_name.split(" ")[1])
                        except ValueError:
                            continue

                    if house_num and "houses" in corrected_chart:
                        houses = corrected_chart["houses"]

                        if isinstance(houses, list) and 1 <= house_num <= len(houses):
                            if isinstance(houses[house_num-1], dict):
                                self._update_house_cusp(houses[house_num-1], correct_value)
                            else:
                                # If houses are just longitudes
                                try:
                                    houses[house_num-1] = float(correct_value)
                                except ValueError:
                                    pass

                elif correction_type == "ascendant":
                    # Handle ascendant corrections
                    if "ascendant" in corrected_chart:
                        self._update_ascendant(corrected_chart["ascendant"], correct_value)
                    elif "angles" in corrected_chart and "asc" in corrected_chart["angles"]:
                        self._update_ascendant(corrected_chart["angles"]["asc"], correct_value)

            except Exception as e:
                logger.error(f"Error applying correction {correction}: {str(e)}")

        return corrected_chart

    def _update_planet_position(self, planet_data: Dict[str, Any], correct_value: str) -> None:
        """Update planet position data with corrected values."""
        # Parse the correction format: sign, degree, etc.
        try:
            # If correction is a full object
            if isinstance(correct_value, dict):
                if "sign" in correct_value:
                    planet_data["sign"] = correct_value["sign"]
                if "degree" in correct_value:
                    planet_data["degree"] = float(correct_value["degree"])
                if "longitude" in correct_value:
                    planet_data["longitude"] = float(correct_value["longitude"])
                if "house" in correct_value:
                    planet_data["house"] = int(correct_value["house"])

            # If correction is a string like "Aries 15.5°"
            elif isinstance(correct_value, str):
                # Look for sign and degree pattern
                match = re.search(r"([A-Za-z]+)\s+(\d+\.?\d*)", correct_value)
                if match:
                    sign, degree = match.groups()
                    planet_data["sign"] = sign.strip()
                    planet_data["degree"] = float(degree)

                # Look for longitude value
                longitude_match = re.search(r"longitude:?\s*(\d+\.?\d*)", correct_value, re.IGNORECASE)
                if longitude_match:
                    planet_data["longitude"] = float(longitude_match.group(1))

                # Look for house value
                house_match = re.search(r"house:?\s*(\d+)", correct_value, re.IGNORECASE)
                if house_match:
                    planet_data["house"] = int(house_match.group(1))
        except Exception as e:
            logger.error(f"Error updating planet position: {str(e)}")

    def _update_house_cusp(self, house_data: Dict[str, Any], correct_value: str) -> None:
        """Update house cusp data with corrected values."""
        try:
            # If correction is a full object
            if isinstance(correct_value, dict):
                if "sign" in correct_value:
                    house_data["sign"] = correct_value["sign"]
                if "degree" in correct_value:
                    house_data["degree"] = float(correct_value["degree"])
                if "longitude" in correct_value:
                    house_data["longitude"] = float(correct_value["longitude"])

            # If correction is a string like "Aries 15.5°"
            elif isinstance(correct_value, str):
                # Look for sign and degree pattern
                match = re.search(r"([A-Za-z]+)\s+(\d+\.?\d*)", correct_value)
                if match:
                    sign, degree = match.groups()
                    house_data["sign"] = sign.strip()
                    house_data["degree"] = float(degree)

                # Look for longitude value
                longitude_match = re.search(r"longitude:?\s*(\d+\.?\d*)", correct_value, re.IGNORECASE)
                if longitude_match:
                    house_data["longitude"] = float(longitude_match.group(1))
        except Exception as e:
            logger.error(f"Error updating house cusp: {str(e)}")

    def _update_ascendant(self, ascendant_data: Dict[str, Any], correct_value: str) -> None:
        """Update ascendant data with corrected values."""
        try:
            # If correction is a full object
            if isinstance(correct_value, dict):
                if "sign" in correct_value:
                    ascendant_data["sign"] = correct_value["sign"]
                if "degree" in correct_value:
                    ascendant_data["degree"] = float(correct_value["degree"])
                if "longitude" in correct_value:
                    ascendant_data["longitude"] = float(correct_value["longitude"])

            # If correction is a string like "Aries 15.5°"
            elif isinstance(correct_value, str):
                # Look for sign and degree pattern
                match = re.search(r"([A-Za-z]+)\s+(\d+\.?\d*)", correct_value)
                if match:
                    sign, degree = match.groups()
                    ascendant_data["sign"] = sign.strip()
                    ascendant_data["degree"] = float(degree)

                # Look for longitude value
                longitude_match = re.search(r"longitude:?\s*(\d+\.?\d*)", correct_value, re.IGNORECASE)
                if longitude_match:
                    ascendant_data["longitude"] = float(longitude_match.group(1))
        except Exception as e:
            logger.error(f"Error updating ascendant: {str(e)}")

    async def rectify_birth_time(self, chart_data: Dict[str, Any],
                               answers: List[Dict[str, Any]],
                               parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Rectify birth time using AI analysis of questionnaire answers.

        Args:
            chart_data: Original chart data
            answers: Questionnaire answers
            parameters: Optional rectification parameters

        Returns:
            Rectification results including the corrected birth time
        """
        try:
            model = self.select_model("rectification")

            # Prepare the prompt with structured chart and questionnaire data
            prompt = self._prepare_rectification_prompt(chart_data, answers, parameters)

            # Send to OpenAI for rectification
            response = await self.chat_completion(
                messages=[
                    {"role": "system", "content": "You are an expert Vedic astrologer specializing in birth time rectification."},
                    {"role": "user", "content": prompt}
                ],
                model=model,
                temperature=0.2,
                response_format={"type": "json_object"}
            )

            # Parse the rectification result
            content = response.choices[0].message.content
            if isinstance(content, str):
                result = json.loads(content)
            else:
                result = content

            # Validate required fields
            if "rectified_time" not in result:
                raise ValueError("Rectification result missing required field 'rectified_time'")

            # Format result
            return {
                "original_time": chart_data.get("birth_details", {}).get("birth_time", "Unknown"),
                "rectified_time": result["rectified_time"],
                "confidence": result.get("confidence", 0.0),
                "explanation": result.get("explanation", ""),
                "time_difference_minutes": result.get("time_difference_minutes", 0),
                "method": "ai_analysis",
                "rectified_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Birth time rectification failed: {e}")
            return {
                "error": f"Rectification failed: {str(e)}",
                "status": "error",
                "original_time": chart_data.get("birth_details", {}).get("birth_time", "Unknown"),
                "confidence": 0.0
            }

    def _prepare_rectification_prompt(self, chart_data: Dict[str, Any],
                                    answers: List[Dict[str, Any]],
                                    parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare a prompt for birth time rectification.

        Args:
            chart_data: Original chart data
            answers: Questionnaire answers
            parameters: Optional rectification parameters

        Returns:
            Formatted rectification prompt
        """
        # Extract birth details
        birth_details = chart_data.get("birth_details", {})
        birth_date = birth_details.get("birth_date", "Unknown")
        birth_time = birth_details.get("birth_time", "Unknown")
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        location = birth_details.get("location", "Unknown")

        # Format answers for prompt
        formatted_answers = []
        for i, answer in enumerate(answers, 1):
            question = answer.get("question_text", f"Question {i}")
            answer_text = answer.get("answer", "No answer")
            formatted_answers.append(f"Q{i}: {question}\nA{i}: {answer_text}")

        answers_text = "\n\n".join(formatted_answers)

        # Format the prompt
        prompt = f"""Please analyze this birth information and questionnaire responses to rectify the birth time according to Vedic astrological principles.

Birth Information:
- Date: {birth_date}
- Reported Time: {birth_time}
- Location: {location}
- Latitude: {latitude}
- Longitude: {longitude}

Questionnaire Responses:
{answers_text}

Based on your analysis of the questionnaire responses, life events, and astrological principles, please determine the most likely correct birth time.

Please return your analysis in the following JSON format:

```json
{{
  "rectified_time": "HH:MM:SS",
  "confidence": 0-100,
  "time_difference_minutes": integer,
  "explanation": "detailed explanation of rectification reasoning",
  "astrological_indicators": [
    "list of key astrological indicators that influenced this rectification"
  ]
}}
```

Consider factors like rising sign characteristics, house placements relevant to life events, planetary periods (dashas), and any transits mentioned in the questionnaire.
"""

        # Add any additional parameters
        if parameters:
            min_adjustment = parameters.get("min_adjustment", -120)
            max_adjustment = parameters.get("max_adjustment", 120)
            primary_factors = parameters.get("primary_factors", [])

            prompt += f"\n\nAdditional Parameters:\n"
            prompt += f"- Search Range: {min_adjustment} to {max_adjustment} minutes from reported time\n"

            if primary_factors:
                prompt += "- Primary Factors to Consider:\n"
                for factor in primary_factors:
                    prompt += f"  - {factor}\n"

        return prompt
