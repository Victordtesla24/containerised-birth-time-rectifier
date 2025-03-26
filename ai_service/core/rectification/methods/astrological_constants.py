"""
Astrological constants for points not directly provided by Swiss Ephemeris.

This module defines constants for astrological points that aren't directly
defined in the pyswisseph library but are commonly used in astrological calculations.
"""
import swisseph as swe

# House points/angles already in pyswisseph
ASC = swe.ASC  # Ascendant (0)
MC = swe.MC    # Midheaven (1)

# House points/angles not in pyswisseph
# DSC - Descendant (opposite to Ascendant)
DSC = 100  # Custom constant for Descendant

# IC - Imum Coeli (opposite to Midheaven)
IC = 101  # Custom constant for Imum Coeli

# Other useful astrological constants can be added here
VERTEX = swe.VERTEX  # Already in pyswisseph (3)

# Lots and special points
LOT_OF_FORTUNE = 102
PART_OF_SPIRIT = 103

# Modern planets that might not be in older pyswisseph versions
URANUS = swe.URANUS  # Already in pyswisseph (7)
NEPTUNE = swe.NEPTUNE  # Already in pyswisseph (8)
PLUTO = swe.PLUTO  # Already in pyswisseph (9)
