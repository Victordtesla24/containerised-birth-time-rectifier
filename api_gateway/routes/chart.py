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
router = APIRouter(prefix="/api/chart", tags=["chart"])

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

# AI Service URL
AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://localhost:8001")
if AI_SERVICE_URL and AI_SERVICE_URL.endswith("/"):
    AI_SERVICE_URL = AI_SERVICE_URL[:-1]

async def proxy_chart_request(request: Request, path: str) -> Dict[str, Any]:
    """
    Generic proxy function to forward chart requests to the AI service.

    Args:
        request: The incoming request
        path: Path to append to the AI service URL (without leading slash)

    Returns:
        The JSON response from the AI service
    """
    # Normalize path by removing any leading slashes
    path = path.lstrip('/')

    # Construct the target URL
    target_url = f"{AI_SERVICE_URL}/api/v1/chart/{path}"

    # Get request method and params
    method = request.method
    params = dict(request.query_params)

    logger.info(f"Proxying {method} chart request to {target_url}")

    # Extract headers (excluding host)
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ["host", "content-length"]}

    try:
        async with httpx.AsyncClient(
            verify=True,  # Explicitly enable SSL verification
            timeout=60.0
        ) as client:
            # Handle request based on method
            if method == "GET":
                response = await client.get(target_url, params=params, headers=headers)
            elif method == "POST":
                body = await request.body()
                response = await client.post(target_url, content=body, headers=headers)
            elif method == "PUT":
                body = await request.body()
                response = await client.put(target_url, content=body, headers=headers)
            else:
                raise HTTPException(
                    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                    detail=f"Method {method} not allowed"
                )

            # Check if response is successful
            if response.status_code >= 400:
                logger.error(f"Error from AI service: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Error from chart service: {response.text}"
                )

            # Return response content
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON response: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid response from chart service"
                )
    except httpx.RequestError as e:
        logger.error(f"Error making request to AI service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chart service unavailable"
        )

@router.post("/validate")
async def validate_chart(request: Request):
    """
    Validate birth chart data.
    Proxies to the AI service's chart validation endpoint.
    """
    return await proxy_chart_request(request, "validate")

@router.post("/generate")
async def generate_chart(request: Request):
    """
    Generate a birth chart.
    Proxies to the AI service's chart generation endpoint.
    """
    return await proxy_chart_request(request, "generate")

@router.get("/{chart_id}")
async def get_chart(request: Request, chart_id: str):
    """
    Get chart details by ID.
    Proxies to the AI service's chart retrieval endpoint.
    """
    return await proxy_chart_request(request, chart_id)

@router.post("/rectify")
async def rectify_chart(request: Request):
    """
    Rectify a birth chart.
    Proxies to the AI service's chart rectification endpoint.
    """
    return await proxy_chart_request(request, "rectify")

@router.get("/compare")
async def compare_charts(
    request: Request,
    chart1: str,
    chart2: str
):
    """
    Compare two charts.
    Proxies to the AI service's chart comparison endpoint.
    """
    # Add chart IDs to query parameters
    return await proxy_chart_request(request, "compare")

@router.post("/export")
async def export_chart(request: Request):
    """
    Export a chart.
    Proxies to the AI service's chart export endpoint.
    """
    return await proxy_chart_request(request, "export")

@router.get("/export/{export_id}/download")
async def download_export(request: Request, export_id: str):
    """
    Download a chart export.
    Proxies to the AI service's chart export download endpoint.
    """
    return await proxy_chart_request(request, f"export/{export_id}/download")
