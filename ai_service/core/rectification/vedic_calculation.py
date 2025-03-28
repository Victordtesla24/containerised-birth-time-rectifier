"""
Vedic chart calculation module using Swiss Ephemeris.

This module provides functions to calculate Vedic astrological charts
with a focus on accuracy and reliability for birth time rectification.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Try to import swisseph, but handle it gracefully if not available
try:
    import swisseph as swe
    SWISSEPH_AVAILABLE = True
except ImportError:
    SWISSEPH_AVAILABLE = False
    swe = None
    # We'll raise appropriate exceptions when functions that need swisseph are called
    # rather than using placeholders

# Import from methods if available
try:
    from .methods.astrological_constants import ASC, MC, DSC, IC
except ImportError:
    # Define these constants if not available
    ASC = 0
    MC = 1
    DSC = 2
    IC = 3

logger = logging.getLogger(__name__)

# Constants for planetary bodies
# Define constants directly rather than accessing them from swe when unavailable
SUN = 0
MOON = 1
MERCURY = 2
VENUS = 3
MARS = 4
JUPITER = 5
SATURN = 6
URANUS = 7
NEPTUNE = 8
PLUTO = 9
MEAN_NODE = 10
MEAN_APOG = 11
SIDM_LAHIRI = 1
FLG_SIDEREAL = 1

# Override with actual values if SwissEph is available
if SWISSEPH_AVAILABLE and swe is not None:
    SUN = swe.SUN
    MOON = swe.MOON
    MERCURY = swe.MERCURY
    VENUS = swe.VENUS
    MARS = swe.MARS
    JUPITER = swe.JUPITER
    SATURN = swe.SATURN
    URANUS = swe.URANUS
    NEPTUNE = swe.NEPTUNE
    PLUTO = swe.PLUTO
    MEAN_NODE = swe.MEAN_NODE
    MEAN_APOG = swe.MEAN_APOG
    SIDM_LAHIRI = swe.SIDM_LAHIRI
    FLG_SIDEREAL = swe.FLG_SIDEREAL

# Zodiac signs in traditional Vedic order
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Main planets used in Vedic astrology
VEDIC_PLANETS = [
    SUN, MOON, MERCURY, VENUS,
    MARS, JUPITER, SATURN,
    MEAN_NODE  # Rahu (North Node)
]

# Planet names for easy reference
PLANET_NAMES = {
    SUN: "Sun",
    MOON: "Moon",
    MERCURY: "Mercury",
    VENUS: "Venus",
    MARS: "Mars",
    JUPITER: "Jupiter",
    SATURN: "Saturn",
    MEAN_NODE: "Rahu",
    MEAN_APOG: "Ketu",
    URANUS: "Uranus",
    NEPTUNE: "Neptune",
    PLUTO: "Pluto"
}

# Nakshatras (lunar mansions) data with their lords
NAKSHATRAS = [
    {"name": "Ashwini", "lord": "Ketu", "start_degree": 0, "end_degree": 13.20},
    {"name": "Bharani", "lord": "Venus", "start_degree": 13.20, "end_degree": 26.40},
    {"name": "Krittika", "lord": "Sun", "start_degree": 26.40, "end_degree": 40.00},
    {"name": "Rohini", "lord": "Moon", "start_degree": 40.00, "end_degree": 53.20},
    {"name": "Mrigashirsha", "lord": "Mars", "start_degree": 53.20, "end_degree": 66.40},
    {"name": "Ardra", "lord": "Rahu", "start_degree": 66.40, "end_degree": 80.00},
    {"name": "Punarvasu", "lord": "Jupiter", "start_degree": 80.00, "end_degree": 93.20},
    {"name": "Pushya", "lord": "Saturn", "start_degree": 93.20, "end_degree": 106.40},
    {"name": "Ashlesha", "lord": "Mercury", "start_degree": 106.40, "end_degree": 120.00},
    {"name": "Magha", "lord": "Ketu", "start_degree": 120.00, "end_degree": 133.20},
    {"name": "Purva Phalguni", "lord": "Venus", "start_degree": 133.20, "end_degree": 146.40},
    {"name": "Uttara Phalguni", "lord": "Sun", "start_degree": 146.40, "end_degree": 160.00},
    {"name": "Hasta", "lord": "Moon", "start_degree": 160.00, "end_degree": 173.20},
    {"name": "Chitra", "lord": "Mars", "start_degree": 173.20, "end_degree": 186.40},
    {"name": "Swati", "lord": "Rahu", "start_degree": 186.40, "end_degree": 200.00},
    {"name": "Vishakha", "lord": "Jupiter", "start_degree": 200.00, "end_degree": 213.20},
    {"name": "Anuradha", "lord": "Saturn", "start_degree": 213.20, "end_degree": 226.40},
    {"name": "Jyeshtha", "lord": "Mercury", "start_degree": 226.40, "end_degree": 240.00},
    {"name": "Mula", "lord": "Ketu", "start_degree": 240.00, "end_degree": 253.20},
    {"name": "Purva Ashadha", "lord": "Venus", "start_degree": 253.20, "end_degree": 266.40},
    {"name": "Uttara Ashadha", "lord": "Sun", "start_degree": 266.40, "end_degree": 280.00},
    {"name": "Shravana", "lord": "Moon", "start_degree": 280.00, "end_degree": 293.20},
    {"name": "Dhanishta", "lord": "Mars", "start_degree": 293.20, "end_degree": 306.40},
    {"name": "Shatabhisha", "lord": "Rahu", "start_degree": 306.40, "end_degree": 320.00},
    {"name": "Purva Bhadrapada", "lord": "Jupiter", "start_degree": 320.00, "end_degree": 333.20},
    {"name": "Uttara Bhadrapada", "lord": "Saturn", "start_degree": 333.20, "end_degree": 346.40},
    {"name": "Revati", "lord": "Mercury", "start_degree": 346.40, "end_degree": 360.00}
]

# Planet dignity states
PLANET_DIGNITIES = {
    "Sun": {"exaltation": "Aries", "debilitation": "Libra", "own_sign": ["Leo"]},
    "Moon": {"exaltation": "Taurus", "debilitation": "Scorpio", "own_sign": ["Cancer"]},
    "Mercury": {"exaltation": "Virgo", "debilitation": "Pisces", "own_sign": ["Gemini", "Virgo"]},
    "Venus": {"exaltation": "Pisces", "debilitation": "Virgo", "own_sign": ["Taurus", "Libra"]},
    "Mars": {"exaltation": "Capricorn", "debilitation": "Cancer", "own_sign": ["Aries", "Scorpio"]},
    "Jupiter": {"exaltation": "Cancer", "debilitation": "Capricorn", "own_sign": ["Sagittarius", "Pisces"]},
    "Saturn": {"exaltation": "Libra", "debilitation": "Aries", "own_sign": ["Capricorn", "Aquarius"]},
    "Rahu": {"exaltation": "Taurus", "debilitation": "Scorpio", "own_sign": []},
    "Ketu": {"exaltation": "Scorpio", "debilitation": "Taurus", "own_sign": []}
}

def initialize_ephemeris(path: Optional[str] = None) -> None:
    """
    Initialize the Swiss Ephemeris with the specified path.

    Args:
        path: Path to the ephemeris files, or None to use default

    Raises:
        RuntimeError: If Swiss Ephemeris is not available
    """
    if not SWISSEPH_AVAILABLE or swe is None:
        error_msg = "Swiss Ephemeris not available. Cannot initialize ephemeris."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    if path and swe is not None:
        swe.set_ephe_path(path)
    logger.info(f"Swiss Ephemeris initialized successfully")

def calculate_houses_positions(birth_dt: datetime, lat: float, lon: float) -> Dict[str, Any]:
    """
    Calculate house positions using Swiss Ephemeris.

    Args:
        birth_dt: Birth datetime
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees

    Returns:
        Dictionary with house positions

    Raises:
        RuntimeError: If Swiss Ephemeris is not available
    """
    if not SWISSEPH_AVAILABLE or swe is None:
        error_msg = "Swiss Ephemeris not available. Cannot calculate house positions."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Convert datetime to Julian day
    jd = swe.julday(
        birth_dt.year,
        birth_dt.month,
        birth_dt.day,
        birth_dt.hour + birth_dt.minute/60.0 + birth_dt.second/3600.0
    )

    # Calculate house positions
    houses_result = swe.houses(jd, lat, lon, b'P')  # Placidus house system
    house_cusps = houses_result[0]
    ascendant = houses_result[1][0]  # Ascendant
    midheaven = houses_result[1][1]  # Midheaven

    # Format and return results
    return {
        "cusps": list(house_cusps),
        "ascendant": ascendant,
        "midheaven": midheaven,
        "houses": [{"number": i+1, "longitude": house_cusps[i]} for i in range(len(house_cusps)) if i < 12]
    }

def calculate_ascendant(birth_dt: datetime, lat: float, lon: float) -> float:
    """
    Calculate the ascendant (rising sign) degree.

    Args:
        birth_dt: Birth datetime
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees

    Returns:
        Ascendant degree in 0-360 range

    Raises:
        RuntimeError: If Swiss Ephemeris is not available
    """
    if not SWISSEPH_AVAILABLE or swe is None:
        error_msg = "Swiss Ephemeris not available. Cannot calculate ascendant."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Convert datetime to Julian day
    jd = swe.julday(
        birth_dt.year,
        birth_dt.month,
        birth_dt.day,
        birth_dt.hour + birth_dt.minute/60.0 + birth_dt.second/3600.0
    )

    # Calculate house positions which includes ascendant
    houses_result = swe.houses(jd, lat, lon, b'P')  # Placidus house system
    ascendant = houses_result[1][0]  # Ascendant

    return ascendant

def calculate_vedic_chart(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    house_system: str = "placidus"
) -> Dict[str, Any]:
    """
    Calculate a Vedic astrological chart using Swiss Ephemeris.

    Args:
        birth_dt: Birth datetime (timezone-aware)
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        house_system: House system to use ('placidus', 'whole_sign', 'equal', etc.)

    Returns:
        Dictionary containing the complete Vedic chart data

    Raises:
        RuntimeError: If Swiss Ephemeris is not available or calculation fails
    """
    if not SWISSEPH_AVAILABLE or swe is None:
        error_msg = "Swiss Ephemeris not available. Cannot calculate Vedic chart."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Set ayanamsa to Lahiri (Indian)
    swe.set_sid_mode(SIDM_LAHIRI)

    # Convert datetime to Julian day
    jd = swe.julday(
        birth_dt.year,
        birth_dt.month,
        birth_dt.day,
        birth_dt.hour + birth_dt.minute/60.0 + birth_dt.second/3600.0
    )

    # Get ayanamsa value
    ayanamsa = swe.get_ayanamsa(jd)
    logger.info(f"Using Lahiri ayanamsa: {ayanamsa:.6f}° for JD {jd:.6f}")

    # Map house system string to Swiss Ephemeris constant
    hsys_map = {
        "placidus": b'P',
        "koch": b'K',
        "porphyrius": b'O',
        "regiomontanus": b'R',
        "campanus": b'C',
        "equal": b'E',
        "whole_sign": b'W',
        "sripati": b'I',
        "krishnamurti": b'K'
    }
    hsys = hsys_map.get(house_system.lower(), b'P')  # Default to Placidus

    # Calculate house cusps
    houses_result = swe.houses(jd, latitude, longitude, hsys)
    house_cusps = houses_result[0]
    ascendant = houses_result[1][0]  # Ascendant
    mc = houses_result[1][1]  # Midheaven

    # Calculate positions for all planets
    planets_data = {}
    houses = []
    for i, planet_id in enumerate(VEDIC_PLANETS + [MEAN_APOG, URANUS, NEPTUNE, PLUTO]):
        if planet_id == MEAN_APOG:  # Calculate Ketu (South Node) as opposite to Rahu
            if MEAN_NODE in planets_data:
                rahu_position = planets_data[MEAN_NODE]["longitude"]
                ketu_position = (rahu_position + 180) % 360
                planet_name = "Ketu"

                # Determine sign and degree
                sign_num = int(ketu_position / 30)
                sign = ZODIAC_SIGNS[sign_num]
                degree = ketu_position % 30

                # Determine house
                house = determine_house(ketu_position, house_cusps)

                planets_data[planet_id] = {
                    "id": planet_id,
                    "name": planet_name,
                    "longitude": ketu_position,
                    "latitude": 0.0,  # Ketu has the opposite latitude of Rahu
                    "speed": -planets_data[MEAN_NODE]["speed"],  # Opposite direction
                    "sign": sign,
                    "sign_num": sign_num,
                    "degree": degree,
                    "house": house
                }
            continue

        try:
            # Calculate planet position
            result = swe.calc_ut(jd, planet_id, FLG_SIDEREAL)

            # result is a tuple: (positions_tuple, flags)
            positions_tuple = result[0]  # First element is the positional data tuple

            # Extract position components from the positions tuple
            longitude = positions_tuple[0]  # longitude (degrees)
            latitude = positions_tuple[1]   # latitude (degrees)
            distance = positions_tuple[2]   # distance (AU)

            # Speed in longitude is the 4th element (index 3) if present
            # If not enough elements in tuple, default to 0
            speed = positions_tuple[3] if len(positions_tuple) > 3 else 0.0

            # Determine sign and degree
            sign_num = int(longitude / 30)
            sign = ZODIAC_SIGNS[sign_num]
            degree = longitude % 30

            # Determine house
            house = determine_house(longitude, house_cusps)

            planet_name = PLANET_NAMES.get(planet_id, f"Planet-{planet_id}")

            planets_data[planet_id] = {
                "id": planet_id,
                "name": planet_name,
                "longitude": longitude,
                "latitude": latitude,
                "speed": speed,
                "sign": sign,
                "sign_num": sign_num,
                "degree": degree,
                "house": house
            }
        except Exception as e:
            logger.error(f"Error calculating position for planet {planet_id}: {e}")
            raise RuntimeError(f"Failed to calculate position for planet {planet_name}: {e}")

    # Create formatted houses with sign information
    for i in range(1, 13):
        if i < len(house_cusps):  # Make sure we don't go out of bounds
            cusp_longitude = house_cusps[i]
            sign_num = int(cusp_longitude / 30)
            sign = ZODIAC_SIGNS[sign_num]
            degree = cusp_longitude % 30

            houses.append({
                "number": i,
                "longitude": cusp_longitude,
                "sign": sign,
                "sign_num": sign_num,
                "degree": degree
            })

    # Calculate ascendant (lagna) details
    asc_sign_num = int(ascendant / 30)
    asc_sign = ZODIAC_SIGNS[asc_sign_num]
    asc_degree = ascendant % 30

    # Calculate MC details
    mc_sign_num = int(mc / 30)
    mc_sign = ZODIAC_SIGNS[mc_sign_num]
    mc_degree = mc % 30

    # Calculate descendant and IC
    dsc = (ascendant + 180) % 360
    dsc_sign_num = int(dsc / 30)
    dsc_sign = ZODIAC_SIGNS[dsc_sign_num]
    dsc_degree = dsc % 30

    ic = (mc + 180) % 360
    ic_sign_num = int(ic / 30)
    ic_sign = ZODIAC_SIGNS[ic_sign_num]
    ic_degree = ic % 30

    # Assemble chart data structure
    chart_data = {
        "type": "vedic",
        "ayanamsa": ayanamsa,
        "julian_day": jd,
        "house_system": house_system,
        "ascendant": {
            "id": ASC,
            "name": "Ascendant",
            "longitude": ascendant,
            "sign": asc_sign,
            "sign_num": asc_sign_num,
            "degree": asc_degree
        },
        "mc": {
            "id": MC,
            "name": "Midheaven",
            "longitude": mc,
            "sign": mc_sign,
            "sign_num": mc_sign_num,
            "degree": mc_degree
        },
        "descendant": {
            "id": DSC,
            "name": "Descendant",
            "longitude": dsc,
            "sign": dsc_sign,
            "sign_num": dsc_sign_num,
            "degree": dsc_degree
        },
        "ic": {
            "id": IC,
            "name": "Imum Coeli",
            "longitude": ic,
            "sign": ic_sign,
            "sign_num": ic_sign_num,
            "degree": ic_degree
        },
        "houses": houses,
        "planets": planets_data
    }

    return chart_data

def determine_house(longitude: float, house_cusps: List[float]) -> int:
    """
    Determine which house a given longitude falls into.

    Args:
        longitude: Celestial longitude in degrees
        house_cusps: List of house cusp longitudes

    Returns:
        House number (1-12)
    """
    # Ensure we're checking with valid indices only
    # For each house, check if the position is between this cusp and the next
    for i in range(1, min(12, len(house_cusps) - 1)):
        if house_between_cusps(longitude, house_cusps[i], house_cusps[(i % 12) + 1]):
            return i

    # If not found, it must be in house 12
    return 12

def house_between_cusps(longitude: float, cusp1: float, cusp2: float) -> bool:
    """
    Check if a longitude falls between two house cusps, considering the circular nature.

    Args:
        longitude: Position to check
        cusp1: First house cusp
        cusp2: Second house cusp

    Returns:
        True if position is in the house, False otherwise
    """
    # Handle cases where the house crosses 0° Aries
    if cusp2 < cusp1:  # House crosses 0°
        return longitude >= cusp1 or longitude < cusp2
    else:  # Normal case
        return longitude >= cusp1 and longitude < cusp2

# Functions needed for chart_calculator.py
def get_nakshatra_from_longitude(longitude: float) -> Dict[str, Any]:
    """
    Get nakshatra (lunar mansion) information from a given longitude.

    Args:
        longitude: Celestial longitude in degrees (0-360)

    Returns:
        Dictionary with nakshatra name, lord, pada, etc.
    """
    # Normalize longitude to 0-360 range
    longitude = longitude % 360

    # Each nakshatra is 13°20' (13.33333 degrees)
    nakshatra_span = 360 / 27  # 27 nakshatras total

    # Determine nakshatra index (0-26)
    nakshatra_index = int(longitude / nakshatra_span)

    # Calculate position within nakshatra (0 to nakshatra_span)
    position_in_nakshatra = longitude % nakshatra_span

    # Calculate pada (quarter) within nakshatra (1-4)
    pada = int(position_in_nakshatra / (nakshatra_span / 4)) + 1

    # Get nakshatra data
    nakshatra_data = NAKSHATRAS[nakshatra_index]

    return {
        "name": nakshatra_data["name"],
        "lord": nakshatra_data["lord"],
        "pada": pada,
        "longitude": position_in_nakshatra,
        "total_longitude": longitude,
        "index": nakshatra_index
    }

def calculate_varga_charts(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate divisional charts (varga charts) from the main chart.

    Args:
        chart_data: Main chart data dictionary

    Returns:
        Dictionary of divisional charts
    """
    varga_charts = {
        "D1": chart_data,  # Rashi chart (main chart)
        "D3": chart_data,  # D3 chart
        "D7": chart_data,  # D7 chart
        "D9": {"type": "navamsa", "message": "D9 calculation would be implemented here"},  # Navamsa chart        "D10": chart_data,  # D10 chart
        "D12": chart_data,  # D12 chart
        "D11": chart_data,  # D11 chart
        "D2": chart_data,  # D2 chart
        "D4": chart_data,  # D4 chart
        "D5": chart_data,  # D5 chart
        "D6": chart_data,  # D6 chart
        "D8": chart_data,  # D8 chart
        "D11": chart_data,  # D11 chart
    }

    return varga_charts

def calculate_planet_dignity(planet_name: str, sign: str, degree: float) -> Dict[str, Any]:
    """
    Calculate a planet's dignity in its sign position.

    Args:
        planet_name: Name of the planet
        sign: Sign where planet is located
        degree: Degree within sign (0-30)

    Returns:
        Dictionary with dignity state and details
    """
    if planet_name not in PLANET_DIGNITIES:
        return {"state": "neutral", "details": f"No dignity data for {planet_name}"}

    planet_dignity = PLANET_DIGNITIES[planet_name]

    if sign == planet_dignity.get("exaltation"):
        return {"state": "exalted", "details": f"{planet_name} is exalted in {sign}"}

    if sign == planet_dignity.get("debilitation"):
        return {"state": "debilitated", "details": f"{planet_name} is debilitated in {sign}"}

    if sign in planet_dignity.get("own_sign", []):
        return {"state": "own_sign", "details": f"{planet_name} is in own sign in {sign}"}

    return {"state": "neutral", "details": f"{planet_name} has neutral dignity in {sign}"}

def calculate_shadbala(planet_name: str, chart_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate Shadbala (sixfold strength) for a planet.

    Args:
        planet_name: Name of the planet
        chart_data: Chart data

    Returns:
        Dictionary with shadbala components
    """
    planets = chart_data.get("planets", {})
    if planet_name not in planets:
        return {
            "sthanabala": 0.0,
            "digbala": 0.0,
            "kalabala": 0.0,
            "chestabala": 0.0,
            "naisargikabala": 0.0,
            "drigbala": 0.0,
            "total": 0.0
        }

    planet_data = planets[planet_name]
    sign = planet_data.get("sign", "")
    house = planet_data.get("house", 0)
    longitude = planet_data.get("longitude", 0)

    # Calculate Sthanabala (Positional Strength)
    sthanabala = 0.0
    # Exaltation strength
    if (planet_name == "Sun" and sign == "Aries") or \
       (planet_name == "Moon" and sign == "Taurus") or \
       (planet_name == "Mercury" and sign == "Virgo") or \
       (planet_name == "Venus" and sign == "Pisces") or \
       (planet_name == "Mars" and sign == "Capricorn") or \
       (planet_name == "Jupiter" and sign == "Cancer") or \
       (planet_name == "Saturn" and sign == "Libra"):
        sthanabala += 1.0

    # Moolatrikona strength
    if (planet_name == "Sun" and sign == "Leo") or \
       (planet_name == "Moon" and sign == "Taurus") or \
       (planet_name == "Mercury" and sign == "Virgo") or \
       (planet_name == "Venus" and sign == "Libra") or \
       (planet_name == "Mars" and sign == "Aries") or \
       (planet_name == "Jupiter" and sign == "Sagittarius") or \
       (planet_name == "Saturn" and sign == "Aquarius"):
        sthanabala += 0.75

    # Own sign strength
    if ((planet_name == "Sun" and sign == "Leo") or
        (planet_name == "Moon" and sign == "Cancer") or
        (planet_name == "Mercury" and (sign == "Gemini" or sign == "Virgo")) or
        (planet_name == "Venus" and (sign == "Taurus" or sign == "Libra")) or
        (planet_name == "Mars" and (sign == "Aries" or sign == "Scorpio")) or
        (planet_name == "Jupiter" and (sign == "Sagittarius" or sign == "Pisces")) or
        (planet_name == "Saturn" and (sign == "Capricorn" or sign == "Aquarius"))):
        sthanabala += 0.5

    # Calculate Digbala (Directional Strength)
    digbala = 0.0
    if (planet_name == "Jupiter" and house in [1, 10]) or \
       (planet_name == "Mercury" and (house in [4, 7])) or \
       (planet_name == "Saturn" and house in [7, 1]) or \
       (planet_name == "Mars" and house in [10, 4]):
        digbala += 1.0

    # Calculate Kalabala (Temporal Strength)
    kalabala = 0.5  # Default value for day/night considerations

    # Calculate Chestabala (Motional Strength)
    chestabala = 0.0
    # Direct motion is strong
    chestabala += 1.0  # Assuming direct motion

    # Calculate Naisargikabala (Natural Strength)
    naisargikabala_values = {
        "Sun": 1.0,
        "Moon": 0.85,
        "Jupiter": 0.7,
        "Mercury": 0.55,
        "Venus": 0.4,
        "Mars": 0.25,
        "Saturn": 0.1
    }
    naisargikabala = naisargikabala_values.get(planet_name, 0.0)

    # Calculate Drigbala (Aspectual Strength)
    drigbala = 0.0
    # Calculate aspects from other planets
    for other_planet, other_data in planets.items():
        if other_planet != planet_name:
            other_long = other_data.get("longitude", 0)
            diff = abs(longitude - other_long) % 360
            if diff > 180:
                diff = 360 - diff

            # Check for aspects
            if abs(diff - 0) <= 10:  # Conjunction
                drigbala += 0.1
            elif abs(diff - 120) <= 10:  # Trine
                drigbala += 0.1
            elif abs(diff - 180) <= 10:  # Opposition
                drigbala -= 0.05
            elif abs(diff - 90) <= 10:  # Square
                drigbala -= 0.05

    # Calculate total Shadbala
    total = sthanabala + digbala + kalabala + chestabala + naisargikabala + drigbala

    return {
        "sthanabala": sthanabala,
        "digbala": digbala,
        "kalabala": kalabala,
        "chestabala": chestabala,
        "naisargikabala": naisargikabala,
        "drigbala": drigbala,
        "total": total
    }

def get_ayanamsha_value(birth_dt: datetime) -> float:
    """
    Get ayanamsha value for a specific date.

    Args:
        birth_dt: Birth datetime

    Returns:
        Ayanamsha value in degrees

    Raises:
        RuntimeError: If Swiss Ephemeris is not available
    """
    if not SWISSEPH_AVAILABLE or swe is None:
        error_msg = "Swiss Ephemeris not available. Cannot calculate ayanamsha."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Set sidereal mode to Lahiri
    swe.set_sid_mode(SIDM_LAHIRI)

    # Convert datetime to Julian day
    jd = swe.julday(
        birth_dt.year,
        birth_dt.month,
        birth_dt.day,
        birth_dt.hour + birth_dt.minute/60.0 + birth_dt.second/3600.0
    )

    # Get ayanamsha value
    ayanamsha = swe.get_ayanamsa(jd)
    return ayanamsha

def verify_vedic_coordinates(chart_data: Dict[str, Any], ayanamsha: float) -> Dict[str, Any]:
    """
    Verify that all coordinates in the chart are properly adjusted for ayanamsha.

    Args:
        chart_data: Chart data dictionary
        ayanamsha: Ayanamsha value in degrees

    Returns:
        Dictionary with verification results and any corrections
    """
    corrections = []
    verified = True

    # Check planets first
    planets = chart_data.get("planets", {})
    for planet_name, planet_data in planets.items():
        tropical_long = planet_data.get("tropical_longitude")
        sidereal_long = planet_data.get("longitude")

        # If we have both tropical and sidereal longitudes, verify the ayanamsha adjustment
        if tropical_long is not None and sidereal_long is not None:
            expected_sidereal = (tropical_long - ayanamsha) % 360

            # Allow a small margin of error (0.01 degrees)
            if abs(expected_sidereal - sidereal_long) > 0.01:
                verified = False
                corrections.append({
                    "type": "planet",
                    "name": planet_name,
                    "original": sidereal_long,
                    "corrected": expected_sidereal,
                    "difference": abs(expected_sidereal - sidereal_long)
                })

    # Check angles (Ascendant, Midheaven, etc.)
    angles = chart_data.get("angles", {})
    for angle_name, angle_data in angles.items():
        tropical_long = angle_data.get("tropical_longitude")
        sidereal_long = angle_data.get("longitude")

        # If we have both tropical and sidereal longitudes, verify the ayanamsha adjustment
        if tropical_long is not None and sidereal_long is not None:
            expected_sidereal = (tropical_long - ayanamsha) % 360

            # Allow a small margin of error (0.01 degrees)
            if abs(expected_sidereal - sidereal_long) > 0.01:
                verified = False
                corrections.append({
                    "type": "angle",
                    "name": angle_name,
                    "original": sidereal_long,
                    "corrected": expected_sidereal,
                    "difference": abs(expected_sidereal - sidereal_long)
                })

    # Check house cusps
    houses = chart_data.get("houses", [])
    for i, house in enumerate(houses):
        tropical_long = house.get("tropical_longitude")
        sidereal_long = house.get("longitude")

        # If we have both tropical and sidereal longitudes, verify the ayanamsha adjustment
        if tropical_long is not None and sidereal_long is not None:
            expected_sidereal = (tropical_long - ayanamsha) % 360

            # Allow a small margin of error (0.01 degrees)
            if abs(expected_sidereal - sidereal_long) > 0.01:
                verified = False
                corrections.append({
                    "type": "house",
                    "number": i + 1,
                    "original": sidereal_long,
                    "corrected": expected_sidereal,
                    "difference": abs(expected_sidereal - sidereal_long)
                })

    return {
        "verified": verified,
        "ayanamsha_value": ayanamsha,
        "corrections": corrections
    }

def calculate_planetary_avasthas(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate planetary avasthas (states) like Bala, Moda, etc.

    Args:
        chart_data: Chart data dictionary

    Returns:
        Dictionary with avasthas for each planet
    """
    avasthas = {}
    planets = chart_data.get("planets", {})

    # Define rulers of each sign
    sign_rulers = {
        "Aries": "Mars",
        "Taurus": "Venus",
        "Gemini": "Mercury",
        "Cancer": "Moon",
        "Leo": "Sun",
        "Virgo": "Mercury",
        "Libra": "Venus",
        "Scorpio": "Mars",
        "Sagittarius": "Jupiter",
        "Capricorn": "Saturn",
        "Aquarius": "Saturn",
        "Pisces": "Jupiter"
    }

    # Define friends and enemies for each planet
    friends = {
        "Sun": ["Moon", "Mars", "Jupiter"],
        "Moon": ["Sun", "Mercury"],
        "Mercury": ["Sun", "Venus"],
        "Venus": ["Mercury", "Saturn"],
        "Mars": ["Sun", "Moon", "Jupiter"],
        "Jupiter": ["Sun", "Moon", "Mars"],
        "Saturn": ["Mercury", "Venus"]
    }

    enemies = {
        "Sun": ["Venus", "Saturn"],
        "Moon": [""],  # Moon has no enemies
        "Mercury": ["Moon"],
        "Venus": ["Sun", "Moon"],
        "Mars": ["Mercury"],
        "Jupiter": ["Mercury", "Venus"],
        "Saturn": ["Sun", "Moon", "Mars"]
    }

    # Check each planet
    for planet_name, planet_data in planets.items():
        sign = planet_data.get("sign", "")
        house = planet_data.get("house", 0)
        longitude = planet_data.get("longitude", 0)
        sign_degree = longitude % 30

        # Calculate Jagradadi Avasthas (waking states)
        jagradadi = "Jagrat"  # Default to waking state
        if sign_degree < 10:
            jagradadi = "Jagrat"  # Awake/waking state
        elif sign_degree < 20:
            jagradadi = "Swapna"  # Dreaming state
        else:
            jagradadi = "Sushupti"  # Deep sleep state

        # Calculate Baladi Avasthas (age states)
        baladi = "Yuva"  # Default to youth state
        if sign_degree < 6:
            baladi = "Bala"  # Infant state
        elif sign_degree < 12:
            baladi = "Kumara"  # Child state
        elif sign_degree < 18:
            baladi = "Yuva"  # Youth state
        elif sign_degree < 24:
            baladi = "Vridha"  # Old state
        else:
            baladi = "Mrita"  # Dead state

        # Calculate Lajjitadi Avasthas (mood states)
        lajjitadi = "Mudita"  # Default to joyful state

        # Check if the planet is in its own sign
        if sign_rulers.get(sign) == planet_name:
            lajjitadi = "Mudita"  # Joyful
        # Check if the planet is in a friendly sign
        elif sign_rulers.get(sign) in friends.get(planet_name, []):
            lajjitadi = "Kshudita"  # Hungry
        # Check if the planet is in an enemy sign
        elif sign_rulers.get(sign) in enemies.get(planet_name, []):
            lajjitadi = "Lajjita"  # Ashamed
        # Check if the planet is in exaltation
        elif (planet_name == "Sun" and sign == "Aries") or \
             (planet_name == "Moon" and sign == "Taurus") or \
             (planet_name == "Mercury" and sign == "Virgo") or \
             (planet_name == "Venus" and sign == "Pisces") or \
             (planet_name == "Mars" and sign == "Capricorn") or \
             (planet_name == "Jupiter" and sign == "Cancer") or \
             (planet_name == "Saturn" and sign == "Libra"):
            lajjitadi = "Mudita"  # Joyful
        # Check if the planet is in debilitation
        elif (planet_name == "Sun" and sign == "Libra") or \
             (planet_name == "Moon" and sign == "Scorpio") or \
             (planet_name == "Mercury" and sign == "Pisces") or \
             (planet_name == "Venus" and sign == "Virgo") or \
             (planet_name == "Mars" and sign == "Cancer") or \
             (planet_name == "Jupiter" and sign == "Capricorn") or \
             (planet_name == "Saturn" and sign == "Aries"):
            lajjitadi = "Lajjita"  # Ashamed

        # Store the avasthas for this planet
        avasthas[planet_name] = {
            "jagradadi": jagradadi,
            "baladi": baladi,
            "lajjitadi": lajjitadi
        }

    return avasthas

def calculate_dasa_periods(birth_dt: datetime, moon_longitude: float, ayanamsha: float) -> Dict[str, Any]:
    """
    Calculate Vimshottari dasha periods starting from birth.

    Args:
        birth_dt: Birth datetime
        moon_longitude: Longitude of the Moon
        ayanamsha: Ayanamsha value

    Returns:
        Dictionary with dasha and bhukti periods
    """
    # Get the nakshatra of the Moon
    moon_nakshatra = get_nakshatra_from_longitude(moon_longitude)

    return {
        "system": "vimshottari",
        "start_date": birth_dt.isoformat(),
        "current_mahadasha": {
            "planet": moon_nakshatra["lord"],
            "start": birth_dt.isoformat(),
            "end": "Calculated based on dasha years"
        },
        "dashas": [
            {
                "planet": moon_nakshatra["lord"],
                "start": birth_dt.isoformat(),
                "duration_years": "Depends on planet"
            }
        ]
    }
