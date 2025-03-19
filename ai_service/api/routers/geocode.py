"""
Geocoding router for the Birth Time Rectifier API.
Handles all location-related endpoints for obtaining accurate coordinates and timezone data.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Request, BackgroundTasks
from pydantic import BaseModel, Field
import logging
import httpx
import os
from typing import Dict, List, Optional, Any, Union
import json
import uuid
import time
from datetime import datetime

from ai_service.api.websocket_events import emit_event, EventType

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["geocoding"],
    responses={404: {"description": "Not found"}},
)

# Define models
class GeocodeRequest(BaseModel):
    query: str

class GeocodeResponse(BaseModel):
    latitude: float
    longitude: float
    timezone: str

class AddressDetails(BaseModel):
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State or region")
    country: str = Field(..., description="Country name")
    postcode: Optional[str] = Field(None, description="Postal code")

class ReverseGeocodeResult(BaseModel):
    id: str = Field(..., description="Location ID")
    name: str = Field(..., description="Location name")
    country: str = Field(..., description="Country name")
    country_code: str = Field(..., description="Country code (ISO)")
    state: str = Field(..., description="State or region")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    timezone: str = Field(..., description="Timezone identifier")
    address: AddressDetails = Field(..., description="Detailed address components")

class ReverseGeocodeResponse(BaseModel):
    result: ReverseGeocodeResult

# Define API endpoints and settings
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
TIMEZONE_API_URL = "http://api.timezonedb.com/v2.1/get-time-zone"
TIMEZONE_API_KEY = os.environ.get("TIMEZONE_API_KEY", "")

# Log timezone API key status
if not TIMEZONE_API_KEY:
    logger.warning("TIMEZONE_API_KEY not set. Geocoding will not include timezone information.")
else:
    logger.info(f"Using TimeZoneDB API key (starts with: {TIMEZONE_API_KEY[:3] if len(TIMEZONE_API_KEY) > 3 else '*****'}...)")

# Cache for API results to minimize external calls
geocode_cache = {}
timezone_cache = {}
MAX_CACHE_SIZE = 200

# Cache management function
def manage_cache_size(cache_dict, max_size=MAX_CACHE_SIZE):
    """Remove oldest entries if cache exceeds maximum size"""
    if len(cache_dict) > max_size:
        # Remove oldest 20% of entries when limit is reached
        items_to_remove = int(max_size * 0.2)
        for _ in range(items_to_remove):
            if cache_dict:
                cache_dict.pop(next(iter(cache_dict)))

@router.post("", response_model=Dict[str, Any])
async def geocode_location(geocode_data: GeocodeRequest, request: Request, background_tasks: BackgroundTasks):
    """
    Geocode a location based on query string using Nominatim API.
    Returns location information including coordinates and timezone.
    """
    try:
        query = geocode_data.query
        logger.info(f"Geocoding location: {query}")

        # Perform geocoding using Nominatim
        results = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "q": query,
                "format": "json",
                "limit": 5,
                "addressdetails": 1
            }

            headers = {
                "User-Agent": "BirthTimeRectifier/1.0"
            }

            response = await client.get(NOMINATIM_URL, params=params, headers=headers)

            if response.status_code != 200:
                logger.error(f"Nominatim API error: status code {response.status_code}")
                raise HTTPException(status_code=response.status_code, detail=f"Geocoding service error: {response.status_code}")

            nominatim_results = response.json()

            if not nominatim_results:
                logger.warning(f"No results found for location: {query}")
                raise HTTPException(status_code=404, detail=f"Location not found: {query}")

            # Transform Nominatim results to our format
            for item in nominatim_results:
                # Extract coordinates
                latitude = float(item["lat"])
                longitude = float(item["lon"])

                # Get timezone for coordinates (if API key is available)
                timezone = "UTC"  # Default timezone
                if TIMEZONE_API_KEY:
                    try:
                        timezone = await get_timezone(latitude, longitude)
                    except Exception as tz_error:
                        logger.error(f"Error getting timezone: {tz_error}")
                        # We don't throw an exception here as timezone is secondary data

                # Extract location details from address
                address = item.get("address", {})

                # Format location result
                location = {
                    "id": f"loc_{uuid.uuid4().hex[:8]}",
                    "name": item.get("display_name", "").split(",")[0],
                    "country": address.get("country", "Unknown"),
                    "country_code": address.get("country_code", "").upper(),
                    "state": address.get("state", address.get("region", "")),
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": timezone,
                    "address": {
                        "city": address.get("city", address.get("town", address.get("village", "Unknown"))),
                        "state": address.get("state", address.get("region", "")),
                        "country": address.get("country", "Unknown"),
                        "postcode": address.get("postcode", "")
                    }
                }

                results.append(location)

        response_data = {
            "results": results
        }

        # Emit geocode completed event if we have a session ID
        if hasattr(request.state, "session_id"):
            session_id = request.state.session_id
            # Send WebSocket event in the background
            background_tasks.add_task(
                emit_event,
                session_id,
                EventType.GEOCODE_COMPLETED,
                {
                    "query": query,
                    "results_count": len(results),
                    "results": results[:1]  # Send only the first result to keep the event payload small
                }
            )

        return response_data

    except httpx.TimeoutException as timeout_err:
        logger.error(f"Geocoding request timed out: {timeout_err}")
        raise HTTPException(status_code=504, detail="Geocoding service timeout")
    except Exception as e:
        logger.error(f"Error in geocoding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=GeocodeResponse)  # Root endpoint for direct access via /geocode?query=...
@router.get("/", response_model=GeocodeResponse)  # Root endpoint with trailing slash
@router.get("/geocode", response_model=GeocodeResponse)
@router.get("/geocoding/geocode", response_model=GeocodeResponse)  # Additional path for legacy compatibility
async def geocode_get(query: str = Query(..., description="Location to geocode")):
    """
    Geocode a location string to coordinates and timezone.
    Uses Nominatim for geocoding and TimeZoneDB for timezone lookup.
    """
    # Normalize query for cache lookup
    normalized_query = query.lower().strip()

    # Check cache first
    if normalized_query in geocode_cache:
        logger.info(f"Geocode cache hit for: {normalized_query}")
        return geocode_cache[normalized_query]

    try:
        # Geocode the location using Nominatim
        async with httpx.AsyncClient(timeout=5.0) as client:
            nominatim_params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1
            }

            logger.info(f"Querying Nominatim for location: {query}")
            response = await client.get(NOMINATIM_URL, params=nominatim_params, headers={
                "User-Agent": "BirthTimeRectifier/1.0"
            })

            if response.status_code != 200:
                logger.error(f"Nominatim API returned status code {response.status_code}")
                raise HTTPException(status_code=response.status_code, detail=f"Geocoding service error: {response.status_code}")

            geocode_results = response.json()

            if not geocode_results:
                logger.warning(f"No results found for location: {query}")
                raise HTTPException(status_code=404, detail=f"Location not found: {query}")

            result = geocode_results[0]
            latitude = float(result["lat"])
            longitude = float(result["lon"])

            # Get timezone for the coordinates
            timezone = "UTC"  # Default timezone
            if TIMEZONE_API_KEY:
                timezone = await get_timezone(latitude, longitude)

            # Prepare response
            geocode_response = GeocodeResponse(
                latitude=latitude,
                longitude=longitude,
                timezone=timezone
            )

            # Cache the result
            geocode_cache[normalized_query] = geocode_response
            manage_cache_size(geocode_cache)

            return geocode_response

    except httpx.TimeoutException:
        logger.error(f"Timeout while geocoding location: {query}")
        raise HTTPException(status_code=504, detail="Geocoding request timed out")
    except Exception as e:
        logger.error(f"Error geocoding location '{query}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)}")

@router.get("/reverse", response_model=ReverseGeocodeResponse)
async def reverse_geocode(
    lat: float = Query(..., description="Latitude coordinate", gt=-90, lt=90),
    lon: float = Query(..., description="Longitude coordinate", gt=-180, lt=180)
):
    """
    Convert geographic coordinates (latitude/longitude) to a human-readable address.
    Uses Nominatim for reverse geocoding and TimeZoneDB for timezone lookup.
    """
    logger.info(f"Reverse geocoding coordinates: {lat}, {lon}")

    try:
        # Use Nominatim for reverse geocoding
        async with httpx.AsyncClient(timeout=5.0) as client:
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json",
                "addressdetails": 1,
                "zoom": 18  # Higher zoom level for more detailed results
            }

            headers = {
                "User-Agent": "BirthTimeRectifier/1.0"
            }

            response = await client.get(NOMINATIM_REVERSE_URL, params=params, headers=headers)

            if response.status_code != 200:
                logger.error(f"Nominatim API error: status code {response.status_code}")
                raise HTTPException(status_code=response.status_code, detail=f"Reverse geocoding service error: {response.status_code}")

            result = response.json()

            if not result or "error" in result:
                logger.warning(f"No results found for coordinates: {lat}, {lon}")
                raise HTTPException(status_code=404, detail=f"Location not found for coordinates: {lat}, {lon}")

            # Get timezone information
            timezone = "UTC"  # Default timezone
            if TIMEZONE_API_KEY:
                timezone = await get_timezone(lat, lon)

            # Extract address details
            address = result.get("address", {})

            # Create structured response
            location_result = ReverseGeocodeResult(
                id=f"loc_{uuid.uuid4().hex[:8]}",
                name=result.get("display_name", "").split(",")[0],
                country=address.get("country", "Unknown"),
                country_code=address.get("country_code", "").upper(),
                state=address.get("state", address.get("region", "")),
                latitude=lat,
                longitude=lon,
                timezone=timezone,
                address=AddressDetails(
                    city=address.get("city", address.get("town", address.get("village", "Unknown"))),
                    state=address.get("state", address.get("region", "")),
                    country=address.get("country", "Unknown"),
                    postcode=address.get("postcode", "")
                )
            )

            return ReverseGeocodeResponse(result=location_result)

    except httpx.TimeoutException:
        logger.error(f"Timeout while reverse geocoding coordinates: {lat}, {lon}")
        raise HTTPException(status_code=504, detail="Reverse geocoding request timed out")
    except Exception as e:
        logger.error(f"Error in reverse geocoding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_timezone(latitude: float, longitude: float) -> str:
    """
    Get timezone for coordinates using TimeZoneDB API.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        Timezone string (e.g., "America/New_York")

    Raises:
        Exception: If timezone lookup fails
    """
    # Round coordinates to reduce cache fragmentation while maintaining accuracy
    cache_key = f"{round(latitude, 2)},{round(longitude, 2)}"

    # Check cache first
    if cache_key in timezone_cache:
        return timezone_cache[cache_key]

    # Verify API key is available
    if not TIMEZONE_API_KEY:
        logger.warning("No TimeZoneDB API key available. Using UTC.")
        return "UTC"

    # Query TimeZoneDB API
    async with httpx.AsyncClient(timeout=5.0) as client:
        timezone_params = {
            "key": TIMEZONE_API_KEY,
            "format": "json",
            "by": "position",
            "lat": latitude,
            "lng": longitude
        }

        try:
            logger.info(f"Querying TimeZoneDB for coordinates: {latitude}, {longitude}")
            response = await client.get(TIMEZONE_API_URL, params=timezone_params)

            # Handle HTTP errors
            if response.status_code != 200:
                logger.error(f"TimeZoneDB API error: {response.status_code}")
                raise Exception(f"TimeZoneDB API error: {response.status_code}")

            # Parse response
            timezone_result = response.json()

            # Check API response status
            if timezone_result.get("status") != "OK":
                error_msg = timezone_result.get("message", "Unknown error")
                logger.error(f"TimeZoneDB API error: {error_msg}")
                raise Exception(f"TimeZoneDB API error: {error_msg}")

            # Extract timezone name
            if "zoneName" not in timezone_result:
                logger.error("TimeZoneDB API response missing zoneName")
                raise Exception("Invalid response from TimeZoneDB API")

            # Get timezone and cache it
            timezone = timezone_result["zoneName"]
            timezone_cache[cache_key] = timezone

            # Manage cache size
            manage_cache_size(timezone_cache)

            logger.info(f"Retrieved timezone: {timezone} for coordinates: {latitude}, {longitude}")
            return timezone

        except httpx.TimeoutException:
            logger.error("TimeZoneDB API request timed out")
            raise Exception("Timezone service timeout")
        except Exception as e:
            logger.error(f"Error getting timezone: {e}")
            raise
