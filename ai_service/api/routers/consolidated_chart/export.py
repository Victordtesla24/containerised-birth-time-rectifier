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
        chart_data = retrieve_chart(chart_id)

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
            del exported_data["verification"]

        # Remove aspects if not requested
        if not request.include_aspects and "aspects" in exported_data:
            del exported_data["aspects"]

        # Add export metadata
        exported_data["export_info"] = {
            "exported_at": datetime.now().isoformat(),
            "format": request.format,
            "include_verification": request.include_verification,
            "include_aspects": request.include_aspects
        }

        # For JSON format, return the data directly
        if request.format == "json":
            return {
                "chart_id": chart_id,
                "format": request.format,
                "export_data": exported_data,
                "message": "Chart exported successfully in JSON format."
            }

        # For other formats, generate a download URL
        # In a real implementation, this would generate the file and store it
        # For this example, we'll just return a mock URL
        export_id = uuid.uuid4().hex[:8]
        download_url = f"/api/chart/export/{export_id}/download"

        # Return the export response with download URL
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
        # In a real implementation, this would retrieve the file from storage
        # For this example, we'll just return a mock response

        # Set content type based on export ID
        # In a real implementation, this would be determined by the file type
        response.headers["Content-Disposition"] = f"attachment; filename=chart_export_{export_id}.pdf"
        response.headers["Content-Type"] = "application/pdf"

        # Return a simple message for demonstration purposes
        # In a real implementation, this would return the file data
        return "This is a mock export file for demonstration purposes."

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
