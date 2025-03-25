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
from typing import Dict, List, Any, Tuple, Optional, Union, Callable
from datetime import datetime, timedelta
import numpy as np

# Flag to indicate if pyswisseph is available
try:
    import pyswisseph as swe
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

# Planet IDs for Swiss Ephemeris
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
    "Pluto": 9
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

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees

    Returns:
        IANA timezone string (e.g., 'America/New_York')

    Raises:
        ValueError: If timezone cannot be determined
    """
    try:
        # Use TimezoneFinder to get the timezone from coordinates
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=latitude, lng=longitude)

        if not timezone_str:
            # If timezone not found at exact point, try a small search radius
            timezone_str = tf.closest_timezone_at(lat=latitude, lng=longitude, delta_degree=1)

        if not timezone_str:
            raise ValueError(f"Could not determine timezone for coordinates: {latitude}, {longitude}")

        return timezone_str
    except Exception as e:
        logger.error(f"Error determining timezone: {e}")
        raise ValueError(f"Failed to determine timezone: {str(e)}")

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

        # Unpack the return value: (positions_tuple, flags)
        result = return_data[0]  # Get the positions tuple
        status = return_data[1]  # Get the flags

        # Extract coordinates from result tuple
        longitude = result[0]  # Longitude in degrees
        latitude = result[1]   # Latitude in degrees
        distance = result[2]   # Distance in AU
        speed_lon = result[3]  # Speed in longitude (deg/day)

        # Determine if planet is retrograde
        retrograde = speed_lon < 0

        # Calculate sign
        sign_num = int(longitude / 30) % 12
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        sign = signs[sign_num]

        return {
            "longitude": longitude,
            "latitude": latitude,
            "distance": distance,
            "speed": speed_lon,
            "sign": sign,
            "retrograde": retrograde
        }
    except Exception as e:
        logger.error(f"Error calculating planet position with Swiss Ephemeris: {e}")
        raise ValueError(f"Failed to calculate planet position: {str(e)}")

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
            if not SWISSEPH_AVAILABLE:
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

        # Planet mapping between flatlib constants and Swiss Ephemeris
        planet_mappings = {
            const.SUN: (swe.SUN, "sun"),
            const.MOON: (swe.MOON, "moon"),
            const.MERCURY: (swe.MERCURY, "mercury"),
            const.VENUS: (swe.VENUS, "venus"),
            const.MARS: (swe.MARS, "mars"),
            const.JUPITER: (swe.JUPITER, "jupiter"),
            const.SATURN: (swe.SATURN, "saturn"),
        }

        # Add outer planets
        outer_planets = {
            "uranus": swe.URANUS,
            "neptune": swe.NEPTUNE,
            "pluto": swe.PLUTO,
            "chiron": swe.CHIRON,
            "north_node": swe.MEAN_NODE  # Using Mean Node
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
    location: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "tropical",
    ayanamsa: str = "lahiri",
    node_type: str = "true",
    verify_with_openai: bool = False
) -> Dict[str, Any]:
    """
    Calculate chart with verification and validation steps.

    This function calculates an astrological chart and applies verification
    using OpenAI if requested, with robust error handling.

    Args:
        birth_date: Birth date in YYYY-MM-DD format
        birth_time: Birth time in HH:MM:SS format
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string (e.g., 'America/New_York')
        location: Optional location name
        house_system: House system (P=Placidus, K=Koch, etc.)
        zodiac_type: Zodiac type (tropical or sidereal)
        ayanamsa: Ayanamsa for sidereal calculations
        node_type: Node type (true or mean)
        verify_with_openai: Whether to verify with OpenAI

    Returns:
        Calculated and verified chart data
    """
    try:
        # Convert string to datetime if needed
        birth_dt = datetime.strptime(birth_date, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # Calculate the chart
        try:
            birth_dt = datetime.fromisoformat(birth_date.replace('Z', '+00:00'))
        except ValueError:
            # Last attempt - try different format
            try:
                birth_dt = datetime.strptime(birth_date, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                raise ValueError(f"Invalid birth date format: {birth_date}")

    # Calculate the chart
    chart_data = calculate_chart(
        birth_dt=birth_dt,
        latitude=latitude,
        longitude=longitude,
        timezone_str=timezone,
        house_system=house_system
    )

    # Add input parameters
    chart_data["input_params"] = {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "location": location,
        "house_system": house_system,
        "zodiac_type": zodiac_type,
        "ayanamsa": ayanamsa,
        "node_type": node_type
    }

    # Apply Vedic standards verification (if sidereal)
    if zodiac_type.lower() == "sidereal":
        chart_data = await _verify_vedic_standards(chart_data, birth_dt)

    # Verify with OpenAI if requested
    if verify_with_openai:
        try:
            verified_chart = await _verify_chart_with_openai(chart_data)

            # If verification failed, log it but continue with unverified chart
            if verified_chart.get("verification", {}).get("verification_status") != "success":
                logger.warning(f"OpenAI verification failed: {verified_chart.get('verification', {}).get('error')}")
                chart_data["verification"] = verified_chart.get("verification", {})
            else:
                # Use the verified chart
                chart_data = verified_chart
        except Exception as e:
            # Log error but continue with unverified chart
            logger.error(f"Error during OpenAI verification: {e}")
            chart_data["verification"] = {
                "verified_with_openai": False,
                "verification_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    # Ensure chart_id is present
    if "chart_id" not in chart_data:
        chart_data["chart_id"] = f"chart_{uuid.uuid4().hex[:8]}"

    return chart_data

async def _verify_vedic_standards(chart_data: Dict[str, Any], birth_dt: datetime) -> Dict[str, Any]:
    """
    Verify chart calculations against Vedic astrological standards.

    This checks for:
    1. Proper nakshatra placements
    2. Correct rashi (sign) calculations
    3. Accurate ayanamsa application
    4. Proper dignities and debilities
    5. Correct varga (divisional chart) calculations

    Args:
        chart_data: Chart data to verify
        birth_dt: Birth datetime

    Returns:
        Verified chart data with any necessary corrections
    """
    try:
        # Import Vedic-specific modules
        from ai_service.core.rectification.vedic_calculation import (
            get_nakshatra_from_longitude,
            calculate_varga_charts,
            calculate_planet_dignity,
            calculate_shadbala,
            get_ayanamsha_value,
            verify_vedic_coordinates,
            calculate_planetary_avasthas,
            calculate_dasa_periods
        )

        # Add ayanamsha information with proper calculation
        ayanamsha_value = get_ayanamsha_value(birth_dt)
        chart_data["ayanamsha"] = {
            "value": ayanamsha_value,
            "type": "Lahiri",  # Default standard for Vedic astrology
            "verified": True
        }

        # First, verify that all coordinates are properly adjusted for ayanamsha
        verified_coords = verify_vedic_coordinates(chart_data, ayanamsha_value)
        if verified_coords.get("corrections", []):
            logger.info(f"Applied {len(verified_coords['corrections'])} ayanamsha corrections")
            # Apply the corrections to the chart data
            for correction in verified_coords.get("corrections", []):
                item_type = correction.get("type")
                item_name = correction.get("name")
                corrected_longitude = correction.get("corrected_longitude")

                if item_type == "planet" and item_name in chart_data.get("planets", {}):
                    chart_data["planets"][item_name]["longitude"] = corrected_longitude
                    chart_data["planets"][item_name]["corrected"] = True
                elif item_type == "house" and item_name.isdigit():
                    house_index = int(item_name) - 1
                    if 0 <= house_index < len(chart_data.get("houses", [])):
                        chart_data["houses"][house_index]["longitude"] = corrected_longitude
                        chart_data["houses"][house_index]["corrected"] = True
                elif item_type == "angle" and item_name in chart_data.get("angles", {}):
                    chart_data["angles"][item_name]["longitude"] = corrected_longitude
                    chart_data["angles"][item_name]["corrected"] = True

        # Verify and add nakshatra positions
        chart_data["nakshatras"] = {}
        for planet_name, planet_data in chart_data.get("planets", {}).items():
            longitude = planet_data.get("longitude", 0)

            # Calculate nakshatra
            nakshatra_info = get_nakshatra_from_longitude(longitude)

            # Store nakshatra information
            chart_data["nakshatras"][planet_name] = nakshatra_info

            # Add to planet data
            planet_data["nakshatra"] = nakshatra_info.get("name")
            planet_data["nakshatra_pada"] = nakshatra_info.get("pada")
            planet_data["nakshatra_longitude"] = nakshatra_info.get("longitude")
            planet_data["nakshatra_lord"] = nakshatra_info.get("lord")

        # Calculate and verify varga (divisional) charts - MANDATORY for Vedic astrology
        varga_charts = calculate_varga_charts(chart_data)
        chart_data["varga_charts"] = varga_charts

        # Verify all required divisional charts are present
        required_vargas = ["D1", "D9", "D3", "D7", "D10", "D12", "D2", "D4", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"]
        missing_vargas = [v for v in required_vargas if v not in varga_charts]

        if missing_vargas:
            missing_vargas_str = ', '.join(missing_vargas)
            logger.error(f"Missing critical divisional charts: {missing_vargas_str}")
            raise ValueError(f"Vedic verification failed: Missing required divisional charts: {missing_vargas_str}")

        # Calculate dasa periods (Vimshottari dasa)
        chart_data["dasa_periods"] = calculate_dasa_periods(
            birth_dt=birth_dt,
            moon_longitude=chart_data.get("planets", {}).get("moon", {}).get("longitude", 0),
            ayanamsha=ayanamsha_value
        )

        # Calculate planetary avasthas (states) for all planets
        chart_data["avasthas"] = calculate_planetary_avasthas(chart_data)

        # Calculate dignity and shadbala - mandatory for all planets
        chart_data["dignities"] = {}
        chart_data["shadbala"] = {}

        essential_planets = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
        missing_dignity_calcs = []

        for planet_name in essential_planets:
            if planet_name not in chart_data.get("planets", {}):
                missing_dignity_calcs.append(planet_name)
                continue

            planet_data = chart_data["planets"][planet_name]

            # Calculate dignity
            sign = planet_data.get("sign", "")
            degree = planet_data.get("longitude", 0) % 30

            dignity = calculate_planet_dignity(planet_name, sign, degree)
            chart_data["dignities"][planet_name] = dignity

            # Calculate shadbala (sixfold strength)
            shadbala = calculate_shadbala(planet_name, chart_data)
            chart_data["shadbala"][planet_name] = shadbala

        if missing_dignity_calcs:
            missing_planets_str = ', '.join(missing_dignity_calcs)
            logger.error(f"Missing essential planets for dignity/shadbala calculation: {missing_planets_str}")
            raise ValueError(f"Vedic verification failed: Cannot calculate dignities for essential planets: {missing_planets_str}")

        # Verify overall chart integrity
        chart_data["verification_details"] = {
            "verified_against": "vedic_standards",
            "verified_at": datetime.now().isoformat(),
            "verification_status": "verified",
            "ayanamsha": ayanamsha_value,
            "ayanamsha_type": "Lahiri"
        }

        return chart_data

    except ImportError as ie:
        logger.error(f"Error importing Vedic calculation modules: {ie}")
        # Don't fall back to simplified implementation - raise the error for proper handling
        raise ValueError(f"Vedic calculation modules not available: {str(ie)}")
    except Exception as e:
        logger.error(f"Error during Vedic verification: {e}")
        logger.error(traceback.format_exc())
        # Don't return unverified chart - raise the error for proper handling
        raise ValueError(f"Vedic verification failed: {str(e)}")

async def _verify_chart_with_openai(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify chart data using OpenAI for accuracy checks.

    Args:
        chart_data: Chart data to verify

    Returns:
        Verified chart data with potential corrections
    """
    try:
        # Import OpenAI service only when needed
        from ai_service.api.services.openai import get_openai_service

        # Get OpenAI service
        openai_service = get_openai_service()  # Not async in this implementation
        if not openai_service:
            logger.warning("OpenAI service not available, skipping chart verification")
            return chart_data

        # Extract key chart elements for verification
        verification_data = {
            "ascendant": chart_data.get("ascendant", {}),
            "houses": chart_data.get("houses", []),
            "planets": {
                k: v for k, v in chart_data.get("planets", {}).items()
                if k in ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
            },
            "aspects": chart_data.get("aspects", [])[:10],  # Limit to first 10 aspects
            "chart_id": chart_data.get("chart_id", ""),
            "zodiac_type": chart_data.get("zodiac_type", "tropical"),
            "house_system": chart_data.get("house_system", "placidus")
        }

        # Create structured prompt for OpenAI
        prompt = {
            "task": "chart_verification",
            "chart_data": verification_data,
            "instructions": [
                "Verify this astrological chart data for accuracy and consistency",
                "Check that planet positions are in valid zodiac signs (0-360°)",
                "Verify house cusps are in correct order",
                "Check if ascendant degree is consistent with house system",
                "Identify any potential errors or inconsistencies",
                "Return corrections as a structured JSON object"
            ]
        }

        # Serialize prompt to JSON
        prompt_str = json.dumps(prompt)

        # Call OpenAI with retry logic
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                response = await openai_service.generate_completion(
                    prompt=prompt_str,
                    task_type="chart_verification",
                    max_tokens=1000
                )

                # Parse response
                corrections = []
                if isinstance(response, dict):
                    if "corrections" in response:
                        corrections = response.get("corrections", [])
                else:
                    # Try to parse from string
                    response_str = response if isinstance(response, str) else json.dumps(response)
                    corrections = _parse_verification_response(response_str)

                if corrections:
                    logger.info(f"Chart verification found {len(corrections)} corrections")
                    # Apply corrections
                    corrected_chart = _apply_corrections(chart_data, corrections)

                    # Add verification metadata
                    corrected_chart["verification"] = {
                        "verified_with_openai": True,
                        "verification_timestamp": datetime.now().isoformat(),
                        "corrections_applied": len(corrections),
                        "verification_status": "success"
                    }

                    return corrected_chart
                else:
                    # No corrections needed
                    chart_data["verification"] = {
                        "verified_with_openai": True,
                        "verification_timestamp": datetime.now().isoformat(),
                        "corrections_applied": 0,
                        "verification_status": "success"
                    }

                    return chart_data

            except Exception as e:
                logger.warning(f"OpenAI verification attempt {attempt+1}/{max_retries} failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff

        # If we get here, all retries failed
        logger.error(f"OpenAI chart verification failed after {max_retries} attempts")

        # Add verification metadata indicating failure
        chart_data["verification"] = {
            "verified_with_openai": False,
            "verification_timestamp": datetime.now().isoformat(),
            "verification_status": "failed",
            "error": "Verification failed after multiple attempts"
        }

        return chart_data

    except Exception as e:
        logger.error(f"Error in chart verification: {e}")

        # Add verification metadata indicating error
        chart_data["verification"] = {
            "verified_with_openai": False,
            "verification_timestamp": datetime.now().isoformat(),
            "verification_status": "error",
            "error": str(e)
        }

        return chart_data

def _parse_verification_response(response: Union[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parse the verification response from OpenAI.

    Args:
        response: Response from OpenAI, can be string or dictionary

    Returns:
        List of corrections to apply
    """
    corrections = []

    try:
        # Check if response is already a dictionary
        if isinstance(response, dict):
            if "corrections" in response:
                return response.get("corrections", [])
            return []

        # If it's a string, try to parse as JSON
        if isinstance(response, str):
            try:
                json_data = json.loads(response)
                if "corrections" in json_data:
                    return json_data.get("corrections", [])
                return []
            except json.JSONDecodeError:
                pass

            # Try to extract JSON block
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(1)
                    json_data = json.loads(json_str)
                    if "corrections" in json_data:
                        return json_data.get("corrections", [])
                except (json.JSONDecodeError, IndexError):
                    pass

            # Extract corrections with alternative regex approach
            correction_pattern = r'([a-zA-Z_]+):\s*([^,]+),\s*correct value:\s*([^,]+)'
            matches = re.findall(correction_pattern, response, re.IGNORECASE)

            for match in matches:
                field, current, correct = match
                corrections.append({
                    "field": field.strip(),
                    "current_value": current.strip(),
                    "correct_value": correct.strip()
                })

    except Exception as e:
        logger.error(f"Error parsing verification response: {e}")

    return corrections

def _apply_corrections(chart_data: Dict[str, Any], corrections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply corrections to chart data from verification.

    Args:
        chart_data: Original chart data
        corrections: List of correction objects

    Returns:
        Chart data with corrections applied
    """
    for correction in corrections:
        correction_type = correction.get("type", "")
        object_name = correction.get("object", "")
        corrected_value = correction.get("corrected", "")

        if not correction_type or not object_name or not corrected_value:
            continue

        try:
            if correction_type == "planet_position" and object_name in chart_data.get("planets", {}):
                # Parse corrected value - could be longitude or sign
                try:
                    # Check if it's a longitude value
                    corrected_longitude = float(corrected_value)
                    chart_data["planets"][object_name]["longitude"] = corrected_longitude

                    # Update sign based on longitude
                    sign_num = int(corrected_longitude / 30) % 12
                    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                    chart_data["planets"][object_name]["sign"] = signs[sign_num]
                except ValueError:
                    # Must be a sign correction
                    chart_data["planets"][object_name]["sign"] = corrected_value
            elif correction_type == "angle" and object_name in chart_data.get("angles", {}):
                try:
                    # Check if it's a longitude value
                    corrected_longitude = float(corrected_value)
                    chart_data["angles"][object_name]["longitude"] = corrected_longitude

                    # Update sign based on longitude
                    sign_num = int(corrected_longitude / 30) % 12
                    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                    chart_data["angles"][object_name]["sign"] = signs[sign_num]
                except ValueError:
                    # Must be a sign correction
                    chart_data["angles"][object_name]["sign"] = corrected_value

        except Exception as e:
            logger.warning(f"Error applying correction {correction}: {e}")

    return chart_data

class EnhancedChartCalculator:
    """Enhanced chart calculator for birth time rectification."""

    def __init__(self, swisseph_proxy: SwissEphemerisProxy):
        """
        Initialize the enhanced chart calculator.

        Args:
            swisseph_proxy: Swiss Ephemeris proxy instance

        Raises:
            RuntimeError: If Swiss Ephemeris proxy is not available
        """
        if not swisseph_proxy:
            raise RuntimeError("Swiss Ephemeris proxy is required but not provided")

        self.swisseph = swisseph_proxy

    async def calculate_planets_positions(
        self, birth_datetime: datetime, latitude: float, longitude: float
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate positions of all planets for a specific birth datetime and location.

        Args:
            birth_datetime: Birth datetime
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees

        Returns:
            Dictionary with planet positions data

        Raises:
            RuntimeError: If calculation fails
        """
        try:
            planets_data = {}

            # Define planet IDs to calculate
            planet_ids = {
                "Sun": 0,
                "Moon": 1,
                "Mercury": 2,
                "Venus": 3,
                "Mars": 4,
                "Jupiter": 5,
                "Saturn": 6,
                "Uranus": 7,
                "Neptune": 8,
                "Pluto": 9
            }

            # Calculate positions for each planet
            for planet_name, planet_id in planet_ids.items():
                try:
                    # Get position data
                    position = await self.swisseph.get_planet_position(
                        birth_datetime, planet_id, latitude, longitude
                    )

                    # Store in result
                    planets_data[planet_name] = {
                        'longitude': position['longitude'],
                        'latitude': position['latitude'],
                        'distance': position['distance'],
                        'speed': position.get('longitude_speed', 0)
                    }
                except Exception as planet_error:
                    # Log error and raise
                    error_msg = f"Failed to calculate position for planet {planet_name}: {planet_error}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from planet_error

            return planets_data
        except Exception as e:
            error_msg = f"Failed to calculate planet positions: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def calculate_houses(
        self, birth_datetime: datetime, latitude: float, longitude: float, house_system: str = "P"
    ) -> Dict[str, float]:
        """
        Calculate house cusps for a specific birth datetime and location.

        Args:
            birth_datetime: Birth datetime
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees
            house_system: House system code (e.g., "P" for Placidus)

        Returns:
            Dictionary with house cusps data

        Raises:
            RuntimeError: If calculation fails
        """
        try:
            # Get house data
            houses_data = await self.swisseph.get_houses(
                birth_datetime, latitude, longitude, house_system
            )

            # Format result
            result = {}

            # Extract cusps
            for i, cusp in enumerate(houses_data['cusps']):
                if i > 0 and i <= 12:  # Skip 0 index, use 1-12
                    result[str(i)] = cusp

            # Add special angles
            result['ASC'] = houses_data['ascendant']
            result['MC'] = houses_data['midheaven']
            result['ARMC'] = houses_data['armc']
            result['Vertex'] = houses_data['vertex']

            return result
        except Exception as e:
            error_msg = f"Failed to calculate houses: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def calculate_aspects(
        self, planets_data: Dict[str, Dict[str, Any]], orb_settings: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate aspects between planets.

        Args:
            planets_data: Dictionary with planet positions data
            orb_settings: Optional dictionary with orb settings by aspect type

        Returns:
            List of aspect dictionaries

        Raises:
            RuntimeError: If calculation fails
        """
        try:
            # Default orb settings if not provided
            if not orb_settings:
                orb_settings = {
                    'conjunction': 8.0,
                    'opposition': 8.0,
                    'trine': 7.0,
                    'square': 7.0,
                    'sextile': 6.0,
                    'quincunx': 5.0,
                    'semisextile': 5.0,
                    'semisquare': 3.0,
                    'sesquisquare': 3.0
                }

            aspects = []
            planets = list(planets_data.keys())

            # Loop through all planet pairs
            for i, planet1 in enumerate(planets):
                for planet2 in planets[i+1:]:  # Only check each pair once
                    # Get planet longitudes
                    if 'longitude' not in planets_data[planet1] or 'longitude' not in planets_data[planet2]:
                        continue

                    lon1 = planets_data[planet1]['longitude']
                    lon2 = planets_data[planet2]['longitude']

                    # Calculate aspect
                    aspect = self._calculate_single_aspect(planet1, lon1, planet2, lon2, orb_settings)

                    # Add if aspect exists
                    if aspect:
                        aspects.append(aspect)

            return aspects
        except Exception as e:
            error_msg = f"Failed to calculate aspects: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def calculate_chart(
        self,
        birth_datetime: datetime,
        latitude: float,
        longitude: float,
        house_system: str = "P"
    ) -> Dict[str, Any]:
        """
        Calculate a complete astrological chart for a specific birth datetime and location.

        Args:
            birth_datetime: Birth datetime
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees
            house_system: House system code (e.g., "P" for Placidus)

        Returns:
            Dictionary with complete chart data

        Raises:
            RuntimeError: If calculation fails
        """
        try:
            # Calculate planets
            planets_data = await self.calculate_planets_positions(birth_datetime, latitude, longitude)

            # Calculate houses
            houses_data = await self.calculate_houses(birth_datetime, latitude, longitude, house_system)

            # Assign houses to planets
            planets_with_houses = self._assign_houses_to_planets(planets_data, houses_data)

            # Calculate aspects
            aspects = await self.calculate_aspects(planets_with_houses)

            # Calculate additional angles
            angles = self._calculate_angles(planets_with_houses, houses_data)

            # Build chart data
            chart_data = {
                'planets': planets_with_houses,
                'houses': houses_data,
                'aspects': aspects,
                'angles': angles,
                'datetime': birth_datetime.isoformat(),
                'latitude': latitude,
                'longitude': longitude,
                'house_system': house_system
            }

            return chart_data
        except Exception as e:
            error_msg = f"Failed to calculate chart: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _calculate_angles(
        self, planets_data: Dict[str, Dict[str, Any]], houses_data: Dict[str, float]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate the main astrological angles (Ascendant, Midheaven, etc.)

        Args:
            planets_data: Planetary positions data
            houses_data: House cusps data

        Returns:
            Dictionary with angular data
        """
        angles = {}

        try:
            # Ascendant is the cusp of house 1
            if "1" in houses_data:
                asc_longitude = houses_data["1"]
                sign_num = int(asc_longitude / 30)
                angles["Asc"] = {
                    "longitude": asc_longitude,
                    "sign": ZODIAC_SIGNS[sign_num],
                    "sign_num": sign_num
                }

            # Midheaven is the cusp of house 10
            if "10" in houses_data:
                mc_longitude = houses_data["10"]
                sign_num = int(mc_longitude / 30)
                angles["MC"] = {
                    "longitude": mc_longitude,
                    "sign": ZODIAC_SIGNS[sign_num],
                    "sign_num": sign_num
                }

            # Descendant is opposite the Ascendant
            if "Asc" in angles:
                desc_longitude = (angles["Asc"]["longitude"] + 180) % 360
                sign_num = int(desc_longitude / 30)
                angles["Desc"] = {
                    "longitude": desc_longitude,
                    "sign": ZODIAC_SIGNS[sign_num],
                    "sign_num": sign_num
                }

            # IC is opposite the Midheaven
            if "MC" in angles:
                ic_longitude = (angles["MC"]["longitude"] + 180) % 360
                sign_num = int(ic_longitude / 30)
                angles["IC"] = {
                    "longitude": ic_longitude,
                    "sign": ZODIAC_SIGNS[sign_num],
                    "sign_num": sign_num
                }

            return angles

        except Exception as e:
            logger.warning(f"Failed to calculate some angles: {str(e)}")
            return angles

    def _assign_houses_to_planets(
        self, planets_data: Dict[str, Dict[str, Any]], houses_data: Dict[str, float]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Assign houses to planets based on their longitudes.

        Args:
            planets_data: Planetary positions data
            houses_data: House cusps data

        Returns:
            Updated planetary data with house assignments
        """
        try:
            # Convert houses_data to a sorted list of (house_num, longitude) tuples
            house_cusps = [(int(house_num), longitude) for house_num, longitude in houses_data.items()]
            house_cusps.sort(key=lambda x: x[1])

            # Add house 13 same as house 1 but + 360° for calculations that span 360°
            if house_cusps:
                house_cusps.append((house_cusps[0][0] + 12, house_cusps[0][1] + 360))

            # Assign house to each planet
            for planet_name, planet_data in planets_data.items():
                planet_longitude = planet_data["longitude"]

                # Find which house the planet is in
                for i in range(len(house_cusps) - 1):
                    current_house, current_cusp = house_cusps[i]
                    next_house, next_cusp = house_cusps[i + 1]

                    # Handle the case where planet longitude is between the last and first house cusp
                    if i == len(house_cusps) - 2 and planet_longitude < current_cusp:
                        planet_longitude += 360

                    if current_cusp <= planet_longitude < next_cusp:
                        planet_data["house"] = str(current_house)
                        break

            return planets_data

        except Exception as e:
            logger.warning(f"Failed to assign houses to planets: {str(e)}")
            return planets_data

    def _calculate_single_aspect(
        self, planet1: str, lon1: float, planet2: str, lon2: float, orb_settings: Dict[str, float]
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate a single aspect between two planets.

        Args:
            planet1: Name of first planet
            lon1: Longitude of first planet
            planet2: Name of second planet
            lon2: Longitude of second planet
            orb_settings: Orb settings for aspects

        Returns:
            Aspect data dictionary or None if no valid aspect
        """
        try:
            # Calculate the angle between planets
            angle_diff = abs(lon1 - lon2)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            # Check against each possible aspect
            for aspect_name, aspect_angle in ASPECT_ANGLES.items():
                allowed_orb = orb_settings.get(aspect_name, DEFAULT_ASPECT_ORBS.get(aspect_name, 5.0))

                # Check if the planets form this aspect
                angle_diff_from_aspect = abs(angle_diff - aspect_angle)

                if angle_diff_from_aspect <= allowed_orb:
                    # Found a valid aspect
                    return {
                        "planet1": planet1,
                        "planet2": planet2,
                        "type": aspect_name,
                        "angle": aspect_angle,
                        "orb": angle_diff_from_aspect,
                        "applying": self._is_aspect_applying(lon1, lon2, aspect_angle)
                    }

            # No valid aspect found
            return None

        except Exception as e:
            logger.warning(f"Error in aspect calculation between {planet1} and {planet2}: {str(e)}")
            return None

    def _is_aspect_applying(self, lon1: float, lon2: float, aspect_angle: float) -> bool:
        """
        Determine if an aspect is applying (planets moving toward exact aspect) or separating.

        This is a simplified version and would need actual planet speeds for accuracy.

        Args:
            lon1: Longitude of first planet
            lon2: Longitude of second planet
            aspect_angle: The aspect angle to check

        Returns:
            True if the aspect is applying, False if separating
        """
        # This is a simplification - would need planet velocities for accurate calculation
        diff = abs(lon1 - lon2)
        if diff > 180:
            diff = 360 - diff

        # If the difference is less than the aspect angle, it's approaching
        return diff < aspect_angle

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

        # If we get here, the files are valid and usable
        logger.info(f"Ephemeris files verified successfully: {sun_data}")
        return True
    except Exception as e:
        error_msg = f"Ephemeris files validation failed: {str(e)}"
        logger.error(error_msg)
        raise EphemerisError(error_msg)
