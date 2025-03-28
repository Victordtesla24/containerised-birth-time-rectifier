"""
Chart Export Router.

This module provides endpoints for exporting astrological charts in various formats.
Following the Unified API Gateway architecture and providing proper versioning.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Body
import traceback
import os
import base64
import uuid
from datetime import datetime

from ai_service.services import get_chart_service
from ai_service.services.chart_utils import retrieve_chart
from ai_service.services.chart_service_export import export_chart, get_content_type

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["export"],
    responses={404: {"description": "Not found"}}
)

@router.post("", response_model=Dict[str, Any])
async def export_chart_handler(
    chart_id: str = Body(..., description="Chart ID to export"),
    format: str = Body("json", description="Export format (json, pdf, png)"),
    include_verification: bool = Body(False, description="Include verification data")
) -> Dict[str, Any]:
    """
    Export a chart in the specified format.

    Args:
        chart_id: Chart ID to export
        format: Export format (json, pdf, png)
        include_verification: Include verification data

    Returns:
        Exported chart data or file URL
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get chart data
        chart_data = await retrieve_chart(chart_id)
        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart not found: {chart_id}")

        # Format should be lowercase
        format = format.lower()
        valid_formats = ["json", "pdf", "png"]

        if format not in valid_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {format}. Must be one of: {', '.join(valid_formats)}"
            )

        # Create a temporary directory for the export
        export_id = f"export_{uuid.uuid4().hex[:8]}"
        tmp_dir = os.path.join(os.environ.get("CHART_OUTPUT_DIR", "tmp"), export_id)
        os.makedirs(tmp_dir, exist_ok=True)

        # Export the chart
        export_result = export_chart(
            chart_data=chart_data,
            chart_output_dir=tmp_dir,
            formats=[format]
        )

        # Get the exported file path
        file_path = export_result.get(format)
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=500, detail=f"Export failed: No file generated")

        # Read the file data
        with open(file_path, "rb") as f:
            file_data = f.read()

        # Encode file data as base64
        encoded_data = base64.b64encode(file_data).decode("utf-8")
        content_type = get_content_type(format)

        # Format as a data URL
        data_url = f"data:{content_type};base64,{encoded_data}"

        # Create the response
        response = {
            "exportId": export_id,
            "chartId": chart_id,
            "format": format,
            "fileData": data_url,
            "exportedAt": datetime.now().isoformat()
        }

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting chart: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chart export failed: {str(e)}")
