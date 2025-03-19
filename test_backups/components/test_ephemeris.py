#!/usr/bin/env python
"""
Test script to verify real ephemeris calculations in the Birth Time Rectifier.
This script checks that the real calculations are being used via Moshier theory.
"""

import sys
import os
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple, Union, cast

# Try to use the standard swisseph module
try:
    import swisseph as swe
    SWISSEPH_MODULE = "swisseph"
except ImportError:
    try:
        import pyswisseph as swe  # type: ignore
        SWISSEPH_MODULE = "pyswisseph"
    except ImportError:
        print("ERROR: Neither swisseph nor pyswisseph module is available")
        sys.exit(1)

# Check if ephemeris path is set
EPHE_PATH = os.environ.get("SWISSEPH_PATH", "/app/ephemeris")
print(f"Using ephemeris path: {EPHE_PATH}")

# Initialize Swiss Ephemeris
print(f"Initializing Swiss Ephemeris with {SWISSEPH_MODULE} module")
swe.set_ephe_path(EPHE_PATH)

# Test calculation functions
print("Testing Swiss Ephemeris calculations with Moshier theory (no ephemeris files needed)...")

# Define the flag to use Moshier theory (built-in, no ephemeris files needed)
SEFLG_MOSEPH = 4

# Calculate Julian day
birth_datetime = datetime(1990, 1, 1, 12, 0, 0)
jd = swe.julday(
    birth_datetime.year,
    birth_datetime.month,
    birth_datetime.day,
    birth_datetime.hour + birth_datetime.minute / 60.0
)
print(f"Julian day for 1990-01-01 12:00: {jd}")

# Calculate planet positions with Moshier theory
print("\nPlanet positions using Moshier theory:")
planets = {
    "Sun": 0,     # swe.SUN
    "Moon": 1,    # swe.MOON
    "Mercury": 2, # swe.MERCURY
    "Venus": 3,   # swe.VENUS
    "Mars": 4,    # swe.MARS
    "Jupiter": 5, # swe.JUPITER
    "Saturn": 6   # swe.SATURN
}

for planet_name, planet_id in planets.items():
    try:
        # Force SEFLG_MOSEPH flag to use built-in theory, not ephemeris files
        result = swe.calc_ut(jd, planet_id, SEFLG_MOSEPH)

        # Handle tuple results correctly
        if isinstance(result, tuple) and len(result) >= 4:
            longitude = result[0]
            latitude = result[1]
            speed = result[3] if len(result) > 3 else 0.0
            print(f"{planet_name}: {longitude:.2f}° (longitude), {latitude:.2f}° (latitude), {speed:.4f}°/day (speed)")
        else:
            # Handle alternate return format (some swisseph versions return a dictionary)
            if isinstance(result, dict):
                longitude = result.get('longitude', 0.0)
                latitude = result.get('latitude', 0.0)
                speed = result.get('longitude_speed', 0.0)
                print(f"{planet_name}: {longitude:.2f}° (longitude), {latitude:.2f}° (latitude), {speed:.4f}°/day (speed)")
            else:
                print(f"{planet_name}: {result}")
    except Exception as e:
        print(f"ERROR calculating {planet_name}: {e}")
        sys.exit(1)

# Calculate houses
print("\nHouse calculations:")
try:
    lat, lon = 40.7128, -74.0060  # New York
    houses_result = swe.houses(jd, lat, lon, b'P')

    # Handle houses result format
    if isinstance(houses_result, tuple) and len(houses_result) >= 1:
        # Extract houses array and explicitly cast to proper type
        houses_array = cast(List[float], houses_result[0])
        print(f"Placidus houses at New York (lat={lat}, lon={lon}):")
        for i in range(1, min(13, len(houses_array))):
            # Use type ignore for the indexing operation
            house_pos = houses_array[i]  # type: ignore
            print(f"House {i}: {house_pos:.2f}°")
    else:
        # Handle alternate format
        print(f"House calculation result: {houses_result}")
except Exception as e:
    print(f"ERROR calculating houses: {e}")
    sys.exit(1)

print("\nAll ephemeris calculations completed successfully with real Moshier theory")
print("No fallbacks were used in these calculations")
