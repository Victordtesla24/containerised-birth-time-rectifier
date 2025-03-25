#!/usr/bin/env python3
"""
Direct test script for geocoding functionality.
This script tests the geocoding functions directly without going through the API.
"""

import asyncio
import logging
import sys
from ai_service.utils.geocoding import (
    geocode_location,
    get_coordinates,
    get_timezone_for_coordinates
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("geocoding_test")

async def test_geocoding():
    """Test geocoding functionality directly."""
    # Test location
    test_location = "Pune, India"

    logger.info(f"Testing geocoding for location: {test_location}")

    # Test geocode_location function
    logger.info("Testing geocode_location...")
    results = await geocode_location(test_location)
    logger.info(f"Geocode results: {results}")

    if not results:
        logger.error(f"❌ No geocoding results found for '{test_location}'")
        return False

    # Test get_coordinates function
    logger.info("Testing get_coordinates...")
    latitude, longitude = await get_coordinates(test_location)
    logger.info(f"Coordinates: {latitude}, {longitude}")

    if latitude is None or longitude is None:
        logger.error(f"❌ Failed to get coordinates for '{test_location}'")
        return False

    # Test get_timezone_for_coordinates function
    logger.info("Testing get_timezone_for_coordinates...")
    timezone_info = await get_timezone_for_coordinates(latitude, longitude)
    logger.info(f"Timezone info: {timezone_info}")

    if not timezone_info or 'timezone_id' not in timezone_info:
        logger.error(f"❌ Failed to get timezone for coordinates: {latitude}, {longitude}")
        return False

    logger.info(f"✅ All geocoding tests passed for location: {test_location}")
    return True

def main():
    """Run the geocoding tests."""
    logger.info("Starting geocoding tests...")

    # Run the async test
    try:
        success = asyncio.run(test_geocoding())

        if success:
            logger.info("✅ All geocoding tests completed successfully")
            return 0
        else:
            logger.error("❌ Some geocoding tests failed")
            return 1
    except Exception as e:
        logger.error(f"Error running geocoding tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
