"""
Astrological constants for birth time rectification.
"""
from datetime import datetime, date
import json

# Import the shared DateTimeEncoder
from ai_service.utils.json_encoder import DateTimeEncoder

# Define planets list once
PLANETS_LIST = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
]

# Define houses list once
HOUSES_LIST = [
    "1st", "2nd", "3rd", "4th", "5th", "6th",
    "7th", "8th", "9th", "10th", "11th", "12th"
]

# Define zodiac signs once
SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Define aspects once
ASPECTS = {
    "conjunction": {"angle": 0, "orb": 10.0, "nature": "major"},
    "opposition": {"angle": 180, "orb": 10.0, "nature": "major"},
    "trine": {"angle": 120, "orb": 8.0, "nature": "major"},
    "square": {"angle": 90, "orb": 8.0, "nature": "major"},
    "sextile": {"angle": 60, "orb": 6.0, "nature": "minor"},
    "quincunx": {"angle": 150, "orb": 5.0, "nature": "minor"},
    "semisextile": {"angle": 30, "orb": 3.0, "nature": "minor"}
}

# Life event mappings
LIFE_EVENT_MAPPING = {
    "marriage": ["Venus", "Juno", "Descendant", "7th_house"],
    "career_change": ["Saturn", "Midheaven", "10th_house"],
    "relocation": ["Moon", "4th_house", "IC"],
    "major_illness": ["Mars", "Saturn", "Chiron", "6th_house", "8th_house"],
    "children": ["Jupiter", "Moon", "5th_house"],
    "education": ["Mercury", "3rd_house", "9th_house"],
    "accident": ["Mars", "Uranus", "8th_house"],
    "death_of_loved_one": ["Pluto", "Saturn", "8th_house"],
    "spiritual_awakening": ["Neptune", "Jupiter", "9th_house", "12th_house"],
    "financial_change": ["Venus", "Jupiter", "2nd_house", "8th_house"]
}
