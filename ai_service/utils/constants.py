"""
Constants for astrological calculations
"""

# Zodiac signs in order
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# House systems
PLACIDUS = "P"
KOCH = "K"
EQUAL = "E"
WHOLE_SIGN = "W"
CAMPANUS = "C"
REGIOMONTANUS = "R"
PORPHYRIUS = "O"
MORINUS = "M"
TOPOCENTRIC = "T"

# Ayanamsa values
AYANAMSA = {
    "lahiri": 23.6647,
    "raman": 23.6647,
    "krishnamurti": 23.73,
    "fagan_bradley": 24.8356,
    "tropical": 0.0
}
