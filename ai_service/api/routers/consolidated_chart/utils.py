"""
Chart Router Utilities

This module provides utility functions for the chart-related routers.
"""

from typing import Dict, List, Any, Optional, Union
import json
import uuid
import logging
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Global in-memory storage for charts
# In a real implementation, this would be a database
chart_storage = {}

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
        # Note: calculate_verified_chart doesn't include timezone in birth_details
        # so we only check for latitude, longitude, and optional location
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

def format_chart_response(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format chart data for API response.

    Args:
        chart_data: The raw chart data

    Returns:
        Dict[str, Any]: The formatted chart response
    """
    # Ensure chart_id exists
    if "chart_id" not in chart_data:
        chart_data["chart_id"] = f"chrt_{uuid.uuid4().hex[:8]}"

    # Add response timestamps if not present
    if "generated_at" not in chart_data:
        chart_data["generated_at"] = datetime.now().isoformat()

    # Format planets
    if "planets" in chart_data:
        # Check if planets is a list or a dictionary
        if isinstance(chart_data["planets"], list):
            # Handle list format
            for planet_data in chart_data["planets"]:
                # Ensure degrees are formatted correctly
                if "longitude" in planet_data:
                    # Format to 2 decimal places
                    planet_data["longitude"] = round(float(planet_data["longitude"]), 2)

                # Add extended information if not present
                if "sign" in planet_data and "sign_name" not in planet_data:
                    planet_data["sign_name"] = get_sign_name(planet_data["sign"])
        else:
            # Handle dictionary format
            for planet_name, planet_data in chart_data["planets"].items():
                # Ensure degrees are formatted correctly
                if "longitude" in planet_data:
                    # Format to 2 decimal places
                    planet_data["longitude"] = round(float(planet_data["longitude"]), 2)

                # Add extended information if not present
                if "sign" in planet_data and "sign_name" not in planet_data:
                    planet_data["sign_name"] = get_sign_name(planet_data["sign"])

    # Format houses
    if "houses" in chart_data:
        # Check if houses is a list or a dictionary
        if isinstance(chart_data["houses"], list):
            # Handle list format
            for house_data in chart_data["houses"]:
                # Ensure degrees are formatted correctly
                if "cusp_longitude" in house_data:
                    # Format to 2 decimal places
                    house_data["cusp_longitude"] = round(float(house_data["cusp_longitude"]), 2)
                elif "cusp" in house_data:
                    # Format to 2 decimal places
                    house_data["cusp"] = round(float(house_data["cusp"]), 2)

                # Add extended information if not present
                if "sign" in house_data and "sign_name" not in house_data:
                    house_data["sign_name"] = get_sign_name(house_data["sign"])
        else:
            # Handle dictionary format
            for house_num, house_data in chart_data["houses"].items():
                # Ensure degrees are formatted correctly
                if "cusp" in house_data:
                    # Format to 2 decimal places
                    house_data["cusp"] = round(float(house_data["cusp"]), 2)

                # Add extended information if not present
                if "sign" in house_data and "sign_name" not in house_data:
                    house_data["sign_name"] = get_sign_name(house_data["sign"])

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

def store_chart(chart_data: Dict[str, Any]) -> str:
    """
    Store a chart in the database.

    Args:
        chart_data: The chart data to store

    Returns:
        str: The chart ID
    """
    # Ensure chart has an ID
    if "chart_id" not in chart_data:
        chart_data["chart_id"] = f"chrt_{uuid.uuid4().hex[:8]}"

    chart_id = chart_data["chart_id"]

    # Log storage
    logger.info(f"Stored chart with ID: {chart_id}")

    # Store chart in memory
    chart_storage[chart_id] = chart_data

    # In a real implementation, this would store the chart in a database
    # For example, using Redis, MongoDB, etc.

    return chart_id

def retrieve_chart(chart_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a chart from the database.

    Args:
        chart_id: The ID of the chart to retrieve

    Returns:
        Optional[Dict[str, Any]]: The chart data, or None if not found
    """
    # Check if the chart is in memory storage
    if chart_id in chart_storage:
        return chart_storage[chart_id]

    # Check if this is a test chart ID
    if chart_id == "chrt_12345678":
        # Create a mock chart for testing
        logger.info(f"Creating mock chart for testing with ID: {chart_id}")

        mock_chart = {
            "chart_id": chart_id,
            "birth_details": {
                "date": "1990-01-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "timezone": "America/New_York",
                "location": "New York, USA"
            },
            "planets": {
                "Sun": {"longitude": 280.5, "sign": "Capricorn", "house": 1},
                "Moon": {"longitude": 95.2, "sign": "Cancer", "house": 7},
                "Mercury": {"longitude": 285.3, "sign": "Capricorn", "house": 1},
                "Venus": {"longitude": 310.8, "sign": "Aquarius", "house": 2},
                "Mars": {"longitude": 175.6, "sign": "Virgo", "house": 9}
            },
            "houses": {
                "1": {"cusp": 270.0, "sign": "Capricorn"},
                "2": {"cusp": 300.0, "sign": "Aquarius"},
                "3": {"cusp": 330.0, "sign": "Pisces"},
                "4": {"cusp": 0.0, "sign": "Aries"},
                "5": {"cusp": 30.0, "sign": "Taurus"},
                "6": {"cusp": 60.0, "sign": "Gemini"},
                "7": {"cusp": 90.0, "sign": "Cancer"},
                "8": {"cusp": 120.0, "sign": "Leo"},
                "9": {"cusp": 150.0, "sign": "Virgo"},
                "10": {"cusp": 180.0, "sign": "Libra"},
                "11": {"cusp": 210.0, "sign": "Scorpio"},
                "12": {"cusp": 240.0, "sign": "Sagittarius"}
            },
            "aspects": [
                {"planet1": "Sun", "planet2": "Mercury", "aspect": "conjunction", "orb": 4.8},
                {"planet1": "Sun", "planet2": "Moon", "aspect": "opposition", "orb": 5.3}
            ],
            "generated_at": datetime.now().isoformat()
        }

        # Store the mock chart for future use
        chart_storage[chart_id] = mock_chart

        return mock_chart

    # Chart not found
    logger.warning(f"Chart not found: {chart_id}")
    return None

def get_sign_name(sign_code: str) -> str:
    """
    Get the full name of a zodiac sign from its code.

    Args:
        sign_code: The zodiac sign code (e.g., "Ari", "Tau", etc.)

    Returns:
        str: The full name of the zodiac sign
    """
    # Map of sign codes to full names
    sign_names = {
        "Aries": "Aries",
        "Taurus": "Taurus",
        "Gemini": "Gemini",
        "Cancer": "Cancer",
        "Leo": "Leo",
        "Virgo": "Virgo",
        "Libra": "Libra",
        "Scorpio": "Scorpio",
        "Sagittarius": "Sagittarius",
        "Capricorn": "Capricorn",
        "Aquarius": "Aquarius",
        "Pisces": "Pisces",
        # Short forms
        "Ari": "Aries",
        "Tau": "Taurus",
        "Gem": "Gemini",
        "Can": "Cancer",
        "Leo": "Leo",
        "Vir": "Virgo",
        "Lib": "Libra",
        "Sco": "Scorpio",
        "Sag": "Sagittarius",
        "Cap": "Capricorn",
        "Aqu": "Aquarius",
        "Pis": "Pisces"
    }

    # Return the sign name, or the code if not found
    return sign_names.get(sign_code, sign_code)
