"""
Birth Details Validation Router

This module provides endpoints for validating birth details
before generating a chart, ensuring data consistency and correctness.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Response
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import logging
import re
from datetime import datetime, timezone

# Import utilities and models
from ai_service.api.routers.consolidated_chart.consts import ERROR_CODES

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["chart_validation"],
    responses={
        500: {"description": "Internal server error"},
        400: {"description": "Bad request - invalid parameters"}
    }
)

# Models for request/response
class BirthDetails(BaseModel):
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format", alias="date")
    birth_time: str = Field(..., description="Birth time in HH:MM:SS or HH:MM format", alias="time")
    latitude: float = Field(..., description="Birth location latitude")
    longitude: float = Field(..., description="Birth location longitude")
    timezone: str = Field(..., description="Timezone of birth location", alias="tz")
    location: Optional[str] = Field(None, description="Birth location name")

    model_config = {
        "populate_by_name": True,
        # Allow both the alias and the attribute name in validation
        # This ensures backward compatibility
    }

# Wrapper for nested request format
class BirthDetailsWrapper(BaseModel):
    birth_details: BirthDetails

class BirthDetailsAlt(BaseModel):
    birthDate: str
    birthTime: str
    latitude: float
    longitude: float
    timezone: str
    location: Optional[str] = None

class ValidationResponse(BaseModel):
    valid: bool
    errors: Optional[Dict[str, str]] = None
    warnings: Optional[Dict[str, str]] = None

@router.post("/validate", response_model=ValidationResponse, operation_id="validate_birth_details_validation")
async def validate_birth_details(request_data: Dict[str, Any] = Body(...)):
    """
    Validate birth details for chart generation.

    This endpoint validates the provided birth details to ensure they are
    correctly formatted and within acceptable ranges for chart generation.
    """
    try:
        # Extract birth details from either format
        if "birth_details" in request_data:
            # Nested format: {"birth_details": {...}}
            birth_details_dict = request_data["birth_details"]
        else:
            # Flat format: {...}
            birth_details_dict = request_data

        # Define field aliases
        field_aliases = {"birth_date": "date", "birth_time": "time", "timezone": "tz"}

        # Ensure all required fields are present
        required_fields = ["birth_date", "birth_time", "latitude", "longitude", "timezone"]
        for field in required_fields:
            if field not in birth_details_dict:
                # Try aliased fields (date/time/tz)
                if field in field_aliases and field_aliases[field] in birth_details_dict:
                    # Field is present with its alias
                    continue
                raise HTTPException(
                    status_code=422,
                    detail={"error": {"code": "invalid_request", "message": "The request was invalid",
                           "details": [{"field": f"body.{field}", "issue": "Field required", "type": "missing"}]}}
                )

        # Convert to expected field names if aliases were used
        bd = {}
        if "date" in birth_details_dict:
            bd["birth_date"] = birth_details_dict["date"]
        else:
            bd["birth_date"] = birth_details_dict["birth_date"]

        if "time" in birth_details_dict:
            bd["birth_time"] = birth_details_dict["time"]
        else:
            bd["birth_time"] = birth_details_dict["birth_time"]

        if "tz" in birth_details_dict:
            bd["timezone"] = birth_details_dict["tz"]
        else:
            bd["timezone"] = birth_details_dict["timezone"]

        bd["latitude"] = birth_details_dict["latitude"]
        bd["longitude"] = birth_details_dict["longitude"]

        # Optional field
        if "location" in birth_details_dict:
            bd["location"] = birth_details_dict["location"]

        # Run validation
        validation_result = validate_details(
            birth_date=bd["birth_date"],
            birth_time=bd["birth_time"],
            latitude=bd["latitude"],
            longitude=bd["longitude"],
            timezone=bd["timezone"]
        )

        return ValidationResponse(
            valid=validation_result.get("valid", False),
            errors=validation_result.get("errors"),
            warnings=validation_result.get("warnings")
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid birth details: {str(e)}"
        )

@router.post("/validate/alt", response_model=ValidationResponse, operation_id="validate_birth_details_alt_validation")
async def validate_birth_details_alt(request_data: Dict[str, Any] = Body(...)):
    """
    Alternative endpoint for validating birth details (backward compatibility).

    This endpoint provides the same functionality as the primary endpoint
    but accepts parameter names in a different format for backward compatibility.
    """
    try:
        # Map alternative field names to standard names
        field_mapping = {
            "birthDate": "birth_date",
            "birthTime": "birth_time",
            "timezone": "timezone",
            "latitude": "latitude",
            "longitude": "longitude",
            "location": "location"
        }

        # Check required fields
        required_alt_fields = ["birthDate", "birthTime", "latitude", "longitude", "timezone"]
        for field in required_alt_fields:
            if field not in request_data:
                raise HTTPException(
                    status_code=422,
                    detail={"error": {"code": "invalid_request", "message": "The request was invalid",
                           "details": [{"field": f"body.{field}", "issue": "Field required", "type": "missing"}]}}
                )

        # Convert alternative field names to standard names
        birth_details = {}
        for alt_field, std_field in field_mapping.items():
            if alt_field in request_data:
                birth_details[std_field] = request_data[alt_field]

        # Run validation
        validation_result = validate_details(
            birth_date=birth_details["birth_date"],
            birth_time=birth_details["birth_time"],
            latitude=birth_details["latitude"],
            longitude=birth_details["longitude"],
            timezone=birth_details["timezone"]
        )

        return ValidationResponse(
            valid=validation_result.get("valid", False),
            errors=validation_result.get("errors"),
            warnings=validation_result.get("warnings")
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error validating birth details: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=400,
            detail=f"Invalid birth details: {str(e)}"
        )

def validate_details(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: str
) -> Dict[str, Any]:
    """
    Validate birth details for correctness and completeness.

    Args:
        birth_date: Birth date in YYYY-MM-DD format
        birth_time: Birth time in HH:MM:SS or HH:MM format
        latitude: Birth location latitude
        longitude: Birth location longitude
        timezone: Timezone of birth location

    Returns:
        Dictionary with validation results
    """
    errors = {}
    warnings = {}

    # Validate date format and value
    try:
        # Check format
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', birth_date):
            errors["birth_date"] = "Birth date must be in YYYY-MM-DD format"
        else:
            # Check if date is valid
            datetime.strptime(birth_date, '%Y-%m-%d')
    except ValueError:
        errors["birth_date"] = "Invalid birth date"

    # Validate time format and value
    try:
        # Check format
        if not re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', birth_time):
            errors["birth_time"] = "Birth time must be in HH:MM or HH:MM:SS format"
        else:
            # Add seconds if not provided
            if len(birth_time.split(':')) == 2:
                birth_time = f"{birth_time}:00"

            # Check if time is valid
            time_parts = birth_time.split(':')
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = int(time_parts[2]) if len(time_parts) > 2 else 0

            if hours < 0 or hours > 23:
                errors["birth_time"] = "Hours must be between 0 and 23"
            elif minutes < 0 or minutes > 59:
                errors["birth_time"] = "Minutes must be between 0 and 59"
            elif seconds < 0 or seconds > 59:
                errors["birth_time"] = "Seconds must be between 0 and 59"
    except ValueError:
        errors["birth_time"] = "Invalid birth time"

    # Validate latitude
    if latitude < -90 or latitude > 90:
        errors["latitude"] = "Latitude must be between -90 and 90"

    # Validate longitude
    if longitude < -180 or longitude > 180:
        errors["longitude"] = "Longitude must be between -180 and 180"

    # Validate timezone
    # This is a basic validation - in a real system, you would check against a list of valid timezone names
    if not timezone:
        errors["timezone"] = "Timezone is required"

    # Check if date is too far in the past or future (warning)
    try:
        birth_year = int(birth_date.split('-')[0])
        current_year = datetime.now().year

        if birth_year < 1800:
            warnings["birth_date"] = "Birth year is before 1800, calculations may be less accurate"
        elif birth_year > current_year:
            warnings["birth_date"] = "Birth year is in the future"
    except (ValueError, IndexError):
        # Already have an error for birth_date, no need to add a warning
        pass

    # Return validation result
    return {
        "valid": len(errors) == 0,
        "errors": errors if errors else None,
        "warnings": warnings if warnings else None
    }
