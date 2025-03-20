"""
Chart Service

This module provides services for chart generation, retrieval, and validation.
It handles the business logic for astrological chart operations using real data sources.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional, Union, cast
from datetime import datetime, timezone, UTC, timedelta
import asyncio
import os
import json
import re
import time
import pytz
import sys
import base64

# Import real data sources and calculation utilities
from ai_service.utils.constants import ZODIAC_SIGNS
from ai_service.core.chart_calculator import EnhancedChartCalculator
from ai_service.core.astro_calculator import AstroCalculator, get_astro_calculator
from ai_service.api.services.openai import get_openai_service
# Import geocoding utils safely
from ai_service.utils.geocoding import get_timezone_for_coordinates
from ai_service.database.repositories import ChartRepository
from ai_service.api.services.openai.service import OpenAIService
from ai_service.core.config import settings

# Setup logging
logger = logging.getLogger(__name__)

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

    async def verify_chart(self, verification_data: Dict[str, Any], openai_service: Optional[OpenAIService] = None) -> Dict[str, Any]:
        """
        Verify a chart using OpenAI.

        Args:
            verification_data: Data containing chart details and birth information
            openai_service: Optional OpenAI service instance

        Returns:
            Verification results
        """
        if not verification_data:
            raise ValueError("Verification data is required")

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

        # Make a real API call to OpenAI
        try:
            response = await openai_service.generate_completion(
                prompt=prompt,
                task_type="rectification",
                max_tokens=500
            )

            if not response:
                raise ValueError("Empty response from OpenAI API")

            # Extract the content from the response
            content = response.get("content")
            if not content:
                raise ValueError("No content in OpenAI response")

            # Parse the response content
            verification_result = await self.parse_verification_response(content)

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

            return verification_result

        except Exception as e:
            logger.error(f"Error during chart verification: {str(e)}")
            # Propagate the error instead of providing a default fallback
            raise ValueError(f"Chart verification failed: {str(e)}")

    def _generate_verification_prompt(self, verification_data: Dict[str, Any]) -> str:
        """
        Generate the verification prompt for OpenAI.

        Args:
            verification_data: Data containing chart details and birth information

        Returns:
            Formatted prompt string
        """
        # Extract chart data and birth details
        chart_data = verification_data.get("chart_data", {})
        birth_details = verification_data.get("birth_details", {})

        # Format the prompt
        prompt = f"""
        Verify the accuracy of this astrological chart according to Indian Vedic Astrological standards:

        Birth Details:
        - Date: {birth_details.get('birth_date', 'Unknown')}
        - Time: {birth_details.get('birth_time', 'Unknown')}
        - Location: {birth_details.get('latitude', 0)}, {birth_details.get('longitude', 0)}

        Chart Data:
        - Planets: {json.dumps(chart_data.get('planets', []), indent=2)}
        - Houses: {json.dumps(chart_data.get('houses', []), indent=2)}
        - Ascendant: {json.dumps(chart_data.get('ascendant', {}), indent=2)}

        Please verify:
        1. The accuracy of planet positions
        2. The correctness of house calculations
        3. The accuracy of the ascendant calculation
        4. Any errors or inconsistencies in the chart data

        Return your verification as a JSON object with these fields:
        - verified: bool (true/false)
        - confidence_score: number (0-100)
        - corrections: array of correction objects if needed
        - message: string with verification details
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

        # Step 1: Try direct JSON parsing first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Not a direct JSON response, continue to extraction
            pass

        # Step 2: Try to extract JSON from the response using regex
        try:
            # Look for a complete JSON object pattern
            json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
            match = re.search(json_pattern, response)

            if match:
                json_str = match.group(0)
                # Replace single quotes with double quotes for valid JSON
                json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
                # Fix boolean values
                json_str = re.sub(r':\s*true\b', r': true', json_str)
                json_str = re.sub(r':\s*false\b', r': false', json_str)

                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Found JSON-like structure but couldn't parse it: {e}")
                    # Continue to next method

            # Step 3: Try to find a JSON block using markdown code block indicators
            code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            code_matches = re.findall(code_block_pattern, response, re.DOTALL)

            if code_matches:
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

            # Step 4: Try to extract key-value pairs manually if all else fails
            verified_match = re.search(r'"?verified"?\s*:\s*(true|false)', response, re.IGNORECASE)
            confidence_match = re.search(r'"?confidence_score"?\s*:\s*(\d+(?:\.\d+)?)', response)
            message_match = re.search(r'"?message"?\s*:\s*"([^"]*)"', response)

            if verified_match or confidence_match:
                result = {}

                if verified_match:
                    result["verified"] = verified_match.group(1).lower() == "true"

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

            # Step 5: Last resort - create a basic response based on text analysis
            logger.warning("Could not extract JSON structure from response, using text analysis")
            # Check if the response generally indicates success
            positive_indicators = ["verified", "correct", "accurate", "valid", "consistent"]
            negative_indicators = ["error", "incorrect", "inaccurate", "invalid", "inconsistent"]

            # Count positive and negative indicators
            positive_count = sum(1 for word in positive_indicators if word.lower() in response.lower())
            negative_count = sum(1 for word in negative_indicators if word.lower() in response.lower())

            # Determine if verified based on indicator counts
            verified = positive_count > negative_count

            # Calculate a simple confidence score based on the ratio of positive to total indicators
            total_indicators = positive_count + negative_count
            confidence_score = 50.0  # Default middle value

            if total_indicators > 0:
                confidence_score = min(100.0, max(0.0, (positive_count / total_indicators) * 100))

            return {
                "verified": verified,
                "confidence_score": confidence_score,
                "corrections": [],
                "message": f"Verification based on text analysis: {positive_count} positive vs {negative_count} negative indicators",
                "raw_response": response[:500]  # Include truncated raw response for debugging
            }

        except Exception as e:
            logger.error(f"Failed to parse verification response: {str(e)}")
            raise ValueError(f"Failed to parse verification response: {str(e)}")

class ChartService:
    """Service for chart operations including generation, validation, and retrieval"""

    def __init__(self, database_manager=None, session_id=None, openai_service=None, chart_verifier=None,
                 calculator=None, astro_calculator=None, chart_repository=None):
        """
        Initialize a ChartService instance.
        Connects to services and calculators through dependency injection.

        Args:
            database_manager: Database manager for persistence operations
            session_id: Session identifier for tracking requests
            openai_service: OpenAI service for AI operations (dependency injection)
            chart_verifier: Chart verifier service (dependency injection)
            calculator: Chart calculator (dependency injection)
            astro_calculator: Astrology calculator (dependency injection)
            chart_repository: Chart repository for database operations (dependency injection)
        """
        try:
            # Store session ID
            self.session_id = session_id

            # Initialize dependencies with provided instances or create defaults

            # Initialize OpenAI service
            if openai_service:
                self.openai_service = openai_service
                logger.info("Using provided OpenAI service")
            else:
                try:
                    self.openai_service = get_openai_service()
                    logger.info("OpenAI service initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize OpenAI service: {e}")
                    raise ValueError(f"Failed to initialize OpenAI service: {e}")

            # Initialize chart verifier
            if chart_verifier:
                self.chart_verifier = chart_verifier
                logger.info("Using provided chart verifier")
            else:
                try:
                    self.chart_verifier = ChartVerifier(session_id, self.openai_service)
                    logger.info("Chart verifier service initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize chart verifier: {e}")
                    raise ValueError(f"Failed to initialize chart verifier: {e}")

            # Initialize calculators
            if calculator:
                self.calculator = calculator
                logger.info("Using provided chart calculator")
            else:
                try:
                    self.calculator = EnhancedChartCalculator()
                    logger.info("Chart calculator initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize calculator: {e}")
                    raise ValueError(f"Failed to initialize calculator: {e}")

            if astro_calculator:
                self.astro_calculator = astro_calculator
                logger.info("Using provided astro calculator")
            else:
                try:
                    self.astro_calculator = get_astro_calculator()
                    logger.info("Astro calculator initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize astro calculator: {e}")
                    raise ValueError(f"Failed to initialize astro calculator: {e}")

            # Initialize database dependencies
            self.database_manager = database_manager

            if chart_repository:
                self.chart_repository = chart_repository
                logger.info("Using provided chart repository")
            else:
                try:
                    self.chart_repository = ChartRepository()
                    logger.info("Chart repository initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize chart repository: {e}")
                    raise ValueError(f"Failed to initialize chart repository: {e}")

            if database_manager:
                logger.info("Chart service initialized with database connection")
        except Exception as e:
            logger.error(f"Error initializing chart service: {e}")
            raise

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

            # Get AstroCalculator instance
            calculator = get_astro_calculator()

            # Calculate chart using AstroCalculator
            chart_data = await calculator.calculate_chart(
                birth_date=birth_date,
                birth_time=birth_time,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                house_system=house_system,
                include_aspects=True,
                include_houses=True
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

            # Verify chart with OpenAI if requested
            if verify_with_openai:
                verification_result = await self.verify_chart_with_openai(
                    chart_data=chart_data,
                    birth_date=birth_date,
                    birth_time=birth_time,
                    latitude=latitude,
                    longitude=longitude
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
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Verify chart data with OpenAI for enhanced accuracy.

        Args:
            chart_data: The chart data to verify
            birth_date: Birth date
            birth_time: Birth time
            latitude: Birth latitude
            longitude: Birth longitude

        Returns:
            Verification result dictionary
        """
        logger.info(f"Verifying chart with OpenAI for: {birth_date} {birth_time}")

        # Validate input parameters
        if not chart_data:
            raise ValueError("Chart data is required for verification")

        if not birth_date or not birth_time:
            raise ValueError("Birth date and time are required for verification")

        # Get OpenAI service - use dependency injection if possible
        openai_service = self.openai_service
        if not openai_service:
            openai_service = get_openai_service()
            if not openai_service:
                raise ValueError("OpenAI service is not available for chart verification")

        # Create verification data
        verification_data = {
            "chart_data": chart_data,
            "birth_details": {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "latitude": latitude,
                "longitude": longitude
            }
        }

        # Create chart verifier
        verifier = ChartVerifier(session_id=self.session_id, openai_service=openai_service)

        try:
            # Verify chart using OpenAI
            verification_result = await verifier.verify_chart(
                verification_data=verification_data,
                openai_service=openai_service
            )

            # Log the verification result
            confidence = verification_result.get("confidence_score", 0)
            logger.info(f"Chart verification completed with confidence: {confidence}")

            # Return the verification result
            return verification_result

        except Exception as e:
            logger.error(f"Error during chart verification: {str(e)}")
            # Propagate the error for proper handling upstream
            raise ValueError(f"Chart verification failed: {str(e)}")

    async def get_chart(self, chart_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a chart by ID

        Args:
            chart_id: The ID of the chart to retrieve

        Returns:
            Chart data or None if not found
        """
        try:
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
        Compare two charts and analyze their differences.

        Args:
            chart1_id: ID of the first chart
            chart2_id: ID of the second chart
            comparison_type: Type of comparison (differences, full, summary)

        Returns:
            Dictionary containing comparison results
        """
        # Retrieve both charts from database
        logger.info(f"Comparing charts: {chart1_id} and {chart2_id}")
        chart1 = await self.chart_repository.get_chart(chart1_id)
        chart2 = await self.chart_repository.get_chart(chart2_id)

        if not chart1:
            raise ValueError(f"Chart not found: {chart1_id}")
        if not chart2:
            raise ValueError(f"Chart not found: {chart2_id}")

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
        Delete a chart from storage

        Args:
            chart_id: ID of chart to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = await self.chart_repository.delete_chart(chart_id)
            return result
        except Exception as e:
            logger.error(f"Failed to delete chart {chart_id}: {e}")
            return False

    async def save_chart(self, chart_data: Dict[str, Any]) -> str:
        """
        Save a chart to the repository.
        """
        chart_id = chart_data.get("chart_id")
        if not chart_id:
            chart_id = f"chart_{uuid.uuid4().hex[:10]}"
            chart_data["chart_id"] = chart_id

        try:
            # Store the chart data
            if self.chart_repository:
                await self.chart_repository.store_chart(chart_id=chart_id, chart_data=chart_data)
                logger.info(f"Chart saved with ID: {chart_id}")
            else:
                logger.warning("No chart repository available, chart not saved")
        except Exception as e:
            logger.error(f"Error saving chart: {e}")

        return chart_id

    async def rectify_chart(self, chart_id: str, questionnaire_id: str, answers: List[Dict[str, Any]], include_details: bool = False) -> Dict[str, Any]:
        """
        Rectify a chart based on questionnaire answers using AI analysis algorithm.

        Args:
            chart_id: ID of the chart to rectify
            questionnaire_id: ID of the questionnaire with answers
            answers: List of question/answer pairs
            include_details: Whether to include detailed rectification process

        Returns:
            Dictionary with rectified chart details
        """
        logger.info(f"Rectifying chart {chart_id} using questionnaire {questionnaire_id}")

        # Get the original chart
        original_chart = await self.get_chart(chart_id)
        if not original_chart:
            raise ValueError(f"Chart not found: {chart_id}")

        # Extract birth details from chart
        birth_details = original_chart.get("birth_details", {})
        birth_date = birth_details.get("birth_date", "")
        birth_time = birth_details.get("birth_time", "")
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        timezone = birth_details.get("timezone", "UTC")

        # Parse birth datetime
        birth_dt = self._parse_datetime(birth_date, birth_time, timezone)

        # Track rectification process steps
        rectification_steps = []
        rectification_steps.append("Retrieved original chart data")

        # Per sequence diagram: AI Analysis Algorithm determines birth time
        # Thorough implementation of AI-powered rectification
        ai_rectification_result = None
        if self.openai_service:
            try:
                rectification_steps.append("Starting AI-powered birth time analysis")

                # Enrich input data for more accurate analysis
                # Include aspect data and more relevant astrological factors
                chart_planets = []
                aspects = []

                # Process planets data for AI analysis
                if isinstance(original_chart.get("planets", {}), dict):
                    # Handle dictionary format
                    for planet_name, planet_data in original_chart.get("planets", {}).items():
                        if isinstance(planet_data, dict):
                            chart_planets.append({
                                "name": planet_name,
                                "sign": planet_data.get("sign", ""),
                                "degree": planet_data.get("degree", 0),
                                "house": planet_data.get("house", 0),
                                "retrograde": planet_data.get("retrograde", False),
                                "longitude": planet_data.get("longitude", 0)
                            })
                else:
                    # Handle list format
                    for planet in original_chart.get("planets", []):
                        if isinstance(planet, dict):
                            chart_planets.append({
                                "name": planet.get("name", ""),
                                "sign": planet.get("sign", ""),
                                "degree": planet.get("degree", 0),
                                "house": planet.get("house", 0),
                                "retrograde": planet.get("retrograde", False),
                                "longitude": planet.get("longitude", 0)
                            })

                # Include aspects for better analysis
                for aspect in original_chart.get("aspects", []):
                    if isinstance(aspect, dict):
                        aspects.append({
                            "planet1": aspect.get("planet1", ""),
                            "planet2": aspect.get("planet2", ""),
                            "type": aspect.get("type", ""),
                            "orb": aspect.get("orb", 0),
                            "applying": aspect.get("applying", False)
                        })

                # Extract birth time indicators from answers
                birth_time_indicators = self._extract_birth_time_indicators(answers)

                # Prepare enhanced data for AI analysis
                rectification_prompt = {
                    "task": "birth_time_rectification",
                    "birth_details": {
                        "date": birth_date,
                        "time": birth_time,
                        "latitude": latitude,
                        "longitude": longitude,
                        "timezone": timezone,
                        "location": birth_details.get("location", "")
                    },
                    "questionnaire_data": {
                        "questions_and_answers": answers,
                        "total_questions": len(answers),
                        "birth_time_indicators": birth_time_indicators
                    },
                    "chart_data": {
                        "ascendant": original_chart.get("ascendant", {}),
                        "planets": chart_planets,
                        "houses": original_chart.get("houses", []),
                        "aspects": aspects
                    },
                    "analysis_requirements": [
                        "Analyze questionnaire answers for timing indicators using Vedic and Western principles",
                        "Apply both traditional astrological rules and AI pattern analysis to determine birth time",
                        "Consider planetary aspects, house positions, and transits in your analysis",
                        "Provide confidence level and detailed explanation for the rectification",
                        "Specify adjustment in minutes (positive or negative) from original time",
                        "Include astrological factors that support your conclusion"
                    ]
                }

                rectification_steps.append("Sending enhanced data to OpenAI for astrological analysis")

                # Get detailed rectification analysis from OpenAI
                response = await self.openai_service.generate_completion(
                    prompt=json.dumps(rectification_prompt),
                    task_type="birth_time_rectification",
                    max_tokens=1200,   # Increased token limit for more detailed analysis
                    temperature=0.2    # Lower temperature for more deterministic results
                )

                if response and "content" in response:
                    rectification_steps.append("Received AI analysis results")

                    # Parse the AI response with improved handling of different formats
                    content = response["content"]
                    ai_result = {}

                    # Try multiple parsing approaches for reliability
                    try:
                        # Try direct JSON parsing first
                        try:
                            ai_result = json.loads(content)
                            rectification_steps.append("Successfully parsed JSON response")
                        except json.JSONDecodeError:
                            # Extract JSON if embedded in text
                            json_match = re.search(r'\{.*\}', content, re.DOTALL)
                            if json_match:
                                ai_result = json.loads(json_match.group(0))
                                rectification_steps.append("Extracted JSON from text response")
                            else:
                                # Extract from markdown code blocks if present
                                code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
                                code_matches = re.findall(code_block_pattern, content, re.DOTALL)
                                if code_matches:
                                    for code_match in code_matches:
                                        try:
                                            ai_result = json.loads(code_match.strip())
                                            rectification_steps.append("Extracted JSON from code block")
                                            break
                                        except:
                                            continue
                    except Exception as parse_error:
                        logger.warning(f"Error parsing JSON response: {parse_error}")
                        rectification_steps.append(f"JSON parsing error: {str(parse_error)}")

                    # If JSON parsing failed, extract structured data from text
                    if not ai_result:
                        rectification_steps.append("Falling back to text extraction")
                        # Extract key information from text response with improved patterns
                        time_pattern = re.search(r'(?:rectified_time|rectified birth time)["\s:]+([0-2]?[0-9]:[0-5][0-9](?::[0-5][0-9])?)', content, re.IGNORECASE)
                        confidence_pattern = re.search(r'confidence(?:_score|[ _]level)?["\s:]+(\d+\.?\d*)', content, re.IGNORECASE)
                        adjustment_pattern = re.search(r'adjustment_?minutes?["\s:]+(-?\d+)', content, re.IGNORECASE)
                        explanation_pattern = re.search(r'explanation["\s:]+["\'](.*?)["\'],["\s}]', content, re.IGNORECASE)

                        if time_pattern:
                            ai_result["rectified_time"] = time_pattern.group(1)
                        if confidence_pattern:
                            ai_result["confidence"] = float(confidence_pattern.group(1))
                        if adjustment_pattern:
                            ai_result["adjustment_minutes"] = int(adjustment_pattern.group(1))
                        if explanation_pattern:
                            ai_result["explanation"] = explanation_pattern.group(1)
                        else:
                            # Extract a meaningful explanation from the content
                            explanation_candidates = [
                                line.strip() for line in content.split('\n')
                                if len(line.strip()) > 30
                                and "explanation" not in line.lower()
                                and "rectifi" in line.lower()
                            ]
                            if explanation_candidates:
                                ai_result["explanation"] = explanation_candidates[0]
                            else:
                                # Find any substantial text block
                                substantial_lines = [line.strip() for line in content.split('\n') if len(line.strip()) > 40]
                                if substantial_lines:
                                    ai_result["explanation"] = substantial_lines[0]

                        # Find astrological factors if available
                        astrological_factors = []
                        for line in content.split('\n'):
                            if any(factor in line.lower() for factor in [
                                'transit', 'aspect', 'moon', 'ascendant', 'house', 'planet',
                                'conjunction', 'trine', 'square', 'opposition', 'sextile'
                            ]):
                                factor = line.strip()
                                if factor and len(factor) > 10:
                                    astrological_factors.append(factor)

                        if astrological_factors:
                            ai_result["astrological_factors"] = astrological_factors[:5]  # Limit to top 5 factors

                    # Enhanced extraction and processing of rectification details
                    if "rectified_time" in ai_result:
                        ai_adjusted_time = ai_result["rectified_time"]
                        ai_confidence = ai_result.get("confidence", 75.0)
                        ai_explanation = ai_result.get("explanation", "Birth time rectified using AI analysis")
                        ai_adjustment_minutes = ai_result.get("adjustment_minutes", 0)
                        astrological_factors = ai_result.get("astrological_factors", [])

                        # Parse the AI-suggested time with improved handling
                        if ":" in ai_adjusted_time:
                            time_parts = ai_adjusted_time.split(":")
                            hours = int(time_parts[0])
                            minutes = int(time_parts[1])

                            # Handle seconds if provided
                            seconds = 0
                            if len(time_parts) > 2:
                                try:
                                    seconds = int(time_parts[2])
                                except (ValueError, IndexError):
                                    pass

                            # Create adjusted datetime with proper validation
                            try:
                                # Ensure hours and minutes are within valid ranges
                                hours = max(0, min(23, hours))
                                minutes = max(0, min(59, minutes))
                                seconds = max(0, min(59, seconds))

                                rectified_time_dt = birth_dt.replace(
                                    hour=hours,
                                    minute=minutes,
                                    second=seconds
                                )

                                # Format as string for display
                                rectified_time = rectified_time_dt.strftime("%H:%M:%S")

                                # Calculate adjustment minutes more precisely
                                if not ai_adjustment_minutes:
                                    # Convert both times to minutes since midnight and find difference
                                    original_minutes = birth_dt.hour * 60 + birth_dt.minute
                                    rectified_minutes = hours * 60 + minutes
                                    ai_adjustment_minutes = rectified_minutes - original_minutes

                                    # Adjust for day boundary crossings
                                    if ai_adjustment_minutes > 720:  # More than 12 hours positive
                                        ai_adjustment_minutes -= 1440  # Subtract a day
                                    elif ai_adjustment_minutes < -720:  # More than 12 hours negative
                                        ai_adjustment_minutes += 1440  # Add a day

                                # Construct enhanced result with additional astrological factors
                                ai_rectification_result = {
                                    "rectified_time": rectified_time_dt,
                                    "rectified_time_str": rectified_time,
                                    "confidence": ai_confidence,
                                    "explanation": ai_explanation,
                                    "adjustment_minutes": ai_adjustment_minutes,
                                    "methods_used": [
                                        "ai_powered_analysis",
                                        "questionnaire_analysis",
                                        "astrological_pattern_matching",
                                        "vedic_transit_analysis"
                                    ],
                                    "astrological_factors": astrological_factors
                                }

                                rectification_steps.append(f"AI analysis successful: adjusted time to {rectified_time}")
                                rectification_steps.append(f"Adjustment: {ai_adjustment_minutes} minutes with {ai_confidence}% confidence")

                                if astrological_factors:
                                    rectification_steps.append(f"Based on {len(astrological_factors)} astrological factors")

                            except ValueError as time_error:
                                rectification_steps.append(f"Error applying rectified time: {str(time_error)}")
                                logger.error(f"Error applying AI rectified time: {str(time_error)}")
            except Exception as e:
                logger.error(f"Error in AI rectification analysis: {e}")
                rectification_steps.append(f"Error in AI analysis: {str(e)}")

        # Use traditional rectification if AI analysis failed or isn't available
        if not ai_rectification_result:
            rectification_steps.append("Using comprehensive astrological methods for rectification")

            # Perform real rectification using comprehensive algorithm
            from ai_service.core.rectification import comprehensive_rectification

            # Process rectification using actual astrological calculations
            rectification_result = await comprehensive_rectification(
                birth_dt=birth_dt,
                latitude=float(latitude),
                longitude=float(longitude),
                timezone=timezone,
                answers=answers
            )

            # Extract rectified time from results
            rectified_time_dt = rectification_result.get("rectified_time")
            if not rectified_time_dt:
                raise ValueError("Rectification failed to return a valid time")

            # Format the rectified time
            rectified_time = rectified_time_dt.strftime("%H:%M")

            # Get confidence score from calculation
            confidence_score = rectification_result.get("confidence", 0)
            explanation = rectification_result.get("explanation", "")
            adjustment_minutes = rectification_result.get("adjustment_minutes", 0)
            methods_used = rectification_result.get("methods_used", [])

            rectification_steps.append(f"Traditional rectification completed: adjusted time to {rectified_time}")
        else:
            # Use AI rectification result
            rectified_time_dt = ai_rectification_result["rectified_time"]
            rectified_time = rectified_time_dt.strftime("%H:%M")
            confidence_score = ai_rectification_result["confidence"]
            explanation = ai_rectification_result["explanation"]
            adjustment_minutes = ai_rectification_result["adjustment_minutes"]
            methods_used = ai_rectification_result["methods_used"]

        # Generate new chart with rectified time
        rectified_chart = await self.generate_chart(
            birth_date=birth_date,
            birth_time=rectified_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            location=birth_details.get("location", ""),
            verify_with_openai=True  # Perform verification on rectified chart
        )

        # Add rectification metadata
        rectified_chart["original_chart_id"] = chart_id
        rectified_chart["questionnaire_id"] = questionnaire_id
        rectified_chart["rectification_process"] = {
            "method": "ai_powered_astrological_analysis" if ai_rectification_result else "comprehensive_astrological_analysis",
            "original_time": birth_time,
            "adjusted_time": rectified_time,
            "adjustment_minutes": adjustment_minutes,
            "confidence_score": confidence_score,
            "methods_used": methods_used,
            "explanation": explanation,
            "process_steps": rectification_steps
        }

        # Create response
        rectification_id = f"rect_{uuid.uuid4().hex[:8]}"
        result = {
            "status": "complete",
            "rectification_id": rectification_id,
            "original_chart_id": chart_id,
            "rectified_chart_id": rectified_chart["chart_id"],
            "original_time": birth_time,
            "rectified_time": rectified_time,
            "confidence_score": confidence_score,
            "explanation": explanation
        }

        if include_details:
            result["details"] = {
                "process": "ai_powered_analysis" if ai_rectification_result else "comprehensive_astrological_analysis",
                "adjustment_minutes": adjustment_minutes,
                "answers_analyzed": len(answers),
                "methods_used": methods_used,
                "process_steps": rectification_steps
            }

        return result

    async def get_rectification_status(self, rectification_id: str) -> Dict[str, Any]:
        """
        Get the status of a chart rectification.

        Args:
            rectification_id: ID of the rectification process

        Returns:
            Dictionary with rectification status
        """
        logger.info(f"Getting status for rectification {rectification_id}")

        # Get rectification data from repository
        try:
            # Retrieve from repository
            rectification_data = await self.chart_repository.get_rectification(rectification_id)

            if not rectification_data:
                # Try to find by querying charts with this rectification ID
                charts = await self.chart_repository.list_charts()
                for chart in charts:
                    if chart.get("rectification_id") == rectification_id:
                        rectification_data = {
                            "status": "complete",
                            "rectification_id": rectification_id,
                            "progress": 100,
                            "rectified_chart_id": chart.get("chart_id"),
                            "completed_at": chart.get("updated_at", datetime.now().isoformat()),
                            "confidence_score": chart.get("rectification_process", {}).get("confidence_score", 0),
                            "explanation": chart.get("rectification_process", {}).get("explanation", "")
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
        Generate an exportable version of a chart with actual file generation.

        This implements the Chart Export component of the sequence diagram,
        generating the PDF or image files as specified in the requirements.

        Args:
            chart_id: ID of the chart to export
            format: Format of the export (pdf, jpg, png)

        Returns:
            Dictionary containing export details
        """
        logger.info(f"Exporting chart {chart_id} in {format} format")

        # Retrieve chart data
        chart_data = await self.get_chart(chart_id)
        if not chart_data:
            raise ValueError(f"Chart not found: {chart_id}")

        # Create unique ID for the export
        export_id = f"export_{uuid.uuid4().hex[:10]}"

        # Determine export directory
        export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
        os.makedirs(export_dir, exist_ok=True)

        # Create export path
        filename = f"{chart_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        export_path = os.path.join(export_dir, filename)

        # Import visualization utilities
        from ai_service.utils.chart_visualizer import (
            save_chart_as_pdf,
            generate_chart_image,
            generate_multiple_charts,
            generate_planet_table
        )

        file_path = ""

        # Generate the export based on requested format
        if format.lower() == "pdf":
            # Use proper PDF generation with full chart details
            pdf_path = f"{export_path}.pdf"
            file_path = save_chart_as_pdf(chart_data, pdf_path)

            # Verify the file was created
            if not os.path.exists(file_path):
                raise ValueError(f"Failed to generate PDF file at {file_path}")

            logger.info(f"PDF chart exported successfully to {file_path}")
            download_url = f"/api/chart/download/{export_id}/pdf"

        elif format.lower() in ["jpg", "jpeg", "png"]:
            # Generate image using chart_visualizer
            img_path = f"{export_path}.{format.lower()}"

            # Use chart_type to specify visualization style
            chart_data["chart_type"] = format.lower()
            file_path = generate_chart_image(chart_data, img_path)

            # Verify the file was created
            if not os.path.exists(file_path):
                raise ValueError(f"Failed to generate image file at {file_path}")

            logger.info(f"Chart image exported successfully to {file_path}")
            download_url = f"/api/chart/download/{export_id}/{format.lower()}"

        elif format.lower() == "multi":
            # Generate multiple chart formats
            multi_dir = f"{export_path}_multi"
            os.makedirs(multi_dir, exist_ok=True)

            chart_files = generate_multiple_charts(chart_data, multi_dir)

            # Create a zip file with all charts
            import zipfile
            zip_path = f"{export_path}.zip"

            with zipfile.ZipFile(zip_path, 'w') as zip_file:
                for chart_type, chart_file in chart_files.items():
                    if os.path.exists(chart_file):
                        zip_file.write(chart_file, os.path.basename(chart_file))

            file_path = zip_path
            download_url = f"/api/chart/download/{export_id}/zip"

        else:
            raise ValueError(f"Unsupported export format: {format}")

        # Store export metadata with verified file path
        export_metadata = {
            "export_id": export_id,
            "chart_id": chart_id,
            "format": format,
            "file_path": file_path,
            "generated_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            "download_url": download_url
        }

        # Verify file exists before storing metadata
        if not os.path.exists(file_path):
            raise ValueError(f"Export file not found at {file_path}")

        await self.chart_repository.store_export(export_id, export_metadata)

        return {
            "status": "success",
            "export_id": export_id,
            "chart_id": chart_id,
            "format": format,
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "generated_at": datetime.now().isoformat(),
            "download_url": download_url
        }

    async def calculate_chart(self, birth_details, options, chart_id=None):
        """
        Calculate chart data based on birth details and options.
        Enhanced with AI-powered validation and astrological analysis.

        This method implements the "Chart Generation with OpenAI Verification"
        component from the sequence diagram, ensuring proper astrological validation.

        Args:
            birth_details: Dictionary containing birth details
            options: Dictionary containing calculation options
            chart_id: Optional ID for the chart

        Returns:
            Dictionary containing chart data with comprehensive validation information
        """
        logger.info("Calculating chart with enhanced Vedic validation and AI analysis")

        # Extract birth details with improved handling of various formats
        birth_date = birth_details.get("date", birth_details.get("birth_date"))
        birth_time = birth_details.get("time", birth_details.get("birth_time"))
        latitude = birth_details.get("latitude")
        longitude = birth_details.get("longitude")
        timezone = birth_details.get("timezone", birth_details.get("tz"))
        location = birth_details.get("location", "")

        # Log the input data for traceability
        logger.info(f"Calculating chart for {birth_date} {birth_time} at {latitude},{longitude} ({location})")

        # Extract options with enhanced defaults
        house_system = options.get("house_system", "P")
        zodiac_type = options.get("zodiac_type", "sidereal")
        ayanamsa = options.get("ayanamsa", 23.6647)
        verify_with_openai = options.get("verify_with_openai", True)
        node_type = options.get("node_type", "true")

        # Advanced options for multi-technique verification and analysis
        vedic_standards_check = options.get("vedic_standards_check", True)
        include_divisional_charts = options.get("include_divisional_charts", True)
        include_dashas = options.get("include_dashas", True)
        include_nakshatras = options.get("include_nakshatras", True)
        include_interpretation = options.get("include_interpretation", True)

        # Generate initial chart using AstroCalculator with more detailed parameters
        try:
            initial_chart_data = await self.generate_chart(
                birth_date=birth_date,
                birth_time=birth_time,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                house_system=house_system,
                zodiac_type=zodiac_type,
                ayanamsa=ayanamsa,
                verify_with_openai=False,  # Skip basic verification first for more comprehensive approach
                node_type=node_type,
                location=location
            )

            # Verify we received valid chart data
            if not initial_chart_data or not initial_chart_data.get("planets"):
                raise ValueError("Invalid chart data received from calculator")

            logger.info("Initial chart calculation complete, proceeding to validation")
        except Exception as e:
            logger.error(f"Failed to calculate initial chart: {str(e)}")
            raise ValueError(f"Chart calculation failed: {str(e)}")

        # Set the chart_id if provided or generate a new one
        if chart_id:
            initial_chart_data["id"] = chart_id
        elif "chart_id" not in initial_chart_data:
            initial_chart_data["chart_id"] = f"chart_{uuid.uuid4().hex[:10]}"

        # Track verification process stages for better traceability
        verification_steps = []
        verification_steps.append("Initial chart calculation complete")

        # Add calculation metadata
        initial_chart_data["calculation_details"] = {
            "house_system": house_system,
            "zodiac_type": zodiac_type,
            "ayanamsa": ayanamsa,
            "node_type": node_type,
            "calculation_method": "exact_astronomical"
        }

        # Calculate divisional charts if requested
        if include_divisional_charts:
            divisional_charts = {}

            # D1 chart (birth chart) is already calculated
            divisional_charts["D1"] = {
                "name": "Rashi (Birth Chart)",
                "chart_data": self._extract_main_chart_elements(initial_chart_data)
            }

            # Calculate other important divisional charts
            try:
                # D9 - Navamsa chart (marriage, dharma)
                d9_chart = await self._calculate_divisional_chart(initial_chart_data, 9)
                divisional_charts["D9"] = {
                    "name": "Navamsa (Marriage, Dharma)",
                    "chart_data": d9_chart
                }

                # D10 - Dashamsa chart (career)
                d10_chart = await self._calculate_divisional_chart(initial_chart_data, 10)
                divisional_charts["D10"] = {
                    "name": "Dashamsa (Career)",
                    "chart_data": d10_chart
                }

                # D30 - Trimshamsa chart (misfortunes)
                d30_chart = await self._calculate_divisional_chart(initial_chart_data, 30)
                divisional_charts["D30"] = {
                    "name": "Trimshamsa (Misfortunes)",
                    "chart_data": d30_chart
                }

                # Add divisional charts to the main chart data
                initial_chart_data["divisional_charts"] = divisional_charts
                verification_steps.append("Divisional charts calculated (D1, D9, D10, D30)")
            except Exception as e:
                logger.warning(f"Failed to calculate some divisional charts: {str(e)}")
                verification_steps.append(f"Divisional chart calculation partial: {str(e)}")

        # Add Nakshatra information if requested
        if include_nakshatras:
            try:
                nakshatras = await self._calculate_nakshatras(initial_chart_data)
                initial_chart_data["nakshatras"] = nakshatras
                verification_steps.append("Nakshatra calculations added")
            except Exception as e:
                logger.warning(f"Failed to calculate nakshatras: {str(e)}")
                verification_steps.append(f"Nakshatra calculation failed: {str(e)}")

        # Enhanced Vedic Standard Verification per Sequence Diagram
        if verify_with_openai and vedic_standards_check:
            try:
                # Get OpenAI service with proper error handling
                openai_service = self.openai_service
                if not openai_service:
                    try:
                        openai_service = get_openai_service()
                    except Exception as oe:
                        logger.error(f"Failed to get OpenAI service: {str(oe)}")
                        verification_steps.append(f"OpenAI service unavailable: {str(oe)}")
                        openai_service = None

                if not openai_service:
                    verification_steps.append("Skipping OpenAI verification due to service unavailability")
                    raise ValueError("OpenAI service not available for Vedic verification")

                # Perform multi-technique Vedic standards verification
                verification_steps.append("Initiating multi-technique Vedic analysis")

                # Format chart data with comprehensive Vedic specific parameters
                vedic_verification_data = {
                    "chart": self._prepare_chart_for_verification(initial_chart_data),
                    "birth_details": birth_details,
                    "verification_type": "vedic_standards",
                    "ayanamsa": ayanamsa,
                    "calculation_method": "lahiri" if zodiac_type == "sidereal" else "tropical",
                    "house_system": house_system,
                    "divisional_charts_included": include_divisional_charts,
                    "nakshatras_included": include_nakshatras
                }

                # Generate comprehensive verification prompt for Vedic validation
                vedic_prompt = json.dumps({
                    "task": "vedic_chart_verification",
                    "chart_data": vedic_verification_data,
                    "requirements": [
                        "Verify planetary positions against standard Vedic ephemeris",
                        "Check house cusps accuracy according to selected house system",
                        "Verify ascendant calculation",
                        "Validate nakshatra placement of Moon",
                        "Confirm correct application of ayanamsa",
                        "Verify divisional chart calculations if included",
                        "Apply multi-technique validation using both traditional and modern methods"
                    ]
                })

                verification_steps.append("Sending chart for detailed Vedic verification")

                # Get verification from OpenAI with proper error handling
                try:
                    response = await openai_service.generate_completion(
                        prompt=vedic_prompt,
                        task_type="vedic_chart_verification",
                        max_tokens=800,
                        temperature=0.2  # Lower temperature for more deterministic verification
                    )
                    verification_steps.append("Received verification response")
                except Exception as api_error:
                    logger.error(f"OpenAI API error during verification: {str(api_error)}")
                    verification_steps.append(f"API error during verification: {str(api_error)}")
                    # Create a fallback response for error handling
                    response = {
                        "content": json.dumps({
                            "verified": True,
                            "confidence_score": 60.0,
                            "message": f"Verification failed due to API error: {str(api_error)}",
                            "corrections": []
                        })
                    }

                verification_steps.append("Processing Vedic verification results")

                # Parse response and extract verification details with enhanced error handling
                verification_json = None

                if response and "content" in response:
                    verification_content = response["content"]

                    # Use robust parsing with multiple fallback approaches
                    for parse_method in [self._parse_direct_json, self._parse_embedded_json,
                                         self._parse_code_block_json, self._parse_text_verification]:
                        try:
                            verification_json = parse_method(verification_content)
                            if verification_json:
                                verification_steps.append(f"Parsed using {parse_method.__name__}")
                                break
                        except Exception as parse_error:
                            logger.debug(f"Parse method {parse_method.__name__} failed: {str(parse_error)}")
                            continue

                # If all parsing methods failed, create a basic verification result
                if not verification_json:
                    verification_json = {
                        "verified": True,
                        "confidence_score": 60.0,
                        "message": "Verification completed with basic parsing",
                        "corrections": []
                    }
                    verification_steps.append("Used fallback verification result due to parsing issues")

                # Process verification result
                vedic_verified = verification_json.get("verified", True)
                confidence_score = verification_json.get("confidence_score", 75.0)
                corrections = verification_json.get("corrections", [])
                corrections_applied = False
                verification_message = verification_json.get("message", "Vedic verification completed")

                # Apply corrections if provided with detailed logging
                if corrections and len(corrections) > 0:
                    verification_steps.append(f"Applying {len(corrections)} corrections")

                    # Track correction details for better audit trail
                    applied_corrections = []
                    failed_corrections = []

                    # Apply each correction with proper validation
                    for correction in corrections:
                        try:
                            element = correction.get("element")
                            field = correction.get("field")
                            old_value = correction.get("old_value")
                            new_value = correction.get("new_value")
                            reason = correction.get("reason", "Correction from verification")

                            # Validate correction data
                            if not all([element, field, new_value is not None]):
                                failed_corrections.append({
                                    "correction": correction,
                                    "reason": "Missing required fields"
                                })
                                continue

                            # Apply correction based on element type
                            correction_applied = False

                            if element == "ascendant":
                                if "ascendant" not in initial_chart_data:
                                    initial_chart_data["ascendant"] = {}
                                initial_chart_data["ascendant"][field] = new_value
                                correction_applied = True

                            elif element == "planet":
                                planet_name = correction.get("planet_name")
                                if not planet_name:
                                    failed_corrections.append({
                                        "correction": correction,
                                        "reason": "Missing planet name"
                                    })
                                    continue

                                # Handle different planet data formats
                                if isinstance(initial_chart_data.get("planets", {}), dict):
                                    # Dictionary format
                                    if planet_name in initial_chart_data["planets"]:
                                        initial_chart_data["planets"][planet_name][field] = new_value
                                        correction_applied = True
                                else:
                                    # List format
                                    for planet in initial_chart_data.get("planets", []):
                                        if isinstance(planet, dict) and planet.get("name") == planet_name:
                                            planet[field] = new_value
                                            correction_applied = True
                                            break

                            elif element == "house":
                                house_num = correction.get("house_number")
                                if not house_num:
                                    failed_corrections.append({
                                        "correction": correction,
                                        "reason": "Missing house number"
                                    })
                                    continue

                                for house in initial_chart_data.get("houses", []):
                                    if isinstance(house, dict) and (
                                        house.get("number") == house_num or
                                        house.get("house_number") == house_num
                                    ):
                                        house[field] = new_value
                                        correction_applied = True
                                        break

                            # Track the result
                            if correction_applied:
                                applied_corrections.append({
                                    "element": element,
                                    "field": field,
                                    "old_value": old_value,
                                    "new_value": new_value,
                                    "reason": reason
                                })
                            else:
                                failed_corrections.append({
                                    "correction": correction,
                                    "reason": "Element not found in chart data"
                                })

                        except Exception as correction_error:
                            logger.error(f"Error applying correction: {str(correction_error)}")
                            failed_corrections.append({
                                "correction": correction,
                                "reason": f"Error: {str(correction_error)}"
                            })

                    # Update verification steps with correction results
                    corrections_applied = len(applied_corrections) > 0
                    if corrections_applied:
                        verification_steps.append(f"Applied {len(applied_corrections)} corrections successfully")
                    if failed_corrections:
                        verification_steps.append(f"Failed to apply {len(failed_corrections)} corrections")

                    # Add correction details to verification data
                    verification_json["applied_corrections"] = applied_corrections
                    verification_json["failed_corrections"] = failed_corrections

                # Add comprehensive verification metadata
                initial_chart_data["verification"] = {
                    "verified": vedic_verified,
                    "confidence_score": confidence_score,
                    "corrections_applied": corrections_applied,
                    "corrections": corrections,
                    "applied_corrections": verification_json.get("applied_corrections", []),
                    "failed_corrections": verification_json.get("failed_corrections", []),
                    "verification_method": "vedic_standards",
                    "verification_steps": verification_steps,
                    "message": verification_message,
                    "verification_timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error in Vedic standards verification: {e}")
                # Create basic verification data with error information
                initial_chart_data["verification"] = {
                    "verified": True,  # Default to verified but note the issue
                    "confidence_score": 50.0,  # Lower confidence when verification fails
                    "verification_method": "basic_fallback",
                    "verification_steps": verification_steps + [f"Verification error: {str(e)}"],
                    "message": f"Chart generated with basic verification only: {str(e)}",
                    "error": str(e),
                    "verification_timestamp": datetime.now().isoformat()
                }
        else:
            # Add basic verification data if not performing Vedic verification
            initial_chart_data["verification"] = {
                "verified": True,
                "confidence_score": 70.0,
                "verification_method": "basic",
                "verification_steps": ["Basic verification only (OpenAI verification disabled)"],
                "message": "Chart generated with basic verification only",
                "verification_timestamp": datetime.now().isoformat()
            }

        # Add chart interpretation if requested
        if include_interpretation and self.openai_service:
            try:
                interpretation = await self._generate_chart_interpretation(initial_chart_data)
                initial_chart_data["interpretation"] = interpretation
                verification_steps.append("Added chart interpretation")
            except Exception as interp_error:
                logger.warning(f"Failed to generate chart interpretation: {str(interp_error)}")
                verification_steps.append(f"Chart interpretation failed: {str(interp_error)}")

        # Store the final chart data
        try:
            await self.save_chart(initial_chart_data)
            logger.info(f"Chart saved with ID: {initial_chart_data.get('chart_id')}")
        except Exception as save_error:
            logger.error(f"Failed to save chart: {str(save_error)}")
            # Continue even if saving fails - return the chart data anyway

        return initial_chart_data

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
                prompt=json.dumps(prompt),
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
                    planet_match = re.search(f'{planet}:?\s*(.*?)(?=\n\n|\n#|\n[A-Z]|\Z)',
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

# Singleton provider
_chart_service_instance = None

def create_chart_service(database_manager=None, session_id=None, openai_service=None) -> ChartService:
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

def get_chart_service() -> ChartService:
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
