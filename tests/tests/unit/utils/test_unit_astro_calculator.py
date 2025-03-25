"""
Component tests for the AstroCalculator class.
These tests validate the astrological calculations required by the sequence diagram flow.
"""

import pytest
import asyncio
import os
import math
from datetime import datetime, timezone
import pytz
import swisseph as swe

from ai_service.core.astro_calculator import AstroCalculator, get_astro_calculator

@pytest.fixture
def astro_calculator():
    """Create a real astro calculator instance."""
    # Check if ephemeris path is set or use a default test path
    ephe_path = os.environ.get("SWISSEPH_PATH", "/app/ephemeris")

    # If the path doesn't exist in the test environment, use a mock path
    # This is the only mock we allow to enable testing without requiring full ephemeris data
    if not os.path.isdir(ephe_path):
        # For tests, use the built-in ephemeris from swisseph
        swisseph_path = os.path.dirname(swe.__file__)
        ephe_path = os.path.join(swisseph_path, 'ephemeris')
        os.environ["SWISSEPH_PATH"] = ephe_path

    return AstroCalculator(ephe_path=ephe_path)

@pytest.mark.asyncio
async def test_calculate_chart(astro_calculator):
    """Test chart calculation with real calculations."""
    # Test data
    birth_date = "1990-01-01"
    birth_time = "12:00:00"
    latitude = 40.7128  # New York
    longitude = -74.0060
    timezone = "America/New_York"

    # Calculate chart
    chart = await astro_calculator.calculate_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        include_aspects=True,
        include_houses=True
    )

    # Verify chart structure
    assert isinstance(chart, dict)
    assert "julian_day" in chart
    assert "positions" in chart
    assert "planets" in chart
    assert "houses" in chart
    assert "aspects" in chart
    assert "ascendant" in chart

    # Verify birth details were recorded correctly
    assert "birth_details" in chart
    birth_details = chart["birth_details"]
    assert birth_details["birth_date"] == birth_date
    assert birth_details["birth_time"] == birth_time
    assert birth_details["latitude"] == latitude
    assert birth_details["longitude"] == longitude
    assert birth_details["timezone"] == timezone

    # Verify planet positions
    planets = chart["planets"]
    assert "sun" in planets
    assert "moon" in planets
    assert "mercury" in planets
    assert "venus" in planets
    assert "mars" in planets
    assert "jupiter" in planets
    assert "saturn" in planets

    # Check specific planet data structure
    sun = planets["sun"]
    assert "longitude" in sun
    assert "latitude" in sun
    assert "distance" in sun
    assert "speed" in sun

    # Verify houses
    houses = chart["houses"]
    assert len(houses) == 12

    # Verify ascendant
    ascendant = chart["ascendant"]
    assert "longitude" in ascendant
    assert "sign" in ascendant
    assert "degree" in ascendant

    # Verify aspects
    aspects = chart["aspects"]
    assert isinstance(aspects, list)
    if len(aspects) > 0:
        aspect = aspects[0]
        assert "planet1" in aspect
        assert "planet2" in aspect
        assert "aspect" in aspect
        assert "orb" in aspect

@pytest.mark.asyncio
async def test_calculate_chart_different_house_systems(astro_calculator):
    """Test chart calculation with different house systems."""
    # Test data
    birth_date = "1990-01-01"
    birth_time = "12:00:00"
    latitude = 40.7128
    longitude = -74.0060
    timezone = "America/New_York"

    # Test different house systems
    house_systems = ["P", "K", "O", "R", "C", "A", "W", "B"]

    for system in house_systems:
        # Calculate chart with specific house system
        chart = await astro_calculator.calculate_chart(
            birth_date=birth_date,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            house_system=system
        )

        # Verify houses were calculated
        assert "houses" in chart
        assert len(chart["houses"]) == 12

        # Verify ascendant was calculated
        assert "ascendant" in chart
        assert chart["ascendant"]["longitude"] >= 0
        assert chart["ascendant"]["longitude"] < 360

@pytest.mark.asyncio
async def test_calculate_chart_tropical_vs_sidereal(astro_calculator):
    """Test chart calculation with tropical vs sidereal calculations."""
    # Test data
    birth_date = "1990-01-01"
    birth_time = "12:00:00"
    latitude = 40.7128
    longitude = -74.0060
    timezone = "America/New_York"

    # Calculate chart using default sidereal settings
    sidereal_chart = await astro_calculator.calculate_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Save sidereal sun position
    sidereal_sun = sidereal_chart["planets"]["sun"]["longitude"]

    # Create a tropical calculator with no ayanamsa
    tropical_calculator = AstroCalculator(ephe_path=astro_calculator.ephe_path, ayanamsa_type=0)

    # Calculate chart using tropical settings
    tropical_chart = await tropical_calculator.calculate_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone
    )

    # Save tropical sun position
    tropical_sun = tropical_chart["planets"]["sun"]["longitude"]

    # The difference should be approximately the ayanamsa value
    # Lahiri ayanamsa is around 24 degrees
    difference = (tropical_sun - sidereal_sun) % 360
    assert 20 <= difference <= 30  # Allowing some margin for precision differences

@pytest.mark.asyncio
async def test_calculate_divisional_charts(astro_calculator):
    """Test calculation of divisional charts for Vedic astrology."""
    # Test data
    birth_date = "1990-01-01"
    birth_time = "12:00:00"
    latitude = 40.7128
    longitude = -74.0060
    timezone = "America/New_York"

    # Calculate chart with divisional charts
    chart = await astro_calculator.calculate_chart(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        include_divisional_charts=True
    )

    # Verify divisional charts were calculated
    assert "divisional_charts" in chart
    divisional_charts = chart["divisional_charts"]

    # Check for common divisional charts
    divisional_types = ["D9", "D3", "D7"]
    for chart_type in divisional_types:
        assert chart_type in divisional_charts

def test_datetime_to_jd(astro_calculator):
    """Test conversion of datetime to Julian day."""
    # Test case: J2000.0 epoch
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Calculate Julian day
    jd = astro_calculator._datetime_to_jd(dt)

    # J2000.0 epoch is defined as JD 2451545.0
    assert abs(jd - 2451545.0) < 0.001

def test_aspect_calculation(astro_calculator):
    """Test calculation of planetary aspects."""
    # Create test position data
    positions = {
        "sun": {"longitude": 0.0, "speed": 1.0},  # 0° Aries
        "moon": {"longitude": 60.0, "speed": 13.0},  # 0° Gemini (60° from Sun)
        "saturn": {"longitude": 90.0, "speed": 0.1},  # 0° Cancer (90° from Sun)
        "jupiter": {"longitude": 180.0, "speed": 0.2},  # 0° Libra (180° from Sun)
    }

    # Calculate aspects
    aspects = astro_calculator._calculate_aspects(positions)

    # Verify aspects
    assert isinstance(aspects, list)

    # Find Sun-Moon aspect (should be sextile - 60°)
    sun_moon_aspect = next((a for a in aspects if
                           (a["planet1"] == "sun" and a["planet2"] == "moon") or
                           (a["planet1"] == "moon" and a["planet2"] == "sun")), None)
    assert sun_moon_aspect is not None
    assert sun_moon_aspect["aspect"] == "sextile"
    assert sun_moon_aspect["angle"] == 60
    assert sun_moon_aspect["orb"] < 5  # Orb should be small

    # Find Sun-Saturn aspect (should be square - 90°)
    sun_saturn_aspect = next((a for a in aspects if
                             (a["planet1"] == "sun" and a["planet2"] == "saturn") or
                             (a["planet1"] == "saturn" and a["planet2"] == "sun")), None)
    assert sun_saturn_aspect is not None
    assert sun_saturn_aspect["aspect"] == "square"
    assert sun_saturn_aspect["angle"] == 90
    assert sun_saturn_aspect["orb"] < 5  # Orb should be small

    # Find Sun-Jupiter aspect (should be opposition - 180°)
    sun_jupiter_aspect = next((a for a in aspects if
                              (a["planet1"] == "sun" and a["planet2"] == "jupiter") or
                              (a["planet1"] == "jupiter" and a["planet2"] == "sun")), None)
    assert sun_jupiter_aspect is not None
    assert sun_jupiter_aspect["aspect"] == "opposition"
    assert sun_jupiter_aspect["angle"] == 180
    assert sun_jupiter_aspect["orb"] < 5  # Orb should be small

def test_get_astro_calculator_singleton():
    """Test the singleton factory function for AstroCalculator."""
    # Get an instance from the factory
    calculator1 = get_astro_calculator()

    # Get another instance
    calculator2 = get_astro_calculator()

    # They should be the same instance
    assert calculator1 is calculator2
    assert isinstance(calculator1, AstroCalculator)
