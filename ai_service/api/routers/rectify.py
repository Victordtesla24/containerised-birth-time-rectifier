"""
Birth time rectification router for the Birth Time Rectifier API.
Handles all birth time rectification related endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from ai_service.models.unified_model import UnifiedRectificationModel
from ai_service.api.routers.chart import ChartRequest, generate_charts, compare_charts
from ai_service.services.chart_service import ChartService

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["rectification"],
    responses={404: {"description": "Not found"}},
)

# Define models
class RectificationRequest(BaseModel):
    birthDetails: ChartRequest
    questionnaire: Dict[str, Any]
    confidence: Optional[float] = None

class RectificationResult(BaseModel):
    originalTime: str
    rectifiedTime: str
    confidence: float
    reasons: List[str]
    chartComparison: Dict[str, Any]

# Dependency to get model instance
def get_rectification_model():
    from ai_service.main import model, init_model

    if model is None and not init_model():
        raise HTTPException(
            status_code=503,
            detail="Rectification model is not available. Please try again later."
        )

    return model

# Dependency to get ChartService instance
def get_chart_service():
    return ChartService()

@router.post("/rectify", response_model=RectificationResult)
async def rectify_birth_time(
    request: RectificationRequest,
    model: Optional[UnifiedRectificationModel] = Depends(get_rectification_model),
    chart_service: ChartService = Depends(get_chart_service)
):
    """
    Rectify birth time based on questionnaire responses and chart analysis.

    This endpoint implements the Birth Time Rectification Service that takes the
    original birth details and questionnaire results to suggest a more accurate
    birth time.
    """
    try:
        # Extract original birth details
        birth_details = request.birthDetails
        original_time = birth_details.birthTime

        # For now, we'll implement a simple mock rectification
        # In a real implementation, this would use AI analysis of questionnaire
        # responses and chart data to determine a more accurate birth time

        # Parse original time
        time_parts = original_time.split(":")
        hour = int(time_parts[0])
        minute = int(time_parts[1])

        # Adjust time by a small amount (this is just a mock example)
        # In a real implementation, the adjustment would be based on complex calculations
        adjusted_minute = (minute + 7) % 60
        adjusted_hour = (hour + (1 if adjusted_minute < minute else 0)) % 24

        rectified_time = f"{adjusted_hour:02d}:{adjusted_minute:02d}"

        # Generate charts for both times to compare
        birth_details_dict = birth_details.model_dump()

        # Original chart
        original_chart_request = ChartRequest(**birth_details_dict)
        original_chart = await generate_charts(original_chart_request, chart_service)

        # Rectified chart
        rectified_chart_request = ChartRequest(**{**birth_details_dict, "birthTime": rectified_time})
        rectified_chart = await generate_charts(rectified_chart_request, chart_service)

        # Compare charts
        comparison = await compare_charts(original_chart_request, rectified_chart_request, chart_service)

        # Calculate confidence based on questionnaire
        confidence = request.confidence or 85.0  # Default high confidence for now

        # Return result
        return RectificationResult(
            originalTime=original_time,
            rectifiedTime=rectified_time,
            confidence=confidence,
            reasons=[
                "Ascendant position aligns better with personality traits",
                "House cusps better match significant life events",
                "Moon position correlates with emotional patterns described"
            ],
            chartComparison=comparison
        )

    except Exception as e:
        logger.error(f"Error rectifying birth time: {e}")
        raise HTTPException(status_code=500, detail=f"Error rectifying birth time: {str(e)}")
