"""
Timezone utilities module for the Birth Time Rectifier application.

This module provides enhanced functions to:
1. Get timezone information for given coordinates with proper error handling
2. Convert datetime between timezones
3. Calculate timezone offsets
4. Handle edge cases and invalid coordinates gracefully
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Tuple, Union
from datetime import datetime, timezone as tz, timedelta
from functools import lru_cache

# Import timezone libraries with fallbacks
try:
    from timezonefinder import TimezoneFinder, TimezonefinderL
    from tzfpy import get_timezone
    HAS_TZFPY = True
except ImportError:
    HAS_TZFPY = False

import pytz
from pytz.exceptions import UnknownTimeZoneError

logger = logging.getLogger(__name__)

# Initialize timezone finders
_timezone_finder = TimezoneFinder(in_memory=True)
try:
    _timezone_finder_light = TimezonefinderL()
    HAS_TZF_LIGHT = True
except (ImportError, NameError):
    HAS_TZF_LIGHT = False

# Default coordinates for fallback (Greenwich, UK)
DEFAULT_LATITUDE = 51.4778
DEFAULT_LONGITUDE = -0.0014
DEFAULT_TIMEZONE = "Europe/London"

# Cache timezone lookups to improve performance
@lru_cache(maxsize=1024)
async def get_timezone_for_coordinates(latitude: float, longitude: float,
                                       use_fast_approach: bool = False) -> Dict[str, Any]:
    """
    Get timezone information for the given geographic coordinates with robust error handling.

    Uses multiple methods to determine the timezone with fallbacks:
    1. TimezoneFinder (high precision, memory intensive)
    2. TimezonefinderL (lower precision, faster, less memory)
    3. tzfpy (if available, fast C implementation)
    4. Fallback to default timezone with warning

    Args:
        latitude: The latitude coordinate (-90 to 90)
        longitude: The longitude coordinate (-180 to 180)
        use_fast_approach: Whether to prioritize speed over accuracy

    Returns:
        Dictionary containing timezone information:
        {
            "timezone": "America/New_York",  # IANA timezone identifier
            "timezone_id": "America/New_York",  # Same as timezone for API consistency
            "offset": -18000,  # Current offset from UTC in seconds
            "offset_hours": -5,  # Current offset from UTC in hours
            "name": "Eastern Standard Time",  # Human-readable timezone name
            "has_dst": True,  # Whether the timezone observes Daylight Saving Time
            "confidence": 1.0  # Confidence in the timezone determination (0-1)
        }

    Raises:
        ValueError: If coordinates are invalid and no fallback available
    """
    # Validate coordinates
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        logger.warning(f"Invalid coordinates: {latitude}, {longitude}. Using fallback.")
        return await get_timezone_for_coordinates(DEFAULT_LATITUDE, DEFAULT_LONGITUDE, use_fast_approach)

    timezone_id = None
    confidence = 1.0  # Default to full confidence
    method_used = "unknown"

    # Try different methods in sequence, with different priorities based on speed vs accuracy
    methods = []

    if use_fast_approach and HAS_TZF_LIGHT:
        # Fast approach prioritizes speed
        methods = [
            ("TimezonefinderL", lambda: _timezone_finder_light.timezone_at(lat=latitude, lng=longitude)),
            ("TimezoneFinder", lambda: _timezone_finder.timezone_at(lat=latitude, lng=longitude)),
            ("tzfpy", lambda: get_timezone(longitude, latitude) if HAS_TZFPY else None)
        ]
    else:
        # Default approach prioritizes accuracy
        methods = [
            ("TimezoneFinder", lambda: _timezone_finder.timezone_at(lat=latitude, lng=longitude)),
            ("TimezonefinderL", lambda: _timezone_finder_light.timezone_at(lat=latitude, lng=longitude) if HAS_TZF_LIGHT else None),
            ("tzfpy", lambda: get_timezone(longitude, latitude) if HAS_TZFPY else None)
        ]

    # Try each method until one succeeds
    for method_name, finder_func in methods:
        try:
            tz_result = finder_func()
            if tz_result:
                timezone_id = tz_result
                method_used = method_name
                # If using less accurate methods, reduce confidence slightly
                if method_name in ["TimezonefinderL", "tzfpy"]:
                    confidence = 0.95
                break
        except Exception as e:
            logger.warning(f"Error using {method_name} for timezone lookup: {e}")
            continue

    # If no timezone found, try a more expensive certain_timezone_at approach
    if not timezone_id:
        try:
            # This does a more intensive search including nearby points
            timezone_id = _timezone_finder.certain_timezone_at(lat=latitude, lng=longitude)
            if timezone_id:
                method_used = "TimezoneFinder.certain_timezone_at"
                confidence = 0.9  # Slightly lower confidence as this uses approximation
        except Exception as e:
            logger.warning(f"Error using TimezoneFinder.certain_timezone_at: {e}")

    # If still no timezone found, try a closest match
    if not timezone_id:
        try:
            # Find closest timezone within max_distance (default 1 degree ~ 111km)
            max_distance = 1.0  # degrees
            closest_tz = _timezone_finder.closest_timezone_at(lat=latitude, lng=longitude, delta_degree=max_distance)
            if closest_tz:
                timezone_id = closest_tz
                method_used = "TimezoneFinder.closest_timezone_at"
                confidence = 0.8  # Lower confidence for approximate match
            else:
                # Last resort: try further distance (3 degrees ~ 333km)
                closest_tz = _timezone_finder.closest_timezone_at(lat=latitude, lng=longitude, delta_degree=3.0)
                if closest_tz:
                    timezone_id = closest_tz
                    method_used = "TimezoneFinder.closest_timezone_at (extended)"
                    confidence = 0.6  # Much lower confidence for extended range
        except Exception as e:
            logger.warning(f"Error using TimezoneFinder.closest_timezone_at: {e}")

    # If still no timezone found, fallback to default with warning
    if not timezone_id:
        logger.warning(f"Could not determine timezone for ({latitude}, {longitude}). Using fallback timezone.")
        timezone_id = DEFAULT_TIMEZONE
        method_used = "fallback"
        confidence = 0.1  # Very low confidence for fallback

    # Get the pytz timezone object
    try:
        tz_obj = pytz.timezone(timezone_id)
    except UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {timezone_id}. Using UTC.")
        tz_obj = pytz.UTC
        timezone_id = "UTC"
        method_used = "fallback to UTC"
        confidence = 0.0  # No confidence in this result

    # Get current datetime in UTC
    now_utc = datetime.now(tz.utc)

    # Get current offset
    now_local = now_utc.astimezone(tz_obj)
    offset = now_local.utcoffset()
    offset_seconds = 0 if offset is None else offset.total_seconds()
    offset_hours = offset_seconds / 3600

    # Get timezone name and DST information
    tzname = now_local.tzname()

    # Check for DST by comparing winter and summer offsets
    winter_date = datetime(now_utc.year, 1, 1, tzinfo=tz.utc).astimezone(tz_obj)
    summer_date = datetime(now_utc.year, 7, 1, tzinfo=tz.utc).astimezone(tz_obj)
    winter_offset = winter_date.utcoffset()
    summer_offset = summer_date.utcoffset()
    has_dst = winter_offset != summer_offset

    return {
        "timezone": timezone_id,
        "timezone_id": timezone_id,
        "offset": int(offset_seconds),
        "offset_hours": offset_hours,
        "name": tzname,
        "has_dst": has_dst,
        "confidence": confidence,
        "method": method_used
    }

def convert_to_timezone(dt: datetime, timezone_id: str) -> datetime:
    """
    Convert a datetime to a specific timezone.

    Args:
        dt: The datetime object to convert
        timezone_id: IANA timezone identifier (e.g., 'America/New_York')

    Returns:
        Datetime object in the specified timezone

    Raises:
        ValueError: If the timezone is invalid
    """
    try:
        # Ensure the datetime has a timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.utc)

        # Get the target timezone
        target_tz = pytz.timezone(timezone_id)

        # Convert to the target timezone
        return dt.astimezone(target_tz)
    except UnknownTimeZoneError:
        raise ValueError(f"Invalid timezone: {timezone_id}")

def get_current_offset(timezone_id: str) -> int:
    """
    Get the current UTC offset in seconds for a timezone.

    Args:
        timezone_id: IANA timezone identifier (e.g., 'America/New_York')

    Returns:
        Current offset from UTC in seconds

    Raises:
        ValueError: If the timezone is invalid
    """
    try:
        # Get the timezone object
        tz_obj = pytz.timezone(timezone_id)

        # Get current time in the timezone
        now_utc = datetime.now(tz.utc)
        now_local = now_utc.astimezone(tz_obj)

        # Get the offset
        offset = now_local.utcoffset()
        if offset is None:
            return 0
        return int(offset.total_seconds())
    except UnknownTimeZoneError:
        raise ValueError(f"Invalid timezone: {timezone_id}")

def get_dst_transitions(timezone_id: str, year: int) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Get the DST transition dates for a specific timezone and year.

    Args:
        timezone_id: IANA timezone identifier (e.g., 'America/New_York')
        year: The year to check

    Returns:
        Tuple of (start_dst, end_dst) datetimes, or (None, None) if no DST

    Raises:
        ValueError: If the timezone is invalid
    """
    try:
        tz_obj = pytz.timezone(timezone_id)
    except UnknownTimeZoneError:
        raise ValueError(f"Invalid timezone: {timezone_id}")

    transitions = []

    # Check each day of the year for DST transitions
    start_date = datetime(year, 1, 1, tzinfo=tz.utc)

    # For efficiency, first check if the timezone has DST at all
    jan_offset = start_date.astimezone(tz_obj).utcoffset()
    jul_offset = datetime(year, 7, 1, tzinfo=tz.utc).astimezone(tz_obj).utcoffset()

    if jan_offset == jul_offset:
        # No DST in this timezone
        return None, None

    # Check each day for transitions
    current_date = start_date
    prev_offset = None

    for _ in range(366):  # Account for leap years
        local_dt = current_date.astimezone(tz_obj)
        current_offset = local_dt.utcoffset()

        if prev_offset is not None and current_offset != prev_offset:
            # Found a transition
            transitions.append(current_date)

            # If we've found two transitions, we're done
            if len(transitions) >= 2:
                break

        prev_offset = current_offset
        current_date += timedelta(days=1)

        # Don't go beyond the year
        if current_date.year > year:
            break

    # Return the transitions, or None if not found
    if len(transitions) >= 2:
        return transitions[0], transitions[1]
    elif len(transitions) == 1:
        return transitions[0], None
    else:
        return None, None
