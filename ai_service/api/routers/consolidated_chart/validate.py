"""
Chart validation utilities for the consolidated chart router.

This module provides validation utilities for chart data.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, date
import re

from ai_service.api.routers.consolidated_chart.utils import validate_chart_data

# Configure logging
logger = logging.getLogger(__name__)

async def validate_birth_date(birth_date: str) -> Dict[str, Any]:
    """
    Validate a birth date string.

    Args:
        birth_date: Date string in YYYY-MM-DD format

    Returns:
        Dictionary with validation results
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }

    # Check format
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, birth_date):
        validation_result["valid"] = False
        validation_result["errors"].append("Birth date must be in YYYY-MM-DD format")
        return validation_result

    # Check if it's a valid date
    try:
        year, month, day = map(int, birth_date.split('-'))
        date(year, month, day)
    except ValueError as e:
        validation_result["valid"] = False
        validation_result["errors"].append(f"Invalid birth date: {str(e)}")
        return validation_result

    return validation_result

async def validate_birth_time(birth_time: str) -> Dict[str, Any]:
    """
    Validate a birth time string.

    Args:
        birth_time: Time string in HH:MM:SS or HH:MM format

    Returns:
        Dictionary with validation results
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }

    # Check format
    time_pattern = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])(:([0-5][0-9]))?$'
    if not re.match(time_pattern, birth_time):
        validation_result["valid"] = False
        validation_result["errors"].append("Birth time must be in HH:MM:SS or HH:MM format")
        return validation_result

    # If no seconds provided, add a warning
    if len(birth_time.split(':')) == 2:
        validation_result["warnings"].append("No seconds provided in birth time, using 00 for seconds")

    return validation_result

async def validate_coordinates(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Validate latitude and longitude coordinates.

    Args:
        latitude: Latitude value (-90 to 90)
        longitude: Longitude value (-180 to 180)

    Returns:
        Dictionary with validation results
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }

    # Check latitude range
    if latitude < -90 or latitude > 90:
        validation_result["valid"] = False
        validation_result["errors"].append("Latitude must be between -90 and 90")

    # Check longitude range
    if longitude < -180 or longitude > 180:
        validation_result["valid"] = False
        validation_result["errors"].append("Longitude must be between -180 and 180")

    return validation_result
