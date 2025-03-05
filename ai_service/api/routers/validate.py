"""
Validation router for the Birth Time Rectifier API.
Handles all validation related endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import logging
from typing import Dict, Optional, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["validation"],
    responses={404: {"description": "Not found"}},
)

# Define models
class ValidationRequest(BaseModel):
    birthDate: str = Field(..., description="Birth date in format YYYY-MM-DD")
    birthTime: Optional[str] = Field(None, description="Birth time in format HH:MM or HH:MM:SS")
    location: Optional[str] = Field(None, description="Location string")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude between -90 and 90 degrees")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude between -180 and 180 degrees")

class ValidationResponse(BaseModel):
    isValid: bool
    errors: Dict[str, str] = {}
    suggestions: Dict[str, Any] = {}

@router.post("/validate", response_model=ValidationResponse)
async def validate_birth_details(request: ValidationRequest):
    """
    Validate birth details before generating a chart.
    Checks date format, time format, and coordinates validity.
    """
    try:
        errors = {}
        suggestions = {}

        # Validate birth date
        try:
            if request.birthDate:
                datetime.strptime(request.birthDate, "%Y-%m-%d")
            else:
                errors["birthDate"] = "Birth date is required"
        except ValueError:
            errors["birthDate"] = "Invalid date format. Use YYYY-MM-DD format."

        # Validate birth time if provided
        if request.birthTime:
            try:
                # Try to parse time in HH:MM or HH:MM:SS format
                time_parts = request.birthTime.split(":")
                if len(time_parts) < 2 or len(time_parts) > 3:
                    errors["birthTime"] = "Invalid time format. Use HH:MM or HH:MM:SS format."
                else:
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    second = int(time_parts[2]) if len(time_parts) > 2 else 0

                    if hour < 0 or hour > 23:
                        errors["birthTime"] = f"Hour must be between 0 and 23, got {hour}"
                    if minute < 0 or minute > 59:
                        errors["birthTime"] = f"Minute must be between 0 and 59, got {minute}"
                    if second < 0 or second > 59:
                        errors["birthTime"] = f"Second must be between 0 and 59, got {second}"
            except ValueError:
                errors["birthTime"] = "Invalid time format. Use HH:MM or HH:MM:SS format with numeric values."

        # Check coordinates validity
        if request.latitude is not None and (request.latitude < -90 or request.latitude > 90):
            errors["latitude"] = f"Latitude must be between -90 and 90, got {request.latitude}"

        if request.longitude is not None and (request.longitude < -180 or request.longitude > 180):
            errors["longitude"] = f"Longitude must be between -180 and 180, got {request.longitude}"

        # If location is provided but coordinates are missing, suggest geocoding
        if request.location and (request.latitude is None or request.longitude is None):
            suggestions["geocoding"] = f"Location '{request.location}' should be geocoded to get coordinates"

        # Return validation result
        is_valid = len(errors) == 0
        return ValidationResponse(
            isValid=is_valid,
            errors=errors,
            suggestions=suggestions
        )

    except Exception as e:
        logger.error(f"Error validating birth details: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating birth details: {str(e)}")
