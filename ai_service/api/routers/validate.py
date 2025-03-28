"""
Validation Router.

This module provides endpoints for validating birth details and other data.
Following the Unified API Gateway architecture and providing proper versioning.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
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
async def validate_birth_details(request: ChartRequest) -> ValidationResponse:
    """
    Validate birth details before generating a chart.

    Args:
        request: Birth details to validate

    Returns:
        Validation result
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Validate birth details
        validation_result = await chart_service.validate_birth_details(request.birth_details)

        return ValidationResponse(
            valid=validation_result.get("valid", False),
            errors=validation_result.get("errors", []),
            warnings=validation_result.get("warnings", [])
        )
    except Exception as e:
        logger.error(f"Error validating birth details: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
