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
import re
import traceback
import tempfile
import base64
import asyncio

from ai_service.services import get_chart_service
from ai_service.api.services.openai import get_openai_service
from ai_service.core.rectification.main import comprehensive_rectification
from ai_service.utils.chart_visualizer import generate_comparison_chart, generate_3d_chart
from ai_service.database.repositories import ChartRepository
from ai_service.core.config import settings
from ai_service.services.chart_service import ChartService

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


@router.post("/generate", response_model=ChartResponse, tags=["Chart"])
async def generate_chart(request: ChartGenerationRequest) -> Dict[str, Any]:
    """
    Generate an astrological chart from birth details.

    This endpoint calculates planetary positions, house cusps, and chart data
    from birth date, time, and location. If requested, the chart is verified
    against Indian Vedic astrological standards via OpenAI.

    Args:
        request: Chart generation request with birth details and options

    Returns:
        Complete chart data with planetary positions and houses
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get chart repository
        chart_repository = await get_chart_repository()

        # Extract birth details from request
        birth_details = request.birth_details
        verify_with_openai = request.verify_with_openai

        # Log the request
        logger.info(f"Generating chart for birth date {birth_details.birth_date}, time {birth_details.birth_time}")

        # Validate birth details
        # (This would normally do more detailed validation)
        if not birth_details.birth_date or not birth_details.birth_time:
            raise HTTPException(status_code=400, detail="Invalid birth details")

        # Calculate chart data
        birth_datetime = f"{birth_details.birth_date} {birth_details.birth_time}"

        try:
            chart_data = chart_service.calculate_chart(
                birth_date=birth_details.birth_date,
                birth_time=birth_details.birth_time,
                latitude=birth_details.latitude,
                longitude=birth_details.longitude,
                timezone=birth_details.timezone or "UTC",
                verify_with_openai=verify_with_openai
            )
        except Exception as calc_error:
            logger.error(f"Error calculating chart: {calc_error}")
            raise HTTPException(status_code=500, detail=f"Chart calculation error: {str(calc_error)}")

        # Chart already verified in calculate_chart if requested
        # No need to verify again here

        # Generate a unique ID for the chart if not already present
        if "chart_id" not in chart_data:
            chart_id = f"chart_{uuid.uuid4().hex[:8]}"
            chart_data["chart_id"] = chart_id
        else:
            chart_id = chart_data["chart_id"]

        # Store chart data in repository if not already stored
        try:
            # Add generation timestamp if not present
            if "generated_at" not in chart_data:
                chart_data["generated_at"] = datetime.now().isoformat()

            # Add birth details for reference if not present
            if "birth_data" not in chart_data:
                chart_data["birth_data"] = {
                    "date": birth_details.birth_date,
                    "time": birth_details.birth_time,
                    "latitude": birth_details.latitude,
                    "longitude": birth_details.longitude,
                    "location": birth_details.location,
                    "timezone": birth_details.timezone
                }

            # Store in repository
            await chart_repository.store_chart(chart_data)

        except Exception as store_error:
            logger.error(f"Error storing chart: {store_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Chart generated but could not be stored: {str(store_error)}"
            )

        # Return chart data
        logger.info(f"Chart {chart_id} generated successfully")
        return chart_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {str(e)}")


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

        # Get chart repository to retrieve the chart
        chart_repository = await get_chart_repository()

        # Get chart from repository
        chart_data = await chart_repository.get_chart(chart_id)

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

        # Get chart repository
        chart_repository = await get_chart_repository()

        # Get original chart data
        chart_data = await chart_repository.get_chart(request.chart_id)
        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart not found with ID: {request.chart_id}")

        # Perform rectification using the core rectification function
        from ai_service.core.rectification.main import comprehensive_rectification

        # Extract birth details from chart
        birth_data = chart_data.get("birth_data", {})

        # Convert to datetime
        try:
            from datetime import datetime
            birth_dt = datetime.fromisoformat(f"{birth_data.get('date')}T{birth_data.get('time')}")
        except Exception as e:
            logger.error(f"Error parsing birth date/time: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid birth date/time format: {str(e)}")

        # Perform rectification
        rectification_result = await comprehensive_rectification(
            birth_dt=birth_dt,
            latitude=birth_data.get("latitude"),
            longitude=birth_data.get("longitude"),
            timezone=birth_data.get("timezone"),
            answers=request.responses,
            chart_id=request.chart_id
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
    include_interpretation: bool = Body(True, description="Include astrological interpretation in export"),
    paper_size: str = Body("letter", description="Paper size for PDF (letter, a4, legal)"),
    is_3d: bool = Query(False, description="Whether to include 3D visualization")
):
    """
    Generate exportable files of an astrological chart.

    This endpoint generates a PDF or image file of the chart for download with
    proper astrological interpretation if requested.
    """
    chart_service = get_chart_service()
    chart_repository = await get_chart_repository()

    try:
        # Validate chart exists
        chart = None
        try:
            chart = await chart_repository.get_chart(chart_id)
            if not chart:
                raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving chart: {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving chart data: {str(e)}")

        # Validate format
        supported_formats = ["pdf", "png", "jpg", "jpeg"]
        if format.lower() not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format: {format}. Supported formats: {', '.join(supported_formats)}"
            )

        # Standardize format
        if format.lower() == "jpg":
            format = "jpeg"

        # Get interpretation if requested with proper error handling
        interpretation = None
        if include_interpretation:
            logger.info(f"Generating interpretation for chart {chart_id} export")

            # Get OpenAI service with retry mechanism
            openai_service = get_openai_service()
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    # Create interpretation request
                    interpretation_request = {
                        "chart_data": chart,
                        "task": "chart_interpretation_for_export",
                        "interpretation_level": "comprehensive",
                        "format": format,
                        "required_sections": [
                            "personality_traits",
                            "life_purpose",
                            "career_indications",
                            "relationship_patterns",
                            "life_challenges",
                            "planetary_influences",
                            "spiritual_path"
                        ]
                    }

                    # Get interpretation from OpenAI
                    interpretation_response = await openai_service.generate_completion(
                        prompt=json.dumps(interpretation_request),
                        task_type="astrological_interpretation",
                        max_tokens=1500
                    )

                    if interpretation_response:
                        # Parse the response
                        try:
                            if isinstance(interpretation_response, str):
                                interpretation = json.loads(interpretation_response)
                            else:
                                interpretation = interpretation_response
                        except json.JSONDecodeError:
                            # If not valid JSON, use as text with safe truncation
                            interpretation = {
                                "overall_summary": safe_truncate(interpretation_response)
                            }

                        # Add interpretation to the chart data
                        chart["interpretation"] = interpretation

                        # Success, break the loop
                        break
                except Exception as interp_error:
                    retry_count += 1
                    logger.warning(f"OpenAI interpretation error (attempt {retry_count}/{max_retries}): {interp_error}")

                    # Exponential backoff
                    await asyncio.sleep(1 * retry_count)

                    if retry_count >= max_retries:
                        logger.warning(f"Failed to generate interpretation after {max_retries} attempts")
                        chart["interpretation"] = {
                            "overall_summary": "Interpretation could not be generated due to a service error."
                        }

        # Define export options
        export_options = {
            "include_interpretation": include_interpretation,
            "include_aspects": True,
            "include_3d": is_3d,
            "paper_size": paper_size
        }

        # Generate export
        logger.info(f"Generating chart export in {format} format for chart {chart_id}")

        # Generate unique export ID
        export_id = f"export_{uuid.uuid4().hex[:8]}"

        # Create output directory
        chart_output_dir = chart_service.chart_output_dir or "exports"
        export_dir = os.path.join(chart_output_dir, "exports")
        os.makedirs(export_dir, exist_ok=True)

        # Determine file extension and output path
        file_ext = format if format != "jpeg" else "jpg"
        output_path = os.path.join(export_dir, f"{chart_id}_{export_id}.{file_ext}")

        # Generate the export file based on format with enhanced error handling
        generated_path = None

        try:
            if format.lower() == "pdf":
                # Import PDF generator directly to ensure proper integration
                from ai_service.utils.chart_visualizer import save_chart_as_pdf

                # Generate PDF with chart data and interpretation
                generated_path = save_chart_as_pdf(
                    chart_data=chart,
                    output_path=output_path,
                    include_interpretation=export_options["include_interpretation"],
                    paper_size=export_options["paper_size"]
                )
            else:
                # Use chart visualizer for image formats
                from ai_service.utils.chart_visualizer import generate_chart_image

                # Generate image with chart data
                generated_path = generate_chart_image(
                    chart_data=chart,
                    output_path=output_path,
                    include_3d=export_options["include_3d"]
                )

            # Verify file exists and is not empty
            if not generated_path or not os.path.exists(generated_path):
                raise ValueError("Export generation failed: output file not created")

            if os.path.getsize(generated_path) == 0:
                raise ValueError("Export generation failed: output file is empty")

        except Exception as e:
            logger.error(f"Error generating export file: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500,
                              detail=f"Export generation failed: {str(e)}")

        # If output path is different from generated path, update it
        if generated_path != output_path:
            output_path = generated_path

        logger.info(f"Successfully generated chart export at {output_path}")

        # Verify file permissions and readability
        try:
            with open(output_path, 'rb') as test_file:
                # Read a few bytes to verify permissions
                test_file.read(10)
        except PermissionError:
            logger.error(f"Permission denied accessing export file: {output_path}")
            raise HTTPException(
                status_code=500,
                detail="Export file has incorrect permissions"
            )
        except IOError as io_error:
            logger.error(f"Error accessing export file: {output_path} - {io_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Cannot read export file: {str(io_error)}"
            )

        # Create download URL
        download_url = f"/api/v1/charts/download/{export_id}?format={format}"

        # Create expiration timestamp (7 days from now)
        expiration = datetime.now() + timedelta(days=7)
        expires_at = expiration.isoformat()

        # Create export metadata
        export_data = {
            "export_id": export_id,
            "chart_id": chart_id,
            "file_path": output_path,
            "format": format,
            "download_url": download_url,
            "content_type": chart_service._get_content_type(format),
            "file_size": os.path.getsize(output_path),
            "generated_at": datetime.now().isoformat(),
            "expires_at": expires_at,
            "include_interpretation": export_options["include_interpretation"],
            "include_aspects": export_options["include_aspects"],
            "include_3d": export_options["include_3d"],
            "paper_size": export_options["paper_size"]
        }

        # Store export metadata in database
        async def store_export(export_id: str, export_data: Dict[str, Any]) -> None:
            """Store export metadata in file system."""
            export_dir = os.path.join(chart_output_dir, "exports_metadata")
            os.makedirs(export_dir, exist_ok=True)

            export_path = os.path.join(export_dir, f"{export_id}.json")
            with open(export_path, 'w') as f:
                json.dump(export_data, f, default=str)

            logger.info(f"Stored export metadata for {export_id}")

        try:
            await store_export(export_id, export_data)
        except Exception as db_error:
            logger.warning(f"Non-critical error storing export metadata: {db_error}")
            # If metadata storage fails, we still have the file, so we can continue

        # Return export details
        return {
            "status": "success",
            "export_id": export_id,
            "chart_id": chart_id,
            "format": format,
            "download_url": download_url,
            "includes_interpretation": export_options["include_interpretation"],
            "file_size": os.path.getsize(output_path),
            "expires_at": expires_at
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chart export: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chart export failed: {str(e)}")

@router.get("/download/{export_id}", response_class=Response)
async def download_chart_export(
    export_id: str,
    format: str = Query(None, description="Export format (optional)"),
    background_tasks: BackgroundTasks = Depends()
):
    """
    Download a previously generated chart export.

    This endpoint returns the actual file for download after verifying its existence.
    It also tracks download statistics.
    """
    try:
        # Retrieve export metadata with retries
        export_data = None
        max_retries = 3

        for attempt in range(max_retries):
            try:
                export_data = await get_export(export_id)
                if export_data:
                    break
                logger.warning(f"Export data not found on attempt {attempt+1}, retrying...")
                await asyncio.sleep(0.5 * (attempt + 1))
            except Exception as e:
                logger.warning(f"Error retrieving export data on attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))

        if not export_data:
            raise HTTPException(status_code=404, detail=f"Export with ID {export_id} not found")

        # Get file path from export data
        file_path = export_data.get("file_path")
        if not file_path:
            raise HTTPException(status_code=404, detail="Export file path not found in metadata")

        # Verify file exists and is readable
        if not os.path.exists(file_path):
            logger.error(f"Export file not found at {file_path}")
            raise HTTPException(status_code=404, detail=f"Export file not found")

        # Verify file is not empty
        if os.path.getsize(file_path) == 0:
            logger.error(f"Export file is empty: {file_path}")
            raise HTTPException(status_code=404, detail="Export file is empty")

        # Test file permissions
        try:
            with open(file_path, 'rb') as test_file:
                # Read a few bytes to verify permissions
                test_file.read(10)
        except PermissionError:
            logger.error(f"Permission denied accessing export file: {file_path}")
            raise HTTPException(
                status_code=403, detail="Permission denied accessing export file")
        except Exception as e:
            logger.error(f"Error accessing export file: {e}")
            raise HTTPException(status_code=500, detail=f"Error accessing export file: {str(e)}")

        # Get content type
        content_type = export_data.get("content_type")
        if not content_type:
            # Determine content type from format
            export_format = export_data.get("format", "").lower() or (format.lower() if format else "")
            if export_format == "pdf":
                content_type = "application/pdf"
            elif export_format in ["png"]:
                content_type = "image/png"
            elif export_format in ["jpg", "jpeg"]:
                content_type = "image/jpeg"
            elif export_format == "svg":
                content_type = "image/svg+xml"
            else:
                content_type = "application/octet-stream"

        # Get filename from file path
        filename = os.path.basename(file_path)

        # Check if export has expired
        expires_at = export_data.get("expires_at")
        if expires_at:
            try:
                expiration_date = datetime.fromisoformat(expires_at)
                if datetime.now() > expiration_date:
                    raise HTTPException(status_code=410, detail="Export has expired and is no longer available")
            except (ValueError, TypeError):
                # If expiration can't be parsed, assume it hasn't expired
                pass

        # Update download statistics in background
        # Define a local function to update stats to avoid chart_repository undefined error
        async def update_stats(export_id: str):
            try:
                # Update the download count in the export metadata
                export_data["download_count"] = export_data.get("download_count", 0) + 1
                export_data["last_downloaded"] = datetime.now().isoformat()

                # Store the updated metadata
                chart_service = get_chart_service()
                chart_output_dir = chart_service.chart_output_dir or "exports"
                export_dir = os.path.join(chart_output_dir, "exports_metadata")
                export_path = os.path.join(export_dir, f"{export_id}.json")

                with open(export_path, 'w') as f:
                    json.dump(export_data, f, default=str)

                logger.info(f"Updated download count for export {export_id}")
            except Exception as e:
                logger.error(f"Error updating download stats: {e}")
                # Don't re-raise, as this is a background task

        background_tasks.add_task(update_stats, export_id)

        # Return the file with additional headers
        return FileResponse(
            path=file_path,
            media_type=content_type,
            filename=filename,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"",
                "X-Export-ID": export_id,
                "X-Generated-Date": export_data.get("generated_at", ""),
                "Cache-Control": "private, max-age=3600"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading export: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@router.get("/compare", response_model=Dict[str, Any])
async def compare_charts(
    chart1_id: str = Query(..., description="First chart ID for comparison"),
    chart2_id: str = Query(..., description="Second chart ID for comparison"),
    interpretation_level: str = Query("detailed", description="Level of astrological interpretation: basic, detailed, or comprehensive"),
    include_visualization: bool = Query(True, description="Whether to include chart visualization in response"),
    is_3d: bool = Query(False, description="Whether to include 3D visualization in response")
):
    """
    Compare two astrological charts with detailed analysis and visualization.

    This endpoint provides in-depth astrological analysis and visual comparison
    between two charts. It returns the key differences, planetary shifts, house changes,
    aspect modifications, and other astrologically significant patterns.

    Args:
        chart1_id: ID of the first chart for comparison
        chart2_id: ID of the second chart for comparison
        interpretation_level: How detailed the astrological interpretation should be
        include_visualization: Whether to include chart visualization in the response
        is_3d: Whether to include 3D visualization in the response

    Returns:
        Detailed comparison data with visualization if requested
    """
    try:
        # Validate parameters
        if not chart1_id or not chart2_id:
            raise HTTPException(status_code=400, detail="Both chart IDs are required")

        if chart1_id == chart2_id:
            raise HTTPException(status_code=400, detail="Cannot compare a chart with itself")

        # Get service instances
        chart_service = get_chart_service()
        chart_repository = await get_chart_repository()
        openai_service = get_openai_service()

        # Retrieve both charts with proper error handling
        try:
            chart1 = await chart_repository.get_chart(chart1_id)
            if not chart1:
                raise HTTPException(status_code=404, detail=f"Chart with ID {chart1_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving chart1: {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving first chart: {str(e)}")

        try:
            chart2 = await chart_repository.get_chart(chart2_id)
            if not chart2:
                raise HTTPException(status_code=404, detail=f"Chart with ID {chart2_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving chart2: {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving second chart: {str(e)}")

        # Generate a comparison ID
        comparison_id = f"comp_{uuid.uuid4().hex[:8]}"

        # Perform detailed chart comparison based on _generate_comparison_data method in ChartService
        logger.info(f"Generating comparison between charts {chart1_id} and {chart2_id}")

        try:
            comparison_data = chart_service._generate_comparison_data(chart1, chart2)
        except Exception as e:
            logger.error(f"Error generating comparison data: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500,
                                detail=f"Error generating chart comparison: {str(e)}")

        # Add comparison metadata
        comparison_data["comparison_id"] = comparison_id
        comparison_data["chart1_id"] = chart1_id
        comparison_data["chart2_id"] = chart2_id
        comparison_data["generated_at"] = datetime.now().isoformat()
        comparison_data["interpretation_level"] = interpretation_level

        # Add interpretation based on level with enhanced error handling
        if interpretation_level.lower() == "basic":
            # Basic analysis is already included in comparison_data
            pass

        elif interpretation_level.lower() == "detailed":
            # Add more detailed analysis to the comparison data
            try:
                vd_analysis = chart_service._perform_vedic_comparison_analysis(chart1, chart2)
                comparison_data["vedic_analysis"] = vd_analysis

                # Add timing implications
                timing = chart_service._analyze_timing_implications(comparison_data)
                comparison_data["timing_implications"] = timing
            except Exception as e:
                logger.warning(f"Non-critical error in detailed analysis: {e}")
                comparison_data["analysis_warning"] = f"Some detailed analysis could not be generated: {str(e)}"

        elif interpretation_level.lower() == "comprehensive":
            # Add comprehensive analysis
            try:
                vd_analysis = chart_service._perform_vedic_comparison_analysis(chart1, chart2)
                comparison_data["vedic_analysis"] = vd_analysis

                # Add timing implications
                timing = chart_service._analyze_timing_implications(comparison_data)
                comparison_data["timing_implications"] = timing

                # Add harmonic relationships
                harmonics = _analyze_harmonic_relationships(chart1, chart2)
                comparison_data["harmonic_relationships"] = harmonics

                # Generate rich astrological interpretation using OpenAI with improved error handling
                interpretation = None
                max_retries = 3
                retry_count = 0

                while retry_count < max_retries:
                    try:
                        # Construct detailed prompt for OpenAI
                        prompt = {
                            "task": "interpret_chart_comparison",
                            "interpretation_level": "comprehensive",
                            "comparison_data": comparison_data,
                            "chart1": {
                                "ascendant": chart1.get("ascendant", {}),
                                "planets": chart1.get("planets", []),
                                "houses": chart1.get("houses", [])
                            },
                            "chart2": {
                                "ascendant": chart2.get("ascendant", {}),
                                "planets": chart2.get("planets", []),
                                "houses": chart2.get("houses", [])
                            },
                            "required_analysis_sections": [
                                "overall_synastry",
                                "planetary_aspect_significance",
                                "house_overlay_impacts",
                                "ascendant_relationship",
                                "predictive_insights",
                                "spiritual_compatibility"
                            ]
                        }

                        interpretation = await openai_service.generate_completion(
                            prompt=json.dumps(prompt),
                            task_type="astrological_interpretation",
                            max_tokens=1500
                        )

                        # Successful response, break the loop
                        break

                    except Exception as e:
                        retry_count += 1
                        logger.warning(f"OpenAI interpretation error (attempt {retry_count}/{max_retries}): {e}")
                        await asyncio.sleep(1 * retry_count)  # Exponential backoff

                        if retry_count >= max_retries:
                            logger.error(f"Failed to get OpenAI interpretation after {max_retries} attempts")
                            comparison_data["interpretation_error"] = f"Could not generate AI interpretation: {str(e)}"

                # Process interpretation if successful
                if interpretation:
                    if isinstance(interpretation, str):
                        try:
                            interpretation = json.loads(interpretation)
                        except json.JSONDecodeError:
                            # Create a valid dictionary with truncated text
                            interpretation = {
                                "overall_summary": safe_truncate(interpretation)
                            }

                    comparison_data["interpretation"] = interpretation
                else:
                    # Add a placeholder if interpretation failed
                    comparison_data["interpretation"] = {
                        "overall_summary": "Detailed interpretation could not be generated. Please see the comparison data for details."
                    }

            except Exception as interp_error:
                logger.warning(f"Error generating comprehensive interpretation: {interp_error}")
                # Add placeholder interpretation
                comparison_data["interpretation"] = {
                    "overall_summary": "Detailed interpretation could not be generated. Please see the comparison data for details.",
                    "error": str(interp_error)
                }

        # Generate visualization if requested
        if include_visualization:
            try:
                # Create temporary directory for visualization files
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Generate visualization paths
                    viz_filename = f"comparison_{comparison_id}.png"
                    viz_path = os.path.join(temp_dir, viz_filename)
                    viz3d_filename = f"comparison_3d_{comparison_id}.png"
                    viz3d_path = os.path.join(temp_dir, viz3d_filename)

                    # Create permanent storage location for the visualizations
                    chart_output_dir = chart_service.chart_output_dir or "charts"
                    comp_viz_dir = os.path.join(chart_output_dir, "comparisons")
                    os.makedirs(comp_viz_dir, exist_ok=True)

                    # Permanent paths for the visualizations
                    permanent_path = os.path.join(comp_viz_dir, viz_filename)
                    permanent_3d_path = os.path.join(comp_viz_dir, viz3d_filename)

                    # Initialize visualization data dictionary
                    comparison_data["visualizations"] = {}

                    # Generate visualizations with error handling
                    viz_generated = False
                    viz3d_generated = False

                    # Generate 2D comparison chart
                    try:
                        from ai_service.utils.chart_visualizer import generate_comparison_chart
                        generate_comparison_chart(chart1, chart2, viz_path)
                        viz_generated = os.path.exists(viz_path) and os.path.getsize(viz_path) > 0
                    except Exception as viz_error:
                        logger.warning(f"Error generating 2D comparison visualization: {viz_error}")
                        comparison_data["visualizations"]["2d_error"] = str(viz_error)

                    # Generate 3D comparison chart if requested
                    if is_3d:
                        try:
                            from ai_service.utils.chart_visualizer import generate_3d_comparison
                            generate_3d_comparison(chart1, chart2, viz3d_path)
                            viz3d_generated = os.path.exists(viz3d_path) and os.path.getsize(viz3d_path) > 0
                        except Exception as viz3d_error:
                            logger.warning(f"Error generating 3D comparison visualization: {viz3d_error}")
                            comparison_data["visualizations"]["3d_error"] = str(viz3d_error)

                    # Add 2D visualization if successful
                    if viz_generated:
                        try:
                            # Read file and convert to base64
                            with open(viz_path, "rb") as img_file:
                                img_data = base64.b64encode(img_file.read()).decode("utf-8")

                            # Add 2D visualization data to comparison
                            comparison_data["visualizations"]["2d"] = {
                                "format": "png",
                                "content_type": "image/png",
                                "data": f"data:image/png;base64,{img_data}",
                                "filename": viz_filename
                            }

                            # Copy to permanent storage
                            try:
                                import shutil
                                shutil.copy2(viz_path, permanent_path)

                                # Verify file was copied successfully
                                if os.path.exists(permanent_path) and os.path.getsize(permanent_path) > 0:
                                    comparison_data["visualizations"]["2d"]["permalink"] = f"/api/v1/charts/comparison/{comparison_id}/visualization"
                                else:
                                    logger.warning(f"2D visualization file verification failed after copy")
                            except Exception as copy_error:
                                logger.warning(f"Error copying 2D visualization to permanent storage: {copy_error}")
                        except Exception as viz_process_error:
                            logger.warning(f"Error processing 2D visualization: {viz_process_error}")

                    # Add 3D visualization if successful
                    if viz3d_generated:
                        try:
                            # Read file and convert to base64
                            with open(viz3d_path, "rb") as img_file:
                                img_data = base64.b64encode(img_file.read()).decode("utf-8")

                            # Add 3D visualization data to comparison
                            comparison_data["visualizations"]["3d"] = {
                                "format": "png",
                                "content_type": "image/png",
                                "data": f"data:image/png;base64,{img_data}",
                                "filename": viz3d_filename
                            }

                            # Copy to permanent storage
                            try:
                                import shutil
                                shutil.copy2(viz3d_path, permanent_3d_path)

                                # Verify file was copied successfully
                                if os.path.exists(permanent_3d_path) and os.path.getsize(permanent_3d_path) > 0:
                                    comparison_data["visualizations"]["3d"]["permalink"] = f"/api/v1/charts/comparison/{comparison_id}/visualization/3d"
                                else:
                                    logger.warning(f"3D visualization file verification failed after copy")
                            except Exception as copy_error:
                                logger.warning(f"Error copying 3D visualization to permanent storage: {copy_error}")
                        except Exception as viz3d_process_error:
                            logger.warning(f"Error processing 3D visualization: {viz3d_process_error}")
            except Exception as viz_error:
                logger.warning(f"Error generating comparison visualization: {viz_error}")
                comparison_data["visualization_error"] = str(viz_error)

        # Store the comparison data
        try:
            await chart_repository.store_comparison(comparison_id, comparison_data)
        except Exception as store_error:
            logger.warning(f"Non-critical error storing comparison data: {store_error}")

        return comparison_data

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error comparing charts: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chart comparison failed: {str(e)}")

@router.get("/comparison/{comparison_id}/visualization", response_class=FileResponse)
async def get_comparison_visualization(
    comparison_id: str = Path(..., description="Comparison ID"),
    dimension: str = Query("2d", description="Visualization dimension (2d or 3d)"),
    background_tasks: BackgroundTasks = Depends()
):
    """
    Get the visualization image for a chart comparison.

    This endpoint returns the comparison visualization image in either 2D or 3D format.

    Args:
        comparison_id: The unique ID of the comparison
        dimension: The visualization dimension to retrieve (2d or 3d)

    Returns:
        The visualization image file
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Determine filename based on dimension
        is_3d = dimension.lower() == "3d"
        viz_filename = f"comparison_{'3d_' if is_3d else ''}{comparison_id}.png"

        # Construct the expected file path
        chart_output_dir = chart_service.chart_output_dir or "charts"
        comp_viz_dir = os.path.join(chart_output_dir, "comparisons")
        viz_path = os.path.join(comp_viz_dir, viz_filename)

        # Verify file exists
        if not os.path.exists(viz_path):
            # If file doesn't exist, check if we need to regenerate it
            comparison = await get_comparison(comparison_id)

            if not comparison:
                raise HTTPException(status_code=404, detail=f"Comparison with ID {comparison_id} not found")

            # Get chart IDs
            chart1_id = comparison.get("chart1_id")
            chart2_id = comparison.get("chart2_id")

            if not chart1_id or not chart2_id:
                raise HTTPException(status_code=400, detail="Comparison data missing chart IDs")

            # Get chart repository
            chart_repository = await get_chart_repository()

            # Get charts
            chart1 = await chart_repository.get_chart(chart1_id)
            chart2 = await chart_repository.get_chart(chart2_id)

            if not chart1 or not chart2:
                raise HTTPException(status_code=404, detail="One or both charts not found")

            # Create comparisons directory if it doesn't exist
            os.makedirs(comp_viz_dir, exist_ok=True)

            # Import visualization functions
            if is_3d:
                from ai_service.utils.chart_visualizer import generate_3d_comparison
                generate_3d_comparison(chart1, chart2, viz_path)
            else:
                from ai_service.utils.chart_visualizer import generate_comparison_chart
                generate_comparison_chart(chart1, chart2, viz_path)

            # Verify file was created
            if not os.path.exists(viz_path):
                raise HTTPException(status_code=500, detail=f"Failed to generate {dimension} comparison visualization")

        # Return the visualization file
        return FileResponse(
            path=viz_path,
            media_type="image/png",
            filename=viz_filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving comparison visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Visualization retrieval failed: {str(e)}")

# Add a dedicated endpoint for 3D visualizations for backward compatibility
@router.get("/comparison/{comparison_id}/visualization/3d", response_class=FileResponse)
async def get_comparison_3d_visualization(
    comparison_id: str = Path(..., description="Comparison ID"),
    background_tasks: BackgroundTasks = Depends()
):
    """
    Get the 3D visualization image for a chart comparison.

    This endpoint returns the 3D comparison visualization image.
    """
    return await get_comparison_visualization(comparison_id, "3d", background_tasks)

async def _update_download_stats(chart_repository, export_id: str) -> None:
    """Update download statistics for an export."""
    try:
        # Get current export details
        export_details = await chart_repository.get_export(export_id)
        if not export_details:
            logger.warning(f"Could not find export {export_id} to update stats")
            return

        # Increment download count
        current_count = export_details.get("download_count", 0)
        new_count = current_count + 1

        # Update stats
        export_details["download_count"] = new_count
        export_details["last_downloaded"] = datetime.now().isoformat()

        # Save updated export details
        await chart_repository.update_export(export_id, export_details)
        logger.info(f"Updated download count for export {export_id} to {new_count}")
    except Exception as e:
        logger.error(f"Error updating download stats: {e}")
        # Don't re-raise, as this is a background task

async def get_export(export_id: str) -> Optional[Dict[str, Any]]:
    """Get export metadata from file system."""
    chart_service = get_chart_service()
    chart_output_dir = chart_service.chart_output_dir or "exports"

    export_dir = os.path.join(chart_output_dir, "exports_metadata")
    export_path = os.path.join(export_dir, f"{export_id}.json")

    if not os.path.exists(export_path):
        logger.warning(f"Export metadata not found for {export_id}")
        return None

    try:
        with open(export_path, 'r') as f:
            export_data = json.load(f)
        return export_data
    except Exception as e:
        logger.error(f"Error loading export metadata: {e}")
        return None

async def get_comparison(comparison_id: str) -> Optional[Dict[str, Any]]:
    """Get comparison data from file system."""
    chart_service = get_chart_service()
    chart_output_dir = chart_service.chart_output_dir or "charts"

    comp_dir = os.path.join(chart_output_dir, "comparisons_metadata")
    comp_path = os.path.join(comp_dir, f"{comparison_id}.json")

    if not os.path.exists(comp_path):
        logger.warning(f"Comparison metadata not found for {comparison_id}")
        return None

    try:
        with open(comp_path, 'r') as f:
            comparison_data = json.load(f)
        return comparison_data
    except Exception as e:
        logger.error(f"Error loading comparison metadata: {e}")
        return None

def _analyze_harmonic_relationships(chart1, chart2):
    """
    Analyze harmonic relationships between two charts.

    This is a helper function that should be a method in ChartService.
    Implemented directly to fix linter errors.

    Args:
        chart1: First chart data
        chart2: Second chart data

    Returns:
        Dictionary of harmonic relationships
    """
    # Simplified implementation to resolve linter error
    harmonic_relationships = {
        "harmonic_1": {
            "description": "Identity",
            "significance": "high",
            "differences": []
        },
        "harmonic_2": {
            "description": "Polarity",
            "significance": "medium",
            "differences": []
        },
        "harmonic_3": {
            "description": "Trinity",
            "significance": "medium",
            "differences": []
        },
        "harmonic_9": {
            "description": "Spiritual",
            "significance": "medium",
            "differences": []
        }
    }

    # Get planets from both charts
    planets1 = chart1.get("planets", [])
    planets2 = chart2.get("planets", [])

    # Analyze major harmonic patterns
    for harm_idx, (harmonic_key, harmonic_data) in enumerate([
        ("harmonic_1", {"divisor": 1, "significance": "high"}),
        ("harmonic_2", {"divisor": 2, "significance": "medium"}),
        ("harmonic_3", {"divisor": 3, "significance": "medium"}),
        ("harmonic_9", {"divisor": 9, "significance": "medium"})
    ]):
        differences = []

        # Compare planets in this harmonic
        for p1 in planets1:
            planet_name = p1.get("name", "")
            p1_long = p1.get("longitude", 0)

            # Find matching planet in chart2
            for p2 in planets2:
                if p2.get("name") == planet_name:
                    p2_long = p2.get("longitude", 0)

                    # Calculate harmonic position
                    h1_pos = (p1_long * harmonic_data["divisor"]) % 360
                    h2_pos = (p2_long * harmonic_data["divisor"]) % 360

                    # Calculate difference
                    diff = min(abs(h1_pos - h2_pos), 360 - abs(h1_pos - h2_pos))

                    if diff > 5:  # Only report significant differences
                        differences.append({
                            "planet": planet_name,
                            "difference": round(diff, 2),
                            "significance": "high" if diff > 10 else "medium"
                        })

        harmonic_relationships[harmonic_key]["differences"] = differences

    return harmonic_relationships

# Add a helper function to safely truncate text
def safe_truncate(text: Any, max_length: int = 1000) -> str:
    """Safely truncate text to a maximum length."""
    # Convert to string first
    text_str = str(text)
    return text_str[:max_length] if len(text_str) > max_length else text_str
