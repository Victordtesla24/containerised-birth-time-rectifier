"""
Flatlib compatibility module.

This module provides direct implementation using Swiss Ephemeris for astronomical calculations.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import sys
import os

# Import constants from flatlib
from flatlib.const import LIST_SIGNS

# Import pyswisseph
import pyswisseph as swe

# Set up logging
logger = logging.getLogger(__name__)

# Define a proper chart calculator class
class BasicChartCalculator:
    """Chart calculator using Swiss Ephemeris directly.

    This implementation uses pyswisseph directly for accurate astronomical calculations.
    """

    def __init__(self):
        self._init_swiss_ephemeris()

    def _init_swiss_ephemeris(self):
        """Initialize Swiss Ephemeris."""
        self.swe = swe

        # Set ephemeris path from environment or use default
        ephemeris_path = os.environ.get('SWISSEPH_PATH', '/usr/share/swisseph')
        if not os.path.exists(ephemeris_path):
            os.environ['SWISSEPH_PATH'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'ephemeris')
            ephemeris_path = os.environ['SWISSEPH_PATH']

        self.swe.set_ephe_path(ephemeris_path)
        logger.info(f"Swiss Ephemeris initialized with path: {ephemeris_path}")

    def _calculate_planet_position_swe(self, planet: str, julian_day: float) -> float:
        """Calculate planet position using Swiss Ephemeris.

        Args:
            planet: Planet name
            julian_day: Julian day number

        Returns:
            Longitude in degrees (0-360)
        """
        # Map planet names to Swiss Ephemeris constants
        planet_map = {
            "Sun": self.swe.SUN,
            "Moon": self.swe.MOON,
            "Mercury": self.swe.MERCURY,
            "Venus": self.swe.VENUS,
            "Mars": self.swe.MARS,
            "Jupiter": self.swe.JUPITER,
            "Saturn": self.swe.SATURN,
            "Uranus": self.swe.URANUS,
            "Neptune": self.swe.NEPTUNE,
            "Pluto": self.swe.PLUTO,
            "North Node": self.swe.MEAN_NODE
        }

        if planet not in planet_map:
            raise ValueError(f"Unknown planet: {planet}")

        # Calculate position using Swiss Ephemeris
        flags = self.swe.FLG_SWIEPH
        result = self.swe.calc_ut(julian_day, planet_map[planet], flags)

        # Swiss Ephemeris returns a tuple (positions_tuple, flags)
        if result and isinstance(result, tuple) and len(result) >= 1:
            positions_tuple = result[0]  # Get the positions tuple

            # The positions tuple should have longitude as first element
            if isinstance(positions_tuple, tuple) and len(positions_tuple) >= 1:
                longitude = positions_tuple[0]  # Extract longitude
            if isinstance(longitude, (int, float)):
                return float(longitude)

        # If we got here, something went wrong with the format
        raise TypeError(f"Unexpected result format from Swiss Ephemeris: {type(result)}")

    def _calculate_houses(self, julian_day: float, latitude: float, longitude: float, hsys: str = 'P') -> List[float]:
        """Calculate house cusps.

        Args:
            julian_day: Julian day number
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            hsys: House system ('P' for Placidus, 'K' for Koch, etc.)

        Returns:
            List of 12 house cusp longitudes
        """
        # Convert house system string to a single byte
        if not hsys or len(hsys) == 0:
            hsys = 'P'

        # Take just the first character and convert to bytes
        hsys_byte = bytes([ord(hsys[0])])

        # Calculate houses using Swiss Ephemeris
        houses, ascmc = self.swe.houses(julian_day, latitude, longitude, hsys_byte)
        return list(houses)

    def calculate_chart(self, date: datetime, latitude: float, longitude: float, hsys: str = 'P') -> Dict[str, Any]:
        """Calculate a complete astrological chart using Swiss Ephemeris.

        Args:
            date: Date and time
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            hsys: House system to use

        Returns:
            Dictionary containing the full chart data
        """
        logger.info(f"Calculating chart for {date}, lat={latitude}, lon={longitude}, hsys={hsys}")

        # Convert date to Julian day
        year, month, day = date.year, date.month, date.day
        hour, minute, second = date.hour, date.minute, date.second

        # Calculate Julian day with Swiss Ephemeris
        julian_day = self.swe.julday(year, month, day, hour + minute/60.0 + second/3600.0)

        # Calculate houses
        houses_cusps = self._calculate_houses(julian_day, latitude, longitude, hsys)

        # Calculate planets
        planets_data = {}
        for planet_name in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "North Node"]:
            longitude = self._calculate_planet_position_swe(planet_name, julian_day)

            # Get sign and degree within sign
            sign_num = int(longitude / 30)
            sign_name = LIST_SIGNS[sign_num]
            sign_lon = longitude % 30

            # Determine house
            house_num = 1
            for i in range(11, -1, -1):
                house_lon = houses_cusps[i]
                if longitude >= house_lon:
                    house_num = i + 1
                    break

            # Store planet data
            planets_data[planet_name] = {
                "longitude": longitude,
                "sign": sign_name,
                "sign_longitude": sign_lon,
                "house": house_num
            }

        # Calculate ascendant and midheaven
        ascendant = houses_cusps[0]
        midheaven = houses_cusps[9]

        # Structure full chart data
        chart_data = {
            "chart_type": "tropical",
            "calculation_method": "pyswisseph",
            "houses": [],
            "planets": planets_data,
            "angles": {
                "Asc": {
                    "longitude": ascendant,
                    "sign": LIST_SIGNS[int(ascendant / 30)],
                    "sign_longitude": ascendant % 30
                },
                "MC": {
                    "longitude": midheaven,
                    "sign": LIST_SIGNS[int(midheaven / 30)],
                    "sign_longitude": midheaven % 30
                }
            }
        }

        # Add houses to chart data
        for i, cusp in enumerate(houses_cusps):
            house_num = i + 1
            sign_num = int(cusp / 30)
            sign_name = LIST_SIGNS[sign_num]
            sign_lon = cusp % 30

            chart_data["houses"].append({
                "house": house_num,
                "longitude": cusp,
                "sign": sign_name,
                "sign_longitude": sign_lon
            })

        return chart_data

class Chart:
    """Chart class using direct Swiss Ephemeris calculations."""

    def __init__(self, date, pos, hsys='P'):
        """Initialize chart with date, position and house system."""
        # Create calculator
        self.calculator = BasicChartCalculator()

        # Calculate chart data
        self.data = self.calculator.calculate_chart(date, pos.lat, pos.lon, hsys)

        # Store input parameters
        self.date = date
        self.pos = pos
        self.hsys = hsys

    def getObject(self, name):
        """Get a celestial object by name."""
        if name in self.data["planets"]:
            planet_data = self.data["planets"][name]
            return PlanetObject(
                name,
                planet_data["sign"],
                planet_data["sign_longitude"],
                planet_data["house"]
            )
        elif name in self.data["angles"]:
            angle_data = self.data["angles"][name]
            return PointObject(
                name,
                angle_data["sign"],
                angle_data["sign_longitude"]
            )
        return None

    def getHouse(self, house_num):
        """Get a house by number."""
        for house in self.data["houses"]:
            if house["house"] == house_num:
                return HouseObject(
                    house_num,
                    house["sign"],
                    house["sign_longitude"]
                )
        return None

    def object_house(self, object_name):
        """Get the house number for a celestial object."""
        obj = self.getObject(object_name)
        if obj and isinstance(obj, PlanetObject) and hasattr(obj, 'house'):
            return obj.house
        return None

    def getAngle(self, angle_name):
        """Get an angle by name."""
        if angle_name in self.data["angles"]:
            angle_data = self.data["angles"][angle_name]
            return PointObject(
                angle_name,
                angle_data["sign"],
                angle_data["sign_longitude"]
            )
        return None

class PlanetObject:
    """Planet object for chart calculations."""

    def __init__(self, name, sign, degree, house, retrograde=False):
        self.name = name
        self.sign = sign
        self.degree = degree
        self.house = house
        self.retrograde = retrograde

    def __str__(self):
        return f"{self.name} {self.sign} {self.degree:.2f}° (House {self.house})"

    def __repr__(self):
        return self.__str__()

    def signlon(self):
        return self.degree

    def lon(self):
        sign_index = LIST_SIGNS.index(self.sign)
        return sign_index * 30 + self.degree

class PointObject:
    """Point object (like angles) for chart calculations."""

    def __init__(self, name, sign, degree):
        self.name = name
        self.sign = sign
        self.degree = degree

    def __str__(self):
        return f"{self.name} {self.sign} {self.degree:.2f}°"

    def __repr__(self):
        return self.__str__()

    def signlon(self):
        return self.degree

    def lon(self):
        sign_index = LIST_SIGNS.index(self.sign)
        return sign_index * 30 + self.degree

class HouseObject:
    """House object for chart calculations."""

    def __init__(self, number, sign, degree):
        self.number = number
        self.sign = sign
        self.degree = degree

    def __str__(self):
        return f"House {self.number}: {self.sign} {self.degree:.2f}°"

    def __repr__(self):
        return self.__str__()

    def signlon(self):
        return self.degree

    def lon(self):
        sign_index = LIST_SIGNS.index(self.sign)
        return sign_index * 30 + self.degree

def createChart(date, pos, hsys='P'):
    """Create a chart using Swiss Ephemeris calculations."""
    return Chart(date, pos, hsys)

def calculate_flatlib_chart(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    house_system: str = 'P'
) -> Dict[str, Any]:
    """Calculate a chart directly using Swiss Ephemeris.

    This function calculates a chart using Swiss Ephemeris directly instead of relying
    on flatlib's implementation. This ensures compatibility and accuracy.

    Args:
        birth_dt: Birth date and time
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        house_system: House system to use (P for Placidus, etc.)

    Returns:
        Dictionary containing comprehensive chart data
    """
    # Create a calculator instance
    calculator = BasicChartCalculator()

    # Calculate the chart directly
    return calculator.calculate_chart(birth_dt, latitude, longitude, house_system)
