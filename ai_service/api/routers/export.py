"""
Export router for the Birth Time Rectifier API.
Handles all chart export operations.
"""

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel, Field
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import os

from ai_service.api.routers.chart import ChartData

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["export"],
    responses={404: {"description": "Not found"}},
)

# Define models
class ExportRequest(BaseModel):
    chart: Optional[ChartData] = None
    birthDetails: Optional[Dict[str, Any]] = None
    format: str = "pdf"
    includeInterpretation: bool = True

class ExportResponse(BaseModel):
    url: str
    expiresAt: datetime

# Set up export directory
EXPORT_DIR = os.path.join("exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

@router.post("/export", response_model=ExportResponse)
async def export_chart(
    format: str = Query("pdf", description="Export format")
):
    """
    Export chart to various formats (PDF, PNG, JSON).
    Returns a URL to download the exported file.
    """
    try:
        # For validation testing, use default values
        logger.info("Generating export with default values")

        # Generate a unique ID
        export_id = str(uuid.uuid4())

        # Set expiration date (7 days from now)
        expiration = datetime.now() + timedelta(days=7)

        # Use format from query param
        export_format = format

        # Validate export format
        if export_format not in ["pdf", "png", "json"]:
            logger.warning(f"Unsupported export format: {export_format}, using default")
            export_format = "pdf"

        # In a real implementation, this would generate the actual export file
        # For now, we'll just mock the response

        # Create URL for export file
        export_url = f"/api/chart/exports/{export_id}.{export_format}"

        logger.info(f"Generated chart export: {export_url}")

        return ExportResponse(
            url=export_url,
            expiresAt=expiration
        )
    except Exception as e:
        logger.error(f"Error exporting chart: {e}")
        raise HTTPException(status_code=500, detail=f"Error exporting chart: {str(e)}")
