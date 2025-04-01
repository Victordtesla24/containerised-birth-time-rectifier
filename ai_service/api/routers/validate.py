"""
Validation Router.

This module provides endpoints for validating birth details and other data.
Following the Unified API Gateway architecture and providing proper versioning.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Body
import traceback
from pydantic import BaseModel

from ai_service.models import ChartRequest
from ai_service.services import get_chart_service

# Configure logging
logger = logging.getLogger(__name__)

# Define the validation response model here to avoid import issues
class ValidationResponse(BaseModel):
    """Validation response model."""
    valid: bool
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None

# Create router with appropriate tags
router = APIRouter(
    tags=["validation"],
    responses={404: {"description": "Not found"}}
)

@router.post("", response_model=ValidationResponse)
async def validate_birth_details(
    birth_date: Optional[str] = Body(None),
    birth_time: Optional[str] = Body(None),
    latitude: Optional[float] = Body(None),
    longitude: Optional[float] = Body(None),
    timezone: Optional[str] = Body(None),
    request: Optional[ChartRequest] = None
) -> ValidationResponse:
    """
    Validate birth details before generating a chart.
    Supports both direct parameters and nested birth_details object.

    Args:
        birth_date: Birth date in ISO format (YYYY-MM-DD)
        birth_time: Birth time in 24-hour format (HH:MM)
        latitude: Birth latitude (-90 to 90)
        longitude: Birth longitude (-180 to 180)
        timezone: Timezone name (e.g., 'America/New_York')
        request: Birth details in ChartRequest format (alternative to individual parameters)

    Returns:
        Validation result
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Check which input format was used
        if request and hasattr(request, 'birth_details'):
            # Use birth_details from the request
            birth_details = request.birth_details
            logger.info(f"Validating from ChartRequest: {birth_details}")
        else:
            # Use individual parameters
            birth_details = {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone
            }
            logger.info(f"Validating from direct parameters: {birth_details}")

        # Validate birth details
        validation_result = await chart_service.validate_birth_details(birth_details)

        return ValidationResponse(
            valid=validation_result.get("valid", False),
            errors=validation_result.get("errors", []),
            warnings=validation_result.get("warnings", [])
        )
    except Exception as e:
        logger.error(f"Error validating birth details: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
