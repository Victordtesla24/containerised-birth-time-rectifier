"""
Chart Router.

This module provides the API endpoints for chart generation and management.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field

from ai_service.services.chart_service import get_chart_service, create_chart_service
from ai_service.api.services.openai.service import get_openai_service

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Define data models
class BirthDetails(BaseModel):
    """Birth details for chart generation."""
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format")
    birth_time: str = Field(..., description="Birth time in HH:MM:SS format")
    latitude: float = Field(..., description="Birth latitude")
    longitude: float = Field(..., description="Birth longitude")
    timezone: Optional[str] = Field(None, description="Timezone, e.g., 'America/New_York'")
    location: Optional[str] = Field(None, description="Location name")


class ChartGenerationRequest(BaseModel):
    """Request for chart generation."""
    birth_details: BirthDetails
    verify_with_openai: bool = Field(True, description="Whether to verify the chart with OpenAI")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")


class ChartResponse(BaseModel):
    """Response for chart generation and retrieval."""
    chart_id: str
    generated_at: str
    birth_details: Optional[Dict[str, Any]] = None
    ascendant: Optional[Dict[str, Any]] = None
    planets: Optional[List[Dict[str, Any]]] = None
    houses: Optional[List[Dict[str, Any]]] = None
    verification: Optional[Dict[str, Any]] = None


@router.post("/generate", response_model=ChartResponse, tags=["Chart"])
async def generate_chart(request: ChartGenerationRequest) -> Dict[str, Any]:
    """
    Generate a new astrological chart based on birth details.

    Args:
        request: Chart generation request with birth details

    Returns:
        Generated chart data
    """
    try:
        # Get chart service with session ID if provided
        if request.session_id:
            chart_service = create_chart_service(session_id=request.session_id)
        else:
            chart_service = get_chart_service()

        # Generate chart
        chart_data = await chart_service.generate_chart(
            birth_date=request.birth_details.birth_date,
            birth_time=request.birth_details.birth_time,
            latitude=request.birth_details.latitude,
            longitude=request.birth_details.longitude,
            timezone=request.birth_details.timezone,
            location=request.birth_details.location,
            verify_with_openai=request.verify_with_openai
        )

        logger.info(f"Chart generated successfully with ID: {chart_data.get('chart_id', 'unknown')}")
        return chart_data

    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating chart: {str(e)}")


@router.get("/{chart_id}", response_model=ChartResponse, tags=["Chart"])
async def get_chart(chart_id: str = Path(..., description="Chart ID")) -> Dict[str, Any]:
    """
    Retrieve an existing chart by ID.

    Args:
        chart_id: The ID of the chart to retrieve

    Returns:
        Chart data
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get chart
        chart_data = await chart_service.get_chart(chart_id)

        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart with ID {chart_id} not found")

        logger.info(f"Retrieved chart with ID: {chart_id}")
        return chart_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chart: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving chart: {str(e)}")


@router.post("/verify", tags=["Chart"])
async def verify_chart(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify a chart's accuracy using OpenAI.

    Args:
        chart_data: The chart data to verify

    Returns:
        Verification results
    """
    try:
        # Get OpenAI service
        openai_service = get_openai_service()

        # Verify chart
        verification_result = await openai_service.verify_chart(chart_data)

        logger.info(f"Chart verification completed with confidence: {verification_result.get('confidence', 0)}")
        return verification_result

    except Exception as e:
        logger.error(f"Error verifying chart: {e}")
        raise HTTPException(status_code=500, detail=f"Error verifying chart: {str(e)}")
