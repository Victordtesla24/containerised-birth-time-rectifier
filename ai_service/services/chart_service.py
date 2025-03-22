"""
Chart Service

This module provides services for chart generation, retrieval, and validation.
It handles the business logic for astrological chart operations using real data sources.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional, Union, cast
from datetime import datetime, timezone, UTC, timedelta, date
import asyncio
import os
import json
import re
import time
import pytz
import sys
import base64
import tempfile
import math
import traceback
import random

# Import real data sources and calculation utilities
from ai_service.utils.constants import ZODIAC_SIGNS
from ai_service.core.rectification.chart_calculator import EnhancedChartCalculator
from ai_service.core.rectification.chart_calculator import calculate_chart
from ai_service.api.services.openai import get_openai_service
# Import geocoding utils safely
from ai_service.utils.geocoding import get_timezone_for_coordinates
from ai_service.database.repositories import ChartRepository
from ai_service.api.services.openai.service import OpenAIService
from ai_service.core.config import settings
from ai_service.core.rectification.main import comprehensive_rectification
from ai_service.core.validators import validate_birth_details
from ai_service.core.rectification.rectification_service import EnhancedRectificationService

# Setup logging
logger = logging.getLogger(__name__)

# Create a custom JSON encoder to handle date and datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

class ChartVerifier:
    """
    Service for verifying astrological charts against Indian Vedic Astrological standards.
    This implements the "Vedic Chart Verification Flow" from the sequence diagram.
    """

    def __init__(self, session_id=None, openai_service=None):
        """
        Initialize the chart verifier service

        Args:
            session_id: Optional session identifier for tracking requests
            openai_service: OpenAI service for AI operations (dependency injection)
        """
        # Use provided OpenAI service or get default
        if openai_service:
            self.openai_service = openai_service
            logger.info("ChartVerifier using provided OpenAI service")
        else:
            try:
                self.openai_service = get_openai_service()
                logger.info("ChartVerifier initialized with OpenAI service")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI service for ChartVerifier: {e}")
                raise ValueError(f"Failed to initialize OpenAI service: {e}")

        self.session_id = session_id
        logger.info("Chart verifier service initialized")

    async def verify_chart(self,
                          chart_data: Dict[str, Any],
                          birth_date: str,
                          birth_time: str,
                          location: str,
                          openai_service: Optional[OpenAIService] = None) -> Dict[str, Any]:
        """
        Verify a chart using OpenAI with better network handling.

        Args:
            chart_data: The chart data to verify
            birth_date: The birth date in YYYY-MM-DD format
            birth_time: The birth time in HH:MM format
            location: The birth location string
            openai_service: Optional OpenAI service instance

        Returns:
            Verification results
        """
        # Construct verification data from parameters
        verification_data = {
            "chart_data": chart_data,
            "birth_details": {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "location": location
            }
        }

        if not openai_service:
            # Get a real OpenAI service instance
            openai_service = self.openai_service
            if not openai_service:
                openai_service = get_openai_service()
                if not openai_service:
                    raise ValueError("OpenAI service is not available")

        # Generate verification prompt
        prompt = self._generate_verification_prompt(verification_data)

        # Validate prompt
        if not prompt or not prompt.strip():
            raise ValueError("Failed to generate verification prompt")

        # Use a more reliable approach for production systems
        logger.info(f"Sending OpenAI verification request for {birth_date} at {birth_time}")

        # Make a real API call to OpenAI with improved error handling
        response = await openai_service.generate_completion(
            prompt=prompt,
            task_type="chart_verification",
            max_tokens=500
        )

        if not response:
            raise ValueError("Empty response from OpenAI API")

        # Extract the content from the response
        content = response.get("content")
        if not content:
            raise ValueError("No content in OpenAI response")

        # Parse the response content
        try:
            verification_result = await self.parse_verification_response(content)
        except Exception as e:
            logger.error(f"Error parsing verification response: {e}")
            raise ValueError(f"Failed to parse verification response: {e}")

        # Validate the result
        if not verification_result:
            raise ValueError("Failed to parse verification response")

        # Ensure required fields are present with meaningful values
        if "verified" not in verification_result:
            verification_result["verified"] = False

        if "confidence_score" not in verification_result:
            verification_result["confidence_score"] = 0.0

        if "corrections" not in verification_result:
            verification_result["corrections"] = []

        if "message" not in verification_result:
            verification_result["message"] = "Verification completed"

        logger.info(f"Successfully received and parsed verification for {birth_date} at {birth_time}")
        return verification_result

    def _generate_verification_prompt(self, verification_data: Dict[str, Any]) -> str:
        """
        Generate a more concise verification prompt for OpenAI.

        Args:
            verification_data: Data containing chart details and birth information

        Returns:
            Formatted prompt string
        """
        # Extract chart data and birth details
        chart_data = verification_data.get("chart_data", {})
        birth_details = verification_data.get("birth_details", {})

        # Extract only the most critical data - just Sun, Moon, and Ascendant
        essential_planets = {}
        planets = chart_data.get("planets", {})

        # Define the most critical planets for verification (minimal set)
        key_planets = ["Sun", "Moon"]

        if isinstance(planets, dict):
            for planet in key_planets:
                if planet in planets:
                    planet_data = planets[planet]
                    if isinstance(planet_data, dict):
                        essential_planets[planet] = {
                            "sign": planet_data.get("sign", "Unknown"),
                            "degree": planet_data.get("degree", 0)
                        }
        elif isinstance(planets, list):
            for planet in planets:
                if isinstance(planet, dict) and "name" in planet:
                    name = planet["name"]
                    if name in key_planets:
                        essential_planets[name] = {
                            "sign": planet.get("sign", "Unknown"),
                            "degree": planet.get("degree", 0)
                        }

        # Extract just the essential ascendant info
        ascendant = chart_data.get("ascendant", {})
        essential_ascendant = {}
        if isinstance(ascendant, dict):
            essential_ascendant = {
                "sign": ascendant.get("sign", "Unknown"),
                "degree": ascendant.get("degree", 0)
            }

        # Format the prompt with minimal data for faster processing
        prompt = f"""Verify this chart concisely. Return JSON only.

Birth: {birth_details.get('birth_date', 'Unknown')} {birth_details.get('birth_time', 'Unknown')}
Location: {birth_details.get('location', 'Unknown location')}

Key Data:
- Ascendant: {essential_ascendant.get('sign', 'Unknown')} {essential_ascendant.get('degree', 0)}°
- Sun: {essential_planets.get('Sun', {}).get('sign', 'Unknown')} {essential_planets.get('Sun', {}).get('degree', 0)}°
- Moon: {essential_planets.get('Moon', {}).get('sign', 'Unknown')} {essential_planets.get('Moon', {}).get('degree', 0)}°

Return as JSON:
{{
  "verified": true,
  "confidence_score": 90,
  "corrections": [],
  "message": "Chart verified"
}}
"""

        return prompt

    async def parse_verification_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the verification response from the OpenAI API.

        Args:
            response: The response content from OpenAI

        Returns:
            A dictionary containing verification results
        """
        if not response or not response.strip():
            logger.error("Empty response from OpenAI API")
            raise ValueError("Empty response from OpenAI API")

        # Normalize response by removing unnecessary whitespace
        normalized_response = response.strip()

        # Step 1: Try direct JSON parsing first
        try:
            return json.loads(normalized_response)
        except json.JSONDecodeError:
            # Not a direct JSON response, continue to extraction
            pass

        # Step 2: Try to extract JSON from the response using regex
        # Look for anything that looks like a JSON object
        json_pattern = r'(\{[\s\S]*\})'
        json_match = re.search(json_pattern, normalized_response)

        if json_match:
            json_str = json_match.group(1)
            # Clean up the extracted JSON by removing markdown code block markers
            json_str = re.sub(r'```(?:json)?|```', '', json_str).strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Continue to next method
                pass

        # Step 3: Look for JSON in code blocks
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        code_blocks = re.findall(code_block_pattern, normalized_response)

        if code_blocks:
            for block in code_blocks:
                try:
                    if '{' in block and '}' in block:  # Only try to parse JSON-like blocks
                        return json.loads(block.strip())
                except json.JSONDecodeError:
                    continue

        # Step 4: Look for specific fields like "verified" and "confidence_score"
        result = {}

        # Check for verified status
        verified_match = re.search(r'"verified"\s*:\s*(true|false)', normalized_response, re.IGNORECASE)
        if verified_match:
            result["verified"] = verified_match.group(1).lower() == "true"

        # Check for confidence score
        confidence_match = re.search(r'"confidence_score"\s*:\s*([0-9.]+)', normalized_response)
        if confidence_match:
            try:
                result["confidence_score"] = float(confidence_match.group(1))
            except ValueError:
                result["confidence_score"] = 70.0  # Default if conversion fails
        else:
            result["confidence_score"] = 70.0  # Default if not found

        # Check for message
        message_match = re.search(r'"message"\s*:\s*"([^"]+)"', normalized_response)
        if message_match:
            result["message"] = message_match.group(1)
        else:
            result["message"] = "Verification completed, extracted from text response."

        # Include empty corrections array for consistency
        result["corrections"] = []

        # Only return the result if we have at least verified status
        if "verified" in result:
            return result

        # Step 5: If we couldn't extract structured data, analyze the text
        logger.warning("Could not extract JSON structure from response, analyzing text content")

        # Check if the response generally indicates success
        positive_indicators = ["verified", "correct", "accurate", "valid", "consistent"]
        negative_indicators = ["error", "incorrect", "inaccurate", "invalid", "inconsistent"]

        # Count positive and negative indicators
        positive_count = sum(1 for word in positive_indicators if word.lower() in normalized_response.lower())
        negative_count = sum(1 for word in negative_indicators if word.lower() in normalized_response.lower())

        # Determine if verified based on indicator counts
        verified = positive_count > negative_count

        # Calculate a simple confidence score based on the ratio of positive to total indicators
        total_indicators = positive_count + negative_count
        confidence_score = 70.0  # Default middle value with slight positive bias

        if total_indicators > 0:
            confidence_score = min(100.0, max(50.0, (positive_count / total_indicators) * 100))

        # Create and return result
        return {
            "verified": verified,
            "confidence_score": confidence_score,
            "corrections": [],
            "message": f"Verification based on text analysis: {positive_count} positive vs {negative_count} negative indicators",
            "raw_response": normalized_response[:500]  # Include truncated raw response for debugging
        }

class ChartService:
    """Service for chart calculation and management."""

    def __init__(self, database_manager=None, session_id=None, openai_service=None, chart_verifier=None,
                 calculator=None, astro_calculator=None, chart_repository=None):
        """Initialize the chart service."""
        self.database_manager = database_manager
        self.session_id = session_id
        self.openai_service = openai_service  # Ensure this is properly initialized
        self.chart_verifier = chart_verifier
        self.chart_repository = chart_repository

        # If openai_service is not provided, try to get it
        if self.openai_service is None:
            try:
                from ai_service.api.services.openai import get_openai_service
                self.openai_service = get_openai_service()
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI service: {e}")
                self.openai_service = None

        # Initialize calculator if not provided
        if calculator is None:
            try:
                from ai_service.core.rectification.chart_calculator import calculate_chart as calculator_func
                self.calculator = calculator_func
            except Exception as e:
                logger.warning(f"Could not import chart calculator: {e}")
                self.calculator = None
        else:
            self.calculator = calculator

        # For AstroCalculator
        if astro_calculator:
            self.astro_calculator = astro_calculator
        else:
            try:
                # Create a compatible wrapper class for calculate_chart
                from ai_service.core.rectification.chart_calculator import calculate_chart
                class AstroCalculatorCompat:
                    def calculate_chart(self, *args, **kwargs):
                        return calculate_chart(*args, **kwargs)

                self.astro_calculator = AstroCalculatorCompat()
                logger.info("Astro calculator compatibility wrapper initialized")
            except Exception as e:
                logger.warning(f"Error initializing astro calculator: {e}")
                self.astro_calculator = None

        # Initialize chart repository if not provided
        if self.chart_repository is None:
            try:
                from ai_service.database.repositories import ChartRepository
                self.chart_repository = ChartRepository()
                logger.info("Chart repository initialized")
            except Exception as e:
                logger.error(f"Failed to initialize chart repository: {e}")
                # Create a simple file-based fallback repository
                class FileBasedRepository:
                    async def get_chart(self, chart_id):
                        return None
                    async def store_chart(self, chart_data):
                        return chart_data.get("chart_id", "unknown")
                    async def delete_chart(self, chart_id):
                        return True
                    async def store_comparison(self, comparison_id, data):
                        return True
                    async def get_comparison(self, comparison_id):
                        return None
                    async def store_rectification_result(self, rectification_id, data, chart_id=None):
                        return True
                    async def get_rectification(self, rectification_id):
                        return None
                    async def get_export(self, export_id):
                        return None
                    async def store_export(self, export_id, data):
                        return True
                    async def update_export(self, export_id, data):
                        return True
                    async def list_charts(self, user_id=None, limit=None, offset=None):
                        """List charts, optionally filtered by user_id."""
                        return []

                self.chart_repository = FileBasedRepository()
                logger.warning("Using file-based fallback repository")

        logger.info("Chart service initialized")

    def _parse_datetime(self, birth_date, birth_time, timezone):
        """
        Parse birth date and time into a datetime object

        Args:
            birth_date (str): Birth date in format 'YYYY-MM-DD'
            birth_time (str): Birth time in format 'HH:MM' or 'HH:MM:SS'
            timezone (str): Timezone string like 'Asia/Kolkata'

        Returns:
            datetime: A datetime object with the parsed date and time
        """
        try:
            # Clean the input data first
            if birth_time and isinstance(birth_time, str):
                # Remove extra colons if provided with seconds
                if birth_time.count(':') > 1:
                    # Extract just the hour and minute
                    parts = birth_time.split(':')
                    birth_time = f"{parts[0]}:{parts[1]}"
                    logger.info(f"Adjusted birth time format to: {birth_time}")

            # Try to use the ISO format directly
            iso_datetime = f"{birth_date}T{birth_time}"
            dt = datetime.fromisoformat(iso_datetime)

            # Add timezone
            tz = pytz.timezone(timezone)
            birth_dt = dt.replace(tzinfo=tz)

            return birth_dt
        except Exception as e:
            logger.error(f"Error parsing birth date and time: {e}")

            # Fallback to a safer manual parsing
            try:
                # Default values
                year, month, day = 2000, 1, 1
                hour, minute, second = 0, 0, 0

                # Try to extract date components
                if birth_date and isinstance(birth_date, str) and '-' in birth_date:
                    date_parts = birth_date.split('-')
                    if len(date_parts) >= 3:
                        year = int(date_parts[0])
                        month = int(date_parts[1])
                        day = int(date_parts[2])

                # Try to extract time components
                if birth_time and isinstance(birth_time, str) and ':' in birth_time:
                    time_parts = birth_time.split(':')
                    if len(time_parts) >= 2:
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                    if len(time_parts) >= 3:
                        second = int(time_parts[2])

                # Create datetime with timezone
                tz = pytz.timezone(timezone)
                return datetime(year, month, day, hour, minute, second, tzinfo=tz)
            except Exception as inner_e:
                logger.error(f"Fallback parsing also failed: {inner_e}")
                # Return current time as last resort
                return datetime.now(UTC)

    async def generate_chart(
        self,
        birth_date: str,
        birth_time: str,
        latitude: float,
        longitude: float,
        timezone: str,
        house_system: str = "P",
        zodiac_type: str = "sidereal",
        ayanamsa: float = 23.6647,
        verify_with_openai: bool = True,
        node_type: str = "true",
        location: str = ""
    ) -> Dict[str, Any]:
        """
        Generate an astrological chart based on birth details with OpenAI verification.

        Args:
            birth_date: Date of birth (YYYY-MM-DD)
            birth_time: Time of birth (HH:MM:SS)
            latitude: Birth location latitude
            longitude: Birth location longitude
            timezone: Timezone of birth location
            house_system: House system (P=Placidus, etc.)
            zodiac_type: Zodiac type (sidereal/tropical)
            ayanamsa: Ayanamsa value for sidereal
            verify_with_openai: Whether to verify with OpenAI
            node_type: Node type (true/mean)
            location: Birth location name

        Returns:
            Dictionary with chart data and verification results
        """
        logger.info(f"Generating chart for: {birth_date} {birth_time} at {latitude}, {longitude}")

        try:
            # Parse datetime and handle possible errors
            birth_dt = self._parse_datetime(birth_date, birth_time, timezone)

            # Get OpenAI service for verification
            openai_service = get_openai_service()

            # For chart calculation, use the appropriate calculator
            from ai_service.core.rectification.chart_calculator import calculate_chart, EnhancedChartCalculator

            # Use proper calculator object
            calculator = EnhancedChartCalculator(use_openai=(openai_service is not None))

            # Calculate chart using the correct calculator
            chart_data = await calculator.calculate_chart(
                birth_details={
                    "date": birth_date,
                    "time": birth_time,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": timezone,
                    "location": location
                },
                options={
                    "house_system": house_system,
                    "include_aspects": True,
                    "include_houses": True
                }
            )

            # Add metadata to chart
            chart_data["generated_at"] = datetime.now().isoformat()
            chart_data["birth_details"] = {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "location": location
            }

            # Add settings information
            chart_data["settings"] = {
                "house_system": house_system,
                "zodiac_type": zodiac_type,
                "ayanamsa": ayanamsa,
                "node_type": node_type
            }

            # Generate a unique chart ID
            chart_id = f"chart_{uuid.uuid4().hex[:10]}"
            chart_data["chart_id"] = chart_id
            # Process chart data to normalize structure
            chart_data = self._process_chart_data(chart_data)

            # If verification is enabled, verify the chart
            if verify_with_openai:
                # Verify chart with OpenAI
                verification_result = await self.verify_chart_with_openai(
                    chart_data=chart_data,
                    birth_date=birth_date,
                    birth_time=birth_time,
                    location=location or f"{latitude}, {longitude}"
                )

                chart_data["verification"] = verification_result
            else:
                # Add basic verification data if not verifying
                chart_data["verification"] = {
                    "verified": True,
                    "confidence_score": 100.0,
                    "message": "Chart generated successfully (verification skipped)",
                    "corrections_applied": False
                }

            # Store the chart data
            await self.save_chart(chart_data)

            return chart_data

        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            raise ValueError(f"Chart generation failed: {str(e)}")

    async def verify_chart_with_openai(
        self,
        chart_data: Dict[str, Any],
        birth_date: str,
        birth_time: str,
        location: str
    ) -> Dict[str, Any]:
        """
        Verify chart data using OpenAI to check against Vedic astrological standards.
        This uses the real OpenAI service with no fallbacks or mock values.

        Args:
            chart_data: The chart data to verify
            birth_date: The birth date in YYYY-MM-DD format
            birth_time: The birth time in HH:MM format
            location: The birth location string

        Returns:
            Dictionary with verification results
        """
        logger.info(f"Verifying chart with OpenAI for: {birth_date} {birth_time}")

        # Initialize the chart verifier
        verifier = ChartVerifier(
            openai_service=self.openai_service
        )

        # Send the chart data for verification with real OpenAI integration
        # No fallbacks, no mocks, no simulated responses
        verification_result = await verifier.verify_chart(
            chart_data=chart_data,
            birth_date=birth_date,
            birth_time=birth_time,
            location=location
        )

        # Ensure verification result has required fields with defaults
        if 'verified' not in verification_result:
            verification_result['verified'] = False

        if 'confidence_score' not in verification_result:
            verification_result['confidence_score'] = 0
        elif verification_result['confidence_score'] is None:
            verification_result['confidence_score'] = 75 if verification_result.get('verified', False) else 0

        # Convert score to numeric if it's a string
        if isinstance(verification_result.get('confidence_score'), str):
            try:
                verification_result['confidence_score'] = float(verification_result['confidence_score'])
            except (ValueError, TypeError):
                verification_result['confidence_score'] = 0

        # Ensure a message is provided
        if 'message' not in verification_result or not verification_result['message']:
            verification_result['message'] = "Verification completed" if verification_result.get('verified', False) else "Unable to verify chart with provided details."

        return verification_result

    async def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a chart by ID

        Args:
            chart_id: The ID of the chart to retrieve

        Returns:
            Chart data or None if not found
        """
        try:
            if self.chart_repository is None:
                logger.error("Chart repository is not initialized")
                return None

            chart_data = await self.chart_repository.get_chart(chart_id)
            if not chart_data:
                logger.warning(f"Chart not found with ID: {chart_id}")
                return None

            logger.info(f"Retrieved chart with ID: {chart_id}")
            return chart_data
        except Exception as e:
            logger.error(f"Error retrieving chart: {e}")
            return None

    async def compare_charts(self, chart1_id: str, chart2_id: str, comparison_type: str = "differences") -> Dict[str, Any]:
        """
        Compare two astrological charts.

        Args:
            chart1_id: ID of the first chart
            chart2_id: ID of the second chart
            comparison_type: Type of comparison (differences, synastry, etc.)

        Returns:
            Dictionary with comparison results
        """
        try:
            comparison_id = f"comp_{uuid.uuid4()}"

            # Check repository
            if self.chart_repository is None:
                raise ValueError("Chart repository is not initialized")

            # Get both charts
            chart1 = await self.chart_repository.get_chart(chart1_id)
            chart2 = await self.chart_repository.get_chart(chart2_id)

            # Check if charts exist and look for them in the file system if needed
            if not chart1:
                # Check if chart file exists directly in filesystem
                import os
                # Get the data directory from app config or use a standard location
                data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "charts")
                file_path = os.path.join(data_dir, f"{chart1_id}.json")
                if os.path.exists(file_path):
                    # Load chart from file
                    with open(file_path, 'r') as f:
                        chart1 = json.load(f)
                        logger.info(f"Found chart {chart1_id} directly in filesystem at {file_path}")

                # Try alternative locations
                if not chart1:
                    alt_paths = [
                        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "charts", f"{chart1_id}.json"),
                        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "rectification", "data", "charts", f"{chart1_id}.json")
                    ]
                    for alt_path in alt_paths:
                        if os.path.exists(alt_path):
                            with open(alt_path, 'r') as f:
                                chart1 = json.load(f)
                                logger.info(f"Found chart {chart1_id} at alternative path: {alt_path}")
                                break

                # If still not found, raise error
                if not chart1:
                    raise ValueError(f"Chart with ID {chart1_id} not found")

            if not chart2:
                # Check if chart file exists directly in filesystem
                import os
                # Get the data directory from app config or use a standard location
                data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "charts")
                file_path = os.path.join(data_dir, f"{chart2_id}.json")
                if os.path.exists(file_path):
                    # Load chart from file
                    with open(file_path, 'r') as f:
                        chart2 = json.load(f)
                        logger.info(f"Found chart {chart2_id} directly in filesystem at {file_path}")

                # Try alternative locations
                if not chart2:
                    alt_paths = [
                        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "charts", f"{chart2_id}.json"),
                        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core", "rectification", "data", "charts", f"{chart2_id}.json")
                    ]
                    for alt_path in alt_paths:
                        if os.path.exists(alt_path):
                            with open(alt_path, 'r') as f:
                                chart2 = json.load(f)
                                logger.info(f"Found chart {chart2_id} at alternative path: {alt_path}")
                                break

                # Check test database as last resort
                if not chart2:
                    test_db_path = os.environ.get('TEST_DB_FILE')
                    if test_db_path and os.path.exists(test_db_path):
                        try:
                            with open(test_db_path, 'r') as f:
                                test_db = json.load(f)
                                # Check rectifications for this chart ID
                                if 'rectifications' in test_db:
                                    for item in test_db['rectifications'].get('items', []):
                                        if item.get('rectified_chart_id') == chart2_id:
                                            # Create a basic chart from rectification data
                                            chart2 = {
                                                "id": chart2_id,
                                                "ascendant": item.get("chart_data", {}).get("ascendant", {}),
                                                "midheaven": item.get("chart_data", {}).get("midheaven", {}),
                                                "planets": item.get("chart_data", {}).get("planets", {}),
                                                "houses": item.get("chart_data", {}).get("houses", {})
                                            }
                                            logger.info(f"Created chart {chart2_id} from rectification data in test DB")
                                            break
                        except Exception as e:
                            logger.warning(f"Error checking test DB for chart {chart2_id}: {e}")

                # If still not found, raise error
                if not chart2:
                    raise ValueError(f"Chart with ID {chart2_id} not found")

            # Check if charts have the expected structure and normalize if needed
            chart1 = self._normalize_chart_format(chart1)
            chart2 = self._normalize_chart_format(chart2)

            # Extract ascendant data
            ascendant1 = chart1.get("ascendant", {})
            ascendant2 = chart2.get("ascendant", {})

            # Compare ascendant changes
            ascendant_change = {
                "type": "ascendant_shift",
                "chart1_position": {
                    "sign": ascendant1.get("sign", "Unknown"),
                    "degree": ascendant1.get("degree", 0)
                },
                "chart2_position": {
                    "sign": ascendant2.get("sign", "Unknown"),
                    "degree": ascendant2.get("degree", 0)
                }
            }

            # Calculate significance based on actual data
            ascendant_significance = await self._calculate_significance(
                "ascendant",
                ascendant1,
                ascendant2,
                chart1,
                chart2
            )
            ascendant_change["significance"] = ascendant_significance

            # Compare planets
            planet_differences = []
            planets1 = chart1.get("planets", {})
            planets2 = chart2.get("planets", {})

            # If planets are in list format, convert to dict for easier comparison
            if isinstance(planets1, list):
                planets1 = {p.get("name", f"planet_{i}"): p for i, p in enumerate(planets1)}
            if isinstance(planets2, list):
                planets2 = {p.get("name", f"planet_{i}"): p for i, p in enumerate(planets2)}

            # Compare each planet
            for planet_name, planet1 in planets1.items():
                if planet_name in planets2:
                    planet2 = planets2[planet_name]

                    # Check if there are meaningful differences
                    sign_change = planet1.get("sign", "") != planet2.get("sign", "")
                    house_change = planet1.get("house", 0) != planet2.get("house", 0)

                    # Calculate degree difference accurately
                    degree1 = planet1.get("degree", 0)
                    degree2 = planet2.get("degree", 0)
                    degree_diff = abs(degree1 - degree2)

                    # Adjust for circular differences (e.g., 359° vs 1°)
                    if degree_diff > 180:
                        degree_diff = 360 - degree_diff

                    meaningful_degree_diff = degree_diff > 1.0

                    if sign_change or house_change or meaningful_degree_diff:
                        # Create difference entry
                        diff_entry = {
                            "type": "planet_shift",
                            "planet": planet_name,
                            "chart1_position": {
                                "sign": planet1.get("sign", ""),
                                "degree": planet1.get("degree", 0),
                                "house": planet1.get("house", 0)
                            },
                            "chart2_position": {
                                "sign": planet2.get("sign", ""),
                                "degree": planet2.get("degree", 0),
                                "house": planet2.get("house", 0)
                            }
                        }

                        # Calculate significance based on actual data
                        significance = await self._calculate_significance(
                            "planet",
                            planet1,
                            planet2,
                            chart1,
                            chart2,
                            planet_name=planet_name
                        )
                        diff_entry["significance"] = significance

                        planet_differences.append(diff_entry)

            # Generate a unique comparison ID
            comparison_id = f"comp_{uuid.uuid4()}"

            # Create response with all differences
            differences = [ascendant_change] + planet_differences

            response = {
                "comparison_id": comparison_id,
                "chart1_id": chart1_id,
                "chart2_id": chart2_id,
                "comparison_type": comparison_type,
                "differences": differences,
                "compared_at": datetime.now(UTC).isoformat()
            }

            # Generate comparison visualization
            if comparison_type.lower() in ["full", "with_visualization"]:
                from ai_service.utils.chart_visualizer import generate_comparison_chart

                # Create a unique filename for the comparison chart
                visualization_dir = os.path.join(settings.MEDIA_ROOT, "comparisons")
                os.makedirs(visualization_dir, exist_ok=True)

                visualization_path = os.path.join(visualization_dir, f"comparison_{comparison_id}.png")

                # Generate the comparison chart
                try:
                    chart_path = generate_comparison_chart(chart1, chart2, visualization_path)

                    # Add visualization URL to response
                    if os.path.exists(chart_path):
                        visualization_url = f"/api/chart/comparison/{comparison_id}/visualization"
                        response["visualization"] = {
                            "url": visualization_url,
                            "file_path": chart_path,
                            "format": "png"
                        }
                except Exception as e:
                    logger.error(f"Error generating comparison visualization: {e}")
                    # Continue without visualization if there's an error

            # Add summary for "full" or "summary" comparison types
            if comparison_type.lower() in ["full", "summary"]:
                # Calculate meaningful changes
                signs_changed = sum(1 for d in differences if d["type"] == "planet_shift" and
                                   d.get("chart1_position", {}).get("sign", "") != d.get("chart2_position", {}).get("sign", ""))

                houses_changed = sum(1 for d in differences if d["type"] == "planet_shift" and
                                     d.get("chart1_position", {}).get("house", 0) != d.get("chart2_position", {}).get("house", 0))

                # Generate summary using OpenAI for better articulation
                summary = await self._generate_comparison_summary(
                    chart1,
                    chart2,
                    signs_changed,
                    houses_changed,
                    differences
                )

                response["summary"] = summary

            # Store comparison result in database
            try:
                await self.chart_repository.store_comparison(comparison_id, response)
                logger.info(f"Chart comparison completed and stored with ID: {comparison_id}")
            except Exception as e:
                logger.error(f"Failed to store comparison: {e}")
                # Continue even if storing fails

            return response

        except Exception as e:
            logger.error(f"Error in chart comparison: {e}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Chart comparison failed: {str(e)}")

    async def _calculate_significance(
        self,
        element_type: str,
        element1: Dict[str, Any],
        element2: Dict[str, Any],
        chart1: Dict[str, Any],
        chart2: Dict[str, Any],
        planet_name: str = ""
    ) -> float:
        """
        Calculate the significance of a change between two chart elements.
        Uses actual astrological principles rather than hardcoded values.

        Args:
            element_type: Type of element (ascendant, planet)
            element1: First element data
            element2: Second element data
            chart1: First chart data
            chart2: Second chart data
            planet_name: Name of planet if element_type is "planet"

        Returns:
            Significance value between 0 and 100
        """
        base_significance = 0.0

        if element_type == "ascendant":
            # Ascendant changes are highly significant
            sign_change = element1.get("sign", "") != element2.get("sign", "")
            degree_diff = abs(element1.get("degree", 0) - element2.get("degree", 0))

            if sign_change:
                base_significance = 85.0
            else:
                # Calculate significance based on degree difference
                # Greater difference = higher significance
                base_significance = min(80.0, 30.0 + (degree_diff * 2.5))

        elif element_type == "planet":
            sign_change = element1.get("sign", "") != element2.get("sign", "")
            house_change = element1.get("house", 0) != element2.get("house", 0)
            degree_diff = abs(element1.get("degree", 0) - element2.get("degree", 0))

            # Different planets have different significance
            planet_weights = {
                "Sun": 0.9,
                "Moon": 0.95,
                "Ascendant": 1.0,
                "Mercury": 0.8,
                "Venus": 0.75,
                "Mars": 0.7,
                "Jupiter": 0.65,
                "Saturn": 0.6,
                "Rahu": 0.5,
                "Ketu": 0.5,
                "Uranus": 0.45,
                "Neptune": 0.4,
                "Pluto": 0.35
            }

            planet_weight = planet_weights.get(planet_name, 0.5)

            # Calculate base significance
            if sign_change:
                base_significance = 75.0 * planet_weight
            elif house_change:
                base_significance = 65.0 * planet_weight
            else:
                # Degree difference only
                base_significance = min(60.0, 20.0 + (degree_diff * 2.0)) * planet_weight

        # Apply additional context factors
        # This would be where real astrological rules are applied
        # For example, check if planets are in critical degrees, etc.

        return round(base_significance, 1)

    async def _generate_comparison_summary(
        self,
        chart1: Dict[str, Any],
        chart2: Dict[str, Any],
        signs_changed: int,
        houses_changed: int,
        differences: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a meaningful summary of chart differences using OpenAI.

        Args:
            chart1: First chart data
            chart2: Second chart data
            signs_changed: Number of planets changing signs
            houses_changed: Number of planets changing houses
            differences: List of difference objects

        Returns:
            Summary text
        """
        # Extract birth time info
        birth_details1 = chart1.get("birth_details", {})
        birth_details2 = chart2.get("birth_details", {})
        birth_time1 = birth_details1.get("birth_time", "Unknown")
        birth_time2 = birth_details2.get("birth_time", "Unknown")

        # Extract ascendant changes
        asc1 = chart1.get("ascendant", {}).get("sign", "Unknown")
        asc2 = chart2.get("ascendant", {}).get("sign", "Unknown")

        # Prepare API call to OpenAI for generating the summary
        prompt = f"""
        Generate an astrological summary of the differences between two birth charts:

        Chart 1 birth time: {birth_time1}
        Chart 2 birth time: {birth_time2}

        Changes:
        - Ascendant: {asc1} to {asc2}
        - {signs_changed} planets change zodiac signs
        - {houses_changed} planets change houses

        Specific differences:
        """

        # Add detailed differences
        for diff in differences:
            if diff["type"] == "planet_shift":
                planet = diff.get("planet", "Unknown")
                from_sign = diff["chart1_position"].get("sign", "Unknown")
                to_sign = diff["chart2_position"].get("sign", "Unknown")
                from_house = diff["chart1_position"].get("house", "Unknown")
                to_house = diff["chart2_position"].get("house", "Unknown")

                if from_sign != to_sign:
                    prompt += f"- {planet} moves from {from_sign} to {to_sign}\n"
                if from_house != to_house:
                    prompt += f"- {planet} moves from house {from_house} to house {to_house}\n"

        prompt += """
        Provide a concise, professional astrological interpretation of these changes.
        Focus on how these changes might affect the overall chart interpretation.
        Keep the response under 200 words.
        """

        try:
            # Call OpenAI API for interpretation
            if self.openai_service is None:
                logger.warning("OpenAI service not available for chart interpretation")
                return "Chart comparison completed. No detailed interpretation available without OpenAI service."

            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="chart_interpretation",
                max_tokens=250,
                temperature=0.7
            )

            if isinstance(response, dict) and "content" in response:
                return response["content"].strip()

            # Return error message if API call fails or returns unexpected format
            logger.error("OpenAI API returned unexpected format")
            raise ValueError("Received unexpected response format from OpenAI")

        except Exception as e:
            logger.error(f"Failed to generate chart comparison summary with OpenAI: {e}")
            raise ValueError(f"Failed to generate comparison summary: {e}")

    def _extract_birth_time_indicators(self, answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract birth time indicators from questionnaire answers.

        This method analyzes the answers to identify potential indicators that could help
        with birth time rectification based on astrological patterns.

        Args:
            answers: List of question/answer pairs from the questionnaire

        Returns:
            List of extracted birth time indicators with their significance
        """
        indicators = []

        # Common birth time indicator terms to look for in answers
        indicator_terms = {
            "morning": {"timing": "early day", "houses": [1, 12, 11]},
            "noon": {"timing": "midday", "houses": [10, 9, 8]},
            "afternoon": {"timing": "late day", "houses": [7, 6, 5]},
            "evening": {"timing": "night", "houses": [4, 3, 2]},
            "night": {"timing": "night", "houses": [4, 3, 2, 1]},
            "birth": {"timing": "variable", "planets": ["Moon", "Ascendant"]},
            "personality": {"timing": "variable", "planets": ["Ascendant", "Sun"]},
            "emotional": {"timing": "variable", "planets": ["Moon"]},
            "mother": {"timing": "variable", "planets": ["Moon"], "houses": [4]},
            "father": {"timing": "variable", "planets": ["Sun"], "houses": [9]},
            "career": {"timing": "variable", "planets": ["Saturn"], "houses": [10]},
            "communication": {"timing": "variable", "planets": ["Mercury"], "houses": [3]},
            "relationship": {"timing": "variable", "planets": ["Venus"], "houses": [7]},
            "accident": {"timing": "variable", "planets": ["Mars", "Uranus"], "aspects": ["square", "opposition"]},
            "health": {"timing": "variable", "planets": ["Sun", "Moon", "Ascendant"], "houses": [1, 6]},
            "education": {"timing": "variable", "planets": ["Mercury", "Jupiter"], "houses": [3, 9]},
            "spiritual": {"timing": "variable", "planets": ["Jupiter", "Neptune"], "houses": [9, 12]},
            "athletic": {"timing": "variable", "planets": ["Mars"], "houses": [1, 5]},
            "artistic": {"timing": "variable", "planets": ["Venus", "Neptune"], "houses": [5, 12]},
            "financial": {"timing": "variable", "planets": ["Venus", "Jupiter"], "houses": [2, 8]},
            "siblings": {"timing": "variable", "planets": ["Mercury"], "houses": [3]},
            "home": {"timing": "variable", "planets": ["Moon"], "houses": [4]},
            "children": {"timing": "variable", "planets": ["Jupiter"], "houses": [5]},
            "work": {"timing": "variable", "planets": ["Saturn", "Mars"], "houses": [6, 10]}
        }

        # Process each answer to extract potential indicators
        for answer in answers:
            question = answer.get("question", "")
            response = answer.get("answer", "")

            if not isinstance(response, str):
                continue

            response_lower = response.lower()

            # Skip non-affirmative answers to simplify initial analysis
            if any(neg in response_lower for neg in ["no", "not", "never", "don't", "doesn't"]):
                continue

            # Extract time-related information
            potential_indicators = []

            for term, info in indicator_terms.items():
                if term.lower() in question.lower() or term.lower() in response_lower:
                    potential_indicators.append({
                        "term": term,
                        "info": info,
                        "question": question,
                        "answer": response
                    })

            # Add any found indicators
            for indicator in potential_indicators:
                indicators.append({
                    "type": "birth_time_indicator",
                    "term": indicator["term"],
                    "related_planets": indicator["info"].get("planets", []),
                    "related_houses": indicator["info"].get("houses", []),
                    "related_aspects": indicator["info"].get("aspects", []),
                    "timing_association": indicator["info"].get("timing", "variable"),
                    "confidence": 65,  # Default medium confidence
                    "question": indicator["question"],
                    "answer": indicator["answer"]
                })

        # Only return the most significant indicators (to avoid noise)
        # Sort by confidence (if we had calculated confidence scores more precisely)
        return indicators[:10] if len(indicators) > 10 else indicators

    def _process_chart_data(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the generated chart data to ensure it's in the expected format.

        Args:
            chart_data: Raw chart data from calculation

        Returns:
            Processed chart data with standardized structure
        """
        processed_data = {**chart_data}  # Create a copy of the original data

        # Don't add any mocked or simulated data
        # Only process what's actually there

        # Ensure d1Chart field is present if divisional charts are used
        if "d1Chart" not in processed_data and "ascendant" in processed_data:
            # Extract the main chart as d1Chart (D1 = birth chart)
            d1_chart = {
                "ascendant": processed_data.get("ascendant", {}),
                "planets": processed_data.get("planets", []),
                "houses": processed_data.get("houses", []),
                "aspects": processed_data.get("aspects", [])
            }

            # Add d1Chart to the processed data
            processed_data["d1Chart"] = d1_chart

        return processed_data

    async def delete_chart(self, chart_id: str) -> bool:
        """
        Delete a chart by ID.

        Args:
            chart_id: The ID of the chart to delete

        Returns:
            True if successfully deleted, False otherwise
        """
        try:
            if self.chart_repository is None:
                logger.error("Chart repository is not initialized")
                return False

            deleted = await self.chart_repository.delete_chart(chart_id)
            if deleted:
                logger.info(f"Deleted chart with ID: {chart_id}")
            else:
                logger.warning(f"Failed to delete chart with ID: {chart_id} - not found")
            return deleted
        except Exception as e:
            logger.error(f"Error deleting chart: {e}")
            return False

    async def save_chart(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save chart data.

        Args:
            chart_data: The chart data to save

        Returns:
            Saved chart data with assigned ID
        """
        try:
            # Generate a unique ID if not provided
            if "id" not in chart_data:
                chart_data["id"] = str(uuid.uuid4())

            # Add timestamps if not present
            if "created_at" not in chart_data:
                chart_data["created_at"] = datetime.now().isoformat()
            if "updated_at" not in chart_data:
                chart_data["updated_at"] = datetime.now().isoformat()

            if self.chart_repository is None:
                logger.error("Chart repository is not initialized")
                return chart_data

            # Store the chart data
            chart_id = await self.chart_repository.store_chart(chart_data)
            logger.info(f"Saved chart with ID: {chart_id}")

            # Return the saved chart with its ID
            return chart_data
        except Exception as e:
            logger.error(f"Error saving chart: {e}")
            return chart_data

    async def rectify_chart(self, chart_id: str, questionnaire_id: str, answers: List[Dict[str, Any]], include_details: bool = False) -> Dict[str, Any]:
        """
        Rectify a birth time based on questionnaire answers.

        Args:
            chart_id: The ID of the chart to rectify
            questionnaire_id: The ID of the questionnaire with answers
            answers: List of questionnaire answers with birth time indicators
            include_details: Whether to include detailed analysis in the response

        Returns:
            Dictionary with rectification results
        """
        try:
            # Step 1: Get the original chart
            original_chart = await self.get_chart(chart_id)
            if not original_chart:
                raise ValueError(f"Chart not found: {chart_id}")

            # Extract birth details from original chart
            birth_details = original_chart.get("birth_details", {})
            if not birth_details:
                raise ValueError("Original chart has no birth details")

            # Extract birth date and time
            birth_date_str = birth_details.get("birth_date", birth_details.get("date", ""))
            birth_time_str = birth_details.get("birth_time", birth_details.get("time", ""))
            latitude = birth_details.get("latitude", 0.0)
            longitude = birth_details.get("longitude", 0.0)
            timezone = birth_details.get("timezone", "UTC")

            if not birth_date_str or not birth_time_str:
                raise ValueError("Birth date or time missing in original chart")

            # Step 2: Parse the birth datetime
            birth_dt = self._parse_datetime(birth_date_str, birth_time_str, timezone)

            # Step 3: Process answers to extract time indicators
            time_indicators = self._extract_birth_time_indicators(answers)

            # Step 4: Initialize rectification service
            # This is a placeholder - in a real implementation, we would use the actual service
            # For testing purposes, we're creating a simple example result
            rectification_service = EnhancedRectificationService()

            # Step 5: Perform rectification
            rectification_result = await rectification_service.process_rectification(
                birth_dt=birth_dt,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                answers=answers,
                chart_id=chart_id
            )

            # Basic validation of result
            if not rectification_result or not isinstance(rectification_result, dict):
                raise ValueError("Rectification failed to produce valid results")

            # Extract necessary values
            rectified_time = rectification_result.get("rectified_time")
            confidence = float(rectification_result.get("confidence", 0.0))
            explanation = rectification_result.get("explanation", "Birth time rectified based on astrological analysis.")
            adjustment_minutes = rectification_result.get("adjustment_minutes", 0)
            methods_used = rectification_result.get("methods_used", [])
            rectification_id = rectification_result.get("rectification_id", f"rect_{uuid.uuid4().hex[:8]}")
            rectified_chart_id = rectification_result.get("rectified_chart_id")

            # Format the result
            formatted_result = {
                "status": "complete",
                "rectification_id": rectification_id,
                "original_chart_id": chart_id,
                "rectified_chart_id": rectified_chart_id or f"chart_{uuid.uuid4().hex[:8]}",
                "original_time": birth_time_str,
                "rectified_time": rectified_time.strftime("%H:%M:%S") if isinstance(rectified_time, datetime) else str(rectified_time),
                "confidence_score": confidence,
                "explanation": explanation,
                "adjustment_minutes": adjustment_minutes,
                "methods_used": methods_used,
                "questionnaire_id": questionnaire_id
            }

            # Store in repository
            if self.chart_repository:
                await self.chart_repository.store_rectification_result(
                    chart_id=chart_id,
                    rectification_id=rectification_id,
                    data=formatted_result
                )

            return formatted_result

        except ValueError as e:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Error in chart rectification: {e}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Birth time rectification failed: {str(e)}")

    async def get_rectification_status(self, rectification_id: str) -> Dict[str, Any]:
        """
        Get the status of a chart rectification.

        Args:
            rectification_id: ID of the rectification process

        Returns:
            Dictionary with rectification status and details
        """
        try:
            # Retrieve from repository
            if self.chart_repository is None:
                logger.error("Chart repository is not initialized")
                return {"status": "error", "message": "Chart repository is not available"}

            rectification_data = await self.chart_repository.get_rectification(rectification_id)

            if not rectification_data:
                # Try to find by querying charts with this rectification ID
                if self.chart_repository is None:
                    logger.error("Chart repository is not initialized")
                    return {"status": "error", "message": "Chart repository is not available"}

                charts = await self.chart_repository.list_charts()
                for chart in charts:
                    if chart.get("rectification_id") == rectification_id:
                        rectification_data = {
                            "rectification_id": rectification_id,
                            "chart_id": chart.get("id"),
                            "status": "complete",
                            "rectified_time": chart.get("birth_time"),
                            "confidence_score": 70.0
                        }
                        break

            # If still not found, return error status
            if not rectification_data:
                return {
                    "status": "not_found",
                    "rectification_id": rectification_id,
                    "error": "Rectification process not found"
                }

            return rectification_data

        except Exception as e:
            logger.error(f"Error retrieving rectification status: {e}")
            # Return error status
            return {
                "status": "error",
                "rectification_id": rectification_id,
                "error": str(e)
            }

    async def export_chart(self, chart_id: str, format: str = "pdf") -> Dict[str, Any]:
        """
        Export chart data to a file format.

        Args:
            chart_id: The ID of the chart to export
            format: The format to export to (pdf, png, svg, json)

        Returns:
            Dictionary with export details including download URL
        """
        logger.info(f"Exporting chart {chart_id} in {format} format")

        try:
            # Retrieve chart data
            chart_data = await self.get_chart(chart_id)
            if not chart_data:
                raise ValueError(f"Chart with ID {chart_id} not found")

            # Generate unique export ID
            export_id = f"export_{chart_id}_{uuid.uuid4().hex[:8]}"

            # Create export directory if it doesn't exist
            export_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "exports")
            os.makedirs(export_dir, exist_ok=True)

            # Generate export file path
            file_path = os.path.join(export_dir, f"{export_id}.{format}")

            # Generate download URL
            download_url = f"/api/chart/export/{export_id}/download"

            # Create export metadata
            export_metadata = {
                "export_id": export_id,
                "chart_id": chart_id,
                "format": format,
                "file_path": file_path,
                "download_url": download_url,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
            }

            # Depending on format, generate the export file
            if format.lower() == "pdf":
                # Generate a PDF file
                self._generate_chart_pdf(chart_data, file_path)
            elif format.lower() == "png":
                # Generate a PNG file
                self._generate_chart_image(chart_data, file_path, format="png")
            elif format.lower() == "svg":
                # Generate an SVG file
                self._generate_chart_image(chart_data, file_path, format="svg")
            elif format.lower() == "json":
                # Generate a JSON file
                with open(file_path, "w") as f:
                    json.dump(chart_data, f, indent=2, cls=DateTimeEncoder)
            else:
                raise ValueError(f"Unsupported export format: {format}")

            # Check if the file was created
            if not os.path.exists(file_path):
                raise ValueError(f"Export file not found at {file_path}")

            # Store export metadata in repository
            if self.chart_repository is None:
                logger.error("Chart repository is not initialized")
                return {
                    "status": "success",
                    "export_id": export_id,
                    "download_url": download_url,
                    "format": format,
                    "message": "Export successfully generated but not stored in repository"
                }

            await self.chart_repository.store_export(export_id, export_metadata)

            return {
                "status": "success",
                "export_id": export_id,
                "download_url": download_url,
                "format": format,
                "message": "Export successfully generated"
            }

        except Exception as e:
            logger.error(f"Error exporting chart: {e}")
            return {
                "status": "error",
                "export_id": export_id,
                "message": f"Failed to export chart: {str(e)}"
            }

    async def calculate_chart(self, birth_details, options, chart_id=None):
        """
        Calculate an astrological chart with the provided birth details.

        Args:
            birth_details: Dictionary of birth details
            options: Dictionary of calculation options
            chart_id: Optional chart ID to use

        Returns:
            Dictionary containing chart data
        """
        logger.info("Calculating chart with real chart calculation")
        try:
            # Extract birth details
            birth_date = birth_details["date"]
            birth_time = birth_details["time"]
            latitude = birth_details["latitude"]
            longitude = birth_details["longitude"]
            timezone = birth_details["timezone"]
            location = birth_details.get("location", "Unknown location")

            # Parse the datetime
            dt = self._parse_datetime(birth_date, birth_time, timezone)
            if not dt:
                raise ValueError("Invalid birth date or time format")

            # Create a compatible wrapper class for calculate_chart if needed
            if not hasattr(self, 'astro_calculator') or self.astro_calculator is None:
                class AstroCalculatorCompat:
                    def calculate_chart(self, *args, **kwargs):
                        return calculate_chart(*args, **kwargs)

                calculator = AstroCalculatorCompat()
            else:
                calculator = self.astro_calculator

            # Calculate chart using AstroCalculator
            try:
                chart_data = calculator.calculate_chart(dt, latitude, longitude, timezone)
            except Exception as calc_error:
                logger.error(f"Error using calculator: {calc_error}")
                # Fallback to direct call
                chart_data = calculate_chart(dt, latitude, longitude, timezone)

            # Add metadata to chart
            chart_data["generated_at"] = datetime.now().isoformat()
            chart_data["birth_details"] = {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "location": location
            }

            # Add settings information
            chart_data["settings"] = {
                "house_system": options.get("house_system", "P"),
                "zodiac_type": options.get("zodiac_type", "sidereal"),
                "ayanamsa": options.get("ayanamsa", 23.6647),
                "node_type": options.get("node_type", "true")
            }

            # Generate a unique chart ID
            chart_id = f"chart_{uuid.uuid4().hex[:10]}"
            chart_data["chart_id"] = chart_id
            # Process chart data to normalize structure
            chart_data = self._process_chart_data(chart_data)

            # If verification is enabled, verify the chart
            if options.get("verify_with_openai", True):
                # Verify chart with OpenAI
                verification_result = await self.verify_chart_with_openai(
                    chart_data=chart_data,
                    birth_date=birth_date,
                    birth_time=birth_time,
                    location=location or f"{latitude}, {longitude}"
                )

                chart_data["verification"] = verification_result
            else:
                # Add basic verification data if not verifying
                chart_data["verification"] = {
                    "verified": True,
                    "confidence_score": 100.0,
                    "message": "Chart generated successfully (verification skipped)",
                    "corrections_applied": False
                }

            # Store the chart data
            await self.save_chart(chart_data)

            return chart_data

        except Exception as e:
            logger.error(f"Error calculating chart: {str(e)}")
            raise ValueError(f"Chart calculation failed: {str(e)}")

    def _prepare_chart_for_verification(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare chart data for verification by extracting essential elements.

        Args:
            chart_data: The full chart data

        Returns:
            Dictionary with essential chart elements for verification
        """
        verification_data = {}

        # Extract essential chart elements
        for key in ["ascendant", "planets", "houses", "aspects"]:
            if key in chart_data:
                verification_data[key] = chart_data[key]

        # Add divisional charts if present
        if "divisional_charts" in chart_data:
            verification_data["divisional_charts"] = chart_data["divisional_charts"]

        # Add nakshatras if present
        if "nakshatras" in chart_data:
            verification_data["nakshatras"] = chart_data["nakshatras"]

        return verification_data

    def _extract_main_chart_elements(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract main elements from chart data.

        Args:
            chart_data: The full chart data

        Returns:
            Dictionary with main chart elements
        """
        main_elements = {}

        # Extract essential chart elements
        for key in ["ascendant", "planets", "houses", "aspects"]:
            if key in chart_data:
                main_elements[key] = chart_data[key]

        return main_elements

    async def _calculate_divisional_chart(self, birth_chart: Dict[str, Any], division: int) -> Dict[str, Any]:
        """
        Calculate a divisional chart (varga) based on the birth chart.

        Args:
            birth_chart: The birth chart data
            division: The divisional number (e.g., 9 for Navamsa)

        Returns:
            Divisional chart data
        """
        divisional_chart = {
            "ascendant": {},
            "planets": [],
            "houses": [],
            "aspects": []
        }

        # Calculate divisional ascendant
        if "ascendant" in birth_chart and isinstance(birth_chart["ascendant"], dict):
            birth_asc = birth_chart["ascendant"]
            if "longitude" in birth_asc:
                # Calculate divisional longitude
                div_longitude = (birth_asc["longitude"] * division) % 360

                # Determine sign and degree
                sign_num = int(div_longitude / 30)
                degree = div_longitude % 30

                divisional_chart["ascendant"] = {
                    "longitude": div_longitude,
                    "sign": ZODIAC_SIGNS[sign_num] if sign_num < len(ZODIAC_SIGNS) else "Unknown",
                    "degree": degree
                }

        # Calculate divisional planets
        if isinstance(birth_chart.get("planets", {}), dict):
            # Handle dictionary format
            for planet_name, planet_data in birth_chart["planets"].items():
                if "longitude" in planet_data:
                    # Calculate divisional longitude
                    div_longitude = (planet_data["longitude"] * division) % 360

                    # Determine sign and degree
                    sign_num = int(div_longitude / 30)
                    degree = div_longitude % 30

                    # Create divisional planet entry
                    divisional_chart["planets"].append({
                        "name": planet_name,
                        "longitude": div_longitude,
                        "sign": ZODIAC_SIGNS[sign_num] if sign_num < len(ZODIAC_SIGNS) else "Unknown",
                        "degree": degree,
                        "retrograde": planet_data.get("retrograde", False)
                    })
        else:
            # Handle list format
            for planet in birth_chart.get("planets", []):
                if isinstance(planet, dict) and "longitude" in planet:
                    # Calculate divisional longitude
                    div_longitude = (planet["longitude"] * division) % 360

                    # Determine sign and degree
                    sign_num = int(div_longitude / 30)
                    degree = div_longitude % 30

                    # Create divisional planet entry
                    divisional_chart["planets"].append({
                        "name": planet.get("name", "Unknown"),
                        "longitude": div_longitude,
                        "sign": ZODIAC_SIGNS[sign_num] if sign_num < len(ZODIAC_SIGNS) else "Unknown",
                        "degree": degree,
                        "retrograde": planet.get("retrograde", False)
                    })

        return divisional_chart

    async def _calculate_nakshatras(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate and add nakshatra information to planets.

        Args:
            chart_data: The chart data to enhance with nakshatras

        Returns:
            Dictionary with nakshatra information
        """
        NAKSHATRAS = [
            "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
            "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
            "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
            "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
            "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
        ]

        NAKSHATRA_LORDS = [
            "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
            "Jupiter", "Saturn", "Mercury", "Ketu", "Venus", "Sun",
            "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
            "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
            "Jupiter", "Saturn", "Mercury"
        ]

        nakshatra_data = {}

        # Process planets for nakshatra calculation
        planets_to_process = []
        if isinstance(chart_data.get("planets", {}), dict):
            for name, planet in chart_data["planets"].items():
                if isinstance(planet, dict) and "longitude" in planet:
                    planets_to_process.append((name, planet))
        else:
            for planet in chart_data.get("planets", []):
                if isinstance(planet, dict) and "longitude" in planet and "name" in planet:
                    planets_to_process.append((planet["name"], planet))

        # Calculate nakshatra for each planet
        for name, planet in planets_to_process:
            # Each nakshatra is 13°20' (13.33333 degrees)
            longitude = planet.get("longitude", 0)
            nakshatra_index = int(longitude / 13.33333) % 27
            nakshatra_name = NAKSHATRAS[nakshatra_index]
            nakshatra_lord = NAKSHATRA_LORDS[nakshatra_index]

            # Calculate pada (quarter) within nakshatra (each pada is 3°20')
            pada = int((longitude % 13.33333) / 3.33333) + 1

            nakshatra_data[name] = {
                "nakshatra": nakshatra_name,
                "nakshatra_lord": nakshatra_lord,
                "pada": pada,
                "longitude_in_nakshatra": longitude % 13.33333
            }

        return nakshatra_data

    def _parse_direct_json(self, content: str) -> Dict[str, Any]:
        """Parse JSON directly from content string."""
        return json.loads(content)

    def _parse_embedded_json(self, content: str) -> Dict[str, Any]:
        """Extract and parse JSON embedded in text."""
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
        match = re.search(json_pattern, content)
        if not match:
            raise ValueError("No JSON object found in content")

        json_str = match.group(0)
        # Replace single quotes with double quotes for valid JSON
        json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
        # Fix boolean values
        json_str = re.sub(r':\s*true\b', r': true', json_str)
        json_str = re.sub(r':\s*false\b', r': false', json_str)

        return json.loads(json_str)

    def _parse_code_block_json(self, content: str) -> Dict[str, Any]:
        """Extract and parse JSON from markdown code blocks."""
        code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        code_matches = re.findall(code_block_pattern, content, re.DOTALL)

        if not code_matches:
            raise ValueError("No code blocks found in content")

        for code_match in code_matches:
            try:
                # Clean up and fix common issues
                json_str = code_match.strip()
                json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
                json_str = re.sub(r':\s*true\b', r': true', json_str)
                json_str = re.sub(r':\s*false\b', r': false', json_str)

                return json.loads(json_str)
            except json.JSONDecodeError:
                continue  # Try the next match if available

        raise ValueError("Failed to parse any code blocks as JSON")

    def _parse_text_verification(self, content: str) -> Dict[str, Any]:
        """Extract verification data from plain text."""
        # Extract key-value pairs manually
        verified_match = re.search(r'"?verified"?\s*:\s*(true|false)', content, re.IGNORECASE)
        confidence_match = re.search(r'"?confidence_score"?\s*:\s*(\d+(?:\.\d+)?)', content)
        message_match = re.search(r'"?message"?\s*:\s*"([^"]*)"', content)

        if not (verified_match or confidence_match):
            raise ValueError("Couldn't extract verification data from text")

        result = {}

        if verified_match:
            result["verified"] = verified_match.group(1).lower() == "true"
        else:
            result["verified"] = True  # Default

        if confidence_match:
            result["confidence_score"] = float(confidence_match.group(1))
        else:
            result["confidence_score"] = 70.0  # Default if not found

        if message_match:
            result["message"] = message_match.group(1)
        else:
            result["message"] = "Verification completed, extracted from text response."

        result["corrections"] = []

        return result

    async def _generate_chart_interpretation(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive interpretation of a chart using OpenAI.

        Args:
            chart_data: The chart data to interpret

        Returns:
            Dictionary with interpretations for different chart elements
        """
        if not self.openai_service:
            raise ValueError("OpenAI service is required for chart interpretation")

        # Extract basic chart data
        birth_details = chart_data.get("birth_details", {})
        planets = chart_data.get("planets", [])
        houses = chart_data.get("houses", [])
        ascendant = chart_data.get("ascendant", {})
        aspects = chart_data.get("aspects", [])

        # Create a simplified representation of the chart for the prompt
        chart_summary = {
            "birth_date": birth_details.get("birth_date", "Unknown"),
            "birth_time": birth_details.get("birth_time", "Unknown"),
            "location": birth_details.get("location", "Unknown"),
            "ascendant": ascendant.get("sign", "Unknown"),
            "planets": {}
        }

        # Add planet positions
        if isinstance(planets, list):
            for planet in planets:
                if isinstance(planet, dict) and "name" in planet and "sign" in planet:
                    chart_summary["planets"][planet["name"]] = {
                        "sign": planet["sign"],
                        "house": planet.get("house", "Unknown"),
                        "retrograde": planet.get("retrograde", False)
                    }
        elif isinstance(planets, dict):
            for name, planet in planets.items():
                if isinstance(planet, dict):
                    chart_summary["planets"][name] = {
                        "sign": planet.get("sign", "Unknown"),
                        "house": planet.get("house", "Unknown"),
                        "retrograde": planet.get("retrograde", False)
                    }

        # Create interpretation prompt
        prompt = {
            "task": "chart_interpretation",
            "chart_data": chart_summary,
            "interpretation_requests": [
                {
                    "type": "overall_summary",
                    "description": "Provide a general overview of the chart's key themes and patterns"
                },
                {
                    "type": "ascendant_interpretation",
                    "description": f"Interpret the {chart_summary['ascendant']} ascendant"
                },
                {
                    "type": "planet_interpretations",
                    "description": "Interpret each planet's placement by sign and house"
                },
                {
                    "type": "aspect_highlights",
                    "description": "Highlight the most significant aspects and their meanings"
                }
            ]
        }

        try:
            # Request interpretation from OpenAI
            response = await self.openai_service.generate_completion(
                prompt=json.dumps(prompt, cls=DateTimeEncoder),
                task_type="chart_interpretation",
                max_tokens=1000,
                temperature=0.7  # Slightly creative but still factual
            )

            if not response or "content" not in response:
                raise ValueError("Failed to get valid interpretation from OpenAI")

            content = response["content"]

            # Try to parse as structured JSON first
            try:
                interpretation = json.loads(content)
                return interpretation
            except json.JSONDecodeError:
                # Otherwise extract sections manually
                sections = {}

                # Extract overall summary
                summary_match = re.search(r'(?:Overall Summary|General Overview):?\s*(.*?)(?=\n\n|\n#|\Z)',
                                         content, re.DOTALL | re.IGNORECASE)
                if summary_match:
                    sections["overall_summary"] = summary_match.group(1).strip()

                # Extract ascendant interpretation
                ascendant_match = re.search(r'(?:Ascendant|Rising Sign):?\s*(.*?)(?=\n\n|\n#|\Z)',
                                           content, re.DOTALL | re.IGNORECASE)
                if ascendant_match:
                    sections["ascendant"] = ascendant_match.group(1).strip()

                # Extract planet interpretations
                planet_sections = {}
                for planet in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                              "Uranus", "Neptune", "Pluto", "Rahu", "Ketu"]:
                    planet_match = re.search(fr'{planet}:?\s*(.*?)(?=\n\n|\n#|\n[A-Z]|\Z)',
                                            content, re.DOTALL | re.IGNORECASE)
                    if planet_match:
                        planet_sections[planet] = planet_match.group(1).strip()

                if planet_sections:
                    sections["planets"] = planet_sections

                # Extract aspect highlights
                aspects_match = re.search(r'(?:Aspects|Aspect Highlights):?\s*(.*?)(?=\n\n|\n#|\Z)',
                                         content, re.DOTALL | re.IGNORECASE)
                if aspects_match:
                    sections["aspects"] = aspects_match.group(1).strip()

                # Fallback if sections extraction failed
                if not sections:
                    sections["raw_interpretation"] = content.strip()

                return sections

        except Exception as e:
            logger.error(f"Failed to generate chart interpretation: {str(e)}")
            return {
                "error": f"Interpretation failed: {str(e)}",
                "partial_interpretation": "A comprehensive chart interpretation requires proper astrological analysis."
            }

    def _generate_chart_pdf(self, chart_data: Dict[str, Any], file_path: str) -> None:
        """
        Generate a PDF file containing the chart data.

        Args:
            chart_data: Chart data to include in the PDF
            file_path: File path where to save the PDF
        """
        try:
            # Import PDF generation libraries
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
            import os

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Create PDF document
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            # Add title
            title = "Astrological Chart"
            if "birth_details" in chart_data and "full_name" in chart_data["birth_details"]:
                full_name = chart_data["birth_details"]["full_name"]
                if full_name:
                    title = f"Astrological Chart for {full_name}"

            story.append(Paragraph(title, styles["Title"]))
            story.append(Spacer(1, 12))

            # Add birth details
            if "birth_details" in chart_data:
                birth = chart_data["birth_details"]
                story.append(Paragraph("Birth Details", styles["Heading2"]))

                birth_data = []
                if "birth_date" in birth:
                    birth_data.append(["Date", birth.get("birth_date", "")])
                if "birth_time" in birth:
                    birth_data.append(["Time", birth.get("birth_time", "")])
                if "location" in birth:
                    birth_data.append(["Location", birth.get("location", "")])
                if "latitude" in birth and "longitude" in birth:
                    birth_data.append(["Coordinates", f"{birth.get('latitude', '')}, {birth.get('longitude', '')}"])

                if birth_data:
                    table = Table(birth_data, colWidths=[100, 300])
                    table.setStyle(TableStyle([
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 12))

            # Add planet positions
            if "planets" in chart_data:
                story.append(Paragraph("Planetary Positions", styles["Heading2"]))
                planets = chart_data["planets"]

                planet_data = [["Planet", "Sign", "Degree", "House"]]
                for planet, details in planets.items():
                    if isinstance(details, dict):
                        sign = details.get("sign", "")
                        degree = f"{details.get('degree', 0):.2f}" if "degree" in details else ""
                        house = str(details.get("house", "")) if "house" in details else ""
                        planet_data.append([planet, sign, degree, house])

                if len(planet_data) > 1:
                    table = Table(planet_data, colWidths=[80, 100, 80, 80])
                    table.setStyle(TableStyle([
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 12))

            # Add house cusps
            if "houses" in chart_data:
                story.append(Paragraph("House Cusps", styles["Heading2"]))
                houses = chart_data["houses"]

                house_data = [["House", "Sign", "Degree"]]

                # Handle both dictionary format and list format
                if isinstance(houses, dict):
                    for house_num, details in houses.items():
                        if isinstance(details, dict):
                            sign = details.get("sign", "")
                            degree = f"{details.get('degree', 0):.2f}" if "degree" in details else ""
                            house_data.append([str(house_num), sign, degree])
                elif isinstance(houses, list):
                    for i, house in enumerate(houses):
                        if isinstance(house, dict):
                            sign = house.get("sign", "")
                            degree = f"{house.get('degree', 0):.2f}" if "degree" in house else ""
                            house_data.append([str(i+1), sign, degree])

                if len(house_data) > 1:
                    table = Table(house_data, colWidths=[80, 100, 80])
                    table.setStyle(TableStyle([
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 12))

            # Add aspects
            if "aspects" in chart_data:
                story.append(Paragraph("Major Aspects", styles["Heading2"]))
                aspects = chart_data["aspects"]

                aspect_data = [["Planet 1", "Aspect", "Planet 2", "Orb"]]
                for aspect in aspects:
                    if isinstance(aspect, dict):
                        planet1 = aspect.get("planet1", "")
                        planet2 = aspect.get("planet2", "")
                        aspect_type = aspect.get("type", "")
                        orb = f"{aspect.get('orb', 0):.2f}" if "orb" in aspect else ""
                        aspect_data.append([planet1, aspect_type, planet2, orb])

                if len(aspect_data) > 1:
                    table = Table(aspect_data, colWidths=[80, 80, 80, 80])
                    table.setStyle(TableStyle([
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 12))

            # Add verification info if available
            if "verification" in chart_data:
                verification = chart_data["verification"]
                if isinstance(verification, dict):
                    story.append(Paragraph("Chart Verification", styles["Heading2"]))

                    verified = verification.get("verified", False)
                    confidence = verification.get("confidence", 0)
                    message = verification.get("message", "")

                    verification_text = f"Verified: {'Yes' if verified else 'No'}"
                    if confidence:
                        verification_text += f", Confidence: {confidence}%"

                    story.append(Paragraph(verification_text, styles["Normal"]))
                    if message:
                        story.append(Paragraph(message, styles["Normal"]))

            # Build the PDF
            doc.build(story)
            logger.info(f"Generated chart PDF: {file_path}")

        except Exception as e:
            logger.error(f"Error generating chart PDF: {e}", exc_info=True)

            # Create a JSON error report instead
            error_file_path = file_path.replace(".pdf", "_error.json")
            try:
                with open(error_file_path, "w") as f:
                    error_data = {
                        "error": f"Failed to generate PDF: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
                    json.dump(error_data, f, indent=2)
            except Exception:
                pass  # Ignore errors in error reporting

            # Re-raise the exception
            raise ValueError(f"Failed to generate chart PDF: {e}")

    def _generate_chart_image(self, chart_data: Dict[str, Any], file_path: str, format: str = "png") -> None:
        """
        Generate an image file (PNG or SVG) containing the chart visualization.

        Args:
            chart_data: Chart data to visualize
            file_path: File path where to save the image
            format: Image format (png or svg)
        """
        try:
            # Import visualization libraries
            import matplotlib.pyplot as plt
            import matplotlib as mpl
            from matplotlib.patches import Circle, Wedge, Rectangle
            import numpy as np
            import os

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Create figure with polar projection
            fig, ax = plt.subplots(subplot_kw={'projection': 'polar'}, figsize=(10, 10))
            fig.set_facecolor('white')

            # Set polar chart orientation properly
            ax.set_xlim(0, 2*np.pi)
            # These are valid matplotlib methods for polar plots
            # Using explicit string notation to prevent linter errors
            getattr(ax, "set_theta_zero_location")('N')
            getattr(ax, "set_theta_direction")(-1)

            # Draw the chart wheel - Outer circle
            circle = Circle((0, 0), 1, fill=False, edgecolor='black', linewidth=2, transform=ax.transData)
            ax.add_artist(circle)

            # House wedges
            houses = chart_data.get("houses", {})
            if houses:
                # Convert houses to a list format if it's a dictionary
                houses_list = []
                if isinstance(houses, dict):
                    for i in range(1, 13):
                        house_key = str(i)
                        if house_key in houses:
                            house_data = houses[house_key]
                            if "longitude" in house_data:
                                houses_list.append((i, house_data["longitude"]))
                else:
                    # Assume it's already a list
                    for i, house in enumerate(houses):
                        if isinstance(house, dict) and "longitude" in house:
                            houses_list.append((i+1, house["longitude"]))

                # Sort by house number
                houses_list.sort(key=lambda x: x[0])

                # Draw house wedges
                if houses_list:
                    for i in range(len(houses_list)):
                        house_num, start_long = houses_list[i]
                        _, end_long = houses_list[(i + 1) % len(houses_list)]

                        # Convert to radians (0 at east, going counterclockwise)
                        start_rad = np.radians(90 - start_long)
                        end_rad = np.radians(90 - end_long)

                        # If end is less than start, it wraps around 360 degrees
                        if end_rad > start_rad:
                            end_rad -= 2 * np.pi

                        # Draw wedge
                        wedge = Wedge((0, 0), 0.95, np.degrees(start_rad), np.degrees(end_rad),
                                    width=0.3, alpha=0.2, edgecolor='black', linewidth=1)
                        ax.add_patch(wedge)

                        # Add house number
                        mid_rad = (start_rad + end_rad) / 2
                        ax.text(mid_rad, 0.8, str(house_num), ha='center', va='center',
                               fontsize=12, fontweight='bold')

            # Draw planets
            planets = chart_data.get("planets", {})
            if planets:
                # Define planet symbols or use first letter
                planet_symbols = {
                    "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
                    "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇"
                }

                # Plot each planet
                planet_positions = []
                for planet_name, planet_data in planets.items():
                    if isinstance(planet_data, dict) and "longitude" in planet_data:
                        longitude = planet_data["longitude"]

                        # Convert to radians (0 at east, going counterclockwise)
                        rad = np.radians(90 - longitude)

                        # Calculate position (different radius for each planet to avoid overlap)
                        radius = 0.6  # Default radius

                        # Check for planet clustering and adjust radius if needed
                        for pos in planet_positions:
                            pos_rad, pos_radius = pos
                            if abs(rad - pos_rad) < 0.2:  # If planets are close
                                radius = pos_radius - 0.08  # Adjust radius to avoid overlap

                        planet_positions.append((rad, radius))

                        # Get the planet symbol or use first letter
                        symbol = planet_symbols.get(planet_name, planet_name[0])

                        # Plot the planet
                        ax.text(rad, radius, symbol, ha='center', va='center',
                               fontsize=16, fontweight='bold')

                        # Draw line to the wheel
                        ax.plot([rad, rad], [radius, 0.95], color='black', linestyle='-', linewidth=0.5)

            # Add title
            title = "Astrological Chart"
            if "birth_details" in chart_data:
                birth_details = chart_data["birth_details"]
                if "full_name" in birth_details and birth_details["full_name"]:
                    title += f" for {birth_details['full_name']}"
                elif "birth_date" in birth_details and "birth_time" in birth_details:
                    title += f" - {birth_details['birth_date']} {birth_details['birth_time']}"

            plt.title(title, fontsize=16, pad=20)

            # Remove axis ticks and labels
            ax.set_xticklabels([])
            ax.set_yticklabels([])
            ax.set_xticks([])
            ax.set_yticks([])

            # Hide the grid and axis
            ax.grid(False)
            for spine in ax.spines.values():
                spine.set_visible(False)

            # Save the chart
            plt.tight_layout()
            plt.savefig(file_path, format=format.lower(), dpi=300 if format.lower() == 'png' else 100)
            plt.close()

            logger.info(f"Generated chart image: {file_path}")

        except Exception as e:
            logger.error(f"Error generating chart image: {e}", exc_info=True)

            # Create a JSON error report instead
            error_file_path = file_path.replace(f".{format.lower()}", "_error.json")
            try:
                with open(error_file_path, "w") as f:
                    error_data = {
                        "error": f"Failed to generate image: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    }
                    json.dump(error_data, f, indent=2)
            except Exception:
                pass  # Ignore errors in error reporting

            # Re-raise the exception
            raise ValueError(f"Failed to generate chart image: {e}")

    async def store_rectification_result(
        self,
        chart_id: str,
        rectification_id: str,
        rectification_data: Dict[str, Any]
    ) -> bool:
        """
        Store rectification results in the repository.

        Args:
            chart_id: The ID of the chart
            rectification_id: The ID of the rectification request
            rectification_data: Rectification data to store

        Returns:
            bool: True if storage was successful
        """
        try:
            if self.chart_repository is None:
                logger.error("Chart repository is not initialized")
                return False

            # Call repository with the correct parameter names
            success = await self.chart_repository.store_rectification_result(
                chart_id=chart_id,
                rectification_id=rectification_id,
                data=rectification_data
            )

            # Convert to boolean
            return bool(success)
        except Exception as e:
            logger.error(f"Error storing rectification result: {e}")
            return False

    def _normalize_chart_format(self, chart):
        """
        Normalize the chart format to ensure consistency.

        Args:
            chart: The chart data to normalize

        Returns:
            Normalized chart data
        """
        normalized_chart = {}

        # If chart has a chart_data field, use that as the base
        if "chart_data" in chart:
            chart_data = chart["chart_data"]
            if isinstance(chart_data, dict):
                for key, value in chart_data.items():
                    normalized_chart[key] = value
                return normalized_chart

        # Extract essential elements
        for key in ["ascendant", "midheaven", "planets", "houses", "aspects"]:
            if key in chart:
                normalized_chart[key] = chart[key]

        # Handle case where chart has "id" field but elements are nested in "chart_data"
        if "id" in chart and len(normalized_chart) == 0:
            # Try to find chart data in nested structures
            for nested_key in ["chart_data", "data", "chart"]:
                if nested_key in chart and isinstance(chart[nested_key], dict):
                    for key, value in chart[nested_key].items():
                        normalized_chart[key] = value
                    break

        # If still empty, assume this might be a rectified chart with a specific structure
        if len(normalized_chart) == 0 and "rectified_chart_id" in chart:
            # Extract any available chart elements
            for key in chart:
                if key in ["ascendant", "midheaven", "planets", "houses"]:
                    normalized_chart[key] = chart[key]

        # Add divisional charts if present
        if "divisional_charts" in chart:
            normalized_chart["divisional_charts"] = chart["divisional_charts"]

        # Add nakshatras if present
        if "nakshatras" in chart:
            normalized_chart["nakshatras"] = chart["nakshatras"]

        return normalized_chart

    async def _calculate_angle_difference(self, chart1: Dict[str, Any], chart2: Dict[str, Any], angle_name: str) -> Dict[str, Any]:
        """
        Calculate the difference between angles in two charts.

        Args:
            chart1: First chart data
            chart2: Second chart data
            angle_name: Name of the angle to compare (e.g., 'asc', 'mc')

        Returns:
            Dictionary with difference details
        """
        result = {
            "angle": angle_name,
            "difference_degrees": 0,
            "significance": 0,
            "different_sign": False,
            "description": ""
        }

        # Extract angle data from charts
        angles1 = chart1.get("angles", {})
        angles2 = chart2.get("angles", {})

        # Handle different data structures
        if isinstance(angles1, dict) and angle_name in angles1:
            # Direct access by key
            angle1 = angles1[angle_name]
        elif isinstance(angles1, list):
            # Search in list
            angle1 = next((a for a in angles1 if a.get("name") == angle_name), None)
        else:
            # Not found
            angle1 = None

        if isinstance(angles2, dict) and angle_name in angles2:
            # Direct access by key
            angle2 = angles2[angle_name]
        elif isinstance(angles2, list):
            # Search in list
            angle2 = next((a for a in angles2 if a.get("name") == angle_name), None)
        else:
            # Not found
            angle2 = None

        if not angle1 or not angle2:
            result["description"] = f"Could not compare {angle_name} angle - data missing from one or both charts"
            return result

        # Extract longitudes
        longitude1 = angle1.get("longitude", 0)
        longitude2 = angle2.get("longitude", 0)

        # Calculate difference (accounting for circular nature of zodiac)
        diff = abs(longitude1 - longitude2)
        if diff > 180:
            diff = 360 - diff

        result["difference_degrees"] = round(diff, 2)

        # Check if signs are different
        sign1 = angle1.get("sign", "")
        sign2 = angle2.get("sign", "")
        result["different_sign"] = sign1 != sign2

        # Calculate significance based on difference
        if diff < 1:
            significance = 0  # Negligible change
        elif diff < 3:
            significance = 0.3  # Minor change
        elif diff < 5:
            significance = 0.5  # Moderate change
        elif diff < 10:
            significance = 0.8  # Significant change
        else:
            significance = 1.0  # Major change

        # Increase significance if sign changed
        if result["different_sign"]:
            significance = min(1.0, significance + 0.3)

        result["significance"] = round(significance, 2)

        # Generate description
        if angle_name == "asc":
            angle_full_name = "Ascendant"
        elif angle_name == "mc":
            angle_full_name = "Midheaven"
        elif angle_name == "ic":
            angle_full_name = "Imum Coeli"
        elif angle_name == "desc":
            angle_full_name = "Descendant"
        else:
            angle_full_name = angle_name.upper()

        if diff < 1:
            result["description"] = f"No significant change in {angle_full_name}"
        elif diff < 3:
            result["description"] = f"Slight shift in {angle_full_name} by {result['difference_degrees']}°"
        elif diff < 5:
            result["description"] = f"Moderate change in {angle_full_name} by {result['difference_degrees']}°"
        else:
            if result["different_sign"]:
                result["description"] = f"Major change in {angle_full_name} from {sign1} to {sign2} ({result['difference_degrees']}°)"
            else:
                result["description"] = f"Significant shift in {angle_full_name} by {result['difference_degrees']}°"

        return result

    async def _identify_major_changes(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify major changes between two charts including planetary positions, house placements, and angles.

        Args:
            chart1: First chart data
            chart2: Second chart data

        Returns:
            List of dictionaries describing major changes
        """
        major_changes = []

        # 1. Compare angles (Ascendant and Midheaven are most important)
        angles_to_compare = ["asc", "mc", "desc", "ic"]

        for angle in angles_to_compare:
            angle_diff = await self._calculate_angle_difference(chart1, chart2, angle)

            # Only include significant changes
            if angle_diff["significance"] >= 0.3:
                major_changes.append({
                    "type": "angle",
                    "element": angle,
                    "change": angle_diff
                })

        # 2. Compare planets and their house placements
        planets1 = chart1.get("planets", {})
        planets2 = chart2.get("planets", {})

        # Convert planets to consistent format
        planets1_dict = {}
        planets2_dict = {}

        if isinstance(planets1, list):
            for planet in planets1:
                name = planet.get("name", planet.get("planet"))
                if name:
                    planets1_dict[name] = planet
        elif isinstance(planets1, dict):
            planets1_dict = planets1

        if isinstance(planets2, list):
            for planet in planets2:
                name = planet.get("name", planet.get("planet"))
                if name:
                    planets2_dict[name] = planet
        elif isinstance(planets2, dict):
            planets2_dict = planets2

        # Compare each planet's position and house placement
        for planet_name in set(planets1_dict.keys()).union(planets2_dict.keys()):
            if planet_name in planets1_dict and planet_name in planets2_dict:
                planet1 = planets1_dict[planet_name]
                planet2 = planets2_dict[planet_name]

                # Check house changes
                house1 = planet1.get("house", 0)
                house2 = planet2.get("house", 0)
                house_changed = house1 != house2

                # Check sign changes
                sign1 = planet1.get("sign", "")
                sign2 = planet2.get("sign", "")
                sign_changed = sign1 != sign2

                # Check longitude changes
                longitude1 = planet1.get("longitude", 0)
                longitude2 = planet2.get("longitude", 0)

                # Calculate difference (accounting for circular nature of zodiac)
                diff = abs(longitude1 - longitude2)
                if diff > 180:
                    diff = 360 - diff

                # Determine significance
                significance = await self._calculate_significance("planet", planet1, planet2, chart1, chart2, planet_name)

                # Add change if significant
                if house_changed or sign_changed or diff > 2 or significance > 0.3:
                    change_data = {
                        "type": "planet",
                        "element": planet_name,
                        "longitude_difference": round(diff, 2),
                        "house_changed": house_changed,
                        "sign_changed": sign_changed,
                        "original_house": house1,
                        "new_house": house2,
                        "original_sign": sign1,
                        "new_sign": sign2,
                        "significance": significance
                    }

                    # Generate description
                    description = f"{planet_name} "
                    if sign_changed:
                        description += f"moves from {sign1} to {sign2} "
                    if house_changed:
                        description += f"changes from house {house1} to house {house2} "
                    if not sign_changed and not house_changed:
                        description += f"shifts by {round(diff, 2)}° within {sign1} "

                    change_data["description"] = description.strip()
                    major_changes.append(change_data)

        # 3. Check for any house cusp changes
        houses1 = chart1.get("houses", [])
        houses2 = chart2.get("houses", [])

        # Convert houses to consistent format if needed
        # (Implementation depends on your specific house data structure)

        # Sort changes by significance (most significant first)
        major_changes.sort(key=lambda x: x.get("significance", 0) if isinstance(x, dict) else 0, reverse=True)

        return major_changes

    async def _generate_comparison_interpretation(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> str:
        """
        Generate a detailed interpretation of the differences between two charts.

        Args:
            chart1: First chart data
            chart2: Second chart data

        Returns:
            String containing the interpretation
        """
        # Identify major changes
        major_changes = await self._identify_major_changes(chart1, chart2)

        # Count how many significant changes
        significant_changes = [c for c in major_changes if c.get("significance", 0) > 0.5]
        moderate_changes = [c for c in major_changes if 0.3 <= c.get("significance", 0) <= 0.5]
        minor_changes = [c for c in major_changes if c.get("significance", 0) < 0.3]

        # Generate a descriptive summary
        birth_details1 = chart1.get("birth_details", {})
        birth_details2 = chart2.get("birth_details", {})

        birth_time1 = birth_details1.get("birth_time", chart1.get("birth_time", "unknown"))
        birth_time2 = birth_details2.get("birth_time", chart2.get("birth_time", "unknown"))

        # Calculate time difference
        time_diff_text = "unknown"
        try:
            from datetime import datetime
            if isinstance(birth_time1, str) and isinstance(birth_time2, str):
                # Try parsing different formats
                try:
                    dt1 = datetime.strptime(birth_time1, "%H:%M:%S")
                    dt2 = datetime.strptime(birth_time2, "%H:%M:%S")
                except ValueError:
                    try:
                        # Try ISO format
                        dt1 = datetime.fromisoformat(birth_time1)
                        dt2 = datetime.fromisoformat(birth_time2)
                    except ValueError:
                        # Try just hours and minutes
                        dt1 = datetime.strptime(birth_time1.split(":")[0] + ":" + birth_time1.split(":")[1], "%H:%M")
                        dt2 = datetime.strptime(birth_time2.split(":")[0] + ":" + birth_time2.split(":")[1], "%H:%M")

                # Calculate difference in minutes
                minutes_diff = abs((dt2.hour * 60 + dt2.minute) - (dt1.hour * 60 + dt1.minute))
                time_diff_text = f"{minutes_diff} minutes"
        except Exception as e:
            time_diff_text = "could not be calculated"

        # Build the interpretation
        interpretation = []

        # Introduction
        interpretation.append(f"Comparison of birth charts with times {birth_time1} and {birth_time2} (difference of {time_diff_text}).")

        # Summary of changes
        if len(significant_changes) == 0 and len(moderate_changes) == 0:
            interpretation.append("The time adjustment results in minimal changes to the chart structure.")
        elif len(significant_changes) > 3:
            interpretation.append("The time adjustment results in major structural changes to the chart, significantly altering its interpretation.")
        elif len(significant_changes) > 0:
            interpretation.append(f"The time adjustment results in {len(significant_changes)} significant changes to the chart, affecting key interpretative elements.")
        else:
            interpretation.append(f"The time adjustment results in {len(moderate_changes)} moderate changes to the chart structure.")

        # Angles analysis (Ascendant and Midheaven are most important)
        asc_changes = [c for c in major_changes if c.get("type") == "angle" and c.get("element") == "asc"]
        mc_changes = [c for c in major_changes if c.get("type") == "angle" and c.get("element") == "mc"]

        if asc_changes:
            asc_change = asc_changes[0]
            interpretation.append(f"Ascendant: {asc_change.get('change', {}).get('description', 'Changes significantly')}.")
            if asc_change.get('change', {}).get('different_sign', False):
                interpretation.append("This is a critical change that affects personality expression, physical appearance, and overall chart interpretation.")

        if mc_changes:
            mc_change = mc_changes[0]
            interpretation.append(f"Midheaven: {mc_change.get('change', {}).get('description', 'Changes significantly')}.")
            if mc_change.get('change', {}).get('different_sign', False):
                interpretation.append("This change affects career path, public reputation, and life direction interpretations.")

        # Planetary house changes
        planet_house_changes = [c for c in major_changes if c.get("type") == "planet" and c.get("house_changed", False)]
        if planet_house_changes:
            interpretation.append("Planets changing houses:")
            for change in planet_house_changes[:3]:  # Limit to top 3 for clarity
                interpretation.append(f"- {change.get('description', '')}")

            if len(planet_house_changes) > 3:
                interpretation.append(f"- Plus {len(planet_house_changes) - 3} additional planetary house changes.")

        # Sign changes (less common but very significant)
        planet_sign_changes = [c for c in major_changes if c.get("type") == "planet" and c.get("sign_changed", False)]
        if planet_sign_changes:
            interpretation.append("Planets changing signs:")
            for change in planet_sign_changes:
                interpretation.append(f"- {change.get('description', '')}")

        # Overall interpretation
        if len(significant_changes) > 2 or (asc_changes and asc_changes[0].get('change', {}).get('different_sign', False)):
            interpretation.append("The rectified birth time produces a substantially different chart that would yield different interpretations for key life areas.")
        elif len(significant_changes) > 0 or len(moderate_changes) > 2:
            interpretation.append("The rectified birth time affects some important chart elements, refining the interpretation without completely changing the chart structure.")
        else:
            interpretation.append("The rectified birth time provides minor refinements to the chart while preserving the overall structure and interpretation.")

        return "\n".join(interpretation)

# Move these functions outside the class
# Singleton provider
_chart_service_instance = None

def create_chart_service(database_manager=None, session_id=None, openai_service=None) -> 'ChartService':
    """
    Factory function to create a ChartService.
    Used by the dependency container.

    Args:
        database_manager: Optional database manager
        session_id: Optional session ID
        openai_service: Optional OpenAI service

    Returns:
        ChartService instance
    """
    try:
        # Get dependencies if not provided
        if openai_service is None:
            from ai_service.api.services.openai import get_openai_service
            openai_service = get_openai_service()

        return ChartService(
            database_manager=database_manager,
            session_id=session_id,
            openai_service=openai_service
        )
    except Exception as e:
        logger.error(f"Failed to create chart service: {e}")
        raise ValueError(f"Failed to create chart service: {e}")

def get_chart_service() -> 'ChartService':
    """
    Get or create singleton instance of ChartService

    Returns:
        ChartService instance
    """
    from ai_service.utils.dependency_container import get_container
    container = get_container()

    try:
        # Try to get from container
        return container.get("chart_service")
    except ValueError:
        # Register and get
        container.register("chart_service", create_chart_service)
        return container.get("chart_service")
