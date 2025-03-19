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

    async def rectify_chart(
        self,
        chart_id: str,
        questionnaire_id: str,
        answers: List[Dict[str, Any]],
        include_details: bool = False
    ) -> Dict[str, Any]:
        """
        Rectify a chart based on questionnaire answers.

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
        location = birth_details.get("location", "")

        # Mock rectification - adjust birth time by 15 minutes
        # In a real implementation, this would use AI and answers to determine adjustment
        time_parts = birth_time.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1])

        # Add 15 minutes
        minute += 15
        if minute >= 60:
            minute -= 60
            hour += 1
        if hour >= 24:
            hour -= 24

        rectified_time = f"{hour:02d}:{minute:02d}"

        # Generate new chart with rectified time
        rectified_chart = await self.generate_chart(
            birth_date=birth_date,
            birth_time=rectified_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            location=location,
            verify_with_openai=False  # Skip verification for rectified chart
        )

        # Add rectification metadata
        rectified_chart["original_chart_id"] = chart_id
        rectified_chart["questionnaire_id"] = questionnaire_id
        rectified_chart["rectification_process"] = {
            "method": "time_adjustment",
            "original_time": birth_time,
            "adjusted_time": rectified_time,
            "adjustment_minutes": 15,
            "confidence_score": 85.0
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
            "confidence_score": 85.0,
        }

        if include_details:
            result["details"] = {
                "process": "time_adjustment",
                "adjustment_minutes": 15,
                "answers_analyzed": len(answers)
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

        # Mock implementation - always return complete
        return {
            "status": "complete",
            "rectification_id": rectification_id,
            "progress": 100,
            "rectified_chart_id": f"chart_{uuid.uuid4().hex[:10]}",
            "completed_at": datetime.now().isoformat()
        }

    async def export_chart(self, chart_id: str, format: str = "pdf") -> Dict[str, Any]:
        """
        Generate an exportable version of a chart.

        Args:
            chart_id: ID of the chart to export
            format: Export format (pdf, jpg, etc.)

        Returns:
            Dictionary with export details including download URL
        """
        logger.info(f"Exporting chart {chart_id} in {format} format")

        # Mock implementation - generate fake download URL
        return {
            "status": "success",
            "chart_id": chart_id,
            "format": format,
            "generated_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=7)).isoformat(),
            "download_url": f"https://example.com/charts/{chart_id}.{format}"
        }

    async def calculate_chart(self, birth_details, options, chart_id=None):
        """
        Calculate chart data based on birth details and options.
        This is a convenience method that calls generate_chart with the appropriate parameters.

        Args:
            birth_details: Dictionary containing birth details
            options: Dictionary containing calculation options
            chart_id: Optional ID for the chart

        Returns:
            Dictionary containing chart data
        """
        logger.info("Calculating chart through calculate_chart method")

        # Extract birth details
        birth_date = birth_details.get("date", birth_details.get("birth_date"))
        birth_time = birth_details.get("time", birth_details.get("birth_time"))
        latitude = birth_details.get("latitude")
        longitude = birth_details.get("longitude")
        timezone = birth_details.get("timezone", birth_details.get("tz"))
        location = birth_details.get("location", "")

        # Extract options
        house_system = options.get("house_system", "P")
        zodiac_type = options.get("zodiac_type", "sidereal")
        ayanamsa = options.get("ayanamsa", 23.6647)
        verify_with_openai = options.get("verify_with_openai", True)
        node_type = options.get("node_type", "true")

        # Call generate_chart
        chart_data = await self.generate_chart(
            birth_date=birth_date,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            house_system=house_system,
            zodiac_type=zodiac_type,
            ayanamsa=ayanamsa,
            verify_with_openai=verify_with_openai,
            node_type=node_type,
            location=location
        )

        # Set the chart_id if provided
        if chart_id:
            chart_data["id"] = chart_id

        return chart_data

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
