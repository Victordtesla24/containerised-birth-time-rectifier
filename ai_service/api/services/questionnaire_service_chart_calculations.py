"""
Chart calculation module for the questionnaire service.

This module contains functions for calculating astrological charts and related data.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pytz

# Import necessary services
from ai_service.api.services.chart import get_chart_service
from ai_service.api.services.questionnaire_service_chart_calculator import chart_calculator

# logger initialization
logger = logging.getLogger(__name__)

def calculate_sensitive_periods(birth_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calculate astrologically sensitive periods in a person's life.

    This function calculates periods where planetary transits and dashas
    (planetary periods) would have significant effects on life events.

    Args:
        birth_data: Birth details including date, time, and location

    Returns:
        List of sensitive periods with dates and descriptions

    Raises:
        ValueError: If birth data is incomplete or calculation fails
    """
    # Validate birth data
    if not birth_data:
        raise ValueError("Birth data is required to calculate sensitive periods")

    required_fields = ["birth_date", "birth_time", "latitude", "longitude", "timezone"]
    missing_fields = [field for field in required_fields if field not in birth_data]
    if missing_fields:
        raise ValueError(f"Missing required birth data fields: {', '.join(missing_fields)}")

    try:
        # Extract birth date components
        birth_date_str = birth_data.get("birth_date", "")
        birth_time_str = birth_data.get("birth_time", "")

        # Create datetime object
        birth_dt_str = f"{birth_date_str}T{birth_time_str}"
        birth_dt = datetime.fromisoformat(birth_dt_str)

        # Extract location
        latitude = float(birth_data.get("latitude", 0))
        longitude = float(birth_data.get("longitude", 0))

        # Calculate planetary positions for birth time
        from ai_service.core.rectification.vedic_calculation import calculate_chart

        chart_data = calculate_chart(
            birth_dt,
            latitude,
            longitude,
            birth_data.get("timezone", "UTC")
        )

        if not chart_data or "planets" not in chart_data:
            raise ValueError("Failed to calculate birth chart data")

        # Calculate dasha periods
        from ai_service.core.rectification.methods.dasha_analysis import calculate_dasha_periods

        dasha_periods = calculate_dasha_periods(chart_data)

        if not dasha_periods:
            raise ValueError("Failed to calculate dasha periods")

        # Calculate transits
        from ai_service.core.rectification.methods.transit_analysis import find_significant_transits

        transits = find_significant_transits(chart_data, years_range=50)

        if not transits:
            raise ValueError("Failed to calculate significant transits")

        # Combine and filter sensitive periods
        sensitive_periods = []

        # Add dasha periods
        for period in dasha_periods:
            sensitive_periods.append({
                "type": "dasha",
                "start_date": period.get("start_date"),
                "end_date": period.get("end_date"),
                "planet": period.get("planet"),
                "sub_planet": period.get("sub_planet", ""),
                "description": period.get("description", ""),
                "significance": period.get("significance", 0.5)
            })

        # Add transit periods
        for transit in transits:
            sensitive_periods.append({
                "type": "transit",
                "date": transit.get("date"),
                "planets": transit.get("planets", []),
                "aspect": transit.get("aspect", ""),
                "description": transit.get("description", ""),
                "significance": transit.get("significance", 0.5)
            })

        # Sort by date
        sensitive_periods.sort(key=lambda x: x.get("start_date", x.get("date", "")))

        return sensitive_periods

    except Exception as e:
        logger.error(f"Error calculating sensitive periods: {e}")
        raise ValueError(f"Failed to calculate sensitive periods: {str(e)}")

def _calculate_significant_periods(self, birth_date: str, birth_time: str, timezone: str) -> List[Dict[str, Any]]:
    """
    Calculate significant astrological periods based on birth date and time.

    Args:
        birth_date: Birth date string (YYYY-MM-DD)
        birth_time: Birth time string (HH:MM)
        timezone: Timezone string

    Returns:
        List of significant periods with start/end dates and descriptions
    """
    try:
        # Parse birth date and time
        birth_dt_str = f"{birth_date} {birth_time}"
        birth_dt = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M")

        # Convert to timezone-aware datetime
        local_tz = pytz.timezone(timezone)
        birth_dt_tz = local_tz.localize(birth_dt)

        # Convert to UTC for calculations
        birth_dt_utc = birth_dt_tz.astimezone(pytz.UTC)

        # Try to get chart service for calculations
        chart_service = get_chart_service()
        if chart_service:
            # Calculate the birth chart first
            chart = chart_service.calculate_chart(
                birth_date=birth_date,
                birth_time=birth_time,
                latitude=0,  # We'll set these in the actual request
                longitude=0, # We'll set these in the actual request
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

        # If chart service fails or isn't available, use a simpler calculation method
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
        # Don't return an empty list, as that might be interpreted as a mockup
        # Instead, raise the exception to be handled by the caller
        raise RuntimeError(f"Failed to calculate significant periods: {e}")

def _calculate_birth_chart(self, birth_date: str, birth_time: str, latitude: float, longitude: float, timezone: str) -> Dict[str, Any]:
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
    # This method would be implemented to calculate the birth chart using astrological algorithms
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

def _get_house_data(self, house_number: int, birth_chart: Dict[str, Any]) -> Dict[str, Any]:
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

def _get_angle_data(self, angle: int, birth_chart: Dict[str, Any]) -> Dict[str, Any]:
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

def _calculate_chart_data(self, birth_date: str, birth_time: str, latitude: float, longitude: float, timezone: str = "UTC") -> Dict[str, Any]:
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
            birth_dt = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M")

            # Create GeoPos object (this is simplified, actual implementation would vary)
            geo_pos = {
                "latitude": latitude,
                "longitude": longitude,
                "altitude": 0,
                "timezone": timezone
            }

            # Use chart calculator to create chart
            chart = chart_calculator.create_chart(birth_dt, geo_pos)
            if chart:
                chart_data = chart
        except Exception as calc_error:
            logger.warning(f"Error calculating chart data with chart calculator: {calc_error}")

    # Return whatever data we have, even if empty
    return chart_data

def _calculate_ascendant_changes(
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

                    # Create GeoPos object
                    geo_pos = {
                        "latitude": latitude,
                        "longitude": longitude,
                        "altitude": 0,
                        "timezone": timezone
                    }

                    # Use chart calculator to create chart
                    chart = chart_calculator.create_chart(birth_dt, geo_pos)

                    if chart and "angles" in chart and "Asc" in chart["angles"]:
                        ascendant_data["ascendant"] = chart["angles"]["Asc"].get("sign")
                        ascendant_data["ascendant_degree"] = chart["angles"]["Asc"].get("degree")
            except Exception as time_error:
                logger.warning(f"Error calculating ascendant for time {time_str}: {time_error}")

            results.append(ascendant_data)
    except Exception as e:
        logger.error(f"Error calculating ascendant changes: {e}")

    return results

def _format_chart_data_for_prompt(self, chart_data: Dict[str, Any]) -> str:
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
