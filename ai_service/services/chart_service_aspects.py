"""
Aspect calculation utilities for chart service.

This module provides functionality for calculating aspects between planets.
"""

import logging
from typing import Dict, Any, List, Optional, Union

# Import from utils module to avoid circular imports
from ai_service.services.chart_service_utils import calculate_arc_difference, get_sign_from_longitude, get_planet_rulerships

logger = logging.getLogger(__name__)

def calculate_aspects(chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calculate astrological aspects between planets with proper orbs and significance.
    Implements both major and minor aspects with appropriate weightings.

    Args:
        chart_data: Chart data with planetary positions

    Returns:
        List of aspect dictionaries with comprehensive astrological data
    """
    # Define aspects and their orbs
    ASPECTS = {
        "conjunction": {"angle": 0, "orb": 8, "type": "major", "harmonic": 1, "influence": "blending", "quality": "neutral"},
        "opposition": {"angle": 180, "orb": 8, "type": "major", "harmonic": 2, "influence": "challenging", "quality": "dynamic"},
        "trine": {"angle": 120, "orb": 8, "type": "major", "harmonic": 3, "influence": "flowing", "quality": "harmonious"},
        "square": {"angle": 90, "orb": 7, "type": "major", "harmonic": 4, "influence": "challenging", "quality": "dynamic"},
        "sextile": {"angle": 60, "orb": 6, "type": "major", "harmonic": 6, "influence": "flowing", "quality": "harmonious"},
        "quincunx": {"angle": 150, "orb": 5, "type": "minor", "harmonic": 12, "influence": "adjusting", "quality": "neutral"},
        "semi-square": {"angle": 45, "orb": 3, "type": "minor", "harmonic": 8, "influence": "irritating", "quality": "dynamic"},
        "semi-sextile": {"angle": 30, "orb": 3, "type": "minor", "harmonic": 12, "influence": "subtle", "quality": "neutral"}
    }

    # Extract planets from chart data
    planets_data = chart_data.get("planets", {})
    if not planets_data:
        return []

    # Convert to normalized format if needed
    planets = []
    if isinstance(planets_data, dict):
        for name, data in planets_data.items():
            if isinstance(data, dict):
                planets.append({"name": name, **data})
    elif isinstance(planets_data, list):
        planets = planets_data

    # Special planet weightings for aspect significance
    PLANET_WEIGHTINGS = {
        "sun": 10,
        "moon": 10,
        "ascendant": 10,
        "mercury": 8,
        "venus": 8,
        "mars": 8,
        "jupiter": 9,
        "saturn": 9,
        "uranus": 7,
        "neptune": 7,
        "pluto": 7,
        "north_node": 6,
        "south_node": 6,
        "chiron": 5
    }

    # Result list for all aspects
    aspects = []

    # Calculate aspects between all planet pairs (avoid duplicate calculations)
    for i in range(len(planets)):
        planet1 = planets[i]
        p1_name = planet1.get("name", "").lower()
        p1_longitude = planet1.get("longitude", 0)

        for j in range(i + 1, len(planets)):
            planet2 = planets[j]
            p2_name = planet2.get("name", "").lower()
            p2_longitude = planet2.get("longitude", 0)

            # Skip aspects between non-planets (e.g., Nodes with each other)
            if p1_name in ["north_node", "south_node"] and p2_name in ["north_node", "south_node"]:
                continue

            # Calculate the angular difference between planets
            angle_diff = calculate_arc_difference(p1_longitude, p2_longitude)

            # Check for valid aspects
            for aspect_name, aspect_data in ASPECTS.items():
                aspect_angle = aspect_data["angle"]
                max_orb = aspect_data["orb"]

                # Adjust orb based on planet importance
                p1_weight = PLANET_WEIGHTINGS.get(p1_name, 5)
                p2_weight = PLANET_WEIGHTINGS.get(p2_name, 5)
                combined_weight = (p1_weight + p2_weight) / 2

                # Luminaries (Sun and Moon) get extra orb allowance
                if p1_name in ["sun", "moon"] or p2_name in ["sun", "moon"]:
                    adjusted_orb = max_orb * 1.2 * (combined_weight / 10)
                else:
                    adjusted_orb = max_orb * (combined_weight / 10)

                # Check if planets are in aspect
                orb = abs(angle_diff - aspect_angle)
                if orb <= adjusted_orb:
                    # Calculate aspect strength (1.0 = exact aspect, 0 = at maximum orb)
                    strength = 1.0 - (orb / adjusted_orb)

                    # Calculate applying or separating
                    # We'd need planet speeds to calculate this properly
                    is_applying = False  # Simplification without speed data

                    # Calculate zodiacal signs for interpretation
                    p1_sign = get_sign_from_longitude(p1_longitude)
                    p2_sign = get_sign_from_longitude(p2_longitude)

                    # Calculate houses for interpretation
                    p1_house = planet1.get("house", 0)
                    p2_house = planet2.get("house", 0)

                    # Get rulerships for deeper analysis
                    p1_rules = get_planet_rulerships(p1_name, chart_data)
                    p2_rules = get_planet_rulerships(p2_name, chart_data)

                    # Calculate aspect significance based on planets, aspect type, and strength
                    significance = calculate_aspect_significance(
                        p1_name, p2_name, aspect_name, strength,
                        p1_house, p2_house, p1_rules, p2_rules
                    )

                    # Add to aspects list
                    aspects.append({
                        "planet1": p1_name,
                        "planet2": p2_name,
                        "aspect": aspect_name,
                        "angle": aspect_angle,
                        "orb": orb,
                        "strength": strength,
                        "significance": significance,
                        "applying": is_applying,
                        "separating": not is_applying,
                        "planet1_sign": p1_sign,
                        "planet2_sign": p2_sign,
                        "planet1_house": p1_house,
                        "planet2_house": p2_house,
                        "influence": aspect_data["influence"],
                        "quality": aspect_data["quality"],
                        "harmonic": aspect_data["harmonic"],
                        "interpretation": get_aspect_interpretation(
                            p1_name, p2_name, aspect_name, p1_sign, p2_sign, p1_house, p2_house
                        )
                    })

    # Sort aspects by significance (most significant first)
    aspects.sort(key=lambda a: a.get("significance", 0), reverse=True)

    return aspects

def calculate_aspect_significance(p1_name: str, p2_name: str, aspect_name: str,
                                  strength: float, p1_house: int, p2_house: int,
                                  p1_rules: List[int], p2_rules: List[int]) -> float:
    """
    Calculate the astrological significance of an aspect based on multiple factors.

    Args:
        p1_name: First planet name
        p2_name: Second planet name
        aspect_name: Type of aspect
        strength: Aspect strength (0-1)
        p1_house: House of first planet
        p2_house: House of second planet
        p1_rules: Houses ruled by first planet
        p2_rules: Houses ruled by second planet

    Returns:
        Significance value (0-100)
    """
    # Base significance by planet importance
    planet_significances = {
        "sun": 10, "moon": 10, "ascendant": 10, "mercury": 7, "venus": 7,
        "mars": 7, "jupiter": 8, "saturn": 8, "uranus": 6, "neptune": 6,
        "pluto": 6, "north_node": 5, "south_node": 5, "chiron": 4
    }

    p1_significance = planet_significances.get(p1_name.lower(), 5)
    p2_significance = planet_significances.get(p2_name.lower(), 5)

    # Base significance by aspect type
    aspect_weights = {
        "conjunction": 10, "opposition": 9, "trine": 8, "square": 8,
        "sextile": 7, "quincunx": 5, "semi-square": 4, "semi-sextile": 3
    }

    aspect_weight = aspect_weights.get(aspect_name, 5)

    # Adjust for angular houses (1, 4, 7, 10 - most important)
    angular_houses = [1, 4, 7, 10]
    succedent_houses = [2, 5, 8, 11]  # Second most important

    house_modifier = 1.0
    if p1_house in angular_houses or p2_house in angular_houses:
        house_modifier = 1.5
    elif p1_house in succedent_houses or p2_house in succedent_houses:
        house_modifier = 1.3

    # Adjust for rulership connections (when a planet aspects a house it rules)
    rulership_modifier = 1.0
    if p2_house in p1_rules or p1_house in p2_rules:
        rulership_modifier = 1.3

    # Calculate final significance (0-100 scale)
    significance = ((p1_significance + p2_significance) / 2 * aspect_weight * strength *
                    house_modifier * rulership_modifier)

    # Normalize to 0-100 range
    normalized_significance = min(100, max(0, significance * 5))

    return normalized_significance

def get_aspect_interpretation(p1_name: str, p2_name: str, aspect_name: str,
                              p1_sign: str, p2_sign: str, p1_house: int, p2_house: int) -> str:
    """
    Generate a brief interpretation for an astrological aspect.

    Args:
        p1_name: First planet name
        p2_name: Second planet name
        aspect_name: Type of aspect
        p1_sign: Sign of first planet
        p2_sign: Sign of second planet
        p1_house: House of first planet
        p2_house: House of second planet

    Returns:
        Brief interpretation of the aspect
    """
    # Define aspect qualities
    aspect_qualities = {
        "conjunction": "blends the energies of",
        "opposition": "creates tension between",
        "trine": "creates harmonious flow between",
        "square": "creates dynamic challenges between",
        "sextile": "offers opportunities between",
        "quincunx": "requires adjustments between",
        "semi-square": "creates irritation between",
        "semi-sextile": "creates subtle connections between"
    }

    quality = aspect_qualities.get(aspect_name, "connects")

    houses_meaning = {
        1: "identity and self-expression",
        2: "resources and values",
        3: "communication and learning",
        4: "home and emotional foundation",
        5: "creativity and pleasure",
        6: "work and health",
        7: "partnerships and relationships",
        8: "transformation and shared resources",
        9: "beliefs and higher learning",
        10: "career and public image",
        11: "groups and aspirations",
        12: "spirituality and hidden matters"
    }

    p1_area = houses_meaning.get(p1_house, f"house {p1_house}")
    p2_area = houses_meaning.get(p2_house, f"house {p2_house}")

    return f"{p1_name.capitalize()} in {p1_sign} {quality} {p2_name.capitalize()} in {p2_sign}, connecting your {p1_area} with your {p2_area}."
