"""
Utility functions for converting between astrological codes and human-readable terms.
This module provides functions to convert between internal codes and proper names
for planets, houses, signs, and aspects in astrological calculations.
"""

def get_planet_name(planet_code: str) -> str:
    """Convert planet code to human-readable name."""
    planet_names = {
        "Sun": "Sun",
        "Moon": "Moon",
        "Mercury": "Mercury",
        "Venus": "Venus",
        "Mars": "Mars",
        "Jupiter": "Jupiter",
        "Saturn": "Saturn",
        "Uranus": "Uranus",
        "Neptune": "Neptune",
        "Pluto": "Pluto",
        "North Node": "North Node",
        "South Node": "South Node",
        "Chiron": "Chiron",
        "Asc": "Ascendant",
        "MC": "Midheaven",
        "Desc": "Descendant",
        "IC": "Imum Coeli"
    }
    return planet_names.get(planet_code, planet_code)

def get_sign_name(sign_code: str) -> str:
    """Convert sign code to human-readable name."""
    sign_names = {
        "Ari": "Aries",
        "Tau": "Taurus",
        "Gem": "Gemini",
        "Can": "Cancer",
        "Leo": "Leo",
        "Vir": "Virgo",
        "Lib": "Libra",
        "Sco": "Scorpio",
        "Sag": "Sagittarius",
        "Cap": "Capricorn",
        "Aqu": "Aquarius",
        "Pis": "Pisces"
    }
    return sign_names.get(sign_code, sign_code)

def get_house_system_name(house_system_code: str) -> str:
    """Convert house system code to human-readable name."""
    house_systems = {
        "P": "Placidus",
        "K": "Koch",
        "O": "Porphyrius",
        "R": "Regiomontanus",
        "C": "Campanus",
        "E": "Equal",
        "W": "Whole Sign",
        "X": "Whole Sign (deprecated)",
        "H": "Horizon",
        "T": "Topocentric",
        "B": "Alcabitus",
        "M": "Morinus",
        "U": "Krusinski",
        "A": "Equal (Ascendant)",
        "V": "Vehlow Equal",
        "L": "Pullen Sinusoidal Delta",
        "Q": "Pullen Sinusoidal Ratio",
        "S": "Sripati",
        "Y": "APC",
        "F": "Carter Poli Equatorial",
        "D": "Equal MC"
    }
    return house_systems.get(house_system_code, f"Unknown ({house_system_code})")

def get_aspect_name(aspect_code: str) -> str:
    """Convert aspect code to human-readable name."""
    aspect_names = {
        "Con": "Conjunction",
        "Sxt": "Sextile",
        "Sq": "Square",
        "Tri": "Trine",
        "Opp": "Opposition",
        "SSq": "Semi-Square",
        "SSx": "Semi-Sextile",
        "Ses": "Sesquiquadrate",
        "Q": "Quintile",
        "BQ": "Biquintile",
        "Sep": "Septile",
        "Nov": "Novile",
        "Qui": "Quincunx",
        "Par": "Parallel",
        "CPar": "Contraparallel"
    }
    return aspect_names.get(aspect_code, aspect_code)

def get_zodiac_type_name(zodiac_code: str) -> str:
    """Convert zodiac type code to human-readable name."""
    zodiac_types = {
        "tropical": "Tropical",
        "sidereal": "Sidereal"
    }
    return zodiac_types.get(zodiac_code, zodiac_code)

def get_ayanamsa_name(ayanamsa_code: str) -> str:
    """Convert ayanamsa code to human-readable name."""
    ayanamsa_names = {
        "lahiri": "Lahiri",
        "deluce": "De Luce",
        "raman": "B.V. Raman",
        "ushashashi": "Usha/Shashi",
        "krishnamurti": "Krishnamurti",
        "djwhalkhul": "DjwhalKhul",
        "yukteshwar": "Yukteshwar",
        "jnbhasin": "J.N. Bhasin",
        "babylonian": "Babylonian",
        "aldebaran": "Aldebaran",
        "galcent": "Galactic Center",
        "hipparchos": "Hipparchos",
        "sassanian": "Sassanian",
        "custom": "Custom",
        "none": "None"
    }
    return ayanamsa_names.get(ayanamsa_code, ayanamsa_code)
