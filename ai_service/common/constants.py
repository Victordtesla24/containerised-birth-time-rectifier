"""
Common constants for the Birth Time Rectifier application.
"""

# Questionnaire related constants
QUESTION_TEMPLATES = {
    "birth_time": [
        {
            "id": "q_birth_time_general",
            "text": "Do you know your approximate birth time?",
            "type": "multiple_choice",
            "options": [
                {"id": "opt_exact", "text": "Yes, I have an exact time"},
                {"id": "opt_approximate", "text": "I have an approximate time"},
                {"id": "opt_window", "text": "I know a time window (e.g., morning, afternoon)"},
                {"id": "opt_unknown", "text": "I don't know my birth time"}
            ]
        },
        {
            "id": "q_birth_time_source",
            "text": "What is the source of your birth time information?",
            "type": "multiple_choice",
            "options": [
                {"id": "opt_birth_cert", "text": "Birth certificate"},
                {"id": "opt_hospital", "text": "Hospital records"},
                {"id": "opt_parent", "text": "Parent's recollection"},
                {"id": "opt_relative", "text": "Other relative's recollection"},
                {"id": "opt_other", "text": "Other source"}
            ]
        }
    ],
    "life_events": [
        {
            "id": "q_major_life_events",
            "text": "Please list any major life events with their dates (as specific as possible)",
            "type": "text"
        },
        {
            "id": "q_marriage",
            "text": "If applicable, when did you get married or enter a significant partnership?",
            "type": "date"
        },
        {
            "id": "q_career_change",
            "text": "When did you experience a significant career change or milestone?",
            "type": "date"
        }
    ],
    "appearance": [
        {
            "id": "q_appearance",
            "text": "How would you describe your physical appearance?",
            "type": "text"
        },
        {
            "id": "q_personality",
            "text": "How would close friends or family describe your personality?",
            "type": "text"
        }
    ]
}

# Astrological constants
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

PLANETS = [
    "Sun", "Moon", "Mercury", "Venus",
    "Mars", "Jupiter", "Saturn", "Uranus",
    "Neptune", "Pluto"
]

HOUSES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

# API related constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_TIMEOUT = 60  # seconds

# Chart calculation constants
DEFAULT_AYANAMSA = "LAHIRI"  # Default ayanamsa for Vedic calculations
