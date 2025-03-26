"""
Chart calculation functionality for the questionnaire service.

This module provides astrological chart calculation functions
specifically designed for birth time rectification questionnaires.
"""

import logging
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import json

# Import necessary services
from ai_service.api.services.chart_calculator_service import chart_calculator, get_chart_calculator_service
from ai_service.services import get_chart_service
import pytz

# logger initialization
logger = logging.getLogger(__name__)

def calculate_sensitive_periods(birth_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calculate astrologically sensitive periods and transitions.

    Args:
        birth_data: Dictionary with birth date, time, and location

    Returns:
        List of sensitive periods with descriptions and years
    """
    try:
        # Create chart calculator service
        calculator_service = get_chart_calculator_service()

        # Return sensitive periods from the service
        sensitive_periods = calculator_service.calculate_sensitive_periods(birth_data)

        # Add additional analysis if available
        if not sensitive_periods or len(sensitive_periods) < 3:
            # Create a basic set of periods based on standard astrological transitions
            birth_date_str = birth_data.get("birth_date", "")
            try:
                birth_year = int(birth_date_str.split("-")[0]) if birth_date_str else 0

                if birth_year > 0:
                    sensitive_periods = [
                        {
                            "age": 7,
                            "year": birth_year + 7,
                            "description": "First Saturn square - early childhood transition",
                            "significance": 0.6
                        },
                        {
                            "age": 14,
                            "year": birth_year + 14,
                            "description": "Second Saturn square - adolescence transition",
                            "significance": 0.7
                        },
                        {
                            "age": 21,
                            "year": birth_year + 21,
                            "description": "First Saturn opposition - early adulthood",
                            "significance": 0.8
                        },
                        {
                            "age": 29,
                            "year": birth_year + 29,
                            "description": "Saturn return - major life transition",
                            "significance": 1.0
                        },
                        {
                            "age": 38,
                            "year": birth_year + 38,
                            "description": "Uranus opposition - midlife transition",
                            "significance": 0.9
                        }
                    ]
            except Exception as e:
                logger.error(f"Failed to calculate basic sensitive periods: {e}")

        return sensitive_periods

    except Exception as e:
        logger.error(f"Error in calculate_sensitive_periods: {e}")
        return []

def calculate_chart_data(birth_date: str, birth_time: str, latitude: float, longitude: float, timezone: str = "UTC") -> Dict[str, Any]:
    """
    Calculate astrological chart data for birth details.

    Args:
        birth_date: Birth date in ISO format (YYYY-MM-DD)
        birth_time: Birth time in 24-hour format (HH:MM or HH:MM:SS)
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: Timezone string (e.g., 'America/New_York')

    Returns:
        Dictionary with calculated chart data
    """
    try:
        # Parse birth date and time
        birth_dt_str = f"{birth_date} {birth_time}"
        birth_dt = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M:%S" if ":" in birth_time else "%Y-%m-%d %H:%M")

        # Set timezone if provided
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                birth_dt = tz.localize(birth_dt)
            except Exception as e:
                logger.warning(f"Error setting timezone: {e}, using UTC")
                birth_dt = pytz.UTC.localize(birth_dt)

        # Get chart service for calculations
        chart_service = get_chart_service()
        if chart_service:
            # Calculate the birth chart
            chart_data = chart_service.calculate_chart(
                birth_date=birth_date,
                birth_time=birth_time,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                chart_type="vedic",
                house_system="whole_sign",
                verify_with_openai=False
            )
            return chart_data if chart_data else {}
        else:
            logger.warning("Chart service not available")
            # Get chart calculator service as fallback
            calculator_service = get_chart_calculator_service()
            # Create birth datetime object for chart calculator
            chart_data = calculator_service.create_chart(
                datetime_obj=birth_dt,
                latitude=latitude,
                longitude=longitude,
                timezone_str=timezone
            )
            return chart_data if chart_data else {}

    except Exception as e:
        logger.error(f"Error calculating chart data: {e}")
        return {}

def calculate_periods(birth_date: str, birth_time: str, latitude: float, longitude: float, timezone: str = "UTC") -> List[Dict[str, Any]]:
    """
    Calculate significant astrological periods based on birth data.

    Args:
        birth_date: Birth date in ISO format (YYYY-MM-DD)
        birth_time: Birth time in 24-hour format
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string

    Returns:
        List of astrological periods with descriptions
    """
    try:
        # Create datetime object from birth date and time
        dt_str = f"{birth_date}T{birth_time}"
        birth_dt = datetime.fromisoformat(dt_str)

        # Set timezone if provided
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                birth_dt = tz.localize(birth_dt)
            except Exception as e:
                logger.warning(f"Error setting timezone: {e}, using UTC")
                birth_dt = pytz.UTC.localize(birth_dt)

        # Convert to UTC for calculations
        birth_dt_utc = birth_dt.astimezone(pytz.UTC)

        # Try to get chart service for calculations
        chart_service = get_chart_service()
        if chart_service:
            # Calculate the birth chart first
            chart = chart_service.calculate_chart(
                birth_date=birth_date,
                birth_time=birth_time,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                chart_type="vedic",
                house_system="whole_sign",
                verify_with_openai=False
            )

            if chart:
                # Extract planetary positions
                planets = chart.get("planets", {})

                # Calculate Dasha periods (major periods)
                # In Vedic astrology, these are typically Vimshottari Dashas

                # Start with Moon position (crucial for Vimshottari Dasha)
                moon_data = planets.get("Moon", {})
                moon_nakshatra_val = moon_data.get("nakshatra_value", 0)

                # Calculate period start dates based on Moon's nakshatra
                # Each nakshatra has a planetary ruler with specific year durations
                ruler_years = {
                    "Sun": 6,
                    "Moon": 10,
                    "Mars": 7,
                    "Rahu": 18,
                    "Jupiter": 16,
                    "Saturn": 19,
                    "Mercury": 17,
                    "Ketu": 7,
                    "Venus": 20
                }

                # Order of dashas based on the starting nakshatra ruler
                dasha_order = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]

                # Calculate the starting dasha lord based on Moon's nakshatra
                # Each nakshatra has a planetary ruler according to Vedic astrology
                nakshatra_rulers = {
                    0: "Ketu",    # Ashwini
                    1: "Venus",   # Bharani
                    2: "Sun",     # Krittika
                    3: "Moon",    # Rohini
                    4: "Mars",    # Mrigashira
                    5: "Rahu",    # Ardra
                    6: "Jupiter", # Punarvasu
                    7: "Saturn",  # Pushya
                    8: "Mercury", # Ashlesha
                    9: "Ketu",    # Magha
                    10: "Venus",  # Purva Phalguni
                    11: "Sun",    # Uttara Phalguni
                    12: "Moon",   # Hasta
                    13: "Mars",   # Chitra
                    14: "Rahu",   # Swati
                    15: "Jupiter",# Vishakha
                    16: "Saturn", # Anuradha
                    17: "Mercury",# Jyeshtha
                    18: "Ketu",   # Mula
                    19: "Venus",  # Purva Ashadha
                    20: "Sun",    # Uttara Ashadha
                    21: "Moon",   # Shravana
                    22: "Mars",   # Dhanishta
                    23: "Rahu",   # Shatabhisha
                    24: "Jupiter",# Purva Bhadrapada
                    25: "Saturn", # Uttara Bhadrapada
                    26: "Mercury" # Revati
                }

                # Determine the nakshatra index (0-26)
                moon_nakshatra_index = int(moon_nakshatra_val * 27 / 360) if moon_nakshatra_val else 0

                # Get the starting dasha lord
                starting_lord = nakshatra_rulers.get(moon_nakshatra_index, "Moon")

                # Find starting position in the dasha order
                start_pos = dasha_order.index(starting_lord)

                # Calculate the consumed portion of the current dasha
                nakshatra_fraction = (moon_nakshatra_val * 27 / 360) - moon_nakshatra_index
                consumed_years = ruler_years[starting_lord] * nakshatra_fraction

                # Calculate birth time for starting point
                current_date = birth_dt_utc - timedelta(days=consumed_years*365.25)

                # Generate the periods
                periods = []
                for i in range(9):  # 9 planetary periods
                    lord_index = (start_pos + i) % 9
                    lord = dasha_order[lord_index]
                    years = ruler_years[lord]

                    period_start = current_date
                    period_end = period_start + timedelta(days=years*365.25)

                    # Format period info
                    periods.append({
                        "name": f"{lord} Dasha",
                        "lord": lord,
                        "start_date": period_start.strftime("%Y-%m-%d"),
                        "end_date": period_end.strftime("%Y-%m-%d"),
                        "duration_years": years,
                        "description": f"{lord} Dasha (major period) lasting {years} years."
                    })

                    current_date = period_end

                return periods

        # Calculate periods based on common planetary cycles
        # This is a simplified version for when the full Vedic calculation isn't available
        current_date = birth_dt_utc
        cycle_data = [
            {"name": "Saturn Return", "years": 29.5, "description": "First Saturn Return - major life transition"},
            {"name": "Jupiter Cycle", "years": 12, "description": "Jupiter cycle - period of growth and expansion"},
            {"name": "Mars Return", "years": 2, "description": "Mars cycle - period of energy and action"},
            {"name": "Venus Cycle", "years": 8, "description": "Venus cycle - relationships and values"},
            {"name": "Mercury Cycle", "years": 1, "description": "Mercury cycle - communication and learning"}
        ]

        periods = []
        for cycle in cycle_data:
            period_start = current_date
            period_end = period_start + timedelta(days=cycle["years"]*365.25)

            periods.append({
                "name": cycle["name"],
                "start_date": period_start.strftime("%Y-%m-%d"),
                "end_date": period_end.strftime("%Y-%m-%d"),
                "duration_years": cycle["years"],
                "description": cycle["description"]
            })

        return periods

    except Exception as e:
        logger.error(f"Error calculating significant periods: {e}")
        return []

class ChartCalculator:
    """
    Class for performing astrological chart calculations needed for questionnaires.
    """

    def calculate_birth_chart(self, birth_date: str, birth_time: str, latitude: float, longitude: float, timezone: str) -> Dict[str, Any]:
        """
        Calculate the birth chart based on birth date and time.

        Args:
            birth_date: Birth date string
            birth_time: Birth time string
            latitude: Birth latitude
            longitude: Birth longitude
            timezone: Birth timezone

        Returns:
            Dictionary with birth chart data
        """
        try:
            # Try to get chart service
            chart_service = get_chart_service()
            if chart_service:
                chart_data = chart_service.calculate_chart(
                    birth_date=birth_date,
                    birth_time=birth_time,
                    latitude=latitude,
                    longitude=longitude,
                    timezone=timezone
                )
                if chart_data:
                    return chart_data
        except Exception as e:
            logger.error(f"Error calculating birth chart: {e}")

        # Return empty dict if calculation fails
        return {}

    def get_house_data(self, house_number: int, birth_chart: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get data for a specific astrological house.

        Args:
            house_number: Number of the house
            birth_chart: Dictionary with birth chart data

        Returns:
            Dictionary with house data
        """
        try:
            houses = birth_chart.get("houses", [])
            if houses and 0 <= house_number - 1 < len(houses):
                return houses[house_number - 1]
        except Exception as e:
            logger.error(f"Error getting house data: {e}")

        return {}

    def get_angle_data(self, angle: int, birth_chart: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get data for a specific astrological angle.

        Args:
            angle: Angle in degrees
            birth_chart: Dictionary with birth chart data

        Returns:
            Dictionary with angle data
        """
        try:
            angles = birth_chart.get("angles", {})
            if angles:
                # Find the closest angle
                closest_angle = min(angles.keys(), key=lambda x: abs(int(x) - angle))
                return angles.get(closest_angle, {})
        except Exception as e:
            logger.error(f"Error getting angle data: {e}")

        return {}

    def calculate_chart_data(self, birth_date: str, birth_time: str, latitude: float, longitude: float, timezone: str = "UTC") -> Dict[str, Any]:
        """
        Calculate basic chart data for astrological analysis.

        Args:
            birth_date: Birth date in YYYY-MM-DD format
            birth_time: Birth time in HH:MM:SS format
            latitude: Birth latitude
            longitude: Birth longitude
            timezone: Birth timezone (default: UTC)

        Returns:
            Dictionary with chart data
        """
        # Try to get chart service for chart calculation
        chart_data = {}
        try:
            chart_service = get_chart_service()
            if chart_service:
                # Create birth details
                birth_details = {
                    "birth_date": birth_date,
                    "birth_time": birth_time,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": timezone
                }

                # Try to calculate chart
                chart = chart_service.calculate_chart(
                    birth_date=birth_date,
                    birth_time=birth_time,
                    latitude=latitude,
                    longitude=longitude,
                    timezone=timezone,
                    chart_type="vedic",
                    house_system="whole_sign",
                    verify_with_openai=False
                )
                if chart:
                    chart_data = chart
        except Exception as e:
            logger.warning(f"Error calculating chart data with chart service: {e}")

            # Try using chart calculator directly
            try:
                # Format birth date and time
                birth_dt_str = f"{birth_date} {birth_time}"
                birth_dt = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M:%S" if len(birth_time.split(':')) > 2 else "%Y-%m-%d %H:%M")

                # Create GeoPos object for chart calculator
                calculator_service = get_chart_calculator_service()

                # Use chart calculator to create chart
                chart = calculator_service.create_chart(
                    datetime_obj=birth_dt,
                    latitude=latitude,
                    longitude=longitude,
                    timezone_str=timezone
                )
                if chart:
                    chart_data = chart
            except Exception as calc_error:
                logger.warning(f"Error calculating chart data with chart calculator: {calc_error}")

        # Return whatever data we have, even if empty
        return chart_data

    def calculate_ascendant_changes(
        self,
        birth_date: str,
        times: List[datetime],
        latitude: float,
        longitude: float,
        timezone: str = "UTC"
    ) -> List[Dict[str, Any]]:
        """
        Calculate how the ascendant changes at different times.

        Args:
            birth_date: Birth date string
            times: List of datetime objects to calculate ascendants for
            latitude: Birth latitude
            longitude: Birth longitude
            timezone: Birth timezone

        Returns:
            List of ascendant data for each time
        """
        results = []
        try:
            # Try to get chart service
            chart_service = get_chart_service()
            calculator_service = get_chart_calculator_service()

            for time in times:
                time_str = time.strftime("%H:%M:%S")
                ascendant_data = {"time": time_str, "ascendant": None, "ascendant_degree": None}

                try:
                    if chart_service:
                        # Calculate full chart
                        chart = chart_service.calculate_chart(
                            birth_date=birth_date,
                            birth_time=time_str,
                            latitude=latitude,
                            longitude=longitude,
                            timezone=timezone,
                            chart_type="vedic",
                            house_system="whole_sign",
                            verify_with_openai=False
                        )

                        if chart and "ascendant" in chart:
                            ascendant_data["ascendant"] = chart["ascendant"].get("sign")
                            ascendant_data["ascendant_degree"] = chart["ascendant"].get("degree")
                    else:
                        # Try using chart calculator directly
                        birth_dt_str = f"{birth_date} {time_str}"
                        birth_dt = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M:%S")

                        # Use chart calculator service
                        chart = calculator_service.create_chart(
                            datetime_obj=birth_dt,
                            latitude=latitude,
                            longitude=longitude,
                            timezone_str=timezone
                        )

                        if chart and "angles" in chart and "Asc" in chart["angles"]:
                            ascendant_data["ascendant"] = chart["angles"]["Asc"].get("sign")
                            ascendant_data["ascendant_degree"] = chart["angles"]["Asc"].get("degree")
                except Exception as time_error:
                    logger.warning(f"Error calculating ascendant for time {time_str}: {time_error}")

                results.append(ascendant_data)
        except Exception as e:
            logger.error(f"Error calculating ascendant changes: {e}")

        return results

    def format_chart_data_for_prompt(self, chart_data: Dict[str, Any]) -> str:
        """
        Format chart data for inclusion in an AI prompt.

        Args:
            chart_data: Dictionary with chart data

        Returns:
            Formatted string with chart data
        """
        if not chart_data:
            return "No chart data available."

        formatted_text = []

        # Add ascendant information
        ascendant = chart_data.get("ascendant", {})
        if ascendant:
            asc_sign = ascendant.get("sign", "Unknown")
            asc_degree = ascendant.get("degree", 0)
            formatted_text.append(f"Ascendant: {asc_sign} {asc_degree}°")

        # Add planet information
        planets = chart_data.get("planets", {})
        if planets:
            formatted_text.append("\nPlanets:")
            for planet, data in planets.items():
                sign = data.get("sign", "Unknown")
                degree = data.get("degree", 0)
                house = data.get("house", "Unknown")

                # Format retrograde status
                retrograde = " (R)" if data.get("retrograde", False) else ""

                # Add formatted planet info
                formatted_text.append(f"- {planet}: {sign} {degree}° in House {house}{retrograde}")

        # Add house information
        houses = chart_data.get("houses", [])
        if houses:
            formatted_text.append("\nHouses:")
            for i, house in enumerate(houses):
                house_num = i + 1
                sign = house.get("sign", "Unknown")
                degree = house.get("degree", 0)
                formatted_text.append(f"- House {house_num}: {sign} {degree}°")

        # Join all sections with newlines
        return "\n".join(formatted_text)


# Create a singleton instance
chart_calculator_instance = ChartCalculator()

# Function to get the chart calculator instance
def get_chart_calculator():
    """Get the chart calculator instance."""
    return chart_calculator_instance
