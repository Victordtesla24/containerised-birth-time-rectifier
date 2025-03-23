"""
Utility functions for chart service.

This module provides utility functions used by the chart service.
"""

import logging
import math
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

def calculate_arc_difference(long1: float, long2: float) -> float:
    """
    Calculate the smallest arc difference between two longitudes on a 360-degree circle.
    This method accounts for cases where longitudes cross the 0°/360° boundary.

    Args:
        long1: First longitude in degrees
        long2: Second longitude in degrees

    Returns:
        Smallest arc difference between the longitudes in degrees (0-180)
    """
    # Ensure longitudes are within 0-360 range
    long1 = long1 % 360.0
    long2 = long2 % 360.0

    # Calculate direct difference
    direct_diff = abs(long1 - long2)

    # Calculate difference going the other way around the circle
    other_way = 360.0 - direct_diff

    # Return the smaller of the two paths
    return min(direct_diff, other_way)

def get_sign_from_longitude(longitude: float) -> str:
    """Get zodiac sign from longitude value."""
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    sign_index = int(longitude / 30) % 12
    return signs[sign_index]

def get_house_meaning(house_num: int) -> str:
    """Get the standard meaning of a house in astrology."""
    house_meanings = {
        1: "Identity, appearance, and self-expression",
        2: "Values, possessions, and resources",
        3: "Communication, learning, and siblings",
        4: "Home, family, and emotional foundation",
        5: "Creativity, pleasure, and children",
        6: "Work, health, and service",
        7: "Partnerships, contracts, and open enemies",
        8: "Joint resources, transformation, and sexuality",
        9: "Higher education, philosophy, and foreign travel",
        10: "Career, reputation, and public standing",
        11: "Friends, groups, and hopes",
        12: "Spirituality, hidden matters, and self-undoing"
    }
    return house_meanings.get(house_num, f"House {house_num}")

def determine_house_for_longitude(houses: List[Any], longitude: float) -> int:
    """
    Determine which house contains a given longitude.

    Args:
        houses: List of house cusps (either as longitudes or dicts)
        longitude: Longitude to check

    Returns:
        House number (1-12)
    """
    if not houses or len(houses) < 12:
        return 1  # Default if house data is incomplete

    # Normalize longitude
    longitude = longitude % 360

    # Extract house cusp longitudes based on data format
    house_longitudes = []
    for i, house in enumerate(houses):
        if isinstance(house, dict):
            house_longitudes.append(house.get("longitude", 0))
        elif isinstance(house, (int, float)):
            house_longitudes.append(house)
        else:
            # Default to 30 degree increments if invalid data
            house_longitudes.append((i * 30) % 360)

    # Pair house numbers with their longitudes
    house_pairs = [(i+1, house_longitudes[i]) for i in range(12)]

    # Sort by longitude for easier comparison
    house_pairs.sort(key=lambda x: x[1])

    # Find which house contains the longitude
    for i in range(len(house_pairs)):
        current_cusp = house_pairs[i][1]
        next_cusp = house_pairs[(i+1) % 12][1]

        # Handle case where house spans 0 degrees
        if next_cusp < current_cusp:
            if longitude >= current_cusp or longitude < next_cusp:
                return house_pairs[i][0]
        # Normal case
        elif current_cusp <= longitude < next_cusp:
            return house_pairs[i][0]

    # Default to house 1 if not found
    return 1

def get_planet_rulerships(planet_name: str, chart_data: Dict[str, Any]) -> List[int]:
    """Get houses ruled by a planet in the chart."""
    # Traditional rulership assignments
    sign_rulers = {
        "Aries": "mars",
        "Taurus": "venus",
        "Gemini": "mercury",
        "Cancer": "moon",
        "Leo": "sun",
        "Virgo": "mercury",
        "Libra": "venus",
        "Scorpio": "mars",
        "Sagittarius": "jupiter",
        "Capricorn": "saturn",
        "Aquarius": "saturn",
        "Pisces": "jupiter"
    }

    # Get house signs from chart data
    houses = chart_data.get("houses", [])
    if not houses:
        return []

    # Convert houses to sign information
    house_signs = []
    for i, house in enumerate(houses):
        if isinstance(house, dict) and "sign" in house:
            house_signs.append(house["sign"])
        elif isinstance(house, (int, float)):
            # Calculate sign from longitude
            sign_index = int(house / 30) % 12
            signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                     "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
            house_signs.append(signs[sign_index])

    # Find houses ruled by this planet
    ruled_houses = []
    for i, sign in enumerate(house_signs):
        if sign_rulers.get(sign) == planet_name.lower():
            ruled_houses.append(i + 1)  # House numbers are 1-based

    return ruled_houses

def is_day_chart(chart_data: Dict[str, Any]) -> bool:
    """
    Determine if a chart is a day chart (Sun above horizon) or night chart.

    Args:
        chart_data: Chart data with Sun position

    Returns:
        True if day chart, False if night chart
    """
    # Get Sun and Ascendant positions
    planets = chart_data.get("planets", {})
    sun_data = planets.get("sun", {})

    if not sun_data:
        # Default to day chart if no Sun data
        return True

    # Get Sun's house placement
    sun_house = sun_data.get("house", 0)

    # Day chart if Sun is in houses 7-12, night chart if in houses 1-6
    # This is a simplified approach; a more accurate approach would
    # check if the Sun is above or below the horizon
    return sun_house >= 7
