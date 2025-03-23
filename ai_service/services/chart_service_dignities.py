"""
Dignity calculation utilities for chart service.

This module provides functionality for calculating planetary dignities and strengths.
"""

import logging
from typing import Dict, Any, List, Optional, Union

from ai_service.services.chart_service_utils import is_day_chart

logger = logging.getLogger(__name__)

def calculate_dignities(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate planetary dignities and debilities according to traditional astrological principles.

    Args:
        chart_data: Chart data with planetary positions

    Returns:
        Dictionary of planetary dignity data
    """
    # Define traditional rulership, exaltation, fall and detriment
    ESSENTIAL_DIGNITIES = {
        "sun": {
            "rulership": ["Leo"],
            "exaltation": ["Aries"],
            "detriment": ["Aquarius"],
            "fall": ["Libra"]
        },
        "moon": {
            "rulership": ["Cancer"],
            "exaltation": ["Taurus"],
            "detriment": ["Capricorn"],
            "fall": ["Scorpio"]
        },
        "mercury": {
            "rulership": ["Gemini", "Virgo"],
            "exaltation": ["Virgo"],  # Some traditions use Virgo or Aquarius
            "detriment": ["Sagittarius", "Pisces"],
            "fall": ["Pisces"]
        },
        "venus": {
            "rulership": ["Taurus", "Libra"],
            "exaltation": ["Pisces"],
            "detriment": ["Scorpio", "Aries"],
            "fall": ["Virgo"]
        },
        "mars": {
            "rulership": ["Aries", "Scorpio"],
            "exaltation": ["Capricorn"],
            "detriment": ["Libra", "Taurus"],
            "fall": ["Cancer"]
        },
        "jupiter": {
            "rulership": ["Sagittarius", "Pisces"],
            "exaltation": ["Cancer"],
            "detriment": ["Gemini", "Virgo"],
            "fall": ["Capricorn"]
        },
        "saturn": {
            "rulership": ["Capricorn", "Aquarius"],
            "exaltation": ["Libra"],
            "detriment": ["Cancer", "Leo"],
            "fall": ["Aries"]
        },
        "uranus": {
            "rulership": ["Aquarius"],
            "exaltation": ["Scorpio"],
            "detriment": ["Leo"],
            "fall": ["Taurus"]
        },
        "neptune": {
            "rulership": ["Pisces"],
            "exaltation": ["Cancer"],
            "detriment": ["Virgo"],
            "fall": ["Capricorn"]
        },
        "pluto": {
            "rulership": ["Scorpio"],
            "exaltation": ["Aries"],
            "detriment": ["Taurus"],
            "fall": ["Libra"]
        }
    }

    # Define triplicity rulers (by element)
    TRIPLICITY_RULERS = {
        "fire": ["sun", "jupiter", "saturn"],  # Day, Night, Participating
        "earth": ["venus", "moon", "mars"],
        "air": ["saturn", "mercury", "jupiter"],
        "water": ["mars", "venus", "moon"]
    }

    # Define sign elements
    SIGN_ELEMENTS = {
        "Aries": "fire", "Leo": "fire", "Sagittarius": "fire",
        "Taurus": "earth", "Virgo": "earth", "Capricorn": "earth",
        "Gemini": "air", "Libra": "air", "Aquarius": "air",
        "Cancer": "water", "Scorpio": "water", "Pisces": "water"
    }

    # Define terms (bounds) - simplified version
    TERMS = {
        # Each sign has 5 terms, roughly dividing the 30 degrees
        # Format: [planet, start_degree, end_degree]
        "Aries": [
            ["jupiter", 0, 6],
            ["venus", 6, 14],
            ["mercury", 14, 21],
            ["mars", 21, 26],
            ["saturn", 26, 30]
        ],
        # Similar definitions for other signs would be included here
    }

    # Define faces (decans) - each sign has 3 faces of 10 degrees each
    FACES = {
        "Aries": ["mars", "sun", "venus"],
        "Taurus": ["mercury", "moon", "saturn"],
        "Gemini": ["jupiter", "mars", "sun"],
        "Cancer": ["venus", "mercury", "moon"],
        "Leo": ["saturn", "jupiter", "mars"],
        "Virgo": ["sun", "venus", "mercury"],
        "Libra": ["moon", "saturn", "jupiter"],
        "Scorpio": ["mars", "sun", "venus"],
        "Sagittarius": ["mercury", "moon", "saturn"],
        "Capricorn": ["jupiter", "mars", "sun"],
        "Aquarius": ["venus", "mercury", "moon"],
        "Pisces": ["saturn", "jupiter", "mars"]
    }

    # Initialize result dictionary
    dignities = {}

    # Get planets from chart data
    planets = chart_data.get("planets", {})
    if not planets:
        return dignities

    # Determine if it's a day or night chart
    is_daytime = is_day_chart(chart_data)

    # Calculate dignities for each planet
    for planet_name, planet_data in planets.items():
        # Skip if not a traditional planet
        if planet_name.lower() not in ESSENTIAL_DIGNITIES:
            continue

        # Extract sign and degree
        sign = planet_data.get("sign", "")
        longitude = planet_data.get("longitude", 0)
        degree = longitude % 30

        # Skip if invalid sign
        if not sign:
            continue

        # Initialize dignity scores
        dignity_info = {
            "status": "peregrine",  # Default status
            "essential_dignity": "peregrine",
            "score": 0,
            "explanation": [],
            "rulership": False,
            "exaltation": False,
            "detriment": False,
            "fall": False,
            "triplicity": False,
            "term": False,
            "face": False
        }

        # Check essential dignities
        planet_dignities = ESSENTIAL_DIGNITIES.get(planet_name.lower(), {})

        # Check rulership
        if sign in planet_dignities.get("rulership", []):
            dignity_info["rulership"] = True
            dignity_info["score"] += 5
            dignity_info["explanation"].append(f"{planet_name.capitalize()} is in its rulership in {sign}")
            dignity_info["essential_dignity"] = "rulership"
            dignity_info["status"] = "dignified by rulership"

        # Check exaltation
        if sign in planet_dignities.get("exaltation", []):
            dignity_info["exaltation"] = True
            dignity_info["score"] += 4
            dignity_info["explanation"].append(f"{planet_name.capitalize()} is exalted in {sign}")
            if dignity_info["score"] < 4:  # Only upgrade if not already in rulership
                dignity_info["essential_dignity"] = "exaltation"
                dignity_info["status"] = "dignified by exaltation"

        # Check detriment
        if sign in planet_dignities.get("detriment", []):
            dignity_info["detriment"] = True
            dignity_info["score"] -= 5
            dignity_info["explanation"].append(f"{planet_name.capitalize()} is in detriment in {sign}")
            dignity_info["essential_dignity"] = "detriment"
            dignity_info["status"] = "debilitated by detriment"

        # Check fall
        if sign in planet_dignities.get("fall", []):
            dignity_info["fall"] = True
            dignity_info["score"] -= 4
            dignity_info["explanation"].append(f"{planet_name.capitalize()} is in fall in {sign}")
            if dignity_info["score"] > -5:  # Only downgrade if not already in detriment
                dignity_info["essential_dignity"] = "fall"
                dignity_info["status"] = "debilitated by fall"

        # Check triplicity rulership
        element = SIGN_ELEMENTS.get(sign)
        if element:
            triplicity_rulers = TRIPLICITY_RULERS.get(element, [])
            triplicity_index = 0 if is_daytime else 1  # Day or night ruler

            if planet_name.lower() == triplicity_rulers[triplicity_index]:
                dignity_info["triplicity"] = True
                dignity_info["score"] += 3
                dignity_info["explanation"].append(
                    f"{planet_name.capitalize()} is a {'day' if is_daytime else 'night'} triplicity ruler in {sign}"
                )
                if not any([dignity_info["rulership"], dignity_info["exaltation"]]):
                    dignity_info["status"] = "dignified by triplicity"

        # Check term rulership
        if sign in TERMS:
            for term in TERMS[sign]:
                if planet_name.lower() == term[0] and term[1] <= degree < term[2]:
                    dignity_info["term"] = True
                    dignity_info["score"] += 2
                    dignity_info["explanation"].append(
                        f"{planet_name.capitalize()} is in its own terms in {sign} at {degree:.1f}°"
                    )
                    if not any([dignity_info["rulership"], dignity_info["exaltation"], dignity_info["triplicity"]]):
                        dignity_info["status"] = "dignified by term"

        # Check face (decan)
        if sign in FACES:
            face_index = min(2, int(degree / 10))  # 0, 1, or 2 for the three decans
            if planet_name.lower() == FACES[sign][face_index]:
                dignity_info["face"] = True
                dignity_info["score"] += 1
                dignity_info["explanation"].append(
                    f"{planet_name.capitalize()} is in its own face in {sign} at {degree:.1f}°"
                )
                if not any([dignity_info["rulership"], dignity_info["exaltation"],
                           dignity_info["triplicity"], dignity_info["term"]]):
                    dignity_info["status"] = "dignified by face"

        # Add to results
        dignities[planet_name] = dignity_info

    return dignities

def calculate_planet_strengths(chart_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate planetary strength scores based on Vedic and Western principles.

    Args:
        chart_data: Chart data with planetary positions

    Returns:
        Dictionary mapping planet names to their strength data
    """
    # Use dignities as part of strength calculation
    dignities = calculate_dignities(chart_data)

    # Extract planets
    planets_data = chart_data.get("planets", {})
    if not planets_data:
        return {}

    # House strength values
    HOUSE_STRENGTHS = {
        1: 10, 4: 10, 7: 10, 10: 10,  # Angular houses (strongest)
        2: 7, 5: 7, 8: 7, 11: 7,      # Succedent houses
        3: 4, 6: 4, 9: 4, 12: 4       # Cadent houses (weakest)
    }

    # Natural planetary strengths
    NATURAL_STRENGTHS = {
        "sun": 10, "moon": 9, "jupiter": 9, "venus": 8,
        "mercury": 7, "mars": 7, "saturn": 6, "north_node": 5
    }

    # Calculate strength for each planet
    strengths = {}
    for planet_name, planet_data in planets_data.items():
        if not isinstance(planet_data, dict):
            continue

        # Get basic data
        house = planet_data.get("house", 0)
        sign = planet_data.get("sign", "")
        retrograde = planet_data.get("retrograde", False)

        # Get dignity score (-5 to +5 scale)
        dignity_score = dignities.get(planet_name, {}).get("score", 0)

        # Calculate house strength (0-10 scale)
        house_strength = HOUSE_STRENGTHS.get(house, 5)

        # Calculate natural strength (0-10 scale)
        natural_strength = NATURAL_STRENGTHS.get(planet_name.lower(), 5)

        # Calculate retrograde penalty
        retro_mod = 0.8 if retrograde else 1.0

        # Calculate total strength (0-100 scale)
        total_strength = (
            (natural_strength * 5) +         # 0-50
            (house_strength) +               # 0-10
            ((dignity_score + 5) * 4)        # 0-40
        ) * retro_mod

        # Ensure it's in 0-100 range
        total_strength = max(0, min(100, total_strength))

        # Determine strength category
        category = "average"
        if total_strength >= 75:
            category = "very strong"
        elif total_strength >= 60:
            category = "strong"
        elif total_strength >= 40:
            category = "moderate"
        elif total_strength >= 25:
            category = "weak"
        else:
            category = "very weak"

        # Store results
        strengths[planet_name] = {
            "total_strength": total_strength,
            "natural_strength": natural_strength,
            "house_strength": house_strength,
            "dignity_score": dignity_score,
            "retrograde": retrograde,
            "category": category
        }

    return strengths

def get_dignity_change_significance(planet: str, original: str, new: str) -> str:
    """
    Get astrological significance of dignity status changes.

    Args:
        planet: Planet name
        original: Original dignity status
        new: New dignity status

    Returns:
        Description of the dignity change significance
    """
    if original == new:
        return f"No change in {planet}'s essential dignity status."

    dignity_strength = {
        "Rulership": 5,
        "Exaltation": 4,
        "Triplicity ruler": 3,
        "Term": 2,
        "Face": 1,
        "Peregrine": 0,
        "Detriment": -4,
        "Fall": -5
    }

    # Extract base dignity status
    orig_base = next((d for d in dignity_strength.keys() if d.lower() in original.lower()), "Peregrine")
    new_base = next((d for d in dignity_strength.keys() if d.lower() in new.lower()), "Peregrine")

    orig_strength = dignity_strength.get(orig_base, 0)
    new_strength = dignity_strength.get(new_base, 0)

    if new_strength > orig_strength:
        return f"{planet} gains essential dignity, moving from {original} to {new}, increasing its effectiveness and natural expression."
    else:
        return f"{planet} loses essential dignity, moving from {original} to {new}, requiring more conscious effort to express its qualities."
