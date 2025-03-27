"""
Direct test for the geocoder module.
This test bypasses the API Gateway and calls the geocoder module directly.
"""

import os
import json
import logging
from pathlib import Path
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_LOCATION = "Pune, India"

def test_geocoder_direct():
    """Test the geocoder module directly without going through the API Gateway."""
    logger.info(f"Starting direct geocoder test for '{TEST_LOCATION}'")

    # Import the test geocoder directly
    from ai_service.utils.test_geocoder import geocode_location

    # Start the timer
    start_time = time.time()

    try:
        # Call the geocoder directly
        logger.info("Calling geocode_location function directly...")
        result = geocode_location(TEST_LOCATION)

        # Calculate elapsed time
        elapsed = time.time() - start_time
        logger.info(f"Geocoding completed in {elapsed:.2f} seconds")

        # Check the result
        assert "results" in result, "Response should contain 'results' field"
        assert isinstance(result["results"], list), "Results should be a list"

        # Even if multiple results, check if at least one was found
        assert len(result["results"]) > 0, "No geocoding results found"

        # Get the first result for validation
        location = result["results"][0]

        # Check that the location has the required fields
        for field in ["latitude", "longitude", "timezone"]:
            assert field in location, f"Location result missing required field: {field}"

        # Verify country and timezone data are sensible for India
        assert location["country"] == "India", f"Expected country to be 'India', got '{location.get('country')}'"
        assert location["country_code"] == "IN", f"Expected country code to be 'IN', got '{location.get('country_code')}'"

        # Check if timezone is appropriate for India (common timezones for India)
        assert location["timezone"] == "Asia/Kolkata", f"Unexpected timezone for India: {location['timezone']}"

        logger.info(f"Geocoding successful with timezone {location['timezone']}")
        logger.info(f"Location: {location['name']} ({location['latitude']}, {location['longitude']})")

        # Don't return a value - pytest doesn't want that

    except Exception as e:
        logger.error(f"Direct geocoder test failed: {e}")
        raise

if __name__ == "__main__":
    # Run this test standalone for debugging
    test_geocoder_direct()
