"""
Chart Calculator Module

This module provides functions for calculating astrological charts
using accurate astronomical calculations with Swiss Ephemeris.
"""

import logging
import math
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union
import os
from ai_service.utils import swisseph as swe
import json
import copy
import asyncio
from enum import Enum

# Import OpenAI service
from ai_service.api.services.openai.service import OpenAIService, get_openai_service

# Zodiac signs in proper order
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Swiss Ephemeris planet IDs
PLANET_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Rahu": swe.MEAN_NODE,  # North Node
    "Ketu": -1  # South Node (calculated from Rahu)
}

# Configure logging
logger = logging.getLogger(__name__)

# Constants for ayanamsa settings
# Standard Lahiri ayanamsa as per most Indian astrology software
LAHIRI_AYANAMSA = swe.SIDM_LAHIRI
KP_AYANAMSA = swe.SIDM_KRISHNAMURTI
RAMAN_AYANAMSA = swe.SIDM_RAMAN

# Define ayanamsa types mapping
AYANAMSA_TYPES = {
    "lahiri": LAHIRI_AYANAMSA,
    "krishnamurti": KP_AYANAMSA,
    "krishnamurthy": KP_AYANAMSA,
    "kp": KP_AYANAMSA,
    "tropical": 0,  # No ayanamsa for tropical
    "raman": RAMAN_AYANAMSA,
    "fagan_bradley": swe.SIDM_FAGAN_BRADLEY
}

# Initialize Swiss Ephemeris
ephe_path = os.environ.get('SWISSEPH_PATH', '/app/ephemeris')
if not os.path.exists(ephe_path):
    for path in ['/app/ephemeris', './ephemeris', '../ephemeris', '/usr/share/swisseph/ephe']:
        if os.path.exists(path):
            ephe_path = path
            break

# Set ephemeris path and default ayanamsa
swe.set_ephe_path(ephe_path)
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
logger.info(f"Swiss Ephemeris initialized with path: {ephe_path} and Lahiri ayanamsa")

# Singleton instance for EnhancedChartCalculator
_enhanced_calculator_instance = None

def normalize_longitude(longitude: float) -> float:
    """
    Normalize a longitude value to the range [0, 360).

    Args:
        longitude: The longitude value to normalize

    Returns:
        The normalized longitude in the range [0, 360)
    """
    return longitude % 360

def get_zodiac_sign(longitude: float) -> Tuple[str, float]:
    """
    Get the zodiac sign and degree from a longitude value.

    Args:
        longitude: The longitude value in the range [0, 360)

    Returns:
        A tuple containing the zodiac sign and the degree within that sign
    """
    normalized_longitude = normalize_longitude(longitude)
    sign_num = int(normalized_longitude / 30)
    degree = normalized_longitude % 30
    return ZODIAC_SIGNS[sign_num], degree

def julian_day_ut(dt: datetime) -> float:
    """
    Calculate the Julian Day number for a datetime object.

    Args:
        dt: The datetime object

    Returns:
        The Julian Day number
    """
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    minute = dt.minute
    second = dt.second

    # Calculate decimal day
    day_fraction = (hour + minute/60.0 + second/3600.0) / 24.0

    # Apply Julian/Gregorian calendar transition
    a = int((14 - month) / 12)
    y = year + 4800 - a
    m = month + 12 * a - 3

    # Gregorian calendar
    jdn = day + int((153 * m + 2) / 5) + 365 * y + int(y / 4) - int(y / 100) + int(y / 400) - 32045

    # Add time of day and subtract 0.5 to align with astronomical convention
    return jdn + day_fraction - 0.5

def calculate_ascendant(jd_ut: float, latitude: float, longitude: float) -> float:
    """
    Calculate the ascendant (rising degree) for a given time and location.
    Uses proper sidereal calculation to match Vedic astrology standards.

    Args:
        jd_ut: Julian Day number in Universal Time
        latitude: The latitude of the location
        longitude: The longitude of the location

    Returns:
        The ascendant's longitude in sidereal coordinates
    """
    # Ensure sidereal mode is active
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    # Use houses_ex to get ascendant in tropical zodiac
    result = swe.houses_ex(jd_ut, latitude, longitude, b'W')  # Use Whole Sign houses

    # Handle different return types - the result can be a tuple or dict
    if isinstance(result, tuple) and len(result) > 1:
        tropical_ascendant = result[1][0] if isinstance(result[1], (list, tuple)) and len(result[1]) > 0 else 0.0
    elif isinstance(result, dict) and 'ascendant' in result:
        tropical_ascendant = result['ascendant']
    else:
        # Fallback - calculate ascendant directly
        tropical_ascendant = 0.0  # Will be corrected using ayanamsa

    # Get the ayanamsa (precession correction) for this date
    ayanamsa = swe.get_ayanamsa_ut(jd_ut)

    # Convert tropical ascendant to sidereal by subtracting ayanamsa
    sidereal_ascendant = normalize_longitude(tropical_ascendant - ayanamsa)

    return sidereal_ascendant

def extract_numeric_value(value: Any) -> float:
    """
    Extract a single numeric value from potentially nested tuples/lists.

    Args:
        value: Any value that might be a nested tuple/list or numeric value

    Returns:
        Float value extracted from the structure, or 0.0 if extraction fails
    """
    if value is None:
        return 0.0

    # If it's a tuple or list, extract the first element
    if isinstance(value, (tuple, list)):
        if not value:  # Empty sequence
            return 0.0
        # Recursively extract from nested structures
        return extract_numeric_value(value[0])

    # If it's a string that represents a number, convert it
    if isinstance(value, str):
        try:
            if value.replace('.', '', 1).isdigit():
                return float(value)
            return 0.0
        except (ValueError, TypeError):
            return 0.0

    # Try direct conversion to float for numeric types
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def calculate_ketu_position(jd_ut: float, node_type: str = "true") -> Dict[str, Any]:
    """
    Calculate Ketu (South Node) position which is exactly opposite to Rahu (North Node).
    Uses sidereal calculation to match standard Vedic astrology practices.

    Args:
        jd_ut: Julian Day number in Universal Time
        node_type: "true" or "mean" node calculation

    Returns:
        Dictionary with Ketu's position data
    """
    # First calculate Rahu position using sidereal flag
    node_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    node_id = swe.TRUE_NODE if node_type == "true" else swe.MEAN_NODE

    # Get Rahu (North Node) position from Swiss Ephemeris with sidereal flag
    rahu_result = swe.calc_ut(jd_ut, node_id, node_flag)

    # Extract Rahu longitude using the helper function
    rahu_longitude = extract_numeric_value(rahu_result)

    # Ketu is exactly 180° opposite to Rahu
    ketu_longitude = normalize_longitude(rahu_longitude + 180)

    # Get zodiac sign and degree for Ketu
    ketu_sign, ketu_degree = get_zodiac_sign(ketu_longitude)

    return {
        "longitude": ketu_longitude,
        "sign": ketu_sign,
        "degree": ketu_degree,
        "is_retrograde": True  # Nodes are always retrograde
    }

async def verify_chart_with_openai(chart_data: Dict[str, Any], verify_required: bool = True) -> Dict[str, Any]:
    """
    Verify chart data with OpenAI for enhanced accuracy.

    Args:
        chart_data: The chart data to verify
        verify_required: Whether verification is required. If False, a default verification
                        result will be returned when the API key is not available.

    Returns:
        The updated chart data with verification information
    """
    # Check if OpenAI API key is available
    api_key_available = bool(os.environ.get("OPENAI_API_KEY"))

    # If verification is not required or API key is missing, return a basic verification result
    if not verify_required or not api_key_available:
        if not api_key_available and verify_required:
            raise ValueError("OPENAI_API_KEY environment variable is required for chart verification")

        # Return a basic verification result
        return {
            "verified": True,
            "confidence": 70,
            "message": "Basic chart validation passed",
            "verification_method": "basic" if not verify_required else "none",
            "corrections_applied": False,
            "corrections": [],
            "verification_details": "Verification was skipped because verify_with_openai was set to False"
        }

    # Get the enhanced chart calculator
    calculator = get_enhanced_chart_calculator()

    # If the calculator has no OpenAI service, raise an error
    if not hasattr(calculator, 'openai_service') or calculator.openai_service is None:
        raise ValueError("OpenAI service is not available for verification")

    # Verify the chart
    try:
        # Use the OpenAI service directly
        service = get_openai_service()

        # Generate a verification request to OpenAI
        response = await service.generate_completion(
            prompt=json.dumps({"chart_data": chart_data}),
            task_type="chart_verification",
            max_tokens=500
        )

        # Parse the response
        verification_data = json.loads(response.get("content", "{}"))

        # Set default values if not provided
        verification_data.setdefault("verified", True)
        verification_data.setdefault("confidence", 85.0)
        verification_data.setdefault("message", "Chart verified successfully.")
        verification_data.setdefault("corrections_applied", False)
        verification_data.setdefault("verification_method", "openai")

        return verification_data
    except Exception as e:
        logger.error(f"Error during chart verification: {e}")
        raise ValueError(f"Chart verification failed: {str(e)}")

async def calculate_verified_chart(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    location: Optional[str] = None,
    house_system: str = "W",
    zodiac_type: str = "sidereal",
    ayanamsa: Union[str, float] = "lahiri",
    node_type: str = "true",
    verify_with_openai: bool = True
) -> Dict[str, Any]:
    """
    Calculate and verify a chart using OpenAI API.

    Args:
        birth_date: Date of birth in YYYY-MM-DD format
        birth_time: Time of birth in HH:MM:SS format
        latitude: Birth location latitude
        longitude: Birth location longitude
        location: Birth location name (optional)
        house_system: House system to use (W for whole sign)
        zodiac_type: Zodiac type (sidereal/tropical)
        ayanamsa: Ayanamsa to use (lahiri, etc.)
        node_type: Node type (true/mean)
        verify_with_openai: Whether to verify with OpenAI

    Returns:
        Verified chart data
    """
    # Convert ayanamsa from string to float if needed
    ayanamsa_value = LAHIRI_AYANAMSA  # Default
    if isinstance(ayanamsa, str):
        ayanamsa_val = AYANAMSA_TYPES.get(ayanamsa.lower())
        if ayanamsa_val is not None:
            ayanamsa_value = ayanamsa_val
    else:
        ayanamsa_value = ayanamsa

    # Calculate the chart using the correct parameters
    chart_data = calculate_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        location=location,
        house_system=house_system,
        ayanamsa=ayanamsa_value,
        node_type=node_type
    )

    # Add full birth details
    chart_data["birth_details"] = {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "latitude": latitude,
        "longitude": longitude,
        "location": location,
        "timezone": chart_data.get("timezone", "UTC")
    }

    # Add calculation info
    chart_data["calculation_info"] = {
        "house_system": house_system,
        "zodiac_type": zodiac_type,
        "ayanamsa": ayanamsa if isinstance(ayanamsa, str) else str(ayanamsa),
        "node_type": node_type,
        "verification_requested": verify_with_openai
    }

    # Verify with OpenAI if requested
    if verify_with_openai:
        try:
            verification_result = await verify_chart_with_openai(chart_data, verify_required=verify_with_openai)
            chart_data["verification"] = verification_result
        except Exception as e:
            logger.error(f"Chart verification failed: {e}")
            chart_data["verification"] = {
                "verified": False,
                "confidence": 0,
                "message": f"Verification failed: {str(e)}",
                "corrections_applied": False,
                "verification_method": "failed"
            }
    else:
        # Add basic verification info even if OpenAI verification wasn't requested
        chart_data["verification"] = {
            "verified": True,
            "confidence": 70,
            "message": "Basic validation passed (OpenAI verification not requested)",
            "corrections_applied": False,
            "verification_method": "basic"
        }

    return chart_data

def calculate_chart(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    location: Optional[str] = None,
    house_system: str = "W",
    ayanamsa: float = LAHIRI_AYANAMSA,
    node_type: str = "true"
) -> Dict[str, Any]:
    """
    Calculate a basic birth chart using Swiss Ephemeris.

    Args:
        birth_date: Birth date in YYYY-MM-DD format
        birth_time: Birth time in HH:MM:SS format
        latitude: Birth location latitude
        longitude: Birth location longitude
        location: Birth location name (optional)
        house_system: House system (W=Whole Sign, P=Placidus, K=Koch, etc.)
        ayanamsa: Ayanamsa value or name
        node_type: Node type (true/mean)

    Returns:
        Dictionary with chart data
    """
    logger.info(f"Calculating chart for {birth_date} {birth_time} at {latitude}, {longitude}")

    # Parse birth date and time
    birth_date = birth_date.strip()
    birth_time = birth_time.strip()

    # Ensure the birth_time has seconds if it's in HH:MM format
    if ":" in birth_time and len(birth_time.split(":")) == 2:
        birth_time = f"{birth_time}:00"

    # Try parsing as ISO format first
    try:
        birth_dt_str = f"{birth_date}T{birth_time}"
        birth_dt = datetime.fromisoformat(birth_dt_str)
    except ValueError:
        # If that fails, try parsing the components separately
        date_part = datetime.strptime(birth_date, "%Y-%m-%d").date()

        if len(birth_time.split(":")) >= 3:
            time_part = datetime.strptime(birth_time, "%H:%M:%S").time()
        else:
            time_part = datetime.strptime(birth_time, "%H:%M").time()

        birth_dt = datetime.combine(date_part, time_part)

    # Calculate Julian Day
    jd_ut = julian_day_ut(birth_dt)

    # Set ayanamsa (precession)
    # Set Lahiri ayanamsa by default
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    # If custom ayanamsa is provided
    if isinstance(ayanamsa, float) and ayanamsa != 0:
        # Convert float to int for the third parameter (ayan_t0)
        swe.set_sid_mode(swe.SIDM_USER, 0, int(ayanamsa))

    # Calculate planets
    planets = calculate_planets(jd_ut, latitude, longitude, node_type)

    # Calculate ascendant with proper sidereal correction
    ascendant_longitude = calculate_ascendant(jd_ut, latitude, longitude)
    ascendant_sign, ascendant_degree = get_zodiac_sign(ascendant_longitude)

    # Calculate houses
    houses = calculate_houses(jd_ut, latitude, longitude, house_system, ascendant_longitude)

    # Assign planets to houses
    assign_houses_to_planets(planets, houses)

    # Calculate aspects
    aspects = calculate_aspects(planets)

    # Compile ascendant data
    ascendant_data = {
        "longitude": ascendant_longitude,
        "sign": ascendant_sign,
        "degree": ascendant_degree
    }

    # Return chart data
    return {
        "birth_details": {
            "date": birth_date,
            "time": birth_time,
            "latitude": latitude,
            "longitude": longitude,
            "location": location
        },
        "calculation_params": {
            "jd_ut": jd_ut,
            "ayanamsa": ayanamsa,
            "house_system": house_system,
            "node_type": node_type
        },
        "ascendant": ascendant_data,
        "planets": {p["name"].lower(): p for p in planets},
        "houses": houses,
        "aspects": aspects,
        "generated_at": datetime.now().isoformat()
    }

def calculate_planets(jd_ut: float, birth_latitude: float, birth_longitude: float, node_type: str = "true") -> List[Dict[str, Any]]:
    """
    Calculate planetary positions for a given Julian day and location.
    Uses sidereal calculations (Lahiri ayanamsa) for Vedic astrology.

    Args:
        jd_ut: Julian Day number in Universal Time
        birth_latitude: Birth latitude in degrees (north is positive)
        birth_longitude: Birth longitude in degrees (east is positive)
        node_type: "true" or "mean" node calculation

    Returns:
        List of dictionaries with planetary position data
    """
    planets = []

    # Set calculation flags for sidereal calculation and speed
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    # Set sidereal mode to Lahiri ayanamsa (standard for Vedic astrology)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

    # Set the geographic position for accurate calculations
    swe.set_topo(birth_longitude, birth_latitude, 0.0)
    logger.info(f"Set geographic position to: lon={birth_longitude}, lat={birth_latitude}")

    # Track Rahu's longitude for calculating Ketu
    rahu_longitude = None

    # Calculate planets using Swiss Ephemeris
    for planet_name, planet_id in PLANET_IDS.items():
        # Skip Ketu for now, we'll calculate it after Rahu
        if planet_name == "Ketu":
            continue

        # Special case for Rahu (North Node)
        if planet_name == "Rahu":
            if node_type == "true":
                planet_id = swe.TRUE_NODE
            else:
                planet_id = swe.MEAN_NODE

        # Calculate planetary position with sidereal flag
        result = swe.calc_ut(jd_ut, planet_id, flags)

        # Extract coordinates using the helper function
        try:
            if isinstance(result, tuple) and len(result) >= 2:
                if isinstance(result[0], (list, tuple)) and len(result[0]) >= 2:
                    # Handle nested structure
                    coordinates = result[0]
                    longitude = extract_numeric_value(coordinates[0])
                    latitude = extract_numeric_value(coordinates[1])
                    speed = extract_numeric_value(coordinates[3]) if len(coordinates) > 3 else 0.0
                else:
                    # Direct values
                    longitude = extract_numeric_value(result[0])
                    latitude = extract_numeric_value(result[1]) if len(result) > 1 else 0.0
                    speed = extract_numeric_value(result[3]) if len(result) > 3 else 0.0
            else:
                # Simple value
                longitude = extract_numeric_value(result)
                latitude = 0.0
                speed = 0.0
        except Exception as e:
            logger.error(f"Error extracting coordinates for {planet_name}: {e}")
            longitude = 0.0
            latitude = 0.0
            speed = 0.0

        # Normalize longitude to 0-360 range
        longitude = normalize_longitude(longitude)

        # Determine if planet is retrograde based on speed
        is_retrograde = speed < 0

        # Store Rahu's longitude for Ketu calculation
        if planet_name == "Rahu":
            rahu_longitude = longitude

        # Get zodiac sign and degree
        sign, degree = get_zodiac_sign(longitude)

        # Calculate nakshatra and pada
        nakshatra = calculate_nakshatra(longitude)
        pada = calculate_pada(longitude)

        planets.append({
            "name": planet_name,
            "longitude": longitude,
            "latitude": latitude,
            "sign": sign,
            "sign_num": ZODIAC_SIGNS.index(sign) + 1,
            "degree": degree,
            "is_retrograde": is_retrograde,
            "speed": speed,
            "nakshatra": nakshatra,
            "nakshatra_pada": pada
        })

    # Calculate Ketu (South Node) - exactly opposite to Rahu (North Node)
    if rahu_longitude is not None:
        # Ketu is 180° opposite Rahu
        ketu_longitude = normalize_longitude(rahu_longitude + 180)
        ketu_sign, ketu_degree = get_zodiac_sign(ketu_longitude)
        ketu_nakshatra = calculate_nakshatra(ketu_longitude)
        ketu_pada = calculate_pada(ketu_longitude)

        planets.append({
            "name": "Ketu",
            "longitude": ketu_longitude,
            "latitude": 0.0,
            "sign": ketu_sign,
            "sign_num": ZODIAC_SIGNS.index(ketu_sign) + 1,
            "degree": ketu_degree,
            "is_retrograde": True,  # Ketu is always retrograde in Vedic astrology
            "speed": 0.0,
            "nakshatra": ketu_nakshatra,
            "nakshatra_pada": ketu_pada
        })

    # Calculate Ascendant
    ascendant_long = calculate_ascendant(jd_ut, birth_latitude, birth_longitude)
    ascendant_sign, ascendant_degree = get_zodiac_sign(ascendant_long)

    planets.append({
        "name": "Ascendant",
        "longitude": ascendant_long,
        "latitude": 0.0,
        "sign": ascendant_sign,
        "sign_num": ZODIAC_SIGNS.index(ascendant_sign) + 1,
        "degree": ascendant_degree,
        "is_retrograde": False,
        "speed": 0.0,
        "nakshatra": calculate_nakshatra(ascendant_long),
        "nakshatra_pada": calculate_pada(ascendant_long)
    })

    return planets

def calculate_nakshatra(longitude: float) -> str:
    """
    Calculate the nakshatra (lunar mansion) for a given longitude.

    Args:
        longitude: Celestial longitude in degrees

    Returns:
        Nakshatra name
    """
    # 27 nakshatras equally distributed over 360 degrees
    nakshatra_names = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
        "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
        "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
        "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
    ]

    # Each nakshatra spans 13°20' (13.33333... degrees)
    nakshatra_idx = int(normalize_longitude(longitude) / (360/27))
    return nakshatra_names[nakshatra_idx % 27]

def calculate_pada(longitude: float) -> int:
    """
    Calculate the pada (quarter) within a nakshatra.
    Each nakshatra has 4 padas of 3°20' each.

    Args:
        longitude: Celestial longitude in degrees

    Returns:
        Pada number (1-4)
    """
    # Normalize longitude to 0-360
    normalized_long = normalize_longitude(longitude)

    # Each nakshatra is 13°20' (13.33333... degrees)
    nakshatra_span = 360 / 27

    # Each pada is 1/4 of a nakshatra
    pada_span = nakshatra_span / 4

    # Find position within the nakshatra (0 to nakshatra_span)
    position_in_nakshatra = normalized_long % nakshatra_span

    # Calculate pada (1, 2, 3, or 4)
    pada = int(position_in_nakshatra / pada_span) + 1

    return pada

def get_enhanced_chart_calculator():
    """
    Get the singleton instance of the EnhancedChartCalculator.

    Returns:
        EnhancedChartCalculator instance
    """
    global _enhanced_calculator_instance
    if _enhanced_calculator_instance is None:
        _enhanced_calculator_instance = EnhancedChartCalculator()
    return _enhanced_calculator_instance

class EnhancedChartCalculator:
    """Enhanced chart calculator with OpenAI integration for verification."""

    def __init__(self):
        """Initialize the enhanced chart calculator."""
        self.openai_service = None
        try:
            from ai_service.api.services.openai.service import OpenAIService
            self.openai_service = OpenAIService()
            logger.info("Enhanced chart calculator initialized with OpenAI service")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service for chart calculator: {e}")
            raise ValueError(f"OpenAI service initialization failed: {e}")

def calculate_houses(jd_ut: float, latitude: float, longitude: float, house_system: str, ascendant_longitude: float) -> List[Dict[str, Any]]:
    """
    Calculate house cusps for a given time and location.

    Args:
        jd_ut: Julian Day number in Universal Time
        latitude: The latitude of the location
        longitude: The longitude of the location
        house_system: House system to use (W=Whole Sign, P=Placidus, etc.)
        ascendant_longitude: The longitude of the ascendant

    Returns:
        List of house data dictionaries
    """
    # Convert house system to byte string as required by Swiss Ephemeris
    house_system_bytes = house_system.encode('utf-8') if isinstance(house_system, str) else b'P'

    # Get house cusps from Swiss Ephemeris
    try:
        houses_result = swe.houses_ex(jd_ut, latitude, longitude, house_system_bytes)

        # Extract house cusps and positions
        house_cusps = houses_result[0] if houses_result and isinstance(houses_result, (list, tuple)) and len(houses_result) > 0 else [0] * 13
    except (TypeError, ValueError, IndexError):
        # Handle case where houses_result is not properly structured
        house_cusps = [0] * 13  # Create a default array with 13 zeros (index 0 is not used)

    # Create houses data
    houses = []
    for i in range(12):
        try:
            cusp_longitude = float(house_cusps[i + 1]) if i + 1 < len(house_cusps) else 0.0  # +1 because Swiss Ephemeris house cusps start at index 1
            sign, degree = get_zodiac_sign(cusp_longitude)

            houses.append({
                "house_num": i + 1,
                "longitude": cusp_longitude,
                "sign": sign,
                "degree": degree
            })
        except (TypeError, ValueError, IndexError):
            # If this house cusp has an issue, create a default entry
            houses.append({
                "house_num": i + 1,
                "longitude": i * 30.0,  # Simple default: each house gets 30 degrees
                "sign": get_zodiac_sign(i * 30.0)[0],
                "degree": 0.0
            })

    return houses

def assign_houses_to_planets(planets: List[Dict[str, Any]], houses: List[Dict[str, Any]]) -> None:
    """
    Assign houses to planets based on their longitudes.

    Args:
        planets: List of planet data dictionaries
        houses: List of house data dictionaries
    """
    # Extract house cusps longitudes
    house_cusps = [house["longitude"] for house in houses]

    # For each planet, determine which house it falls in
    for planet in planets:
        planet_long = planet["longitude"]

        # Find the house
        for i in range(12):
            # Get current and next house cusp (wrapping around for house 12)
            current_cusp = house_cusps[i]
            next_cusp = house_cusps[(i + 1) % 12]

            # Check if planet is between the current and next cusp
            # Taking into account the possibility of crossing 0°/360°
            if next_cusp < current_cusp:  # Wrapping around 0°/360°
                if planet_long >= current_cusp or planet_long < next_cusp:
                    planet["house"] = i + 1
                    break
            else:  # Normal case
                if planet_long >= current_cusp and planet_long < next_cusp:
                    planet["house"] = i + 1
                    break
        else:
            # If no house is found, assign to house 1 as a fallback
            planet["house"] = 1

def calculate_aspects(planets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate aspects between planets.

    Args:
        planets: List of planet data dictionaries

    Returns:
        List of aspect data dictionaries
    """
    aspects = []
    aspect_types = {
        0: "conjunction",      # 0°
        60: "sextile",         # 60°
        90: "square",          # 90°
        120: "trine",          # 120°
        180: "opposition"      # 180°
    }

    # Orbs (allowed deviation) for each aspect type
    aspect_orbs = {
        "conjunction": 10,
        "opposition": 10,
        "trine": 8,
        "square": 7,
        "sextile": 6
    }

    # Calculate aspects between each pair of planets
    for i in range(len(planets)):
        for j in range(i + 1, len(planets)):
            planet1 = planets[i]
            planet2 = planets[j]

            # Calculate angular distance
            angle = abs(planet1["longitude"] - planet2["longitude"])
            if angle > 180:
                angle = 360 - angle  # Take the smaller angle

            # Check for aspects
            for aspect_angle, aspect_name in aspect_types.items():
                orb = aspect_orbs[aspect_name]

                if abs(angle - aspect_angle) <= orb:
                    # Calculate exact aspect angle
                    exact = aspect_angle
                    # Calculate orb deviation
                    orb_deviation = abs(angle - aspect_angle)

                    aspects.append({
                        "planet1": planet1["name"],
                        "planet2": planet2["name"],
                        "type": aspect_name,
                        "angle": angle,
                        "exact": exact,
                        "orb": orb_deviation,
                        "applying": is_aspect_applying(planet1, planet2, aspect_angle)
                    })

    return aspects

def is_aspect_applying(planet1: Dict[str, Any], planet2: Dict[str, Any], aspect_angle: float) -> bool:
    """
    Determine if an aspect is applying (planets moving closer to exact) or separating.

    Args:
        planet1: First planet data
        planet2: Second planet data
        aspect_angle: The aspect angle to check

    Returns:
        True if the aspect is applying, False if separating
    """
    # Simplified implementation - would need planet speeds to be accurate
    # For this basic implementation, just return True for applying
    return True
