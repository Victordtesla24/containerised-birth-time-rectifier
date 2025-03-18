"""
Geocoding utility for resolving location names to coordinates.
"""

import logging
import os
from typing import Dict, Optional, Any
import aiohttp

logger = logging.getLogger(__name__)

async def get_coordinates(location: str) -> Optional[Dict[str, float]]:
    """
    Convert a location name to coordinates using a geocoding service.

    Args:
        location: Location name as string (e.g., "New York", "Paris, France")

    Returns:
        Dictionary with latitude and longitude or None if location couldn't be resolved
    """
    # If location is empty, return None
    if not location or location.strip() == "":
        return None

    try:
        # Using Nominatim geocoding service (OpenStreetMap)
        # This is rate-limited and should be used with caching in production
        async with aiohttp.ClientSession() as session:
            # Build the URL for the geocoding request
            nominatim_url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": location,
                "format": "json",
                "limit": 1,
                # Add a custom user agent as required by Nominatim's usage policy
                "user-agent": "birth-time-rectifier-app"
            }

            # Send the request
            async with session.get(nominatim_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # Check if we got any results
                    if data and len(data) > 0:
                        first_result = data[0]
                        # Extract latitude and longitude
                        latitude = float(first_result.get("lat", 0))
                        longitude = float(first_result.get("lon", 0))

                        logger.info(f"Resolved location '{location}' to coordinates: lat={latitude}, lon={longitude}")

                        return {
                            "latitude": latitude,
                            "longitude": longitude,
                            "display_name": first_result.get("display_name", location)
                        }
                    else:
                        logger.warning(f"Could not find coordinates for location: {location}")
                else:
                    logger.warning(f"Geocoding API returned status {response.status} for location: {location}")

    except Exception as e:
        logger.error(f"Error in geocoding lookup for {location}: {str(e)}")

    # Return sensible defaults if geocoding fails
    return None

# For testing purposes
if __name__ == "__main__":
    import asyncio

    async def test_geocoding():
        test_locations = ["New York", "London, UK", "Sydney, Australia", "Invalid Location XYZ"]

        for loc in test_locations:
            coords = await get_coordinates(loc)
            print(f"Location: {loc} -> Coordinates: {coords}")

    asyncio.run(test_geocoding())
