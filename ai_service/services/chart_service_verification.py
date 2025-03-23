"""
Chart verification functionality for chart service.

This module provides functions for verifying astrological charts with OpenAI.
"""

import logging
import json
import asyncio
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

logger = logging.getLogger(__name__)

def verify_chart_with_openai(chart_data: Dict[str, Any], max_retries: int = 3,
                             fallback_provider: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Verify chart calculations using OpenAI with robust error recovery.

    Args:
        chart_data: Chart data to verify
        max_retries: Maximum number of verification attempts (default: 3)
        fallback_provider: Optional alternative AI provider to use if OpenAI fails

    Returns:
        Verified chart data with corrections, or None if verification failed
    """
    try:
        # Import OpenAI service
        from ai_service.services.openai_service import get_openai_service
        openai_service = get_openai_service()

        if not openai_service:
            logger.warning("OpenAI service not available for chart verification")

            # Try fallback AI provider if specified
            if fallback_provider:
                logger.info(f"Attempting verification with fallback provider: {fallback_provider}")
                return _verify_with_fallback_provider(chart_data, fallback_provider)

            # If no fallback, return original chart with warning
            chart_data["verification"] = {
                "verified_with_ai": False,
                "verification_date": datetime.now().isoformat(),
                "status": "unavailable",
                "message": "OpenAI service not available for verification",
                "confidence": 0
            }
            return chart_data

        logger.info("Verifying chart data with OpenAI")

        # Prepare chart data for verification
        verification_data = prepare_chart_for_verification(chart_data)

        # Set up retry logic with exponential backoff
        retry_count = 0
        verification_result = None
        last_error = None

        while retry_count < max_retries:
            try:
                # Call OpenAI service for verification
                verification_result = asyncio.run(openai_service.verify_chart(verification_data))
                if verification_result:
                    break

                # Exponential backoff between retries
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # 2, 4, 8 seconds
                    logger.info(f"Retry {retry_count}/{max_retries} for OpenAI verification in {wait_time} seconds")
                    time.sleep(wait_time)
            except Exception as e:
                last_error = e
                logger.warning(f"Verification attempt {retry_count+1} failed: {e}")

                # Exponential backoff between retries
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # 2, 4, 8 seconds
                    logger.info(f"Retry {retry_count}/{max_retries} for OpenAI verification in {wait_time} seconds")
                    time.sleep(wait_time)

        # If all retries failed, try fallback provider
        if retry_count >= max_retries and not verification_result:
            if fallback_provider:
                logger.info(f"OpenAI verification failed after {max_retries} attempts. "
                           f"Trying fallback provider: {fallback_provider}")
                return _verify_with_fallback_provider(chart_data, fallback_provider)
            else:
                logger.warning(f"Chart verification failed after {max_retries} attempts")
                chart_data["verification"] = {
                    "verified_with_ai": False,
                    "verification_date": datetime.now().isoformat(),
                    "status": "failed_retries",
                    "message": f"Verification failed after {max_retries} attempts: {str(last_error)}",
                    "confidence": 0
                }
                return chart_data

        # Process verification result
        if not verification_result:
            logger.warning("OpenAI chart verification returned no result")
            chart_data["verification"] = {
                "verified_with_ai": False,
                "verification_date": datetime.now().isoformat(),
                "status": "no_result",
                "message": "Verification process completed but returned no result",
                "confidence": 0
            }
            return chart_data

        # Check if corrections are needed
        corrections = verification_result.get("corrections", [])
        if corrections:
            logger.info(f"OpenAI suggested {len(corrections)} corrections to chart data")

            # Apply corrections
            corrected_chart = apply_corrections(chart_data, corrections)

            # Add verification data to chart
            corrected_chart["verification"] = {
                "verified_with_ai": True,
                "verification_date": datetime.now().isoformat(),
                "status": "verified_with_corrections",
                "confidence": verification_result.get("confidence", 0),
                "message": verification_result.get("message", ""),
                "corrections_applied": len(corrections),
                "corrections": corrections
            }

            # Validate the corrected chart for integrity
            if validate_corrected_chart(corrected_chart):
                return corrected_chart
            else:
                # If validation fails, log warning and return original with partial corrections
                logger.warning("Corrected chart validation failed, returning chart with partial corrections")
                chart_data["verification"] = {
                    "verified_with_ai": True,
                    "verification_date": datetime.now().isoformat(),
                    "status": "verified_with_partial_corrections",
                    "confidence": verification_result.get("confidence", 0) * 0.7,  # Reduce confidence
                    "message": "Some corrections could not be applied due to validation issues",
                    "corrections_applied": len(corrections),
                    "corrections": corrections
                }

                # Apply only safe corrections
                return apply_safe_corrections(chart_data, corrections)
        else:
            # No corrections needed
            chart_data["verification"] = {
                "verified_with_ai": True,
                "verification_date": datetime.now().isoformat(),
                "status": "verified_no_corrections",
                "confidence": verification_result.get("confidence", 100),
                "message": verification_result.get("message", "Chart verified, no corrections needed")
            }

            return chart_data

    except Exception as e:
        logger.error(f"Error verifying chart with OpenAI: {e}")

        # Return original chart data with error status
        chart_data["verification"] = {
            "verified_with_ai": False,
            "verification_date": datetime.now().isoformat(),
            "status": "error",
            "message": f"Verification error: {str(e)}",
            "confidence": 0
        }

        return chart_data

def _verify_with_fallback_provider(chart_data: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """
    Verify chart with a fallback AI provider when OpenAI is unavailable.

    Args:
        chart_data: Chart data to verify
        provider: Fallback provider name ('local', 'azure', etc.)

    Returns:
        Verified chart data
    """
    try:
        if provider == "local":
            # Use local verification logic based on astronomical algorithms
            return _verify_with_local_algorithms(chart_data)
        elif provider == "azure":
            # Use Azure OpenAI service
            from ai_service.services.azure_openai_service import get_azure_openai_service
            azure_service = get_azure_openai_service()
            if azure_service:
                verification_data = prepare_chart_for_verification(chart_data)
                result = asyncio.run(azure_service.verify_chart(verification_data))
                if result:
                    # Apply corrections if any
                    if result.get("corrections", []):
                        corrected_chart = apply_corrections(chart_data, result["corrections"])
                        corrected_chart["verification"] = {
                            "verified_with_ai": True,
                            "verification_provider": "azure",
                            "verification_date": datetime.now().isoformat(),
                            "status": "verified_with_corrections",
                            "confidence": result.get("confidence", 0),
                            "corrections_applied": len(result["corrections"]),
                            "corrections": result["corrections"]
                        }
                        return corrected_chart
                    else:
                        # No corrections needed
                        chart_data["verification"] = {
                            "verified_with_ai": True,
                            "verification_provider": "azure",
                            "verification_date": datetime.now().isoformat(),
                            "status": "verified_no_corrections",
                            "confidence": result.get("confidence", 100)
                        }
                        return chart_data

            # If Azure verification failed, fall back to local
            logger.warning("Azure verification failed, falling back to local algorithms")
            return _verify_with_local_algorithms(chart_data)
        else:
            logger.warning(f"Unknown fallback provider: {provider}, using local verification")
            return _verify_with_local_algorithms(chart_data)
    except Exception as e:
        logger.error(f"Error using fallback provider {provider}: {e}")
        # Return original data with fallback error status
        chart_data["verification"] = {
            "verified_with_ai": False,
            "verification_date": datetime.now().isoformat(),
            "status": "fallback_error",
            "message": f"Fallback verification error with {provider}: {str(e)}",
            "confidence": 0
        }
        return chart_data

def _verify_with_local_algorithms(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify chart using local astronomical algorithms without AI.

    Args:
        chart_data: Chart data to verify

    Returns:
        Verified chart data
    """
    try:
        # Import necessary components for local verification
        from ai_service.core.rectification.swisseph_direct import calculate_swiss_ephemeris_chart
        import swisseph as swe
        import pytz
        from datetime import datetime

        # Extract birth details
        birth_details = chart_data.get("birth_details", {})
        birth_date = birth_details.get("date", "")
        birth_time = birth_details.get("time", "")
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        timezone = birth_details.get("timezone", "UTC")

        if not (birth_date and birth_time):
            logger.warning("Insufficient birth details for local verification")
            return chart_data

        # Parse birth datetime
        birth_dt_str = f"{birth_date} {birth_time}"
        birth_dt_naive = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M:%S")

        # Get the timezone object
        tz = pytz.timezone(timezone)

        # Convert naive datetime to timezone-aware datetime
        birth_dt = tz.localize(birth_dt_naive)

        # Calculate chart using Swiss Ephemeris directly
        recalculated_chart = calculate_swiss_ephemeris_chart(
            birth_dt=birth_dt,
            latitude=latitude,
            longitude=longitude,
            house_system=chart_data.get("calculation_details", {}).get("house_system", "placidus"),
            is_sidereal=(chart_data.get("calculation_details", {}).get("chart_type", "").lower() == "vedic")
        )

        # Compare planets between original and recalculated chart
        corrections = []
        for planet_name, planet_data in chart_data.get("planets", {}).items():
            if planet_name in recalculated_chart.get("planets", {}):
                original_lon = planet_data.get("longitude", 0)
                recalc_lon = recalculated_chart["planets"][planet_name].get("longitude", 0)

                # Check if difference is significant (more than 0.5 degrees)
                difference = abs(original_lon - recalc_lon)
                if difference > 180:
                    difference = 360 - difference

                if difference > 0.5:
                    corrections.append({
                        "type": "planet_position",
                        "object": planet_name,
                        "original": original_lon,
                        "corrected": recalc_lon,
                        "explanation": f"Corrected {planet_name} longitude based on Swiss Ephemeris calculation"
                    })

        # Apply corrections if needed
        if corrections:
            corrected_chart = apply_corrections(chart_data, corrections)
            corrected_chart["verification"] = {
                "verified_with_ai": False,
                "verified_with_local": True,
                "verification_date": datetime.now().isoformat(),
                "status": "verified_with_local_corrections",
                "confidence": 85,  # Local verification is reliable but not as comprehensive as AI
                "corrections_applied": len(corrections),
                "corrections": corrections
            }
            return corrected_chart
        else:
            # No corrections needed
            chart_data["verification"] = {
                "verified_with_ai": False,
                "verified_with_local": True,
                "verification_date": datetime.now().isoformat(),
                "status": "verified_no_corrections",
                "confidence": 90
            }
            return chart_data
    except Exception as e:
        logger.error(f"Error in local verification: {e}")
        chart_data["verification"] = {
            "verified_with_ai": False,
            "verification_date": datetime.now().isoformat(),
            "status": "local_verification_error",
            "message": f"Local verification error: {str(e)}",
            "confidence": 0
        }
        return chart_data

def prepare_chart_for_verification(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare chart data for verification by extracting essential components.

    Args:
        chart_data: Full chart data

    Returns:
        Simplified chart data for verification
    """
    # Extract only the necessary parts to reduce token usage
    verification_data = {
        "chart_id": chart_data.get("chart_id", ""),
        "birth_details": chart_data.get("birth_details", {}),
        "planets": chart_data.get("planets", {}),
        "houses": chart_data.get("houses", []),
        "angles": chart_data.get("angles", {}),
        "calculation_details": chart_data.get("calculation_details", {})
    }

    return verification_data

def apply_corrections(chart_data: Dict[str, Any], corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply corrections to chart data.

    Args:
        chart_data: Original chart data
        corrections: List of corrections to apply

    Returns:
        Corrected chart data
    """
    # Make a copy to avoid modifying the original
    corrected_chart = chart_data.copy()

    # Keep track of applied corrections
    corrected_values = []

    # Apply each correction
    for correction in corrections:
        correction_type = correction.get("type", "")
        object_name = correction.get("object", "")
        original_value = correction.get("original", "")
        corrected_value = correction.get("corrected", "")
        explanation = correction.get("explanation", "")

        # Apply correction based on type
        corrected = False

        if correction_type == "planet_position" and object_name in corrected_chart.get("planets", {}):
            # Store original data for reference
            original_longitude = corrected_chart["planets"][object_name].get("longitude", 0)
            corrected_chart["planets"][object_name]["original_longitude"] = original_longitude

            # Update planet position
            try:
                corrected_chart["planets"][object_name]["longitude"] = float(corrected_value)
                corrected_chart["planets"][object_name]["ai_corrected"] = True

                # Update sign based on corrected longitude
                corrected_longitude = float(corrected_value)
                sign_num = int(corrected_longitude / 30) % 12
                signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                corrected_chart["planets"][object_name]["sign"] = signs[sign_num]

                corrected = True
                logger.info(f"Corrected planet {object_name} longitude from {original_longitude} to {corrected_value}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not apply correction to planet {object_name}: {e}")

        elif correction_type == "house_cusp" and corrected_chart.get("houses"):
            try:
                house_num = int(object_name)
                if 1 <= house_num <= len(corrected_chart["houses"]):
                    # Check if houses is a list of floats or a list of dicts
                    if isinstance(corrected_chart["houses"][house_num-1], dict):
                        original_longitude = corrected_chart["houses"][house_num-1].get("longitude", 0)
                        corrected_chart["houses"][house_num-1]["original_longitude"] = original_longitude
                        corrected_chart["houses"][house_num-1]["longitude"] = float(corrected_value)
                        corrected_chart["houses"][house_num-1]["ai_corrected"] = True

                        # Update sign based on corrected longitude
                        corrected_longitude = float(corrected_value)
                        sign_num = int(corrected_longitude / 30) % 12
                        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                        corrected_chart["houses"][house_num-1]["sign"] = signs[sign_num]
                    else:
                        # Houses is a list of longitudes
                        original_longitude = corrected_chart["houses"][house_num-1]
                        corrected_chart["houses"][house_num-1] = float(corrected_value)

                    corrected = True
                    logger.info(f"Corrected house {house_num} from {original_longitude} to {corrected_value}")
            except (ValueError, IndexError, TypeError) as e:
                logger.warning(f"Could not apply house correction for {object_name}: {e}")

        elif correction_type == "angle" and object_name.lower() in [a.lower() for a in corrected_chart.get("angles", {})]:
            # Find the actual key using case-insensitive match
            angle_key = next((k for k in corrected_chart.get("angles", {}) if k.lower() == object_name.lower()), object_name)

            # Store original data for reference
            original_longitude = corrected_chart["angles"][angle_key].get("longitude", 0)
            corrected_chart["angles"][angle_key]["original_longitude"] = original_longitude

            try:
                # Update angle position
                corrected_chart["angles"][angle_key]["longitude"] = float(corrected_value)
                corrected_chart["angles"][angle_key]["ai_corrected"] = True

                # Update sign based on corrected longitude
                corrected_longitude = float(corrected_value)
                sign_num = int(corrected_longitude / 30) % 12
                signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                corrected_chart["angles"][angle_key]["sign"] = signs[sign_num]

                corrected = True
                logger.info(f"Corrected angle {angle_key} from {original_longitude} to {corrected_value}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not apply correction to angle {angle_key}: {e}")

        # If correction was applied, add to tracking list
        if corrected:
            corrected_values.append({
                "type": correction_type,
                "object": object_name,
                "original": original_value,
                "corrected": corrected_value,
                "explanation": explanation
            })

    # Recalculate derived data if corrections were made
    if corrected_values:
        # Recalculate aspects
        try:
            from ai_service.services.chart_service_aspects import calculate_aspects
            corrected_chart["aspects"] = calculate_aspects(corrected_chart)
        except Exception as aspect_error:
            logger.warning(f"Failed to recalculate aspects after corrections: {str(aspect_error)}")

        # Recalculate dignities
        try:
            from ai_service.services.chart_service_dignities import calculate_dignities
            corrected_chart["dignities"] = calculate_dignities(corrected_chart)
        except Exception as dignity_error:
            logger.warning(f"Failed to recalculate dignities after corrections: {str(dignity_error)}")

        # Recalculate strengths
        try:
            from ai_service.services.chart_service_dignities import calculate_planet_strengths
            corrected_chart["strengths"] = calculate_planet_strengths(corrected_chart)
        except Exception as strength_error:
            logger.warning(f"Failed to recalculate planet strengths after corrections: {str(strength_error)}")

    return corrected_chart

def apply_safe_corrections(chart_data: Dict[str, Any], corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply only safe corrections to chart data when full validation fails.

    Args:
        chart_data: Original chart data
        corrections: List of all proposed corrections

    Returns:
        Chart with only safe corrections applied
    """
    # Define which correction types are considered safer
    safe_correction_types = ["planet_position"]

    # Filter to only apply corrections of safe types
    safe_corrections = [c for c in corrections if c.get("type", "") in safe_correction_types]

    if safe_corrections:
        logger.info(f"Applying {len(safe_corrections)} safe corrections out of {len(corrections)} total")
        return apply_corrections(chart_data, safe_corrections)
    else:
        # No safe corrections to apply
        logger.warning("No safe corrections available, returning original chart")
        chart_data["verification"] = {
            "verified_with_ai": True,
            "verification_date": datetime.now().isoformat(),
            "status": "verification_failed",
            "message": "No safe corrections could be applied",
            "confidence": 0
        }
        return chart_data

def validate_corrected_chart(chart_data: Dict[str, Any]) -> bool:
    """
    Validate that the corrected chart maintains data integrity.

    Args:
        chart_data: Corrected chart data to validate

    Returns:
        True if validation passes, False if issues detected
    """
    try:
        # Check that all planets have the required fields
        for planet_name, planet_data in chart_data.get("planets", {}).items():
            if not isinstance(planet_data, dict):
                logger.warning(f"Invalid planet data format for {planet_name}")
                return False

            required_fields = ["longitude", "sign"]
            for field in required_fields:
                if field not in planet_data:
                    logger.warning(f"Missing required field {field} for planet {planet_name}")
                    return False

            # Validate longitude is in valid range
            try:
                longitude = float(planet_data.get("longitude", 0))
                if not (0 <= longitude < 360):
                    logger.warning(f"Invalid longitude {longitude} for planet {planet_name}")
                    return False
            except (ValueError, TypeError):
                logger.warning(f"Invalid longitude value for planet {planet_name}")
                return False

        # Check house data integrity
        houses = chart_data.get("houses", [])
        if not houses or len(houses) != 12:
            logger.warning(f"Invalid house data: expected 12 houses, got {len(houses)}")
            return False

        # Check that house cusps form a valid sequence
        house_longitudes = []
        for i, house in enumerate(houses):
            if isinstance(house, dict):
                if "longitude" not in house:
                    logger.warning(f"Missing longitude for house {i+1}")
                    return False
                house_longitudes.append(house.get("longitude", 0))
            elif isinstance(house, (int, float)):
                house_longitudes.append(house)
            else:
                logger.warning(f"Invalid house data format for house {i+1}")
                return False

        # Houses should usually be in increasing order (not always, but often)
        # This is a simple check that could be improved
        problems = 0
        for i in range(len(house_longitudes)-1):
            if house_longitudes[i] > house_longitudes[i+1] and house_longitudes[i+1] > 30:
                problems += 1

        if problems > 1:  # Allow one potential wrap around 0/360
            logger.warning("House sequence appears invalid")
            return False

        return True
    except Exception as e:
        logger.error(f"Error validating corrected chart: {e}")
        return False
