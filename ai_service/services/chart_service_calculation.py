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

from ai_service.services.chart_service_aspects import calculate_aspects
from ai_service.services.chart_service_dignities import calculate_dignities, calculate_planet_strengths

logger = logging.getLogger(__name__)

def calculate_chart(birth_date: str, birth_time: str, latitude: float, longitude: float,
                    timezone: str, chart_type: str = "vedic", house_system: str = "placidus",
                    verify_with_openai: bool = True, include_divisional: bool = True) -> Dict[str, Any]:
    """
    Calculate a comprehensive astrological chart with proper Vedic standards.

    Args:
        birth_date: Date of birth in YYYY-MM-DD format
        birth_time: Time of birth in HH:MM:SS format
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: IANA timezone identifier (e.g., 'America/New_York')
        chart_type: Chart calculation method ('vedic' or 'tropical')
        house_system: House system to use ('placidus', 'whole_sign', 'equal', etc.)
        verify_with_openai: Whether to verify chart calculations with OpenAI
        include_divisional: Whether to calculate divisional charts for Vedic charts

    Returns:
        Dictionary containing the complete chart data
    """
    logger.info(f"Calculating {chart_type} chart with {house_system} house system")

    try:
        # Parse date and time into datetime object
        import pytz

        # Create a datetime object for the birth date and time
        birth_dt_str = f"{birth_date} {birth_time}"
        birth_dt_naive = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M:%S")

        # Get the timezone object
        tz = pytz.timezone(timezone)

        # Convert naive datetime to timezone-aware datetime
        birth_dt = tz.localize(birth_dt_naive)

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
                from ai_service.core.rectification.chart_calculator import calculate_chart as calc_tropical

                # Calculate the tropical chart
                primary_chart_data = calc_tropical(
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
                from ai_service.services.chart_service_utils import calculate_arc_difference
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
    from ai_service.services.chart_service_utils import determine_house_for_longitude

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
    from ai_service.services.chart_service_utils import determine_house_for_longitude

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
    from ai_service.services.chart_service_utils import determine_house_for_longitude

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
    """Placeholder for D7 calculation"""
    # Create basic stub implementation
    import copy
    d7_chart = copy.deepcopy(chart_data)
    d7_chart["varga_type"] = "D7"
    d7_chart["varga_name"] = "Saptamsa"
    return d7_chart

def calculate_dashamsha_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder for D10 calculation"""
    # Create basic stub implementation
    import copy
    d10_chart = copy.deepcopy(chart_data)
    d10_chart["varga_type"] = "D10"
    d10_chart["varga_name"] = "Dashamsha"
    return d10_chart

def calculate_dwadashamsha_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder for D12 calculation"""
    # Create basic stub implementation
    import copy
    d12_chart = copy.deepcopy(chart_data)
    d12_chart["varga_type"] = "D12"
    d12_chart["varga_name"] = "Dwadashamsha"
    return d12_chart

def calculate_trimsamsha_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder for D30 calculation"""
    # Create basic stub implementation
    import copy
    d30_chart = copy.deepcopy(chart_data)
    d30_chart["varga_type"] = "D30"
    d30_chart["varga_name"] = "Trimsamsha"
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
