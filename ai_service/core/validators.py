"""
Validators for birth chart details.

This module provides validation functions for birth charts, including birth date, time,
and location validation.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

async def validate_birth_details(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: str
) -> Dict[str, Any]:
    """
    Validate birth details for astrological calculations.

    Args:
        birth_date: Birth date in YYYY-MM-DD format
        birth_time: Birth time in HH:MM:SS format
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        timezone: IANA timezone identifier

    Returns:
        A dictionary with validation results
    """
    errors = []

    # Validate birth date
    try:
        datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        errors.append("Invalid birth date format. Use YYYY-MM-DD format.")

    # Validate birth time
    try:
        if not re.match(r"^\d{1,2}:\d{2}:\d{2}$", birth_time):
            errors.append("Invalid birth time format. Use HH:MM:SS format.")
        else:
            hour, minute, second = map(int, birth_time.split(':'))
            if hour < 0 or hour > 23 or minute < 0 or minute > 59 or second < 0 or second > 59:
                errors.append("Invalid birth time values. Hours must be 0-23, minutes and seconds must be 0-59.")
    except Exception as e:
        errors.append(f"Invalid birth time: {str(e)}")

    # Validate latitude
    if latitude < -90 or latitude > 90:
        errors.append("Invalid latitude. Must be between -90 and 90 degrees.")

    # Validate longitude
    if longitude < -180 or longitude > 180:
        errors.append("Invalid longitude. Must be between -180 and 180 degrees.")

    # Validate timezone (basic check)
    if not timezone:
        errors.append("Timezone is required.")

    # Result
    result = {
        "valid": len(errors) == 0,
        "errors": errors if errors else None,
        "birth_date": birth_date if len(errors) == 0 else None,
        "birth_time": birth_time if len(errors) == 0 else None,
        "latitude": latitude if len(errors) == 0 else None,
        "longitude": longitude if len(errors) == 0 else None,
        "timezone": timezone if len(errors) == 0 else None
    }

    return result
