"""
Chart Router.

This module provides the API endpoints for chart generation and management.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body, Request, Response, BackgroundTasks, Header
from pydantic import BaseModel, Field
import os
import json
import uuid
from datetime import datetime, timedelta
from fastapi.responses import FileResponse
import re
import traceback
import tempfile
import base64
import asyncio

# Import chart service
from ai_service.services import get_chart_service

# Import other dependencies
from ai_service.api.services.openai import get_openai_service
from ai_service.core.rectification.main import comprehensive_rectification
from ai_service.utils.chart_visualizer import generate_comparison_chart, generate_3d_chart
from ai_service.database.repositories import ChartRepository

from ai_service.core.config import settings

# Import WebSocket manager
from ai_service.utils.websocket_manager import manager as ws_manager

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["chart"])

# Helper function to get chart repository
async def get_chart_repository():
    """Get instance of chart repository for data storage"""
    return ChartRepository()

# Define data models
class BirthDetails(BaseModel):
    """Birth details for chart generation."""
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format")
    birth_time: str = Field(..., description="Birth time in HH:MM:SS format")
    latitude: float = Field(..., description="Birth latitude")
    longitude: float = Field(..., description="Birth longitude")
    timezone: Optional[str] = Field(None, description="Timezone string (e.g., 'America/New_York')")
    location: Optional[str] = Field(None, description="Birth location name")
    house_system: Optional[str] = Field("P", description="House system to use (e.g., 'P' for Placidus)")
    zodiac_type: Optional[str] = Field("sidereal", description="Zodiac type (sidereal or tropical)")

class ChartGenerationRequest(BaseModel):
    """Request body for chart generation."""
    birth_details: BirthDetails = Field(..., description="Birth details for chart generation")
    verify_with_openai: bool = Field(True, description="Whether to verify the chart with OpenAI")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    generate_visualization: bool = Field(True, description="Whether to generate chart visualization")

class ChartResponse(BaseModel):
    """Response body for chart endpoints."""
    status: str = Field(..., description="Status of the operation")
    message: Optional[str] = Field(None, description="Message about the operation")
    chart_id: Optional[str] = Field(None, description="Generated chart ID")
    chart_data: Optional[Dict[str, Any]] = Field(None, description="Chart data")
    verification: Optional[Dict[str, Any]] = Field(None, description="Verification results if verified")

class RectificationRequest(BaseModel):
    """Request for birth time rectification."""
    chart_id: str = Field(..., description="ID of the chart to rectify")
    questionnaire_id: Optional[str] = Field(None, description="ID of the questionnaire with answers")
    responses: List[Dict[str, Any]] = Field(..., description="List of questionnaire responses")
    include_details: bool = Field(False, description="Whether to include detailed rectification process")
    session_id: Optional[str] = Field(None, description="Session ID for WebSocket progress updates")

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

class ChartVerificationRequest(BaseModel):
    """Request for chart verification."""
    sessionId: Optional[str] = Field(None, description="Session ID for tracking")
    chartId: str = Field(..., description="Chart ID to verify")

# Background task functions
async def generate_chart_visualization(chart_data: Dict[str, Any]) -> None:
    """
    Background task to generate chart visualizations.

    Args:
        chart_data: The chart data to visualize
    """
    try:
        chart_service = get_chart_service()

        # Generate different chart visualizations
        try:
            chart_service.generate_vedic_kundli_chart(chart_data)
            logger.info(f"Generated Vedic Kundli chart for chart_id: {chart_data.get('chart_id')}")
        except Exception as e:
            logger.error(f"Error generating Vedic chart: {e}")

        try:
            chart_service.generate_western_chart(chart_data)
            logger.info(f"Generated Western chart for chart_id: {chart_data.get('chart_id')}")
        except Exception as e:
            logger.error(f"Error generating Western chart: {e}")

    except Exception as e:
        logger.error(f"Error in chart visualization background task: {e}")

@router.post("/generate", response_model=ChartResponse)
async def generate_chart(
    chart_request: ChartGenerationRequest,
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Dict[str, Any]:
    """
    Generate a birth chart based on birth details.

    Args:
        chart_request: Birth details and options
        background_tasks: Background tasks to run
        session_id: Session ID from header

    Returns:
        Generated chart data or processing status
    """
    if not session_id and chart_request.session_id:
        session_id = chart_request.session_id

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    # Generate a chart ID (would normally come from a database)
    chart_id = f"chart_{uuid.uuid4().hex[:10]}"

    # Send initial processing message via WebSocket
    background_tasks.add_task(
        ws_manager.send_update,
        session_id,
        {
            "type": "chart_calculation_status",
            "status": "processing",
            "chart_id": chart_id,
            "message": "Chart calculation started"
        }
    )

    # Extract birth details
    birth_date = chart_request.birth_details.birth_date
    birth_time = chart_request.birth_details.birth_time
    latitude = chart_request.birth_details.latitude
    longitude = chart_request.birth_details.longitude
    timezone = chart_request.birth_details.timezone
    location = chart_request.birth_details.location
    verify_with_openai = chart_request.verify_with_openai

    logger.info(f"Generating chart for {birth_date} {birth_time} at {latitude}, {longitude}")

    try:
        # Get chart service using the async method to ensure proper initialization
        from ai_service.services import get_chart_service_async
        chart_service = await get_chart_service_async()

        # 1. Generate the chart with the service
        chart_data = await chart_service.generate_chart(
            birth_date=birth_date,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            location=location,
            verify_with_openai=verify_with_openai,
            session_id=session_id
        )

        # Generate chart visualization in the background
        if chart_request.generate_visualization:
            background_tasks.add_task(
                generate_chart_visualization,
                chart_data=chart_data
            )

        # 2. Return chart data with success status
        return ChartResponse(
            status="success",
            message="Chart generated successfully",
            chart_id=chart_data["chart_id"],
            chart_data=chart_data,
            verification=chart_data.get("verification", {})
        )

    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error in chart generation: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid chart data: {str(e)}"
        )

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Error generating chart: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Chart generation failed: {str(e)}"
        )

@router.get("/{chart_id}", response_model=ChartResponse, tags=["Chart"])
async def get_chart(
    chart_id: str,
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Dict[str, Any]:
    """
    Retrieve a previously generated chart.

    Args:
        chart_id: Chart ID to retrieve
        session_id: Session ID from header

    Returns:
        Chart data
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")

    logger.info(f"Retrieving chart {chart_id}")

    try:
        # Get chart service
        chart_service = get_chart_service()

        # Retrieve chart
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
async def verify_chart(request: ChartVerificationRequest) -> Dict[str, Any]:
    """
    Verify a chart's accuracy using OpenAI.

    Args:
        request: Verification request with chart ID

    Returns:
        Verification results
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get chart repository
        chart_repository = await get_chart_repository()

        # Get the chart data
        chart_data = await chart_repository.get_chart(request.chartId)
        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart with ID {request.chartId} not found")

        # Generate a verification ID
        verification_id = f"ver_{uuid.uuid4().hex[:8]}"

        # Import verification function directly to avoid circular imports
        from ai_service.services.chart_service_verification import verify_chart_with_openai

        # Get OpenAI service for verification
        openai_service = await get_openai_service()
        if not openai_service:
            raise HTTPException(
                status_code=503,
                detail="OpenAI service not available. Cannot perform chart verification."
            )

        # Verify chart
        try:
            verification_data = await verify_chart_with_openai(chart_data)

            # Format the response
            verification_result = {
                "verificationId": verification_id,
                "result": {
                    "confidence": verification_data.get("confidence", 0.8),
                    "suggestedCorrection": {
                        "adjustment": verification_data.get("suggested_adjustment", "None"),
                        "newTime": verification_data.get("suggested_time", chart_data.get("birth_details", {}).get("time", "")),
                        "reason": verification_data.get("adjustment_reason", "No adjustments needed")
                    },
                    "analysis": verification_data.get("verification_result", "Chart verified successfully.")
                }
            }
        except Exception as e:
            logger.error(f"Error in chart verification: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Chart verification failed: {str(e)}"
            )

        logger.info(f"Chart verification completed successfully with ID: {verification_id}")
        return verification_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying chart: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error verifying chart: {str(e)}")

@router.post("/api/v1/chart/verify", tags=["Chart"])
async def verify_chart_v1(request: ChartVerificationRequest) -> Dict[str, Any]:
    """
    API v1 endpoint for verifying a chart's accuracy using OpenAI.
    This endpoint is used by the integration tests and returns a format compatible with test expectations.

    Args:
        request: Verification request with chart ID and session ID

    Returns:
        Verification results in the format expected by integration tests
    """
    try:
        # Get chart repository
        chart_repository = await get_chart_repository()

        # Get the chart data
        chart_data = await chart_repository.get_chart(request.chartId)
        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart with ID {request.chartId} not found")

        # Generate a verification ID
        verification_id = f"ver_{uuid.uuid4().hex[:8]}"

        # Import verification function directly to avoid circular imports
        from ai_service.services.chart_service_verification import verify_chart_with_openai

        # Get OpenAI service for verification
        openai_service = await get_openai_service()
        if not openai_service:
            raise HTTPException(
                status_code=503,
                detail="OpenAI service not available. Cannot perform chart verification."
            )

        # Verify chart
        try:
            verification_data = await verify_chart_with_openai(chart_data)

            # Check if verification was successful
            if not verification_data:
                raise RuntimeError("Verification returned empty data")

            # Format the response in the expected structure for API v1
            verification_result = {
                "verificationId": verification_id,
                "result": {
                    "confidence": verification_data.get("confidence", 0.5),
                    "suggestedCorrection": {
                        "adjustment": verification_data.get("suggested_adjustment", "No adjustment needed"),
                        "newTime": verification_data.get("suggested_time", chart_data.get("birth_details", {}).get("time", "")),
                        "reason": verification_data.get("adjustment_reason", "Chart verified with no adjustment needed")
                    },
                    "analysis": verification_data.get("verification_result", "Chart verification completed")
                }
            }
        except Exception as e:
            logger.error(f"Error in chart verification: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Chart verification failed: {str(e)}"
            )

        logger.info(f"Chart verification completed successfully with ID: {verification_id}")
        return verification_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying chart: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error verifying chart: {str(e)}")

@router.post("/rectify", response_model=RectificationResponse, tags=["Chart"])
async def rectify_birth_time(
    request: RectificationRequest,
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Rectify birth time based on questionnaire responses and events.

    Args:
        request: Rectification request with chart ID and questionnaire data
        background_tasks: Background tasks for cleanup

    Returns:
        Rectification result with original and rectified charts
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get chart repository
        chart_repository = await get_chart_repository()

        # Get original chart
        original_chart = await chart_repository.get_chart(request.chart_id)
        if not original_chart:
            raise HTTPException(status_code=404, detail=f"Original chart with ID {request.chart_id} not found")

        # Extract birth details from original chart
        birth_details = original_chart.get("birth_details", {})
        if not birth_details:
            raise HTTPException(status_code=400, detail="Original chart missing birth details")

        # Convert birth details to datetime
        try:
            from datetime import datetime
            birth_date_str = birth_details.get("date", "")
            birth_time_str = birth_details.get("time", "")
            birth_dt_str = f"{birth_date_str} {birth_time_str}"
            birth_dt = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=f"Invalid birth date/time format: {ve}")

        # Extract location details
        latitude = birth_details.get("latitude")
        longitude = birth_details.get("longitude")
        timezone = birth_details.get("timezone", "UTC")

        # Perform rectification
        rectification_result = await comprehensive_rectification(
            birth_dt=birth_dt,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            answers=request.responses,
            options={"include_details": request.include_details}
        )

        # Store rectified chart
        rectified_chart_id = await chart_repository.store_chart(rectification_result.get("rectified_chart", {}))

        # Prepare response
        response = {
            "status": "success",
            "rectification_id": f"rect_{uuid.uuid4().hex[:8]}",
            "original_chart_id": request.chart_id,
            "rectified_chart_id": rectified_chart_id,
            "original_time": birth_time_str,
            "rectified_time": rectification_result.get("rectified_time", ""),
            "confidence_score": rectification_result.get("confidence_score", 0),
            "explanation": rectification_result.get("explanation", ""),
            "details": rectification_result.get("details") if request.include_details else None
        }

        # If background tasks are available, add cleanup
        if background_tasks:
            # Clean up temporary files if any were created
            temp_files = rectification_result.get("temp_files", [])
            for file_path in temp_files:
                if os.path.exists(file_path):
                    background_tasks.add_task(os.remove, file_path)

        logger.info(f"Birth time rectification completed with confidence: {response['confidence_score']}")
        return response
    except Exception as e:
        logger.error(f"Error rectifying birth time: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Birth time rectification failed: {str(e)}")

@router.post("/compare", response_model=Dict[str, Any], tags=["Chart"])
async def compare_charts(
    chart_ids: List[str] = Body(..., description="List of chart IDs to compare"),
    output_format: str = Query("json", description="Output format (json or image)"),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Compare multiple charts side by side.

    Args:
        chart_ids: List of chart IDs to compare
        output_format: Output format (json or image)
        background_tasks: Background tasks for cleanup

    Returns:
        Comparison data or image
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get chart repository
        chart_repository = await get_chart_repository()

        # Fetch all charts
        charts = []
        for chart_id in chart_ids:
            chart = await chart_repository.get_chart(chart_id)
            if not chart:
                raise HTTPException(status_code=404, detail=f"Chart with ID {chart_id} not found")
            charts.append(chart)

        # Compare charts
        comparison_result = await chart_service.compare_charts(charts)

        # Generate visualization if requested
        if output_format.lower() == "image":
            # Create temp file for image
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_path = temp_file.name

            # Generate comparison visualization
            image_path = generate_comparison_chart(
                charts[0],  # First chart
                charts[1] if len(charts) > 1 else None,  # Second chart if available
                output_path=temp_path
            )

            # Add image data to result
            if isinstance(image_path, str):  # Ensure image_path is a string
                with open(image_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode("utf-8")
                    comparison_result["image"] = f"data:image/png;base64,{img_data}"
            else:
                logger.error(f"Invalid image path type: {type(image_path)}")
                raise HTTPException(status_code=500, detail="Failed to generate chart comparison image")

            # Clean up temp file
            if background_tasks:
                background_tasks.add_task(os.remove, image_path)

        logger.info(f"Chart comparison completed for {len(charts)} charts")
        return comparison_result
    except Exception as e:
        logger.error(f"Error comparing charts: {e}")
        raise HTTPException(status_code=500, detail=f"Chart comparison failed: {str(e)}")

@router.get("/export/{chart_id}", tags=["Chart"])
async def export_chart(
    chart_id: str = Path(..., description="Chart ID to export"),
    format: str = Query("pdf", description="Export format (pdf, png, json)"),
    background_tasks: BackgroundTasks = None
) -> FileResponse:
    """
    Export chart to various formats.

    Args:
        chart_id: The ID of the chart to export
        format: Export format (pdf, png, json)
        background_tasks: Background tasks for cleanup

    Returns:
        Exported chart file
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get chart repository
        chart_repository = await get_chart_repository()

        # Get chart data
        chart_data = await chart_repository.get_chart(chart_id)
        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart with ID {chart_id} not found")

        # Create temporary file with appropriate extension
        ext = format.lower()
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as temp_file:
            temp_path = temp_file.name

        # Generate exported file based on format
        if format.lower() == "json":
            # Export as JSON
            with open(temp_path, "w") as json_file:
                json.dump(chart_data, json_file, indent=2)
        elif format.lower() in ("pdf", "png", "jpg"):
            # Export as image or PDF
            if format.lower() == "pdf":
                # Generate PDF with chart visualization
                # This would typically use a PDF generation library
                pass
            else:
                # Generate image using chart visualizer
                generate_3d_chart(chart_data, output_path=temp_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")

        # Set up background task to clean up temp file
        if background_tasks:
            # Schedule file deletion after response is sent
            background_tasks.add_task(os.remove, temp_path)

        # Return file response
        return FileResponse(
            path=temp_path,
            media_type=f"application/{format.lower()}" if format.lower() == "pdf" else f"image/{format.lower()}",
            filename=f"chart_{chart_id}.{format.lower()}"
        )
    except Exception as e:
        logger.error(f"Error exporting chart: {e}")
        raise HTTPException(status_code=500, detail=f"Chart export failed: {str(e)}")

# Add a plural version of the endpoint for compatibility with v1 API
@router.post("/charts/generate", response_model=ChartResponse)
async def generate_charts(
    chart_request: ChartGenerationRequest,
    background_tasks: BackgroundTasks,
    request: Request
) -> ChartResponse:
    """
    Generate a new astrological chart (plural endpoint for v1 API compatibility).

    This is an alias of the /chart/generate endpoint that maintains compatibility
    with the v1 API that uses plural 'charts' in the path.

    Args:
        chart_request: Birth details and options
        background_tasks: FastAPI background tasks
        request: FastAPI request object

    Returns:
        ChartResponse: Generated chart data with verification status
    """
    # Simply delegate to the singular endpoint
    return await generate_chart(chart_request, background_tasks, request)
