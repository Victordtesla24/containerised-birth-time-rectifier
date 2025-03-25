"""
Geocoding Router for Birth Time Rectifier API
---------------------------------------------

Handles all location-related endpoints for obtaining accurate coordinates and timezone data.
Provides direct integration with various geocoding providers.
"""

from fastapi import APIRouter, HTTPException, Query, Request, BackgroundTasks, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import logging
import json
import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from urllib.parse import quote

from ai_service.utils.geocoding import (
    geocode_location,
    geocode_location_sync,
    reverse_geocode,
    reverse_geocode_sync,
    get_coordinates,
    get_timezone_for_coordinates
)
from ai_service.api.websocket_events import emit_event as emit, EventType

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/geocode",
    tags=["geocode"],
    responses={404: {"description": "Not found"}},
)

# Request/Response models
class GeocodeRequest(BaseModel):
    """Geocode request model"""
    query: str = Field(..., description="Location query to geocode")
    exactly_one: bool = Field(False, description="Return only the first result")
    limit: int = Field(5, description="Maximum number of results to return")

class ReverseGeocodeRequest(BaseModel):
    """Reverse geocode request model"""
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")

class TimezoneRequest(BaseModel):
    """Timezone request model"""
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")

class GeocodeResponse(BaseModel):
    """Geocode response model"""
    results: List[Dict[str, Any]] = []
    query: str
    count: int
    status: str = "success"
    error: Optional[str] = None

class GeocodingError(Exception):
    """Custom exception for geocoding errors"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

@router.post("", response_model=GeocodeResponse)
async def geocode_address(
    request: GeocodeRequest,
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = None,
    emit_event: Optional[bool] = False
) -> GeocodeResponse:
    """
    Geocode a location string to get coordinates and address details.

    Args:
        request: Geocode request containing location query
        background_tasks: FastAPI background tasks
        session_id: Optional session ID for WebSocket events
        emit_event: Whether to emit WebSocket events

    Returns:
        Geocoding results with coordinates and address details
    """
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Empty location query")

    try:
        # Emit start event if requested
        if emit_event and session_id:
            background_tasks.add_task(
                emit,
                session_id,
                EventType.GEOCODE_STARTED,
                {"query": query}
            )

        # Geocode the location
        results = await geocode_location(
            query=query,
            exactly_one=request.exactly_one,
            limit=request.limit
        )

        # Prepare response
        response = GeocodeResponse(
            results=results,
            query=query,
            count=len(results),
            status="success"
        )

        # Emit completion event if requested
        if emit_event and session_id:
            background_tasks.add_task(
                emit,
                session_id,
                EventType.GEOCODE_COMPLETED,
                {
                    "query": query,
                    "count": len(results),
                    "results": results[:5]  # Limit event payload size
                }
            )

        return response

    except Exception as e:
        logger.error(f"Geocoding error: {e}")

        # Emit error event if requested
        if emit_event and session_id:
            background_tasks.add_task(
                emit,
                session_id,
                EventType.GENERAL_ERROR,
                {
                    "message": f"Geocoding failed: {str(e)}",
                    "query": query
                }
            )

        return GeocodeResponse(
            results=[],
            query=query,
            count=0,
            status="error",
            error=f"Geocoding failed: {str(e)}"
        )

@router.post("/reverse", response_model=GeocodeResponse)
async def reverse_geocode_coordinates(
    request: ReverseGeocodeRequest,
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = None,
    emit_event: Optional[bool] = False
) -> GeocodeResponse:
    """
    Reverse geocode coordinates to get address details.

    Args:
        request: Reverse geocode request containing coordinates
        background_tasks: FastAPI background tasks
        session_id: Optional session ID for WebSocket events
        emit_event: Whether to emit WebSocket events

    Returns:
        Reverse geocoding results with address details
    """
    latitude = request.latitude
    longitude = request.longitude

    try:
        # Validate coordinates
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise HTTPException(
                status_code=400,
                detail="Invalid coordinates: latitude must be between -90 and 90, longitude between -180 and 180"
            )

        # Emit start event if requested
        if emit_event and session_id:
            background_tasks.add_task(
                emit,
                session_id,
                EventType.GEOCODE_STARTED,
                {"coordinates": f"{latitude}, {longitude}"}
            )

        # Reverse geocode the coordinates
        results = await reverse_geocode(latitude, longitude)

        # Prepare response
        response = GeocodeResponse(
            results=results,
            query=f"{latitude},{longitude}",
            count=len(results),
            status="success"
        )

        # Emit completion event if requested
        if emit_event and session_id:
            background_tasks.add_task(
                emit,
                session_id,
                EventType.REVERSE_GEOCODE_COMPLETED,
                {
                    "coordinates": f"{latitude}, {longitude}",
                    "results": results[:5]  # Limit event payload size
                }
            )

        return response

    except Exception as e:
        logger.error(f"Reverse geocoding error: {e}")

        # Emit error event if requested
        if emit_event and session_id:
            background_tasks.add_task(
                emit,
                session_id,
                EventType.GENERAL_ERROR,
                {
                    "message": f"Reverse geocoding failed: {str(e)}",
                    "coordinates": f"{latitude}, {longitude}"
                }
            )

        return GeocodeResponse(
            results=[],
            query=f"{latitude},{longitude}",
            count=0,
            status="error",
            error=f"Reverse geocoding failed: {str(e)}"
        )

@router.post("/timezone", response_model=Dict[str, Any])
async def get_timezone(
    request: TimezoneRequest,
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = None,
    emit_event: Optional[bool] = False
) -> Dict[str, Any]:
    """
    Get timezone information for coordinates.

    Args:
        request: Timezone request containing coordinates
        background_tasks: FastAPI background tasks
        session_id: Optional session ID for WebSocket events
        emit_event: Whether to emit WebSocket events

    Returns:
        Timezone information
    """
    latitude = request.latitude
    longitude = request.longitude

    try:
        # Validate coordinates
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            raise HTTPException(
                status_code=400,
                detail="Invalid coordinates: latitude must be between -90 and 90, longitude between -180 and 180"
            )

        # Get timezone for coordinates
        timezone_info = await get_timezone_for_coordinates(latitude, longitude)

        # Prepare response
        response = {
            "coordinates": f"{latitude},{longitude}",
            "timezone": timezone_info,
            "status": "success"
        }

        return response

    except Exception as e:
        logger.error(f"Timezone lookup error: {e}")

        # Emit error event if requested
        if emit_event and session_id:
            background_tasks.add_task(
                emit,
                session_id,
                EventType.GENERAL_ERROR,
                {
                    "message": f"Timezone lookup failed: {str(e)}",
                    "coordinates": f"{latitude}, {longitude}"
                }
            )

        return {
            "coordinates": f"{latitude},{longitude}",
            "timezone": {
                "timezone_id": "UTC",
                "timezone_name": "Coordinated Universal Time",
                "dst_offset": 0,
                "raw_offset": 0,
                "total_offset": 0,
                "source": "utc_standard"
            },
            "status": "error",
            "error": f"Timezone lookup failed: {str(e)}"
        }

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "ok", "service": "geocoding"}
