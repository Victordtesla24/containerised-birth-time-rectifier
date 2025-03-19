"""
Utility tests for astrological calculations.

These tests ensure that the astrological calculation utilities work correctly.
No mocks, stubs, or fallbacks are used.
"""

import pytest
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the utilities
from ai_service.core.astro_calculator import AstroCalculator
from ai_service.core.chart_calculator import calculate_chart
from ai_service.api.services.openai.service import get_openai_service


def test_astro_calculator_initialization():
    """Test that the AstroCalculator can be properly initialized."""
    # Initialize with real ephemeris path
    calculator = AstroCalculator(ephe_path="/app/ephemeris")

    # Check that the calculator was initialized
    assert calculator is not None
    # Verify it works by trying a calculation that should succeed if initialized properly
    test_date = datetime(1990, 1, 1, 12, 0, 0)
    jd = calculator._datetime_to_jd(test_date)
    assert jd > 0


def test_astro_planet_calculations():
    """Test actual planetary calculations with the Swiss Ephemeris."""
    # Initialize calculator with real ephemeris
    calculator = AstroCalculator(ephe_path="/app/ephemeris")

    # Set a test date and location
    test_date = datetime(1990, 1, 1, 12, 0, 0)
    latitude = 40.7128
    longitude = -74.0060

    # Calculate Julian day
    jd = calculator._datetime_to_jd(test_date)

    # Calculate planetary positions
    positions = calculator._calculate_positions(jd)

    # Check if positions were calculated
    assert isinstance(positions, dict)
    assert len(positions) > 0

    # Check structure for a planet (e.g., Sun)
    for planet_name, planet_data in positions.items():
        assert isinstance(planet_data, dict)
        assert "longitude" in planet_data
        assert 0 <= planet_data["longitude"] < 360
        break


def test_house_calculations():
    """Test actual house calculations with the Swiss Ephemeris."""
    # Initialize calculator with real ephemeris
    calculator = AstroCalculator(ephe_path="/app/ephemeris")

    # Set a test date and location
    test_date = datetime(1990, 1, 1, 12, 0, 0)
    latitude = 40.7128
    longitude = -74.0060

    # Calculate Julian day
    jd = calculator._datetime_to_jd(test_date)

    # Calculate houses using the Whole Sign system ("W")
    houses = calculator._calculate_houses(jd, latitude, longitude, "W")

    # Verify structure of result
    assert isinstance(houses, list)
    assert len(houses) >= 12  # Should have at least 12 house cusps

    # All cusps should be between 0-360 degrees
    for cusp in houses:
        assert 0 <= cusp < 360


def test_chart_calculation():
    """Test that the chart calculation works with real calculations."""
    # Calculate a chart using the function directly
    chart_data = calculate_chart(
        birth_date="1990-01-01",
        birth_time="12:00:00",
        latitude=40.7128,
        longitude=-74.0060,
        location="New York, NY"
    )

    # Check chart data structure
    assert isinstance(chart_data, dict)
    assert "ascendant" in chart_data
    assert "planets" in chart_data
    assert "houses" in chart_data

    # Check ascendant
    assert "sign" in chart_data["ascendant"]
    assert "degree" in chart_data["ascendant"]

    # Check planets
    planets = chart_data["planets"]
    assert len(planets) >= 7  # Should have at least 7 major planets

    # Check houses
    houses = chart_data["houses"]
    assert len(houses) >= 12  # Should have 12 houses


@pytest.mark.asyncio
async def test_openai_integration():
    """Test that OpenAI service works with real API calls."""
    # Get real OpenAI service
    openai_service = get_openai_service()

    # Make a simple API call
    response = await openai_service.generate_completion(
        prompt="Provide a brief explanation of astrological chart rectification.",
        task_type="explanation",
        max_tokens=100
    )

    # Check response
    assert isinstance(response, dict)
    assert "content" in response
    assert len(response["content"]) > 0
    assert "tokens" in response
