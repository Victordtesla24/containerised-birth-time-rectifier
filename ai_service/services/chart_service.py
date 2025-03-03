"""
Chart Service Module for Birth Time Rectifier

This service provides high-accuracy astrological chart calculations
using our improved chart_calculator module.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import pytz
from zoneinfo import ZoneInfo

from ai_service.core.chart_calculator import (
    calculate_chart as core_calculate_chart,
    get_chart_with_aspects,
    calculate_ketu_position,
    calculate_ascendant,
    julian_day_ut,
    get_zodiac_sign,
    normalize_longitude
)

# Configure logging
logger = logging.getLogger(__name__)

class ChartService:
    """
    Service for handling astrological chart calculations with high accuracy.
    """

    def __init__(self, ephemeris_path: Optional[str] = None):
        """
        Initialize the ChartService.

        Args:
            ephemeris_path: Optional path to ephemeris files
        """
        # If ephemeris_path is provided, the chart_calculator will use it
        self.ephemeris_path = ephemeris_path
        logger.info("ChartService initialized")

    def parse_datetime(self, birth_date: str, birth_time: str, timezone_str: str) -> datetime:
        """
        Parse birth date and time into a datetime object with timezone.

        Args:
            birth_date: Birth date in format 'YYYY-MM-DD'
            birth_time: Birth time in format 'HH:MM:SS' or 'HH:MM'
            timezone_str: Timezone string (e.g., 'Asia/Kolkata')

        Returns:
            Datetime object with timezone information
        """
        # Parse birth date and time
        datetime_str = f"{birth_date} {birth_time}"

        # Check time format and adjust if needed
        if birth_time.count(':') == 1:
            # Only hour and minute provided, add seconds
            datetime_str = f"{datetime_str}:00"

        # Parse into datetime object
        birth_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')

        # Apply timezone
        try:
            # Try with ZoneInfo first (Python 3.9+)
            tz = ZoneInfo(timezone_str)
            birth_dt_with_tz = birth_dt.replace(tzinfo=tz)
        except (ImportError, KeyError):
            # Fall back to pytz if ZoneInfo fails
            try:
                tz = pytz.timezone(timezone_str)
                birth_dt_with_tz = tz.localize(birth_dt)
            except Exception as e:
                logger.warning(f"Invalid timezone {timezone_str}: {e}. Using UTC.")
                birth_dt_with_tz = birth_dt.replace(tzinfo=pytz.UTC)

        return birth_dt_with_tz

    def generate_chart(self,
                      birth_date: str,
                      birth_time: str,
                      latitude: float,
                      longitude: float,
                      timezone: str,
                      location_name: str = "",
                      house_system: str = "placidus",
                      ayanamsa: float = 23.6647,  # Lahiri ayanamsa by default
                      node_type: str = "true",
                      zodiac_type: str = "sidereal") -> Dict[str, Any]:
        """
        Generate a complete astrological chart.

        Args:
            birth_date: Birth date in format 'YYYY-MM-DD'
            birth_time: Birth time in format 'HH:MM:SS' or 'HH:MM'
            latitude: Birth place latitude
            longitude: Birth place longitude
            timezone: Timezone string (e.g., 'Asia/Kolkata')
            location_name: Name of birth place (optional)
            house_system: House system to use (default: 'placidus')
            ayanamsa: Ayanamsa value for sidereal calculations
            node_type: 'mean' or 'true' for node calculations
            zodiac_type: 'tropical' or 'sidereal'

        Returns:
            Complete chart data
        """
        try:
            # Calculate chart using the improved calculator
            chart_data = get_chart_with_aspects(
                birth_date=birth_date,
                birth_time=birth_time,
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
                house_system=house_system,
                ayanamsa=ayanamsa,
                node_type=node_type,
                zodiac_type=zodiac_type
            )

            # Transform the data for API compatibility
            transformed_data = self._transform_chart_data(chart_data)

            return transformed_data

        except Exception as e:
            logger.error(f"Error generating chart: {str(e)}")
            raise

    def _transform_chart_data(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform chart data from internal format to API format.

        Args:
            chart_data: Chart data from chart_calculator

        Returns:
            Transformed chart data for API
        """
        # Extract basic chart information
        birth_details = chart_data["birth_details"]
        ascendant = chart_data["ascendant"]
        planets = chart_data["planets"]
        houses = chart_data["houses"]
        aspects = chart_data.get("aspects", [])

        # Format planets for API
        formatted_planets = []
        rahu_data = None
        for planet_name, planet_data in planets.items():
            if planet_name.lower() == "rahu":
                rahu_data = planet_data
            formatted_planet = {
                "name": planet_name.capitalize(),
                "sign": planet_data["sign"],
                "house": planet_data["house"],
                "degree": planet_data["degree"],
                "retrograde": planet_data.get("retrograde", False),
                "longitude": planet_data["longitude"],
                "latitude": planet_data.get("latitude", 0.0)
            }
            formatted_planets.append(formatted_planet)

        # Ensure Ketu's degree is exactly opposite to Rahu's
        if rahu_data:
            ketu_degree = (30 - rahu_data["degree"]) % 30
            for planet in formatted_planets:
                if planet["name"] == "Ketu":
                    planet["degree"] = ketu_degree

        # Format houses for API
        formatted_houses = []
        for house in houses:
            formatted_house = {
                "number": house["number"],
                "sign": house["sign"],
                "degree": house["degree"]
            }
            formatted_houses.append(formatted_house)

        # Format aspects for API
        formatted_aspects = []
        for aspect in aspects:
            formatted_aspect = {
                "planet1": aspect["planet1"],
                "planet2": aspect["planet2"],
                "aspect_type": aspect["type"],
                "orb": aspect["orb"]
            }
            formatted_aspects.append(formatted_aspect)

        # Compile the final chart data
        transformed_chart = {
            "birth_details": birth_details,
            "ascendant": {
                "sign": ascendant["sign"],
                "degree": ascendant["degree"],
                "longitude": ascendant["longitude"]
            },
            "planets": formatted_planets,
            "houses": formatted_houses,
            "aspects": formatted_aspects
        }

        return transformed_chart

    def compare_charts(self, original_chart: Dict[str, Any], rectified_chart: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare two charts and identify differences.

        Args:
            original_chart: Original chart data
            rectified_chart: Rectified chart data

        Returns:
            Differences between the charts
        """
        # Extract key components from both charts
        original_ascendant = original_chart["ascendant"]
        rectified_ascendant = rectified_chart["ascendant"]

        # Create dictionary to store differences
        differences = {
            "ascendant": {
                "sign_changed": original_ascendant["sign"] != rectified_ascendant["sign"],
                "degree_difference": abs(original_ascendant["degree"] - rectified_ascendant["degree"]),
                "original": original_ascendant,
                "rectified": rectified_ascendant
            },
            "planets": [],
            "houses": []
        }

        # Compare planets
        original_planets = {p["name"]: p for p in original_chart["planets"]}
        rectified_planets = {p["name"]: p for p in rectified_chart["planets"]}

        for name, original_planet in original_planets.items():
            if name in rectified_planets:
                rectified_planet = rectified_planets[name]
                differences["planets"].append({
                    "name": name,
                    "sign_changed": original_planet["sign"] != rectified_planet["sign"],
                    "house_changed": original_planet["house"] != rectified_planet["house"],
                    "degree_difference": abs(original_planet["degree"] - rectified_planet["degree"]),
                    "original": original_planet,
                    "rectified": rectified_planet
                })

        # Compare houses
        original_houses = {h["number"]: h for h in original_chart["houses"]}
        rectified_houses = {h["number"]: h for h in rectified_chart["houses"]}

        for number, original_house in original_houses.items():
            if number in rectified_houses:
                rectified_house = rectified_houses[number]
                differences["houses"].append({
                    "number": number,
                    "sign_changed": original_house["sign"] != rectified_house["sign"],
                    "degree_difference": abs(original_house["degree"] - rectified_house["degree"]),
                    "original": original_house,
                    "rectified": rectified_house
                })

        return differences
