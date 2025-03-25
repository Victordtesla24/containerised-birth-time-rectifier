"""
Geocoding Service
----------------

Production-ready geocoding service implementation using Google Maps API and OpenStreetMap.
Provides accurate coordinates and timezone data for global locations.
"""

import asyncio
import logging
import time
import json
import os
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union
from functools import lru_cache
import hashlib
from datetime import datetime

# Geocoding libraries
import httpx
from timezonefinder import TimezoneFinder
import pytz

# Setup logging
logger = logging.getLogger(__name__)

# API keys and configuration
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
GOOGLE_MAPS_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
GOOGLE_MAPS_TIMEZONE_URL = "https://maps.googleapis.com/maps/api/timezone/json"

# OpenStreetMap service configuration
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"

# Cache configuration
CACHE_TTL = 86400  # 24 hours in seconds
_geocode_cache: Dict[str, Dict[str, Any]] = {}
_timezone_cache: Dict[str, Dict[str, Any]] = {}

# HTTP client for geocoding services
_http_client = None

# Initialize timezone finder for local computation when network services aren't available
timezone_finder = TimezoneFinder()

def manage_cache_size(cache: Dict, max_size: int = 1000) -> None:
    """
    Remove oldest entries when cache exceeds maximum size.

    Args:
        cache: Cache dictionary to manage
        max_size: Maximum number of entries
    """
    if len(cache) > max_size:
        # Sort by timestamp (oldest first) and remove oldest entries
        sorted_keys = sorted(cache.keys(), key=lambda k: cache[k].get("timestamp", 0))
        for key in sorted_keys[:len(cache) - max_size]:
            cache.pop(key, None)

async def get_http_client() -> httpx.AsyncClient:
    """
    Get or create a shared HTTP client with appropriate timeouts.

    Returns:
        AsyncClient instance
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            http2=True
        )
        logger.info("Created shared HTTP client for geocoding services")
    return _http_client

async def get_shared_session() -> httpx.AsyncClient:
    """
    Get a shared HTTP client session for geocoding services.

    Returns:
        Shared HTTP client
    """
    return await get_http_client()

# Location result structure
class Location:
    """Structure to hold geocoding results"""
    def __init__(
        self,
        address: str,
        latitude: float,
        longitude: float,
        country: str = "",
        state: str = "",
        city: str = "",
        postal_code: str = "",
        formatted_address: str = "",
        provider: str = ""
    ):
        self.address = address
        self.latitude = latitude
        self.longitude = longitude
        self.country = country
        self.state = state
        self.city = city
        self.postal_code = postal_code
        self.formatted_address = formatted_address or address
        self.provider = provider

    def to_dict(self) -> Dict[str, Any]:
        """Convert location to dictionary"""
        return {
            "address": self.address,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "country": self.country,
            "state": self.state,
            "city": self.city,
            "postal_code": self.postal_code,
            "formatted_address": self.formatted_address,
            "provider": self.provider
        }

async def geocode_location(query: str, exactly_one: bool = False, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Geocode a location query to coordinates and address components.

    Args:
        query: Location string to geocode
        exactly_one: Whether to return only the top result
        limit: Maximum number of results to return

    Returns:
        List of location dictionaries with coordinates and address components
    """
    if not query:
        logger.warning("Empty geocoding query")
        return []

    cache_key = generate_cache_key(query)
    cache_entry = _geocode_cache.get(cache_key)

    # Return from cache if valid
    if cache_entry and (time.time() - cache_entry.get("timestamp", 0) < CACHE_TTL):
        logger.info(f"Geocode cache hit for '{query}'")
        return cache_entry.get("results", [])

    logger.info(f"Geocoding location: '{query}'")
    results = []

    # Try Google Maps API first if key is available
    if GOOGLE_MAPS_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    GOOGLE_MAPS_GEOCODING_URL,
                    params={
                        "address": query,
                        "key": GOOGLE_MAPS_API_KEY,
                        "sensor": "false"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        for result in data.get("results", [])[:limit]:
                            location = _parse_google_result(result, query)
                            if location:
                                results.append(location.to_dict())

                        # Store in cache
                        _geocode_cache[cache_key] = {
                            "results": results,
                            "timestamp": time.time()
                        }

                        if exactly_one and results:
                            return [results[0]]
                        return results
                    else:
                        logger.warning(f"Google geocoding error: {data.get('status')}")
                else:
                    logger.warning(f"Google geocoding HTTP error: {response.status_code}")
        except Exception as e:
            logger.error(f"Google geocoding failed: {e}")

    # Use OpenStreetMap Nominatim if Google Maps API is not available or fails
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={
                    "q": query,
                    "format": "json",
                    "addressdetails": 1,
                    "limit": limit
                },
                headers={"User-Agent": "Birth-Time-Rectifier/1.0"}
            )

            if response.status_code == 200:
                data = response.json()
                for result in data[:limit]:
                    location = _parse_nominatim_result(result, query)
                    if location:
                        results.append(location.to_dict())

                # Store in cache
                _geocode_cache[cache_key] = {
                    "results": results,
                    "timestamp": time.time()
                }

                if exactly_one and results:
                    return [results[0]]
                return results
            else:
                logger.warning(f"Nominatim geocoding HTTP error: {response.status_code}")
    except Exception as e:
        logger.error(f"Nominatim geocoding failed: {e}")

    return results

def geocode_location_sync(query: str, exactly_one: bool = False, limit: int = 5) -> List[Dict[str, Any]]:
    """Synchronous function to geocode a location"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new event loop if the current one is running
            new_loop = asyncio.new_event_loop()
            results = new_loop.run_until_complete(geocode_location(query, exactly_one, limit))
            new_loop.close()
            return results
        else:
            return loop.run_until_complete(geocode_location(query, exactly_one, limit))
    except Exception as e:
        logger.error(f"Error in synchronous geocoding: {e}")
        return []

async def get_coordinates(location_query: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Get coordinates for a location query.

    Args:
        location_query: Location string to geocode

    Returns:
        Tuple of (latitude, longitude) or (None, None) if geocoding fails
    """
    if not location_query:
        logger.warning("Empty location query provided to get_coordinates")
        return None, None

    results = await geocode_location(location_query, exactly_one=True)

    if results and len(results) > 0:
        location = results[0]
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        # Validate that we actually have numeric coordinates
        if latitude is not None and longitude is not None:
            try:
                latitude = float(latitude)
                longitude = float(longitude)
                if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                    return latitude, longitude
                else:
                    logger.warning(f"Invalid coordinates for {location_query}: {latitude}, {longitude}")
            except (ValueError, TypeError):
                logger.warning(f"Non-numeric coordinates for {location_query}: {latitude}, {longitude}")

    logger.warning(f"Failed to get coordinates for location query: {location_query}")
    return None, None

async def get_coordinates_sync(location_query: str) -> Tuple[Optional[float], Optional[float]]:
    """Synchronous function to get coordinates for a location"""
    try:
        if not location_query:
            logger.warning("Empty location query provided to get_coordinates_sync")
            return None, None

        results = geocode_location_sync(location_query, exactly_one=True)

        if results and len(results) > 0:
            location = results[0]
            latitude = location.get("latitude")
            longitude = location.get("longitude")

            # Validate that we actually have numeric coordinates
            if latitude is not None and longitude is not None:
                try:
                    latitude = float(latitude)
                    longitude = float(longitude)
                    if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                        return latitude, longitude
                    else:
                        logger.warning(f"Invalid coordinates for {location_query}: {latitude}, {longitude}")
                except (ValueError, TypeError):
                    logger.warning(f"Non-numeric coordinates for {location_query}: {latitude}, {longitude}")
    except Exception as e:
        logger.error(f"Error getting coordinates synchronously: {e}")

    logger.warning(f"Failed to get coordinates for location query: {location_query}")
    return None, None

async def reverse_geocode(latitude: float, longitude: float) -> List[Dict[str, Any]]:
    """
    Reverse geocode coordinates to address.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        List of location dictionaries with address components
    """
    cache_key = generate_cache_key(f"{latitude},{longitude}")
    cache_entry = _geocode_cache.get(cache_key)

    # Return from cache if valid
    if cache_entry and (time.time() - cache_entry.get("timestamp", 0) < CACHE_TTL):
        return cache_entry.get("results", [])

    results = []

    # Try Google Maps API first if key is available
    if GOOGLE_MAPS_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    GOOGLE_MAPS_GEOCODING_URL,
                    params={
                        "latlng": f"{latitude},{longitude}",
                        "key": GOOGLE_MAPS_API_KEY,
                        "sensor": "false"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        for result in data.get("results", [])[:5]:
                            location = _parse_google_result(result, f"{latitude},{longitude}")
                            if location:
                                results.append(location.to_dict())

                        # Store in cache
                        _geocode_cache[cache_key] = {
                            "results": results,
                            "timestamp": time.time()
                        }
                        return results
                    else:
                        logger.warning(f"Google reverse geocoding error: {data.get('status')}")
                else:
                    logger.warning(f"Google reverse geocoding HTTP error: {response.status_code}")
        except Exception as e:
            logger.error(f"Google reverse geocoding failed: {e}")

    # Use OpenStreetMap Nominatim if Google Maps API is not available or fails
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                NOMINATIM_REVERSE_URL,
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "json",
                    "addressdetails": 1
                },
                headers={"User-Agent": "Birth-Time-Rectifier/1.0"}
            )

            if response.status_code == 200:
                data = response.json()
                location = _parse_nominatim_result(data, f"{latitude},{longitude}")
                if location:
                    results.append(location.to_dict())

                # Store in cache
                _geocode_cache[cache_key] = {
                    "results": results,
                    "timestamp": time.time()
                }
                return results
            else:
                logger.warning(f"Nominatim reverse geocoding HTTP error: {response.status_code}")
    except Exception as e:
        logger.error(f"Nominatim reverse geocoding failed: {e}")

    return results

def reverse_geocode_sync(latitude: float, longitude: float) -> List[Dict[str, Any]]:
    """Synchronous function to reverse geocode coordinates"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new event loop if the current one is running
            new_loop = asyncio.new_event_loop()
            results = new_loop.run_until_complete(reverse_geocode(latitude, longitude))
            new_loop.close()
            return results
        else:
            return loop.run_until_complete(reverse_geocode(latitude, longitude))
    except Exception as e:
        logger.error(f"Error in synchronous reverse geocoding: {e}")
        return []

async def get_timezone_for_coordinates(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get timezone information for coordinates.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        Dictionary with timezone information
    """
    cache_key = generate_cache_key(f"tz_{latitude},{longitude}")
    cache_entry = _timezone_cache.get(cache_key)

    # Return from cache if valid
    if cache_entry and (time.time() - cache_entry.get("timestamp", 0) < CACHE_TTL):
        return cache_entry.get("results", {})

    # Try Google Maps Timezone API if available
    if GOOGLE_MAPS_API_KEY:
        try:
            timestamp = int(time.time())
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    GOOGLE_MAPS_TIMEZONE_URL,
                    params={
                        "location": f"{latitude},{longitude}",
                        "timestamp": timestamp,
                        "key": GOOGLE_MAPS_API_KEY
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        result = {
                            "timezone_id": data.get("timeZoneId"),
                            "timezone_name": data.get("timeZoneName"),
                            "dst_offset": data.get("dstOffset"),
                            "raw_offset": data.get("rawOffset"),
                            "total_offset": data.get("dstOffset", 0) + data.get("rawOffset", 0),
                            "source": "google"
                        }

                        # Store in cache
                        _timezone_cache[cache_key] = {
                            "results": result,
                            "timestamp": time.time()
                        }
                        return result
                    else:
                        logger.warning(f"Google timezone error: {data.get('status')}")
                else:
                    logger.warning(f"Google timezone HTTP error: {response.status_code}")
        except Exception as e:
            logger.error(f"Google timezone API failed: {e}")

    # Use TimeZoneFinder for local computation when Google Maps API is not available
    try:
        timezone_str = timezone_finder.timezone_at(lat=latitude, lng=longitude)

        if timezone_str:
            timezone = pytz.timezone(timezone_str)
            now = datetime.fromtimestamp(time.time())
            offset = timezone.utcoffset(now)
            if offset is not None:
                offset_seconds = offset.total_seconds()

                # Try to get DST information
                dst = timezone.localize(now).dst()
                is_dst = dst is not None and dst.total_seconds() > 0

                result = {
                    "timezone_id": timezone_str,
                    "timezone_name": timezone_str.replace('_', ' '),
                    "dst_offset": 3600 if is_dst else 0,  # 1 hour if DST is active
                    "raw_offset": offset_seconds - (3600 if is_dst else 0),
                    "total_offset": offset_seconds,
                    "source": "timezonefinder"
                }

                # Store in cache
                _timezone_cache[cache_key] = {
                    "results": result,
                    "timestamp": time.time()
                }
                return result
    except Exception as e:
        logger.error(f"TimeZoneFinder error: {e}")

    # When no timezone data is available, use UTC as standard reference
    result = {
        "timezone_id": "UTC",
        "timezone_name": "Coordinated Universal Time",
        "dst_offset": 0,
        "raw_offset": 0,
        "total_offset": 0,
        "source": "utc_standard"
    }

    # Store in cache
    _timezone_cache[cache_key] = {
        "results": result,
        "timestamp": time.time()
    }

    return result

def get_timezone_for_coordinates_sync(latitude: float, longitude: float) -> Dict[str, Any]:
    """Synchronous function to get timezone for coordinates"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create a new event loop if the current one is running
            new_loop = asyncio.new_event_loop()
            result = new_loop.run_until_complete(get_timezone_for_coordinates(latitude, longitude))
            new_loop.close()
            return result
        else:
            return loop.run_until_complete(get_timezone_for_coordinates(latitude, longitude))
    except Exception as e:
        logger.error(f"Error getting timezone synchronously: {e}")

        # When timezone service fails, use UTC as standard reference
        return {
            "timezone_id": "UTC",
            "timezone_name": "Coordinated Universal Time",
            "dst_offset": 0,
            "raw_offset": 0,
            "total_offset": 0,
            "source": "utc_standard"
        }

def generate_cache_key(data: str) -> str:
    """
    Generate a cache key for storing and retrieving geocoding results.

    Args:
        data: String data to hash

    Returns:
        Cache key (MD5 hash)
    """
    data = data.strip().lower()
    return hashlib.md5(data.encode('utf-8')).hexdigest()

def _parse_google_result(result: Dict[str, Any], query: str) -> Optional[Location]:
    """Parse Google Maps geocoding result into a standardized location"""
    try:
        if not result or not isinstance(result, dict):
            return None

        geometry = result.get("geometry")
        if not geometry or not isinstance(geometry, dict):
            return None

        location_data = geometry.get("location")
        if not location_data or not isinstance(location_data, dict):
            return None

        latitude = location_data.get("lat")
        longitude = location_data.get("lng")

        if latitude is None or longitude is None:
            return None

        # Parse address components
        address_components = result.get("address_components", [])
        country = ""
        state = ""
        city = ""
        postal_code = ""

        for component in address_components:
            types = component.get("types", [])
            if "country" in types:
                country = component.get("long_name", "")
            elif "administrative_area_level_1" in types:
                state = component.get("long_name", "")
            elif "locality" in types or "administrative_area_level_2" in types:
                city = component.get("long_name", "")
            elif "postal_code" in types:
                postal_code = component.get("long_name", "")

        return Location(
            address=query,
            latitude=latitude,
            longitude=longitude,
            country=country,
            state=state,
            city=city,
            postal_code=postal_code,
            formatted_address=result.get("formatted_address", ""),
            provider="google"
        )
    except Exception as e:
        logger.error(f"Error parsing Google result: {e}")
        return None

def _parse_nominatim_result(result: Dict[str, Any], query: str) -> Optional[Location]:
    """Parse Nominatim geocoding result into a standardized location"""
    try:
        if not result or not isinstance(result, dict):
            return None

        lat = result.get("lat")
        lon = result.get("lon")

        if not lat or not lon:
            return None

        # Convert string coordinates to float
        try:
            latitude = float(lat)
            longitude = float(lon)
        except (ValueError, TypeError):
            return None

        # Parse address components
        address = result.get("address", {})
        country = address.get("country", "")
        state = address.get("state", "")
        city = address.get("city", "") or address.get("town", "") or address.get("village", "")
        postal_code = address.get("postcode", "")

        display_name = result.get("display_name", "")

        return Location(
            address=query,
            latitude=latitude,
            longitude=longitude,
            country=country,
            state=state,
            city=city,
            postal_code=postal_code,
            formatted_address=display_name,
            provider="nominatim"
        )
    except Exception as e:
        logger.error(f"Error parsing Nominatim result: {e}")
        return None

async def close_shared_session() -> None:
    """
    Close the shared HTTP client session.

    This should be called during application shutdown.
    """
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        logger.info("Closed shared HTTP client for geocoding services")
        _http_client = None
