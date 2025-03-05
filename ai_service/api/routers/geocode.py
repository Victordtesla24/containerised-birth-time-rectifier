"""
Geocoding router for the Birth Time Rectifier API.
Handles all location-related endpoints.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging
import httpx
import os
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["geocoding"],
    responses={404: {"description": "Not found"}},
)

# Define models
class GeocodeRequest(BaseModel):
    place: str

class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str

# Define API keys and endpoints
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
TIMEZONE_API_URL = "http://api.timezonedb.com/v2.1/get-time-zone"
TIMEZONE_API_KEY = os.getenv("TIMEZONE_API_KEY", "")

@router.get("/geocode", response_model=GeocodeResponse)
@router.get("/geocoding/geocode", response_model=GeocodeResponse)  # Additional path for test compatibility
async def geocode(query: str = Query("New York", description="Location to geocode")):
    """
    Geocode a location string to coordinates and timezone.

    Uses Nominatim for geocoding and TimeZoneDB for timezone lookup.
    """
    try:
        # Geocode the location using Nominatim
        async with httpx.AsyncClient() as client:
            nominatim_params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1
            }

            response = await client.get(NOMINATIM_URL, params=nominatim_params, headers={
                "User-Agent": "BirthTimeRectifier/1.0"
            })

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Error during geocoding")

            geocode_results = response.json()

            if not geocode_results:
                raise HTTPException(status_code=404, detail=f"Location not found: {query}")

            result = geocode_results[0]
            latitude = float(result["lat"])
            longitude = float(result["lon"])

            # Get timezone for the coordinates
            timezone = await get_timezone(latitude, longitude)

            return GeocodeResponse(
                latitude=latitude,
                longitude=longitude,
                timezone=timezone
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during geocoding: {e}")
        raise HTTPException(status_code=500, detail=f"Error during geocoding: {str(e)}")

async def get_timezone(latitude: float, longitude: float) -> str:
    """
    Get timezone for coordinates using TimeZoneDB API.

    Falls back to UTC if the API is not available.
    """
    try:
        if not TIMEZONE_API_KEY:
            logger.warning("TIMEZONE_API_KEY not set. Using UTC as fallback.")
            return "UTC"

        async with httpx.AsyncClient() as client:
            timezone_params = {
                "key": TIMEZONE_API_KEY,
                "format": "json",
                "by": "position",
                "lat": latitude,
                "lng": longitude
            }

            response = await client.get(TIMEZONE_API_URL, params=timezone_params)

            if response.status_code != 200:
                logger.warning(f"TimeZoneDB API error: {response.status_code}. Using UTC as fallback.")
                return "UTC"

            timezone_result = response.json()

            if timezone_result["status"] != "OK":
                logger.warning(f"TimeZoneDB API error: {timezone_result['message']}. Using UTC as fallback.")
                return "UTC"

            return timezone_result["zoneName"]

    except Exception as e:
        logger.error(f"Error getting timezone: {e}")
        return "UTC"  # Fallback to UTC
