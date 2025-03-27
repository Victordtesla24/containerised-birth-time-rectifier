"""
Unit tests for the formatting utility functions.

This module tests various formatting functions for astrological data.
"""

import pytest
from datetime import datetime
from ai_service.utils.formatting import (
    format_degree,
    format_longitude,
    format_time,
    format_aspect,
    format_planet_position
)

class TestFormatting:
    """Test cases for formatting utilities."""

    def test_format_degree(self):
        """Test formatting of degrees."""
        # Test basic degree formatting
        assert format_degree(15.5) == "15°30'"
        # Degrees are normalized to 0-30 range within a sign
        assert format_degree(359.99) == "29°59'"

        # Test with zodiac sign
        assert format_degree(15.5, include_sign=True) == "Aries 15°30'"
        assert format_degree(45.5, include_sign=True) == "Taurus 15°30'"

        # Test without minutes
        assert format_degree(15.5, include_minutes=False) == "15°"

    def test_format_longitude(self):
        """Test formatting of celestial longitudes."""
        # Test full format
        assert format_longitude(15.5) == "Aries 15°30'"
        assert format_longitude(45.5) == "Taurus 15°30'"

        # Test sign only format
        assert format_longitude(15.5, format_type="sign_only") == "Aries"
        assert format_longitude(45.5, format_type="sign_only") == "Taurus"

        # Test degree only format
        assert format_longitude(15.5, format_type="degree_only") == "15°30'"
        assert format_longitude(45.5, format_type="degree_only") == "15°30'"

    def test_format_time(self):
        """Test time formatting."""
        # Test datetime object
        dt = datetime(2023, 1, 1, 14, 30, 45)
        assert format_time(dt) == "14:30:45"
        assert format_time(dt, include_seconds=False) == "14:30"

        # Test string inputs that match expected formats
        assert format_time("14:30:45") == "14:30:45"
        # The function includes seconds by default
        assert format_time("14:30") == "14:30:00"
        assert format_time("14:30", include_seconds=False) == "14:30"

        # Test unrecognized format - should return as is
        unrecognized = "Unknown format"
        assert format_time(unrecognized) == unrecognized

        # 12-hour format with AM/PM - parsed and converted to 24h format
        assert format_time("02:30 PM") in ["14:30:00", "02:30 PM"]

    def test_format_aspect(self):
        """Test formatting of astrological aspects."""
        # Test known aspects with symbols
        assert format_aspect("conjunction", 0.5) == "☌ (0.5°)"
        assert format_aspect("trine", 1.2) == "△ (1.2°)"
        assert format_aspect("square", 2.5) == "□ (2.5°)"

        # Test unknown aspect (should use capitalized name)
        assert format_aspect("nonstandard", 0.8) == "Nonstandard (0.8°)"

    def test_format_planet_position(self):
        """Test formatting of planet positions."""
        # Test without house
        assert format_planet_position("Sun", "Aries", 15.5) == "☉ Aries 15°30'"
        assert format_planet_position("Moon", "Taurus", 10.25) == "☽ Taurus 10°15'"

        # Test with house
        assert format_planet_position("Sun", "Aries", 15.5, house=1) == "☉ Aries 15°30' (House 1)"

        # Test non-standard planet (should use name as is)
        assert format_planet_position("Chiron", "Gemini", 5.75) == "Chiron Gemini 5°45'"
