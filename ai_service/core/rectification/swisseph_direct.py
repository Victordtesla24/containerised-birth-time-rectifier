"""
Direct Swiss Ephemeris calculator for astrological charts.

This module provides direct access to the Swiss Ephemeris library for calculating
accurate astrological charts without intermediate abstractions.
"""

import logging
import os
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

import swisseph as swe

logger = logging.getLogger(__name__)

# Set up Swiss Ephemeris with the path from environment variable
EPHEMERIS_PATH = os.environ.get("SWISSEPH_PATH", "/app/ephemeris")
try:
    swe.set_ephe_path(EPHEMERIS_PATH)
    logger.info(f"Swiss Ephemeris path set to: {EPHEMERIS_PATH}")
except Exception as e:
    logger.error(f"Error setting Swiss Ephemeris path: {e}")

# Define constants
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

HOUSE_SYSTEMS = {
    "placidus": b'P',
    "koch": b'K',
    "porphyrius": b'O',
    "regiomontanus": b'R',
    "campanus": b'C',
    "equal": b'E',
    "whole_sign": b'W',
    "alcabitius": b'B'
}

# Map planet IDs to names
PLANET_MAP = {
    swe.SUN: "Sun",
    swe.MOON: "Moon",
    swe.MERCURY: "Mercury",
    swe.VENUS: "Venus",
    swe.MARS: "Mars",
    swe.JUPITER: "Jupiter",
    swe.SATURN: "Saturn",
    swe.URANUS: "Uranus",
    swe.NEPTUNE: "Neptune",
    swe.PLUTO: "Pluto",
    swe.MEAN_NODE: "North Node",
    swe.TRUE_NODE: "True Node",
    swe.CHIRON: "Chiron"
}

def calculate_swiss_ephemeris_chart(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    house_system: str = "placidus",
    is_sidereal: bool = False,
    ayanamsa_method: int = swe.SIDM_LAHIRI
) -> Dict[str, Any]:
    """
    Calculate a complete astrological chart using Swiss Ephemeris.

    Args:
        birth_dt: Birth date and time (timezone-aware)
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        house_system: House system to use (default: 'placidus')
        is_sidereal: Whether to use sidereal zodiac instead of tropical
        ayanamsa_method: Ayanamsa method for sidereal calculations

    Returns:
        Dict containing the complete chart data
    """
    try:
        # Convert datetime to Julian day
        logger.debug("Converting datetime to Julian day")
        jd_ut = convert_datetime_to_jd(birth_dt)
        logger.debug(f"Julian day: {jd_ut}")

        # Set ayanamsa for sidereal calculations
        ayanamsa = 0
        if is_sidereal:
            logger.debug(f"Setting sidereal mode with ayanamsa method: {ayanamsa_method}")
            swe.set_sid_mode(ayanamsa_method)
            ayanamsa = swe.get_ayanamsa_ut(jd_ut)
            logger.info(f"Using sidereal zodiac with ayanamsa: {ayanamsa:.6f}°")

        # Set topocentric coordinates
        logger.debug(f"Setting topocentric coordinates: lon={longitude}, lat={latitude}")
        swe.set_topo(longitude, latitude, 0)  # 0 altitude

        # Calculate houses and angles
        logger.debug(f"Calculating houses with system: {house_system}")
        hsys = HOUSE_SYSTEMS.get(house_system.lower(), b'P')  # Default to Placidus
        houses_result = swe.houses_ex(jd_ut, latitude, longitude, hsys)
        logger.debug(f"Houses result type: {type(houses_result).__name__}, length: {len(houses_result)}")

        # Extract house cusps and angles
        house_cusps = houses_result[0]  # Array of 12 house cusps
        angles = houses_result[1]      # Array of angles (Asc, MC, etc.)
        logger.debug(f"House cusps length: {len(house_cusps)}, Angles length: {len(angles)}")

        # Calculate planet positions
        logger.debug("Calculating planet positions")
        planets_data = calculate_planet_positions(jd_ut, is_sidereal)
        logger.debug(f"Planets calculated: {len(planets_data)}")

        # Calculate house positions for each planet
        logger.debug("Assigning houses to planets")
        assign_houses_to_planets(planets_data, house_cusps)

        # Create formatted houses data
        logger.debug("Formatting houses data")
        houses_data = format_houses_data(house_cusps)

        # Create formatted angles data
        logger.debug("Formatting angles data")
        angles_data = format_angles_data(angles)

        # Combine all data into chart
        logger.debug("Assembling final chart data")
        chart_data = {
            "chart_id": f"swe_{int(jd_ut)}",
            "calculation_method": "swiss_ephemeris_direct",
            "julian_day": jd_ut,
            "is_sidereal": is_sidereal,
            "ayanamsa": ayanamsa if is_sidereal else 0,
            "ayanamsa_method": ayanamsa_method if is_sidereal else None,
            "house_system": house_system,
            "planets": planets_data,
            "houses": houses_data,
            "angles": angles_data,
            "latitude": latitude,
            "longitude": longitude,
            "birth_time": birth_dt.isoformat()
        }

        return chart_data
    except Exception as e:
        logger.error(f"Error calculating chart: {e}")
        import traceback
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise

def convert_datetime_to_jd(dt: datetime) -> float:
    """
    Convert a datetime object to Julian Day.

    Args:
        dt: Datetime object (must be timezone-aware)

    Returns:
        Julian Day number
    """
    # Extract UTC time components
    utc_dt = dt.astimezone(timezone.utc)
    year = utc_dt.year
    month = utc_dt.month
    day = utc_dt.day
    hour = utc_dt.hour
    minute = utc_dt.minute
    second = utc_dt.second + utc_dt.microsecond / 1e6

    # Calculate time as decimal hours
    hour_decimal = hour + minute/60.0 + second/3600.0

    # Calculate Julian Day
    jd_ut = swe.julday(year, month, day, hour_decimal)

    return jd_ut

def calculate_planet_positions(jd_ut: float, is_sidereal: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Calculate positions for all standard planets.

    Args:
        jd_ut: Julian day (UT)
        is_sidereal: Whether to use sidereal positions

    Returns:
        Dictionary of planet data
    """
    # Set calculation flags
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    if is_sidereal:
        flags |= swe.FLG_SIDEREAL

    planets_data = {}

    # Calculate positions for each planet
    for planet_id, planet_name in PLANET_MAP.items():
        try:
            # Calculate planet position - returns a tuple with two elements:
            # 1. A tuple containing the positions, velocities, etc.
            # 2. An integer return code
            result = swe.calc_ut(jd_ut, planet_id, flags)

            # Unpack the result properly
            positions_tuple = result[0]  # The first element is a tuple with all the planetary data

            # Extract data from the positions tuple
            longitude = positions_tuple[0]  # Longitude in degrees
            latitude = positions_tuple[1]   # Latitude in degrees
            distance = positions_tuple[2]   # Distance in AU

            # The speed values might be zero in some library versions, so handle this safely
            speed_long = positions_tuple[3] if len(positions_tuple) > 3 else 0.0
            speed_lat = positions_tuple[4] if len(positions_tuple) > 4 else 0.0
            speed_dist = positions_tuple[5] if len(positions_tuple) > 5 else 0.0

            # Determine zodiac sign
            sign_num = int(longitude / 30) % 12
            sign = ZODIAC_SIGNS[sign_num]

            # Determine if retrograde
            is_retrograde = speed_long < 0

            # Store planet data
            planets_data[planet_name.lower()] = {
                "name": planet_name,
                "longitude": longitude,
                "latitude": latitude,
                "distance": distance,
                "speed": speed_long,
                "speed_lat": speed_lat,
                "speed_dist": speed_dist,
                "sign": sign,
                "sign_num": sign_num,
                "sign_longitude": longitude % 30,
                "retrograde": is_retrograde
            }
        except Exception as e:
            logger.warning(f"Error calculating position for {planet_name}: {e}")

    return planets_data

def assign_houses_to_planets(planets_data: Dict[str, Dict[str, Any]], house_cusps: Tuple) -> None:
    """
    Determine which house each planet is in.

    Args:
        planets_data: Dictionary of planet data
        house_cusps: Tuple of house cusp longitudes

    Returns:
        None (modifies planets_data in place)
    """
    if not planets_data:
        logger.error("No planet data available to assign houses")
        raise ValueError("No planet data available to assign houses")

    if not house_cusps or len(house_cusps) < 12:  # Need at least 12 cusps for the 12 houses
        logger.error(f"Invalid house cusps data for house assignment: {house_cusps}")
        raise ValueError(f"Invalid house cusps data for house assignment: {house_cusps}")

    for planet_name, planet_data in planets_data.items():
        planet_long = planet_data["longitude"]
        house = determine_house(planet_long, house_cusps)
        planet_data["house"] = house

def determine_house(longitude: float, house_cusps: Tuple) -> int:
    """
    Determine which house a planet is in based on its longitude.

    Args:
        longitude: Planet longitude in degrees
        house_cusps: Tuple of house cusp longitudes

    Returns:
        House number (1-12)
    """
    # Validate inputs
    if not isinstance(house_cusps, (tuple, list)) or len(house_cusps) < 12:
        logger.error(f"Invalid house cusps data: {house_cusps}")
        raise ValueError(f"Invalid house cusps data: {house_cusps}")

    # Normalize longitude to 0-360
    lon = longitude % 360

    # Check each house
    for i in range(0, 11):  # House cusps are now 0-indexed
        cusp1 = house_cusps[i] % 360
        cusp2 = house_cusps[(i + 1) % 12] % 360  # Wrap around for the last house

        # If house crosses 0°, we need special handling
        if cusp2 < cusp1:
            if lon >= cusp1 or lon < cusp2:
                return i + 1  # Convert to 1-indexed house number
        else:
            if cusp1 <= lon < cusp2:
                return i + 1  # Convert to 1-indexed house number

    # If not found in houses 1-11, it must be in house 12
    return 12

def format_houses_data(house_cusps: Tuple) -> List[Dict[str, Any]]:
    """
    Format house cusps data.

    Args:
        house_cusps: Tuple of house cusp longitudes

    Returns:
        List of house data dictionaries
    """
    if not house_cusps or len(house_cusps) < 12:  # Need exactly 12 houses
        logger.error(f"Invalid house cusps data: {house_cusps}")
        raise ValueError(f"Invalid house cusps data: {house_cusps}")

    houses_data = []

    # House cusps are 0-indexed in the tuple but traditionally 1-indexed in astrology
    for i in range(0, 12):
        longitude = house_cusps[i]

        # Determine sign
        sign_num = int(longitude / 30) % 12
        sign = ZODIAC_SIGNS[sign_num]

        houses_data.append({
            "house": i + 1,  # Convert to 1-indexed house number
            "longitude": longitude,
            "sign": sign,
            "sign_num": sign_num,
            "sign_longitude": longitude % 30
        })

    return houses_data

def format_angles_data(angles: Tuple) -> Dict[str, Dict[str, Any]]:
    """
    Format major angles data.

    Args:
        angles: Tuple of angles data from Swiss Ephemeris

    Returns:
        Dictionary of angle data
    """
    if not angles or len(angles) < 2:
        logger.error(f"Invalid angles data: {angles}")
        raise ValueError(f"Invalid angles data: {angles}")

    # Extract major angles
    asc_lon = angles[0]  # Ascendant longitude
    mc_lon = angles[1]   # Midheaven longitude

    # Create angles data dictionary
    angles_data = {
        "ascendant": format_angle_data("Ascendant", asc_lon),
        "midheaven": format_angle_data("Midheaven", mc_lon)
    }

    # Add additional points if available
    if len(angles) > 2:
        angles_data["descendant"] = format_angle_data("Descendant", angles[2])
    if len(angles) > 3:
        angles_data["imum_coeli"] = format_angle_data("Imum Coeli", angles[3])

    return angles_data

def format_angle_data(name: str, longitude: float) -> Dict[str, Any]:
    """
    Format data for a single angle.

    Args:
        name: Name of the angle
        longitude: Longitude of the angle

    Returns:
        Dictionary of angle data
    """
    # Determine sign
    sign_num = int(longitude / 30) % 12
    sign = ZODIAC_SIGNS[sign_num]

    return {
        "name": name,
        "longitude": longitude,
        "sign": sign,
        "sign_num": sign_num,
        "sign_longitude": longitude % 30
    }
