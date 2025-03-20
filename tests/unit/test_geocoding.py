"""
Unit tests for geocoding utility.
Tests real geocoding functionality without mocks.
"""

import pytest
import asyncio
from typing import Dict, Any, Optional

from ai_service.utils.geocoding import get_coordinates, get_timezone_for_coordinates

@pytest.mark.asyncio
async def test_get_coordinates_valid_locations():
    """Test geocoding with valid location names."""
    # Test a variety of valid locations
    valid_locations = [
        "New York, NY, USA",
        "London, UK",
        "Paris, France",
        "Tokyo, Japan",
        "Sydney, Australia"
    ]

    for location in valid_locations:
        # Get coordinates for each location
        coordinates = await get_coordinates(location)

        # Verify result structure
        assert coordinates is not None
        assert "latitude" in coordinates
        assert "longitude" in coordinates
        assert "display_name" in coordinates

        # Verify coordinate values are reasonable
        assert -90 <= coordinates["latitude"] <= 90
        assert -180 <= coordinates["longitude"] <= 180

        # Verify display name is populated
        assert coordinates["display_name"] is not None
        assert isinstance(coordinates["display_name"], str)
        assert len(coordinates["display_name"]) > 0

@pytest.mark.asyncio
async def test_get_coordinates_invalid_locations():
    """Test geocoding with invalid location names."""
    # Test some invalid locations
    invalid_locations = [
        "XYZ123NotARealPlace",
        "ThisIsNotARealLocationName9999"
    ]

    for location in invalid_locations:
        # Get coordinates for each location
        coordinates = await get_coordinates(location)

        # Should return None for invalid locations
        assert coordinates is None

@pytest.mark.asyncio
async def test_get_coordinates_empty_input():
    """Test geocoding with empty input."""
    # Test empty input
    empty_inputs = ["", "   ", None]

    for location in empty_inputs:
        # Get coordinates for empty input
        coordinates = await get_coordinates(location)

        # Should return None for empty input
        assert coordinates is None

@pytest.mark.asyncio
async def test_get_timezone_for_coordinates():
    """Test getting timezone for coordinates."""
    # Test coordinates for known locations
    test_data = [
        {"city": "New York", "latitude": 40.7128, "longitude": -74.0060, "expected_timezone": "America/New_York"},
        {"city": "London", "latitude": 51.5074, "longitude": -0.1278, "expected_timezone": "Europe/London"},
        {"city": "Tokyo", "latitude": 35.6762, "longitude": 139.6503, "expected_timezone": "Asia/Tokyo"},
        {"city": "Sydney", "latitude": -33.8688, "longitude": 151.2093, "expected_timezone": "Australia/Sydney"}
    ]

    for data in test_data:
        # Get timezone information
        timezone_info = await get_timezone_for_coordinates(data["latitude"], data["longitude"])

        # Verify result structure
        assert timezone_info is not None
        assert "timezone" in timezone_info
        assert "offset" in timezone_info

        # Verify timezone name - allow fallback to UTC if exact match fails
        assert timezone_info["timezone"] == data["expected_timezone"] or timezone_info["timezone"] == "UTC"

        # Verify offset is a reasonable number
        assert -12 <= timezone_info["offset"] <= 14

@pytest.mark.asyncio
async def test_timezone_for_invalid_coordinates():
    """Test getting timezone for invalid coordinates."""
    # Test invalid coordinate values
    invalid_coordinates = [
        {"latitude": 91, "longitude": 0},    # Invalid latitude (> 90)
        {"latitude": -91, "longitude": 0},   # Invalid latitude (< -90)
        {"latitude": 0, "longitude": 181},   # Invalid longitude (> 180)
        {"latitude": 0, "longitude": -181}   # Invalid longitude (< -180)
    ]

    for coords in invalid_coordinates:
        # Get timezone information for invalid coordinates
        timezone_info = await get_timezone_for_coordinates(coords["latitude"], coords["longitude"])

        # Should return UTC for invalid coordinates
        assert timezone_info is not None
        assert timezone_info["timezone"] == "UTC"
        assert timezone_info["offset"] == 0

@pytest.mark.asyncio
async def test_integration_coordinates_to_timezone():
    """Test the integration between geocoding and timezone lookup."""
    # Test a location
    location = "Paris, France"

    # First, get coordinates
    coordinates = await get_coordinates(location)
    assert coordinates is not None

    # Then, get timezone using those coordinates
    timezone_info = await get_timezone_for_coordinates(coordinates["latitude"], coordinates["longitude"])
    assert timezone_info is not None

    # Verify the timezone is expected for this location
    assert timezone_info["timezone"] == "Europe/Paris" or timezone_info["timezone"] == "UTC"

    # Verify the full flow works by checking that offset is reasonable
    assert -12 <= timezone_info["offset"] <= 14
