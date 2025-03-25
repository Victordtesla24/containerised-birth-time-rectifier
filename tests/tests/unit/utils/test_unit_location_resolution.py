"""
Component tests for location resolution and timezone conversion.

These tests verify the functionality of geocoding and timezone utilities.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import the modules to test
from ai_service.utils.geocoding import geocode_location, GeocodingError, get_coordinates
from ai_service.utils.timezone import get_timezone_for_coordinates, TimezoneError

# Test data
TEST_LOCATION = "New York City, NY, USA"
TEST_LATITUDE = 40.7128
TEST_LONGITUDE = -74.0060
TEST_TIMEZONE = "America/New_York"

# Mock geocoding response
MOCK_GEOCODE_RESPONSE = {
    "name": "New York City, New York, USA",
    "latitude": TEST_LATITUDE,
    "longitude": TEST_LONGITUDE,
    "country": "United States",
    "country_code": "US",
    "raw": {
        "address": {
            "city": "New York City",
            "state": "New York",
            "country": "United States",
            "country_code": "us"
        }
    }
}

class TestGeocoding:
    """Test suite for geocoding functionality."""

    def test_geocode_valid_location(self):
        """Test geocoding a valid location."""
        with patch('ai_service.utils.geocoding.Nominatim') as mock_nominatim:
            # Configure the mock
            mock_geocoder = MagicMock()
            mock_nominatim.return_value = mock_geocoder

            # Configure the geocode method
            mock_location = MagicMock()
            mock_location.latitude = TEST_LATITUDE
            mock_location.longitude = TEST_LONGITUDE
            mock_location.address = "New York City, New York, USA"
            mock_location.raw = {
                "address": {
                    "country": "United States",
                    "country_code": "us"
                }
            }
            mock_geocoder.geocode.return_value = mock_location

            # Call the function
            result = geocode_location(TEST_LOCATION)

            # Verify
            mock_nominatim.assert_called_once()
            mock_geocoder.geocode.assert_called_once()
            assert result["latitude"] == TEST_LATITUDE
            assert result["longitude"] == TEST_LONGITUDE
            assert result["name"] == "New York City, New York, USA"
            assert result["country"] == "United States"

    def test_geocode_invalid_location(self):
        """Test geocoding an invalid location raises an exception."""
        with patch('ai_service.utils.geocoding.Nominatim') as mock_nominatim:
            # Configure the mock
            mock_geocoder = MagicMock()
            mock_nominatim.return_value = mock_geocoder

            # Configure to return None for invalid location
            mock_geocoder.geocode.return_value = None

            # Test with an invalid location
            with pytest.raises(GeocodingError):
                geocode_location("XYZ123NonExistentPlace")

    def test_geocode_empty_location(self):
        """Test geocoding an empty location raises an exception."""
        # Test with an empty location
        with pytest.raises(GeocodingError):
            geocode_location("")

        # Test with None-like value (using empty string to avoid type error)
        with pytest.raises(GeocodingError):
            geocode_location("   ")

    def test_get_coordinates(self):
        """Test getting coordinates for a location."""
        with patch('ai_service.utils.geocoding.geocode_location') as mock_geocode:
            # Configure the mock
            mock_geocode.return_value = MOCK_GEOCODE_RESPONSE

            # Call the function
            lat, lon = get_coordinates(TEST_LOCATION)

            # Verify
            mock_geocode.assert_called_once_with(TEST_LOCATION)
            assert lat == TEST_LATITUDE
            assert lon == TEST_LONGITUDE

class TestTimezones:
    """Test suite for timezone functionality."""

    def test_get_timezone_valid_coordinates(self):
        """Test getting timezone for valid coordinates."""
        with patch('ai_service.utils.timezone._timezone_finder') as mock_finder:
            # Configure the mock
            mock_finder.timezone_at.return_value = TEST_TIMEZONE

            # Call the function
            result = get_timezone_for_coordinates(TEST_LATITUDE, TEST_LONGITUDE)

            # Verify
            mock_finder.timezone_at.assert_called_once_with(lat=TEST_LATITUDE, lng=TEST_LONGITUDE)
            assert result == TEST_TIMEZONE

    def test_get_timezone_invalid_coordinates(self):
        """Test getting timezone for invalid coordinates raises an exception."""
        # Test with invalid latitude
        with pytest.raises(ValueError):
            get_timezone_for_coordinates(91.0, TEST_LONGITUDE)

        # Test with invalid longitude
        with pytest.raises(ValueError):
            get_timezone_for_coordinates(TEST_LATITUDE, 181.0)

    def test_get_timezone_error(self):
        """Test handling errors in timezone resolution."""
        with patch('ai_service.utils.timezone._timezone_finder') as mock_finder:
            # Configure the mock to return None
            mock_finder.timezone_at.return_value = None
            mock_finder.closest_timezone_at.return_value = None

            # Call the function and assert it raises the expected exception
            with pytest.raises(TimezoneError):
                get_timezone_for_coordinates(0.0, 0.0)  # Middle of the ocean

            # Verify the mocks were called
            mock_finder.timezone_at.assert_called_once_with(lat=0.0, lng=0.0)
            mock_finder.closest_timezone_at.assert_called_once()

class TestIntegration:
    """Integration tests for geocoding and timezone functionality."""

    def test_location_to_timezone_flow(self):
        """Test the flow from location to timezone."""
        with patch('ai_service.utils.geocoding.geocode_location') as mock_geocode:
            with patch('ai_service.utils.timezone.get_timezone_for_coordinates') as mock_timezone:
                # Configure the mocks
                mock_geocode.return_value = MOCK_GEOCODE_RESPONSE
                mock_timezone.return_value = TEST_TIMEZONE

                # Execute the flow
                location_data = geocode_location(TEST_LOCATION)
                timezone = get_timezone_for_coordinates(
                    location_data["latitude"],
                    location_data["longitude"]
                )

                # Verify
                mock_geocode.assert_called_once_with(TEST_LOCATION)
                mock_timezone.assert_called_once_with(TEST_LATITUDE, TEST_LONGITUDE)
                assert location_data["latitude"] == TEST_LATITUDE
                assert location_data["longitude"] == TEST_LONGITUDE
                assert timezone == TEST_TIMEZONE
