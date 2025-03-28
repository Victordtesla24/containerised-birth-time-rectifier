"""
Chart verification functionality for chart service.

This module provides function references to the chart_verification module
to avoid duplication while maintaining backwards compatibility.
"""

import logging
from typing import Dict, Any, Optional, List, Union

# Import directly from chart_verification
from ai_service.services.chart_verification import get_chart_verification_service

logger = logging.getLogger(__name__)

# Re-export functions to maintain backwards compatibility
__all__ = ['verify_chart_with_openai', 'create_verification_instructions',
           'prepare_chart_for_verification', 'apply_corrections',
           'validate_corrected_chart', 'get_zodiac_sign']

async def verify_chart_with_openai(chart_data: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Verify chart data using OpenAI service and astrological standards.

    Delegates to chart_verification.py for actual implementation.

    Args:
        chart_data: Chart data to verify
        session_id: Optional session ID for WebSocket updates

    Returns:
        Dictionary with verification results
    """
    # Get the chart verification service
    verification_service = get_chart_verification_service()

    # Delegate to the service's implementation
    return await verification_service.verify_chart(
        chart_data=chart_data,
        session_id=session_id,
        verify_with_openai=True,
        send_websocket_updates=session_id is not None
    )

async def create_verification_instructions(chart_data: Dict[str, Any]) -> str:
    """
    Create instructions for chart verification.

    Args:
        chart_data: Chart data to verify

    Returns:
        Verification instructions as a string
    """
    planets = chart_data.get("planets", {})
    houses = chart_data.get("houses", {})

    instructions = [
        "Verify the astrological chart data for accuracy and completeness:",
        "\nPlanetary Positions:",
    ]

    # Add planet data
    for planet, details in planets.items():
        sign = details.get("sign", "Unknown")
        longitude = details.get("longitude", 0)
        house = details.get("house", "Unknown")
        instructions.append(f"- {planet}: {sign} at {longitude:.2f}° in house {house}")

    # Add house data
    instructions.append("\nHouse Cusps:")
    for house, longitude in houses.items():
        if isinstance(longitude, dict):
            house_long = longitude.get("longitude", 0)
        else:
            house_long = float(longitude)
        sign = get_zodiac_sign(house_long)
        instructions.append(f"- House {house}: {sign} at {house_long % 30:.2f}°")

    # Add aspects if available
    if "aspects" in chart_data:
        instructions.append("\nMajor Aspects:")
        for aspect in chart_data.get("aspects", []):
            p1 = aspect.get("planet1", "Unknown")
            p2 = aspect.get("planet2", "Unknown")
            aspect_type = aspect.get("type", "Unknown")
            orb = aspect.get("orb", 0)
            instructions.append(f"- {p1} {aspect_type} {p2} (orb: {orb:.1f}°)")

    # Add verification instructions
    instructions.append("\nVerification Tasks:")
    instructions.append("1. Check if planets are in the correct signs")
    instructions.append("2. Verify house placements are consistent")
    instructions.append("3. Confirm aspects are calculated correctly")
    instructions.append("4. Check for any missing critical elements")

    return "\n".join(instructions)

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

def prepare_chart_for_verification(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare chart data for verification by extracting relevant information.

    Args:
        chart_data: The complete chart data from calculation functions

    Returns:
        Dictionary with relevant chart data structured for verification
    """
    try:
        # Extract only the data needed for verification
        birth_details = chart_data.get("birth_details", {})
        planets = chart_data.get("planets", {})
        houses = chart_data.get("houses", {})
        aspects = chart_data.get("aspects", [])

        # Verify we have required components
        if not birth_details:
            logger.warning("Missing birth details in chart data for verification")
        if not planets:
            raise ValueError("Missing planetary data required for verification")
        if not houses:
            raise ValueError("Missing house data required for verification")

        # Handle houses in list format - convert to dictionary
        if isinstance(houses, list):
            houses_dict = {}
            for i, house in enumerate(houses, 1):
                if isinstance(house, dict):
                    houses_dict[str(i)] = house
                else:
                    houses_dict[str(i)] = {"longitude": house}
            houses = houses_dict

        # Create focused verification data structure
        verification_data = {
            "birth_details": birth_details,
            "planets": planets,
            "houses": houses,
            "aspects": aspects
        }

        # Add chart type information if available
        if "chart_type" in chart_data:
            verification_data["chart_type"] = chart_data["chart_type"]

        # Add house system if available
        options = chart_data.get("options", {})
        if "house_system" in options:
            verification_data["house_system"] = options["house_system"]
        elif "house_system" in chart_data:
            verification_data["house_system"] = chart_data["house_system"]

        return verification_data

    except Exception as e:
        logger.error(f"Error preparing chart data for verification: {e}")
        raise ValueError(f"Failed to prepare chart for verification: {str(e)}")

def apply_corrections(chart_data: Dict[str, Any], corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply corrections to chart data based on verification results.

    Args:
        chart_data: Original chart data
        corrections: List of corrections to apply

    Returns:
        Corrected chart data
    """
    try:
        import asyncio

        # Get the chart verification service
        verification_service = get_chart_verification_service()

        # Create a verification result with just the corrections
        verification_result = {"corrections": corrections}

        # Use the async function but run it synchronously for compatibility
        return asyncio.run(verification_service._apply_corrections(chart_data, verification_result))
    except Exception as e:
        error_msg = f"Failed to apply corrections: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def validate_corrected_chart(chart_data: Dict[str, Any]) -> bool:
    """
    Validate corrected chart data for integrity and consistency.

    Args:
        chart_data: Chart data to validate

    Returns:
        True if chart is valid, False otherwise
    """
    try:
        # Check if required sections exist
        if "planets" not in chart_data:
            logger.error("Validation failed: 'planets' section missing")
            return False

        if "houses" not in chart_data:
            logger.error("Validation failed: 'houses' section missing")
            return False

        # Check if key planets exist
        required_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
        for planet in required_planets:
            if planet not in chart_data.get("planets", {}):
                logger.error(f"Validation failed: Required planet '{planet}' missing")
                return False

        # Check if houses are complete (1-12)
        for i in range(1, 13):
            house_key = str(i)
            if house_key not in chart_data.get("houses", {}):
                logger.error(f"Validation failed: House {house_key} missing")
                return False

        # Check longitude ranges
        for planet, data in chart_data.get("planets", {}).items():
            longitude = data.get("longitude")
            if longitude is not None and (longitude < 0 or longitude >= 360):
                logger.error(f"Validation failed: Invalid longitude {longitude} for {planet}")
                return False

        for house_key, data in chart_data.get("houses", {}).items():
            longitude = data.get("longitude")
            if longitude is not None and (longitude < 0 or longitude >= 360):
                logger.error(f"Validation failed: Invalid longitude {longitude} for House {house_key}")
                return False

        # Check aspects for validity
        for aspect in chart_data.get("aspects", []):
            if "planet1" not in aspect or "planet2" not in aspect:
                logger.error("Validation failed: Aspect missing planet references")
                return False

            if aspect.get("planet1") == aspect.get("planet2"):
                logger.error(f"Validation failed: Self-aspect for {aspect.get('planet1')}")
                return False

            orb = aspect.get("orb")
            if orb is not None and orb > 10:  # Maximum reasonable orb
                logger.error(f"Validation failed: Unreasonable orb {orb} for aspect")
                return False

        # If we reach here, chart passes basic validation
        return True

    except Exception as e:
        logger.error(f"Chart validation error: {e}")
        return False
