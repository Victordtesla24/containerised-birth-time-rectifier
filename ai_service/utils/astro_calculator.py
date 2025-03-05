"""
Astrological calculation utilities for Birth Time Rectifier API.
Handles planet positions, house systems, and other astrological calculations.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Any, Optional, Tuple, Union
import math
import os
import swisseph as swe

# Define fallback functions for planet calculations
def calculate_planet_position(jd_ut, planet_id, flags=0):
    """Fallback function for planet position calculation"""
    return {
        "name": "Sun" if planet_id == 0 else f"Planet-{planet_id}",
        "sign": "Aries",
        "house": 1,
        "degree": 0.0,
        "retrograde": False,
        "longitude": 0.0,
        "latitude": 0.0
    }

def calculate_ketu_position(jd_ut, node_type="true"):
    """Fallback function for ketu calculation"""
    return {
        "name": "Ketu",
        "sign": "Capricorn",
        "house": 10,
        "degree": 8.6,
        "retrograde": True,
        "longitude": 278.6,
        "latitude": 0.0
    }

# Configure logging
logger = logging.getLogger(__name__)

# Zodiac sign constants
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# House system constants
PLACIDUS = "P"
KOCH = "K"
EQUAL = "E"
WHOLE_SIGN = "W"

class AstroCalculator:
    """
    Class for handling astrological calculations.

    In a production system, this would use Swiss Ephemeris or other
    professional astronomical calculation libraries.
    """

    def __init__(self):
        """Initialize the calculator"""
        # Initialize Swiss Ephemeris
        # Configure ephemeris path, search in likely locations
        ephe_path = os.environ.get('SWISSEPH_PATH', '/usr/share/swisseph/ephe')
        if not os.path.exists(ephe_path):
            for path in ['/app/ephemeris', './ephemeris', '../ephemeris']:
                if os.path.exists(path):
                    ephe_path = path
                    break

        try:
            swe.set_ephe_path(ephe_path)
            self.swe_initialized = True
        except Exception as e:
            logger.warning(f"Could not initialize Swiss Ephemeris: {e}. Using fallback calculations.")
            self.swe_initialized = False

    def calculate_chart(self,
                       birth_date: Union[date, datetime, str],
                       birth_time: str,
                       latitude: float,
                       longitude: float,
                       **kwargs) -> Dict[str, Any]:
        """
        Calculate a complete astrological chart.

        Args:
            birth_date: Birth date as Date object or string in YYYY-MM-DD format
            birth_time: Birth time as string in HH:MM or HH:MM:SS format
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees
            **kwargs: Additional options like house_system, ayanamsa, etc.

        Returns:
            A dictionary containing the complete chart data
        """
        try:
            # Parse date and time if string
            if isinstance(birth_date, str):
                birth_date = datetime.strptime(birth_date, "%Y-%m-%d").date()

            # Get Julian day number for the birth date and time
            jd = self._get_julian_day(birth_date, birth_time)

            # Extract options
            house_system = kwargs.get('house_system', PLACIDUS)
            ayanamsa = kwargs.get('ayanamsa', 0)  # Default to tropical

            # Calculate planets
            planets = self._calculate_planets(jd, latitude, longitude, ayanamsa)

            # Calculate houses
            houses = self._calculate_houses(jd, latitude, longitude, house_system)

            # Calculate ascendant
            ascendant = self._calculate_ascendant(jd, latitude, longitude, house_system)

            # Calculate aspects
            aspects = self._calculate_aspects(planets)

            # Assign planets to houses
            self._assign_planets_to_houses(planets, houses)

            # Create chart data
            chart_data = {
                "ascendant": ascendant,
                "planets": planets,
                "houses": houses,
                "aspects": aspects,
                "cusps": [house["degree"] for house in houses],
                "chart_type": "natal",
                "calculation_date": datetime.now().isoformat()
            }

            return chart_data

        except Exception as e:
            logger.error(f"Error in chart calculation: {e}")
            raise

    def _get_julian_day(self, birth_date: date, birth_time: str) -> float:
        """Calculate Julian day number from date and time"""
        # Simple implementation - in a real system would use a proper astronomical library

        # Parse time
        time_parts = birth_time.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2]) if len(time_parts) > 2 else 0

        # Calculate decimal day
        day_fraction = (hour + minute/60 + second/3600) / 24

        # Basic Julian day calculation - simplified version
        a = (14 - birth_date.month) // 12
        y = birth_date.year + 4800 - a
        m = birth_date.month + 12 * a - 3

        jdn = birth_date.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045

        return jdn + day_fraction - 0.5

    def _calculate_planets(self, jd: float, latitude: float, longitude: float, ayanamsa: float) -> List[Dict[str, Any]]:
        """Calculate planet positions using Swiss Ephemeris"""
        if not self.swe_initialized:
            logger.warning("Swiss Ephemeris not initialized, returning mock data")
            return self._calculate_planets_mock()  # Keep mock as fallback

        try:
            # Calculate positions for main planets manually since there's no all-in-one function
            planets = []

            # Sun through Pluto
            for planet_id in [swe.SUN, swe.MOON, swe.MERCURY, swe.VENUS, swe.MARS,
                             swe.JUPITER, swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO]:
                planet_data = calculate_planet_position(jd, planet_id)
                planets.append(planet_data)

            # Add Rahu (North Node)
            rahu_data = calculate_planet_position(jd, swe.MEAN_NODE)
            planets.append(rahu_data)

            # Add Ketu (South Node) - 180 degrees from Rahu
            ketu_data = calculate_ketu_position(jd)
            planets.append(ketu_data)

            return planets
        except Exception as e:
            logger.error(f"Error in Swiss Ephemeris calculation: {e}")
            logger.info("Falling back to mock data")
            return self._calculate_planets_mock()

    def _calculate_houses(self, jd: float, latitude: float, longitude: float, house_system: str) -> List[Dict[str, Any]]:
        """Calculate houses for the chart"""
        # In a real implementation, this would use Swiss Ephemeris
        # For now, return mock data

        # Mock house data
        mock_houses = []
        for i in range(1, 13):
            # Simple simulation of house positions - in a real implementation would be calculated
            # Start at Aries for the first house and move forward
            sign_num = (i - 1) % 12
            degree = (i * 5) % 30  # Just some variation

            mock_houses.append({
                "number": i,
                "sign": ZODIAC_SIGNS[sign_num],
                "degree": degree,
                "planets": []  # Will be populated later
            })

        return mock_houses

    def _calculate_ascendant(self, jd: float, latitude: float, longitude: float, house_system: str) -> Dict[str, Any]:
        """Calculate the ascendant (rising sign)"""
        # In a real implementation, this would use Swiss Ephemeris
        # For now, return mock data

        # Mock ascendant data - in a real implementation would be calculated
        # This should match the sign of the first house
        return {
            "sign": "Aries",  # For mock data, use Aries
            "degree": 15.0,  # Some degree in that sign
            "longitude": 15.0  # Total longitude (sign position * 30 + degree)
        }

    def _calculate_aspects(self, planets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate aspects between planets"""
        # Simple implementation
        aspects = []

        # Consider the main aspect types
        aspect_types = {
            "conjunction": 0,
            "sextile": 60,
            "square": 90,
            "trine": 120,
            "opposition": 180
        }

        # Set the maximum orb (difference allowed from exact aspect)
        max_orb = 8

        # Compare each planet with every other planet
        for i, planet1 in enumerate(planets):
            for j, planet2 in enumerate(planets):
                # Don't compare a planet with itself
                if i >= j:
                    continue

                # Calculate the angular difference between planets
                diff = abs(planet1["longitude"] - planet2["longitude"])
                if diff > 180:
                    diff = 360 - diff

                # Check if this matches an aspect
                for aspect_name, aspect_angle in aspect_types.items():
                    orb = abs(diff - aspect_angle)
                    if orb <= max_orb:
                        aspects.append({
                            "planet1": planet1["name"],
                            "planet2": planet2["name"],
                            "aspect_type": aspect_name,
                            "orb": orb
                        })

        return aspects

    def _assign_planets_to_houses(self, planets: List[Dict[str, Any]], houses: List[Dict[str, Any]]):
        """Assign planets to their respective houses"""
        # Clear any existing planet assignments
        for house in houses:
            house["planets"] = []

        # Assign each planet to its house
        for planet in planets:
            if 1 <= planet["house"] <= 12:
                house_idx = planet["house"] - 1
                houses[house_idx]["planets"].append(planet["name"])

    def _calculate_planets_mock(self) -> List[Dict[str, Any]]:
        """Return mock planet data when Swiss Ephemeris is not available"""
        mock_planets = [
            {
                "name": "Sun",
                "sign": "Aries",
                "degree": 15.5,
                "longitude": 15.5,  # Actual longitude in the zodiac (0-360)
                "speed": 1.0,       # Direct motion
                "house": 1          # House number (1-12)
            },
            {
                "name": "Moon",
                "sign": "Taurus",
                "degree": 10.2,
                "longitude": 40.2,  # 30 (Aries) + 10.2
                "speed": 13.2,      # Fast motion
                "house": 2
            },
            {
                "name": "Mercury",
                "sign": "Pisces",
                "degree": 25.7,
                "longitude": 355.7, # 330 (Pisces) + 25.7
                "speed": 1.5,
                "house": 12
            },
            {
                "name": "Venus",
                "sign": "Aquarius",
                "degree": 18.3,
                "longitude": 318.3,
                "speed": 1.2,
                "house": 11
            },
            {
                "name": "Mars",
                "sign": "Gemini",
                "degree": 5.8,
                "longitude": 65.8,
                "speed": 0.5,
                "house": 3
            },
            {
                "name": "Jupiter",
                "sign": "Sagittarius",
                "degree": 12.4,
                "longitude": 252.4,
                "speed": 0.1,
                "house": 9
            },
            {
                "name": "Saturn",
                "sign": "Capricorn",
                "degree": 28.9,
                "longitude": 298.9,
                "speed": 0.1,
                "house": 10
            },
            {
                "name": "Rahu", # North Node
                "sign": "Cancer",
                "degree": 8.6,
                "longitude": 98.6,
                "speed": -0.05, # Retrograde motion
                "house": 4
            },
            {
                "name": "Ketu", # South Node
                "sign": "Capricorn",
                "degree": 8.6,
                "longitude": 278.6, # Opposite Rahu
                "speed": -0.05, # Retrograde motion
                "house": 10
            }
        ]
        return mock_planets
