"""
Chart Export Router

This module provides endpoints for exporting astrological charts
in various formats.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Response
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import logging
import uuid
from datetime import datetime
import os
import tempfile
import json

# Import utilities and models
from ai_service.api.routers.consolidated_chart.utils import retrieve_chart
from ai_service.api.routers.consolidated_chart.consts import ERROR_CODES, EXPORT_FORMATS

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["chart_export"],
    responses={
        500: {"description": "Internal server error"},
        404: {"description": "Chart not found"},
        400: {"description": "Bad request - invalid parameters"}
    }
)

# Models for request/response
class ExportRequest(BaseModel):
    chart_id: str
    format: str = Field("json", description="Export format (json, pdf, png, svg, text)")
    include_verification: bool = Field(False, description="Include verification data")
    include_aspects: bool = Field(True, description="Include aspect data")

class ExportResponse(BaseModel):
    chart_id: str
    format: str
    download_url: Optional[str] = None
    export_data: Optional[Dict[str, Any]] = None
    message: str

@router.post("/export", response_model=ExportResponse)
async def export_chart(
    request: ExportRequest,
    response: Response
):
    """
    Export an astrological chart in the specified format.

    This endpoint retrieves a chart by ID and exports it in the requested format.
    For JSON format, the data is returned directly. For other formats, a download
    URL is provided.
    """
    try:
        # Check if the requested format is supported
        if request.format not in EXPORT_FORMATS:
            valid_formats = ", ".join(EXPORT_FORMATS)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": ERROR_CODES["VALIDATION_ERROR"],
                        "message": f"Invalid export format: {request.format}. Supported formats: {valid_formats}",
                        "details": {"format": request.format}
                    }
                }
            )

        # Retrieve the chart
        chart_id = request.chart_id
        chart_data = await retrieve_chart(chart_id)

        # Check if chart exists
        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ERROR_CODES["CHART_NOT_FOUND"],
                        "message": f"Chart not found: {chart_id}",
                        "details": {"chart_id": chart_id}
                    }
                }
            )

        # Log export request
        logger.info(f"Exporting chart: {chart_id} in format: {request.format}")

        # Remove verification data if not requested
        exported_data = dict(chart_data)
        if not request.include_verification and "verification" in exported_data:
            exported_data.pop("verification")

        # Remove aspects if not requested
        if not request.include_aspects and "aspects" in exported_data:
            exported_data.pop("aspects")

        # Add export metadata to a new dictionary to avoid modifying potentially incompatible types
        result_data = {
            "chart_data": exported_data,
            "export_info": {
                "exported_at": datetime.now().isoformat(),
                "format": request.format,
                "include_verification": request.include_verification,
                "include_aspects": request.include_aspects
            }
        }

        # Create export ID
        export_id = uuid.uuid4().hex[:8]

        # Define export directory
        export_dir = os.path.join(tempfile.gettempdir(), "chart_exports")
        os.makedirs(export_dir, exist_ok=True)

        # For JSON format, return the data directly but also save a file
        if request.format == "json":
            # Save the JSON file
            json_path = os.path.join(export_dir, f"{export_id}.json")
            with open(json_path, "w") as json_file:
                json.dump(result_data, json_file, indent=2)

            return {
                "chart_id": chart_id,
                "format": request.format,
                "export_data": result_data,
                "download_url": f"/export/{export_id}/download",
                "message": "Chart exported successfully in JSON format."
            }

        # For other formats, generate the appropriate file
        file_path = os.path.join(export_dir, f"{export_id}.{request.format}")

        if request.format in ["pdf", "png", "svg"]:
            # Import chart visualization utilities
            from ai_service.utils.chart_visualizer import generate_chart_visualization

            # Generate the visualization file
            generate_chart_visualization(
                chart_data=exported_data,
                output_path=file_path,
                format=request.format
            )
        elif request.format == "text":
            # Generate a text report
            from ai_service.utils.text_formatter import format_chart_as_text

            # Generate text report
            text_content = format_chart_as_text(exported_data)

            # Write to file
            with open(file_path, "w") as text_file:
                text_file.write(text_content)

        # Return the export response with download URL
        download_url = f"/export/{export_id}/download"
        return {
            "chart_id": chart_id,
            "format": request.format,
            "download_url": download_url,
            "message": f"Chart exported successfully in {request.format.upper()} format. Use the download URL to retrieve the file."
        }

    except HTTPException:
        # Pass through HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error exporting chart: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ERROR_CODES["EXPORT_FAILED"],
                    "message": f"Failed to export chart: {str(e)}",
                    "details": {
                        "chart_id": request.chart_id,
                        "format": request.format,
                        "type": str(type(e).__name__)
                    }
                }
            }
        )

@router.get("/export/{export_id}/download")
async def download_export(
    export_id: str,
    response: Response
):
    """
    Download an exported chart file.

    This endpoint returns the binary data of an exported chart file.
    """
    try:
        # Determine the file path based on export ID
        # Export files are stored in a temporary directory with their export ID
        export_dir = os.path.join(tempfile.gettempdir(), "chart_exports")
        os.makedirs(export_dir, exist_ok=True)

        # Construct file path - try both PDF and JSON formats since we don't know which was requested
        pdf_path = os.path.join(export_dir, f"{export_id}.pdf")
        json_path = os.path.join(export_dir, f"{export_id}.json")
        png_path = os.path.join(export_dir, f"{export_id}.png")

        # Determine which file exists and should be served
        if os.path.exists(pdf_path):
            file_path = pdf_path
            content_type = "application/pdf"
            filename = f"chart_export_{export_id}.pdf"
        elif os.path.exists(json_path):
            file_path = json_path
            content_type = "application/json"
            filename = f"chart_export_{export_id}.json"
        elif os.path.exists(png_path):
            file_path = png_path
            content_type = "image/png"
            filename = f"chart_export_{export_id}.png"
        else:
            # Export file not found
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ERROR_CODES["EXPORT_NOT_FOUND"],
                        "message": f"Export file not found for ID: {export_id}",
                        "details": {"export_id": export_id}
                    }
                }
            )

        # Set appropriate headers
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-Type"] = content_type

        # Read and return the file content
        with open(file_path, "rb") as file:
            content = file.read()

        # Return the file content
        return Response(content=content, media_type=content_type, headers=response.headers)

    except HTTPException:
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error downloading export: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ERROR_CODES["EXPORT_FAILED"],
                    "message": f"Failed to download export: {str(e)}",
                    "details": {
                        "export_id": export_id,
                        "type": str(type(e).__name__)
                    }
                }
            }
        )
