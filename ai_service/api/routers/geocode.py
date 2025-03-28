"""
Geocoding Router for Birth Time Rectifier

This module provides geocoding endpoints that rely on the canonical implementation
in ai_service.utils.geocoding.
"""

import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Query, HTTPException, status, Depends
from fastapi.responses import JSONResponse

# Import the canonical geocoding implementation
from ai_service.utils.geocoding import (
    geocode_location,
    reverse_geocode,
    get_timezone_for_coordinates
)

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("", summary="Geocode a location to coordinates and timezone")
async def geocode_endpoint(
    query: str = Query(..., description="Location to geocode"),
    limit: int = Query(5, description="Maximum number of results to return"),
    include_timezone: bool = Query(True, description="Include timezone information")
) -> Dict[str, Any]:
    """
    Geocode a location string to coordinates and timezone information.

    Args:
        query: Location to geocode (city, address, etc.)
        limit: Maximum number of results to return
        include_timezone: Whether to include timezone information

    Returns:
        Geocoding results including coordinates and timezone
    """
    try:
        # Use the canonical implementation
        results = await geocode_location(query, False, limit)

        if not results:
            return {
                "success": False,
                "error": "Location not found",
                "results": []
            }

        # If requested, add timezone information to results
        if include_timezone:
            for result in results:
                if "latitude" in result and "longitude" in result:
                    timezone_info = await get_timezone_for_coordinates(
                        result["latitude"],
                        result["longitude"]
                    )
                    result["timezone"] = timezone_info.get("timezone")
                    result["timezone_offset"] = timezone_info.get("offset")
                    result["timezone_abbreviation"] = timezone_info.get("abbreviation")

        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }

    except Exception as e:
        logger.error(f"Error geocoding location '{query}': {str(e)}")
        return {
            "success": False,
            "error": f"Geocoding error: {str(e)}",
            "results": []
        }

@router.get("/reverse", summary="Reverse geocode coordinates to address")
async def reverse_geocode_endpoint(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    include_timezone: bool = Query(True, description="Include timezone information")
) -> Dict[str, Any]:
    """
    Reverse geocode coordinates to address and location information.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        include_timezone: Whether to include timezone information

    Returns:
        Reverse geocoding results including address components
    """
    try:
        # Validate coordinates
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180."
            )

        # Use the canonical implementation
        results = await reverse_geocode(latitude, longitude)

        # If requested, add timezone information
        timezone_info = None
        if include_timezone:
            timezone_info = await get_timezone_for_coordinates(latitude, longitude)

        return {
            "success": True,
                            "latitude": latitude,
                            "longitude": longitude,
            "count": len(results),
            "results": results,
            "timezone": timezone_info if include_timezone else None
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error reverse geocoding coordinates ({latitude}, {longitude}): {str(e)}")
        return {
            "success": False,
            "error": f"Reverse geocoding error: {str(e)}",
            "results": []
        }

@router.get("/timezone", summary="Get timezone information for coordinates")
async def timezone_endpoint(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate")
) -> Dict[str, Any]:
    """
    Get timezone information for coordinates.

    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        Timezone information including name, offset, and abbreviation
    """
    try:
        # Validate coordinates
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid coordinates. Latitude must be between -90 and 90, longitude between -180 and 180."
            )

        # Use the canonical implementation
        timezone_info = await get_timezone_for_coordinates(latitude, longitude)

        return {
            "success": True,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone_info.get("timezone"),
            "offset": timezone_info.get("offset"),
            "dst": timezone_info.get("dst", False),
            "abbreviation": timezone_info.get("abbreviation")
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting timezone for coordinates ({latitude}, {longitude}): {str(e)}")
        return {
            "success": False,
            "error": f"Timezone error: {str(e)}",
            "timezone": None
        }
