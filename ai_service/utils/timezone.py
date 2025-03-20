"""
Timezone utilities module for the Birth Time Rectifier application.

This module provides functions to:
1. Get timezone information for given coordinates
2. Convert datetime between timezones
3. Calculate timezone offsets
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from timezonefinder import TimezoneFinder
import pytz
from datetime import datetime, timezone as tz

logger = logging.getLogger(__name__)

# Initialize timezone finder
_timezone_finder = TimezoneFinder()

async def get_timezone_for_coordinates(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get timezone information for the given geographic coordinates.

    Uses TimezoneFinder to determine the IANA timezone identifier and then
    calculates the current offset from UTC.

    Args:
        latitude: The latitude coordinate
        longitude: The longitude coordinate

    Returns:
        Dictionary containing timezone information:
        {
            "timezone": "America/New_York",  # IANA timezone identifier
            "timezone_id": "America/New_York",  # Same as timezone for API consistency
            "offset": -18000,  # Current offset from UTC in seconds
            "offset_hours": -5,  # Current offset from UTC in hours
            "name": "Eastern Standard Time",  # Human-readable timezone name
            "has_dst": True  # Whether the timezone observes Daylight Saving Time
        }

    Raises:
        ValueError: If no timezone could be determined for the coordinates
    """
    # Use timezonefinder to get the timezone ID
    timezone_id = _timezone_finder.timezone_at(lat=latitude, lng=longitude)

    if not timezone_id:
        logger.error(f"Could not determine timezone for coordinates: {latitude}, {longitude}")
        raise ValueError(f"No timezone found for coordinates: {latitude}, {longitude}")

    # Get the pytz timezone object
    tz_obj = pytz.timezone(timezone_id)

    # Get current datetime in UTC
    now_utc = datetime.now(tz.utc)

    # Get current offset
    now_local = now_utc.astimezone(tz_obj)
    offset_seconds = now_local.utcoffset().total_seconds()
    offset_hours = offset_seconds / 3600

    # Get timezone name and DST information
    tzname = now_local.tzname()
    has_dst = hasattr(tz_obj, '_dst') and tz_obj._dst is not None

    return {
        "timezone": timezone_id,
        "timezone_id": timezone_id,
        "offset": int(offset_seconds),
        "offset_hours": offset_hours,
        "name": tzname,
        "has_dst": has_dst
    }

def convert_to_timezone(dt: datetime, timezone_id: str) -> datetime:
    """
    Convert a datetime object to the specified timezone.

    Args:
        dt: The datetime object to convert
        timezone_id: The IANA timezone identifier

    Returns:
        The datetime object in the specified timezone
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.utc)

    return dt.astimezone(pytz.timezone(timezone_id))

def get_current_offset(timezone_id: str) -> int:
    """
    Get the current offset from UTC for a timezone in seconds.

    Args:
        timezone_id: The IANA timezone identifier

    Returns:
        The current offset in seconds
    """
    tz_obj = pytz.timezone(timezone_id)
    now_utc = datetime.now(tz.utc)
    now_local = now_utc.astimezone(tz_obj)
    return int(now_local.utcoffset().total_seconds())
