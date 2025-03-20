"""
Chart Router.

This module provides the API endpoints for chart generation and management.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body, Request, Response
from pydantic import BaseModel, Field
import os
import json
import uuid
from datetime import datetime, timedelta
from fastapi.responses import FileResponse
from fastapi.background import BackgroundTasks

from ai_service.services.chart_service import get_chart_service, create_chart_service
from ai_service.api.services.openai.service import get_openai_service
from ai_service.core.rectification import comprehensive_rectification
from ai_service.utils.chart_visualizer import generate_comparison_chart
from ai_service.database.repositories import ChartRepository

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Helper function to get chart repository
async def get_chart_repository():
    """Get instance of chart repository for data storage"""
    from ai_service.database.repositories import ChartRepository
    return ChartRepository()

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


class RectificationRequest(BaseModel):
    """Request for birth time rectification."""
    chart_id: str = Field(..., description="ID of the chart to rectify")
    questionnaire_id: Optional[str] = Field(None, description="ID of the questionnaire with answers")
    responses: List[Dict[str, Any]] = Field(..., description="List of questionnaire responses")
    include_details: bool = Field(False, description="Whether to include detailed rectification process")


class RectificationResponse(BaseModel):
    """Response for birth time rectification."""
    status: str
    rectification_id: str
    original_chart_id: str
    rectified_chart_id: str
    original_time: str
    rectified_time: str
    confidence_score: float
    explanation: str
    details: Optional[Dict[str, Any]] = None


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


@router.post("/rectify", response_model=RectificationResponse, tags=["Chart"])
async def rectify_chart(request: RectificationRequest) -> Dict[str, Any]:
    """
    Rectify birth time based on questionnaire responses using astrological analysis.

    This endpoint performs birth time rectification using a comprehensive algorithm that
    analyzes questionnaire responses and astrological patterns to determine a more accurate
    birth time.

    Args:
        request: Rectification request with chart ID and questionnaire responses

    Returns:
        Rectification results including original and rectified times, confidence score,
        and explanation of the rectification process
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get original chart data
        chart_data = await chart_service.get_chart(request.chart_id)
        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart not found with ID: {request.chart_id}")

        # Perform rectification
        rectification_result = await chart_service.rectify_chart(
            chart_id=request.chart_id,
            questionnaire_id=request.questionnaire_id or "direct_api_call",
            answers=request.responses,
            include_details=request.include_details
        )

        logger.info(f"Birth time rectification completed for chart {request.chart_id} with "
                   f"confidence {rectification_result.get('confidence_score', 0)}")

        return rectification_result

    except ValueError as e:
        # Handle specific validation errors
        logger.error(f"Validation error in rectification: {e}")
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")
    except Exception as e:
        # Handle general errors
        logger.error(f"Error rectifying birth time: {e}")
        raise HTTPException(status_code=500, detail=f"Error rectifying birth time: {str(e)}")


@router.post("/export", response_model=Dict[str, Any])
async def export_chart(
    chart_id: str = Body(..., description="Chart ID to export"),
    format: str = Body("pdf", description="Export format: pdf, png, jpg"),
    include_interpretation: bool = Body(True, description="Include astrological interpretation in export")
):
    """
    Generate exportable files of an astrological chart.

    This endpoint generates a PDF or image file of the chart for download.
    """
    chart_service = get_chart_service()

    try:
        # Validate chart exists
        chart = await chart_service.get_chart(chart_id)
        if not chart:
            raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")

        # Validate format
        if format.lower() not in ["pdf", "png", "jpg", "jpeg"]:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

        # Standardize format
        if format.lower() == "jpg":
            format = "jpeg"

        # Generate export
        export_result = await chart_service.export_chart(chart_id, format)

        if not export_result or "export_id" not in export_result:
            raise HTTPException(status_code=500, detail="Failed to generate export")

        # Return export details
        return {
            "status": "success",
            "export_id": export_result["export_id"],
            "chart_id": chart_id,
            "format": format,
            "download_url": export_result["download_url"],
            "expires_at": export_result.get("expires_at", (datetime.now() + timedelta(days=7)).isoformat())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chart export: {e}")
        raise HTTPException(status_code=500, detail=f"Chart export failed: {str(e)}")

@router.get("/download/{export_id}/{format}")
async def download_chart_export(
    export_id: str,
    format: str,
    background_tasks: BackgroundTasks
):
    """
    Download a previously generated chart export.

    This endpoint returns the actual file for download.
    """
    chart_service = get_chart_service()

    try:
        # Get export details from chart repository instead of using non-existent method
        chart_repository = await get_chart_repository()
        export_details = await chart_repository.get_export(export_id)

        if not export_details:
            raise HTTPException(status_code=404, detail=f"Export {export_id} not found")

        # Check if export has expired
        expires_at = datetime.fromisoformat(export_details.get("expires_at", "2099-12-31T00:00:00"))
        if datetime.now() > expires_at:
            raise HTTPException(status_code=410, detail="Export has expired")

        # Get file path
        file_path = export_details.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Export file not found")

        # Determine content type
        content_types = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpeg": "image/jpeg"
        }

        content_type = content_types.get(format.lower(), "application/octet-stream")

        # Log download but skip updating count (we don't have the right method)
        logger.info(f"Export {export_id} downloaded in {format} format")

        # In a real implementation, we would update download count
        # For now, we'll simply log the download event
        background_tasks.add_task(
            lambda: logger.info(f"Download of export {export_id} completed")
        )

        # Return file
        return FileResponse(
            path=file_path,
            filename=f"chart_{export_details.get('chart_id')}_{datetime.now().strftime('%Y%m%d')}.{format}",
            media_type=content_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chart download: {e}")
        raise HTTPException(status_code=500, detail=f"Chart download failed: {str(e)}")

@router.get("/compare", response_model=Dict[str, Any])
async def compare_charts(
    chart1_id: str = Query(..., description="First chart ID for comparison"),
    chart2_id: str = Query(..., description="Second chart ID for comparison"),
    interpretation_level: str = Query("detailed", description="Level of astrological interpretation: basic, detailed, or comprehensive")
):
    """
    Compare two astrological charts with deep astrological interpretation.

    This endpoint analyzes the differences between two charts and provides
    detailed astrological interpretation of the differences.
    """
    chart_service = get_chart_service()
    openai_service = get_openai_service()

    try:
        # Get both charts
        chart1 = await chart_service.get_chart(chart1_id)
        if not chart1:
            raise HTTPException(status_code=404, detail=f"Chart {chart1_id} not found")

        chart2 = await chart_service.get_chart(chart2_id)
        if not chart2:
            raise HTTPException(status_code=404, detail=f"Chart {chart2_id} not found")

        # Extract key birth details for context
        chart1_details = chart1.get("birth_details", {})
        chart2_details = chart2.get("birth_details", {})

        # Calculate basic differences
        differences = {
            "planetary_positions": [],
            "house_cusps": [],
            "aspects": [],
            "key_points": []
        }

        # Compare planetary positions
        chart1_planets = {p.get("name"): p for p in chart1.get("planets", [])}
        chart2_planets = {p.get("name"): p for p in chart2.get("planets", [])}

        for planet_name in set(chart1_planets.keys()).union(chart2_planets.keys()):
            planet1 = chart1_planets.get(planet_name)
            planet2 = chart2_planets.get(planet_name)

            if planet1 and planet2:
                # Calculate degree difference
                sign1_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3, "Leo": 4, "Virgo": 5,
                              "Libra": 6, "Scorpio": 7, "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(planet1.get("sign"), 0)
                sign2_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3, "Leo": 4, "Virgo": 5,
                              "Libra": 6, "Scorpio": 7, "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(planet2.get("sign"), 0)

                pos1 = sign1_index * 30 + planet1.get("degree", 0)
                pos2 = sign2_index * 30 + planet2.get("degree", 0)

                # Calculate absolute difference in degrees
                diff = min(abs(pos1 - pos2), 360 - abs(pos1 - pos2))

                # Check if house changed
                house_changed = planet1.get("house") != planet2.get("house")

                # Add to differences
                differences["planetary_positions"].append({
                    "planet": planet_name,
                    "chart1_position": f"{planet1.get('sign')} {planet1.get('degree'):.2f}°",
                    "chart2_position": f"{planet2.get('sign')} {planet2.get('degree'):.2f}°",
                    "degree_difference": diff,
                    "house_changed": house_changed,
                    "significance": "high" if planet_name in ["Sun", "Moon", "Ascendant"] or diff > 5 else "medium"
                })

        # Compare house cusps
        chart1_houses = {h.get("number"): h for h in chart1.get("houses", [])}
        chart2_houses = {h.get("number"): h for h in chart2.get("houses", [])}

        for house_num in range(1, 13):
            house1 = chart1_houses.get(house_num)
            house2 = chart2_houses.get(house_num)

            if house1 and house2:
                sign1_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3, "Leo": 4, "Virgo": 5,
                              "Libra": 6, "Scorpio": 7, "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(house1.get("sign"), 0)
                sign2_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3, "Leo": 4, "Virgo": 5,
                              "Libra": 6, "Scorpio": 7, "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(house2.get("sign"), 0)

                pos1 = sign1_index * 30 + house1.get("degree", 0)
                pos2 = sign2_index * 30 + house2.get("degree", 0)

                # Calculate absolute difference
                diff = min(abs(pos1 - pos2), 360 - abs(pos1 - pos2))

                # Add to differences
                differences["house_cusps"].append({
                    "house": house_num,
                    "chart1_position": f"{house1.get('sign')} {house1.get('degree'):.2f}°",
                    "chart2_position": f"{house2.get('sign')} {house2.get('degree'):.2f}°",
                    "degree_difference": diff,
                    "sign_changed": house1.get("sign") != house2.get("sign"),
                    "significance": "high" if house_num in [1, 4, 7, 10] else "medium"
                })

        # Use OpenAI for deep astrological interpretation
        interpretation_request = {
            "chart1": {
                "birth_details": chart1_details,
                "ascendant": chart1.get("ascendant", {}),
                "planets": chart1.get("planets", []),
                "houses": chart1.get("houses", [])
            },
            "chart2": {
                "birth_details": chart2_details,
                "ascendant": chart2.get("ascendant", {}),
                "planets": chart2.get("planets", []),
                "houses": chart2.get("houses", [])
            },
            "differences": differences,
            "interpretation_level": interpretation_level,
            "task": "chart_comparison_interpretation"
        }

        # Get interpretation from OpenAI
        interpretation_response = await openai_service.generate_completion(
            prompt=json.dumps(interpretation_request),
            task_type="astrological_interpretation",
            max_tokens=1000
        )

        if interpretation_response and "content" in interpretation_response:
            try:
                interpretation = json.loads(interpretation_response["content"])

                # Generate comparison ID and store
                comparison_id = f"comp_{uuid.uuid4().hex[:8]}"

                # Store comparison results with interpretation
                comparison_data = {
                    "comparison_id": comparison_id,
                    "chart1_id": chart1_id,
                    "chart2_id": chart2_id,
                    "differences": differences,
                    "interpretation": interpretation,
                    "created_at": datetime.now().isoformat()
                }

                # Try to store the comparison, but don't block if it fails
                try:
                    # Create a file-based storage as a fallback
                    from ai_service.core.config import settings

                    # Ensure directory exists
                    comparisons_dir = os.path.join(settings.MEDIA_ROOT, "comparisons")
                    os.makedirs(comparisons_dir, exist_ok=True)

                    # Write comparison to file
                    comparison_file_path = os.path.join(comparisons_dir, f"{comparison_id}.json")
                    with open(comparison_file_path, "w") as f:
                        json.dump(comparison_data, f, indent=2)

                    logger.info(f"Comparison {comparison_id} stored in file system")
                except Exception as storage_error:
                    logger.error(f"Error storing comparison data: {storage_error}")
                    # Continue anyway - the comparison was successful even if storage failed

                # Return enhanced comparison with interpretation
                return {
                    "status": "success",
                    "comparison_id": comparison_id,
                    "chart1_id": chart1_id,
                    "chart2_id": chart2_id,
                    "differences": differences,
                    "interpretation": interpretation
                }
            except json.JSONDecodeError:
                logger.error("Error parsing OpenAI response for comparison interpretation")
                raise HTTPException(status_code=500, detail="Error in astrological interpretation")
        else:
            logger.error("Failed to get interpretation from OpenAI")
            raise HTTPException(status_code=500, detail="Failed to generate astrological interpretation")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chart comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Chart comparison failed: {str(e)}")

@router.get("/download/comparison/{filename}", response_class=Response)
async def download_comparison(
    filename: str,
    response: Response
) -> Any:
    """
    Download a chart comparison visualization.

    This endpoint returns the binary data of a comparison chart image.

    Args:
        filename: Filename of the comparison chart image

    Returns:
        Binary image data with appropriate content type
    """
    try:
        # Construct the file path
        from ai_service.core.config import settings
        file_path = os.path.join(settings.MEDIA_ROOT, "exports", "comparisons", filename)

        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"Comparison file not found: {filename}")

        # Set content type based on file extension
        if filename.lower().endswith(".png"):
            response.headers["Content-Type"] = "image/png"
        elif filename.lower().endswith((".jpg", ".jpeg")):
            response.headers["Content-Type"] = "image/jpeg"
        else:
            response.headers["Content-Type"] = "application/octet-stream"

        # Set content disposition for display
        response.headers["Content-Disposition"] = f"inline; filename={filename}"

        # Read and return file content
        with open(file_path, "rb") as f:
            content = f.read()

        return content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Error downloading comparison: {str(e)}")
