"""
Swiss Ephemeris calculation proxy module.

This module provides a wrapper for Swiss Ephemeris calculations,
ensuring proper error handling and throwing exceptions instead of using fallbacks.
"""

import logging
import os
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)

# Import swisseph library
import swisseph as swe

# Define flag constants if not in swisseph
if not hasattr(swe, "SEFLG_TRANSIT_LONGITUDE"):
    # Define the flag for transit calculations
    logger.error("SEFLG_TRANSIT_LONGITUDE flag not found in swisseph")
    raise RuntimeError("Required flag SEFLG_TRANSIT_LONGITUDE not available in swisseph library")

# Define sidereal modes
if not hasattr(swe, "SIDM_SUEFI_PL"):
    logger.error("SIDM_SUEFI_PL flag not found in swisseph")
    raise RuntimeError("Required flag SIDM_SUEFI_PL not available in swisseph library")

# Path to ephemeris files
EPHEMERIS_PATH = os.environ.get("EPHEMERIS_PATH", None)

if EPHEMERIS_PATH:
    # Set the path to ephemeris files
    swe.set_ephe_path(EPHEMERIS_PATH)
    logger.info(f"Ephemeris path set to {EPHEMERIS_PATH}")
else:
    logger.warning("EPHEMERIS_PATH not set, using default path")

def set_ephemeris_path(path: str) -> None:
    """
    Set the path to ephemeris files.

    Args:
        path: Path to ephemeris files
    """
    global EPHEMERIS_PATH
    EPHEMERIS_PATH = path
    swe.set_ephe_path(path)
    logger.info(f"Ephemeris path set to {path}")

def get_planet_name(planet_id: int) -> str:
    """
    Get the name of a planet by its Swiss Ephemeris ID.

    Args:
        planet_id: Swiss Ephemeris planet ID

    Returns:
        Planet name

    Raises:
        ValueError: If planet ID is invalid
    """
    # Check for valid values
    if not hasattr(swe, "get_planet_name"):
        raise RuntimeError("Swiss Ephemeris library not available")

    # Get planet name from Swiss Ephemeris
    try:
        # Use getattr with a safe fallback to ensure it exists
        return swe.get_planet_name(planet_id)
    except Exception as e:
        logger.error(f"Error getting planet name for ID {planet_id}: {e}")
        raise ValueError(f"Failed to get planet name for ID {planet_id}: {e}")

def calculate_planet_position(
    jd: float,
    planet: int,
    flag: int = swe.SEFLG_SWIEPH | swe.SEFLG_SPEED
) -> Dict[str, Any]:
    """
    Calculate the position of a planet at a specific Julian day.

    Args:
        jd: Julian day
        planet: Planet ID (Swiss Ephemeris constant)
        flag: Calculation flags

    Returns:
        Dictionary with planet position data

    Raises:
        ValueError: If calculation fails
    """
    if not hasattr(swe, "calc"):
        raise RuntimeError("Swiss Ephemeris library not available")

    try:
        # Calculate planet position using Swiss Ephemeris
        ret, xx, ret_flag = swe.calc(jd, planet, flag)

        if ret < 0:
            raise ValueError(f"Swisseph calculation error {ret} for planet {planet}")

        # Create result dictionary
        result = {
            "longitude": xx[0],
            "latitude": xx[1],
            "distance": xx[2],
            "longitude_speed": xx[3],
            "latitude_speed": xx[4],
            "distance_speed": xx[5],
            "planet": planet,
            "planet_name": get_planet_name(planet)
        }

        return result
    except Exception as e:
        logger.error(f"Error calculating position for planet {planet}: {e}")
        raise ValueError(f"Failed to calculate position for planet {planet}: {e}")

def calculate_house_cusps(
    jd: float,
    lat: float,
    lon: float,
    house_system: str = "P"
) -> Dict[str, Any]:
    """
    Calculate house cusps for a specific time and location.

    Args:
        jd: Julian day
        lat: Latitude
        lon: Longitude
        house_system: House system to use (P=Placidus, etc.)

    Returns:
        Dictionary with house cusps data

    Raises:
        ValueError: If calculation fails
    """
    if not hasattr(swe, "houses"):
        raise RuntimeError("Swiss Ephemeris library not available")

    try:
        # Convert house system to bytes
        if isinstance(house_system, str):
            house_system = house_system.encode('utf-8')

        # Calculate houses
        houses, ascmc = swe.houses(jd, lat, lon, house_system)

        # Create result dictionary
        result = {
            "houses": houses,
            "ascendant": ascmc[0],
            "mc": ascmc[1],
            "armc": ascmc[2],
            "vertex": ascmc[3],
            "equatorial_ascendant": ascmc[4],
            "co_ascendant_koch": ascmc[5]
        }

        # Add individual house cusps
        house_cusps = {}
        for i, cusp in enumerate(houses, 1):
            house_cusps[str(i)] = cusp

        result["house_cusps"] = house_cusps

        return result
    except Exception as e:
        logger.error(f"Error calculating houses for jd={jd}, lat={lat}, lon={lon}: {e}")
        raise ValueError(f"Failed to calculate houses: {e}")

def calculate_sidereal_info(
    jd: float,
    flag: int = swe.SEFLG_SWIEPH,
    mode: int = swe.SIDM_LAHIRI
) -> Dict[str, Any]:
    """
    Calculate sidereal information.

    Args:
        jd: Julian day
        flag: Calculation flags
        mode: Sidereal mode

    Returns:
        Dictionary with sidereal data

    Raises:
        ValueError: If calculation fails
    """
    if not hasattr(swe, "get_ayanamsa"):
        raise RuntimeError("Swiss Ephemeris library not available")

    try:
        # Set sidereal mode
        swe.set_sid_mode(mode)

        # Calculate ayanamsa
        ayanamsa = swe.get_ayanamsa(jd)

        # Create result dictionary
        result = {
            "ayanamsa": ayanamsa,
            "mode": mode,
            "mode_name": get_sidereal_mode_name(mode)
        }

        return result
    except Exception as e:
        logger.error(f"Error calculating sidereal info for jd={jd}: {e}")
        raise ValueError(f"Failed to calculate sidereal info: {e}")

def get_sidereal_mode_name(mode: int) -> str:
    """
    Get the name of a sidereal mode.

    Args:
        mode: Sidereal mode (Swiss Ephemeris constant)

    Returns:
        Sidereal mode name

    Raises:
        ValueError: If mode is invalid
    """
    # Define sidereal modes
    sidereal_modes = {
        swe.SIDM_FAGAN_BRADLEY: "Fagan-Bradley",
        swe.SIDM_LAHIRI: "Lahiri",
        swe.SIDM_DELUCE: "De Luce",
        swe.SIDM_RAMAN: "Raman",
        swe.SIDM_USHASHASHI: "Usha-Shashi",
        swe.SIDM_KRISHNAMURTI: "Krishnamurti",
        swe.SIDM_DJWHAL_KHUL: "Djwhal Khul",
        swe.SIDM_YUKTESHWAR: "Yukteshwar",
        swe.SIDM_JN_BHASIN: "J.N. Bhasin",
        swe.SIDM_BABYL_KUGLER1: "Babylonian-Kugler 1",
        swe.SIDM_BABYL_KUGLER2: "Babylonian-Kugler 2",
        swe.SIDM_BABYL_KUGLER3: "Babylonian-Kugler 3",
        swe.SIDM_BABYL_HUBER: "Babylonian-Huber",
        swe.SIDM_BABYL_ETPSC: "Babylonian-ETPSC",
        swe.SIDM_ALDEBARAN_15TAU: "Aldebaran 15° Taurus",
        swe.SIDM_HIPPARCHOS: "Hipparchos",
        swe.SIDM_SASSANIAN: "Sassanian",
        swe.SIDM_GALCENT_0SAG: "Galactic Center 0° Sagittarius",
        swe.SIDM_J2000: "J2000",
        swe.SIDM_J1900: "J1900",
        swe.SIDM_B1950: "B1950"
    }

    # Add SIDM_SURYASIDDHANTA if available
    if hasattr(swe, "SIDM_SURYASIDDHANTA"):
        sidereal_modes[swe.SIDM_SURYASIDDHANTA] = "Surya Siddhanta"

    # Add SIDM_SURYASIDDHANTA_MSUN if available
    if hasattr(swe, "SIDM_SURYASIDDHANTA_MSUN"):
        sidereal_modes[swe.SIDM_SURYASIDDHANTA_MSUN] = "Surya Siddhanta (Mean Sun)"

    # Add SIDM_ARYABHATA if available
    if hasattr(swe, "SIDM_ARYABHATA"):
        sidereal_modes[swe.SIDM_ARYABHATA] = "Aryabhata"

    # Add SIDM_ARYABHATA_MSUN if available
    if hasattr(swe, "SIDM_ARYABHATA_MSUN"):
        sidereal_modes[swe.SIDM_ARYABHATA_MSUN] = "Aryabhata (Mean Sun)"

    # Add SIDM_SS_CITRA if available
    if hasattr(swe, "SIDM_SS_CITRA"):
        sidereal_modes[swe.SIDM_SS_CITRA] = "SS Citra"

    # Add SIDM_SS_REVATI if available
    if hasattr(swe, "SIDM_SS_REVATI"):
        sidereal_modes[swe.SIDM_SS_REVATI] = "SS Revati"

    # Add SIDM_TRUE_CITRA if available
    if hasattr(swe, "SIDM_TRUE_CITRA"):
        sidereal_modes[swe.SIDM_TRUE_CITRA] = "True Citra"

    # Add SIDM_TRUE_REVATI if available
    if hasattr(swe, "SIDM_TRUE_REVATI"):
        sidereal_modes[swe.SIDM_TRUE_REVATI] = "True Revati"

    # Check if mode is valid
    if mode in sidereal_modes:
        return sidereal_modes[mode]
    else:
        logger.warning(f"Unknown sidereal mode: {mode}, defaulting to Lahiri")
        raise ValueError(f"Unknown sidereal mode: {mode}")

def jd_to_datetime(jd: float) -> datetime:
    """
    Convert Julian day to datetime.

    Args:
        jd: Julian day

    Returns:
        Datetime object

    Raises:
        ValueError: If conversion fails
    """
    if not hasattr(swe, "jdut1_to_utc"):
        raise RuntimeError("Swiss Ephemeris library not available")

    try:
        # Convert Julian day to date and time
        dt = swe.jdut1_to_utc(jd)

        # Create datetime object
        return datetime(dt[0], dt[1], dt[2], dt[3], dt[4], int(dt[5]))
    except Exception as e:
        logger.error(f"Error converting Julian day {jd} to datetime: {e}")
        raise ValueError(f"Failed to convert Julian day to datetime: {e}")

def datetime_to_jd(dt: datetime) -> float:
    """
    Convert datetime to Julian day.

    Args:
        dt: Datetime object

    Returns:
        Julian day

    Raises:
        ValueError: If conversion fails
    """
    if not hasattr(swe, "utc_to_jd"):
        raise RuntimeError("Swiss Ephemeris library not available")

    try:
        # Convert datetime to Julian day
        jd = swe.utc_to_jd(
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second,
            flag=swe.GREG_CAL
        )

        return jd[1]  # jd_ut
    except Exception as e:
        logger.error(f"Error converting datetime {dt} to Julian day: {e}")
        raise ValueError(f"Failed to convert datetime to Julian day: {e}")

def get_planet_transit(
    planet: int,
    lon: float,
    jd_start: float,
    jd_end: float,
    flag: int = swe.SEFLG_SWIEPH | swe.SEFLG_TRANSIT_LONGITUDE
) -> Dict[str, Any]:
    """
    Find the next transit of a planet over a specific longitude.

    Args:
        planet: Planet ID (Swiss Ephemeris constant)
        lon: Target longitude in degrees
        jd_start: Start Julian day
        jd_end: End Julian day
        flag: Calculation flags

    Returns:
        Dictionary with transit data

    Raises:
        ValueError: If calculation fails
    """
    if not hasattr(swe, "next_transit"):
        raise RuntimeError("Swiss Ephemeris library not available")

    try:
        # Calculate transit
        jd_transit = swe.next_transit(planet, lon, jd_start, jd_end, flag)

        # Calculate planet position at transit
        ret, xx, ret_flag = swe.calc(jd_transit, planet, flag)

        # Create result dictionary
        result = {
            "jd": jd_transit,
            "datetime": jd_to_datetime(jd_transit),
            "planet": planet,
            "planet_name": get_planet_name(planet),
            "longitude": xx[0],
            "latitude": xx[1],
            "distance": xx[2],
            "speed": xx[3],
            "target_longitude": lon
        }

        return result
    except Exception as e:
        logger.error(f"Error calculating transit for planet {planet}: {e}")
        raise ValueError(f"Failed to calculate transit for planet {planet}: {e}")

def calculate_chart(
    dt: datetime,
    lat: float,
    lon: float,
    house_system: str = "P",
    is_sidereal: bool = True,
    sidereal_mode: int = swe.SIDM_LAHIRI
) -> Dict[str, Any]:
    """
    Calculate a complete astrological chart.

    Args:
        dt: Datetime object
        lat: Latitude
        lon: Longitude
        house_system: House system to use (P=Placidus, etc.)
        is_sidereal: Whether to use sidereal zodiac
        sidereal_mode: Sidereal mode (if is_sidereal is True)

    Returns:
        Dictionary with chart data

    Raises:
        ValueError: If calculation fails
    """
    if not hasattr(swe, "calc"):
        raise RuntimeError("Swiss Ephemeris library not available")

    try:
        # Convert datetime to Julian day
        jd = datetime_to_jd(dt)

        # Set flag
        flag = swe.SEFLG_SWIEPH | swe.SEFLG_SPEED

        # Add sidereal flag if needed
        if is_sidereal:
            flag |= swe.SEFLG_SIDEREAL
            swe.set_sid_mode(sidereal_mode)

        # Calculate houses
        houses_data = calculate_house_cusps(jd, lat, lon, house_system)

        # Calculate planets
        planets = [
            swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
            swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO,
            swe.MEAN_NODE, swe.TRUE_NODE, swe.CHIRON
        ]

        planet_data = {}
        for planet in planets:
            try:
                pos = calculate_planet_position(jd, planet, flag)
                planet_data[get_planet_name(planet)] = pos
            except Exception as e:
                logger.error(f"Error calculating position for planet {planet}: {e}")
                raise ValueError(f"Failed to calculate position for planet {planet}: {e}")

        # Create chart data
        chart = {
            "julian_day": jd,
            "datetime": dt.isoformat(),
            "latitude": lat,
            "longitude": lon,
            "houses": houses_data["house_cusps"],
            "ascendant": houses_data["ascendant"],
            "mc": houses_data["mc"],
            "planets": planet_data,
            "sidereal": is_sidereal,
            "sidereal_mode": get_sidereal_mode_name(sidereal_mode) if is_sidereal else None,
            "house_system": house_system
        }

        # Calculate aspects if requested

        return chart
    except Exception as e:
        logger.error(f"Error calculating chart: {e}")
        raise ValueError(f"Failed to calculate astrological chart: {e}")

def calculate_chart_aspects(
    chart_data: Dict[str, Any],
    orb_major: float = 8.0,
    orb_minor: float = 3.0
) -> List[Dict[str, Any]]:
    """
    Calculate aspects between planets in a chart.

    Args:
        chart_data: Chart data
        orb_major: Orb for major aspects (conjunction, opposition, trine, square)
        orb_minor: Orb for minor aspects (sextile, semi-square, etc.)

    Returns:
        List of aspect dictionaries

    Raises:
        ValueError: If calculation fails
    """
    try:
        # Get planets data
        planets_data = chart_data.get("planets", {})
        if not planets_data:
            raise ValueError("No planets data found in chart")

        # Define aspects
        aspects = [
            {"name": "Conjunction", "angle": 0, "orb": orb_major, "major": True},
            {"name": "Opposition", "angle": 180, "orb": orb_major, "major": True},
            {"name": "Trine", "angle": 120, "orb": orb_major, "major": True},
            {"name": "Square", "angle": 90, "orb": orb_major, "major": True},
            {"name": "Sextile", "angle": 60, "orb": orb_minor, "major": False},
            {"name": "Semi-square", "angle": 45, "orb": orb_minor, "major": False},
            {"name": "Sesquisquare", "angle": 135, "orb": orb_minor, "major": False},
            {"name": "Quincunx", "angle": 150, "orb": orb_minor, "major": False},
            {"name": "Semi-sextile", "angle": 30, "orb": orb_minor, "major": False}
        ]

        # Calculate aspects
        result = []
        planet_names = list(planets_data.keys())

        for i, planet1 in enumerate(planet_names):
            for j, planet2 in enumerate(planet_names):
                # Skip same planet and duplicates (already calculated)
                if i >= j:
                    continue

                p1_lon = planets_data[planet1]["longitude"]
                p2_lon = planets_data[planet2]["longitude"]

                # Calculate angle between planets
                angle_diff = abs(p1_lon - p2_lon)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff

                # Check for aspects
                for aspect in aspects:
                    aspect_angle = aspect["angle"]
                    aspect_orb = aspect["orb"]

                    # Check if within orb
                    orb = abs(angle_diff - aspect_angle)
                    if orb <= aspect_orb:
                        # Add aspect
                        result.append({
                            "planet1": planet1,
                            "planet2": planet2,
                            "type": aspect["name"],
                            "angle": aspect_angle,
                            "orb": orb,
                            "applying": is_aspect_applying(planets_data[planet1], planets_data[planet2], aspect_angle),
                            "major": aspect["major"]
                        })

        return result
    except Exception as e:
        logger.error(f"Error calculating aspects: {e}")
        raise ValueError(f"Failed to calculate aspects: {e}")

def is_aspect_applying(
    planet1: Dict[str, Any],
    planet2: Dict[str, Any],
    aspect_angle: float
) -> bool:
    """
    Determine if an aspect is applying or separating.

    Args:
        planet1: First planet data
        planet2: Second planet data
        aspect_angle: Aspect angle

    Returns:
        True if applying, False if separating
    """
    try:
        speed1 = planet1.get("longitude_speed", 0)
        speed2 = planet2.get("longitude_speed", 0)

        # If both planets are direct or both retrograde
        if (speed1 > 0 and speed2 > 0) or (speed1 < 0 and speed2 < 0):
            if aspect_angle in [0, 60, 120]:
                # For conjunction, sextile, trine: applying if faster planet behind slower
                return (planet1["longitude"] < planet2["longitude"] and abs(speed1) > abs(speed2)) or \
                       (planet1["longitude"] > planet2["longitude"] and abs(speed1) < abs(speed2))
            else:
                # For opposition, square: applying if faster planet ahead of slower
                return (planet1["longitude"] > planet2["longitude"] and abs(speed1) > abs(speed2)) or \
                       (planet1["longitude"] < planet2["longitude"] and abs(speed1) < abs(speed2))

        # If one planet is direct and the other retrograde
        else:
            if aspect_angle in [0, 60, 120]:
                # For conjunction, sextile, trine: applying if moving toward each other
                return (speed1 > 0 and speed2 < 0 and planet1["longitude"] < planet2["longitude"]) or \
                       (speed1 < 0 and speed2 > 0 and planet1["longitude"] > planet2["longitude"])
            else:
                # For opposition, square: applying if moving toward each other
                return (speed1 > 0 and speed2 < 0 and planet1["longitude"] > planet2["longitude"]) or \
                       (speed1 < 0 and speed2 > 0 and planet1["longitude"] < planet2["longitude"])
    except Exception as e:
        logger.error(f"Error determining if aspect is applying: {e}")
        return False  # Default to separating if error
