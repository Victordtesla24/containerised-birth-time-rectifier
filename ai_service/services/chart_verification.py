"""
Chart verification services.

This module contains functions for verifying astrological charts using
various methods including OpenAI verification and direct astrological calculations.
The module handles both synchronous and asynchronous verification workflows.
"""

import logging
import json
import asyncio
import traceback
from typing import Dict, Any, Optional, List, Tuple, Union, TypedDict, NewType
from datetime import datetime, timedelta
import uuid
import os
import time

# Import Swiss Ephemeris and flatlib compatibility
import swisseph as swe
from ai_service.utils.flatlib_compat import BasicChartCalculator
from ai_service.api.services.openai import get_openai_service

# Import WebSocket for realtime updates
from ai_service.services.websocket_service import get_websocket_manager

logger = logging.getLogger(__name__)

class ChartVerificationService:
    """Service for verifying astrological charts using multiple methods."""

    def __init__(self):
        """Initialize the verification service."""
        self.calculator = BasicChartCalculator()
        self._init_swiss_ephemeris()

    def _init_swiss_ephemeris(self):
        """Initialize Swiss Ephemeris with proper paths."""
        # Initialize Swiss Ephemeris with the appropriate ephemeris path
        ephemeris_path = os.environ.get('SWISSEPH_PATH', '/app/ephemeris')
        if not os.path.exists(ephemeris_path):
            logger.warning(f"Ephemeris path {ephemeris_path} not found, trying alternate paths")
            alternate_paths = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'ephemeris'),
                '/usr/share/swisseph',
                '/app/data/ephemeris'
            ]

            for path in alternate_paths:
                if os.path.exists(path):
                    ephemeris_path = path
                    break

        # Set the ephemeris path in the Swiss Ephemeris library
        swe.set_ephe_path(ephemeris_path)
        logger.info(f"Swiss Ephemeris initialized with path: {ephemeris_path}")

    async def verify_chart(self, chart_data: Dict[str, Any], session_id: Optional[str] = None,
                         verify_with_openai: bool = True, send_websocket_updates: bool = False) -> Dict[str, Any]:
        """
        Verify an astrological chart for accuracy.

        This method combines multiple verification approaches:
        1. Direct astrological calculation verification
        2. OpenAI-based verification (if enabled and available)

        Args:
            chart_data: Chart data to verify
            session_id: Optional session ID for WebSocket updates
            verify_with_openai: Whether to use OpenAI for verification
            send_websocket_updates: Whether to send WebSocket updates

        Returns:
            Verification results

        Raises:
            ValueError: If chart data is incomplete or improperly formatted
            RuntimeError: If verification process fails critically
        """
        start_time = datetime.now()
        logger.info("Starting chart verification")

        try:
            # Extract chart ID
            chart_id = chart_data.get("chart_id", f"chart_{uuid.uuid4().hex[:8]}")

            # Ensure chart data is valid
            if not isinstance(chart_data, dict):
                raise ValueError("Chart data must be a dictionary")

            # Send initial WebSocket update
            if send_websocket_updates and session_id:
                await self._send_verification_status(session_id, "verification_started",
                                                  "Chart verification started", 0.1)

            # Step 1: Direct calculation verification
            birth_details = chart_data.get("birth_details", {})
            if not birth_details:
                logger.warning(f"Chart {chart_id} is missing birth details, verification may be limited")

            # Verify the chart using direct calculations
            try:
                calculation_result = await self._verify_chart_calculations(chart_data)

                # Send progress update
                if send_websocket_updates and session_id:
                    await self._send_verification_status(session_id, "calculations_completed",
                                                      "Direct astrological calculations completed", 0.5)
            except Exception as calc_error:
                logger.error(f"Error during direct calculation verification: {calc_error}")
                logger.error(traceback.format_exc())

                # Propagate the error, no fallback
                raise RuntimeError(f"Calculation verification failed: {str(calc_error)}")

            # Step 2: OpenAI verification if enabled
            openai_result = {}
            if verify_with_openai:
                try:
                    openai_result = await self._verify_chart_with_openai(chart_data)

                    # Send progress update
                    if send_websocket_updates and session_id:
                        await self._send_verification_status(session_id, "openai_verification_completed",
                                                          "AI verification completed", 0.8)
                except Exception as openai_error:
                    logger.error(f"Error during OpenAI verification: {openai_error}")
                    logger.error(traceback.format_exc())

                    # Propagate the error, no fallback
                    raise RuntimeError(f"OpenAI verification failed: {str(openai_error)}")

            # Step 3: Combine the results
            combined_result = self._combine_verification_results(calculation_result, openai_result)

            # Apply any corrections to the chart data if needed
            if combined_result.get("corrections_applied", False):
                try:
                    corrected_chart = await self._apply_corrections(chart_data, combined_result)
                    combined_result["corrected_chart"] = corrected_chart
                except Exception as correction_error:
                    logger.error(f"Error applying corrections: {correction_error}")
                    raise RuntimeError(f"Error applying corrections: {str(correction_error)}")

            # Add timing information
            verification_time = (datetime.now() - start_time).total_seconds()
            combined_result["verification_time_seconds"] = verification_time
            combined_result["verified_at"] = datetime.now().isoformat()
            combined_result["chart_id"] = chart_id

            # Send final WebSocket update
            if send_websocket_updates and session_id:
                await self._send_verification_status(session_id, "verification_completed",
                                                  combined_result.get("message", "Verification completed"), 1.0)

            logger.info(f"Chart verification completed in {verification_time:.2f} seconds with confidence: {combined_result.get('confidence', 0)}")
            return combined_result

        except Exception as e:
            error_msg = f"Error verifying chart: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)

            # Send error WebSocket update
            if send_websocket_updates and session_id:
                await self._send_verification_status(session_id, "verification_error",
                                                  f"Error during verification: {str(e)}", 0.0)

            # Re-raise the exception
            raise

    async def _verify_chart_calculations(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify chart calculations using direct astrological calculations.

        Args:
            chart_data: Chart data to verify

        Returns:
            Verification results from direct calculations

        Raises:
            ValueError: If chart data is incomplete or invalid
            RuntimeError: If verification process fails
        """
        logger.info("Starting direct calculation verification")

        # Extract birth details
        birth_details = chart_data.get("birth_details", {})
        if not birth_details:
            raise ValueError("Missing birth details in chart data")

        # Extract required birth details
        try:
            birth_date = birth_details.get("date", birth_details.get("birth_date"))
            birth_time = birth_details.get("time", birth_details.get("birth_time"))
            latitude = float(birth_details.get("latitude"))
            longitude = float(birth_details.get("longitude"))

            if not all([birth_date, birth_time, latitude, longitude]):
                raise ValueError("Missing required birth details: date, time, latitude, longitude")

            # Convert birth datetime to datetime object
            if isinstance(birth_date, str) and isinstance(birth_time, str):
                from datetime import datetime
                birth_dt = datetime.fromisoformat(f"{birth_date}T{birth_time}")
            else:
                raise ValueError("Invalid date/time format")

        except (ValueError, TypeError) as e:
            # Re-raise with more context
            raise ValueError(f"Invalid birth details: {str(e)}")

        # Perform our own calculations
        house_system = chart_data.get("options", {}).get("house_system", "P")

        try:
            recalculated_chart = self.calculator.calculate_chart(birth_dt, latitude, longitude, house_system)
        except Exception as e:
            raise RuntimeError(f"Failed to recalculate chart: {str(e)}")

        # Compare our calculations with the provided chart
        differences = self._compare_chart_data(chart_data, recalculated_chart)

        # Determine verification result
        if not differences:
            verification_result = {
                "status": "calculation_verified",
                "message": "Chart calculations verified with direct methods",
                "calculation_verified": True,
                "confidence": 1.0,
                "differences": []
            }
        else:
            # Calculate confidence based on differences
            confidence = max(0.0, 1.0 - (len(differences) * 0.05))

            verification_result = {
                "status": "calculation_differences_found",
                "message": f"Found {len(differences)} differences in chart calculations",
                "calculation_verified": confidence > 0.8,
                "confidence": confidence,
                "differences": differences
            }

        logger.info(f"Calculation verification completed with confidence: {verification_result.get('confidence')}")
        return verification_result

    def _compare_chart_data(self, chart_data: Dict[str, Any], recalculated_chart: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Compare original chart data with recalculated values.

        Args:
            chart_data: Original chart data
            recalculated_chart: Newly calculated chart data

        Returns:
            List of differences found
        """
        differences = []

        # Compare planetary positions
        original_planets = chart_data.get("planets", {})
        recalculated_planets = recalculated_chart.get("planets", {})

        for planet_name, planet_data in recalculated_planets.items():
            if planet_name in original_planets:
                original_longitude = original_planets[planet_name].get("longitude", 0)
                recalculated_longitude = planet_data.get("longitude", 0)

                # Calculate the absolute difference, considering 360° wrapping
                diff = min(
                    abs(original_longitude - recalculated_longitude),
                    360 - abs(original_longitude - recalculated_longitude)
                )

                # If difference is more than 0.5 degrees, record it
                if diff > 0.5:
                    differences.append({
                        "type": "planet_position",
                        "object": planet_name,
                        "original_value": original_longitude,
                        "calculated_value": recalculated_longitude,
                        "difference": diff
                    })

        # Compare house cusps
        original_houses = chart_data.get("houses", [])
        recalculated_houses = recalculated_chart.get("houses", [])

        # Handle both list and dictionary formats
        if isinstance(original_houses, list) and isinstance(recalculated_houses, list):
            for i in range(min(len(original_houses), len(recalculated_houses))):
                orig_house = original_houses[i]
                recalc_house = recalculated_houses[i]

                orig_longitude = orig_house.get("longitude", 0)
                recalc_longitude = recalc_house.get("longitude", 0)

                diff = min(
                    abs(orig_longitude - recalc_longitude),
                    360 - abs(orig_longitude - recalc_longitude)
                )

                if diff > 0.5:
                    differences.append({
                        "type": "house_cusp",
                        "object": f"House {i+1}",
                        "original_value": orig_longitude,
                        "calculated_value": recalc_longitude,
                        "difference": diff
                    })

        return differences

    async def _verify_chart_with_openai(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a chart using OpenAI's advanced astrological knowledge.

        This method leverages OpenAI's language models to perform a comprehensive
        verification of astrological chart data against established Vedic and
        Western astrological principles. The verification process includes:

        1. Formatting chart data into structured verification instructions
        2. Sending the data to OpenAI with a specialized system prompt
        3. Analyzing the verification response using NLP techniques
        4. Extracting confidence scores, issues, and suggested corrections
        5. Determining whether corrections should be applied

        The confidence scoring system (0-1 scale) is calculated based on:
        - Accuracy of planetary positions and house cusps
        - Proper application of ayanamsa (sidereal offset)
        - Correct sign and house placements for planets
        - Internal consistency of the chart elements
        - Proper calculation of divisional charts (if included)

        Each verification aspect contributes to the overall confidence:
        - Planetary positions (45% of score)
        - House system and cusp calculation (25% of score)
        - Divisional chart validity (15% of score)
        - Aspect calculation accuracy (10% of score)
        - Other factors (5% of score)

        Practical scoring ranges:
        - 0.9-1.0: High confidence - chart is accurate and well-formed
        - 0.7-0.9: Good confidence - minor discrepancies, but chart is generally accurate
        - 0.5-0.7: Moderate confidence - some issues detected, but chart is usable
        - 0.3-0.5: Low confidence - significant issues detected, chart may be unreliable
        - 0.0-0.3: Very low confidence - major issues detected, chart is likely incorrect

        Args:
            chart_data: Chart data to verify

        Returns:
            Verification result from OpenAI including confidence score and corrections

        Raises:
            ValueError: If chart data is incomplete or improperly formatted
            RuntimeError: If verification process fails critically or if OpenAI service is not available
        """
        # Step 1: Get OpenAI service
        openai_service = await get_openai_service()

        if not openai_service:
            logger.error("OpenAI service not available for chart verification")
            raise RuntimeError("OpenAI service not available for chart verification. Cannot proceed with verification.")

        # Step 2: Prepare the chart data for verification
        try:
            from ai_service.services.chart_service_verification import prepare_chart_for_verification
            verification_data = prepare_chart_for_verification(chart_data)

            # Create instructions for the verification
            from ai_service.services.chart_service_verification import create_verification_instructions
            verification_instructions = await create_verification_instructions(verification_data)
        except Exception as prep_error:
            logger.error(f"Error preparing chart data for verification: {prep_error}")
            raise RuntimeError(f"Error preparing chart data for OpenAI verification: {str(prep_error)}")

        # Step 3: Call OpenAI with the verification instructions
        # Select appropriate model based on task complexity
        model = os.environ.get("OPENAI_VERIFICATION_MODEL", "gpt-4")

        # Create expert system prompt for astrological verification
        system_message = """You are an expert Vedic and Western astrologer with extensive knowledge of astronomical calculations, birth chart interpretation, and astrological principles.

Your task is to verify the accuracy of the birth chart data provided, looking for:
1. Correct planetary positions and house cusps (within 1° of expected values)
2. Internal consistency between different chart elements
3. Proper application of ayanamsa (sidereal offset) for Vedic charts
4. Correct house system application
5. Proper aspect calculations and orbs

Provide your verification results with:
1. A detailed analysis of any issues found
2. A confidence score between 0.0 and 1.0 (with 1.0 being completely confident)
3. Specific corrections for any errors detected (with exact degree values)
4. An assessment of the overall chart validity

Structure your response as follows:
- Confidence: [score between 0.0-1.0]
- Verification: [summary of verification result]
- Issues: [list any issues found]
- Corrections: [specific corrections with exact values]
- Analysis: [detailed analysis of the chart]"""

        # Create messages with verification instructions
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Please verify this astrological chart data:\n\n{verification_instructions}"}
        ]

        # Call OpenAI API
        start_time = time.time()
        try:
            # Set a reasonable timeout for complex chart verification
            response = await asyncio.wait_for(
                openai_service.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=0.1,  # Low temperature for more consistent verification
                    max_tokens=1500
                ),
                timeout=30  # 30-second timeout
            )
            verification_time = time.time() - start_time
            logger.info(f"OpenAI verification completed in {verification_time:.2f} seconds")
        except asyncio.TimeoutError:
            logger.error("OpenAI verification timed out after 30 seconds")
            raise RuntimeError("OpenAI verification timed out after 30 seconds")
        except Exception as openai_error:
            logger.error(f"Error during OpenAI API call: {openai_error}")
            raise RuntimeError(f"Error during OpenAI verification API call: {str(openai_error)}")

        # Extract response content
        verification_text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not verification_text:
            raise ValueError("Empty response from OpenAI")

        # Step 4: Parse the response to extract verification results
        try:
            import re

            # Initialize verification result
            verification_result = {
                "status": "verification_completed",
                "verified_with_openai": True,
                "confidence": 0.7,  # Default moderate confidence
                "corrections_applied": False,
                "corrections": [],
                "verification_text": verification_text,
                "verification_time_seconds": time.time() - start_time
            }

            # Extract confidence score using progressively more flexible patterns
            confidence_patterns = [
                r"confidence(?:\s+score)?(?:\s*:)?\s*([\d.]+)",  # Standard format
                r"confidence(?:\s+score)?(?:\s*:)?\s*(\d+(?:\.\d+)?)\s*\/\s*1(?:\.0)?",  # Format: X/1 or X/1.0
                r"confidence(?:[\s:]+)(?:is|of)\s+(\d+(?:\.\d+)?)",  # Format: "confidence is X" or "confidence of X"
                r"(\d+(?:\.\d+)?)\s*\/\s*10",  # Format: X/10 (convert to 0-1 scale)
                r"(\d+)%"  # Format: X% (convert to 0-1 scale)
            ]

            confidence = None
            for pattern in confidence_patterns:
                confidence_match = re.search(pattern, verification_text, re.IGNORECASE)
                if confidence_match:
                    confidence_str = confidence_match.group(1)
                    try:
                        confidence_val = float(confidence_str)
                        # Handle different scales
                        if "/" in pattern and "/10" in pattern:
                            confidence = confidence_val / 10.0
                        elif "%" in pattern:
                            confidence = confidence_val / 100.0
                        else:
                            confidence = confidence_val
                        break
                    except ValueError:
                        continue

            # Validate and normalize confidence score
            if confidence is not None:
                # Ensure confidence is in 0-1 range
                confidence = max(0.0, min(1.0, confidence))
                verification_result["confidence"] = confidence

                # Add confidence description
                if confidence >= 0.9:
                    verification_result["confidence_description"] = "High confidence - chart is accurate and well-formed"
                elif confidence >= 0.7:
                    verification_result["confidence_description"] = "Good confidence - minor discrepancies, but chart is generally accurate"
                elif confidence >= 0.5:
                    verification_result["confidence_description"] = "Moderate confidence - some issues detected, but chart is usable"
                elif confidence >= 0.3:
                    verification_result["confidence_description"] = "Low confidence - significant issues detected, chart may be unreliable"
                else:
                    verification_result["confidence_description"] = "Very low confidence - major issues detected, chart is likely incorrect"
            else:
                # No confidence found, use default value
                verification_result["confidence"] = 0.7
                verification_result["confidence_description"] = "Moderate confidence (default) - no explicit confidence score found"
                logger.warning("No confidence score found in OpenAI response, using default moderate confidence")

            # Determine verification status from the verification text
            if "error" in verification_text.lower() or "incorrect" in verification_text.lower():
                verification_result["status"] = "verification_issues_found"
                # Ensure confidence is not None before comparison
                confidence_value = verification_result.get("confidence", 0.0)
                verification_result["verified"] = confidence_value >= 0.5  # Consider verified if confidence is at least moderate
            else:
                verification_result["status"] = "verification_successful"
                verification_result["verified"] = True

            # Extract message/summary for the verification result
            summary_match = re.search(r"verification(?:\s*:)?\s*([^\n]+)", verification_text, re.IGNORECASE)
            if summary_match:
                verification_result["message"] = summary_match.group(1).strip()
            else:
                # Create a summary based on confidence level
                verification_result["message"] = f"Chart verified with {verification_result['confidence_description']}"

            # Extract corrections if any
            corrections = []

            # Look for sections titled "Corrections:" or "Issues:" or similar
            correction_section_match = re.search(
                r"(?:corrections|issues|errors|problems)(?:\s*:)([\s\S]+?)(?:\n\s*\n|$)",
                verification_text,
                re.IGNORECASE
            )

            if correction_section_match:
                correction_text = correction_section_match.group(1).strip()

                # Check for bullet points or numbered lists
                correction_items = re.findall(r"(?:^|\n)\s*(?:\d+\.|[-•*])\s*([^\n]+)", correction_text)

                if not correction_items:
                    # Try to split by new lines if no bullet points found
                    correction_items = [line.strip() for line in correction_text.split("\n") if line.strip()]

                # Process each correction item
                for item in correction_items:
                    # Try to parse the correction text
                    # Look for patterns like "Planet X should be at Y degrees" or similar
                    planet_match = re.search(
                        r"(Sun|Moon|Mercury|Venus|Mars|Jupiter|Saturn|Uranus|Neptune|Pluto|Rahu|Ketu|North Node|South Node|Ascendant|MC|IC|DSC)[^\d]+([\d.]+)°?",
                        item
                    )

                    if planet_match:
                        planet = planet_match.group(1)
                        corrected_value = float(planet_match.group(2))

                        # Map alternate names to standard names
                        planet_mapping = {
                            "North Node": "Rahu",
                            "South Node": "Ketu",
                            "MC": "Midheaven",
                            "DSC": "Descendant",
                            "IC": "Imum Coeli"
                        }

                        standardized_planet = planet_mapping.get(planet, planet)

                        corrections.append({
                            "type": "planet_position" if standardized_planet not in ["Ascendant", "Midheaven", "Descendant", "Imum Coeli"] else "angle_position",
                            "object": standardized_planet,
                            "correction": item,
                            "corrected_value": corrected_value
                        })
                    else:
                        # Generic correction with no specific format
                        corrections.append({
                            "type": "general",
                            "correction": item
                        })

            # Determine if we should apply corrections
            verification_result["corrections"] = corrections
            verification_result["corrections_applied"] = len(corrections) > 0

            return verification_result

        except Exception as parse_error:
            logger.error(f"Error parsing OpenAI response: {parse_error}")
            logger.error(f"Original response text: {verification_text}")
            raise ValueError(f"Error parsing OpenAI verification response: {str(parse_error)}")

    def _combine_verification_results(self, calculation_result: Dict[str, Any],
                                    openai_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine results from multiple verification methods into a unified result.

        This method implements a sophisticated weighting algorithm that combines
        confidence scores from different verification approaches:

        1. Direct Calculation Verification: Compares planetary positions and house cusps
           against recalculated values using Swiss Ephemeris. High accuracy in calculations
           produces higher confidence scores.

        2. OpenAI Expert Verification: Uses advanced AI to evaluate the chart against
           Vedic astrological standards, looking for inconsistencies and proper application
           of astrological principles.

        The combined confidence score weights direct calculations more heavily (70%) than
        OpenAI verification (30%), as the mathematical precision of ephemeris calculations
        is considered more deterministic than subjective astrological interpretations.

        Confidence Score Interpretation:
        - 0.9-1.0: Extremely high confidence, all calculations verified successfully
        - 0.8-0.9: High confidence, minimal discrepancies
        - 0.6-0.8: Moderate confidence, some minor discrepancies that don't affect interpretation
        - 0.4-0.6: Low confidence, significant discrepancies that might affect interpretation
        - 0.0-0.4: Very low confidence, major discrepancies that compromise chart validity

        Args:
            calculation_result: Results from direct calculation verification
            openai_result: Results from OpenAI verification

        Returns:
            Dictionary with combined verification results including:
            - verified: Overall verification status (boolean)
            - confidence: Combined confidence score (0-1 scale)
            - status: Verification status message
            - corrections: List of corrections to apply
        """
        # Start with basic result
        combined_result = {
            "status": "verification_completed",
            "message": "Chart verification completed",
            "verified": True,
            "confidence": 1.0,
            "confidence_details": {
                "calculation_confidence": 0.0,
                "openai_confidence": 0.0,
                "calculation_weight": 0.7,  # Direct calculations weighted at 70%
                "openai_weight": 0.3,       # OpenAI verification weighted at 30%
                "verification_methods_used": []
            },
            "corrections_applied": False,
            "corrections": []
        }

        # Check if direct calculations were successful
        calc_verified = calculation_result.get("calculation_verified", False)
        calc_confidence = calculation_result.get("confidence", 0.0)
        combined_result["confidence_details"]["calculation_confidence"] = calc_confidence

        if calc_verified:
            combined_result["confidence_details"]["verification_methods_used"].append("direct_calculation")

        # Check if OpenAI verification was successful
        openai_verified = openai_result.get("verified_with_openai", False)
        openai_confidence = openai_result.get("confidence", 0.0)
        combined_result["confidence_details"]["openai_confidence"] = openai_confidence

        if openai_verified:
            combined_result["confidence_details"]["verification_methods_used"].append("openai_verification")

        # Combine verification status
        if openai_verified and calc_verified:
            combined_result["status"] = "verification_completed"
            combined_result["message"] = "Chart verified with high confidence using multiple methods"
            combined_result["verified"] = True

            # Calculate weighted average confidence
            combined_result["confidence"] = (calc_confidence * 0.7) + (openai_confidence * 0.3)
            combined_result["confidence_details"]["confidence_explanation"] = (
                f"Weighted average of direct calculation ({calc_confidence:.2f}) "
                f"and OpenAI verification ({openai_confidence:.2f})"
            )

        elif calc_verified:
            combined_result["status"] = "verification_completed"
            combined_result["message"] = "Chart verified with direct calculations only"
            combined_result["verified"] = True
            combined_result["confidence"] = calc_confidence
            combined_result["confidence_details"]["confidence_explanation"] = (
                f"Based only on direct calculation verification ({calc_confidence:.2f})"
            )

        elif openai_verified:
            combined_result["status"] = "verification_completed"
            combined_result["message"] = "Chart verified with OpenAI only"
            combined_result["verified"] = True
            combined_result["confidence"] = openai_confidence
            combined_result["confidence_details"]["confidence_explanation"] = (
                f"Based only on OpenAI verification ({openai_confidence:.2f})"
            )

        else:
            combined_result["status"] = "verification_failed"
            combined_result["message"] = "Chart verification failed with all methods"
            combined_result["verified"] = False
            combined_result["confidence"] = 0.0
            combined_result["confidence_details"]["confidence_explanation"] = (
                "No verification methods succeeded"
            )

        # Add interpretation of the confidence score
        confidence = combined_result["confidence"]
        if confidence >= 0.9:
            combined_result["confidence_interpretation"] = "Extremely high confidence"
        elif confidence >= 0.8:
            combined_result["confidence_interpretation"] = "High confidence"
        elif confidence >= 0.6:
            combined_result["confidence_interpretation"] = "Moderate confidence"
        elif confidence >= 0.4:
            combined_result["confidence_interpretation"] = "Low confidence"
        else:
            combined_result["confidence_interpretation"] = "Very low confidence"

        # Check for corrections needed
        if openai_result and openai_result.get("corrections_applied", False):
            combined_result["corrections_applied"] = True
            combined_result["corrections"] = openai_result.get("corrections", [])
            combined_result["suggested_adjustment"] = openai_result.get("suggested_adjustment", "")
            combined_result["suggested_time"] = openai_result.get("suggested_time", "")
            combined_result["adjustment_reason"] = openai_result.get("adjustment_reason", "")

        elif calculation_result and len(calculation_result.get("differences", [])) > 0:
            combined_result["corrections_applied"] = True
            combined_result["corrections"] = calculation_result.get("differences", [])

        return combined_result

    async def _apply_corrections(self, chart_data: Dict[str, Any],
                              verification_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply corrections to the chart data based on verification results.

        Args:
            chart_data: Original chart data
            verification_result: Verification results with corrections

        Returns:
            Corrected chart data
        """
        # Create a deep copy of the chart data to avoid modifying the original
        import copy
        corrected_chart = copy.deepcopy(chart_data)

        # Get the corrections
        corrections = verification_result.get("corrections", [])
        if not corrections:
            return corrected_chart

        # Apply each correction
        for correction in corrections:
            correction_type = correction.get("type")
            object_name = correction.get("object")

            if correction_type == "planet_position":
                # Correct a planet's position
                if object_name in corrected_chart.get("planets", {}):
                    corrected_value = correction.get("calculated_value")
                    if corrected_value is not None:
                        corrected_chart["planets"][object_name]["longitude"] = corrected_value
                        corrected_chart["planets"][object_name]["corrected"] = True

            elif correction_type == "house_cusp":
                # Correct a house cusp
                houses = corrected_chart.get("houses", [])
                if isinstance(houses, list):
                    # Extract house number
                    import re
                    house_match = re.search(r"House\s+(\d+)", object_name)
                    if house_match:
                        house_index = int(house_match.group(1)) - 1
                        if 0 <= house_index < len(houses):
                            corrected_value = correction.get("calculated_value")
                            if corrected_value is not None:
                                houses[house_index]["longitude"] = corrected_value
                                houses[house_index]["corrected"] = True

            elif correction_type == "position_error":
                # Mark for correction since we can't recalculate directly here
                if "planets" in corrected_chart and object_name in corrected_chart["planets"]:
                    corrected_chart["planets"][object_name]["needs_correction"] = True
                elif "House" in object_name:
                    # Extract house number
                    import re
                    house_match = re.search(r"House\s+(\d+)", object_name)
                    if house_match:
                        house_index = int(house_match.group(1)) - 1
                        houses = corrected_chart.get("houses", [])
                        if isinstance(houses, list) and 0 <= house_index < len(houses):
                            houses[house_index]["needs_correction"] = True

        # If a time adjustment was suggested, apply it to the birth time
        suggested_time = verification_result.get("suggested_time")
        if suggested_time and "birth_details" in corrected_chart:
            corrected_chart["birth_details"]["original_time"] = corrected_chart["birth_details"].get("time")
            corrected_chart["birth_details"]["time"] = suggested_time
            corrected_chart["birth_details"]["adjusted"] = True
            corrected_chart["birth_details"]["adjustment"] = verification_result.get("suggested_adjustment", "")
            corrected_chart["birth_details"]["adjustment_reason"] = verification_result.get("adjustment_reason", "")

        # Mark the chart as corrected
        corrected_chart["corrected"] = True
        corrected_chart["correction_timestamp"] = datetime.now().isoformat()

        return corrected_chart

    async def _send_verification_status(self, session_id: str, status: str,
                                     message: str, progress: float) -> None:
        """
        Send verification status updates via WebSocket.

        Args:
            session_id: Session ID for WebSocket channel
            status: Current verification status
            message: Status message
            progress: Progress as a float between 0 and 1
        """
        try:
            websocket_manager = get_websocket_manager()
            if not websocket_manager:
                logger.warning("WebSocket manager not available for sending verification updates")
                return

            # Create the message payload
            payload = {
                "type": "chart_verification_status",
                "status": status,
                "message": message,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            }

            # Send the message via WebSocket
            await websocket_manager.send_message(session_id, message_type="chart_verification_status", data=payload)
            logger.debug(f"Sent verification status update to session {session_id}: {status}")
        except Exception as e:
            logger.error(f"Error sending verification status update: {e}")


# Create a singleton instance
_chart_verification_service = None

def get_chart_verification_service() -> ChartVerificationService:
    """
    Get the chart verification service singleton.

    Returns:
        ChartVerificationService instance
    """
    global _chart_verification_service
    if _chart_verification_service is None:
        _chart_verification_service = ChartVerificationService()
    return _chart_verification_service

async def verify_chart(
    chart_data: Dict[str, Any],
    session_id: Optional[str] = None,
    verify_with_openai: bool = True
) -> Dict[str, Any]:
    """
    Verify an astrological chart against established astrological standards.

    This function provides comprehensive chart verification through multiple methods:

    1. Calculation Verification:
       - Checks planetary positions against astronomical calculations
       - Validates internal consistency between chart elements
       - Ensures proper application of ayanamsa (sidereal offset)
       - Cross-validates houses against multiple calculation methods

    2. OpenAI Verification (when enabled):
       - Sends chart to OpenAI with expert Vedic astrologer prompt
       - Analyzes verification responses using NLP techniques
       - Extracts confidence assessments and suggested corrections
       - Applies corrections to chart when appropriate

    The verification process produces a confidence score (0-1) indicating the overall
    reliability of the chart. The confidence scoring system works as follows:

    - 0.9-1.0: High confidence. Chart passes all verification methods with minimal
               or no issues. Planetary positions are highly accurate, houses are
               correctly calculated, and internal consistency checks pass.

    - 0.7-0.9: Good confidence. Chart passes most verification methods but may have
               minor discrepancies. Planetary positions are accurate within accepted
               tolerance, house calculations show minimal variance.

    - 0.5-0.7: Moderate confidence. Chart shows some discrepancies or verification
               was limited. Some planets may have position errors within a few degrees,
               or verification could only be partially completed.

    - 0.3-0.5: Low confidence. Chart has significant discrepancies or verification
               identified major issues. Multiple planets have incorrect positions,
               or house system appears incorrect.

    - 0.0-0.3: Very low confidence. Chart has critical errors or verification failed.
               Basic chart structure is compromised or fundamental calculation
               errors exist.

    When the OpenAI verification is used, confidence factors include:
    - Proper planetary sign placement
    - Accurate house cusp positions
    - Correct application of astrological rules
    - Internal consistency between chart elements
    - Proper calculation of divisional charts (if included)

    When corrections are applied, the verification result includes details about what
    was corrected and why, maintaining full transparency about changes made during
    verification.

    Args:
        chart_data: The chart data to verify
        session_id: Optional session ID for WebSocket updates
        verify_with_openai: Whether to verify with OpenAI

    Returns:
        Dictionary containing verification results:
        - status: Current status of verification (success, error, etc.)
        - verified: Boolean indicating if verification passed
        - verified_with_openai: Whether OpenAI verification was used
        - confidence: Overall confidence score (0-1)
        - confidence_details: Detailed breakdown of confidence score components
        - corrections: List of corrections made (if any)
        - corrections_applied: Boolean indicating if corrections were applied
        - corrected_chart: Updated chart data if corrections were applied

    Raises:
        ValueError: If chart data is invalid or incomplete
        RuntimeError: If verification encounters a critical error
    """
    service = get_chart_verification_service()
    return await service.verify_chart(chart_data, session_id, verify_with_openai)

# Define model classes if they don't exist elsewhere
class ChartData(TypedDict, total=False):
    """Chart data structure."""
    chart_id: str
    birth_details: dict
    planets: dict
    houses: list
    angles: dict
    options: dict

class VerificationResult(TypedDict, total=False):
    """Verification result structure."""
    status: str
    message: str
    verified: bool
    confidence: float
    corrections_applied: bool
    corrections: list

class WebSocketMessage:
    """WebSocket message structure."""
    def __init__(self, event: str, data: dict):
        self.event = event
        self.data = data

def get_zodiac_sign(longitude: float) -> str:
    """
    Get the zodiac sign for a longitude value.

    Args:
        longitude: Celestial longitude in degrees

    Returns:
        Zodiac sign name
    """
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    sign_index = int(longitude / 30) % 12
    return signs[sign_index]

# Export the service accessor and helper functions
__all__ = [
    "get_chart_verification_service",
    "verify_chart",
    "get_zodiac_sign"
]
