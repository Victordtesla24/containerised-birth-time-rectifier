"""
Chart calculation functionality for chart service.

This module provides functions for calculating astrological charts.
"""

import os
import json
import asyncio
import traceback
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
import re

from ai_service.services.chart_service_aspects import calculate_aspects
from ai_service.services.chart_service_dignities import calculate_dignities, calculate_planet_strengths
from ai_service.services.chart_service_utils import determine_house_for_longitude, calculate_arc_difference
from ai_service.utils.timezone import get_timezone_info, convert_to_timezone, validate_timezone
from ai_service.core.rectification.chart_calculator import calculate_chart as core_calculate_chart

logger = logging.getLogger(__name__)

def calculate_chart(birth_date: str, birth_time: str, latitude: float, longitude: float,
                    timezone: str, chart_type: str = "vedic", house_system: str = "placidus",
                    verify_with_openai: bool = True, include_divisional: bool = True) -> Dict[str, Any]:
    """
    Calculate an astrological chart with optional verification.

    Args:
        birth_date: Birth date in ISO format (YYYY-MM-DD)
        birth_time: Birth time in format HH:MM:SS
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string (IANA format, e.g., 'America/New_York')
        chart_type: Type of chart to calculate (vedic or tropical)
        house_system: House system to use
        verify_with_openai: Whether to verify the chart with OpenAI
        include_divisional: Whether to include divisional charts (for Vedic only)

    Returns:
        Dictionary with chart data
    """
    import pytz
    from ai_service.utils.timezone import get_timezone_for_coordinates

    logger.info(f"Calculating chart for {birth_date} {birth_time} at {latitude}, {longitude} in timezone {timezone}")

    try:
        # Validate timezone or use a default
        if not timezone or not validate_timezone(timezone):
            logger.warning(f"Invalid timezone {timezone}, inferring from coordinates")
            try:
                timezone = get_timezone_for_coordinates(latitude, longitude)
                logger.info(f"Using inferred timezone: {timezone}")
            except Exception as tz_error:
                logger.warning(f"Could not determine timezone from coordinates: {tz_error}")
                timezone = "UTC"
                logger.info(f"Falling back to UTC timezone")

        # Ensure birth_date is in ISO format
        if birth_date and not re.match(r'^\d{4}-\d{2}-\d{2}$', birth_date):
            try:
                # Try to parse and convert to ISO format
                parsed_date = datetime.strptime(birth_date, "%m/%d/%Y")
                birth_date = parsed_date.strftime("%Y-%m-%d")
                logger.info(f"Converted birth date to ISO format: {birth_date}")
            except ValueError:
                logger.warning(f"Could not parse birth date: {birth_date}")
                raise ValueError(f"Invalid birth date format: {birth_date}. Use YYYY-MM-DD format.")

        # Parse birth date and time to create datetime object
        try:
            # Handle both HH:MM:SS and HH:MM formats
            if re.match(r'^\d{2}:\d{2}:\d{2}$', birth_time):
                birth_dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M:%S")
            elif re.match(r'^\d{2}:\d{2}$', birth_time):
                birth_dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
            else:
                raise ValueError(f"Invalid birth time format: {birth_time}. Use HH:MM:SS or HH:MM format.")

            # Create timezone-aware datetime using proper localization
            tz = pytz.timezone(timezone)
            birth_dt = tz.localize(birth_dt)

            logger.info(f"Parsed birth datetime: {birth_dt} with timezone {timezone}")
        except ValueError as ve:
            logger.error(f"Error parsing birth date/time: {ve}")
            raise ValueError(f"Invalid birth date/time: {birth_date} {birth_time}. {str(ve)}")
        except pytz.exceptions.UnknownTimeZoneError:
            logger.error(f"Unknown timezone: {timezone}")
            raise ValueError(f"Unknown timezone: {timezone}")

        # Multi-library approach for redundancy and accuracy
        charts_data = []
        calculation_errors = []

        # First calculation method: Primary calculations
        try:
            # Initialize calculation libraries based on chart type
            if chart_type.lower() == "vedic":
                # Use Vedic calculation methods
                from ai_service.core.rectification.vedic_calculation import calculate_vedic_chart

                # Calculate the Vedic chart
                primary_chart_data = calculate_vedic_chart(
                    birth_dt=birth_dt,
                    latitude=latitude,
                    longitude=longitude,
                    house_system=house_system
                )
                charts_data.append(("primary_vedic", primary_chart_data))
            else:
                # Use tropical/western calculation methods
                primary_chart_data = core_calculate_chart(
                    birth_dt=birth_dt,
                    latitude=latitude,
                    longitude=longitude,
                    timezone_str=timezone
                )
                charts_data.append(("primary_tropical", primary_chart_data))
        except Exception as e:
            error_msg = f"Primary calculation method failed: {str(e)}"
            logger.error(error_msg)
            calculation_errors.append(error_msg)
            primary_chart_data = None

        # Second calculation method: Swiss Ephemeris direct (for verification)
        try:
            from ai_service.core.rectification.swisseph_direct import calculate_swiss_ephemeris_chart
            swiss_chart_data = calculate_swiss_ephemeris_chart(
                birth_dt=birth_dt,
                latitude=latitude,
                longitude=longitude,
                house_system=house_system,
                is_sidereal=(chart_type.lower() == "vedic")
            )
            charts_data.append(("swiss_ephemeris", swiss_chart_data))
        except Exception as e:
            error_msg = f"Swiss Ephemeris calculation failed: {str(e)}"
            logger.error(error_msg)
            calculation_errors.append(error_msg)

        # Third calculation method: Flatlib (backup calculation)
        try:
            from ai_service.utils.flatlib_compat import calculate_flatlib_chart
            flatlib_chart_data = calculate_flatlib_chart(
                birth_dt=birth_dt,
                latitude=latitude,
                longitude=longitude,
                house_system=house_system
            )
            charts_data.append(("flatlib", flatlib_chart_data))
        except Exception as e:
            error_msg = f"Flatlib calculation failed: {str(e)}"
            logger.error(error_msg)
            calculation_errors.append(error_msg)

        # Verify we have at least one successful calculation
        if not charts_data:
            raise ValueError(f"All calculation methods failed: {', '.join(calculation_errors)}")

        # Cross-validate calculations if we have multiple methods
        # Start with the primary method's results, or the first available results
        if primary_chart_data:
            chart_data = primary_chart_data
        else:
            chart_data = charts_data[0][1]

        # Add cross-validation data if we have multiple sources
        if len(charts_data) > 1:
            validation_results = cross_validate_calculations(charts_data)
            chart_data["cross_validation"] = validation_results

            # Add confidence score based on cross-validation
            validation_confidence = validation_results.get("confidence_score", 0)
            chart_data["calculation_confidence"] = validation_confidence

            # Apply corrections from cross-validation if needed
            if validation_results.get("corrections"):
                logger.info(f"Applying {len(validation_results['corrections'])} corrections from cross-validation")
                for correction in validation_results["corrections"]:
                    object_name = correction.get("object")
                    corrected_value = correction.get("corrected_value")
                    if object_name in chart_data.get("planets", {}):
                        chart_data["planets"][object_name]["longitude"] = corrected_value
                        chart_data["planets"][object_name]["corrected_by"] = "cross_validation"

        # Generate a chart ID if not already present
        if "chart_id" not in chart_data:
            chart_id = f"chart_{uuid.uuid4().hex[:8]}"
            chart_data["chart_id"] = chart_id

        # Add birth details to the chart data
        chart_data["birth_details"] = {
            "date": birth_date,
            "time": birth_time,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "location": chart_data.get("location", "Unknown")
        }

        # Add calculation details
        chart_data["calculation_details"] = {
            "chart_type": chart_type,
            "house_system": house_system,
            "calculated_at": datetime.now().isoformat(),
            "calculation_version": "3.0",
            "calculation_methods": [method for method, _ in charts_data],
            "calculation_errors": calculation_errors if calculation_errors else None
        }

        # Calculate aspects between planets
        try:
            chart_data["aspects"] = calculate_aspects(chart_data)
        except Exception as aspect_error:
            logger.error(f"Error calculating aspects: {aspect_error}")
            chart_data["aspects"] = []
            chart_data["calculation_errors"] = chart_data.get("calculation_errors", []) + [f"Aspect calculation failed: {str(aspect_error)}"]

        # Calculate dignities and debilities
        try:
            chart_data["dignities"] = calculate_dignities(chart_data)
        except Exception as dignity_error:
            logger.error(f"Error calculating dignities: {dignity_error}")
            chart_data["dignities"] = {}
            chart_data["calculation_errors"] = chart_data.get("calculation_errors", []) + [f"Dignity calculation failed: {str(dignity_error)}"]

        # Calculate strength scores for planets
        try:
            chart_data["strengths"] = calculate_planet_strengths(chart_data)
        except Exception as strength_error:
            logger.error(f"Error calculating planet strengths: {strength_error}")
            chart_data["strengths"] = {}
            chart_data["calculation_errors"] = chart_data.get("calculation_errors", []) + [f"Strength calculation failed: {str(strength_error)}"]

        # Calculate divisional charts if Vedic and include_divisional is True
        if chart_type.lower() == "vedic" and include_divisional:
            try:
                chart_data["divisional_charts"] = calculate_divisional_charts(chart_data)
            except Exception as div_error:
                logger.error(f"Error calculating divisional charts: {div_error}")
                chart_data["divisional_charts"] = {}
                chart_data["calculation_errors"] = chart_data.get("calculation_errors", []) + [f"Divisional chart calculation failed: {str(div_error)}"]

        # Verify the chart with OpenAI if requested
        if verify_with_openai:
            from ai_service.services.chart_service_verification import verify_chart_with_openai
            verification_result = None

            try:
                # Try to get event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If event loop is running, use run_coroutine_threadsafe
                        # with a reasonable timeout
                        logger.info("Using running event loop for verification")
                        future = asyncio.run_coroutine_threadsafe(
                            _async_verify_with_openai(chart_data),
                            loop
                        )
                        # Add a timeout of 20 seconds to prevent hanging
                        verified_chart_data = future.result(timeout=20)
                    else:
                        # If not in a running event loop, use asyncio.run with timeout
                        logger.info("Using asyncio.run for verification")
                        # Create a task with timeout
                        async def run_with_timeout():
                            return await asyncio.wait_for(_async_verify_with_openai(chart_data), timeout=20)

                        verified_chart_data = asyncio.run(run_with_timeout())
                except (RuntimeError, asyncio.TimeoutError) as e:
                    # If we have a timeout or runtime error, log and continue without verification
                    logger.warning(f"Verification timed out or runtime error: {e}")
                    verified_chart_data = None
                    verification_result = {
                        "verified": False,
                        "confidence": 0,
                        "status": "timeout",
                        "message": f"Verification timed out: {str(e)}"
                    }

                # If verification succeeded, update our chart data
                if verified_chart_data is not None:
                    # Apply OpenAI corrections to the chart data
                    chart_data = verified_chart_data
                    verification_result = chart_data.get("verification", {})

                    # If corrections were made, update divisional charts accordingly
                    if chart_type.lower() == "vedic" and include_divisional and "divisional_charts" in chart_data:
                        if verification_result.get("corrections_applied", 0) > 0:
                            logger.info("Recalculating divisional charts after OpenAI corrections")
                            chart_data["divisional_charts"] = calculate_divisional_charts(chart_data)
                else:
                    # Handle the case where verification returns None
                    logger.warning("OpenAI verification returned None, using unverified chart")
                    verification_result = {
                        "verified": False,
                        "confidence": 0,
                        "status": "failed",
                        "message": "Verification returned no result"
                    }
            except Exception as retry_error:
                # Handle any errors during verification
                logger.error(f"Error during chart verification: {retry_error}")
                logger.error(traceback.format_exc())
                verification_result = {
                    "verified": False,
                    "confidence": 0,
                    "status": "error",
                    "message": f"Verification error: {str(retry_error)}"
                }

        # Add verification data to chart
        chart_data["verification"] = verification_result

        # Return the calculated chart data
        return chart_data

    except Exception as e:
        logger.error(f"Error calculating chart: {str(e)}")
        logger.error(traceback.format_exc())
        raise

async def _async_verify_with_openai(chart_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Asynchronously verify chart with OpenAI.

    Args:
        chart_data: Chart data to verify

    Returns:
        Verified chart data or None if verification failed
    """
    try:
        # Import only when needed
        from ai_service.services.chart_service_verification import verify_chart_with_openai

        # Add a timeout to prevent hanging
        result = await asyncio.wait_for(
            asyncio.create_task(_do_verification(chart_data)),
            timeout=15  # 15 second timeout for verification
        )
        return result
    except asyncio.TimeoutError:
        logger.warning("OpenAI verification timed out after 15 seconds")
        return None
    except Exception as e:
        logger.error(f"Error during OpenAI verification: {e}")
        return None

async def _do_verification(chart_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Perform the actual verification without timeouts.
    This allows proper separation of concerns for error handling.

    Args:
        chart_data: Chart data to verify

    Returns:
        Verified chart data or None if verification failed
    """
    from ai_service.services.chart_service_verification import verify_chart_with_openai
    return await verify_chart_with_openai(chart_data)

def cross_validate_calculations(charts_data: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Cross-validate chart calculations from multiple sources.

    Args:
        charts_data: List of tuples with (source_name, chart_data)

    Returns:
        Dictionary with validation results
    """
    validation_results = {
        "sources": [source for source, _ in charts_data],
        "comparisons": [],
        "corrections": [],
        "confidence_score": 0
    }

    # If only one source, no validation needed
    if len(charts_data) < 2:
        validation_results["confidence_score"] = 70  # Moderate confidence by default
        return validation_results

    # Extract planetary positions from each source
    planet_positions = {}
    for source, chart in charts_data:
        planets = chart.get("planets", {})
        for planet_name, planet_data in planets.items():
            if planet_name not in planet_positions:
                planet_positions[planet_name] = []

            # Store position with source
            planet_positions[planet_name].append({
                "source": source,
                "longitude": planet_data.get("longitude", 0),
                "data": planet_data
            })

    # Calculate discrepancies and consensus
    total_discrepancy = 0
    total_comparisons = 0

    for planet_name, positions in planet_positions.items():
        if len(positions) < 2:
            continue

        # Compare all pairs of sources
        for i in range(len(positions)):
            for j in range(i+1, len(positions)):
                pos1 = positions[i]["longitude"]
                pos2 = positions[j]["longitude"]
                source1 = positions[i]["source"]
                source2 = positions[j]["source"]

                # Calculate angular difference
                diff = calculate_arc_difference(pos1, pos2)

                # Add to comparisons
                validation_results["comparisons"].append({
                    "planet": planet_name,
                    "source1": source1,
                    "source2": source2,
                    "longitude1": pos1,
                    "longitude2": pos2,
                    "difference": diff
                })

                # Update total discrepancy
                total_discrepancy += diff
                total_comparisons += 1

    # Calculate average discrepancy and confidence score
    if total_comparisons > 0:
        avg_discrepancy = total_discrepancy / total_comparisons

        # Convert to confidence score (0-100)
        # High discrepancy = low confidence
        # Example: 0° discrepancy = 100 confidence, 5° = 50 confidence
        confidence = max(0, min(100, 100 - avg_discrepancy * 10))
        validation_results["confidence_score"] = confidence
        validation_results["average_discrepancy"] = avg_discrepancy
    else:
        # Default confidence if no comparisons were made
        validation_results["confidence_score"] = 50

    return validation_results

def calculate_divisional_charts(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate divisional charts (Varga charts) used in Vedic astrology.

    This method implements proper divisional chart calculations including:
    - D1 (Rashi) - Main birth chart
    - D9 (Navamsa) - Marriage, partner, general fortune
    - D3 (Drekkana) - Siblings, courage
    - D7 (Saptamsa) - Children, progeny
    - D10 (Dashamsha) - Career, profession
    - D12 (Dwadashamsha) - Parents, ancestry
    - D30 (Trimsamsha) - Misfortunes, challenges
    - D60 (Shashtyamsha) - General karmic indications

    Args:
        chart_data: Dictionary containing the birth chart data

    Returns:
        Dictionary of divisional charts with their respective data

    Raises:
        ValueError: If chart_data is invalid or missing required components
    """
    import copy

    # Validate input chart data
    if not chart_data or not isinstance(chart_data, dict):
        raise ValueError("Invalid chart data provided for divisional chart calculation")

    # Check for required elements
    if "planets" not in chart_data:
        raise ValueError("Chart data missing planetary positions")

    # Define zodiac signs for reference
    ZODIAC_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    # Initialize result dictionary with D1 (birth chart) as a reference
    divisional_charts = {
        "D1": copy.deepcopy(chart_data)
    }
    divisional_charts["D1"]["varga_type"] = "D1"
    divisional_charts["D1"]["varga_name"] = "Rashi"

    # Dictionary to track calculation functions for each divisional chart
    divisional_calculators = {
        "D9": calculate_navamsa_chart,
        "D3": calculate_drekkana_chart,
        "D7": calculate_saptamsa_chart,
        "D10": calculate_dashamsha_chart,
        "D12": calculate_dwadashamsha_chart,
        "D30": calculate_trimsamsha_chart,
    }

    # Calculate each divisional chart
    for varga_code, calculator_func in divisional_calculators.items():
        try:
            divisional_charts[varga_code] = calculator_func(chart_data)
        except Exception as e:
            logger.warning(f"Error calculating {varga_code} chart: {e}")
            # Create a minimal placeholder chart
            divisional_charts[varga_code] = {
                "varga_type": varga_code,
                "varga_name": get_varga_name(varga_code),
                "planets": copy.deepcopy(chart_data.get("planets", {})),
                "houses": copy.deepcopy(chart_data.get("houses", [])),
                "calculation_error": str(e)
            }

    return divisional_charts

def calculate_navamsa_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate D9 (Navamsa) chart.

    Args:
        chart_data: Base chart data

    Returns:
        D9 chart data
    """
    import copy

    # Create a deep copy of the chart data
    d9_chart = copy.deepcopy(chart_data)
    d9_chart["varga_type"] = "D9"
    d9_chart["varga_name"] = "Navamsa"

    # Define zodiac signs
    ZODIAC_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    # Process planets for D9
    for planet_name, planet_data in d9_chart["planets"].items():
        if "longitude" not in planet_data:
            continue

        # Get original longitude
        longitude = planet_data["longitude"]

        # Calculate navamsa (1/9th division of sign)
        sign_num = int(longitude / 30)
        pos_in_sign = longitude % 30
        navamsa_num = int(pos_in_sign / 3.333333)

        # Determine new sign based on original sign and navamsa
        # Different calculation methods for odd and even signs
        if sign_num % 2 == 0:  # Odd signs (0-based indexing: Aries, Gemini, etc.)
            new_sign_num = (sign_num * 3 + navamsa_num) % 12
        else:  # Even signs (0-based indexing: Taurus, Cancer, etc.)
            new_sign_num = (sign_num * 3 + 9 - navamsa_num) % 12

        # Calculate new longitude
        new_longitude = new_sign_num * 30 + (pos_in_sign % 3.333333) * 9

        # Update planet data
        planet_data["original_longitude"] = longitude
        planet_data["longitude"] = new_longitude
        planet_data["sign"] = ZODIAC_SIGNS[new_sign_num]

        # Recalculate house position if houses are defined
        if "houses" in d9_chart:
            planet_data["house"] = determine_house_for_longitude(d9_chart["houses"], new_longitude)

    # Calculate aspects for the D9 chart
    try:
        d9_chart["aspects"] = calculate_aspects(d9_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate aspects for D9 chart: {e}")
        d9_chart["aspects"] = []

    # Calculate dignities for the D9 chart
    try:
        d9_chart["dignities"] = calculate_dignities(d9_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate dignities for D9 chart: {e}")
        d9_chart["dignities"] = {}

    return d9_chart

def calculate_drekkana_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate D3 (Drekkana) chart.

    Args:
        chart_data: Base chart data

    Returns:
        D3 chart data
    """
    import copy

    # Create a deep copy of the chart data
    d3_chart = copy.deepcopy(chart_data)
    d3_chart["varga_type"] = "D3"
    d3_chart["varga_name"] = "Drekkana"

    # Define zodiac signs
    ZODIAC_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    # Process planets for D3
    for planet_name, planet_data in d3_chart["planets"].items():
        if "longitude" not in planet_data:
            continue

        # Get original longitude
        longitude = planet_data["longitude"]

        # Calculate drekkana (1/3rd division of sign)
        sign_num = int(longitude / 30)
        pos_in_sign = longitude % 30
        drekkana_num = int(pos_in_sign / 10)

        # Determine new sign based on original sign and drekkana
        # For fire signs (Aries, Leo, Sagittarius)
        if sign_num in [0, 4, 8]:
            new_sign_num = (sign_num + drekkana_num * 4) % 12
        # For earth signs (Taurus, Virgo, Capricorn)
        elif sign_num in [1, 5, 9]:
            new_sign_num = ((sign_num + drekkana_num * 4) + 8) % 12
        # For air signs (Gemini, Libra, Aquarius)
        elif sign_num in [2, 6, 10]:
            new_sign_num = ((sign_num + drekkana_num * 4) + 4) % 12
        # For water signs (Cancer, Scorpio, Pisces)
        else:
            new_sign_num = (sign_num + drekkana_num * 4) % 12

        # Calculate new longitude
        new_longitude = new_sign_num * 30 + (pos_in_sign % 10) * 3

        # Update planet data
        planet_data["original_longitude"] = longitude
        planet_data["longitude"] = new_longitude
        planet_data["sign"] = ZODIAC_SIGNS[new_sign_num]

        # Recalculate house position if houses are defined
        if "houses" in d3_chart:
            planet_data["house"] = determine_house_for_longitude(d3_chart["houses"], new_longitude)

    # Calculate aspects for the D3 chart
    try:
        d3_chart["aspects"] = calculate_aspects(d3_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate aspects for D3 chart: {e}")
        d3_chart["aspects"] = []

    # Calculate dignities for the D3 chart
    try:
        d3_chart["dignities"] = calculate_dignities(d3_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate dignities for D3 chart: {e}")
        d3_chart["dignities"] = {}

    return d3_chart

def calculate_saptamsa_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate D7 (Saptamsa) chart - related to children and progeny.

    Args:
        chart_data: Base chart data

    Returns:
        D7 chart data
    """
    import copy

    # Create a deep copy of the chart data
    d7_chart = copy.deepcopy(chart_data)
    d7_chart["varga_type"] = "D7"
    d7_chart["varga_name"] = "Saptamsa"

    # Define zodiac signs
    ZODIAC_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    # Process planets for D7
    for planet_name, planet_data in d7_chart["planets"].items():
        if "longitude" not in planet_data:
            continue

        # Get original longitude
        longitude = planet_data["longitude"]

        # Calculate saptamsa (1/7th division of sign)
        sign_num = int(longitude / 30)
        pos_in_sign = longitude % 30
        saptamsa_num = int(pos_in_sign / 4.285714)  # 30/7 = 4.285714 degrees per division

        # Different calculations for odd and even signs
        if sign_num % 2 == 0:  # Odd signs (0-based indexing)
            # For odd signs, start from the current sign and move forward
            new_sign_num = (sign_num + saptamsa_num) % 12
        else:  # Even signs (0-based indexing)
            # For even signs, start from 7th from the current sign and move forward
            new_sign_num = (sign_num + 6 + saptamsa_num) % 12

        # Calculate new longitude
        new_longitude = new_sign_num * 30 + (pos_in_sign % 4.285714) * 7

        # Update planet data
        planet_data["original_longitude"] = longitude
        planet_data["longitude"] = new_longitude
        planet_data["sign"] = ZODIAC_SIGNS[new_sign_num]

        # Recalculate house position if houses are defined
        if "houses" in d7_chart:
            planet_data["house"] = determine_house_for_longitude(d7_chart["houses"], new_longitude)

    # Calculate aspects for the D7 chart
    try:
        d7_chart["aspects"] = calculate_aspects(d7_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate aspects for D7 chart: {e}")
        d7_chart["aspects"] = []

    # Calculate dignities for the D7 chart
    try:
        d7_chart["dignities"] = calculate_dignities(d7_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate dignities for D7 chart: {e}")
        d7_chart["dignities"] = {}

    return d7_chart

def calculate_dashamsha_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate D10 (Dashamsha) chart - related to career and profession.

    Args:
        chart_data: Base chart data

    Returns:
        D10 chart data
    """
    import copy

    # Create a deep copy of the chart data
    d10_chart = copy.deepcopy(chart_data)
    d10_chart["varga_type"] = "D10"
    d10_chart["varga_name"] = "Dashamsha"

    # Define zodiac signs
    ZODIAC_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    # Process planets for D10
    for planet_name, planet_data in d10_chart["planets"].items():
        if "longitude" not in planet_data:
            continue

        # Get original longitude
        longitude = planet_data["longitude"]

        # Calculate dashamsha (1/10th division of sign)
        sign_num = int(longitude / 30)
        pos_in_sign = longitude % 30
        dashamsha_num = int(pos_in_sign / 3.0)  # 30/10 = 3 degrees per division

        # Different calculations for different sign types
        sign_element = sign_num % 4  # 0=Fire, 1=Earth, 2=Air, 3=Water

        if sign_element == 0:  # Fire signs (Aries, Leo, Sagittarius)
            new_sign_num = (sign_num + dashamsha_num) % 12
        elif sign_element == 1:  # Earth signs (Taurus, Virgo, Capricorn)
            new_sign_num = (sign_num + 9 + dashamsha_num) % 12
        elif sign_element == 2:  # Air signs (Gemini, Libra, Aquarius)
            new_sign_num = (sign_num + 6 + dashamsha_num) % 12
        else:  # Water signs (Cancer, Scorpio, Pisces)
            new_sign_num = (sign_num + 3 + dashamsha_num) % 12

        # Calculate new longitude
        new_longitude = new_sign_num * 30 + (pos_in_sign % 3.0) * 10

        # Update planet data
        planet_data["original_longitude"] = longitude
        planet_data["longitude"] = new_longitude
        planet_data["sign"] = ZODIAC_SIGNS[new_sign_num]

        # Recalculate house position if houses are defined
        if "houses" in d10_chart:
            planet_data["house"] = determine_house_for_longitude(d10_chart["houses"], new_longitude)

    # Calculate aspects for the D10 chart
    try:
        d10_chart["aspects"] = calculate_aspects(d10_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate aspects for D10 chart: {e}")
        d10_chart["aspects"] = []

    # Calculate dignities for the D10 chart
    try:
        d10_chart["dignities"] = calculate_dignities(d10_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate dignities for D10 chart: {e}")
        d10_chart["dignities"] = {}

    return d10_chart

def calculate_dwadashamsha_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate D12 (Dwadashamsha) chart - related to parents and ancestry.

    Args:
        chart_data: Base chart data

    Returns:
        D12 chart data
    """
    import copy

    # Create a deep copy of the chart data
    d12_chart = copy.deepcopy(chart_data)
    d12_chart["varga_type"] = "D12"
    d12_chart["varga_name"] = "Dwadashamsha"

    # Define zodiac signs
    ZODIAC_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    # Process planets for D12
    for planet_name, planet_data in d12_chart["planets"].items():
        if "longitude" not in planet_data:
            continue

        # Get original longitude
        longitude = planet_data["longitude"]

        # Calculate dwadashamsha (1/12th division of sign)
        sign_num = int(longitude / 30)
        pos_in_sign = longitude % 30
        dwadashamsha_num = int(pos_in_sign / 2.5)  # 30/12 = 2.5 degrees per division

        # For D12, calculation is simpler - each sign is divided into 12 equal parts
        # corresponding to the 12 signs starting from the sign itself
        new_sign_num = (sign_num + dwadashamsha_num) % 12

        # Calculate new longitude
        new_longitude = new_sign_num * 30 + (pos_in_sign % 2.5) * 12

        # Update planet data
        planet_data["original_longitude"] = longitude
        planet_data["longitude"] = new_longitude
        planet_data["sign"] = ZODIAC_SIGNS[new_sign_num]

        # Recalculate house position if houses are defined
        if "houses" in d12_chart:
            planet_data["house"] = determine_house_for_longitude(d12_chart["houses"], new_longitude)

    # Calculate aspects for the D12 chart
    try:
        d12_chart["aspects"] = calculate_aspects(d12_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate aspects for D12 chart: {e}")
        d12_chart["aspects"] = []

    # Calculate dignities for the D12 chart
    try:
        d12_chart["dignities"] = calculate_dignities(d12_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate dignities for D12 chart: {e}")
        d12_chart["dignities"] = {}

    return d12_chart

def calculate_trimsamsha_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate D30 (Trimsamsha) chart - related to misfortunes and challenges.

    Args:
        chart_data: Base chart data

    Returns:
        D30 chart data
    """
    import copy

    # Create a deep copy of the chart data
    d30_chart = copy.deepcopy(chart_data)
    d30_chart["varga_type"] = "D30"
    d30_chart["varga_name"] = "Trimsamsha"

    # Define zodiac signs
    ZODIAC_SIGNS = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    # Trimsamsha has a complex calculation with varying segment sizes
    # Different for odd and even signs

    # For odd signs (Aries, Gemini, Leo, Libra, Sagittarius, Aquarius):
    # 0°-5° = Mars, 5°-10° = Saturn, 10°-18° = Jupiter, 18°-25° = Mercury, 25°-30° = Venus

    # For even signs (Taurus, Cancer, Virgo, Scorpio, Capricorn, Pisces):
    # 0°-5° = Venus, 5°-12° = Mercury, 12°-20° = Jupiter, 20°-25° = Saturn, 25°-30° = Mars

    # Define segment ranges and rulers for odd and even signs
    odd_segments = [
        (0, 5, 4),     # 0-5° = Mars (ruler of Aries and Scorpio = 0, 7 -> simplified to 4)
        (5, 10, 6),    # 5-10° = Saturn (ruler of Capricorn and Aquarius = 9, 10 -> simplified to 6)
        (10, 18, 9),   # 10-18° = Jupiter (ruler of Sagittarius and Pisces = 8, 11 -> simplified to 9)
        (18, 25, 2),   # 18-25° = Mercury (ruler of Gemini and Virgo = 2, 5 -> simplified to 2)
        (25, 30, 1)    # 25-30° = Venus (ruler of Taurus and Libra = 1, 6 -> simplified to 1)
    ]

    even_segments = [
        (0, 5, 1),     # 0-5° = Venus
        (5, 12, 2),    # 5-12° = Mercury
        (12, 20, 9),   # 12-20° = Jupiter
        (20, 25, 6),   # 20-25° = Saturn
        (25, 30, 4)    # 25-30° = Mars
    ]

    # Process planets for D30
    for planet_name, planet_data in d30_chart["planets"].items():
        if "longitude" not in planet_data:
            continue

        # Get original longitude
        longitude = planet_data["longitude"]

        # Calculate trimsamsha
        sign_num = int(longitude / 30)
        pos_in_sign = longitude % 30

        # Determine segment and new sign
        if sign_num % 2 == 0:  # Odd signs (0-based indexing)
            segments = odd_segments
        else:  # Even signs (0-based indexing)
            segments = even_segments

        # Find which segment the position falls into
        for start, end, ruler_offset in segments:
            if start <= pos_in_sign < end:
                # Calculate new sign based on ruler
                new_sign_num = (ruler_offset) % 12
                # Calculate new position within sign based on proportional position in segment
                segment_width = end - start
                pos_in_segment = pos_in_sign - start
                new_pos_in_sign = (pos_in_segment / segment_width) * 30
                break
        else:
            # This is an error condition - the segments should cover the entire sign
            logger.error(f"Position {pos_in_sign} in sign {sign_num} not found in any segment")
            raise ValueError(f"Invalid segment definition for Trimsamsha calculation at position {pos_in_sign} in sign {sign_num}")

        # Calculate new longitude
        new_longitude = new_sign_num * 30 + new_pos_in_sign

        # Update planet data
        planet_data["original_longitude"] = longitude
        planet_data["longitude"] = new_longitude
        planet_data["sign"] = ZODIAC_SIGNS[new_sign_num]

        # Recalculate house position if houses are defined
        if "houses" in d30_chart:
            planet_data["house"] = determine_house_for_longitude(d30_chart["houses"], new_longitude)

    # Calculate aspects for the D30 chart
    try:
        d30_chart["aspects"] = calculate_aspects(d30_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate aspects for D30 chart: {e}")
        d30_chart["aspects"] = []

    # Calculate dignities for the D30 chart
    try:
        d30_chart["dignities"] = calculate_dignities(d30_chart)
    except Exception as e:
        logger.warning(f"Failed to calculate dignities for D30 chart: {e}")
        d30_chart["dignities"] = {}

    return d30_chart

def get_varga_name(varga_code: str) -> str:
    """Get the Sanskrit name for a varga (divisional) chart code."""
    varga_names = {
        "D1": "Rashi",
        "D2": "Hora",
        "D3": "Drekkana",
        "D4": "Chaturthamsha",
        "D7": "Saptamsha",
        "D9": "Navamsha",
        "D10": "Dashamsha",
        "D12": "Dwadashamsha",
        "D16": "Shodashamsha",
        "D20": "Vimshamsha",
        "D24": "Chaturvimshamsha",
        "D27": "Saptavimshamsha",
        "D30": "Trimsamsha",
        "D40": "Khavedamsha",
        "D45": "Akshavedamsha",
        "D60": "Shashtyamsha"
    }
    return varga_names.get(varga_code, varga_code)
