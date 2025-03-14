#!/usr/bin/env python3
"""
Chart Visualizer Module

This module provides functions for visualizing birth charts in various formats
including Lagna, Navamsa, Chandra, and D4 charts along with planetary positions.
It also includes functions for comparing and exporting charts.
"""

import os
import math
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

# Planet symbols and abbreviations
PLANET_SYMBOLS = {
    "Sun": "Su",
    "Moon": "Mo",
    "Mars": "Ma",
    "Mercury": "Me",
    "Jupiter": "Ju",
    "Venus": "Ve",
    "Saturn": "Sa",
    "Rahu": "Ra",
    "Ketu": "Ke",
    "Ascendant": "As"
}

# Zodiac sign names and abbreviations
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

ZODIAC_ABBR = {
    "Aries": "Ar",
    "Taurus": "Ta",
    "Gemini": "Ge",
    "Cancer": "Ca",
    "Leo": "Le",
    "Virgo": "Vi",
    "Libra": "Li",
    "Scorpio": "Sc",
    "Sagittarius": "Sg",
    "Capricorn": "Cp",
    "Aquarius": "Aq",
    "Pisces": "Pi"
}

# House arrangement for South Indian chart style
SOUTH_INDIAN_HOUSE_LAYOUT = [1, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]

def normalize_longitude(longitude: float) -> float:
    """Normalize longitude to 0-360 range."""
    return longitude % 360

def get_zodiac_sign(longitude: float) -> str:
    """Get zodiac sign name from longitude."""
    sign_index = int(longitude / 30)
    return ZODIAC_SIGNS[sign_index]

def get_zodiac_degree(longitude: float) -> float:
    """Get degree within zodiac sign from longitude."""
    return longitude % 30

def get_house_occupants(planets_data: Union[Dict[str, Any], List[Dict[str, Any]]], houses_data: List[Dict[str, Any]]) -> Dict[int, List[str]]:
    """
    Determine which planets occupy which houses.

    Args:
        planets_data: Planet data (either list of dictionaries or dictionary of planet data)
        houses_data: List of house data dictionaries

    Returns:
        Dictionary mapping house numbers to lists of planet abbreviations
    """
    house_occupants = {i: [] for i in range(1, 13)}

    # Convert planets dictionary to list if needed
    planets = []
    if planets_data and isinstance(planets_data, dict):
        # Handle dictionary format (where keys are planet names)
        for planet_key, planet_data in planets_data.items():
            # Create a planet entry with name from the key
            if isinstance(planet_data, dict):
                planet_entry = dict(planet_data)
                if "name" not in planet_entry:
                    planet_entry["name"] = planet_key.capitalize()
                planets.append(planet_entry)
    else:
        # Handle list format (or empty data)
        planets = planets_data if planets_data else []

    # Handle case where planets is a list of strings
    if planets and all(isinstance(p, str) for p in planets):
        # In this case, we can't determine house occupants
        # Just return empty dictionary
        return house_occupants

    # Create mapping of house cusps
    house_cusps = {}
    for house in houses_data:
        house_num = house.get("house_number")
        if house_num:
            house_cusps[house_num] = normalize_longitude(house.get("longitude", 0))

    # For each planet, find which house it's in
    for planet in planets:
        # Skip if planet is not a dictionary
        if not isinstance(planet, dict):
            continue

        planet_name = planet.get("name")
        if not planet_name:
            continue

        abbr = PLANET_SYMBOLS.get(planet_name, planet_name[:2])
        longitude = normalize_longitude(planet.get("longitude", 0))

        # Find which house contains this longitude
        for house_num in range(1, 13):
            next_house = house_num + 1 if house_num < 12 else 1
            start_long = house_cusps.get(house_num, 0)
            end_long = house_cusps.get(next_house, 0)

            # Handle case where house spans 0°
            if end_long < start_long:
                if longitude >= start_long or longitude < end_long:
                    house_occupants[house_num].append(abbr)
                    break
            else:
                if start_long <= longitude < end_long:
                    house_occupants[house_num].append(abbr)
                    break
        else:
            # If we can't determine the house, put it in house 1
            house_occupants[1].append(abbr)

    return house_occupants

def render_vedic_square_chart(
    chart_data: Dict[str, Any],
    chart_type: str = "Lagna",
    output_file: Optional[str] = None,
    include_aspects: bool = True
) -> str:
    """
    Render a Vedic square style chart.

    Args:
        chart_data: Chart data from the API
        chart_type: Type of chart (Lagna, Navamsa, etc.)
        output_file: Path to output file (optional)
        include_aspects: Whether to include aspects (kept for backward compatibility)

    Returns:
        String representation of the Vedic square chart
    """
    planets_data = chart_data.get("planets", [])
    houses_data = chart_data.get("houses", [])

    # Convert planets dictionary to list if needed
    planets = []
    if planets_data and isinstance(planets_data, dict):
        # Handle dictionary format (where keys are planet names)
        for planet_key, planet_data in planets_data.items():
            # Create a planet entry with name from the key
            if isinstance(planet_data, dict):
                planet_entry = dict(planet_data)
                if "name" not in planet_entry:
                    planet_entry["name"] = planet_key.capitalize()
                planets.append(planet_entry)
    else:
        # Handle list format (or empty data)
        planets = planets_data if planets_data else []

    # Get house occupants
    house_occupants = get_house_occupants(planets, houses_data)

    # Create the chart grid
    chart = []

    # Top row
    chart.append("┌─────────┬─────────┬─────────┬─────────┐")

    # House 12, 1, 2 content
    occupants_12 = " ".join(house_occupants.get(12, []))
    occupants_1 = " ".join(house_occupants.get(1, []))
    occupants_2 = " ".join(house_occupants.get(2, []))
    chart.append(f"│    {occupants_12:<5} │    {occupants_1:<5} │    {occupants_2:<5} │         │")

    # House numbers for houses 12, 1, 2
    chart.append(f"│   12    │    1    │    2    │         │")

    # Middle rows top
    chart.append("├─────────┼─────────┼─────────┤         │")

    # House 11 and 3 content
    occupants_11 = " ".join(house_occupants.get(11, []))
    occupants_3 = " ".join(house_occupants.get(3, []))
    chart.append(f"│    {occupants_11:<5} │         │    {occupants_3:<5} │         │")
    chart.append(f"│   11    │         │    3    │         │")

    # Middle rows middle
    chart.append("├─────────┤         ├─────────┤         │")

    # House 10 content
    occupants_10 = " ".join(house_occupants.get(10, []))
    occupants_4 = " ".join(house_occupants.get(4, []))
    chart.append(f"│    {occupants_10:<5} │         │    {occupants_4:<5} │         │")
    chart.append(f"│   10    │         │    4    │         │")

    # Middle rows bottom
    chart.append("├─────────┤         ├─────────┤         │")

    # House 9 content
    occupants_9 = " ".join(house_occupants.get(9, []))
    occupants_5 = " ".join(house_occupants.get(5, []))
    chart.append(f"│    {occupants_9:<5} │         │    {occupants_5:<5} │         │")
    chart.append(f"│    9    │         │    5    │         │")

    # Bottom rows
    chart.append("├─────────┼─────────┼─────────┤         │")

    # House 8, 7, 6 content
    occupants_8 = " ".join(house_occupants.get(8, []))
    occupants_7 = " ".join(house_occupants.get(7, []))
    occupants_6 = " ".join(house_occupants.get(6, []))
    chart.append(f"│    {occupants_8:<5} │    {occupants_7:<5} │    {occupants_6:<5} │         │")
    chart.append(f"│    8    │    7    │    6    │         │")

    # Final line
    chart.append("└─────────┴─────────┴─────────┴─────────┘")
    chart.append(f"\n{chart_type} Chart")

    chart_str = "\n".join(chart)

    # Write to file if requested
    if output_file:
        with open(output_file, 'w') as f:
            f.write(chart_str)

    return chart_str

def generate_multiple_charts(chart_data: Dict[str, Any], output_file: Optional[str] = None) -> Dict[str, str]:
    """
    Generate multiple chart visualizations from chart data.

    Args:
        chart_data: Chart data from the API
        output_file: Path to output file (optional)

    Returns:
        Dictionary of chart types to string representations
    """
    charts = {}

    # Generate Lagna (birth) chart
    charts["lagna"] = render_vedic_square_chart(chart_data, "Lagna", output_file)

    # Generate Navamsa chart (9th harmonic)
    navamsa_data = modify_chart_for_harmonic(chart_data, 9)
    charts["navamsa"] = render_vedic_square_chart(navamsa_data, "Navamsa", output_file)

    # Generate Chandra (Moon as Ascendant) chart
    chandra_data = modify_chart_for_moon_ascendant(chart_data)
    charts["chandra"] = render_vedic_square_chart(chandra_data, "Chandra", output_file)

    # Generate D4 chart (4th harmonic)
    d4_data = modify_chart_for_harmonic(chart_data, 4)
    charts["d4"] = render_vedic_square_chart(d4_data, "D4", output_file)

    # Generate planetary positions table
    charts["planetary_positions"] = generate_planetary_positions_table(chart_data)

    return charts

def generate_planetary_positions_table(chart_data: Dict[str, Any]) -> str:
    """
    Generate a formatted table of planetary positions.

    Args:
        chart_data: Chart data from the API

    Returns:
        String representation of the planetary positions table
    """
    planets_data = chart_data.get("planets", [])

    # Convert planets dictionary to list if needed
    planets = []
    if planets_data and isinstance(planets_data, dict):
        # Handle dictionary format (where keys are planet names)
        for planet_key, planet_data in planets_data.items():
            # Create a planet entry with name from the key
            if isinstance(planet_data, dict):
                planet_entry = dict(planet_data)
                if "name" not in planet_entry:
                    planet_entry["name"] = planet_key.capitalize()
                planets.append(planet_entry)
    else:
        # Handle list format (or empty data)
        planets = planets_data if planets_data else []

    # Handle case where planets is a list of strings
    if planets and all(isinstance(p, str) for p in planets):
        # Create a simple table with the planet names
        table = []
        table.append("\nPlanetary Position")
        table.append("=" * 80)
        table.append("Planets found: " + ", ".join(planets))
        table.append("\nNote: Detailed planetary data not available in this format.")
        return "\n".join(table)

    # Table header
    table = []
    table.append("\nPlanetary Position")
    table.append("=" * 80)
    header_row = "Planets    |"
    for planet_name in ["Asc", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        header_row += f" {planet_name:<10} |"
    table.append(header_row)

    # Separator line - calculate width based on number of planets
    separator = "-" * (10 + (12 * 10))  # Base width + width per planet
    table.append(separator)

    # Extract planet data
    planet_data = {}
    for planet in planets:
        # Skip if planet is not a dictionary
        if not isinstance(planet, dict):
            continue

        name = planet.get("name")
        if name:
            longitude = planet.get("longitude", 0)
            sign = get_zodiac_sign(longitude)
            degree = get_zodiac_degree(longitude)
            nakshatra = planet.get("nakshatra", "")

            # Determine Nakshatra lord based on nakshatra
            nakshalord = get_nakshatra_lord(nakshatra)

            # Get planet house and relationship status
            house = planet.get("house", "")
            relation = get_planet_relation(name, sign)

            planet_data[name] = {
                "longitude": longitude,
                "sign": sign,
                "degree": degree,
                "nakshatra": nakshatra,
                "pada": planet.get("pada", ""),
                "house": house,
                "nakshalord": nakshalord,
                "relation": relation
            }

    # Special handling for Ascendant which is not in planets array
    ascendant_data = chart_data.get("ascendant", {})
    if ascendant_data:
        ascendant_longitude = ascendant_data.get("longitude", 0)
        ascendant_sign = ascendant_data.get("sign", get_zodiac_sign(ascendant_longitude))
        ascendant_degree = ascendant_data.get("degree", get_zodiac_degree(ascendant_longitude))
        ascendant_nakshatra = ascendant_data.get("nakshatra", "")

        planet_data["Ascendant"] = {
            "longitude": ascendant_longitude,
            "sign": ascendant_sign,
            "degree": ascendant_degree,
            "nakshatra": ascendant_nakshatra,
            "pada": ascendant_data.get("pada", ""),
            "house": 1,  # Ascendant is always the 1st house
            "nakshalord": get_nakshatra_lord(ascendant_nakshatra),
            "relation": "Neutral"  # Ascendant doesn't have friend/enemy relations
        }

    # If no valid planet data was found, return a message
    if not planet_data:
        table.append("No detailed planetary data available in this format.")
        return "\n".join(table)

    # Degree row
    degree_row = f"{'Degree':<10} |"
    for planet_name in ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        key = "Asc" if planet_name == "Ascendant" else planet_name
        if key in planet_data and 'degree' in planet_data[key]:
            degree_row += f" {planet_data[key]['degree']:.2f}° |"
        else:
            degree_row += f" {'--':<10} |"
    table.append(degree_row)

    # Rashi row
    rashi_row = f"{'Rashi':<10} |"
    for planet_name in ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        key = "Asc" if planet_name == "Ascendant" else planet_name
        if key in planet_data and 'sign' in planet_data[key]:
            rashi_row += f" {planet_data[key]['sign']:<10} |"
        else:
            rashi_row += f" {'--':<10} |"
    table.append(rashi_row)

    # Longitude row
    longitude_row = f"{'Longitude':<10} |"
    for planet_name in ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        key = "Asc" if planet_name == "Ascendant" else planet_name
        if key in planet_data and 'longitude' in planet_data[key]:
            longitude_row += f" {planet_data[key]['longitude']:.2f}° |"
        else:
            longitude_row += f" {'--':<10} |"
    table.append(longitude_row)

    # Nakshatra row
    nakshatra_row = f"{'Nakshatra':<10} |"
    for planet_name in ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        key = "Asc" if planet_name == "Ascendant" else planet_name
        if key in planet_data and 'nakshatra' in planet_data[key]:
            nakshatra_row += f" {planet_data[key]['nakshatra']:<10} |"
        else:
            nakshatra_row += f" {'--':<10} |"
    table.append(nakshatra_row)

    # Pada row
    pada_row = f"{'Pada':<10} |"
    for planet_name in ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        key = "Asc" if planet_name == "Ascendant" else planet_name
        if key in planet_data and 'pada' in planet_data[key]:
            pada_row += f" {planet_data[key]['pada']:<10} |"
        else:
            pada_row += f" {'--':<10} |"
    table.append(pada_row)

    # NakshaLord row
    nakshalord_row = f"{'NakshaLord':<10} |"
    for planet_name in ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        key = "Asc" if planet_name == "Ascendant" else planet_name
        if key in planet_data and 'nakshalord' in planet_data[key]:
            nakshalord_row += f" {planet_data[key]['nakshalord']:<10} |"
        else:
            nakshalord_row += f" {'--':<10} |"
    table.append(nakshalord_row)

    # House row
    house_row = f"{'House':<10} |"
    for planet_name in ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        key = "Asc" if planet_name == "Ascendant" else planet_name
        if key in planet_data and 'house' in planet_data[key]:
            house_row += f" {planet_data[key]['house']:<10} |"
        else:
            house_row += f" {'--':<10} |"
    table.append(house_row)

    # Relation row
    relation_row = f"{'Relation':<10} |"
    for planet_name in ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
        key = "Asc" if planet_name == "Ascendant" else planet_name
        if key in planet_data and 'relation' in planet_data[key]:
            relation_row += f" {planet_data[key]['relation']:<10} |"
        else:
            relation_row += f" {'--':<10} |"
    table.append(relation_row)

    return "\n".join(table)

def get_nakshatra_lord(nakshatra: str) -> str:
    """Get the lord of a nakshatra."""
    # Standard lords mapping according to Vedic astrology
    nakshatra_lords = {
        "Ashwini": "Ketu",
        "Bharani": "Venus",
        "Krittika": "Sun",
        "Rohini": "Moon",
        "Mrigashira": "Mars",
        "Ardra": "Rahu",
        "Punarvasu": "Jupiter",
        "Pushya": "Saturn",
        "Ashlesha": "Mercury",
        "Magha": "Ketu",
        "Purva Phalguni": "Venus",
        "Uttara Phalguni": "Sun",
        "Hasta": "Moon",
        "Chitra": "Mars",
        "Swati": "Rahu",
        "Vishakha": "Jupiter",
        "Anuradha": "Saturn",
        "Jyeshtha": "Mercury",
        "Mula": "Ketu",
        "Purva Ashadha": "Venus",
        "Uttara Ashadha": "Sun",
        "Shravana": "Moon",
        "Dhanishta": "Mars",
        "Shatabhisha": "Rahu",
        "Purva Bhadrapada": "Jupiter",
        "Uttara Bhadrapada": "Saturn",
        "Revati": "Mercury",
        # Alternative names and spellings
        "Bharani": "Yama",
        "Krittika": "Agni",
        "Mrigashirsha": "Mars",
        "Purva Phalguni": "Venus",
        "Uttara Phalguni": "Sun",
        "Swati": "Vayu",
        "Vishakha": "Indra,Agni",
        "Jyestha": "Mercury",
        "Purvashadha": "Venus",
        "Uttarashadha": "Sun",
        "Dhanishtha": "Mars",
        "Shatabhisha": "Varuna",
        "Purva Bhadrapada": "Jupiter",
        "Uttara Bhadrapada": "Saturn",
    }
    return nakshatra_lords.get(nakshatra, "Unknown")

def get_planet_relation(planet: str, sign: str) -> str:
    """Get the relationship status of a planet in a sign."""
    # Basic relationship table for planets in signs
    # This is a simplified version - a comprehensive version would account for
    # sign lordships, exaltation, debilitation, etc.

    # Map of planet to friendly/enemy/neutral signs
    relation_map = {
        "Sun": {
            "Friend": ["Leo", "Aries", "Sagittarius"],
            "Enemy": ["Aquarius", "Libra", "Capricorn"],
            "Neutral": ["Taurus", "Gemini", "Cancer", "Virgo", "Scorpio", "Pisces"]
        },
        "Moon": {
            "Friend": ["Cancer", "Taurus", "Pisces"],
            "Enemy": ["Scorpio", "Capricorn"],
            "Neutral": ["Aries", "Gemini", "Leo", "Virgo", "Libra", "Sagittarius", "Aquarius"]
        },
        "Mars": {
            "Friend": ["Aries", "Scorpio", "Capricorn", "Leo"],
            "Enemy": ["Cancer", "Libra", "Taurus"],
            "Neutral": ["Gemini", "Virgo", "Sagittarius", "Aquarius", "Pisces"]
        },
        "Mercury": {
            "Friend": ["Gemini", "Virgo", "Libra", "Aquarius"],
            "Enemy": ["Pisces", "Sagittarius"],
            "Neutral": ["Aries", "Taurus", "Cancer", "Leo", "Scorpio", "Capricorn"]
        },
        "Jupiter": {
            "Friend": ["Sagittarius", "Pisces", "Cancer", "Leo"],
            "Enemy": ["Virgo", "Gemini", "Capricorn"],
            "Neutral": ["Aries", "Taurus", "Libra", "Scorpio", "Aquarius"]
        },
        "Venus": {
            "Friend": ["Taurus", "Libra", "Pisces", "Cancer"],
            "Enemy": ["Scorpio", "Aries", "Virgo"],
            "Neutral": ["Gemini", "Leo", "Sagittarius", "Capricorn", "Aquarius"]
        },
        "Saturn": {
            "Friend": ["Capricorn", "Aquarius", "Libra"],
            "Enemy": ["Leo", "Aries", "Cancer"],
            "Neutral": ["Taurus", "Gemini", "Virgo", "Scorpio", "Sagittarius", "Pisces"]
        },
        "Rahu": {
            "Friend": ["Gemini", "Virgo", "Aquarius", "Libra"],
            "Enemy": ["Cancer", "Leo", "Pisces"],
            "Neutral": ["Aries", "Taurus", "Scorpio", "Sagittarius", "Capricorn"]
        },
        "Ketu": {
            "Friend": ["Scorpio", "Pisces", "Aries"],
            "Enemy": ["Gemini", "Libra", "Virgo"],
            "Neutral": ["Taurus", "Cancer", "Leo", "Sagittarius", "Capricorn", "Aquarius"]
        },
        "Ascendant": {
            "Friend": [],
            "Enemy": [],
            "Neutral": ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                       "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        }
    }

    # Normalize planet name to match keys in our relation map
    if planet in ["Asc", "Ascendant", "Lagna"]:
        planet = "Ascendant"

    # Return relationship if planet and sign exist in our mappings
    if planet in relation_map:
        if sign in relation_map[planet]["Friend"]:
            return "Friend"
        elif sign in relation_map[planet]["Enemy"]:
            return "Enemy"
        else:
            return "Neutral"

    return "Neutral"  # Default to neutral if relationship not found

def modify_chart_for_harmonic(chart_data: Dict[str, Any], harmonic_number: int) -> Dict[str, Any]:
    """
    Modify chart data for harmonic analysis (e.g., Navamsa or D4).

    Args:
        chart_data: Chart data from the API
        harmonic_number: Harmonic number to apply (e.g., 9 for Navamsa)

    Returns:
        Modified chart data
    """
    # Create a deep copy of the chart data
    modified_data = json.loads(json.dumps(chart_data))

    # Handle different planet data formats
    planets_data = modified_data.get("planets", [])

    if isinstance(planets_data, dict):
        # Dictionary format (keys are planet names)
        for planet_name, planet_data in planets_data.items():
            if isinstance(planet_data, dict) and "longitude" in planet_data:
                longitude = planet_data.get("longitude", 0)
                # Harmonic calculation: multiply by harmonic and take modulo 360
                harmonic_longitude = (longitude * harmonic_number) % 360
                planets_data[planet_name]["longitude"] = harmonic_longitude
    else:
        # List format (each item is a planet object)
        for i, planet in enumerate(planets_data):
            if isinstance(planet, dict):
                longitude = planet.get("longitude", 0)
                # Harmonic calculation: multiply by harmonic and take modulo 360
                harmonic_longitude = (longitude * harmonic_number) % 360
                planets_data[i]["longitude"] = harmonic_longitude

    # Update planets in modified data
    modified_data["planets"] = planets_data

    return modified_data

def modify_chart_for_moon_ascendant(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modify chart data to use Moon as the Ascendant (Chandra Lagna).

    Args:
        chart_data: Chart data from the API

    Returns:
        Modified chart data with Moon as Ascendant
    """
    # Create a deep copy of the chart data
    modified_data = json.loads(json.dumps(chart_data))

    # Find Moon longitude based on the data structure
    moon_longitude = 0
    planets_data = modified_data.get("planets", [])

    if isinstance(planets_data, dict):
        # Dictionary format (keys are planet names)
        if "Moon" in planets_data and isinstance(planets_data["Moon"], dict):
            moon_longitude = planets_data["Moon"].get("longitude", 0)
    else:
        # List format (each item is a planet object)
        for planet in planets_data:
            if isinstance(planet, dict) and planet.get("name") == "Moon":
                moon_longitude = planet.get("longitude", 0)
                break

    # Find Ascendant longitude
    asc_longitude = 0
    if "ascendant" in modified_data and isinstance(modified_data["ascendant"], dict):
        # Direct ascendant object
        asc_longitude = modified_data["ascendant"].get("longitude", 0)
    elif isinstance(planets_data, dict):
        # Dictionary format (keys are planet names)
        if "Ascendant" in planets_data and isinstance(planets_data["Ascendant"], dict):
            asc_longitude = planets_data["Ascendant"].get("longitude", 0)
    else:
        # List format (each item is a planet object)
        for planet in planets_data:
            if isinstance(planet, dict) and planet.get("name") == "Moon":
                moon_longitude = planet.get("longitude", 0)
                break

    # Find Ascendant longitude
    asc_longitude = 0
    if "ascendant" in modified_data and isinstance(modified_data["ascendant"], dict):
        # Direct ascendant object
        asc_longitude = modified_data["ascendant"].get("longitude", 0)
    elif isinstance(planets_data, dict):
        # Dictionary format (keys are planet names)
        if "Ascendant" in planets_data and isinstance(planets_data["Ascendant"], dict):
            asc_longitude = planets_data["Ascendant"].get("longitude", 0)
    else:
        # List format (each item is a planet object)
        for planet in planets_data:
            if isinstance(planet, dict) and planet.get("name") == "Ascendant":
                asc_longitude = planet.get("longitude", 0)
                break

    # Calculate shift required
    shift = moon_longitude - asc_longitude

    # Apply shift based on data structure
    if isinstance(planets_data, dict):
        # Dictionary format (keys are planet names)
        for planet_name, planet_data in planets_data.items():
            if isinstance(planet_data, dict) and "longitude" in planet_data:
                longitude = planet_data.get("longitude", 0)
                shifted_longitude = (longitude + shift) % 360
                planets_data[planet_name]["longitude"] = shifted_longitude
    else:
        # List format (each item is a planet object)
        for i, planet in enumerate(planets_data):
            if isinstance(planet, dict) and "longitude" in planet:
                longitude = planet.get("longitude", 0)
                shifted_longitude = (longitude + shift) % 360
                planets_data[i]["longitude"] = shifted_longitude

    # Update houses data
    houses = modified_data.get("houses", [])
    for i, house in enumerate(houses):
        if isinstance(house, dict) and "longitude" in house:
            longitude = house.get("longitude", 0)
            shifted_longitude = (longitude + shift) % 360
            houses[i]["longitude"] = shifted_longitude

    # Update planets and houses in modified data
    modified_data["planets"] = planets_data
    modified_data["houses"] = houses

    return modified_data

def compare_charts(chart1_data: Dict[str, Any], chart2_data: Dict[str, Any]) -> str:
    """
    Compare two charts and generate a textual comparison.

    Args:
        chart1_data: First chart data
        chart2_data: Second chart data

    Returns:
        String with comparison results
    """
    comparison = []
    comparison.append("Chart Comparison")
    comparison.append("=" * 80)

    # Compare planetary positions
    planets1 = chart1_data.get("planets", [])
    planets2 = chart2_data.get("planets", [])

    comparison.append("\nPlanetary Positions Comparison:")
    comparison.append("-" * 80)
    comparison.append(f"{'Planet':<10} | {'Original':<15} | {'Rectified':<15} | {'Difference':<10}")
    comparison.append("-" * 80)

    # Create dictionaries for easier comparison
    planet_dict1 = {}
    planet_dict2 = {}

    # Process planets from chart1
    if isinstance(planets1, dict):
        # Dictionary format (keys are planet names)
        for planet_key, planet_data in planets1.items():
            if isinstance(planet_data, dict) and "longitude" in planet_data:
                planet_dict1[planet_key] = planet_data
    else:
        # List format (each item is a planet object)
        for planet in planets1:
            if isinstance(planet, dict) and "name" in planet:
                planet_dict1[planet["name"]] = planet

    # Process planets from chart2
    if isinstance(planets2, dict):
        # Dictionary format (keys are planet names)
        for planet_key, planet_data in planets2.items():
            if isinstance(planet_data, dict) and "longitude" in planet_data:
                planet_dict2[planet_key] = planet_data
    else:
        # List format (each item is a planet object)
        for planet in planets2:
            if isinstance(planet, dict) and "name" in planet:
                planet_dict2[planet["name"]] = planet

    # Compare each planet
    all_planets = set(planet_dict1.keys()) | set(planet_dict2.keys())
    for planet_name in all_planets:
        if planet_name in planet_dict1 and planet_name in planet_dict2:
            long1 = planet_dict1[planet_name].get("longitude", 0)
            long2 = planet_dict2[planet_name].get("longitude", 0)

            # Calculate smallest difference (handle 0°/360° boundary)
            diff = abs(long1 - long2)
            if diff > 180:
                diff = 360 - diff

            sign1 = get_zodiac_sign(long1)
            sign2 = get_zodiac_sign(long2)

            comparison.append(f"{planet_name:<10} | {sign1} {long1:.2f}° | {sign2} {long2:.2f}° | {diff:.2f}°")

    # Compare house cusps
    houses1 = chart1_data.get("houses", [])
    houses2 = chart2_data.get("houses", [])

    comparison.append("\nHouse Cusps Comparison:")
    comparison.append("-" * 80)
    comparison.append(f"{'House':<10} | {'Original':<15} | {'Rectified':<15} | {'Difference':<10}")
    comparison.append("-" * 80)

    # Create dictionaries for easier comparison
    house_dict1 = {h.get("house_number"): h for h in houses1 if isinstance(h, dict) and "house_number" in h}
    house_dict2 = {h.get("house_number"): h for h in houses2 if isinstance(h, dict) and "house_number" in h}

    # Compare each house
    for house_num in range(1, 13):
        if house_num in house_dict1 and house_num in house_dict2:
            long1 = house_dict1[house_num].get("longitude", 0)
            long2 = house_dict2[house_num].get("longitude", 0)

            # Calculate smallest difference (handle 0°/360° boundary)
            diff = abs(long1 - long2)
            if diff > 180:
                diff = 360 - diff

            sign1 = get_zodiac_sign(long1)
            sign2 = get_zodiac_sign(long2)

            comparison.append(f"House {house_num:<5} | {sign1} {long1:.2f}° | {sign2} {long2:.2f}° | {diff:.2f}°")

    return "\n".join(comparison)

def export_charts(original_charts: Dict[str, str], rectified_charts: Dict[str, str], birth_details: Dict[str, Any]) -> str:
    """
    Export charts to file.

    Args:
        original_charts: Dictionary of original chart visualizations
        rectified_charts: Dictionary of rectified chart visualizations
        birth_details: Birth details

    Returns:
        Path to exported file
    """
    # Create directory for exports
    export_dir = "chart_exports"
    os.makedirs(export_dir, exist_ok=True)

    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Extract name from birth details or use "unnamed"
    name = birth_details.get("name", "unnamed").replace(" ", "_").lower()

    # Generate filename
    filename = f"{export_dir}/{name}_{timestamp}_charts.txt"

    # Write to file
    with open(filename, "w") as f:
        # Write header
        f.write("=" * 80 + "\n")
        f.write("BIRTH TIME RECTIFICATION REPORT\n")
        f.write("=" * 80 + "\n\n")

        # Write birth details
        f.write("BIRTH DETAILS:\n")
        f.write("-" * 80 + "\n")
        for key, value in birth_details.items():
            f.write(f"{key}: {value}\n")
        f.write("\n")

        # Write original charts
        f.write("ORIGINAL CHARTS:\n")
        f.write("-" * 80 + "\n")
        for chart_type, chart_display in original_charts.items():
            f.write(f"\n{chart_type.upper()}:\n")
            f.write(chart_display)
            f.write("\n" + "-" * 40 + "\n")

        # Write rectified charts
        f.write("\nRECTIFIED CHARTS:\n")
        f.write("-" * 80 + "\n")
        for chart_type, chart_display in rectified_charts.items():
            f.write(f"\n{chart_type.upper()}:\n")
            f.write(chart_display)
            f.write("\n" + "-" * 40 + "\n")

    return filename

def render_vedic_chart(chart_data: Dict[str, Any], output_file: Optional[str] = None, include_aspects: bool = True) -> str:
    """
    Render a Vedic (South Indian) style chart.

    Args:
        chart_data: Chart data from the API
        output_file: Path to output file (optional)
        include_aspects: Whether to include aspects in the visualization

    Returns:
        String representation of the Vedic chart
    """
    # For backward compatibility, call render_vedic_square_chart
    return render_vedic_square_chart(chart_data, "Lagna", output_file, include_aspects)
