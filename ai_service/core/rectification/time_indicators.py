"""
Time indicators module for birth time rectification.

This module provides functionality for extracting time-sensitive astrological
indicators from a birth chart, which can be used for refining birth times.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import math

logger = logging.getLogger(__name__)

# Constants for time sensitivity
TIME_SENSITIVITY = {
    "Ascendant": 1.0,          # Most sensitive (~4 min per degree)
    "Midheaven": 0.95,         # Very sensitive (~4 min per degree)
    "Moon": 0.7,               # Sensitive (~2 degrees per day)
    "Sun": 0.05,               # Not very sensitive (1 degree per day)
    "Mercury": 0.2,            # Somewhat sensitive (variable speed)
    "Venus": 0.15,             # Low sensitivity (slower moving)
    "Mars": 0.1,               # Low sensitivity (slower moving)
    "Jupiter": 0.05,           # Very low sensitivity (very slow moving)
    "Saturn": 0.03,            # Extremely low sensitivity (very slow moving)
    "Houses": 0.85,            # Very sensitive to time changes
    "Aspects": 0.75            # Sensitive to time changes
}

def extract_birth_time_indicators(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract time-sensitive indicators from a birth chart.

    This function analyzes a birth chart and extracts elements that
    are sensitive to changes in birth time, which can be used for
    birth time rectification.

    Args:
        chart_data: The birth chart data to analyze

    Returns:
        Dictionary of time indicators and their sensitivity values
    """
    indicators = {
        "ascendant": {},
        "midheaven": {},
        "lunar_position": {},
        "house_cusps": {},
        "key_aspects": [],
        "sensitive_axes": {}
    }

    # Extract ascendant (most sensitive to time)
    if "ascendant" in chart_data:
        asc_data = chart_data["ascendant"]
        indicators["ascendant"] = {
            "sign": asc_data.get("sign", ""),
            "degree": asc_data.get("degree", 0),
            "longitude": asc_data.get("longitude", 0),
            "sensitivity": TIME_SENSITIVITY["Ascendant"]
        }

    # Extract midheaven
    if "angles" in chart_data and "MC" in chart_data["angles"]:
        mc_data = chart_data["angles"]["MC"]
        indicators["midheaven"] = {
            "sign": mc_data.get("sign", ""),
            "degree": mc_data.get("degree", 0),
            "longitude": mc_data.get("longitude", 0),
            "sensitivity": TIME_SENSITIVITY["Midheaven"]
        }

    # Extract Moon position (second most sensitive to time)
    planets = chart_data.get("planets", {})
    if isinstance(planets, list):
        # Convert list to dictionary if needed
        planets_dict = {}
        for planet in planets:
            if isinstance(planet, dict) and "name" in planet:
                planets_dict[planet["name"]] = planet
        planets = planets_dict

    if "Moon" in planets:
        moon_data = planets["Moon"]
        indicators["lunar_position"] = {
            "sign": moon_data.get("sign", ""),
            "degree": moon_data.get("degree", 0),
            "longitude": moon_data.get("longitude", 0),
            "house": moon_data.get("house", 0),
            "sensitivity": TIME_SENSITIVITY["Moon"]
        }

    # Extract house cusps (sensitive to time)
    houses = chart_data.get("houses", {})
    house_indicators = {}

    # Handle houses whether they're a dict or list
    if isinstance(houses, list):
        for house in houses:
            if isinstance(house, dict) and "house" in house:
                house_num = house["house"]
                house_indicators[str(house_num)] = {
                    "longitude": house.get("longitude", 0),
                    "sign": house.get("sign", ""),
                    "sensitivity": TIME_SENSITIVITY["Houses"]
                }
    else:
        for house_num, house_data in houses.items():
            if isinstance(house_data, dict):
                house_indicators[str(house_num)] = {
                    "longitude": house_data.get("longitude", 0),
                    "sign": house_data.get("sign", ""),
                    "sensitivity": TIME_SENSITIVITY["Houses"]
                }
            else:
                # Simple longitude value
                house_indicators[str(house_num)] = {
                    "longitude": float(house_data),
                    "sign": get_sign_from_longitude(float(house_data)),
                    "sensitivity": TIME_SENSITIVITY["Houses"]
                }

    indicators["house_cusps"] = house_indicators

    # Extract key aspects that would change with time
    aspects = chart_data.get("aspects", [])
    key_aspects = []

    for aspect in aspects:
        # Focus on aspects involving fast-moving points
        planet1 = aspect.get("planet1", "")
        planet2 = aspect.get("planet2", "")

        # Calculate the combined sensitivity of the aspect
        sensitivity1 = TIME_SENSITIVITY.get(planet1, 0.1)
        sensitivity2 = TIME_SENSITIVITY.get(planet2, 0.1)

        # Aspects involving fast-moving points like Ascendant, MC, or Moon
        # are more sensitive to time changes
        if planet1 in ["Ascendant", "Midheaven", "Moon"] or planet2 in ["Ascendant", "Midheaven", "Moon"]:
            combined_sensitivity = (sensitivity1 + sensitivity2) / 2

            key_aspects.append({
                "planet1": planet1,
                "planet2": planet2,
                "type": aspect.get("type", ""),
                "orb": aspect.get("orb", 0),
                "sensitivity": combined_sensitivity
            })

    # Sort aspects by sensitivity
    key_aspects.sort(key=lambda x: x["sensitivity"], reverse=True)
    indicators["key_aspects"] = key_aspects[:5]  # Keep only top 5 most sensitive

    return indicators

def calculate_time_sensitivity(chart_data: Dict[str, Any]) -> float:
    """
    Calculate overall time sensitivity score for a chart.

    Higher values indicate elements that change rapidly with time.

    Args:
        chart_data: The birth chart data

    Returns:
        Overall time sensitivity score (0.0-1.0)
    """
    indicators = extract_birth_time_indicators(chart_data)

    # Calculate weighted sensitivity score
    total_weight = 0
    weighted_sum = 0

    # Ascendant weight
    if indicators["ascendant"]:
        weighted_sum += indicators["ascendant"]["sensitivity"] * 10
        total_weight += 10

    # Midheaven weight
    if indicators["midheaven"]:
        weighted_sum += indicators["midheaven"]["sensitivity"] * 8
        total_weight += 8

    # Lunar position weight
    if indicators["lunar_position"]:
        weighted_sum += indicators["lunar_position"]["sensitivity"] * 7
        total_weight += 7

    # House cusps weight
    if indicators["house_cusps"]:
        house_sensitivity = sum(house["sensitivity"] for house in indicators["house_cusps"].values())
        avg_house_sensitivity = house_sensitivity / len(indicators["house_cusps"]) if indicators["house_cusps"] else 0
        weighted_sum += avg_house_sensitivity * 6
        total_weight += 6

    # Key aspects weight
    if indicators["key_aspects"]:
        aspect_sensitivity = sum(aspect["sensitivity"] for aspect in indicators["key_aspects"])
        avg_aspect_sensitivity = aspect_sensitivity / len(indicators["key_aspects"]) if indicators["key_aspects"] else 0
        weighted_sum += avg_aspect_sensitivity * 5
        total_weight += 5

    # Calculate overall sensitivity
    overall_sensitivity = weighted_sum / total_weight if total_weight > 0 else 0.5

    return overall_sensitivity

def get_sign_from_longitude(longitude: float) -> str:
    """
    Get the zodiac sign for a longitude value.

    Args:
        longitude: Celestial longitude in degrees

    Returns:
        Zodiac sign name
    """
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    sign_index = int(longitude / 30) % 12
    return signs[sign_index]

def estimate_time_change_impact(
    chart_data: Dict[str, Any],
    minutes_change: float
) -> Dict[str, Any]:
    """
    Estimate the impact of a change in birth time on chart elements.

    Args:
        chart_data: Original chart data
        minutes_change: Minutes to adjust the birth time

    Returns:
        Dictionary with predicted changes to chart elements
    """
    # Approximate changes based on standard rates of motion
    # Ascendant moves ~1 degree / 4 minutes
    asc_change_deg = minutes_change / 4

    # Midheaven moves at a similar but variable rate
    mc_change_deg = minutes_change / 4

    # Moon moves ~12-15 degrees per day, or ~0.5-0.625 degrees per hour
    moon_change_deg = minutes_change * (0.5 / 60)

    # Houses move with the Ascendant but at different rates

    # Create predicted changes
    impact = {
        "ascendant_change": asc_change_deg,
        "midheaven_change": mc_change_deg,
        "moon_change": moon_change_deg,
        "house_changes": {},
        "sign_changes": [],
        "aspect_changes": []
    }

    # Check for sign changes
    ascendant = chart_data.get("ascendant", {})
    if ascendant:
        asc_longitude = ascendant.get("longitude", 0)
        new_asc_longitude = (asc_longitude + asc_change_deg) % 360
        old_sign = get_sign_from_longitude(asc_longitude)
        new_sign = get_sign_from_longitude(new_asc_longitude)

        if old_sign != new_sign:
            impact["sign_changes"].append({
                "point": "Ascendant",
                "old_sign": old_sign,
                "new_sign": new_sign,
                "significance": 1.0
            })

    # Calculate house changes
    for house_num in range(1, 13):
        # Houses move at different rates relative to the Ascendant
        # This is a simplified model; in reality, it depends on latitude and other factors
        if house_num in [1, 7]:
            # These move at the same rate as Ascendant
            house_change = asc_change_deg
        elif house_num in [10, 4]:
            # These move at the same rate as Midheaven
            house_change = mc_change_deg
        else:
            # Other houses move at intermediate rates
            house_change = (asc_change_deg + mc_change_deg) / 2

        impact["house_changes"][str(house_num)] = house_change

    return impact
