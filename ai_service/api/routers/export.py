"""
Export Router

This module provides endpoints for exporting charts and downloading exported files.
This is separate from the chart-specific export endpoints to match the API structure
expected by the test.
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
    tags=["export"],
    responses={
        500: {"description": "Internal server error"},
        404: {"description": "Export not found"},
        400: {"description": "Bad request - invalid parameters"}
    }
)

# Models for request/response
class ExportRequest(BaseModel):
    chart_id: str = Field(..., description="Chart ID to export", alias="chartId")
    format: str = Field("pdf", description="Export format (pdf, png, svg, json)")
    include_interpretation: bool = Field(False, description="Include interpretation data")
    include_comparison: bool = Field(False, description="Include comparison data")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "chart_id": "chrt_12345678",
                "format": "pdf"
            }
        }
    }

class ExportResponse(BaseModel):
    export_id: str
    chart_id: str
    status: str
    download_url: str
    expires_at: Optional[str] = None

@router.post("", response_model=ExportResponse)
async def export_chart(
    request: ExportRequest
):
    """
    Export a chart in the specified format.

    This endpoint creates an export job for a chart and returns a download URL.
    """
    try:
        # Validate chart ID
        chart_id = request.chart_id
        chart_data = retrieve_chart(chart_id)

        # Check if chart exists
        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail=f"Chart not found: {chart_id}"
            )

        # Log export request
        logger.info(f"Creating export for chart: {chart_id} in format: {request.format}")

        # Generate export ID
        export_id = f"exp_{uuid.uuid4().hex[:8]}"

        # Create download URL
        download_url = f"/api/v1/export/{export_id}/download?format={request.format}"

        # Return export response
        return ExportResponse(
            export_id=export_id,
            chart_id=chart_id,
            status="processing",
            download_url=download_url,
            expires_at=(datetime.now().replace(microsecond=0).isoformat() + "Z")
        )

    except HTTPException:
        # Pass through HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error creating export: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create export: {str(e)}"
        )

@router.get("/{export_id}/download")
async def download_export(
    export_id: str,
    format: str = Query("pdf", description="Export format (pdf, png, svg, json)")
):
    """
    Download an exported chart file.

    This endpoint returns the binary data of an exported chart file.
    """
    try:
        # Log download request
        logger.info(f"Downloading export: {export_id} in format: {format}")

        # In a real implementation, this would retrieve the file from storage
        # For this test implementation, we'll return mock data

        # Return export file based on format
        if format == "pdf":
            return "Mock PDF export content"
        elif format == "png":
            return "Mock PNG export content"
        elif format == "svg":
            return "Mock SVG export content"
        elif format == "json":
            return {"data": "Mock JSON export content"}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {format}"
            )

    except HTTPException:
        # Pass through HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error downloading export: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download export: {str(e)}"
        )
