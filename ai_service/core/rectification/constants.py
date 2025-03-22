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
