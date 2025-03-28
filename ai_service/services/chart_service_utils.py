"""
Chart Service Utilities

This module provides utility functions for chart generation, manipulation and validation.
"""

import logging
import uuid
import json
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

# Constants for chart calculations
ZODIAC_SIGNS = {
    "1": "Aries",
    "2": "Taurus",
    "3": "Gemini",
    "4": "Cancer",
    "5": "Leo",
    "6": "Virgo",
    "7": "Libra",
    "8": "Scorpio",
    "9": "Sagittarius",
    "10": "Capricorn",
    "11": "Aquarius",
    "12": "Pisces"
}

# Planet constants
PLANETS = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
    "North Node", "South Node", "Chiron", "Ceres", "Pallas",
    "Juno", "Vesta"
]

# Aspect types and orbs
ASPECTS = {
    "conjunction": {"angle": 0, "orb": 8, "harmonious": True},
    "sextile": {"angle": 60, "orb": 6, "harmonious": True},
    "square": {"angle": 90, "orb": 8, "harmonious": False},
    "trine": {"angle": 120, "orb": 8, "harmonious": True},
    "opposition": {"angle": 180, "orb": 8, "harmonious": False},
    "quincunx": {"angle": 150, "orb": 3, "harmonious": False},
    "semisextile": {"angle": 30, "orb": 3, "harmonious": True},
    "semisquare": {"angle": 45, "orb": 3, "harmonious": False},
    "sesquisquare": {"angle": 135, "orb": 3, "harmonious": False}
}

# Error codes for standardized error responses
ERROR_CODES = {
    "CHART_NOT_FOUND": "ERR_CHART_NOT_FOUND",
    "CALCULATION_ERROR": "ERR_CALCULATION_FAILED",
    "VALIDATION_ERROR": "ERR_VALIDATION_FAILED",
    "RECTIFICATION_FAILED": "ERR_RECTIFICATION_FAILED",
    "COMPARISON_FAILED": "ERR_COMPARISON_FAILED",
    "EXPORT_FAILED": "ERR_EXPORT_FAILED",
    "INTERNAL_SERVER_ERROR": "ERR_INTERNAL_SERVER",
    "INVALID_REQUEST": "ERR_INVALID_REQUEST"
}

# Default chart options
DEFAULT_CHART_OPTIONS = {
    "house_system": "P",
    "zodiac_type": "sidereal",
    "ayanamsa": "lahiri",
    "node_type": "true",
    "verify_with_openai": True
}

# Chart types
CHART_TYPES = [
    "natal",
    "transit",
    "progressed",
    "synastry",
    "composite",
    "rectified"
]

# Export formats
EXPORT_FORMATS = [
    "json",
    "pdf",
    "png",
    "svg",
    "text"
]

def calculate_arc_difference(longitude1: float, longitude2: float) -> float:
    """
    Calculate the shortest arc distance between two celestial longitudes.

    Useful for finding the angular separation between planets or points
    in the zodiac, taking into account the circular nature of the zodiac.

    Args:
        longitude1: First longitude in degrees (0-360)
        longitude2: Second longitude in degrees (0-360)

    Returns:
        The shortest arc distance in degrees (0-180)
    """
    # Ensure both longitudes are in 0-360 range
    lon1 = float(longitude1) % 360
    lon2 = float(longitude2) % 360

    # Calculate the absolute difference
    diff = abs(lon1 - lon2)

    # Take the shorter of the two possible arcs
    if diff > 180:
        diff = 360 - diff

    return diff

def validate_birth_details(birth_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate birth details for chart generation.

    Args:
        birth_details: Dictionary containing birth details to validate

    Returns:
        Dict with validation result and any errors
    """
    errors = {}
    warnings = {}

    # Basic birth date validation
    if "birth_date" not in birth_details:
        errors["birth_date"] = "Birth date is required"

    # Birth time validation - required for accurate charts
    if "birth_time" not in birth_details:
        errors["birth_time"] = "Birth time is required for accurate chart calculation"

    # Coordinates validation
    if "latitude" not in birth_details:
        errors["latitude"] = "Latitude is required"
    elif not isinstance(birth_details["latitude"], (int, float)) and not (
            isinstance(birth_details["latitude"], str) and birth_details["latitude"].replace('-', '').replace('.', '').isdigit()):
        errors["latitude"] = "Latitude must be a valid number"
    elif isinstance(birth_details["latitude"], (int, float)) and (birth_details["latitude"] < -90 or birth_details["latitude"] > 90):
        errors["latitude"] = "Latitude must be between -90 and 90 degrees"

    if "longitude" not in birth_details:
        errors["longitude"] = "Longitude is required"
    elif not isinstance(birth_details["longitude"], (int, float)) and not (
            isinstance(birth_details["longitude"], str) and birth_details["longitude"].replace('-', '').replace('.', '').isdigit()):
        errors["longitude"] = "Longitude must be a valid number"
    elif isinstance(birth_details["longitude"], (int, float)) and (birth_details["longitude"] < -180 or birth_details["longitude"] > 180):
        errors["longitude"] = "Longitude must be between -180 and 180 degrees"

    # Timezone validation - add warning if missing
    if "timezone" not in birth_details:
        warnings["timezone"] = "Timezone is recommended for accurate chart calculation"

    # Return validation result
    if errors:
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings
        }

    return {
        "valid": True,
        "errors": None,
        "warnings": warnings or None
    }

def validate_chart_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate chart data to ensure it contains all required fields.

    Args:
        data: The chart data dictionary to validate

    Returns:
        Dict[str, Any]: Validation result with status and any error messages
    """
    errors = {}

    # Validate birth details
    if "birth_details" not in data:
        errors["birth_details"] = "Birth details are required"
    else:
        birth_details = data["birth_details"]

        # Define field name mappings
        date_fields = ["date", "birth_date"]
        time_fields = ["time", "birth_time"]
        # Required fields for accurate calculations
        other_required_fields = ["latitude", "longitude"]

        # Check for date (either date or birth_date)
        if not any(field in birth_details for field in date_fields):
            errors["birth_details.date"] = "date is required"

        # Check for time (either time or birth_time)
        if not any(field in birth_details for field in time_fields):
            errors["birth_details.time"] = "time is required"

        # Check for other required fields
        for field in other_required_fields:
            if field not in birth_details:
                errors[f"birth_details.{field}"] = f"{field} is required"

    # Validate options
    if "options" in data:
        options = data["options"]

        # Validate house system
        if "house_system" in options and options["house_system"] not in ["P", "K", "W", "R", "B", "O", "C"]:
            errors["options.house_system"] = "Invalid house system"

        # Validate zodiac type
        if "zodiac_type" in options and options["zodiac_type"] not in ["sidereal", "tropical"]:
            errors["options.zodiac_type"] = "Invalid zodiac type"

        # Validate node type
        if "node_type" in options and options["node_type"] not in ["true", "mean"]:
            errors["options.node_type"] = "Invalid node type"

    # Return validation result
    if errors:
        return {
            "valid": False,
            "errors": errors
        }
    else:
        return {
            "valid": True,
            "errors": None
        }

def format_chart_data(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format chart data to ensure consistent structure and values.

    Args:
        chart_data: Raw chart data

    Returns:
        Formatted chart data
    """
    # Ensure chart_id exists
    if "chart_id" not in chart_data:
        chart_data["chart_id"] = f"chrt_{uuid.uuid4().hex[:8]}"

    # Add response timestamps if not present
    if "generated_at" not in chart_data:
        chart_data["generated_at"] = datetime.now().isoformat()

    # Format planets
    if "planets" in chart_data and chart_data["planets"]:
        # Format different planet structure types
        if isinstance(chart_data["planets"], list):
            for planet in chart_data["planets"]:
                _format_planet(planet)
        elif isinstance(chart_data["planets"], dict):
            for planet_key, planet in chart_data["planets"].items():
                if isinstance(planet, dict):
                    _format_planet(planet)

    # Format houses
    if "houses" in chart_data and chart_data["houses"]:
        # Format different house structure types
        if isinstance(chart_data["houses"], list):
            for house in chart_data["houses"]:
                _format_house(house)
        elif isinstance(chart_data["houses"], dict):
            for house_key, house in chart_data["houses"].items():
                if isinstance(house, dict):
                    _format_house(house)

    # Ensure verification data is consistently formatted
    if "verification" in chart_data:
        verification = chart_data["verification"]

        # Add default fields if missing
        if "verified" not in verification:
            verification["verified"] = False

        if "confidence_score" not in verification:
            verification["confidence_score"] = 0.0

        # Add timestamp if not present
        if "verified_at" not in verification:
            verification["verified_at"] = chart_data.get("generated_at", datetime.now().isoformat())

    return chart_data

def _format_planet(planet: Dict[str, Any]) -> None:
    """Helper function to format a planet dictionary."""
    # Ensure longitude is a float with 2 decimal places
    if "longitude" in planet and planet["longitude"] is not None:
        try:
            planet["longitude"] = round(float(planet["longitude"]), 2)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert longitude to float: {planet.get('longitude')}")

    # Add sign name if missing
    if "sign" in planet and "sign_name" not in planet:
        sign = str(planet["sign"])
        planet["sign_name"] = ZODIAC_SIGNS.get(sign, f"Unknown Sign ({sign})")

def _format_house(house: Dict[str, Any]) -> None:
    """Helper function to format a house dictionary."""
    # Ensure cusp is a float with 2 decimal places
    if "cusp" in house and house["cusp"] is not None:
        try:
            house["cusp"] = round(float(house["cusp"]), 2)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert house cusp to float: {house.get('cusp')}")
    elif "cusp_longitude" in house and house["cusp_longitude"] is not None:
        try:
            house["cusp_longitude"] = round(float(house["cusp_longitude"]), 2)
            # Add cusp as alias if missing
            if "cusp" not in house:
                house["cusp"] = house["cusp_longitude"]
        except (ValueError, TypeError):
            logger.warning(f"Could not convert house cusp_longitude to float: {house.get('cusp_longitude')}")

    # Add sign name if missing
    if "sign" in house and "sign_name" not in house:
        sign = str(house["sign"])
        house["sign_name"] = ZODIAC_SIGNS.get(sign, f"Unknown Sign ({sign})")

def calculate_aspects(chart_data: Dict[str, Any], orb_multiplier: float = 1.0) -> List[Dict[str, Any]]:
    """
    Calculate aspects between planets in a chart.

    Args:
        chart_data: The chart data containing planets
        orb_multiplier: Multiplier to adjust default orbs (1.0 = standard orbs)

    Returns:
        List of aspect dictionaries
    """
    aspects = []

    # If no planets, return empty list
    if "planets" not in chart_data or not chart_data["planets"]:
        return aspects

    # Get the planets in the right format for processing
    planets_list = []
    if isinstance(chart_data["planets"], list):
        planets_list = chart_data["planets"]
    elif isinstance(chart_data["planets"], dict):
        for name, data in chart_data["planets"].items():
            if isinstance(data, dict):
                # Add name if not in the dictionary
                if "name" not in data:
                    data["name"] = name
                planets_list.append(data)

    # Calculate aspects between each pair of planets
    for i in range(len(planets_list)):
        planet1 = planets_list[i]

        if "longitude" not in planet1:
            continue

        for j in range(i + 1, len(planets_list)):
            planet2 = planets_list[j]

            if "longitude" not in planet2:
                continue

            # Calculate the angular difference
            angle_diff = abs(float(planet1["longitude"]) - float(planet2["longitude"]))

            # Normalize to 0-180 degrees
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            # Check for aspects
            for aspect_name, aspect_data in ASPECTS.items():
                aspect_angle = aspect_data["angle"]
                aspect_orb = aspect_data["orb"] * orb_multiplier

                if abs(angle_diff - aspect_angle) <= aspect_orb:
                    # Create aspect dictionary
                    aspect = {
                        "aspect_type": aspect_name,
                        "planet1": planet1.get("name", planet1.get("id", "Unknown")),
                        "planet2": planet2.get("name", planet2.get("id", "Unknown")),
                        "orb": round(abs(angle_diff - aspect_angle), 2),
                        "exact": abs(angle_diff - aspect_angle) < 1.0,
                        "harmonious": aspect_data["harmonious"]
                    }
                    aspects.append(aspect)
                    break  # Found the aspect, no need to check others

    return aspects

def get_sign_name(sign_code: str) -> str:
    """
    Get the sign name from a sign code.

    Args:
        sign_code: The sign code (1-12)

    Returns:
        The sign name
    """
    try:
        # Handle numerical sign codes
        if isinstance(sign_code, (int, float)) or sign_code.isdigit():
            sign_num = str(int(float(sign_code)))
            return ZODIAC_SIGNS.get(sign_num, f"Unknown Sign ({sign_code})")

        # Try to handle textual sign codes
        sign_code = sign_code.title()
        for key, value in ZODIAC_SIGNS.items():
            if sign_code == value:
                return value

        # If we get here, the sign code was invalid
        return f"Unknown Sign ({sign_code})"
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning(f"Invalid sign code: {sign_code}, error: {e}")
        return f"Unknown Sign ({sign_code})"

def get_sign_from_longitude(longitude: float) -> str:
    """
    Convert a celestial longitude to zodiac sign name.

    Args:
        longitude: The celestial longitude in degrees (0-360)

    Returns:
        The name of the zodiac sign at that longitude
    """
    # Normalize longitude to 0-360 range
    longitude = float(longitude) % 360

    # Calculate sign index (0-11)
    sign_index = int(longitude / 30) + 1

    # Convert index to string key for the ZODIAC_SIGNS dictionary
    sign_key = str(sign_index)

    # Return sign name or fallback to Unknown with the longitude
    return ZODIAC_SIGNS.get(sign_key, f"Unknown Sign ({longitude}°)")

def get_planet_rulerships() -> Dict[str, List[str]]:
    """
    Get the traditional rulerships of planets over zodiac signs.

    Returns:
        Dictionary mapping planet names to lists of signs they rule
    """
    return {
        "Sun": ["Leo"],
        "Moon": ["Cancer"],
        "Mercury": ["Gemini", "Virgo"],
        "Venus": ["Taurus", "Libra"],
        "Mars": ["Aries", "Scorpio"],
        "Jupiter": ["Sagittarius", "Pisces"],
        "Saturn": ["Capricorn", "Aquarius"],
        # Modern rulerships
        "Uranus": ["Aquarius"],
        "Neptune": ["Pisces"],
        "Pluto": ["Scorpio"]
    }

def is_day_chart(chart_data: Dict[str, Any]) -> bool:
    """
    Determine if a chart is a day chart or a night chart.

    A day chart is when the Sun is above the horizon (in houses 7-12).
    A night chart is when the Sun is below the horizon (in houses 1-6).

    Args:
        chart_data: The chart data containing planets and houses

    Returns:
        True if it's a day chart, False if it's a night chart
    """
    # Default to day chart if we can't determine
    if "planets" not in chart_data:
        return True

    # Get the Sun's position
    sun = None
    if isinstance(chart_data["planets"], dict) and "Sun" in chart_data["planets"]:
        sun = chart_data["planets"]["Sun"]
    elif isinstance(chart_data["planets"], list):
        for planet in chart_data["planets"]:
            if planet.get("name") == "Sun":
                sun = planet
                break

    # If we couldn't find the Sun, return default
    if not sun:
        return True

    # Check if the Sun is in houses 7-12 (day chart) or 1-6 (night chart)
    sun_house = sun.get("house")
    if sun_house:
        return 7 <= int(sun_house) <= 12

    # Alternate method: check if Sun is above the horizon
    # This is a simplified approach - a more accurate implementation
    # would compare the Sun's longitude with the Ascendant and Descendant
    sun_longitude = sun.get("longitude")
    if "angles" in chart_data and "ascendant" in chart_data["angles"]:
        asc_longitude = chart_data["angles"]["ascendant"].get("longitude")
        if sun_longitude is not None and asc_longitude is not None:
            # Calculate the difference between Sun and Ascendant
            diff = (sun_longitude - asc_longitude) % 360
            # If Sun is in houses 7-12 (i.e., 180-360 degrees from Ascendant)
            return 180 <= diff <= 360

    # If we can't determine, default to True
    return True
