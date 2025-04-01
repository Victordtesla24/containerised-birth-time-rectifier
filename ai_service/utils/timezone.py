"""
Timezone utilities for working with locations.

This module provides functions for determining the timezone for a given location
based on coordinates. It raises proper exceptions when timezone lookup fails
instead of silently falling back to alternatives.
"""

import logging
import datetime
from typing import Dict, Optional, Any, Tuple
from zoneinfo import ZoneInfo, available_timezones

import timezonefinder
import pytz

# Custom exception for timezone errors
class TimezoneError(Exception):
    """Exception raised when timezone resolution fails."""
    pass

logger = logging.getLogger(__name__)

# Initialize timezone finder once
_timezone_finder = timezonefinder.TimezoneFinder()

def get_timezone_for_coordinates(
    latitude: float,
    longitude: float
) -> str:
    """
    Determine the timezone for a given latitude and longitude.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees

    Returns:
        Timezone string (e.g., 'America/New_York')

    Raises:
        TimezoneError: If the timezone cannot be determined
        ValueError: If the coordinates are invalid
    """
    # Validate coordinates
    if not -90 <= latitude <= 90:
        raise ValueError(f"Invalid latitude: {latitude}. Must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError(f"Invalid longitude: {longitude}. Must be between -180 and 180.")

    try:
        logger.info(f"Looking up timezone for coordinates: {latitude}, {longitude}")

        # Try to get the timezone from coordinates
        timezone_str = _timezone_finder.timezone_at(lat=latitude, lng=longitude)

        if not timezone_str:
            # No exact match, try the closest timezone
            timezone_str = _timezone_finder.closest_timezone_at(
                lat=latitude,
                lng=longitude,
                delta_degree=3  # Search within 3 degrees (~300km at equator)
            )

        # Ensure we have a string, not a tuple or other type
        if timezone_str is None:
            raise TimezoneError(f"Could not determine timezone for coordinates: {latitude}, {longitude}")

        # Ensure we're returning a string
        timezone_str = str(timezone_str)

        # Validate that the timezone exists in the pytz database
        if timezone_str not in pytz.all_timezones:
            raise TimezoneError(f"Invalid timezone identifier: {timezone_str}")

        logger.info(f"Found timezone {timezone_str} for coordinates {latitude}, {longitude}")
        return timezone_str

    except Exception as e:
        if isinstance(e, TimezoneError):
            raise

        logger.error(f"Error determining timezone for coordinates {latitude}, {longitude}: {str(e)}")
        raise TimezoneError(f"Failed to determine timezone: {str(e)}")

def get_utc_offset(timezone_str: str, dt: Optional[datetime.datetime] = None) -> int:
    """
    Get the UTC offset in minutes for a timezone at a specific date and time.

    Args:
        timezone_str: Timezone string (e.g., 'America/New_York')
        dt: Datetime for which to calculate the offset (default: current time)

    Returns:
        UTC offset in minutes

    Raises:
        TimezoneError: If the timezone is invalid or the offset cannot be determined
    """
    if not timezone_str:
        raise TimezoneError("Timezone string cannot be empty")

    try:
        # Default to current time if not provided
        if dt is None:
            dt = datetime.datetime.now()

        # Get the timezone
        timezone = pytz.timezone(timezone_str)

        # Localize the datetime to get the correct DST information
        localized_dt = timezone.localize(dt.replace(tzinfo=None))

        # Get the UTC offset in seconds - safely handle potential None value
        utc_offset = localized_dt.utcoffset()
        if utc_offset is None:
            raise TimezoneError(f"Could not determine UTC offset for timezone {timezone_str}")

        offset_seconds = utc_offset.total_seconds()

        # Convert to minutes
        offset_minutes = int(offset_seconds / 60)

        return offset_minutes

    except pytz.exceptions.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {timezone_str}")
        raise TimezoneError(f"Unknown timezone: {timezone_str}")
    except Exception as e:
        logger.error(f"Error calculating UTC offset for timezone {timezone_str}: {str(e)}")
        raise TimezoneError(f"Failed to calculate UTC offset: {str(e)}")

def convert_to_timezone(
    dt: datetime.datetime,
    source_timezone: str,
    target_timezone: str
) -> datetime.datetime:
    """
    Convert a datetime from one timezone to another.

    Args:
        dt: Datetime to convert
        source_timezone: Source timezone string
        target_timezone: Target timezone string

    Returns:
        Converted datetime

    Raises:
        TimezoneError: If the timezone conversion fails
    """
    if not source_timezone or not target_timezone:
        raise TimezoneError("Source and target timezone strings cannot be empty")

    try:
        # Get the timezone objects
        source_tz = pytz.timezone(source_timezone)
        target_tz = pytz.timezone(target_timezone)

        # Handle naive datetime objects properly
        if dt.tzinfo is None:
            # For naive datetimes, use localize to attach the timezone
            # This properly handles DST transitions
            localized_dt = source_tz.localize(dt)
        else:
            # If datetime already has timezone info
            # First normalize to UTC then to source timezone to ensure correct handling
            utc_dt = dt.astimezone(pytz.UTC)
            localized_dt = utc_dt.astimezone(source_tz)

        # Convert to the target timezone
        converted_dt = localized_dt.astimezone(target_tz)

        return converted_dt

    except pytz.exceptions.UnknownTimeZoneError as e:
        logger.error(f"Unknown timezone: {str(e)}")
        raise TimezoneError(f"Unknown timezone: {str(e)}")
    except Exception as e:
        logger.error(f"Error converting datetime between timezones: {str(e)}")
        raise TimezoneError(f"Failed to convert datetime between timezones: {str(e)}")

def is_dst_at_datetime(timezone_str: str, dt: datetime.datetime) -> bool:
    """
    Check if daylight saving time is in effect for a timezone at a specific datetime.

    Args:
        timezone_str: Timezone string
        dt: Datetime to check

    Returns:
        True if DST is in effect, False otherwise

    Raises:
        TimezoneError: If the timezone is invalid or the DST status cannot be determined
    """
    if not timezone_str:
        raise TimezoneError("Timezone string cannot be empty")

    try:
        # Get the timezone
        timezone = pytz.timezone(timezone_str)

        # Localize the datetime to get DST information
        localized_dt = timezone.localize(dt.replace(tzinfo=None))

        # Check if DST is in effect
        return localized_dt.dst() != datetime.timedelta(0)

    except pytz.exceptions.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {timezone_str}")
        raise TimezoneError(f"Unknown timezone: {timezone_str}")
    except Exception as e:
        logger.error(f"Error checking DST status for timezone {timezone_str}: {str(e)}")
        raise TimezoneError(f"Failed to check DST status: {str(e)}")

def get_timezone_info(
    lat: float,
    lon: float,
    dt: Optional[datetime.datetime] = None
) -> Dict[str, Any]:
    """
    Get comprehensive timezone information for coordinates at a specific datetime.

    Args:
        lat: Latitude
        lon: Longitude
        dt: Datetime for which to get timezone info (default: current time)

    Returns:
        Dictionary with timezone information

    Raises:
        TimezoneError: If the timezone information cannot be determined
    """
    if dt is None:
        dt = datetime.datetime.now()

    try:
        # Get the timezone string
        timezone_str = get_timezone_for_coordinates(lat, lon)

        # Get the timezone object
        timezone = pytz.timezone(timezone_str)

        # Localize the datetime
        localized_dt = timezone.localize(dt.replace(tzinfo=None))

        # Calculate the UTC offset
        utc_offset_minutes = get_utc_offset(timezone_str, dt)
        hours, minutes = divmod(abs(utc_offset_minutes), 60)
        offset_str = f"{'-' if utc_offset_minutes < 0 else '+'}{hours:02d}:{minutes:02d}"

        # Check if DST is in effect
        is_dst = is_dst_at_datetime(timezone_str, dt)

        # Construct the result
        result = {
            "timezone": timezone_str,
            "offset_minutes": utc_offset_minutes,
            "offset_string": offset_str,
            "is_dst": is_dst,
            "datetime_local": localized_dt.strftime("%Y-%m-%d %H:%M:%S %Z%z"),
            "coordinates": {
                "latitude": lat,
                "longitude": lon
            }
        }

        return result

    except Exception as e:
        if isinstance(e, (TimezoneError, ValueError)):
            raise

        logger.error(f"Error getting timezone info for coordinates {lat}, {lon}: {str(e)}")
        raise TimezoneError(f"Failed to get timezone information: {str(e)}")

def get_timezone_abbreviation(timezone_str: str, dt: Optional[datetime.datetime] = None) -> str:
    """
    Get the abbreviation for a timezone at a specific datetime.

    Args:
        timezone_str: Timezone string
        dt: Datetime for which to get the abbreviation (default: current time)

    Returns:
        Timezone abbreviation (e.g., 'EST', 'EDT')

    Raises:
        TimezoneError: If the timezone abbreviation cannot be determined
    """
    if dt is None:
        dt = datetime.datetime.now()

    try:
        # Get the timezone
        timezone = pytz.timezone(timezone_str)

        # Localize the datetime
        localized_dt = timezone.localize(dt.replace(tzinfo=None))

        # Get the abbreviation
        abbreviation = localized_dt.strftime("%Z")

        # If the abbreviation is just a numeric offset, use the timezone name
        if abbreviation.startswith(("GMT", "UTC")) and ('+' in abbreviation or '-' in abbreviation):
            is_dst = is_dst_at_datetime(timezone_str, dt)
            timezone_parts = timezone_str.split('/')
            if len(timezone_parts) > 1:
                # Use the last part of the timezone name
                abbreviation = timezone_parts[-1]
                # Add a 'D' for Daylight Time if DST is in effect
                if is_dst:
                    abbreviation = f"{abbreviation[0]}DT"
                else:
                    abbreviation = f"{abbreviation[0]}ST"

        return abbreviation

    except pytz.exceptions.UnknownTimeZoneError:
        logger.error(f"Unknown timezone: {timezone_str}")
        raise TimezoneError(f"Unknown timezone: {timezone_str}")
    except Exception as e:
        logger.error(f"Error getting timezone abbreviation for {timezone_str}: {str(e)}")
        raise TimezoneError(f"Failed to get timezone abbreviation: {str(e)}")

def validate_timezone(timezone_str: str) -> bool:
    """
    Validate that a timezone string exists in the timezone database.

    Args:
        timezone_str: Timezone string to validate

    Returns:
        True if the timezone is valid, False otherwise
    """
    try:
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False
