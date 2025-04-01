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
                    # Get timezone info for the coordinates
                    timezone_info = await get_timezone_for_coordinates(
                        result["latitude"],
                        result["longitude"]
                    )

                    # Map the timezone information to the expected fields
                    # The timezone_info contains different keys than what we're mapping to
                    result["timezone"] = timezone_info.get("timezone_id")  # Changed from "timezone" to "timezone_id"

                    # Get total offset, which is the sum of raw offset and DST offset
                    total_offset = timezone_info.get("total_offset")
                    if total_offset is not None:
                        # Convert seconds to hours for better readability
                        result["timezone_offset"] = total_offset / 3600  # Convert seconds to hours

                    # Calculate abbreviation from timezone_id if not present
                    # We don't have direct access to the abbreviation, so derive it from the timezone_id
                    timezone_name = timezone_info.get("timezone_name", "")
                    if timezone_name:
                        # Extract a simple abbreviation (e.g., EST, CST) from the timezone name
                        # This is a best-effort approach
                        parts = timezone_name.split()
                        if parts:
                            result["timezone_abbreviation"] = ''.join([p[0] for p in parts if p])
                    else:
                        # Default to empty if we can't determine an abbreviation
                        result["timezone_abbreviation"] = None

                    # Add additional timezone information that might be useful
                    result["timezone_name"] = timezone_info.get("timezone_name")
                    result["is_dst"] = timezone_info.get("dst_offset", 0) > 0

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
        timezone_data = None
        if include_timezone:
            timezone_info = await get_timezone_for_coordinates(latitude, longitude)

            # Process timezone information in the same format as the timezone endpoint
            # Calculate an abbreviation from the timezone_id
            abbreviation = None
            timezone_name = timezone_info.get("timezone_name", "")
            if timezone_name:
                parts = timezone_name.split()
                if parts:
                    abbreviation = ''.join([p[0] for p in parts if p])

            # Safely get offset values and convert to hours
            total_offset = timezone_info.get("total_offset")
            total_offset_hours = total_offset / 3600 if total_offset is not None else 0

            raw_offset = timezone_info.get("raw_offset")
            raw_offset_hours = raw_offset / 3600 if raw_offset is not None else 0

            dst_offset = timezone_info.get("dst_offset")
            dst_offset_hours = dst_offset / 3600 if dst_offset is not None else 0

            # Format the timezone data consistently
            timezone_data = {
                "timezone": timezone_info.get("timezone_id"),
                "timezone_name": timezone_info.get("timezone_name"),
                "offset": total_offset_hours,
                "raw_offset": raw_offset_hours,
                "dst_offset": dst_offset_hours,
                "is_dst": timezone_info.get("dst_offset", 0) > 0,
                "abbreviation": abbreviation
            }

        return {
            "success": True,
            "latitude": latitude,
            "longitude": longitude,
            "count": len(results),
            "results": results,
            "timezone": timezone_data
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

        # Calculate an abbreviation from the timezone_id
        abbreviation = None
        timezone_name = timezone_info.get("timezone_name", "")
        if timezone_name:
            parts = timezone_name.split()
            if parts:
                abbreviation = ''.join([p[0] for p in parts if p])

        # Safely get offset values and convert to hours
        total_offset = timezone_info.get("total_offset")
        total_offset_hours = total_offset / 3600 if total_offset is not None else 0

        raw_offset = timezone_info.get("raw_offset")
        raw_offset_hours = raw_offset / 3600 if raw_offset is not None else 0

        dst_offset = timezone_info.get("dst_offset")
        dst_offset_hours = dst_offset / 3600 if dst_offset is not None else 0

        # Map the timezone information to the expected fields
        return {
            "success": True,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone_info.get("timezone_id"),  # Use timezone_id instead of timezone
            "timezone_name": timezone_info.get("timezone_name"),
            "offset": total_offset_hours,
            "raw_offset": raw_offset_hours,
            "dst_offset": dst_offset_hours,
            "is_dst": timezone_info.get("dst_offset", 0) > 0,
            "abbreviation": abbreviation
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
