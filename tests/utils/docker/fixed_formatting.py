"""
Utility functions for formatting astrological data.

This module provides formatting utilities for displaying chart data in a consistent manner.
"""

import math
import re
from datetime import datetime
from typing import Union, Optional, Tuple

def format_degree(degree: float, include_sign: bool = False, include_minutes: bool = True) -> str:
def format_degree(degree: float, include_sign: bool = False, include_minutes: bool = True) -> str:
    """
    """
    Format a degree value into a human-readable format.
    Format a degree value into a human-readable format.


    Args:
    Args:
        degree: Degree value (0-360)
        degree: Degree value (0-360)
        include_sign: Whether to include the zodiac sign
        include_sign: Whether to include the zodiac sign
        include_minutes: Whether to include minutes in addition to degrees
        include_minutes: Whether to include minutes in addition to degrees


    Returns:
    Returns:
        Formatted degree string (e.g., "15°30'" or "Leo 15°30'")
        Formatted degree string (e.g., "15°30'" or "Leo 15°30'")
    """
    """
    # Normalize degree value to 0-360 range
    # Normalize degree value to 0-360 range
    degree = degree % 360
    degree = degree % 360


    # Get zodiac sign if requested
    # Get zodiac sign if requested
    sign_name = ""
    sign_name = ""
    if include_sign:
    if include_sign:
        signs = [
        signs = [
            "Aries", "Taurus", "Gemini", "Cancer",
            "Aries", "Taurus", "Gemini", "Cancer",
            "Leo", "Virgo", "Libra", "Scorpio",
            "Leo", "Virgo", "Libra", "Scorpio",
            "Sagittarius", "Capricorn", "Aquarius", "Pisces"
            "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        ]
        sign_index = int(degree / 30)
        sign_index = int(degree / 30)
        sign_name = signs[sign_index] + " "
        sign_name = signs[sign_index] + " "


    # Calculate degrees within sign
    # Calculate degrees within sign
    degree_in_sign = degree % 30
    degree_in_sign = degree % 30


    # Format degrees and minutes
    # Format degrees and minutes
    degree_part = int(degree_in_sign)
    degree_part = int(degree_in_sign)


    if include_minutes:
    if include_minutes:
        minutes_part = int((degree_in_sign - degree_part) * 60)
        minutes_part = int((degree_in_sign - degree_part) * 60)
        return f"{sign_name}{degree_part}°{minutes_part}'"
        return f"{sign_name}{degree_part}°{minutes_part}'"
    else:
    else:
        return f"{sign_name}{degree_part}°"
        return f"{sign_name}{degree_part}°"


def format_longitude(longitude: float, format_type: str = "full") -> str:
def format_longitude(longitude: float, format_type: str = "full") -> str:
    """
    """
    Format a celestial longitude into a human-readable format.
    Format a celestial longitude into a human-readable format.


    Args:
    Args:
        longitude: Celestial longitude in degrees (0-360)
        longitude: Celestial longitude in degrees (0-360)
        format_type: Format type: "full", "sign_only", "degree_only"
        format_type: Format type: "full", "sign_only", "degree_only"


    Returns:
    Returns:
        Formatted longitude string
        Formatted longitude string
    """
    """
    # Normalize longitude value to 0-360 range
    # Normalize longitude value to 0-360 range
    longitude = longitude % 360
    longitude = longitude % 360


    # Define zodiac signs
    # Define zodiac signs
    signs = [
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]
    ]


    # Get sign and position within sign
    # Get sign and position within sign
    sign_index = int(longitude / 30)
    sign_index = int(longitude / 30)
    sign_name = signs[sign_index]
    sign_name = signs[sign_index]
    pos_in_sign = longitude % 30
    pos_in_sign = longitude % 30


    # Format based on requested format type
    # Format based on requested format type
    if format_type == "sign_only":
    if format_type == "sign_only":
        return sign_name
        return sign_name
    elif format_type == "degree_only":
    elif format_type == "degree_only":
        return format_degree(pos_in_sign, include_sign=False)
        return format_degree(pos_in_sign, include_sign=False)
    else:  # "full" format
    else:  # "full" format
        degree_part = int(pos_in_sign)
        degree_part = int(pos_in_sign)
        minutes_part = int((pos_in_sign - degree_part) * 60)
        minutes_part = int((pos_in_sign - degree_part) * 60)
        return f"{sign_name} {degree_part}°{minutes_part}'"
        return f"{sign_name} {degree_part}°{minutes_part}'"


def format_time(time_value: Union[str, datetime], include_seconds: bool = True) -> str:
def format_time(time_value: Union[str, datetime], include_seconds: bool = True) -> str:
    """
    """
    Format a time value into a consistent human-readable format.
    Format a time value into a consistent human-readable format.


    Args:
    Args:
        time_value: Time value as string or datetime object
        time_value: Time value as string or datetime object
        include_seconds: Whether to include seconds in the formatted output
        include_seconds: Whether to include seconds in the formatted output


    Returns:
    Returns:
        Formatted time string (e.g., "14:30:00" or "14:30")
        Formatted time string (e.g., "14:30:00" or "14:30")
    """
    """
    # Convert string to datetime if needed
    # Convert string to datetime if needed
    if isinstance(time_value, str):
    if isinstance(time_value, str):
        # Try different formats
        # Try different formats
        formats = [
        formats = [
            "%H:%M:%S",
            "%H:%M:%S",
            "%H:%M",
            "%H:%M",
            "%I:%M:%S %p",
            "%I:%M:%S %p",
            "%I:%M %p",
            "%I:%M %p",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M"
            "%Y-%m-%d %H:%M"
        ]
        ]


        for fmt in formats:
        for fmt in formats:
            try:
            try:
                time_value = datetime.strptime(time_value, fmt)
                time_value = datetime.strptime(time_value, fmt)
                break
                break
            except ValueError:
            except ValueError:
                continue
                continue
        else:
        else:
            # If no format matched, return the original string
            # If no format matched, return the original string
            return time_value
            return time_value


    # Format datetime object
    # Format datetime object
    if isinstance(time_value, datetime):
    if isinstance(time_value, datetime):
        if include_seconds:
        if include_seconds:
            return time_value.strftime("%H:%M:%S")
            return time_value.strftime("%H:%M:%S")
        else:
        else:
            return time_value.strftime("%H:%M")
            return time_value.strftime("%H:%M")


    # If we couldn't parse the input, return it as is
    # If we couldn't parse the input, return it as is
    return str(time_value)
    return str(time_value)


def format_aspect(aspect_type: str, orb: float) -> str:
def format_aspect(aspect_type: str, orb: float) -> str:
    """
    """
    Format an astrological aspect.
    Format an astrological aspect.


    Args:
    Args:
        aspect_type: Type of aspect (conjunction, trine, square, etc.)
        aspect_type: Type of aspect (conjunction, trine, square, etc.)
        orb: Orb value in degrees
        orb: Orb value in degrees


    Returns:
    Returns:
        Formatted aspect string
        Formatted aspect string
    """
    """
    aspect_symbols = {
    aspect_symbols = {
        "conjunction": "☌",
        "conjunction": "☌",
        "opposition": "☍",
        "opposition": "☍",
        "trine": "△",
        "trine": "△",
        "square": "□",
        "square": "□",
        "sextile": "⚹",
        "sextile": "⚹",
        "quincunx": "⚻",
        "quincunx": "⚻",
        "semisextile": "⚺",
        "semisextile": "⚺",
        "semisquare": "⚼",
        "semisquare": "⚼",
        "sesquiquadrate": "⚿"
        "sesquiquadrate": "⚿"
    }
    }


    symbol = aspect_symbols.get(aspect_type.lower(), "")
    symbol = aspect_symbols.get(aspect_type.lower(), "")
    if symbol:
    if symbol:
        return f"{symbol} ({orb:.1f}°)"
        return f"{symbol} ({orb:.1f}°)"
    else:
    else:
        return f"{aspect_type.capitalize()} ({orb:.1f}°)"
        return f"{aspect_type.capitalize()} ({orb:.1f}°)"


def format_planet_position(planet: str, sign: str, degree: float, house: Optional[int] = None) -> str:
def format_planet_position(planet: str, sign: str, degree: float, house: Optional[int] = None) -> str:
    """
    """
    Format a planet's position in a chart.
    Format a planet's position in a chart.


    Args:
    Args:
        planet: Planet name
        planet: Planet name
        sign: Zodiac sign
        sign: Zodiac sign
        degree: Degree within sign
        degree: Degree within sign
        house: Optional house number
        house: Optional house number


    Returns:
    Returns:
        Formatted planet position string
        Formatted planet position string
    """
    """
    # Define planet symbols
    # Define planet symbols
    planet_symbols = {
    planet_symbols = {
        "Sun": "☉",
        "Sun": "☉",
        "Moon": "☽",
        "Moon": "☽",
        "Mercury": "☿",
        "Mercury": "☿",
        "Venus": "♀",
        "Venus": "♀",
        "Mars": "♂",
        "Mars": "♂",
        "Jupiter": "♃",
        "Jupiter": "♃",
        "Saturn": "♄",
        "Saturn": "♄",
        "Uranus": "♅",
        "Uranus": "♅",
        "Neptune": "♆",
        "Neptune": "♆",
        "Pluto": "♇",
        "Pluto": "♇",
        "Rahu": "☊",
        "Rahu": "☊",
        "Ketu": "☋"
        "Ketu": "☋"
    }
    }


    # Get planet symbol or name
    # Get planet symbol or name
    planet_sym = planet_symbols.get(planet, planet)
    planet_sym = planet_symbols.get(planet, planet)


    # Format position
    # Format position
    pos_str = format_degree(degree, include_sign=False)
    pos_str = format_degree(degree, include_sign=False)


    # Include house information if provided
    # Include house information if provided
    if house is not None:
    if house is not None:
        return f"{planet_sym} {sign} {pos_str} (House {house})"
        return f"{planet_sym} {sign} {pos_str} (House {house})"
    else:
    else:
        return f"{planet_sym} {sign} {pos_str}"
        return f"{planet_sym} {sign} {pos_str}"
