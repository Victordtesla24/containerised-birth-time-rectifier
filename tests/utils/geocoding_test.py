#!/usr/bin/env python3
"""
Direct test script for geocoding functionality.
This script tests the geocoding functions directly without going through the API.
"""

import asyncio
import logging
import sys
import os
import traceback
import socket
from pathlib import Path
import time
import requests

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("geocoding_test")

# Import geocoding functions from the module
from ai_service.api.routers.geocode import (
    geocode_location,
    get_timezone_for_coordinates,
    nominatim_geocode_direct
)

# Test network connectivity first
def test_network_connectivity():
    """Test basic network connectivity to common geocoding services."""
    logger.info("Testing network connectivity...")

    services = [
        ("nominatim.openstreetmap.org", 443),
        ("maps.googleapis.com", 443),
        ("atlas.microsoft.com", 443)
    ]

    for hostname, port in services:
        try:
            start_time = time.time()
            # Test TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((hostname, port))
            sock.close()

            if result == 0:
                logger.info(f"✅ TCP connection to {hostname}:{port} successful ({time.time() - start_time:.2f}s)")
            else:
                logger.error(f"❌ TCP connection to {hostname}:{port} failed with error code {result}")

            # Test HTTP/HTTPS request
            try:
                start_time = time.time()
                response = requests.get(f"https://{hostname}/", timeout=5)
                logger.info(f"✅ HTTP request to {hostname} successful: {response.status_code} ({time.time() - start_time:.2f}s)")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ HTTP request to {hostname} failed: {e}")

        except Exception as e:
            logger.error(f"❌ Connection to {hostname}:{port} failed: {e}")

async def test_nominatim_direct():
    """Test Nominatim directly using requests."""
    try:
        logger.info("Testing Nominatim directly with requests...")
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": "New York City",
            "format": "json",
            "addressdetails": 1,
            "limit": 1
        }
        headers = {
            "User-Agent": "birth-time-rectifier/2.0 Test Script"
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data:
                logger.info(f"✅ Direct Nominatim test with requests successful: {data[0].get('display_name')}")
                return True
            else:
                logger.error("❌ Direct Nominatim test with requests returned no results")
                return False
        else:
            logger.error(f"❌ Direct Nominatim test with requests failed with status code: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Direct Nominatim test with requests failed with error: {e}")
        traceback.print_exc()
        return False

async def test_direct_nominatim_impl():
    """Test our direct Nominatim implementation."""
    try:
        logger.info("Testing our direct Nominatim implementation...")
        test_location = "New York City"

        results = await nominatim_geocode_direct(test_location)

        if results and len(results) > 0:
            logger.info(f"✅ Our direct Nominatim implementation successful: {results[0].get('address')}")
            # Store the first result for testing timezone
            location = results[0]
            latitude = location.get("latitude")
            longitude = location.get("longitude")

            # Ensure latitude and longitude are floats and not None
            if latitude is not None and longitude is not None:
                latitude_float = float(latitude) if isinstance(latitude, str) else latitude
                longitude_float = float(longitude) if isinstance(longitude, str) else longitude

                logger.info(f"Testing get_timezone_for_coordinates for: {latitude_float}, {longitude_float}...")
                timezone_info = await get_timezone_for_coordinates(latitude_float, longitude_float)

                if timezone_info:
                    logger.info(f"✅ Timezone lookup successful: {timezone_info}")
                    return True
                else:
                    logger.error("❌ Timezone lookup failed")
                    return False
            else:
                logger.error("❌ Invalid coordinates in direct Nominatim result")
                return False
        else:
            logger.error("❌ Our direct Nominatim implementation returned no results")
            return False
    except Exception as e:
        logger.error(f"❌ Our direct Nominatim implementation failed with error: {e}")
        traceback.print_exc()
        return False

async def test_geocoding():
    """Test the main geocoding functionality."""
    try:
        # Test location
        test_location = "New York City"
        logger.info(f"Testing full geocoding for location: {test_location}")

        # Test geocode_location function
        logger.info("Testing geocode_location...")
        results = await geocode_location(test_location)

        if not results:
            logger.error(f"❌ No geocoding results found for '{test_location}'")
            return False

        logger.info(f"Geocoding results: {results}")

        # Get the first result to test timezone functionality
        if results and len(results) > 0:
            location = results[0]
            latitude = location.get("latitude")
            longitude = location.get("longitude")

            # Check if latitude and longitude are valid
            if latitude is not None and longitude is not None:
                # Ensure they are float values
                latitude_float = float(latitude) if isinstance(latitude, str) else latitude
                longitude_float = float(longitude) if isinstance(longitude, str) else longitude

                logger.info(f"Testing get_timezone_for_coordinates for: {latitude_float}, {longitude_float}...")
                timezone_info = await get_timezone_for_coordinates(latitude_float, longitude_float)

                if timezone_info:
                    logger.info(f"Timezone info: {timezone_info}")
                    logger.info(f"✅ All geocoding tests passed for location: {test_location}")
                    return True
                else:
                    logger.error(f"❌ Failed to get timezone for coordinates: {latitude_float}, {longitude_float}")
                    return False
            else:
                logger.error(f"❌ Invalid coordinates in geocoding result: {location}")
                return False
        else:
            logger.error(f"❌ No geocoding results available for '{test_location}'")
            return False
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # First test network connectivity
    test_network_connectivity()

    # Then test direct Nominatim access with requests
    asyncio.run(test_nominatim_direct())

    # Test our direct implementation
    asyncio.run(test_direct_nominatim_impl())

    # Finally, test the full geocoding implementation
    asyncio.run(test_geocoding())
