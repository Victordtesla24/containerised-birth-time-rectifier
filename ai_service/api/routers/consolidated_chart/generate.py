"""
Chart Generation Router

This module provides endpoints for generating and retrieving astrological charts,
with OpenAI verification against Indian Vedic Astrological standards.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Response, Depends, Request, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import logging
import time
from datetime import datetime
import uuid
import os

from ai_service.api.websocket_events import emit_event, EventType

# Import utilities and models
from ai_service.api.routers.consolidated_chart.utils import validate_chart_data, format_chart_response, store_chart, retrieve_chart
from ai_service.core.chart_calculator import calculate_chart, calculate_verified_chart
from ai_service.api.routers.consolidated_chart.consts import ERROR_CODES
from ai_service.services.chart_service import get_chart_service, ChartService
from ai_service.api.middleware import get_session_id
from ai_service.api.services.openai import get_openai_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["chart_generation"],
    responses={
        500: {"description": "Internal server error"},
        400: {"description": "Bad request - invalid parameters"},
        404: {"description": "Chart not found"}
    }
)

# Models for request/response
class ChartOptions(BaseModel):
    house_system: str = Field("P", description="House system (P=Placidus, K=Koch, etc.)")
    zodiac_type: str = Field("sidereal", description="Zodiac type (sidereal/tropical)")
    ayanamsa: Union[str, float] = Field("lahiri", description="Ayanamsa name or value")
    node_type: str = Field("true", description="Node type (true/mean)")
    verify_with_openai: bool = Field(True, description="Verify chart with OpenAI")

class BirthDetails(BaseModel):
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format", alias="date")
    birth_time: str = Field(..., description="Birth time in HH:MM:SS or HH:MM format", alias="time")
    latitude: float = Field(..., description="Birth location latitude")
    longitude: float = Field(..., description="Birth location longitude")
    location: Optional[str] = Field(None, description="Birth location name")
    timezone: str = Field(..., description="Timezone of birth location", alias="tz")
    full_name: Optional[str] = Field(None, description="Full name of the person")
    additional_info: Optional[str] = Field(None, description="Additional information")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "examples": [
                {
                    "birth_date": "1990-01-01",
                    "birth_time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "timezone": "America/New_York",
                }
            ]
        }
    }

class ChartRequest(BaseModel):
    birth_details: BirthDetails
    options: Optional[ChartOptions] = Field(None, description="Chart generation options")

# Alternative models for backward compatibility
class BirthDetailsAlt(BaseModel):
    birthDate: str
    birthTime: str
    latitude: float
    longitude: float
    timezone: str
    fullName: Optional[str] = None

class ChartRequestAlt(BaseModel):
    birthDetails: BirthDetailsAlt
    options: Optional[Dict[str, Any]] = None

# Simple format for maximum backward compatibility
class ChartRequestSimple(BaseModel):
    date: str
    time: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    timezone: Optional[str] = None
    tz: Optional[str] = None
    location: Optional[str] = None

class ChartResponse(BaseModel):
    chart_id: str
    verification: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class ValidationResponse(BaseModel):
    valid: bool
    errors: Optional[Dict[str, str]] = None
    message: Optional[str] = None

# Add these models for chart comparison
class ComparisonQueryParams(BaseModel):
    chart1_id: str = Field(..., description="ID of the first chart to compare")
    chart2_id: str = Field(..., description="ID of the second chart to compare")
    comparison_type: str = Field("differences", description="Type of comparison: differences, full, or summary")
    include_significance: bool = Field(True, description="Include significance scores in the response")

class ComparisonRequest(BaseModel):
    chart1_id: str = Field(..., description="ID of the first chart to compare")
    chart2_id: str = Field(..., description="ID of the second chart to compare")
    comparison_type: str = Field("differences", description="Type of comparison: differences, full, or summary")
    include_significance: bool = Field(True, description="Include significance scores in the response")

# Define required schemas locally
class ChartGenerationRequest(BaseModel):
    chart_data: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None

class ChartGenerationResponse(BaseModel):
    chart_id: str
    chart_data: Dict[str, Any]
    verification: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class ChartVerificationRequest(BaseModel):
    chart_id: str
    verification_type: str = "standard"

class ChartVerificationResponse(BaseModel):
    chart_id: str
    verification: Dict[str, Any]
    verified: bool = False
    message: Optional[str] = None

@router.post("/validate", response_model=ValidationResponse, operation_id="validate_birth_details_generator")
async def validate_birth_details(
    request: ChartRequest,
    response: Response
):
    """
    Validate birth details for chart generation.

    This endpoint validates birth date, time, and coordinates to ensure they are
    properly formatted and within valid ranges before chart generation.
    """
    try:
        # Extract birth details
        birth_details = request.birth_details

        # Basic validation checks
        errors = {}

        # Get date and time values
        date_str = birth_details.birth_date
        time_str = birth_details.birth_time

        # Add seconds if not provided in time
        if len(time_str.split(':')) == 2:
            time_str = f"{time_str}:00"

        # Get coordinates
        latitude = birth_details.latitude
        longitude = birth_details.longitude

        # Check date format
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            errors["birth_date"] = "Invalid date format. Use YYYY-MM-DD."

        # Check time format
        try:
            datetime.strptime(time_str, "%H:%M:%S")
        except ValueError:
            errors["birth_time"] = "Invalid time format. Use HH:MM:SS."

        # Check latitude range
        if latitude < -90 or latitude > 90:
            errors["latitude"] = "Latitude must be between -90 and 90."

        # Check longitude range
        if longitude < -180 or longitude > 180:
            errors["longitude"] = "Longitude must be between -180 and 180."

        # Return validation result
        if errors:
            return {
                "valid": False,
                "errors": errors,
                "message": "Birth details contain errors."
            }
        else:
            return {
                "valid": True,
                "errors": None,
                "message": "Birth details are valid."
            }

    except Exception as e:
        # Log the error
        logger.error(f"Error validating birth details: {str(e)}", exc_info=True)

        # Return validation error
        return {
            "valid": False,
            "errors": {"general": str(e)},
            "message": "Validation failed due to an error."
        }

@router.post("/validate/alt", response_model=ValidationResponse, operation_id="validate_birth_details_alt_generator")
async def validate_birth_details_alt(request: ChartRequestAlt, response: Response):
    """
    Alternative endpoint for birth details validation (backward compatibility).

    This endpoint provides the same functionality as the primary validation endpoint
    but accepts parameter names in a different format for backward compatibility.
    """
    # Convert from alternative format to standard format
    std_birth_details = BirthDetails(
        date=request.birthDetails.birthDate,
        time=request.birthDetails.birthTime,
        latitude=request.birthDetails.latitude,
        longitude=request.birthDetails.longitude,
        tz=request.birthDetails.timezone,
        full_name=request.birthDetails.fullName,
        location=None,
        additional_info=None
    )

    # Convert options
    std_options = None
    if request.options:
        std_options = ChartOptions(
            house_system=request.options.get("house_system", "P"),
            zodiac_type=request.options.get("zodiac_type", "sidereal"),
            ayanamsa=request.options.get("ayanamsa", "lahiri"),
            node_type=request.options.get("node_type", "true"),
            verify_with_openai=request.options.get("verify_with_openai", True)
        )

    # Create standard request
    std_request = ChartRequest(
        birth_details=std_birth_details,
        options=std_options
    )

    # Add deprecation warning header
    response.headers["X-Deprecation-Warning"] = "This endpoint is deprecated. Please use /validate instead."

    # Call primary endpoint
    return await validate_birth_details(std_request, response)

@router.post("/generate", response_model=Dict[str, Any])
async def generate_chart(
    request: Union[ChartRequest, Dict[str, Any]],
    response: Response,
    req: Request,
    background_tasks: BackgroundTasks
):
    """
    Generate an astrological chart based on birth details with OpenAI verification.

    This endpoint calculates an astrological chart based on the provided birth details
    and verifies it against Indian Vedic Astrological standards using OpenAI.
    """
    request_start_time = time.time()
    logger.info(f"Received chart generation request: {request}")

    try:
        # Verify OpenAI API key is available
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable is required for chart verification")

        # Check if request is a dict (flat format) or ChartRequest (nested format)
        if isinstance(request, dict):
            # Check if birth_details is present as a nested object
            birth_details_dict = request.get("birth_details", {})

            if not birth_details_dict:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": {
                            "code": ERROR_CODES["VALIDATION_ERROR"],
                            "message": "Chart validation failed",
                            "details": {"birth_details": "Birth details are required"}
                        }
                    }
                )

            # Extract options if present
            options_dict = request.get("options", {})
            if not isinstance(options_dict, dict):
                options_dict = {}

            options = ChartOptions(
                house_system=options_dict.get("house_system", "P"),
                zodiac_type=options_dict.get("zodiac_type", "sidereal"),
                ayanamsa=options_dict.get("ayanamsa", "lahiri"),
                node_type=options_dict.get("node_type", "true"),
                verify_with_openai=options_dict.get("verify_with_openai", True)
            )

            # Extract birth details fields
            birth_date = birth_details_dict.get("birth_date", birth_details_dict.get("date", birth_details_dict.get("birthDate", "")))
            birth_time = birth_details_dict.get("birth_time", birth_details_dict.get("time", birth_details_dict.get("birthTime", "")))
            location = birth_details_dict.get("location", birth_details_dict.get("birthLocation", "Unknown Location"))
            latitude = birth_details_dict.get("latitude", birth_details_dict.get("lat", 0.0))
            longitude = birth_details_dict.get("longitude", birth_details_dict.get("lng", 0.0))
            timezone = birth_details_dict.get("timezone", birth_details_dict.get("tz", "UTC"))

            # Validate required fields
            if not birth_date or not birth_time:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": {
                            "code": ERROR_CODES["VALIDATION_ERROR"],
                            "message": "Chart validation failed",
                            "details": {"birth_details": "Birth date and time are required"}
                        }
                    }
                )

            # Convert to proper BirthDetails object
            try:
                birth_details = BirthDetails(
                    date=birth_date,
                    time=birth_time,
                    latitude=float(latitude),
                    longitude=float(longitude),
                    tz=timezone,
                    location=location,
                    full_name=birth_details_dict.get("full_name", birth_details_dict.get("fullName", None)),
                    additional_info=birth_details_dict.get("additional_info", None)
                )
            except Exception as e:
                logger.error(f"Error parsing birth details: {e}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": {
                            "code": ERROR_CODES["VALIDATION_ERROR"],
                            "message": "Chart validation failed",
                            "details": {"birth_details": f"Invalid birth details: {str(e)}"}
                        }
                    }
                )

            # Store session_id if provided
            session_id = request.get("session_id")
        else:
            # Extract birth details from ChartRequest
            birth_details = request.birth_details

            # Extract options or use defaults
            options = request.options or ChartOptions(
                house_system="P",
                zodiac_type="sidereal",
                ayanamsa="lahiri",
                node_type="true",
                verify_with_openai=True
            )

            session_id = getattr(request, "session_id", None)

        # Format birth date and time
        date_str = getattr(birth_details, 'birth_date', getattr(birth_details, 'date', ''))
        if not date_str:
            raise ValueError("Birth date is required")

        time_str = getattr(birth_details, 'birth_time', getattr(birth_details, 'time', ''))
        if not time_str:
            raise ValueError("Birth time is required")

        # Add seconds if not provided in time
        if len(time_str.split(':')) == 2:
            time_str = f"{time_str}:00"

        # Get coordinates
        latitude = float(birth_details.latitude)
        longitude = float(birth_details.longitude)

        # Get timezone
        timezone = getattr(birth_details, 'timezone', getattr(birth_details, 'tz', 'UTC'))

        # Format birth details for calculation
        birth_details_formatted = {
            "date": date_str,
            "time": time_str,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "location": getattr(birth_details, 'location', 'Unknown')
        }

        # Generate unique chart ID
        chart_id = str(uuid.uuid4())

        # Prepare options for calculation
        calculation_options = {
            "house_system": options.house_system,
            "zodiac_type": options.zodiac_type,
            "ayanamsa": options.ayanamsa,
            "node_type": options.node_type,
            "verify_with_openai": options.verify_with_openai,
            "session_id": session_id,
        }

        # Get chart service for calculation
        chart_service = get_chart_service()

        # Calculate chart
        logger.info("Calculating chart with real service and data")
        try:
            chart_data = await chart_service.calculate_chart(
                birth_details=birth_details_formatted,
                options=calculation_options,
                chart_id=chart_id
            )
        except Exception as e:
            logger.error(f"Error in chart calculation: {e}")
            raise ValueError(f"Chart calculation failed: {str(e)}")

        # Format response
        formatted_response = format_chart_response(chart_data)

        # Store chart in database
        await store_chart(formatted_response)

        # Calculate processing time
        processing_time = time.time() - request_start_time

        # Return successful response
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "chart_id": chart_id,
                "processing_time": processing_time,
                "verification": formatted_response.get("verification", {}),
                "birth_details": {
                    "date": date_str,
                    "time": time_str,
                    "latitude": latitude,
                    "longitude": longitude,
                    "timezone": timezone
                },
                "message": "Chart generated successfully"
            }
        )

    except ValueError as e:
        # Handle validation errors
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": ERROR_CODES["VALIDATION_ERROR"],
                    "message": "Chart validation failed",
                    "details": {"validation_error": str(e)}
                }
            }
        )
    except Exception as e:
        # Log the full error for debugging
        logger.error(f"Error generating chart: {e}", exc_info=True)

        # Return a user-friendly error response
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": ERROR_CODES["INTERNAL_ERROR"],
                    "message": "Failed to generate chart",
                    "details": {"error": str(e)}
                }
            }
        )

@router.post("/generate/alt", response_model=Dict[str, Any])
async def generate_chart_alt(
    request: ChartRequestAlt,
    response: Response,
    req: Request,
    background_tasks: BackgroundTasks
):
    """
    Alternative endpoint for chart generation (backward compatibility).

    This endpoint provides the same functionality as the primary endpoint
    but accepts parameter names in a different format for backward compatibility.
    """
    # Convert from alternative format to standard format
    std_birth_details = BirthDetails(
        date=request.birthDetails.birthDate,
        time=request.birthDetails.birthTime,
        latitude=request.birthDetails.latitude,
        longitude=request.birthDetails.longitude,
        tz=request.birthDetails.timezone,
        full_name=request.birthDetails.fullName,
        location=None,
        additional_info=None
    )

    # Convert options
    std_options = None
    if request.options:
        std_options = ChartOptions(
            house_system=request.options.get("house_system", "P"),
            zodiac_type=request.options.get("zodiac_type", "sidereal"),
            ayanamsa=request.options.get("ayanamsa", "lahiri"),
            node_type=request.options.get("node_type", "true"),
            verify_with_openai=request.options.get("verify_with_openai", True)
        )

    # Create standard request
    std_request = ChartRequest(
        birth_details=std_birth_details,
        options=std_options
    )

    # Add deprecation warning header
    response.headers["X-Deprecation-Warning"] = "This endpoint is deprecated. Please use /generate instead."

    # Call primary endpoint
    return await generate_chart(std_request, response, req, background_tasks)

@router.post("/generate/simple", response_model=Dict[str, Any])
async def generate_chart_simple(
    request: ChartRequestSimple,
    response: Response,
    req: Request,
    background_tasks: BackgroundTasks
):
    """
    Simple endpoint for chart generation (maximum backward compatibility).

    This endpoint provides the same functionality as the primary endpoint
    but accepts a simplified set of parameters for maximum backward compatibility.
    """
    # Extract and normalize values
    lat = request.latitude or request.lat or 0.0
    lng = request.longitude or request.lng or 0.0
    tz = request.timezone or request.tz or "UTC"

    # Convert to standard format
    std_birth_details = BirthDetails(
        date=request.date,
        time=request.time,
        latitude=lat,
        longitude=lng,
        tz=tz,
        location=request.location,
        full_name=None,
        additional_info=None
    )

    # Create standard request
    std_request = ChartRequest(
        birth_details=std_birth_details,
        options=None
    )

    # Add deprecation warning header
    response.headers["X-Deprecation-Warning"] = "This endpoint is deprecated. Please use /generate instead."

    # Call primary endpoint
    return await generate_chart(std_request, response, req, background_tasks)

@router.get("/{chart_id}", response_model=Dict[str, Any])
async def get_chart(
    chart_id: str,
    response: Response,
    req: Request,
    background_tasks: BackgroundTasks
):
    """
    Retrieve a previously generated chart by ID.

    This endpoint retrieves a chart that was previously generated and stored in the system.
    """
    try:
        # Retrieve chart from storage
        chart_data = await retrieve_chart(chart_id)

        # Check if chart exists
        if not chart_data:
            # Return standardized error response
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ERROR_CODES["CHART_NOT_FOUND"],
                        "message": f"Chart not found: {chart_id}",
                        "details": {
                            "chart_id": chart_id
                        }
                    }
                }
            )

        # Format the chart response
        formatted_response = format_chart_response(chart_data)

        # Emit chart retrieved event if we have a session ID
        if hasattr(req.state, "session_id"):
            session_id = req.state.session_id
            # Send WebSocket event in the background
            background_tasks.add_task(
                emit_event,
                session_id,
                EventType.CHART_RETRIEVED,
                {
                    "chart_id": chart_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

        # Return the formatted chart
        return formatted_response
    except HTTPException:
        # Pass through HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error retrieving chart: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": f"Failed to retrieve chart: {str(e)}",
                    "details": {
                        "type": str(type(e).__name__)
                    }
                }
            }
        )

@router.get("/compare", response_model=Dict[str, Any])
async def compare_charts_get(
    chart1_id: str = Query(..., description="ID of the first chart to compare"),
    chart2_id: str = Query(..., description="ID of the second chart to compare"),
    comparison_type: str = Query("differences", description="Type of comparison: differences, full, or summary"),
    include_significance: bool = Query(True, description="Include significance scores in the response")
):
    """
    Compare two charts and return their differences (GET method).

    This endpoint compares two previously generated charts and analyzes their differences.
    Different comparison types provide different levels of detail:
    - 'differences': Just the list of differences
    - 'full': Complete comparison with detailed analysis
    - 'summary': Brief overview of key differences
    """
    # Create a standardized request object
    comparison_params = ComparisonQueryParams(
        chart1_id=chart1_id,
        chart2_id=chart2_id,
        comparison_type=comparison_type,
        include_significance=include_significance
    )

    # Call the comparison function
    return await compare_charts(comparison_params)

@router.post("/compare", response_model=Dict[str, Any])
async def compare_charts_post(request: ComparisonRequest):
    """
    Compare two charts and return their differences (POST method).

    This endpoint compares two previously generated charts and analyzes their differences.
    Different comparison types provide different levels of detail:
    - 'differences': Just the list of differences
    - 'full': Complete comparison with detailed analysis
    - 'summary': Brief overview of key differences
    """
    return await compare_charts(request)

async def compare_charts(params: Union[ComparisonQueryParams, ComparisonRequest]) -> Dict[str, Any]:
    """
    Common implementation for chart comparison (used by both GET and POST endpoints).

    Args:
        params: Parameters for the comparison, either from query or body

    Returns:
        Dict[str, Any]: The comparison result
    """
    try:
        # Retrieve both charts
        chart1 = await retrieve_chart(params.chart1_id)
        chart2 = await retrieve_chart(params.chart2_id)

        # Check if both charts exist
        if not chart1:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ERROR_CODES["CHART_NOT_FOUND"],
                        "message": f"Chart not found: {params.chart1_id}",
                        "details": {"chart_id": params.chart1_id}
                    }
                }
            )

        if not chart2:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ERROR_CODES["CHART_NOT_FOUND"],
                        "message": f"Chart not found: {params.chart2_id}",
                        "details": {"chart_id": params.chart2_id}
                    }
                }
            )

        # Generate a unique comparison ID
        comparison_id = f"cmp_{uuid.uuid4().hex[:8]}"

        # Compare the charts and generate differences
        differences = calculate_chart_differences(chart1, chart2, params.include_significance)

        # Create the base response
        response = {
            "comparison_id": comparison_id,
            "chart1_id": params.chart1_id,
            "chart2_id": params.chart2_id,
            "differences": differences
        }

        # Add summary if requested
        if params.comparison_type in ["full", "summary"]:
            summary = generate_comparison_summary(chart1, chart2, differences)
            response["summary"] = summary

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error comparing charts: {str(e)}", exc_info=True)

        # Return a standardized error response
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ERROR_CODES["COMPARISON_FAILED"],
                    "message": f"Failed to compare charts: {str(e)}",
                    "details": {
                        "type": str(type(e).__name__)
                    }
                }
            }
        )

def get_planet_significance(planet_name: str) -> float:
    """
    Get the significance score for a planet.

    Args:
        planet_name: The name of the planet

    Returns:
        float: The significance score (0.0-1.0)
    """
    # Define significance scores for different planets
    significance_map = {
        "sun": 0.95,
        "moon": 0.95,
        "mercury": 0.85,
        "venus": 0.85,
        "mars": 0.85,
        "jupiter": 0.9,
        "saturn": 0.9,
        "uranus": 0.8,
        "neptune": 0.8,
        "pluto": 0.75,
        "north_node": 0.7,
        "south_node": 0.7,
        "chiron": 0.65,
        "ascendant": 0.95,
        "midheaven": 0.9
    }

    # Normalize planet name
    normalized_name = planet_name.lower().replace(" ", "_")

    # Return significance score or default
    return significance_map.get(normalized_name, 0.7)

def get_house_significance(house_number: int) -> float:
    """
    Get the significance score for a house.

    Args:
        house_number: The house number (1-12)

    Returns:
        float: The significance score (0.0-1.0)
    """
    # Define significance scores for different houses
    significance_map = {
        1: 0.95,  # Ascendant/1st house - very important
        4: 0.9,   # IC/4th house - important for home/family
        7: 0.9,   # Descendant/7th house - important for relationships
        10: 0.9,  # MC/10th house - important for career
        2: 0.8,   # 2nd house - finances
        5: 0.8,   # 5th house - creativity, children
        8: 0.8,   # 8th house - transformation
        11: 0.8,  # 11th house - social connections
        3: 0.7,   # 3rd house - communication
        6: 0.7,   # 6th house - health, service
        9: 0.7,   # 9th house - higher learning
        12: 0.7   # 12th house - spirituality
    }

    # Return significance score or default
    return significance_map.get(house_number, 0.7)

def calculate_chart_differences(chart1: Dict[str, Any], chart2: Dict[str, Any], include_significance: bool) -> List[Dict[str, Any]]:
    """
    Calculate the differences between two charts.

    Args:
        chart1: The first chart data
        chart2: The second chart data
        include_significance: Whether to include significance scores

    Returns:
        List[Dict[str, Any]]: List of differences between the charts
    """
    differences = []

    # Compare birth details
    if "birth_details" in chart1 and "birth_details" in chart2:
        birth1 = chart1["birth_details"]
        birth2 = chart2["birth_details"]

        # Compare birth time
        time1 = birth1.get("birth_time", birth1.get("time", ""))
        time2 = birth2.get("birth_time", birth2.get("time", ""))

        if time1 != time2:
            differences.append({
                "type": "birth_time",
                "description": f"Birth time differs: {time1} vs {time2}",
                "significance": 0.9 if include_significance else None
            })

    # Compare ascendant
    if "ascendant" in chart1 and "ascendant" in chart2:
        asc1 = chart1["ascendant"]
        asc2 = chart2["ascendant"]

        if isinstance(asc1, dict) and isinstance(asc2, dict):
            if asc1.get("sign") != asc2.get("sign"):
                differences.append({
                    "type": "ascendant_sign",
                    "description": f"Ascendant sign differs: {asc1.get('sign')} vs {asc2.get('sign')}",
                    "significance": 0.95 if include_significance else None
                })

            long1 = asc1.get("longitude", 0)
            long2 = asc2.get("longitude", 0)

            if abs(long1 - long2) > 5:  # More than 5 degrees difference
                differences.append({
                    "type": "ascendant_position",
                    "description": f"Ascendant position differs by {abs(long1 - long2):.2f} degrees",
                    "significance": 0.9 if include_significance else None
                })

    # Compare planets
    if "planets" in chart1 and "planets" in chart2:
        planets1 = chart1["planets"]
        planets2 = chart2["planets"]

        # For dictionary format planets
        if isinstance(planets1, dict) and isinstance(planets2, dict):
            for planet_name in set(list(planets1.keys()) + list(planets2.keys())):
                if planet_name in planets1 and planet_name in planets2:
                    planet1 = planets1[planet_name]
                    planet2 = planets2[planet_name]

                    # Compare house placements
                    house1 = planet1.get("house")
                    house2 = planet2.get("house")
                    if house1 is not None and house2 is not None and house1 != house2:
                        differences.append({
                            "type": "planet_house",
                            "description": f"{planet_name} changes houses: {house1} to {house2}",
                            "significance": get_planet_significance(planet_name) if include_significance else None
                        })

                    # Compare signs
                    sign1 = planet1.get("sign")
                    sign2 = planet2.get("sign")
                    if sign1 is not None and sign2 is not None and sign1 != sign2:
                        differences.append({
                            "type": "planet_sign",
                            "description": f"{planet_name} changes signs: {sign1} to {sign2}",
                            "significance": get_planet_significance(planet_name) if include_significance else None
                        })

    # Compare houses
    if "houses" in chart1 and "houses" in chart2:
        houses1 = chart1["houses"]
        houses2 = chart2["houses"]

        # For list format houses
        if isinstance(houses1, list) and isinstance(houses2, list) and len(houses1) == len(houses2):
            for i in range(len(houses1)):
                house1 = houses1[i]
                house2 = houses2[i]

                if house1.get("sign") != house2.get("sign"):
                    house_num = house1.get("number", i+1)
                    differences.append({
                        "type": "house_sign",
                        "description": f"House {house_num} sign differs: {house1.get('sign')} vs {house2.get('sign')}",
                        "significance": get_house_significance(house_num) if include_significance else None
                    })

    return differences

def generate_comparison_summary(chart1: Dict[str, Any], chart2: Dict[str, Any], differences: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of the comparison between two charts.

    Args:
        chart1: The first chart data
        chart2: The second chart data
        differences: The list of differences between the charts

    Returns:
        Dict[str, Any]: A summary of the comparison
    """
    # Count differences by type
    diff_counts = {}
    for diff in differences:
        diff_type = diff.get("type", "unknown")
        diff_counts[diff_type] = diff_counts.get(diff_type, 0) + 1

    # Get the most significant differences
    significant_diffs = sorted(
        [d for d in differences if d.get("significance", 0) > 0.8],
        key=lambda x: x.get("significance", 0),
        reverse=True
    )[:5]  # Top 5 most significant differences

    # Create summary
    summary = {
        "total_differences": len(differences),
        "difference_counts": diff_counts,
        "significant_differences": significant_diffs,
        "summary_text": generate_summary_text(chart1, chart2, differences)
    }

    return summary

def generate_summary_text(chart1: Dict[str, Any], chart2: Dict[str, Any], differences: List[Dict[str, Any]]) -> str:
    """
    Generate a human-readable summary text of the comparison.

    Args:
        chart1: The first chart data
        chart2: The second chart data
        differences: The list of differences between the charts

    Returns:
        str: A human-readable summary of the comparison
    """
    if not differences:
        return "The charts are identical with no significant differences."

    # Get birth details
    birth1 = chart1.get("birth_details", {})
    birth2 = chart2.get("birth_details", {})

    time1 = birth1.get("birth_time", birth1.get("time", "unknown"))
    time2 = birth2.get("birth_time", birth2.get("time", "unknown"))

    # Count difference types
    planet_sign_diffs = sum(1 for d in differences if d.get("type") == "planet_sign")
    planet_house_diffs = sum(1 for d in differences if d.get("type") == "planet_house")
    house_sign_diffs = sum(1 for d in differences if d.get("type") == "house_sign")

    # Generate summary text
    summary = f"Comparison between charts for birth times {time1} and {time2}:\n"
    summary += f"Found {len(differences)} differences, including "
    summary += f"{planet_sign_diffs} planet sign changes, "
    summary += f"{planet_house_diffs} planet house changes, and "
    summary += f"{house_sign_diffs} house sign changes."

    # Add note about most significant difference if available
    if differences:
        most_significant = max(differences, key=lambda x: x.get("significance", 0))
        summary += f"\nMost significant difference: {most_significant.get('description')}"

    return summary

@router.post("/generate",
             summary="Generate a natal chart based on birth details",
             response_model=ChartGenerationResponse)
async def generate_chart_with_verification(
    request: Request,
    session_id: str = Depends(get_session_id)
) -> Dict[str, Any]:
    """
    Generate an astrological chart with OpenAI verification.

    This is the main implementation of the "Generate Chart with Verification"
    step in the sequence diagram.
    """
    logger.info("Received chart generation request")

    # Extract request data
    data = await request.json()

    # Get birth details from either nested object or top-level fields
    birth_details = data.get("birth_details", {})

    # Extract birth details from nested object or top-level fields
    birth_date = birth_details.get("birth_date") or data.get("birth_date")
    birth_time = birth_details.get("birth_time") or data.get("birth_time")
    location = birth_details.get("location") or data.get("location", "")
    latitude = birth_details.get("latitude") or data.get("latitude")
    longitude = birth_details.get("longitude") or data.get("longitude")
    timezone = birth_details.get("timezone") or data.get("timezone")

    # Check for alternative field names
    if not birth_date:
        birth_date = birth_details.get("date") or data.get("date") or birth_details.get("birthDate") or data.get("birthDate")
    if not birth_time:
        birth_time = birth_details.get("time") or data.get("time") or birth_details.get("birthTime") or data.get("birthTime")
    if not latitude:
        latitude = birth_details.get("lat") or data.get("lat")
    if not longitude:
        longitude = birth_details.get("lng") or data.get("lng")
    if not timezone:
        timezone = birth_details.get("tz") or data.get("tz")

    # Log extracted birth details
    logger.info(f"Extracted birth details - date: {birth_date}, time: {birth_time}, location: {location}")

    # Validate required fields
    if not birth_date or not birth_time:
        logger.error("Birth details missing required fields")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"birth_details": "Birth details are required"}
        )

    # Get options from request
    options = data.get("options", {})
    house_system = options.get("house_system", "W")  # Default to Whole Sign for Vedic
    verify_with_openai = options.get("verify_with_openai", True)

    # Get chart service
    chart_service = get_chart_service()

    # Step 3: Calculate the chart with or without verification
    try:
        if verify_with_openai and not os.environ.get("OPENAI_API_KEY"):
            # Handle missing API key by disabling verification
            logger.warning("OpenAI verification requested but API key missing, disabling verification")
            verification_warning = "OpenAI verification requested but API key missing"
            verify_with_openai = False

        chart_data = await calculate_verified_chart(
            birth_date=birth_date,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            location=location,
            house_system=house_system,
            zodiac_type=options.zodiac_type,
            ayanamsa=options.ayanamsa,
            node_type=options.node_type,
            verify_with_openai=verify_with_openai
        )
    except Exception as e:
        # Log the error
        logger.error(f"Error calculating chart: {str(e)}", exc_info=True)

        # Return error response with the standard error code format
        return {
            "error": {
                "code": ERROR_CODES["CALCULATION_ERROR"],
                "message": "Chart calculation failed",
                "details": {"calculation_error": str(e)}
            }
        }

    # Add chart ID if not present
    if "id" not in chart_data:
        chart_data["id"] = str(uuid.uuid4())

    # Create response
    response = {
        "chart_id": chart_data["id"],
        "message": "Chart generated successfully",
    }

    # Include verification if available
    if "verification" in chart_data:
        response["verification"] = chart_data["verification"]

    logger.info(f"Chart generated successfully with ID: {chart_data['id']}")
    return response
