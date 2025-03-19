"""
Chart-related API routes
-----------------------
Handles all chart-related API requests including rectification, analysis, and visualization.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import Dict, Any, Optional, List
import httpx
import os
import json
import logging
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger("api_gateway.routes.chart")

# Initialize router
router = APIRouter()

# Define request/response models
class ChartRectificationRequest(BaseModel):
    birth_details: Dict[str, Any] = Field(..., description="Birth details including date, time, and location")
    questionnaire_responses: List[Dict[str, Any]] = Field(default=[], description="Responses to the rectification questionnaire")

class ChartExplanationRequest(BaseModel):
    chart_id: str = Field(..., description="ID of the chart to explain")
    explanation_type: str = Field(default="general", description="Type of explanation to generate")

class ChartComparisonRequest(BaseModel):
    chart1_id: str = Field(..., description="ID of the first chart")
    chart2_id: str = Field(..., description="ID of the second chart")
    comparison_type: str = Field(default="differences", description="Type of comparison to perform")
    include_significance: bool = Field(default=True, description="Whether to include significance ratings")

class ChartGenerationRequest(BaseModel):
    birth_date: str = Field(..., description="Birth date in ISO format (YYYY-MM-DD)")
    birth_time: str = Field(..., description="Birth time in 24-hour format (HH:MM)")
    latitude: float = Field(..., description="Latitude of birth place")
    longitude: float = Field(..., description="Longitude of birth place")
    location: str = Field(default="", description="Birth location name")
    timezone: str = Field(default="UTC", description="Timezone name (from pytz)")
    verify_with_openai: bool = Field(default=True, description="Whether to verify chart with OpenAI")
    house_system: str = Field(default="P", description="House system to use (P=Placidus, etc.)")
    zodiac_type: str = Field(default="sidereal", description="Zodiac type (sidereal/tropical)")

# Helper function to request data from the AI service
async def request_ai_service(endpoint: str, data: Dict[str, Any] = {}, method: str = "POST") -> Dict[str, Any]:
    """Send a request to the AI service"""
    ai_service_url = os.getenv("AI_SERVICE_URL", "http://ai_service:8000")

    url = f"{ai_service_url}/api/v1/{endpoint}"
    logger.info(f"Requesting AI service at {url}")

    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, params=data, timeout=60.0)
            else:
                response = await client.post(url, json=data, timeout=60.0)

            if response.status_code != 200:
                logger.error(f"AI service returned error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"AI service error: {response.text}"
                )

            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error requesting AI service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable"
        )

# Chart comparison endpoint (GET) - Must be defined BEFORE the {chart_id} endpoint
@router.get("/compare", response_model=Dict[str, Any])
async def compare_charts_get(
    chart1_id: str = Query(..., description="ID of the first chart"),
    chart2_id: str = Query(..., description="ID of the second chart"),
    comparison_type: str = Query("differences", description="Type of comparison to perform"),
    include_significance: bool = Query(True, description="Include significance ratings")
):
    """
    Compare two astrological charts using a GET request with query parameters.

    This endpoint analyzes differences between two charts, such as planetary positions,
    house placements, and aspects. It supports different comparison types.

    Args:
        chart1_id: ID of the first chart
        chart2_id: ID of the second chart
        comparison_type: Type of comparison to perform (differences, full, summary)
        include_significance: Whether to include significance ratings

    Returns:
        A detailed comparison of the two charts
    """
    logger.info(f"GET compare request: chart1={chart1_id}, chart2={chart2_id}, type={comparison_type}")

    try:
        # Using the /compare/root endpoint to avoid routing conflicts with the {chart_id} endpoint
        result = await request_ai_service(
            endpoint="chart/compare/root",
            data={
                "chart1_id": chart1_id,
                "chart2_id": chart2_id,
                "comparison_type": comparison_type,
                "include_significance": include_significance
            },
            method="GET"
        )
        return result
    except Exception as e:
        logger.error(f"Chart comparison failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chart comparison failed: {str(e)}")

# Chart comparison endpoint (POST)
@router.post("/compare", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def compare_charts_post(request: ChartComparisonRequest):
    """
    Compare two charts and highlight key differences using POST method.

    Request body:
    - chart1_id: ID of the first chart
    - chart2_id: ID of the second chart
    - comparison_type: Type of comparison (differences, full, summary)
    - include_significance: Whether to include significance ratings
    """
    try:
        # Use the correct endpoint path for the AI service
        result = await request_ai_service("chart/compare", request.dict())
        return result
    except Exception as exc:
        logger.error(f"Error in chart comparison: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chart comparison failed: {str(exc)}"
        )

# Chart generation endpoint
@router.post("/generate", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def generate_chart(request: ChartGenerationRequest):
    """
    Generate an astrological chart based on birth details.

    Request body:
    - birth_date: Birth date in ISO format (YYYY-MM-DD)
    - birth_time: Birth time in 24-hour format (HH:MM)
    - latitude: Latitude of birth location
    - longitude: Longitude of birth location
    - location: Birth location name
    - timezone: Timezone of birth location
    - verify_with_openai: Whether to verify with OpenAI
    - house_system: House system to use
    - zodiac_type: Zodiac type (sidereal/tropical)
    """
    try:
        logger.info(f"Generating chart for {request.birth_date} {request.birth_time} at {request.latitude}, {request.longitude}")

        # Use the correct endpoint path for the AI service
        result = await request_ai_service("chart/generate", request.dict())

        # Ensure we have a chart_id in the response
        if "chart_id" not in result:
            result["chart_id"] = f"chart_{os.urandom(5).hex()}"

        return result
    except Exception as exc:
        logger.error(f"Error in chart generation: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chart generation failed: {str(exc)}"
        )

@router.get("/{chart_id}", status_code=status.HTTP_200_OK)
async def get_chart(chart_id: str):
    """
    Get a chart by ID.
    """
    try:
        result = await request_ai_service(f"chart/{chart_id}", {}, method="GET")
        return result
    except Exception as exc:
        logger.error(f"Error retrieving chart: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chart retrieval failed: {str(exc)}"
        )
