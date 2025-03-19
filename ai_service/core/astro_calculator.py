"""
Astrological calculation module for Birth Time Rectifier.
"""

import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz
import swisseph as swe  # Required dependency

logger = logging.getLogger(__name__)

# Constants
PLANETS = {
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
    "mean_node": swe.MEAN_NODE,  # North Node (Rahu)
    "true_node": swe.TRUE_NODE,
    "mean_apog": swe.MEAN_APOG,  # Lilith
    "chiron": swe.CHIRON
}

# House systems
HOUSE_SYSTEMS = {
    "P": "Placidus",
    "K": "Koch",
    "O": "Porphyrius",
    "R": "Regiomontanus",
    "C": "Campanus",
    "A": "Equal",
    "W": "Whole Sign",
    "B": "Alcabitus",
    "X": "Meridian",
    "H": "Horizon",
    "T": "Polich/Page",
    "M": "Morinus",
    "V": "Vehlow Equal"
}

def get_position_value(result: Any, index: int) -> float:
    """Extract a value from a calculation result tuple safely."""
    if result and len(result) > index:
        return float(result[index])
    return 0.0

class AstroCalculator:
    """Astrological calculator for birth chart generation."""

    def __init__(self, ephe_path: Optional[str] = None, ayanamsa_type: int = 1):
        """
        Initialize the calculator.

        Args:
            ephe_path: Path to the ephemeris files (defaults to environment variable)
            ayanamsa_type: Type of ayanamsa (1 = Lahiri, default for Indian/Vedic astrology)
        """
        # Use environment variable if path not provided
        if ephe_path is None:
            ephe_path = os.environ.get("SWISSEPH_PATH", "/app/ephemeris")

        # Check if directory exists and has files
        if not os.path.isdir(ephe_path):
            raise ValueError(f"Ephemeris directory {ephe_path} does not exist")

        files = os.listdir(ephe_path)
        if not any(f.endswith('.se1') for f in files):
            raise ValueError(f"No ephemeris files found in {ephe_path}")

        logger.info(f"Using ephemeris files from: {ephe_path}")
        self.ephe_path = ephe_path
        self.ayanamsa_type = ayanamsa_type

        # Initialize Swiss Ephemeris
        try:
            swe.set_ephe_path(ephe_path)
            swe.set_sid_mode(ayanamsa_type)
            logger.info(f"Swiss Ephemeris initialized with path: {ephe_path} and Lahiri ayanamsa")
        except Exception as e:
            logger.error(f"Error initializing Swiss Ephemeris: {e}")
            raise ValueError(f"Failed to initialize Swiss Ephemeris: {e}")

    async def calculate_chart(self, birth_date: str, birth_time: str,
                            latitude: float, longitude: float,
                            timezone: str = "UTC",
                            house_system: str = "W",
                            include_aspects: bool = True,
                            include_houses: bool = True,
                            include_divisional_charts: bool = False) -> Dict[str, Any]:
        """
        Calculate birth chart for given date, time and location.

        Args:
            birth_date: Date of birth in ISO format (YYYY-MM-DD)
            birth_time: Time of birth in 24-hour format (HH:MM)
            latitude: Latitude of birth place
            longitude: Longitude of birth place
            timezone: Timezone name (from pytz)
            house_system: House system to use (default: Whole Sign)
            include_aspects: Whether to include planetary aspects
            include_houses: Whether to include houses
            include_divisional_charts: Whether to include divisional charts for Vedic astrology

        Returns:
            Dictionary with chart data
        """
        # Parse birth date and time
        try:
            birth_datetime_str = f"{birth_date} {birth_time}"
            birth_datetime = datetime.strptime(birth_datetime_str, "%Y-%m-%d %H:%M")

            # Apply timezone
            try:
                tz = pytz.timezone(timezone)
                birth_datetime = tz.localize(birth_datetime)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone: {timezone}, using UTC")
                tz = pytz.UTC
                birth_datetime = tz.localize(birth_datetime)

            # Convert to UTC for calculations
            utc_datetime = birth_datetime.astimezone(pytz.UTC)

        except ValueError as e:
            logger.error(f"Error parsing birth date/time: {e}")
            raise ValueError(f"Invalid birth date or time format: {e}")

        # Calculate Julian day
        jd = self._datetime_to_jd(utc_datetime)

        # Calculate positions
        positions = self._calculate_positions(jd)

        # Calculate houses if requested
        houses = None
        if include_houses:
            houses = self._calculate_houses(jd, latitude, longitude, house_system)

        # Calculate aspects if requested
        aspects = None
        if include_aspects:
            aspects = self._calculate_aspects(positions)

        # Calculate divisional charts if requested (for Vedic astrology)
        divisional_charts = None
        if include_divisional_charts:
            divisional_charts = self._calculate_divisional_charts(jd, latitude, longitude)

        # Compile result
        result = {
            "julian_day": jd,
            "birth_details": {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone
            },
            "positions": positions,
            "ephemeris_path_used": self.ephe_path,
            "calculation_accuracy": "high"
        }

        if houses:
            result["houses"] = houses

        if aspects:
            result["aspects"] = aspects

        if divisional_charts:
            result["divisional_charts"] = divisional_charts

        return result

    def _datetime_to_jd(self, dt: datetime) -> float:
        """
        Convert datetime to Julian day.

        Args:
            dt: Datetime in UTC

        Returns:
            Julian day number
        """
        # Use Swiss Ephemeris for accurate Julian day
        return swe.julday(
            dt.year,
            dt.month,
            dt.day,
            dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        )

    def _calculate_positions(self, jd: float) -> Dict[str, Dict[str, float]]:
        """
        Calculate planet positions for the given Julian day.

        Args:
            jd: Julian day number

        Returns:
            Dictionary of planet positions with longitude, latitude, distance, speed
        """
        positions = {}

        # Use Swiss Ephemeris for accurate calculations
        for planet_name, planet_id in PLANETS.items():
            # Calculate position
            calc_result = swe.calc_ut(jd, planet_id)

            # Convert to dictionary
            positions[planet_name] = {
                "longitude": get_position_value(calc_result, 0),  # Longitude in degrees
                "latitude": get_position_value(calc_result, 1),   # Latitude in degrees
                "distance": get_position_value(calc_result, 2),   # Distance in AU
                "speed": get_position_value(calc_result, 3)       # Speed in degrees/day
            }

        return positions

    def _calculate_houses(self, jd: float, lat: float, lon: float, system: str = "W") -> List[float]:
        """
        Calculate house cusps for given Julian day and location.

        Args:
            jd: Julian day number
            lat: Latitude
            lon: Longitude
            system: House system (default: Whole Sign)

        Returns:
            List of house cusps (12 positions)
        """
        if system not in HOUSE_SYSTEMS:
            logger.warning(f"Unknown house system {system}, using Whole Sign (W)")
            system = "W"

        # Calculate houses with Swiss Ephemeris
        houses, ascmc = swe.houses(jd, lat, lon, bytes(system, "utf-8"))
        return list(houses)

    def _calculate_aspects(self, positions: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
        """
        Calculate aspects between planets.

        Args:
            positions: Dictionary of planet positions

        Returns:
            List of aspects
        """
        # Define aspects and their orbs
        aspect_types = {
            "conjunction": {"angle": 0, "orb": 8},
            "opposition": {"angle": 180, "orb": 8},
            "trine": {"angle": 120, "orb": 8},
            "square": {"angle": 90, "orb": 7},
            "sextile": {"angle": 60, "orb": 6},
            "quincunx": {"angle": 150, "orb": 5},
            "semi-sextile": {"angle": 30, "orb": 4}
        }

        aspects = []

        # Calculate aspects between planets
        planet_names = list(positions.keys())
        for i, p1 in enumerate(planet_names):
            for j, p2 in enumerate(planet_names):
                if i >= j:  # Only calculate aspects once for each pair
                    continue

                # Get planet positions
                p1_pos = positions[p1]["longitude"]
                p2_pos = positions[p2]["longitude"]

                # Calculate angular distance
                angle = abs(p1_pos - p2_pos)
                if angle > 180:
                    angle = 360 - angle

                # Check for aspects
                for aspect_name, aspect_info in aspect_types.items():
                    aspect_angle = aspect_info["angle"]
                    orb = aspect_info["orb"]

                    # Check if within orb
                    if abs(angle - aspect_angle) <= orb:
                        # Calculate exact orb
                        exact_orb = abs(angle - aspect_angle)

                        # Add aspect to list
                        aspect = {
                            "planet1": p1,
                            "planet2": p2,
                            "aspect": aspect_name,
                            "orb": exact_orb,
                            "angle": aspect_angle,
                            "applying": self._is_aspect_applying(positions, p1, p2, aspect_angle)
                        }
                        aspects.append(aspect)

        return aspects

    def _is_aspect_applying(self, positions: Dict[str, Dict[str, float]], p1: str, p2: str, aspect_angle: float) -> bool:
        """
        Determine if an aspect is applying or separating.

        Args:
            positions: Dictionary of planet positions
            p1: First planet
            p2: Second planet
            aspect_angle: Aspect angle in degrees

        Returns:
            True if aspect is applying, False if separating
        """
        # Get positions and speeds
        p1_pos = positions[p1]["longitude"]
        p2_pos = positions[p2]["longitude"]
        p1_speed = positions[p1]["speed"]
        p2_speed = positions[p2]["speed"]

        # Calculate relative speed
        rel_speed = p1_speed - p2_speed

        # Calculate current angle
        angle = (p1_pos - p2_pos) % 360
        if angle > 180:
            angle = 360 - angle

        # Determine if applying or separating
        if aspect_angle == 0:  # Conjunction
            if angle > 180:
                return rel_speed > 0
            else:
                return rel_speed < 0
        elif aspect_angle == 180:  # Opposition
            if angle < 180:
                return rel_speed > 0
            else:
                return rel_speed < 0
        else:
            # For other aspects
            if angle < aspect_angle:
                return rel_speed > 0
            else:
                return rel_speed < 0

    def _calculate_divisional_charts(self, jd: float, lat: float, lon: float) -> Dict[str, Dict[str, Any]]:
        """
        Calculate divisional charts (D-charts) for Vedic astrology.

        Args:
            jd: Julian day number
            lat: Latitude
            lon: Longitude

        Returns:
            Dictionary of divisional charts
        """
        divisional_charts = {}

        # Calculate D-9 (Navamsa) chart
        navamsa = self._calculate_navamsa(jd)
        divisional_charts["D9"] = navamsa

        # Add other divisional charts as needed
        # D-3 (Drekkana)
        drekkana = self._calculate_drekkana(jd)
        divisional_charts["D3"] = drekkana

        # D-7 (Saptamsa)
        saptamsa = self._calculate_saptamsa(jd)
        divisional_charts["D7"] = saptamsa

        return divisional_charts

    def _calculate_navamsa(self, jd: float) -> Dict[str, Any]:
        """
        Calculate Navamsa (D-9) chart.

        Args:
            jd: Julian day number

        Returns:
            Dictionary with Navamsa positions
        """
        navamsa = {}

        # Calculate Navamsa positions for each planet
        for planet_name, planet_id in PLANETS.items():
            # Get tropical position
            calc_result = swe.calc_ut(jd, planet_id)
            longitude = get_position_value(calc_result, 0)

            # Calculate Navamsa position (D-9)
            navamsa_long = (longitude % 30) * 9 % 360

            # Determine sign
            sign_num = int(navamsa_long / 30)

            navamsa[planet_name] = {
                "longitude": navamsa_long,
                "sign": sign_num,
                "sign_name": self._get_sign_name(sign_num)
            }

        return navamsa

    def _calculate_drekkana(self, jd: float) -> Dict[str, Any]:
        """
        Calculate Drekkana (D-3) chart.

        Args:
            jd: Julian day number

        Returns:
            Dictionary with Drekkana positions
        """
        drekkana = {}

        # Calculate Drekkana positions for each planet
        for planet_name, planet_id in PLANETS.items():
            # Get tropical position
            calc_result = swe.calc_ut(jd, planet_id)
            longitude = get_position_value(calc_result, 0)

            # Calculate Drekkana position (D-3)
            drekkana_long = (longitude % 30) * 3 % 360

            # Determine sign
            sign_num = int(drekkana_long / 30)

            drekkana[planet_name] = {
                "longitude": drekkana_long,
                "sign": sign_num,
                "sign_name": self._get_sign_name(sign_num)
            }

        return drekkana

    def _calculate_saptamsa(self, jd: float) -> Dict[str, Any]:
        """
        Calculate Saptamsa (D-7) chart.

        Args:
            jd: Julian day number

        Returns:
            Dictionary with Saptamsa positions
        """
        saptamsa = {}

        # Calculate Saptamsa positions for each planet
        for planet_name, planet_id in PLANETS.items():
            # Get tropical position
            calc_result = swe.calc_ut(jd, planet_id)
            longitude = get_position_value(calc_result, 0)

            # Calculate Saptamsa position (D-7)
            saptamsa_long = (longitude % 30) * 7 % 360

            # Determine sign
            sign_num = int(saptamsa_long / 30)

            saptamsa[planet_name] = {
                "longitude": saptamsa_long,
                "sign": sign_num,
                "sign_name": self._get_sign_name(sign_num)
            }

        return saptamsa

    def _get_sign_name(self, sign_num: int) -> str:
        """
        Get zodiac sign name from sign number (0-11).

        Args:
            sign_num: Sign number (0-11)

        Returns:
            Sign name
        """
        signs = [
            "Aries", "Taurus", "Gemini", "Cancer",
            "Leo", "Virgo", "Libra", "Scorpio",
            "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        return signs[sign_num % 12]

# Required for dependency injection
def get_astro_calculator():
    """Factory function for AstroCalculator for dependency injection."""
    return AstroCalculator()
