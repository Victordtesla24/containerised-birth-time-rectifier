"""DEPRECATED: This file has been moved as part of code deduplication.

This functionality has been moved to ai_service.core.rectification.chart_calculator
Please update your imports to use ai_service.core.rectification.chart_calculator directly.

Example:
from ai_service.core.rectification.chart_calculator import calculate_chart

For more advanced chart functionality:
from ai_service.core.rectification.chart_calculator import calculate_chart
"""

# Import datetime for legacy compatibility
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List, Union, Tuple
import math
import traceback
import os
from pathlib import Path

# Import from the new module to allow legacy imports to still work
from ai_service.core.rectification.chart_calculator import (
    calculate_chart as new_calculate_chart,
    get_planets_list,
    normalize_longitude
)

# Create a logger
logger = logging.getLogger(__name__)

# Legacy wrapper function to maintain backward compatibility
def calculate_chart(birth_data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Calculate an astrological chart based on birth data.

    Args:
        birth_data: Dictionary containing birth date, time, and location.
        options: Dictionary of chart calculation options (optional).

    Returns:
        Dict containing the calculated chart data.
    """
    options = options or {}

    # Extract birth data
    date_str = birth_data.get("date", "")
    time_str = birth_data.get("time", "")
    latitude = birth_data.get("latitude")
    longitude = birth_data.get("longitude")

    # Validate required inputs
    if not all([date_str, time_str, latitude is not None, longitude is not None]):
        raise ValueError("Missing required birth data for chart calculation")

    # Parse date and time
    try:
        year, month, day = map(int, date_str.split("-"))
        hour, minute = map(int, time_str.split(":"))

        # Set seconds to 0 if not provided
        second = 0

        birth_datetime = datetime(year, month, day, hour, minute, second)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid date or time format: {e}")

    # Extract timezone if provided
    timezone_str = birth_data.get("timezone", "UTC")

    # Call the new implementation
    try:
        # Ensure latitude and longitude are floats
        if latitude is None or longitude is None:
            raise ValueError("Latitude and longitude must not be None")

        lat_float = float(latitude)
        lon_float = float(longitude)

        return new_calculate_chart(
            birth_datetime,
            lat_float,
            lon_float,
            timezone_str
        )
    except Exception as e:
        logger.error(f"Error in calculate_chart: {e}")
        logger.error(traceback.format_exc())
        raise

def calculate_tropical_chart(birth_datetime: datetime, latitude: float, longitude: float, house_system: str = "P") -> Dict[str, Any]:
    """
    Calculate a tropical (Western) astrological chart.

    Args:
        birth_datetime: The date and time of birth.
        latitude: Birth location latitude.
        longitude: Birth location longitude.
        house_system: House system to use (default to Placidus).

    Returns:
        Dict containing tropical chart data.
    """
    import swisseph as swe

    # Set ephemeris path if available
    ephemeris_path = os.environ.get("SWISSEPH_PATH")
    if ephemeris_path:
        swe.set_ephe_path(ephemeris_path)

    # Convert datetime to Julian day
    year = birth_datetime.year
    month = birth_datetime.month
    day = birth_datetime.day
    hour = birth_datetime.hour
    minute = birth_datetime.minute
    second = birth_datetime.second

    # Calculate Julian day
    jd = swe.julday(year, month, day, hour + minute/60.0 + second/3600.0)

    # Set calculation flags
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    # Dictionary to store result
    tropical_chart: Dict[str, Any] = {
        "planets": [],
        "houses": [],
        "ascendant": {}
    }

    # Calculate planetary positions
    planet_map = {
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

    for planet_name, planet_id in planet_map.items():
        try:
            result = swe.calc_ut(jd, planet_id, flags)
            longitude = result[0]
            latitude = result[1]
            distance = result[2]
            speed = result[3]  # Speed in longitude

            # Determine zodiac sign
            sign_index = int(longitude / 30)
            sign_names = [
                "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
            ]
            sign = sign_names[sign_index]

            planet_data = {
                "name": planet_name,
                "longitude": longitude,
                "latitude": latitude,
                "distance": distance,
                "speed": speed,
                "sign": sign,
                "sign_longitude": longitude % 30,
                "retrograde": speed < 0
            }

            tropical_chart["planets"].append(planet_data)

        except Exception as e:
            logger.error(f"Error calculating position for {planet_name}: {e}")

    # Calculate houses and angles
    house_system_map = {
        "P": b'P',  # Placidus
        "K": b'K',  # Koch
        "O": b'O',  # Porphyrius
        "R": b'R',  # Regiomontanus
        "C": b'C',  # Campanus
        "A": b'A',  # Equal (Vehlow)
        "E": b'E',  # Equal
        "W": b'W',  # Whole sign
        "B": b'B',  # Alcabitius
    }

    hsys = house_system_map.get(house_system, b'P')  # Default to Placidus

    try:
        # Calculate houses
        houses_result = swe.houses(jd, latitude, longitude, hsys)

        # Houses_result contains:
        # 0: array of 12 house cusps
        # 1: array of 8 additional points (ascendant, MC, etc.)

        house_cusps = houses_result[0]
        angles = houses_result[1]

        # Extract house cusps
        for i in range(1, 13):  # Houses are 1-12
            house_data = {
                "house": i,
                "longitude": house_cusps[i],
                "sign": sign_names[int(house_cusps[i] / 30)],
                "sign_longitude": house_cusps[i] % 30
            }
            tropical_chart["houses"].append(house_data)

        # Extract angles
        ascendant = angles[0]
        midheaven = angles[1]

        tropical_chart["ascendant"] = {
            "longitude": ascendant,
            "sign": sign_names[int(ascendant / 30)],
            "sign_longitude": ascendant % 30
        }

        tropical_chart["midheaven"] = {
            "longitude": midheaven,
            "sign": sign_names[int(midheaven / 30)],
            "sign_longitude": midheaven % 30
        }

    except Exception as e:
        logger.error(f"Error calculating houses: {e}")

    return tropical_chart

def calculate_vedic_chart(birth_datetime: datetime, latitude: float, longitude: float, house_system: str = "W", ayanamsa_type: str = "lahiri") -> Dict[str, Any]:
    """
    Calculate a Vedic astrological chart using proper ayanamsa (precession).

    Args:
        birth_datetime: The date and time of birth.
        latitude: Birth location latitude.
        longitude: Birth location longitude.
        house_system: House system to use (default to Whole Sign for Vedic).
        ayanamsa_type: Type of ayanamsa to use (default to Lahiri).

    Returns:
        Dict containing Vedic chart data.
    """
    import swisseph as swe

    # Set ephemeris path if available
    ephemeris_path = os.environ.get("SWISSEPH_PATH")
    if ephemeris_path:
        swe.set_ephe_path(ephemeris_path)

    # Convert datetime to Julian day
    year = birth_datetime.year
    month = birth_datetime.month
    day = birth_datetime.day
    hour = birth_datetime.hour
    minute = birth_datetime.minute
    second = birth_datetime.second

    # Calculate Julian day
    jd = swe.julday(year, month, day, hour + minute/60.0 + second/3600.0)

    # Set ayanamsa type
    ayanamsa_map = {
        "lahiri": swe.SIDM_LAHIRI,
        "raman": swe.SIDM_RAMAN,
        "krishnamurti": swe.SIDM_KRISHNAMURTI,
        "djwhal_khul": swe.SIDM_DJWHAL_KHUL,
        "fagan_bradley": swe.SIDM_FAGAN_BRADLEY
    }

    ayanamsa_id = ayanamsa_map.get(ayanamsa_type.lower(), swe.SIDM_LAHIRI)
    swe.set_sid_mode(ayanamsa_id)

    # Get ayanamsa value
    ayanamsa = swe.get_ayanamsa_ut(jd)

    # Calculate tropical chart first
    tropical_chart = calculate_tropical_chart(birth_datetime, latitude, longitude, house_system)

    # Convert to Vedic (sidereal) positions
    vedic_planets = []
    for planet in tropical_chart["planets"]:
        # Convert tropical longitude to sidereal
        sidereal_longitude = (planet["longitude"] - ayanamsa) % 360

        # Determine sidereal zodiac sign
        sign_index = int(sidereal_longitude / 30)
        sign_names = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        sign = sign_names[sign_index]

        # Create Vedic planet data
        vedic_planet = {
            "name": planet["name"],
            "longitude": sidereal_longitude,
            "latitude": planet["latitude"],
            "distance": planet.get("distance", 0),
            "speed": planet["speed"],
            "sign": sign,
            "sign_longitude": sidereal_longitude % 30,
            "retrograde": planet["retrograde"]
        }

        vedic_planets.append(vedic_planet)

    # Convert houses to sidereal
    vedic_houses = []
    for house in tropical_chart["houses"]:
        sidereal_longitude = (house["longitude"] - ayanamsa) % 360
        sign_index = int(sidereal_longitude / 30)
        sign = sign_names[sign_index]

        vedic_house = {
            "house": house["house"],
            "longitude": sidereal_longitude,
            "sign": sign,
            "sign_longitude": sidereal_longitude % 30
        }

        vedic_houses.append(vedic_house)

    # Convert ascendant to sidereal
    asc_tropical = tropical_chart["ascendant"]
    asc_sidereal_longitude = (asc_tropical["longitude"] - ayanamsa) % 360
    asc_sign_index = int(asc_sidereal_longitude / 30)
    asc_sign = sign_names[asc_sign_index]

    # Create Vedic chart
    vedic_chart: Dict[str, Any] = {
        "planets": vedic_planets,
        "houses": vedic_houses,
        "ascendant": {
            "longitude": asc_sidereal_longitude,
            "sign": asc_sign,
            "sign_longitude": asc_sidereal_longitude % 30
        },
        "ayanamsa": {
            "type": ayanamsa_type,
            "value": ayanamsa
        }
    }

    # Add midheaven if available
    if "midheaven" in tropical_chart:
        mc_tropical = tropical_chart["midheaven"]
        mc_sidereal_longitude = (mc_tropical["longitude"] - ayanamsa) % 360
        mc_sign_index = int(mc_sidereal_longitude / 30)
        mc_sign = sign_names[mc_sign_index]

        vedic_chart["midheaven"] = {
            "longitude": mc_sidereal_longitude,
            "sign": mc_sign,
            "sign_longitude": mc_sidereal_longitude % 30
        }

    return vedic_chart
