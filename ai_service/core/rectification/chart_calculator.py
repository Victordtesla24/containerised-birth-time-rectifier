"""
Chart calculation module for astrological rectification.
"""
from datetime import datetime
import logging
import os
from typing import Any, Optional, Dict, Union, List
import traceback
import uuid
import json
import asyncio
import math
from contextlib import contextmanager
import time
import re

# Proper timezone handling - no fallbacks
import pytz
from pytz.exceptions import UnknownTimeZoneError
from timezonefinder import TimezoneFinder

# Import astrological calculation libraries
try:
    import swisseph as swe
    SWISSEPH_AVAILABLE = True
except ImportError:
    SWISSEPH_AVAILABLE = False
    logging.error("Swiss Ephemeris (swisseph) not available. This is REQUIRED for accurate calculations.")
    raise ImportError("Swiss Ephemeris (swisseph) is required for astrological calculations")

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
from ai_service.core.exceptions import EphemerisError

logger = logging.getLogger(__name__)

# Set up Swiss Ephemeris path
if SWISSEPH_AVAILABLE:
    # Set the ephemeris path from environment variable or use default
    EPHEMERIS_PATH = os.environ.get('SWISSEPH_PATH', os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'ephemeris'))
    if not os.path.exists(EPHEMERIS_PATH):
        logger.warning(f"Swiss Ephemeris path not found: {EPHEMERIS_PATH}")
        # Try to use flatlib path as fallback
        EPHEMERIS_PATH = os.environ.get('FLATLIB_EPHE_PATH', '/usr/share/swisseph')

    # Initialize Swiss Ephemeris
    swe.set_ephe_path(EPHEMERIS_PATH)
    logger.info(f"Swiss Ephemeris initialized with path: {EPHEMERIS_PATH}")

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
        ValueError: If calculation fails
    """
    if not SWISSEPH_AVAILABLE:
        raise ValueError("Swiss Ephemeris not available for outer planet calculation")

    try:
        # Calculate planet positions with high precision
        result, status = swe.calc_ut(jd, planet_id, swe.FLG_SWIEPH | swe.FLG_SPEED)

        # Extract coordinates
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

def calculate_chart(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone_str: str,
    house_system: str = 'P'  # Default to Placidus house system
) -> Dict[str, Any]:
    """
    Calculate astrological chart using flatlib with Swiss Ephemeris for accuracy.
    This is a synchronous function that returns the chart data.

    Args:
        birth_dt: Birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone_str: Birth location timezone string
        house_system: House system to use ('P' for Placidus, 'K' for Koch, etc.)

    Returns:
        Dictionary containing chart data

    Raises:
        EphemerisError: If ephemeris files are missing or corrupted
        ValueError: If chart calculation fails
    """
    try:
        # Generate chart ID
        chart_id = f"chart_{uuid.uuid4().hex[:10]}"

        # Validate timezone string by creating a timezone object
        try:
            timezone = pytz.timezone(timezone_str)
            utc_offset = timezone.utcoffset(birth_dt)
            utc_offset_hours = utc_offset.total_seconds() / 3600
        except (UnknownTimeZoneError, AttributeError) as e:
            logger.warning(f"Invalid timezone '{timezone_str}': {e}. Attempting to determine timezone from coordinates.")
            try:
                # Try to determine timezone from coordinates
                timezone_str = get_timezone_from_coordinates(latitude, longitude)
                timezone = pytz.timezone(timezone_str)
                utc_offset = timezone.utcoffset(birth_dt)
                utc_offset_hours = utc_offset.total_seconds() / 3600
                logger.info(f"Determined timezone: {timezone_str}")
            except Exception as tz_error:
                logger.error(f"Failed to determine timezone from coordinates: {tz_error}")
                raise ValueError(f"Invalid timezone and could not determine from coordinates: {str(e)}")

        # Format date and time for flatlib
        dt_str = birth_dt.strftime('%Y/%m/%d')
        time_str = birth_dt.strftime('%H:%M')

        # Format offset as required by flatlib
        sign = '+' if utc_offset_hours >= 0 else '-'
        hours = abs(int(utc_offset_hours))
        minutes = abs(int((utc_offset_hours - int(utc_offset_hours)) * 60))
        offset_str = f"{sign}{hours:02d}:{minutes:02d}"

        # Create flatlib datetime
        flat_datetime = Datetime(dt_str, time_str, offset_str)

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
            lat_dir = "N" if latitude >= 0 else "S"

            lon_deg = int(lon_abs)
            lon_min = int((lon_abs - lon_deg) * 60)
            lon_dir = "E" if longitude >= 0 else "W"

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
            "chart_id": chart_id,
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

        # Get Julian Day for Swiss Ephemeris calculations
        # This ensures consistent calculations between flatlib and Swiss Ephemeris
        jd = swe.julday(
            birth_dt.year,
            birth_dt.month,
            birth_dt.day,
            birth_dt.hour + birth_dt.minute/60 + birth_dt.second/3600
        )

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

        # Add outer planets which need Swiss Ephemeris
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
                planet = flat_chart.getObject(planet_name)

                # Determine house for this planet
                house = _determine_house(chart_data["houses"], float(planet.lon))

                # Check if we have a valid planet object
                if planet:
                    # Extract planet data
                    chart_data["planets"][output_name] = {
                        "name": output_name,
                        "longitude": float(planet.lon),
                        "latitude": float(planet.lat),
                        "speed": float(planet.speed),
                        "sign": planet.sign,
                        "house": house,
                        "retrograde": planet.speed < 0
                    }
            except Exception as e:
                logger.error(f"Error extracting planet {planet_name}: {e}")
                # Try Swiss Ephemeris as fallback
                try:
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
                except Exception as e2:
                    logger.error(f"Failed to calculate {output_name} with Swiss Ephemeris: {e2}")
                    # Continue with other planets

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
                # Don't create placeholder data, treat this as a critical error
                # If Swiss Ephemeris fails, we shouldn't proceed with inaccurate data
                raise ValueError(f"Failed to calculate position for {planet_name}. Accurate ephemeris data is required for chart calculation.")

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
    using OpenAI if requested, with robust error handling and fallbacks.

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
        # Parse birth date and time
        try:
            birth_dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Try alternative formats
            try:
                birth_dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                raise ValueError(f"Invalid birth date/time format: {birth_date} {birth_time}")

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

    except Exception as e:
        logger.error(f"Error calculating verified chart: {e}")
        logger.error(traceback.format_exc())

        # Return error information in consistent format
        return {
            "error": str(e),
            "chart_id": f"error_{uuid.uuid4().hex[:8]}",
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "input_params": {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone
            }
        }

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

        # Verify overall chart integrity - no fallbacks or placeholders allowed
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

            # Extract corrections with regex as a fallback
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

            elif correction_type == "house_cusp" and chart_data.get("houses"):
                try:
                    house_num = int(object_name)
                    if 1 <= house_num <= len(chart_data["houses"]):
                        chart_data["houses"][house_num - 1] = float(corrected_value)
                except (ValueError, IndexError):
                    logger.warning(f"Invalid house correction: {correction}")

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
    """
    Enhanced chart calculator that provides more detailed chart data.
    """

    def __init__(self, use_openai: bool = False):
        """Initialize the enhanced chart calculator."""
        self.use_openai = use_openai
        logger.info("Enhanced chart calculator initialized")

    async def calculate_chart(self, birth_details: dict, options: Optional[dict] = None) -> dict:
        """
        Calculate chart from birth details.

        Args:
            birth_details: Dictionary with birth details
            options: Optional calculation options

        Returns:
            Dictionary with chart data
        """
        if not options:
            options = {}

        # Debug log the inputs
        logger.debug(f"Calculating chart with birth_details: {birth_details}")

        # Extract birth details with better validation
        birth_date = birth_details.get("birth_date", "")
        if not birth_date:
            birth_date = birth_details.get("date", "")  # Try alternate key

        birth_time = birth_details.get("birth_time", "")
        if not birth_time:
            birth_time = birth_details.get("time", "")  # Try alternate key

        # Extract and validate latitude (ensure it's a float)
        try:
            latitude = float(birth_details.get("latitude", 0.0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid latitude value: {birth_details.get('latitude')}. Using default 0.0")
            latitude = 0.0

        # Extract and validate longitude (ensure it's a float)
        try:
            longitude = float(birth_details.get("longitude", 0.0))
        except (ValueError, TypeError):
            logger.warning(f"Invalid longitude value: {birth_details.get('longitude')}. Using default 0.0")
            longitude = 0.0

        timezone = birth_details.get("timezone", "UTC")
        location = birth_details.get("location", "")

        # Get calculation options
        house_system = options.get("house_system", "P")
        zodiac_type = options.get("zodiac_type", "tropical")
        ayanamsa = options.get("ayanamsa", "lahiri")
        node_type = options.get("node_type", "true")
        verify_with_openai = options.get("verify_with_openai", False) and self.use_openai

        # Calculate chart with all needed validation
        chart_data = await calculate_verified_chart(
            birth_date=birth_date,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            location=location,
            house_system=house_system,
            zodiac_type=zodiac_type,
            ayanamsa=ayanamsa,
            node_type=node_type,
            verify_with_openai=verify_with_openai
        )

        return chart_data

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
