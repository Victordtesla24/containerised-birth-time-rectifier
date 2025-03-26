"""
Ephemeris utility functions for astrological calculations.

This module provides functions for calculating planetary positions, house cusps,
angles, and other astrological elements using the Swiss Ephemeris library.
"""

import logging
import math
import os
from typing import Tuple, List, Dict, Any, Optional
from datetime import datetime, timezone

import swisseph as swe

logger = logging.getLogger(__name__)

# Set ephemeris path from environment variable or use a default
EPHEMERIS_PATH = os.environ.get("SWISSEPH_PATH", "/app/ephemeris")
try:
    swe.set_ephe_path(EPHEMERIS_PATH)
    logger.info(f"Swiss Ephemeris path set to: {EPHEMERIS_PATH}")
except Exception as e:
    logger.error(f"Error setting Swiss Ephemeris path: {e}")

# Constants for house systems
HOUSE_SYSTEMS = {
    "P": b'P',  # Placidus (default)
    "K": b'K',  # Koch
    "O": b'O',  # Porphyrius
    "R": b'R',  # Regiomontanus
    "C": b'C',  # Campanus
    "E": b'E',  # Equal
    "W": b'W',  # Whole Sign
    "B": b'B'   # Alcabitius
}

def get_planet_position(
    dt: datetime,
    planet_id: int,
    flag: int = swe.FLG_SWIEPH
) -> Tuple[float, float, float]:
    """
    Get the longitude, latitude, and distance of a planet at a given time.

    Args:
        dt: The datetime for which to calculate the position
        planet_id: The Swiss Ephemeris planet ID
        flag: Calculation flag (default: SWIEPH for Swiss Ephemeris)

    Returns:
        Tuple of (longitude, latitude, distance)
    """
    try:
        # Convert datetime to Julian day
        jd = get_julian_day(dt)

        # Calculate planet position
        result = swe.calc_ut(jd, planet_id, flag)

        # Extract longitude, latitude, and distance
        longitude = result[0]
        latitude = result[1]
        distance = result[2]

        return longitude, latitude, distance
    except Exception as e:
        logger.error(f"Error calculating position for planet {planet_id}: {e}")
        return 0.0, 0.0, 0.0

def get_house_cusps(
    dt: datetime,
    lat: float,
    lon: float,
    house_system: str = "P"
) -> List[float]:
    """
    Calculate house cusps for a given time and location.

    Args:
        dt: The datetime for which to calculate houses
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        house_system: House system to use (default: "P" for Placidus)

    Returns:
        List of house cusps longitudes (1-12)
    """
    try:
        # Convert datetime to Julian day
        jd = get_julian_day(dt)

        # Get house system code
        hsys = HOUSE_SYSTEMS.get(house_system, b'P')

        # Calculate houses
        houses, ascmc = swe.houses(jd, lat, lon, hsys)

        # Return house cusps as a list
        return list(houses)
    except Exception as e:
        logger.error(f"Error calculating house cusps: {e}")
        # Return default values if calculation fails
        return [i * 30.0 for i in range(12)]

def calculate_ascendant(
    dt: datetime,
    lat: float,
    lon: float
) -> float:
    """
    Calculate the Ascendant (rising sign) for a given time and location.

    Args:
        dt: The datetime for which to calculate the Ascendant
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees

    Returns:
        Ascendant longitude in degrees
    """
    try:
        # Convert datetime to Julian day
        jd = get_julian_day(dt)

        # Calculate houses with Placidus system
        houses, ascmc = swe.houses(jd, lat, lon, b'P')

        # The Ascendant is the first value in ascmc
        asc = ascmc[0]

        return asc
    except Exception as e:
        logger.error(f"Error calculating Ascendant: {e}")
        return 0.0

def calculate_midheaven(
    dt: datetime,
    lat: float,
    lon: float
) -> float:
    """
    Calculate the Midheaven (MC) for a given time and location.

    Args:
        dt: The datetime for which to calculate the Midheaven
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees

    Returns:
        Midheaven longitude in degrees
    """
    try:
        # Convert datetime to Julian day
        jd = get_julian_day(dt)

        # Calculate houses with Placidus system
        houses, ascmc = swe.houses(jd, lat, lon, b'P')

        # The Midheaven is the second value in ascmc
        mc = ascmc[1]

        return mc
    except Exception as e:
        logger.error(f"Error calculating Midheaven: {e}")
        return 0.0

def get_julian_day(dt: datetime) -> float:
    """
    Convert a datetime object to Julian day.

    Args:
        dt: The datetime to convert

    Returns:
        Julian day as a float
    """
    # Ensure datetime is timezone-aware (convert to UTC if not)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    # Extract date and time components
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    minute = dt.minute
    second = dt.second

    # Calculate time as decimal hours
    time = hour + minute/60.0 + second/3600.0

    # Calculate Julian day
    jd = swe.julday(year, month, day, time)

    return jd

def calculate_aspects(
    lon1: float,
    lon2: float,
    orb: float = 5.0
) -> Dict[str, float]:
    """
    Calculate aspects between two zodiacal longitudes.

    Args:
        lon1: First longitude in degrees
        lon2: Second longitude in degrees
        orb: Maximum orb in degrees for aspects

    Returns:
        Dictionary of aspect types with their exact orbs, or empty dict if no aspect found
    """
    # Major aspects with their exact angles
    aspects = {
        "conjunction": 0.0,
        "sextile": 60.0,
        "square": 90.0,
        "trine": 120.0,
        "opposition": 180.0
    }

    # Calculate angular difference
    diff = abs((lon1 - lon2) % 360)
    if diff > 180:
        diff = 360 - diff

    # Check for aspects within orb
    result = {}
    for aspect_name, aspect_angle in aspects.items():
        aspect_diff = abs(diff - aspect_angle)
        if aspect_diff <= orb:
            result[aspect_name] = aspect_diff

    return result

def get_planet_positions(
    dt: datetime,
    planets: Optional[List[int]] = None
) -> Dict[int, Dict[str, float]]:
    """
    Get positions for multiple planets at once.

    Args:
        dt: The datetime for which to calculate positions
        planets: List of planet IDs to calculate (defaults to major planets)

    Returns:
        Dictionary mapping planet IDs to position data
    """
    if planets is None:
        planets = [
            swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
            swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO
        ]

    result = {}
    for planet_id in planets:
        longitude, latitude, distance = get_planet_position(dt, planet_id)
        result[planet_id] = {
            "longitude": longitude,
            "latitude": latitude,
            "distance": distance
        }

    return result

def verify_ephemeris_files() -> bool:
    """
    Verify that required ephemeris files are present.

    Returns:
        True if all required files are found, False otherwise
    """
    required_files = [
        "seas_18.se1",  # Asteroids
        "semo_18.se1",  # Moon
        "sepl_18.se1"   # Planets
    ]

    missing_files = []

    for filename in required_files:
        file_path = os.path.join(EPHEMERIS_PATH, filename)
        if not os.path.exists(file_path):
            missing_files.append(filename)

    if missing_files:
        logger.error(f"Missing ephemeris files: {', '.join(missing_files)}")
        return False

    logger.info("All required ephemeris files found")
    return True

class MinimalChart:
    """
    Minimal chart implementation for efficient planetary calculations.

    This class provides a lightweight but accurate chart calculation
    using Swiss Ephemeris directly, without the overhead of
    complete chart libraries.
    """

    def __init__(self, dt: datetime, lat: float, lon: float, house_system: str = "P"):
        """
        Initialize a minimal chart with accurate planetary positions.

        Args:
            dt: Birth datetime
            lat: Birth latitude in decimal degrees
            lon: Birth longitude in decimal degrees
            house_system: House system to use (default: "P" for Placidus)
        """
        self.dt = dt
        self.lat = lat
        self.lon = lon
        self.house_system = house_system
        self.jd = get_julian_day(dt)

        # Calculate planets
        self.planets = self._calculate_planets()

        # Calculate houses and angles
        self.houses, self.angles = self._calculate_houses_and_angles()

        # Generate sign data
        self.sign_longitudes = self._calculate_sign_longitudes()

        # Calculate aspects between planets
        self.aspects = self.calculate_aspects()

    def _calculate_planets(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate accurate planetary positions with Swiss Ephemeris.

        Returns:
            Dictionary of planet data
        """
        planet_data = {}

        # Planet mappings (planet name -> Swiss Ephemeris ID)
        planet_mappings = {
            "sun": swe.SUN,
            "moon": swe.MOON,
            "mercury": swe.MERCURY,
            "venus": swe.VENUS,
            "mars": swe.MARS,
            "jupiter": swe.JUPITER,
            "saturn": swe.SATURN,
            "uranus": swe.URANUS,
            "neptune": swe.NEPTUNE,
            "pluto": swe.PLUTO,
            "chiron": swe.CHIRON,
            "north_node": swe.MEAN_NODE,
            "true_node": swe.TRUE_NODE,
            "south_node": -1  # Special handling for South Node
        }

        # Calculate positions for all planets
        for planet_name, planet_id in planet_mappings.items():
            try:
                # Special handling for South Node (opposite to North Node)
                if planet_id == -1:
                    if "north_node" in planet_data:
                        north_node = planet_data["north_node"]
                        south_node_lon = (north_node["longitude"] + 180) % 360

                        # Calculate sign for south node
                        sign_num = int(south_node_lon / 30) % 12
                        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

                        planet_data["south_node"] = {
                            "longitude": south_node_lon,
                            "latitude": -north_node["latitude"],
                            "distance": north_node["distance"],
                            "speed": -north_node["speed"],
                            "sign": signs[sign_num],
                            "sign_num": sign_num,
                            "degree": south_node_lon % 30,
                            "retrograde": not north_node["retrograde"]
                        }
                    continue  # Skip the regular calculation for South Node
            except Exception as e:
                logger.error(f"Error calculating South Node position: {e}")
                continue

            try:
                # Calculate position with high precision
                flags = swe.FLG_SWIEPH | swe.FLG_SPEED
                result = swe.calc_ut(self.jd, planet_id, flags)

                # Extract data
                longitude = result[0]
                latitude = result[1]
                distance = result[2]
                speed_lon = result[3]  # Speed in longitude
                speed_lat = result[4]  # Speed in latitude
                speed_dist = result[5]  # Speed in distance

                # Determine if retrograde
                retrograde = speed_lon < 0

                # Calculate sign
                sign_num = int(longitude / 30) % 12
                signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                sign = signs[sign_num]

                # Store planet data
                planet_data[planet_name] = {
                    "longitude": longitude,
                    "latitude": latitude,
                    "distance": distance,
                    "speed": speed_lon,
                    "speed_lat": speed_lat,
                    "speed_dist": speed_dist,
                    "sign": sign,
                    "sign_num": sign_num,
                    "degree": longitude % 30,
                    "retrograde": retrograde
                }
            except Exception as e:
                logger.error(f"Error calculating position for planet {planet_name}: {e}")

        return planet_data

    def _calculate_houses_and_angles(self) -> Tuple[List[float], Dict[str, Dict[str, Any]]]:
        """
        Calculate houses and angles (Ascendant, MC, etc.) with Swiss Ephemeris.

        Returns:
            Tuple of (house cusps, angles)
        """
        houses = []
        angles = {}

        try:
            # Get house system code
            hsys = HOUSE_SYSTEMS.get(self.house_system, b'P')

            # Calculate houses and angles
            house_cusps, ascmc = swe.houses(self.jd, self.lat, self.lon, hsys)

            # Store house cusps
            houses = list(house_cusps)

            # Extract angles
            asc_lon = ascmc[0]
            mc_lon = ascmc[1]
            # Calculate descendant and IC
            dsc_lon = (asc_lon + 180) % 360
            ic_lon = (mc_lon + 180) % 360

            # Calculate signs for angles
            signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

            # Store angle data
            angles["asc"] = {
                "name": "Ascendant",
                "longitude": asc_lon,
                "sign": signs[int(asc_lon / 30) % 12],
                "degree": asc_lon % 30
            }

            angles["mc"] = {
                "name": "Midheaven",
                "longitude": mc_lon,
                "sign": signs[int(mc_lon / 30) % 12],
                "degree": mc_lon % 30
            }

            angles["dsc"] = {
                "name": "Descendant",
                "longitude": dsc_lon,
                "sign": signs[int(dsc_lon / 30) % 12],
                "degree": dsc_lon % 30
            }

            angles["ic"] = {
                "name": "Imum Coeli",
                "longitude": ic_lon,
                "sign": signs[int(ic_lon / 30) % 12],
                "degree": ic_lon % 30
            }

            # Add additional points if available in extended house calculation
            if len(ascmc) > 4:
                # East point (EP)
                ep_lon = ascmc[4]
                angles["ep"] = {
                    "name": "East Point",
                    "longitude": ep_lon,
                    "sign": signs[int(ep_lon / 30) % 12],
                    "degree": ep_lon % 30
                }

            if len(ascmc) > 5:
                # Vertex (VX)
                vx_lon = ascmc[5]
                angles["vertex"] = {
                    "name": "Vertex",
                    "longitude": vx_lon,
                    "sign": signs[int(vx_lon / 30) % 12],
                    "degree": vx_lon % 30
                }

        except Exception as e:
            logger.error(f"Error calculating houses and angles: {e}")

        return houses, angles

    def _calculate_sign_longitudes(self) -> Dict[str, float]:
        """
        Calculate the longitudes of the zodiac signs.

        Returns:
            Dictionary of sign names and their starting longitudes
        """
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        sign_longitudes = {}
        for i, sign in enumerate(signs):
            sign_longitudes[sign] = i * 30.0

        return sign_longitudes

    def get_planet_house(self, planet_name: str) -> int:
        """
        Determine which house a planet is in using improved algorithm.

        Args:
            planet_name: Name of the planet

        Returns:
            House number (1-12)
        """
        if planet_name not in self.planets:
            return 1  # Default to first house if planet not found

        planet_lon = self.planets[planet_name]["longitude"]

        # Handle special case when house 1 spans 0° Aries
        house1_cusp = self.houses[0]
        if planet_lon >= house1_cusp or planet_lon < self.houses[-1]:
            return 1

        # Find the house containing this longitude
        for i in range(11):
            current_cusp = self.houses[i]
            next_cusp = self.houses[i+1]

            # Check if planet is in this house
            if current_cusp <= planet_lon < next_cusp:
                return i + 1

        # If we reach here, planet must be in house 12
        return 12

    def calculate_aspects(self, orb_dict: Optional[Dict[str, float]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculate aspects between planets with improved accuracy.

        Args:
            orb_dict: Optional dictionary of aspect types and their orbs

        Returns:
            Dictionary of aspects by type
        """
        # Default orbs if not provided
        if orb_dict is None:
            orb_dict = {
                "conjunction": 8.0,
                "opposition": 8.0,
                "trine": 7.0,
                "square": 7.0,
                "sextile": 6.0,
                "quincunx": 3.0,
                "semisextile": 3.0,
                "semisquare": 2.0,
                "sesquisquare": 2.0
            }

        # Aspect angles
        aspect_angles = {
            "conjunction": 0.0,
            "opposition": 180.0,
            "trine": 120.0,
            "square": 90.0,
            "sextile": 60.0,
            "quincunx": 150.0,
            "semisextile": 30.0,
            "semisquare": 45.0,
            "sesquisquare": 135.0
        }

        aspects = {aspect: [] for aspect in aspect_angles}

        # Calculate aspects between planets
        planet_names = list(self.planets.keys())

        for i, p1 in enumerate(planet_names):
            for p2 in planet_names[i+1:]:
                if p1 not in self.planets or p2 not in self.planets:
                    continue

                lon1 = self.planets[p1]["longitude"]
                lon2 = self.planets[p2]["longitude"]

                # Calculate angular difference
                diff = abs((lon1 - lon2) % 360)
                if diff > 180:
                    diff = 360 - diff

                # Check for aspects
                for aspect, angle in aspect_angles.items():
                    orb = orb_dict.get(aspect, 5.0)
                    aspect_diff = abs(diff - angle)

                    if aspect_diff <= orb:
                        # Calculate applying/separating
                        # Need speed of both planets
                        speed1 = self.planets[p1].get("speed", 0)
                        speed2 = self.planets[p2].get("speed", 0)

                        # Determine if applying or separating
                        applying = False

                        # Calculate relative motion
                        rel_motion = _calculate_aspect_motion(lon1, lon2, speed1, speed2, angle)
                        applying = rel_motion < 0  # Negative means planets are moving closer to exact aspect

                        # Calculate aspect strength (100% = exact, 0% = at maximum orb)
                        strength = (1 - (aspect_diff / orb)) * 100 if orb > 0 else 100

                        # Add aspect to list
                        aspects[aspect].append({
                            "planet1": p1,
                            "planet2": p2,
                            "angle": angle,
                            "orb": aspect_diff,
                            "applying": applying,
                            "strength": strength,
                            "planet1_speed": speed1,
                            "planet2_speed": speed2
                        })

        return aspects

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert chart to dictionary format with enhanced data.

        Returns:
            Dictionary representation of the chart
        """
        # Update house placements for all planets
        for planet_name in self.planets:
            house_num = self.get_planet_house(planet_name)
            self.planets[planet_name]["house"] = house_num

            # Add additional house information
            if 1 <= house_num <= 12:
                cusp_longitude = self.houses[house_num - 1]
                sign_num = int(cusp_longitude / 30) % 12
                signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

                self.planets[planet_name]["house_sign"] = signs[sign_num]
                self.planets[planet_name]["house_cusp_longitude"] = cusp_longitude

        # Organize aspects data for readability
        organized_aspects = {}

        # First, list major aspects
        major_aspects = ["conjunction", "opposition", "trine", "square", "sextile"]
        minor_aspects = ["quincunx", "semisextile", "semisquare", "sesquisquare"]

        for aspect_type in major_aspects + minor_aspects:
            if aspect_type in self.aspects and self.aspects[aspect_type]:
                # Sort aspects by strength (strongest first)
                organized_aspects[aspect_type] = sorted(
                    self.aspects[aspect_type],
                    key=lambda x: x.get("strength", 0),
                    reverse=True
                )

        return {
            "birth_datetime": self.dt.isoformat(),
            "latitude": self.lat,
            "longitude": self.lon,
            "house_system": self.house_system,
            "planets": self.planets,
            "houses": self.houses,
            "angles": self.angles,
            "aspects": organized_aspects,
            "jd": self.jd
        }


def _calculate_aspect_motion(lon1: float, lon2: float, speed1: float, speed2: float, aspect_angle: float) -> float:
    """
    Calculate if an aspect is applying or separating based on planetary speeds.

    Returns:
        Relative motion value (negative = applying, positive = separating)
    """
    # Calculate the current angle between the planets
    diff = (lon1 - lon2) % 360
    if diff > 180:
        diff = 360 - diff

    # Calculate direction to exact aspect
    if aspect_angle == 0:  # Conjunction
        if diff < 180:
            # Planet 1 is ahead of planet 2
            rel_motion = speed1 - speed2
        else:
            # Planet 2 is ahead of planet 1
            rel_motion = speed2 - speed1
    else:
        # For other aspects, we need to consider the direction
        if diff < aspect_angle:
            # Need to increase the angle
            rel_motion = speed2 - speed1
        else:
            # Need to decrease the angle
            rel_motion = speed1 - speed2

    return rel_motion
