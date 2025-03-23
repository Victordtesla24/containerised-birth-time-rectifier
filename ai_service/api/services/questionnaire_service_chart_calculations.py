"""
Chart calculation module for the questionnaire service.

This module contains functions for calculating astrological charts and related data.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# logger initialization
logger = logging.getLogger(__name__)

from ai_service.api.services.questionnaire_service_chart_calculator import chart_calculator
from ai_service.services import get_chart_service

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
    # This would normally calculate dasha periods, transits, etc.
    # For now, return a placeholder
    try:
        # Parse birth date and time
        birth_dt_str = f"{birth_date} {birth_time}"
        birth_dt = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M")

        # Create some placeholder periods (would be calculated using proper astrological algorithms)
        periods = []

        # Add some sample periods
        current_date = birth_dt
        for i in range(5):
            period_start = current_date + timedelta(days=i*365)
            period_end = period_start + timedelta(days=365)

            periods.append({
                "name": f"Period {i+1}",
                "start_date": period_start.strftime("%Y-%m-%d"),
                "end_date": period_end.strftime("%Y-%m-%d"),
                "description": f"Sample period {i+1} description."
            })

        return periods
    except Exception as e:
        logger.error(f"Error calculating significant periods: {e}")
        return []

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
