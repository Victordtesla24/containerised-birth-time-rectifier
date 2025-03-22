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

from ai_service.services import get_chart_service
from ai_service.services.chart_service import create_chart_service
from ai_service.api.services.openai import get_openai_service
from ai_service.core.rectification.main import comprehensive_rectification
from ai_service.utils.chart_visualizer import generate_comparison_chart, generate_chart_image
from ai_service.database.repositories import ChartRepository
from ai_service.core.config import settings

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
    include_interpretation: bool = Body(True, description="Include astrological interpretation in export"),
    paper_size: str = Body("letter", description="Paper size for PDF (letter, a4, legal)")
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
        chart = await chart_service.get_chart(chart_id)
        if not chart:
            raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")

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

        # Get interpretation if requested
        interpretation = None
        if include_interpretation:
            logger.info(f"Generating interpretation for chart {chart_id} export")
            try:
                openai_service = get_openai_service()

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

                if interpretation_response and "content" in interpretation_response:
                    try:
                        content = interpretation_response["content"]

                        # Try to parse as JSON first
                        try:
                            interpretation = json.loads(content)
                        except json.JSONDecodeError:
                            # If not valid JSON, extract structured information from text
                            interpretation = {
                                "overall_summary": "",
                                "key_planetary_changes": [],
                                "house_cusp_shifts": [],
                                "astrological_implications": [],
                                "life_area_effects": {}
                            }

                            # Extract sections using regex patterns - use raw strings
                            summary_match = re.search(r'(?:overall_summary|summary)[\s:"]*([^"]*?)(?:"|$|,\s*")', content, re.IGNORECASE | re.DOTALL)
                            if summary_match:
                                interpretation["overall_summary"] = summary_match.group(1).strip()

                            # Extract other sections as needed
                            implications_pattern = r'(?:implications|astrological_implications)[\s:"]*([^"]*?)(?:"|$|,\s*")'
                            implications_match = re.search(implications_pattern, content, re.IGNORECASE | re.DOTALL)
                            if implications_match:
                                interpretation["astrological_implications"] = implications_match.group(1).strip()

                            # Extract life area effects
                            life_areas = ["career", "relationships", "health", "finances", "spirituality", "family"]
                            for area in life_areas:
                                area_pattern = r'(?:' + area + r')[\s:"]*([^"]*?)(?:"|$|,\s*")'
                                area_match = re.search(area_pattern, content, re.IGNORECASE | re.DOTALL)
                                if area_match:
                                    if "life_area_effects" not in interpretation:
                                        interpretation["life_area_effects"] = {}
                                    interpretation["life_area_effects"][area] = area_match.group(1).strip()

                        logger.info("Successfully parsed interpretation data")
                    except Exception as parsing_error:
                        logger.error(f"Error processing interpretation response: {parsing_error}")
                        interpretation = {
                            "overall_summary": "Failed to parse detailed interpretation. Please see the differences data for comparison information."
                        }

            except Exception as interp_error:
                logger.error(f"Error generating interpretation: {interp_error}")
                logger.info("Continuing with export without interpretation")
                interpretation = None

        # Add export options
        export_options = {
            "include_interpretation": include_interpretation and interpretation is not None,
            "paper_size": paper_size if format.lower() == "pdf" else None,
            "include_aspects": True,  # Always include aspects in exports
            "include_chart_wheel": True,  # Always include chart wheel in exports
        }

        # Generate export
        logger.info(f"Generating chart export in {format} format for chart {chart_id}")
        export_result = await chart_service.export_chart(
            chart_id=chart_id,
            format=format
        )

        # Verify file exists after export
        file_path = export_result.get("file_path")
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=500,
                detail="Export generated but file is missing. Please try again."
            )

        logger.info(f"Successfully generated chart export at {file_path}")

        # Store export download stats
        try:
            # Create or update export stats
            export_stats = {
                "chart_id": chart_id,
                "file_path": file_path,
                "format": format,
                "download_url": export_result["download_url"],
                "generated_at": datetime.now().isoformat(),
                "expires_at": export_result.get("expires_at", (datetime.now() + timedelta(days=7)).isoformat())
            }

            # Store the export stats using the store_export method
            await chart_repository.store_export(export_result["export_id"], export_stats)
        except Exception as stats_error:
            logger.warning(f"Non-critical error storing export stats: {stats_error}")

        # Update download count in background
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            _update_download_stats,
            chart_repository,
            export_result["export_id"]
        )

        # Return export details
        return {
            "status": "success",
            "export_id": export_result["export_id"],
            "chart_id": chart_id,
            "format": format,
            "download_url": export_result["download_url"],
            "includes_interpretation": export_options["include_interpretation"],
            "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            "expires_at": export_result.get("expires_at", (datetime.now() + timedelta(days=7)).isoformat())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chart export: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chart export failed: {str(e)}")

@router.get("/download/{export_id}/{format}")
async def download_chart_export(
    export_id: str,
    format: str,
    background_tasks: BackgroundTasks
):
    """
    Download a previously generated chart export.

    This endpoint returns the actual file for download after verifying its existence.
    """
    chart_repository = await get_chart_repository()

    try:
        # Get export details from chart repository
        export_details = await chart_repository.get_export(export_id)

        if not export_details:
            raise HTTPException(status_code=404, detail=f"Export {export_id} not found")

        # Check if export has expired
        expires_at = datetime.fromisoformat(export_details.get("expires_at", "2099-12-31T00:00:00"))
        if datetime.now() > expires_at:
            raise HTTPException(status_code=410, detail="Export has expired")

        # Get file path
        file_path = export_details.get("file_path")

        # Verify file exists and is accessible
        if not file_path:
            raise HTTPException(status_code=404, detail="Export file path not found")

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Export file not found on server")

        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="Export path exists but is not a file")

        try:
            # Check file is readable
            with open(file_path, 'rb') as test_file:
                test_file.read(1)
        except Exception as file_error:
            logger.error(f"File exists but cannot be read: {file_error}")
            raise HTTPException(status_code=500, detail="Export file cannot be read")

        # Determine content type
        content_types = {
            "pdf": "application/pdf",
            "png": "image/png",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg"
        }

        content_type = content_types.get(format.lower(), "application/octet-stream")

        # Log download
        logger.info(f"Export {export_id} downloading in {format} format")

        # Update download count in background
        background_tasks.add_task(
            _update_download_stats,
            chart_repository,
            export_id
        )

        # Create a meaningful filename for the downloaded file
        chart_id = export_details.get("chart_id", "chart")
        download_filename = f"astrological_chart_{chart_id}_{datetime.now().strftime('%Y%m%d')}.{format}"

        # Return file
        return FileResponse(
            path=file_path,
            filename=download_filename,
            media_type=content_type,
            background=background_tasks
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chart download: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chart download failed: {str(e)}")

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

@router.get("/compare", response_model=Dict[str, Any])
async def compare_charts(
    chart1_id: str = Query(..., description="First chart ID for comparison"),
    chart2_id: str = Query(..., description="Second chart ID for comparison"),
    interpretation_level: str = Query("detailed", description="Level of astrological interpretation: basic, detailed, or comprehensive"),
    include_visualization: bool = Query(True, description="Whether to include chart visualization in response")
):
    """
    Compare two astrological charts with deep astrological interpretation.

    This endpoint analyzes the differences between two charts and provides
    detailed astrological interpretation of the differences, including
    visualization if requested.
    """
    chart_service = get_chart_service()
    openai_service = get_openai_service()
    chart_repository = await get_chart_repository()

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

        logger.info(f"Comparing charts {chart1_id} and {chart2_id} with interpretation level: {interpretation_level}")

        # Use chart service for comprehensive comparison
        comparison_result = await chart_service.compare_charts(
            chart1_id=chart1_id,
            chart2_id=chart2_id,
            comparison_type="comprehensive"
        )

        if not comparison_result:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate chart comparison using chart service"
            )

        # Extract differences from the comparison result
        differences = comparison_result.get("differences", {})

        # Enhanced analysis: Use OpenAI for deep astrological interpretation
        interpretation_request = {
            "chart1": {
                "id": chart1_id,
                "birth_details": chart1_details,
                "ascendant": chart1.get("ascendant", {}),
                "planets": chart1.get("planets", []),
                "houses": chart1.get("houses", [])
            },
            "chart2": {
                "id": chart2_id,
                "birth_details": chart2_details,
                "ascendant": chart2.get("ascendant", {}),
                "planets": chart2.get("planets", []),
                "houses": chart2.get("houses", [])
            },
            "differences": differences,
            "interpretation_level": interpretation_level,
            "task": "chart_comparison_interpretation",
            "required_sections": [
                "overall_summary",
                "key_planetary_changes",
                "house_cusp_shifts",
                "ascendant_changes",
                "astrological_implications",
                "life_area_effects",
                "remedial_measures"
            ],
            "astrological_systems": ["western", "vedic"]
        }

        # Get interpretation from OpenAI
        interpretation_response = await openai_service.generate_completion(
            prompt=json.dumps(interpretation_request),
            task_type="astrological_interpretation",
            max_tokens=1500  # Increased for more detailed interpretation
        )

        if not interpretation_response or "content" not in interpretation_response:
            logger.error("Failed to get interpretation from OpenAI")
            raise HTTPException(status_code=500, detail="Failed to generate astrological interpretation")

        # Parse the interpretation results
        try:
            interpreted_content = interpretation_response["content"]

            # Try to parse as JSON first
            try:
                interpretation = json.loads(interpreted_content)
            except json.JSONDecodeError:
                # If not valid JSON, extract structured information from text
                interpretation = {
                    "overall_summary": "",
                    "key_planetary_changes": [],
                    "house_cusp_shifts": [],
                    "astrological_implications": [],
                    "life_area_effects": {}
                }

                # Extract sections using regex patterns - use raw strings
                summary_match = re.search(r'(?:overall_summary|summary)[\s:"]*([^"]*?)(?:"|$|,\s*")', interpreted_content, re.IGNORECASE | re.DOTALL)
                if summary_match:
                    interpretation["overall_summary"] = summary_match.group(1).strip()

                # Extract other sections as needed
                implications_pattern = r'(?:implications|astrological_implications)[\s:"]*([^"]*?)(?:"|$|,\s*")'
                implications_match = re.search(implications_pattern, interpreted_content, re.IGNORECASE | re.DOTALL)
                if implications_match:
                    interpretation["astrological_implications"] = implications_match.group(1).strip()

                # Extract life area effects
                life_areas = ["career", "relationships", "health", "finances", "spirituality", "family"]
                for area in life_areas:
                    area_pattern = r'(?:' + area + r')[\s:"]*([^"]*?)(?:"|$|,\s*")'
                    area_match = re.search(area_pattern, interpreted_content, re.IGNORECASE | re.DOTALL)
                    if area_match:
                        if "life_area_effects" not in interpretation:
                            interpretation["life_area_effects"] = {}
                        interpretation["life_area_effects"][area] = area_match.group(1).strip()

            logger.info("Successfully parsed interpretation data")
        except Exception as parsing_error:
            logger.error(f"Error processing interpretation response: {parsing_error}")
            interpretation = {
                "overall_summary": "Failed to parse detailed interpretation. Please see the differences data for comparison information."
            }

        # Generate comparison ID
        comparison_id = f"comp_{uuid.uuid4().hex[:8]}"

        # Generate comparison visualization if requested
        visualization_data = None
        visualization_url = None

        if include_visualization:
            try:
                # Import chart visualization utilities
                from ai_service.utils.chart_visualizer import generate_comparison_chart

                # Create directory for visualizations
                visualization_dir = os.path.join(settings.MEDIA_ROOT, "visualizations")
                os.makedirs(visualization_dir, exist_ok=True)

                # Generate visualization file path
                visualization_path = os.path.join(visualization_dir, f"comparison_{comparison_id}.png")

                # Generate the comparison visualization
                logger.info(f"Generating comparison visualization for {chart1_id} and {chart2_id}")
                visualization_success = generate_comparison_chart(
                    original_chart=chart1,
                    rectified_chart=chart2,
                    output_path=visualization_path
                )

                if visualization_success and os.path.exists(visualization_path):
                    visualization_url = f"/api/chart/comparison/{comparison_id}/visualization"

                    # Get base64 encoding of the image for inline display
                    import base64
                    with open(visualization_path, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode('utf-8')
                        visualization_data = f"data:image/png;base64,{image_data}"

                    logger.info(f"Successfully generated comparison visualization at {visualization_path}")
                else:
                    logger.warning(f"Failed to generate visualization image at {visualization_path}")
            except Exception as viz_error:
                logger.error(f"Error generating comparison visualization: {viz_error}")
                # Continue without visualization if it fails

        # Store comparison results with interpretation in database
        comparison_data = {
            "comparison_id": comparison_id,
            "chart1_id": chart1_id,
            "chart2_id": chart2_id,
            "differences": differences,
            "interpretation": interpretation,
            "created_at": datetime.now().isoformat(),
            "visualization_url": visualization_url
        }

        # Store in database
        try:
            await chart_repository.store_comparison(comparison_id, comparison_data)
            logger.info(f"Comparison {comparison_id} stored in database")
        except Exception as db_error:
            logger.error(f"Error storing comparison data in database: {db_error}")
            # Throw error since storing in the database is critical
            raise HTTPException(status_code=500, detail=f"Failed to store comparison data: {str(db_error)}")

        # Return enhanced comparison with interpretation and visualization
        response_data = {
            "status": "success",
            "comparison_id": comparison_id,
            "chart1_id": chart1_id,
            "chart2_id": chart2_id,
            "charts": {
                "chart1": {
                    "id": chart1_id,
                    "birth_details": chart1_details,
                    "ascendant": chart1.get("ascendant", {}),
                },
                "chart2": {
                    "id": chart2_id,
                    "birth_details": chart2_details,
                    "ascendant": chart2.get("ascendant", {}),
                }
            },
            "differences": differences,
            "interpretation": interpretation
        }

        # Add visualization data if available
        if visualization_url:
            response_data["visualization_url"] = visualization_url

        if visualization_data:
            response_data["visualization_data"] = visualization_data

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chart comparison: {e}")
        logger.error(traceback.format_exc())
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

@router.get("/comparison/{comparison_id}/visualization", response_class=FileResponse)
async def get_comparison_visualization(
    comparison_id: str = Path(..., description="Comparison ID"),
    background_tasks: BackgroundTasks = Depends()
):
    """
    Retrieve the visualization image for a chart comparison.

    Args:
        comparison_id: The ID of the comparison
        background_tasks: Background tasks manager for cleanup

    Returns:
        The visualization image file
    """
    try:
        # Create path to the visualization file
        visualization_dir = os.path.join(settings.MEDIA_ROOT, "comparisons")
        file_path = os.path.join(visualization_dir, f"comparison_{comparison_id}.png")

        # Check if the file exists
        if not os.path.exists(file_path):
            # Try to get the comparison data to regenerate it
            chart_repository = await get_chart_repository()
            comparison_data = await chart_repository.get_comparison(comparison_id)

            if not comparison_data:
                raise HTTPException(status_code=404, detail=f"Comparison {comparison_id} not found")

            # If the comparison exists but the file doesn't, we need to regenerate it
            chart_service = get_chart_service()
            chart1_id = comparison_data.get("chart1_id")
            chart2_id = comparison_data.get("chart2_id")

            if not chart1_id or not chart2_id:
                raise HTTPException(status_code=404, detail="Comparison data incomplete")

            chart1 = await chart_service.get_chart(chart1_id)
            chart2 = await chart_service.get_chart(chart2_id)

            if not chart1 or not chart2:
                raise HTTPException(status_code=404, detail="One or both charts not found")

            # Ensure the directory exists
            os.makedirs(visualization_dir, exist_ok=True)

            # Generate the visualization
            from ai_service.utils.chart_visualizer import generate_comparison_chart
            file_path = generate_comparison_chart(chart1, chart2, file_path)

            if not os.path.exists(file_path):
                raise HTTPException(status_code=500, detail="Failed to generate comparison visualization")

        # Return the file
        return FileResponse(
            path=file_path,
            filename=f"comparison_{comparison_id}.png",
            media_type="image/png"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving comparison visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving comparison visualization: {str(e)}")
