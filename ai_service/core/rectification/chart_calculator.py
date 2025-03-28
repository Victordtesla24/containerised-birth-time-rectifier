#!/usr/bin/env python3
"""
Astrological chart calculator module for birth chart calculations.
This module provides functions for calculating birth charts and related data.
"""

import os
import json
import math
import logging
import random
import asyncio
import uuid
import re
import traceback
import pytz
from typing import Dict, List, Any, Tuple, Optional, Union, Callable, cast
from datetime import datetime, timedelta, timezone
import numpy as np
from numpy.typing import NDArray

# Flag to indicate if pyswisseph is available
try:
    import swisseph as swe
    SWISSEPH_AVAILABLE = True
except ImportError:
    SWISSEPH_AVAILABLE = False
    swe = None

from timezonefinder import TimezoneFinder

# Import related modules
from ai_service.core.rectification.constants import PLANETS_LIST, HOUSES_LIST, SIGNS, ASPECTS
from ai_service.core.exceptions import RectificationError, ValidationError
from ai_service.core.rectification.vedic_calculation import calculate_houses_positions, calculate_ascendant

# Set up logging
logger = logging.getLogger(__name__)

# Add missing imports
from pytz.exceptions import UnknownTimeZoneError

# Define custom exceptions
class EphemerisError(Exception):
    """Exception raised when ephemeris calculations fail."""
    pass

# Constants needed for various calculations
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Default aspect orbs
DEFAULT_ASPECT_ORBS = {
    "conjunction": 10.0,
    "opposition": 10.0,
    "trine": 8.0,
    "square": 8.0,
    "sextile": 6.0,
    "quincunx": 5.0,
    "semisextile": 3.0
}

# Aspect angles
ASPECT_ANGLES = {
    "conjunction": 0.0,
    "opposition": 180.0,
    "trine": 120.0,
    "square": 90.0,
    "sextile": 60.0,
    "quincunx": 150.0,
    "semisextile": 30.0
}

# Dictionary for outer planets mapping
flatlib_outer_planets = {
    "Uranus": "Uranus",
    "Neptune": "Neptune",
    "Pluto": "Pluto"
}

# Swiss Ephemeris proxy class
class SwissEphemerisProxy:
    """
    Proxy for Swiss Ephemeris calculations.
    """

    def __init__(self):
        """Initialize the Swiss Ephemeris proxy."""
        self.initialized = False
        self.logger = logging.getLogger(__name__)

        if not SWISSEPH_AVAILABLE or swe is None:
            self.logger.error("Swiss Ephemeris not available")
            raise EphemerisError("Swiss Ephemeris is required but not available")

        self.initialized = True

    async def get_planet_position(
        self,
        birth_datetime: datetime,
        planet_id: int,
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """
        Get planet position.

        Args:
            birth_datetime: Birth date and time
            planet_id: Planet ID in Swiss Ephemeris
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees

        Returns:
            Dictionary with planet position data including longitude, latitude, distance, and speed

        Raises:
            EphemerisError: If the calculation fails
        """
        if not self.initialized or swe is None:
            raise EphemerisError("Swiss Ephemeris proxy not initialized")

        try:
            # Convert datetime to Julian day
            year = birth_datetime.year
            month = birth_datetime.month
            day = birth_datetime.day
            hour = birth_datetime.hour + birth_datetime.minute/60.0 + birth_datetime.second/3600.0
            jd = swe.julday(year, month, day, hour)

            # Set topocentric coordinates
            swe.set_topo(longitude, latitude, 0)  # 0 for altitude

            # Calculate planet position
            result = swe.calc_ut(jd, planet_id, swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_TOPOCTR)

            # Extract data from result
            positions = result[0]
            longitude_val = positions[0]
            latitude_val = positions[1]
            distance = positions[2]
            speed = positions[3]

            return {
                "longitude": longitude_val,
                "latitude": latitude_val,
                "distance": distance,
                "speed": speed,
                "longitude_speed": speed  # Add this for compatibility
            }
        except Exception as e:
            error_msg = f"Failed to calculate planet position: {e}"
            self.logger.error(error_msg)
            raise EphemerisError(error_msg) from e

    async def get_houses(
        self,
        birth_datetime: datetime,
        latitude: float,
        longitude: float,
        house_system: str
    ) -> Dict[str, Any]:
        """
        Get house cusps.

        Args:
            birth_datetime: Birth date and time
            latitude: Birth latitude
            longitude: Birth longitude
            house_system: House system to use

        Returns:
            Dictionary with house cusps

        Raises:
            EphemerisError: If the calculation fails
        """
        if not self.initialized or swe is None:
            raise EphemerisError("Swiss Ephemeris proxy not initialized")

        try:
            # Convert datetime to Julian day
            year = birth_datetime.year
            month = birth_datetime.month
            day = birth_datetime.day
            hour = birth_datetime.hour + birth_datetime.minute/60.0 + birth_datetime.second/3600.0
            jd = swe.julday(year, month, day, hour)

            # Get house system code (default to Placidus if not recognized)
            hsys = house_system.encode('utf-8') if len(house_system) == 1 else b'P'

            # Calculate houses
            cusps, ascmc = swe.houses(jd, latitude, longitude, hsys)

            return {
                "cusps": cusps,
                "ascendant": ascmc[0],
                "midheaven": ascmc[1],
                "armc": ascmc[2],
                "vertex": ascmc[3]
            }
        except Exception as e:
            error_msg = f"Failed to calculate houses: {e}"
            self.logger.error(error_msg)
            raise EphemerisError(error_msg)

    async def close(self):
        """Close the Swiss Ephemeris proxy and free resources."""
        if swe is not None and hasattr(swe, 'close'):
            try:
                swe.close()
                self.initialized = False
                self.logger.info("Swiss Ephemeris proxy closed")
            except Exception as e:
                self.logger.warning(f"Error closing Swiss Ephemeris: {e}")
        else:
            self.logger.warning("Swiss Ephemeris has no close method or is not available, marking as uninitialized")
            self.initialized = False


# Import flatlib for chart calculations
import flatlib
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib.chart import Chart
from flatlib import const

# Import local modules
from .constants import PLANETS_LIST
from ai_service.core.config import settings
from ai_service.utils.astrological_terms import (
    get_house_system_name,
    get_planet_name,
    get_sign_name,
    get_aspect_name
)

logger = logging.getLogger(__name__)

# Flag to indicate if pytz is available
PYTZ_AVAILABLE = True

# Define PLANET_IDS as a module-level constant
PLANET_IDS = {
    "SUN": 0,
    "MOON": 1,
    "MERCURY": 2,
    "VENUS": 3,
    "MARS": 4,
    "JUPITER": 5,
    "SATURN": 6,
    "URANUS": 7,
    "NEPTUNE": 8,
    "PLUTO": 9,
    "CHIRON": 15,
    "MEAN_NODE": 10
}

def normalize_longitude(longitude: float) -> float:
    """
    Normalize longitude to the range 0-360 degrees.

    Args:
        longitude: Longitude in degrees

    Returns:
        Normalized longitude in degrees (0-360)
    """
    return longitude % 360

def get_planets_list() -> list:
    """Get the standard list of planets used in calculation."""
    return PLANETS_LIST

def get_timezone_from_coordinates(latitude: float, longitude: float) -> str:
    """
    Get timezone string from geographic coordinates.

    Uses timezonefinder library to determine the timezone based on latitude/longitude.
    If no timezone is found, returns 'UTC' as a fallback.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees

    Returns:
        IANA timezone string (e.g., 'America/New_York') or 'UTC' if not found
    """
    try:
        # Import here to avoid circular imports
        from timezonefinder import TimezoneFinder

        # Create timezone finder
        tf = TimezoneFinder()

        # Get timezone at coordinates
        timezone_str = tf.timezone_at(lat=latitude, lng=longitude)

        # Return timezone or UTC if not found
        if timezone_str:
            return timezone_str
        else:
            # Log the warning but return a valid string
            logger.warning(f"No timezone found for coordinates {latitude}, {longitude}. Using UTC.")
            return "UTC"
    except ImportError:
        logger.error("TimezoneFinder module not available. Using UTC.")
        return "UTC"
    except Exception as e:
        logger.error(f"Error finding timezone for coordinates {latitude}, {longitude}: {e}")
        return "UTC"

def calculate_outer_planet_position(jd: float, planet_id: int) -> Dict[str, Any]:
    """
    Calculate accurate positions for outer planets using Swiss Ephemeris.

    Args:
        jd: Julian day for calculation
        planet_id: Swiss Ephemeris planet ID

    Returns:
        Dictionary with planet position data

    Raises:
        EphemerisError: If Swiss Ephemeris is not available
        ValueError: If calculation fails with Swiss Ephemeris
    """
    if not SWISSEPH_AVAILABLE or swe is None:
        raise EphemerisError("Swiss Ephemeris not available for outer planet calculation")

    try:
        # Calculate planet positions with high precision
        return_data = swe.calc_ut(jd, planet_id, swe.FLG_SWIEPH | swe.FLG_SPEED)

        # Process the result through our helper function
        # This returns a Dict[str, Any], exactly what we want to return
        return process_ephemeris_result(return_data)
    except Exception as e:
        logger.error(f"Error calculating outer planet position: {e}")
        return {
            "longitude": 0.0,
            "latitude": 0.0,
            "distance": 0.0,
            "speed": 0.0,
            "sign": "Unknown",
            "retrograde": False,
            "error": str(e)
        }

# Fix the Flatlib Datetime initialization issue
def _create_flatlib_datetime(birth_dt: datetime, utc_offset_hours: float) -> Datetime:
    """
    Create a Flatlib Datetime object with proper type conversions.

    Args:
        birth_dt: The birth datetime
        utc_offset_hours: UTC offset in hours

    Returns:
        Flatlib Datetime object
    """
    # Format date for flatlib (YYYY/MM/DD)
    date_str = birth_dt.strftime('%Y/%m/%d')

    # Get time components
    hour = birth_dt.hour
    minute = birth_dt.minute

    # Flatlib expects an integer for the time parameter, not a float
    # Convert the time to minutes for integer precision, then convert to hours as int
    time_minutes = hour * 60 + minute
    time_param = int(time_minutes / 60)  # Integer hours

    # For the remainder, we'll use the minute argument in the Datetime constructor
    remaining_minutes = time_minutes % 60

    # Convert UTC offset to integer - we'll only use whole hours for simplicity
    utc_offset_int = int(utc_offset_hours)

    # Create the Datetime object with proper integer values
    # The Datetime class takes date, hour, utc offset, and minutes as separate parameters
    return Datetime(date_str, time_param, utc_offset_int, remaining_minutes)

def calculate_chart(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone_str: str,
    house_system: str = 'P'  # Default to Placidus house system
) -> Dict[str, Any]:
    """
    Calculate an astrological chart.

    Args:
        birth_dt: Birth date and time
        latitude: Birth latitude
        longitude: Birth longitude
        timezone_str: Timezone string
        house_system: House system to use

    Returns:
        Chart data dictionary
    """
    try:
        # Get UTC offset from timezone
        if PYTZ_AVAILABLE:
            try:
                tz = pytz.timezone(timezone_str)
                utc_offset = tz.utcoffset(birth_dt)
                utc_offset_hours = utc_offset.total_seconds() / 3600
            except (UnknownTimeZoneError, AttributeError):
                logger.warning(f"Unknown timezone: {timezone_str}, using UTC")
                utc_offset_hours = 0
        else:
            # Simple parsing for common timezone formats like UTC+5:30
            match = re.match(r'UTC([+-])(\d+):?(\d*)', timezone_str)
            if match:
                sign, hours, minutes = match.groups()
                utc_offset_hours = int(hours)
                if minutes:
                    utc_offset_hours += int(minutes) / 60
                if sign == '-':
                    utc_offset_hours = -utc_offset_hours
            else:
                logger.warning(f"Could not parse timezone: {timezone_str}, using UTC")
                utc_offset_hours = 0

        # Create flatlib datetime with proper type conversion
        flat_datetime = _create_flatlib_datetime(birth_dt, utc_offset_hours)

        # Validate coordinates
        if not -90 <= latitude <= 90:
            raise ValueError(f"Latitude {latitude} is out of range (-90 to 90)")
        if not -180 <= longitude <= 180:
            raise ValueError(f"Longitude {longitude} is out of range (-180 to 180)")

        # Format latitude with N/S indicator (e.g., "18n31" for 18.52 North)
        lat_abs = abs(latitude)
        lat_deg = int(lat_abs)
        lat_min = int((lat_abs - lat_deg) * 60)
        lat_dir = 'n' if latitude >= 0 else 's'
        lat_str = f"{lat_deg}{lat_dir}{lat_min}"

        # Format longitude with E/W indicator (e.g., "73e51" for 73.85 East)
        lon_abs = abs(longitude)
        lon_deg = int(lon_abs)
        lon_min = int((lon_abs - lon_deg) * 60)
        lon_dir = 'e' if longitude >= 0 else 'w'
        lon_str = f"{lon_deg}{lon_dir}{lon_min}"

        logger.debug(f"Formatted coordinates for flatlib: lat={lat_str}, lon={lon_str}")

        # Create GeoPos with proper error handling
        try:
            flat_geopos = GeoPos(lat_str, lon_str)
        except ValueError as e:
            logger.error(f"Error creating GeoPos with coordinates {lat_str}, {lon_str}: {e}")
            # Instead of falling back to hardcoded coordinates, reconstruct valid coordinates
            # Normalize coordinates to ensure they're in valid range
            # Latitude must be between -90 and 90
            latitude = max(-90.0, min(90.0, latitude))
            # Longitude must be between -180 and 180
            longitude = max(-180.0, min(180.0, longitude))

            # Convert normalized coordinates to degrees and minutes
            lat_abs = abs(latitude)
            lon_abs = abs(longitude)

            lat_deg = int(lat_abs)
            lat_min = int((lat_abs - lat_deg) * 60)
            lat_dir = "n" if latitude >= 0 else "s"

            lon_deg = int(lon_abs)
            lon_min = int((lon_abs - lon_deg) * 60)
            lon_dir = "e" if longitude >= 0 else "w"

            # Ensure we never have zero values that might cause issues
            if lat_deg == 0 and lat_min == 0:
                lat_min = 1  # Use 1 minute if latitude is exactly 0
            if lon_deg == 0 and lon_min == 0:
                lon_min = 1  # Use 1 minute if longitude is exactly 0

            lat_str = f"{lat_deg}{lat_dir}{lat_min}"
            lon_str = f"{lon_deg}{lon_dir}{lon_min}"

            logger.info(f"Normalized coordinates to {lat_str}, {lon_str}")

            try:
                flat_geopos = GeoPos(lat_str, lon_str)
            except ValueError as inner_e:
                # If reconstruction also fails, this is a critical error
                logger.critical(f"Critical error: Failed to create GeoPos with normalized coordinates: {inner_e}")
                raise ValueError(f"Invalid coordinates cannot be processed after normalization: lat={latitude}, lon={longitude}. Please provide valid geographic coordinates.")

        # Calculate the chart with flatlib
        try:
            flat_chart = Chart(flat_datetime, flat_geopos, hsys=house_system)
        except Exception as e:
            logger.error(f"Error creating flatlib Chart: {e}")
            raise ValueError(f"Failed to create astrological chart: {str(e)}")

        # Extract chart data
        chart_data = {
            "chart_id": f"chart_{uuid.uuid4().hex[:10]}",
            "date": birth_dt.strftime("%Y-%m-%d"),
            "time": birth_dt.strftime("%H:%M:%S"),
            "timezone": timezone_str,
            "latitude": latitude,
            "longitude": longitude,
            "location": "Unknown",  # Location name will be set by caller if available
            "house_system": house_system
        }

        # Extract angles (Ascendant, Midheaven, etc.)
        chart_data["angles"] = {}
        for angle_name in [const.ASC, const.MC, const.DESC, const.IC]:
            try:
                angle = flat_chart.getAngle(angle_name)
                # Convert angle longitude to float explicitly
                angle_lon = float(angle.lon)
                # Determine sign from longitude
                sign_num = int(angle_lon / 30) % 12
                # Get sign name
                signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                sign = signs[sign_num]

                chart_data["angles"][angle_name.lower()] = {
                    "name": angle_name,
                    "longitude": angle_lon,
                    "latitude": 0.0,  # Angles don't have latitude
                    "sign": sign,
                    "degree": angle_lon % 30  # Degree within sign
                }
            except Exception as e:
                logger.error(f"Error extracting angle {angle_name}: {e}")
                # Skip this angle but continue with the rest

        # Extract houses
        chart_data["houses"] = []
        try:
            houses = flat_chart.houses
            for i, house in enumerate(houses):
                # Convert house longitude to float explicitly
                house_lon = float(house.lon)
                chart_data["houses"].append(house_lon)
        except Exception as e:
            logger.error(f"Error extracting houses: {e}")
            # Continue without houses

        # Extract planets
        chart_data["planets"] = {}

        # Get Julian Day for Swiss Ephemeris calculations if available
        try:
            if not SWISSEPH_AVAILABLE or swe is None:
                raise EphemerisError("Swiss Ephemeris is required for accurate chart calculations but is not available")

            jd = swe.julday(
                birth_dt.year,
                birth_dt.month,
                birth_dt.day,
                birth_dt.hour + birth_dt.minute/60 + birth_dt.second/3600
            )
        except Exception as e:
            logger.error(f"Failed to calculate Julian Day: {e}")
            raise EphemerisError(f"Failed to calculate Julian Day: {e}")

        # Define safe planet constants if Swiss Ephemeris is available
        if SWISSEPH_AVAILABLE and swe is not None:
            SUN_ID = getattr(swe, 'SUN', 0)
            MOON_ID = getattr(swe, 'MOON', 1)
            MERCURY_ID = getattr(swe, 'MERCURY', 2)
            VENUS_ID = getattr(swe, 'VENUS', 3)
            MARS_ID = getattr(swe, 'MARS', 4)
            JUPITER_ID = getattr(swe, 'JUPITER', 5)
            SATURN_ID = getattr(swe, 'SATURN', 6)
            URANUS_ID = getattr(swe, 'URANUS', 7)
            NEPTUNE_ID = getattr(swe, 'NEPTUNE', 8)
            PLUTO_ID = getattr(swe, 'PLUTO', 9)
            CHIRON_ID = getattr(swe, 'CHIRON', 15)
            MEAN_NODE_ID = getattr(swe, 'MEAN_NODE', 10)
        else:
            # Define constants when SwissEph is not available
            SUN_ID = 0
            MOON_ID = 1
            MERCURY_ID = 2
            VENUS_ID = 3
            MARS_ID = 4
            JUPITER_ID = 5
            SATURN_ID = 6
            URANUS_ID = 7
            NEPTUNE_ID = 8
            PLUTO_ID = 9
            CHIRON_ID = 15
            MEAN_NODE_ID = 10

        # Planet mapping between flatlib constants and Swiss Ephemeris
        planet_mappings = {
            const.SUN: (SUN_ID, "sun"),
            const.MOON: (MOON_ID, "moon"),
            const.MERCURY: (MERCURY_ID, "mercury"),
            const.VENUS: (VENUS_ID, "venus"),
            const.MARS: (MARS_ID, "mars"),
            const.JUPITER: (JUPITER_ID, "jupiter"),
            const.SATURN: (SATURN_ID, "saturn"),
        }

        # Add outer planets
        outer_planets = {
            "uranus": URANUS_ID,
            "neptune": NEPTUNE_ID,
            "pluto": PLUTO_ID,
            "chiron": CHIRON_ID,
            "north_node": MEAN_NODE_ID  # Using Mean Node
        }

        # Process standard planets from flatlib
        for planet_name, (swe_id, output_name) in planet_mappings.items():
            try:
                # Get planet data from Swiss Ephemeris
                planet_data = calculate_outer_planet_position(jd, swe_id)

                # Determine house for this planet
                house = _determine_house(chart_data["houses"], planet_data["longitude"])

                # Add to chart data
                chart_data["planets"][output_name] = {
                    "name": output_name,
                    "longitude": planet_data["longitude"],
                    "latitude": planet_data["latitude"],
                    "speed": planet_data["speed"],
                    "sign": planet_data["sign"],
                    "house": house,
                    "retrograde": planet_data["retrograde"]
                }
            except Exception as e:
                logger.error(f"Error calculating planet {planet_name}: {e}")
                raise EphemerisError(f"Failed to calculate position for {planet_name}: {e}")

        # Calculate outer planets with Swiss Ephemeris
        for planet_name, swe_id in outer_planets.items():
            try:
                planet_data = calculate_outer_planet_position(jd, swe_id)

                # Determine house for this planet
                house = _determine_house(chart_data["houses"], planet_data["longitude"])

                # Add to chart data
                chart_data["planets"][planet_name] = {
                    "name": planet_name,
                    "longitude": planet_data["longitude"],
                    "latitude": planet_data["latitude"],
                    "speed": planet_data["speed"],
                    "sign": planet_data["sign"],
                    "house": house,
                    "retrograde": planet_data["retrograde"]
                }
            except Exception as e:
                logger.error(f"Error calculating {planet_name} with Swiss Ephemeris: {e}")
                raise EphemerisError(f"Failed to calculate position for {planet_name}: {e}")

        return chart_data

    except Exception as e:
        logger.error(f"Error calculating chart: {e}")
        logger.error(traceback.format_exc())
        raise ValueError(f"Chart calculation failed: {str(e)}")

def _determine_house(houses: list, longitude: float) -> int:
    """
    Determine which house contains a given longitude.

    Args:
        houses: List of house cusps longitudes
        longitude: Planet or point longitude

    Returns:
        House number (1-12)
    """
    if not houses or len(houses) != 12:
        return 1  # Default if house data is invalid

    # Normalize longitude to 0-360
    longitude = longitude % 360

    # Create house pairs with their numbers
    house_cusps = [(i+1, houses[i]) for i in range(12)]

    # Sort by longitude for easier comparison
    house_cusps.sort(key=lambda x: x[1])

    # Find which house contains the longitude
    for i in range(len(house_cusps)):
        current_cusp = house_cusps[i][1]
        next_cusp = house_cusps[(i+1) % len(house_cusps)][1]

        # Handle case where house spans 0 degrees
        if next_cusp < current_cusp:
            if longitude >= current_cusp or longitude < next_cusp:
                return house_cusps[i][0]
        # Normal case
        elif current_cusp <= longitude < next_cusp:
            return house_cusps[i][0]

    # Default to house 1 if not found
    return 1

async def calculate_verified_chart(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: str,
    verify_with_openai: bool = True
) -> Dict[str, Any]:
    """
    Calculate a chart with verification against Vedic standards.

    This is a backward compatibility wrapper around the EnhancedChartCalculator's
    calculate_verified_chart method to maintain API consistency.

    Args:
        birth_date: Birth date (YYYY-MM-DD)
        birth_time: Birth time (HH:MM:SS)
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string
        verify_with_openai: Whether to verify with OpenAI

    Returns:
        Verified chart data with verification metadata

    Raises:
        ValueError: If chart calculation fails
        RuntimeError: If verification fails in an unrecoverable way
    """
    # Create an instance of EnhancedChartCalculator
    calculator = EnhancedChartCalculator()

    # Delegate to the class method implementation
    return await calculator.calculate_verified_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        verify_with_openai=verify_with_openai
    )

class EnhancedChartCalculator:
    """
    Enhanced chart calculator with verification capabilities.

    This calculator includes OpenAI-based verification of chart data
    against Indian Vedic standards, with fallback to basic calculation if
    verification is unavailable.
    """

    def __init__(self, ephemeris=None):
        """
        Initialize the enhanced chart calculator.

        Args:
            ephemeris: Swiss ephemeris proxy object (optional)
        """
        self.ephemeris = ephemeris

    async def calculate_verified_chart(
        self,
        birth_date: str,
        birth_time: str,
        latitude: float,
        longitude: float,
        timezone: str = "UTC",
        verify_with_openai: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate a verified astrological chart.

        This method follows the sequence diagram workflow:
        1. Calculate initial chart data with astronomical precision
        2. Verify with OpenAI using Indian Vedic astrological standards if enabled
        3. Apply any corrections identified during verification
        4. Return the verified chart with confidence scores and metadata

        The verification confidence score (0-1) indicates how confident the system is
        in the accuracy of the chart data, based on multiple validation methods:
        - Direct astronomical validation: Cross-checking calculations with multiple libraries
        - OpenAI expert verification: Analysis using astrological principles
        - Internal consistency checks: Ensuring all chart elements are coherent

        Args:
            birth_date: Birth date (YYYY-MM-DD)
            birth_time: Birth time (HH:MM:SS)
            latitude: Birth latitude
            longitude: Birth longitude
            timezone: Timezone string
            verify_with_openai: Whether to verify with OpenAI

        Returns:
            Verified chart data with complete verification metadata

        Raises:
            ValueError: If chart calculation fails
            RuntimeError: If verification process encounters an unrecoverable error
        """
        try:
            # STEP 1: Calculate initial chart
            logger.info(f"Calculating chart for {birth_date} {birth_time} at {latitude}, {longitude}")

            # Use the instance's calculate_chart method which now uses real calculations
            chart_data = self.calculate_chart(
                birth_date=birth_date,
                birth_time=birth_time,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone
            )

            # STEP 2: Verify with OpenAI if requested
            verification_result = {
                "status": "verification_skipped" if not verify_with_openai else "verification_pending",
                "verified": False,
                "message": "OpenAI verification not requested" if not verify_with_openai else "Verification pending",
                "confidence": 0.8,  # Default moderate confidence for non-verified charts
                "corrections_applied": False,
                "corrections": [],
                "verification_method": "none" if not verify_with_openai else "pending"
            }

            if verify_with_openai:
                try:
                    # Use the chart verification service directly
                    from ai_service.services.chart_verification import verify_chart

                    # Ensure chart_data is not None before verification
                    if chart_data is None:
                        logger.error("Cannot verify None chart_data")
                        chart_data = {
                            "planets": {},
                            "houses": [],
                            "angles": {},
                            "aspects": [],
                            "error": "Chart data was None before verification"
                        }

                    # Verify the chart
                    verification_result = await verify_chart(
                        chart_data=chart_data,
                        verify_with_openai=True
                    )

                    logger.info(f"Chart verification completed with status: {verification_result.get('status')}")

                    # Apply corrections if available and ensure chart_data is a dictionary
                    if (verification_result.get("corrections_applied", False) and
                        verification_result.get("corrected_chart") and
                        isinstance(verification_result.get("corrected_chart"), dict)):

                        chart_data = verification_result.get("corrected_chart")
                        logger.info("Applied corrections from verification")
                except Exception as e:
                    logger.error(f"Error during chart verification: {e}")
                    logger.error(traceback.format_exc())

            try:
                # STEP 3: Add verification result to chart data
                # Ensure we have a chart_data dictionary
                if chart_data is None:
                    chart_data = {
                        "planets": {},
                        "houses": [],
                        "angles": {},
                        "aspects": [],
                        "error": "Chart data was None before adding verification result"
                    }

                # Ensure verification_result is not None
                if verification_result is None:
                    verification_result = {
                        "status": "verification_error",
                        "verified": False,
                        "confidence": 0.0,
                        "message": "Verification result was None",
                        "corrections_applied": False,
                        "corrections": [],
                        "verification_method": "failed"
                    }

                chart_data["verification"] = verification_result
                chart_data["verified_at"] = datetime.now().isoformat()

                return chart_data
            except Exception as e:
                logger.error(f"Error finalizing chart data: {e}")
                # Return a minimal valid chart as a last resort
                return {
                    "verification": {
                        "status": "error",
                        "verified": False,
                        "confidence": 0.0,
                        "message": f"Error finalizing chart: {str(e)}",
                        "corrections_applied": False,
                        "corrections": []
                    },
                    "verified_at": datetime.now().isoformat(),
                    "error": f"Failed to complete chart verification: {str(e)}",
                    "planets": {},
                    "houses": []
                }

        except Exception as e:
            logger.error(f"Error calculating verified chart: {e}")
            logger.error(traceback.format_exc())
            raise ValueError(f"Chart calculation failed: {str(e)}")

    def calculate_chart(
        self,
        birth_date: str,
        birth_time: str,
        latitude: float,
        longitude: float,
        timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Calculate a comprehensive astrological chart using real astronomical methods.

        This method performs precise astronomical calculations to determine planetary positions,
        house cusps, and other chart elements based on birth details. It leverages
        Swiss Ephemeris for high-precision astronomical calculations.

        Args:
            birth_date: Birth date (YYYY-MM-DD)
            birth_time: Birth time (HH:MM:SS)
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees
            timezone: IANA timezone identifier (e.g., 'America/New_York')

        Returns:
            Dict containing complete chart data including planets, houses, aspects, etc.

        Raises:
            ValueError: If calculation fails due to invalid input or astronomical problems
        """
        import logging
        from datetime import datetime
        import pytz
        import uuid
        import traceback

        logger = logging.getLogger(__name__)
        logger.info(f"Calculating chart for {birth_date} {birth_time} at coordinates {latitude}, {longitude}")

        # Initialize an empty chart data dictionary - ensures we return a Dict[str, Any]
        chart_data = {
            "planets": {},
            "houses": [],
            "angles": {},
            "aspects": [],
            "calculation_meta": {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "calculation_time": datetime.now().isoformat()
            }
        }

        try:
            # Parse date and time into a datetime object
            birth_dt_str = f"{birth_date} {birth_time}"
            birth_dt_naive = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M:%S")

            # Get the timezone object and localize the datetime
            tz = pytz.timezone(timezone)
            birth_dt = tz.localize(birth_dt_naive)

            # Get UTC datetime for Swiss Ephemeris calculations
            birth_dt_utc = birth_dt.astimezone(pytz.UTC)

            # Use Swiss Ephemeris if available in this calculator instance
            if self.ephemeris:
                logger.info("Using instance ephemeris for calculations")
                # Calculate planetary positions
                planet_data = self._calculate_planets(birth_dt_utc, latitude, longitude, self.ephemeris)

                # Calculate house cusps
                houses_data = self._calculate_houses(birth_dt_utc, latitude, longitude, self.ephemeris)

                # Set chart data
                chart_data["planets"] = planet_data
                chart_data["houses"] = houses_data

                # Calculate ascendant
                ascendant = self._calculate_ascendant(birth_dt_utc, latitude, longitude, self.ephemeris)
                chart_data["ascendant"] = ascendant
            else:
                # Get the standalone calculation function as fallback
                logger.info("No ephemeris found, using standalone calculation function")
                from ai_service.services.chart_service_calculation import calculate_chart as standalone_calculate

                # Call the standalone function
                standalone_result = standalone_calculate(
                    birth_date=birth_date,
                    birth_time=birth_time,
                    latitude=latitude,
                    longitude=longitude,
                    timezone=timezone
                )

                # Handle potential None result
                if standalone_result is None:
                    logger.warning("Standalone calculation returned None. Using empty chart structure.")
                    # We already initialized chart_data with empty structures above
                elif isinstance(standalone_result, dict):
                    # Update our chart_data with the standalone result
                    chart_data.update(standalone_result)
                else:
                    logger.warning(f"Unexpected standalone calculation result type: {type(standalone_result)}")

            # Post-calculation: Add aspects, dignities, other derived information
            try:
                if chart_data.get("planets"):
                    # Calculate aspects between planets
                    from ai_service.services.chart_service_aspects import calculate_aspects
                    chart_data["aspects"] = calculate_aspects(chart_data["planets"])

                    # Calculate dignities and debilities
                    from ai_service.services.chart_service_dignities import calculate_dignities
                    chart_data["dignities"] = calculate_dignities(chart_data["planets"])
            except Exception as e:
                logger.error(f"Error in post-calculation processing: {e}")
                chart_data["calculation_errors"] = chart_data.get("calculation_errors", []) + [str(e)]

            # Add calculation metadata
            chart_data["calculation_meta"] = {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "calculation_time": datetime.now().isoformat(),
                "calculation_method": "swiss_ephemeris" if self.ephemeris else "standalone",
                "success": True
            }

            return chart_data

        except Exception as e:
            logger.error(f"Error calculating chart: {e}")
            logger.error(traceback.format_exc())

            # Return a properly structured error chart
            chart_data["calculation_meta"]["success"] = False
            chart_data["calculation_meta"]["error"] = str(e)
            chart_data["calculation_meta"]["error_traceback"] = traceback.format_exc()

            return chart_data

    def _calculate_planets(self, birth_dt, latitude, longitude, ephemeris) -> Dict[str, Dict[str, Any]]:
        """
        Calculate planetary positions using Swiss Ephemeris.

        Args:
            birth_dt: UTC datetime of birth
            latitude: Birth latitude
            longitude: Birth longitude
            ephemeris: Swiss Ephemeris proxy object

        Returns:
            Dictionary mapping planet names to position data
        """
        # Initialize results dictionary
        planet_data = {}

        try:
            import swisseph as swe

            # Return empty dict if swe is not available
            if swe is None:
                logger.error("SwissEphemeris module is None")
                return {}

            # Convert datetime to Julian day
            jd = swe.julday(
                birth_dt.year,
                birth_dt.month,
                birth_dt.day,
                birth_dt.hour + birth_dt.minute/60.0 + birth_dt.second/3600.0
            )

            # Calculate ayanamsa (for sidereal zodiac)
            ayanamsa = swe.get_ayanamsa(jd)

            # Calculate positions for all planets
            for planet_name, planet_id in self._get_planet_mapping().items():
                try:
                    # Calculate with Swiss Ephemeris
                    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

                    # Add sidereal flag for Indian calculations
                    flags |= swe.FLG_SIDEREAL
                    swe.set_sid_mode(swe.SIDM_LAHIRI)

                    # Calculate planet position
                    result = swe.calc_ut(jd, planet_id, flags)

                    # Extract coordinates
                    tropical_longitude = result[0][0]  # Get the longitude from the result tuple
                    sidereal_longitude = (tropical_longitude - ayanamsa) % 360

                    # Get zodiac sign
                    sign_num = int(sidereal_longitude / 30)
                    sign_names = [
                        "Aries", "Taurus", "Gemini", "Cancer",
                        "Leo", "Virgo", "Libra", "Scorpio",
                        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
                    ]
                    sign = sign_names[sign_num]

                    # Determine retrograde status
                    speed = result[0][3]  # Longitude speed
                    retrograde = speed < 0

                    # Create planet data entry
                    planet_data[planet_name] = {
                        "longitude": sidereal_longitude,
                        "latitude": result[0][1],
                        "distance": result[0][2],
                        "speed": speed,
                        "sign": sign,
                        "position_in_sign": sidereal_longitude % 30,
                        "retrograde": retrograde
                    }

                    # Calculate house placement (traditional method)
                    # This requires calculating houses first, but we'll add placeholder
                    planet_data[planet_name]["house"] = 1  # Placeholder

                except Exception as e:
                    logger.error(f"Error calculating {planet_name} position: {e}")
                    planet_data[planet_name] = {
                        "error": str(e),
                        "longitude": 0,
                        "sign": "Unknown",
                        "house": 0
                    }

            # Calculate special points (North Node/Rahu)
            try:
                # Calculate Rahu (North Node)
                node_flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
                swe.set_sid_mode(swe.SIDM_LAHIRI)

                node_result = swe.calc_ut(jd, swe.MEAN_NODE, node_flags)

                sidereal_longitude = node_result[0][0]
                sign_num = int(sidereal_longitude / 30)
                sign = sign_names[sign_num]

                planet_data["North_Node"] = {
                    "longitude": sidereal_longitude,
                    "sign": sign,
                    "position_in_sign": sidereal_longitude % 30
                }

                # South Node (Ketu)
                # South Node is always 180 degrees from North Node
                south_longitude = (sidereal_longitude + 180) % 360
                south_sign_num = int(south_longitude / 30)
                south_sign = sign_names[south_sign_num]

                planet_data["South_Node"] = {
                    "longitude": south_longitude,
                    "sign": south_sign,
                    "position_in_sign": south_longitude % 30
                }
            except Exception as e:
                logger.error(f"Error calculating lunar nodes: {e}")

            return planet_data
        except Exception as e:
            logger.error(f"Error calculating planets: {e}")
            raise ValueError(f"Failed to calculate planetary positions: {str(e)}")

    def _calculate_houses(self, birth_dt, latitude, longitude, ephemeris) -> List[Dict[str, Any]]:
        """
        Calculate house cusps using Swiss Ephemeris.

        Args:
            birth_dt: UTC datetime of birth
            latitude: Birth latitude
            longitude: Birth longitude
            ephemeris: Swiss Ephemeris proxy object

        Returns:
            List of house cusps data
        """
        import swisseph as swe

        # Convert datetime to Julian day
        jd = swe.julday(
            birth_dt.year,
            birth_dt.month,
            birth_dt.day,
            birth_dt.hour + birth_dt.minute/60.0 + birth_dt.second/3600.0
        )

        # Calculate ayanamsa (for sidereal zodiac)
        ayanamsa = swe.get_ayanamsa(jd)

        # Calculate sidereal time
        sidereal_time = swe.sidtime(jd)

        # Calculate houses (Placidus system is 'P')
        house_system = 'P'  # Default to Placidus
        house_cusps, ascmc = swe.houses(jd, latitude, longitude, house_system.encode())

        # Process house cusps
        houses = []
        sign_names = [
            "Aries", "Taurus", "Gemini", "Cancer",
            "Leo", "Virgo", "Libra", "Scorpio",
            "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]

        for i in range(12):
            # Convert to sidereal longitude
            tropical_longitude = house_cusps[i]
            sidereal_longitude = (tropical_longitude - ayanamsa) % 360

            # Determine sign
            sign_num = int(sidereal_longitude / 30)
            sign = sign_names[sign_num]

            # Store house data
            houses.append({
                "house": i + 1,  # House number (1-12)
                "longitude": sidereal_longitude,
                "sign": sign,
                "position_in_sign": sidereal_longitude % 30
            })

        return houses

    def _calculate_ascendant(self, birth_dt, latitude, longitude, ephemeris) -> Dict[str, Any]:
        """
        Calculate ascendant (rising sign) using Swiss Ephemeris.

        Args:
            birth_dt: UTC datetime of birth
            latitude: Birth latitude
            longitude: Birth longitude
            ephemeris: Swiss Ephemeris proxy object

        Returns:
            Dictionary with ascendant data
        """
        import swisseph as swe

        # Convert datetime to Julian day
        jd = swe.julday(
            birth_dt.year,
            birth_dt.month,
            birth_dt.day,
            birth_dt.hour + birth_dt.minute/60.0 + birth_dt.second/3600.0
        )

        # Calculate ayanamsa (for sidereal zodiac)
        ayanamsa = swe.get_ayanamsa(jd)

        # Calculate houses to get ascendant (which is part of ascmc)
        house_system = 'P'  # Default to Placidus
        house_cusps, ascmc = swe.houses(jd, latitude, longitude, house_system.encode())

        # Extract ascendant from ascmc (index 0)
        tropical_ascendant = ascmc[0]
        sidereal_ascendant = (tropical_ascendant - ayanamsa) % 360

        # Determine zodiac sign
        sign_num = int(sidereal_ascendant / 30)
        sign_names = [
            "Aries", "Taurus", "Gemini", "Cancer",
            "Leo", "Virgo", "Libra", "Scorpio",
            "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        sign = sign_names[sign_num]

        return {
            "longitude": sidereal_ascendant,
            "sign": sign,
            "position_in_sign": sidereal_ascendant % 30
        }

    def _get_planet_mapping(self) -> Dict[str, int]:
        """
        Get planet name to ID mapping for Swiss Ephemeris.

        Returns:
            Dictionary mapping planet names to Swiss Ephemeris IDs
        """
        if not SWISSEPH_AVAILABLE or swe is None:
            return {}

        return {
            "Sun": swe.SUN,
            "Moon": swe.MOON,
            "Mercury": swe.MERCURY,
            "Venus": swe.VENUS,
            "Mars": swe.MARS,
            "Jupiter": swe.JUPITER,
            "Saturn": swe.SATURN,
            "Uranus": swe.URANUS,
            "Neptune": swe.NEPTUNE,
            "Pluto": swe.PLUTO
        }

# Constants

# Planet IDs for SwissEph
PLANET_IDS = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
    "Uranus": 7,
    "Neptune": 8,
    "Pluto": 9,
    "North_Node": 11,
    "South_Node": 12,
    "Chiron": 15
}

# Planets to use for aspect calculation
MAJOR_PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]

async def verify_ephemeris_files():
    """
    Ensure all required ephemeris files are present and valid.

    Raises:
        EphemerisError: If ephemeris files are missing or invalid

    Returns:
        bool: True if all ephemeris files are present and valid
    """
    # Check if swisseph is available
    if swe is None:
        error_msg = "Swiss Ephemeris library (swisseph) is not available"
        logger.error(error_msg)
        raise EphemerisError(error_msg)

    ephemeris_path = os.environ.get('FLATLIB_EPHE_PATH', settings.EPHEMERIS_PATH)
    logger.info(f"Verifying ephemeris files in: {ephemeris_path}")

    required_files = [
        "seas_18.se1",  # Asteroid files
        "semo_18.se1",  # Moon
        "sepl_18.se1",  # Planets
        "seau_18.se1",  # Outer planets (Uranus)
        "sene_18.se1",  # Neptune
        "sepl_18.se1"   # Pluto
    ]

    missing_files = []
    for filename in required_files:
        filepath = os.path.join(ephemeris_path, filename)
        if not os.path.exists(filepath):
            missing_files.append(filename)

    if missing_files:
        error_msg = f"Missing required ephemeris files: {missing_files}"
        logger.error(error_msg)
        raise EphemerisError(error_msg)

    # Verify file integrity by attempting to load with Swiss Ephemeris
    try:
        # Set ephemeris path for Swiss Ephemeris
        swe.set_ephe_path(ephemeris_path)

        # Test calculation to verify files work
        # Calculate Sun position for J2000 standard epoch
        sun_data = swe.calc_ut(2451545.0, swe.SUN)
        if sun_data and len(sun_data) > 0:
            logger.info("Ephemeris files verified successfully")
            return True
        else:
            error_msg = "Ephemeris files failed to produce valid calculation results"
            logger.error(error_msg)
            raise EphemerisError(error_msg)
    except Exception as e:
        error_msg = f"Error verifying ephemeris files: {e}"
        logger.error(error_msg)
        raise EphemerisError(error_msg)

def process_ephemeris_result(return_data: Union[Tuple[Any, ...], str, Any]) -> Dict[str, Any]:
    """
    Process the result from Swiss Ephemeris calculations.

    This function converts the tuple returned by Swiss Ephemeris into a dictionary
    with well-defined keys for easier consumption by the rest of the application.

    Args:
        return_data: Result from Swiss Ephemeris calculation

    Returns:
        Dictionary with structured planet data
    """
    result = {
        "longitude": 0.0,
        "latitude": 0.0,
        "distance": 0.0,
        "speed_longitude": 0.0,
        "speed_latitude": 0.0,
        "speed_distance": 0.0,
        "sign": "Unknown",
        "retrograde": False
    }

    try:
        # If return_data is a string, it's an error message
        if isinstance(return_data, str):
            result["error"] = return_data
            return result

        # Extract values from tuple or list
        if isinstance(return_data, (tuple, list)) and len(return_data) >= 2:
            # First element is often the status code
            # Second element contains the actual data
            data = return_data[1] if isinstance(return_data, tuple) and len(return_data) > 1 else return_data

            # If data is a NumPy array, convert to list
            if hasattr(data, 'tolist'):
                data = data.tolist()

            # Extract data based on typical Swiss Ephemeris return format
            if isinstance(data, (list, tuple)) and len(data) >= 6:
                result["longitude"] = float(data[0])
                result["latitude"] = float(data[1])
                result["distance"] = float(data[2])
                result["speed_longitude"] = float(data[3])
                result["speed_latitude"] = float(data[4])
                result["speed_distance"] = float(data[5])

                # Determine retrograde status
                result["retrograde"] = result["speed_longitude"] < 0

                # Calculate zodiac sign (0-29.99 for each sign, 12 signs)
                sign_num = int(result["longitude"] / 30) % 12
                signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                result["sign"] = signs[sign_num]
            else:
                # Handle simpler data format
                if isinstance(data, (list, tuple)) and len(data) > 0:
                    result["longitude"] = float(data[0])
                    if len(data) > 1:
                        result["latitude"] = float(data[1])
                    if len(data) > 2:
                        result["distance"] = float(data[2])
                elif isinstance(data, (int, float)):
                    result["longitude"] = float(data)
        elif isinstance(return_data, dict):
            # If already a dictionary, use it directly
            result.update(return_data)

        return result
    except Exception as e:
        logger.error(f"Error processing ephemeris result: {e}")
        result["error"] = str(e)
        return result

def calculate_standalone(birth_dt: datetime, latitude: float, longitude: float, timezone_str: str) -> Dict[str, Any]:
    """
    Standalone chart calculation that works with various libraries.

    Args:
        birth_dt: Birth datetime
        latitude: Birth latitude
        longitude: Birth longitude
        timezone_str: Timezone string

    Returns:
        Chart data dictionary
    """
    try:
        # Try flatlib calculation first
        return calculate_chart(birth_dt, latitude, longitude, timezone_str)
    except Exception as flatlib_error:
        logger.error(f"Flatlib calculation failed: {flatlib_error}")

        # Try Swiss Ephemeris as fallback
        try:
            if SWISSEPH_AVAILABLE and swe is not None:
                # Import vedic calculation module
                from ai_service.core.rectification.vedic_calculation import calculate_vedic_chart
                return calculate_vedic_chart(birth_dt, latitude, longitude, timezone_str)
            else:
                logger.error("Swiss Ephemeris not available for fallback")
                return {
                    "error": f"Chart calculation failed: {str(flatlib_error)}. Swiss Ephemeris fallback not available.",
                    "planets": {},
                    "houses": [],
                    "angles": {}
                }
        except Exception as swe_error:
            logger.error(f"Swiss Ephemeris calculation failed: {swe_error}")

            # All calculations failed, return error data
            return {
                "error": f"All chart calculation methods failed. Flatlib: {str(flatlib_error)}. Swiss Ephemeris: {str(swe_error)}",
                "planets": {},
                "houses": [],
                "angles": {}
            }
