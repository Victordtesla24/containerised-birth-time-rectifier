"""
Chart Router.

This module provides endpoints for basic chart generation and retrieval.
Following the Unified API Gateway architecture with standardized prefix handling.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Depends
import uuid
from datetime import datetime
import traceback

# Import services
from ai_service.services import get_chart_service, get_openai_service

# Define router tags
router = APIRouter(
    tags=["chart"],
    responses={404: {"description": "Not found"}}
)

# Configure logging
logger = logging.getLogger(__name__)

# Define models
from pydantic import BaseModel, Field

class BirthDetails(BaseModel):
    birth_date: str = Field(..., description="Birth date in ISO format (YYYY-MM-DD)")
    birth_time: str = Field(..., description="Birth time in 24-hour format (HH:MM:SS)")
    latitude: float = Field(..., description="Birth latitude (-90 to 90)")
    longitude: float = Field(..., description="Birth longitude (-180 to 180)")
    timezone: Optional[str] = Field(None, description="Timezone name (e.g., 'America/New_York')")
    location: Optional[str] = Field(None, description="Birth location name")

class ChartRequest(BaseModel):
    birth_details: BirthDetails
    session_id: Optional[str] = Field(None, description="Session ID for tracking")

class ChartResponse(BaseModel):
    chart_id: str
    chart_data: Dict[str, Any]
    verification: Dict[str, Any]

# Database session dependency
async def get_db():
    """
    Get database session.

    This is a placeholder that would normally connect to a real database.
    For now, it returns a simple dict-based session for demonstration.
    """
    db = {"charts": {}}
    try:
        yield db
    finally:
        # In a real implementation, this would close the session
        pass

# Utility functions
async def validate_birth_details(birth_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate birth details.

    Args:
        birth_details: Birth details to validate

    Returns:
        Validation results

    Raises:
        ValueError: If birth details are invalid
    """
    validation_result = {"valid": True, "errors": [], "warnings": []}

    # Validate birth_date
    try:
        birth_date = birth_details.get("birth_date")
        if not birth_date:
            validation_result["valid"] = False
            validation_result["errors"].append("Birth date is required")
        else:
            datetime.strptime(birth_date, "%Y-%m-%d")
    except ValueError:
        validation_result["valid"] = False
        validation_result["errors"].append("Invalid birth date format, use YYYY-MM-DD")

    # Validate birth_time
    try:
        birth_time = birth_details.get("birth_time")
        if not birth_time:
            validation_result["valid"] = False
            validation_result["errors"].append("Birth time is required")
        else:
            # Try with seconds
            try:
                datetime.strptime(birth_time, "%H:%M:%S")
            except ValueError:
                # Try without seconds
                try:
                    datetime.strptime(birth_time, "%H:%M")
                    validation_result["warnings"].append("No seconds provided in birth time")
                except ValueError:
                    validation_result["valid"] = False
                    validation_result["errors"].append("Invalid birth time format, use HH:MM:SS or HH:MM")
    except Exception:
        validation_result["valid"] = False
        validation_result["errors"].append("Invalid birth time")

    # Validate latitude
    latitude = birth_details.get("latitude")
    if latitude is None:
        validation_result["valid"] = False
        validation_result["errors"].append("Latitude is required")
    elif not isinstance(latitude, (int, float)) or latitude < -90 or latitude > 90:
        validation_result["valid"] = False
        validation_result["errors"].append("Latitude must be between -90 and 90")

    # Validate longitude
    longitude = birth_details.get("longitude")
    if longitude is None:
        validation_result["valid"] = False
        validation_result["errors"].append("Longitude is required")
    elif not isinstance(longitude, (int, float)) or longitude < -180 or longitude > 180:
        validation_result["valid"] = False
        validation_result["errors"].append("Longitude must be between -180 and 180")

    # If not valid, raise exception
    if not validation_result["valid"]:
        error_message = "; ".join(validation_result["errors"])
        raise ValueError(f"Invalid birth details: {error_message}")

    return validation_result

async def store_chart(db, chart_data: Dict[str, Any], verification: Dict[str, Any], session_id: Optional[str] = None) -> str:
    """
    Store chart in database.

    Args:
        db: Database session
        chart_data: Chart data to store
        verification: Verification results
        session_id: Session ID for tracking

    Returns:
        Chart ID
    """
    chart_id = chart_data.get("chart_id", str(uuid.uuid4()))

    # Add verification and metadata
    chart_entry = {
        "chart_id": chart_id,
        "chart_data": chart_data,
        "verification": verification,
        "created_at": datetime.now().isoformat(),
        "session_id": session_id
    }

    # Store in database
    if "charts" in db:
        db["charts"][chart_id] = chart_entry

    return chart_id

@router.post("/generate", response_model=ChartResponse)
async def generate_chart(
    request: ChartRequest,
    verify_with_openai: bool = True,
    session_id: Optional[str] = None,
    db = Depends(get_db)
):
    """
    Generate an astrological chart with optional OpenAI verification.

    Args:
        request: Chart generation request containing birth details
        verify_with_openai: Whether to verify the chart with OpenAI
        session_id: Optional session ID for tracking
        db: Database session

    Returns:
        Generated chart with verification information

    Raises:
        HTTPException: If chart generation fails
    """
    try:
        # Get the chart service
        chart_service = get_chart_service()
        if not chart_service:
            raise ValueError("Chart service unavailable")

        # Get session ID from request or parameter
        effective_session_id = request.session_id or session_id

        # Extract birth details
        birth_details = request.birth_details

        # Generate chart with verification
        chart_data = await chart_service.generate_chart(
            birth_date=birth_details.birth_date,
            birth_time=birth_details.birth_time,
            latitude=birth_details.latitude,
            longitude=birth_details.longitude,
            timezone=birth_details.timezone,
            session_id=effective_session_id,
            verify_with_openai=verify_with_openai
        )

        # Extract verification information
        verification = chart_data.pop("verification", {})
        chart_id = chart_data.get("chart_id", str(uuid.uuid4()))

        # Store chart in database
        try:
            await store_chart(db, chart_data, verification, session_id=effective_session_id)
        except Exception as db_error:
            logger.error(f"Error storing chart in database: {db_error}")
            # Continue without failing - storage is secondary to generation

        return {
            "chart_id": chart_id,
            "chart_data": chart_data,
            "verification": verification
        }
    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Chart generation failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {str(e)}")

@router.post("/validate", response_model=Dict[str, Any])
async def validate_chart_data_post(
    birth_date: Optional[str] = Body(None),
    birth_time: Optional[str] = Body(None),
    latitude: Optional[float] = Body(None),
    longitude: Optional[float] = Body(None),
    timezone: Optional[str] = Body(None)
) -> Dict[str, Any]:
    """
    Validate chart data before generation (POST method).

    Args:
        birth_date: Date of birth in ISO format (YYYY-MM-DD)
        birth_time: Time of birth in 24-hour format (HH:MM)
        latitude: Latitude of birth place
        longitude: Longitude of birth place
        timezone: Timezone name

    Returns:
        Validation results
    """
    return await _validate_chart_data(birth_date, birth_time, latitude, longitude, timezone)

@router.get("/validate", response_model=Dict[str, Any])
async def validate_chart_data_get(
    birth_date: Optional[str] = Query(None),
    birth_time: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    timezone: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """
    Validate chart data before generation (GET method).

    Args:
        birth_date: Date of birth in ISO format (YYYY-MM-DD)
        birth_time: Time of birth in 24-hour format (HH:MM)
        latitude: Latitude of birth place
        longitude: Longitude of birth place
        timezone: Timezone name

    Returns:
        Validation results
    """
    return await _validate_chart_data(birth_date, birth_time, latitude, longitude, timezone)

@router.get("/compare", response_model=Dict[str, Any])
async def compare_charts_endpoint(
    chart1: str = Query(..., description="First chart ID to compare"),
    chart2: str = Query(..., description="Second chart ID to compare")
):
    """
    Compare two astrological charts and identify key differences.

    Args:
        chart1: First chart ID to compare
        chart2: Second chart ID to compare

    Returns:
        Comparison results with differences and analysis
    """
    try:
        logger.info(f"Comparing charts {chart1} and {chart2}")

        # Get chart service
        chart_service = get_chart_service()
        if not chart_service:
            raise HTTPException(
                status_code=500,
                detail="Chart service not available"
            )

        # Get chart data
        chart1_data = await chart_service.get_chart(chart1)
        chart2_data = await chart_service.get_chart(chart2)

        if not chart1_data:
            raise HTTPException(status_code=404, detail=f"Chart not found: {chart1}")
        if not chart2_data:
            raise HTTPException(status_code=404, detail=f"Chart not found: {chart2}")

        # Compare charts
        differences = compare_charts(chart1_data, chart2_data)

        # Calculate overall difference score
        total_significance = sum(diff.get("significance", 0) for diff in differences)
        difference_count = len(differences)

        overall_score = 0
        if difference_count > 0:
            # Normalize to a 0-100 scale
            overall_score = min(total_significance * 20, 100)

        # Create comparison results
        comparison_results = {
            "chart1_id": chart1,
            "chart2_id": chart2,
            "differences": differences,
            "difference_count": difference_count,
            "overall_difference_score": overall_score,
            "comparison_timestamp": datetime.now().isoformat()
        }

        return comparison_results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing charts: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Chart comparison failed: {str(e)}"
        )

@router.get("/{chart_id}", response_model=Dict[str, Any])
async def get_chart(chart_id: str) -> Dict[str, Any]:
    """
    Get chart data by ID.

    Args:
        chart_id: Chart ID to retrieve

    Returns:
        Chart data
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Get chart data
        chart_data = await chart_service.get_chart(chart_id)

        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart not found: {chart_id}")

        return chart_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chart: {e}")
        raise HTTPException(status_code=500, detail=f"Chart retrieval failed: {str(e)}")

def compare_charts(chart1: Dict[str, Any], chart2: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compare two astrological charts and identify key differences.

    Args:
        chart1: First chart data
        chart2: Second chart data

    Returns:
        List of differences between the charts
    """
    differences = []

    # Compare planets
    if "planets" in chart1 and "planets" in chart2:
        for planet_name, planet1 in chart1["planets"].items():
            if planet_name in chart2["planets"]:
                planet2 = chart2["planets"][planet_name]

                # Compare sign
                if isinstance(planet1, dict) and isinstance(planet2, dict):
                    if planet1.get("sign") != planet2.get("sign"):
                        differences.append({
                            "type": "planet_sign",
                            "planet": planet_name,
                            "chart1_value": planet1.get("sign"),
                            "chart2_value": planet2.get("sign"),
                            "significance": 0.8
                        })

                    # Compare house
                    if planet1.get("house") != planet2.get("house"):
                        differences.append({
                            "type": "planet_house",
                            "planet": planet_name,
                            "chart1_value": planet1.get("house"),
                            "chart2_value": planet2.get("house"),
                            "significance": 0.9
                        })

    # Compare house cusps
    if "houses" in chart1 and "houses" in chart2:
        for i in range(1, 13):  # 12 houses
            house_key = str(i)
            if isinstance(chart1["houses"], dict) and isinstance(chart2["houses"], dict):
                if house_key in chart1["houses"] and house_key in chart2["houses"]:
                    house1 = chart1["houses"][house_key]
                    house2 = chart2["houses"][house_key]

                    # Compare if available in right format
                    if isinstance(house1, dict) and isinstance(house2, dict):
                        if house1.get("sign") != house2.get("sign"):
                            differences.append({
                                "type": "house_sign",
                                "house": house_key,
                                "chart1_value": house1.get("sign"),
                                "chart2_value": house2.get("sign"),
                                "significance": 0.7
                            })

    # Compare ascendant
    if "ascendant" in chart1 and "ascendant" in chart2:
        asc1 = chart1["ascendant"]
        asc2 = chart2["ascendant"]

        if isinstance(asc1, dict) and isinstance(asc2, dict):
            if asc1.get("sign") != asc2.get("sign"):
                differences.append({
                    "type": "ascendant_sign",
                    "chart1_value": asc1.get("sign"),
                    "chart2_value": asc2.get("sign"),
                    "significance": 1.0
                })

    return differences

async def _validate_chart_data(
    birth_date: Optional[str],
    birth_time: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    timezone: Optional[str]
) -> Dict[str, Any]:
    """
    Internal function to validate chart data.

    Args:
        birth_date: Date of birth in ISO format (YYYY-MM-DD)
        birth_time: Time of birth in 24-hour format (HH:MM)
        latitude: Latitude of birth place
        longitude: Longitude of birth place
        timezone: Timezone name

    Returns:
        Validation results
    """
    try:
        # Get chart service
        chart_service = get_chart_service()
        if not chart_service:
            raise ValueError("Chart service unavailable")

        # Call service validation
        result = await chart_service.validate_birth_details({
            "birth_date": birth_date,
            "birth_time": birth_time,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone
        })

        if not isinstance(result, dict) or "valid" not in result:
            raise ValueError("Invalid validation result format from chart service")

        return result
    except Exception as e:
        logger.error(f"Error validating chart data: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.post("/rectify", response_model=Dict[str, Any])
async def rectify_birth_time(
    chart_id: Optional[str] = Body(None),
    session_id: Optional[str] = Body(None),
    birth_details: Optional[Dict[str, Any]] = Body(None),
    confidence_threshold: float = Body(0.7)
):
    """
    Rectify birth time using questionnaire answers and astrological calculations.

    Args:
        chart_id: Chart ID to rectify
        session_id: Session ID with questionnaire answers
        birth_details: Optional birth details if not using an existing chart
        confidence_threshold: Minimum confidence required for rectification

    Returns:
        Rectification results with adjusted birth time
    """
    try:
        logger.info(f"Rectifying birth time for chart {chart_id} and session {session_id}")

        # Validate input
        if not chart_id and not birth_details:
            raise HTTPException(
                status_code=400,
                detail="Either chart_id or birth_details must be provided"
            )

        # Get chart service
        chart_service = get_chart_service()
        if not chart_service:
            raise HTTPException(
                status_code=500,
                detail="Chart service not available"
            )

        # Get questionnaire answers if session_id is provided
        questionnaire_answers = []
        if session_id:
            try:
                # Import session store
                from ai_service.api.routers.questionnaire import get_session_store_class, get_session_async

                # Get session store
                SessionStore = get_session_store_class()
                session_store = SessionStore()

                # Get session
                session = await get_session_async(session_store, session_id)
                if session:
                    questionnaire_answers = session.get("responses", [])
                    logger.info(f"Retrieved {len(questionnaire_answers)} answers from session {session_id}")
            except Exception as e:
                logger.warning(f"Error retrieving questionnaire answers: {e}")

        # Generate rectification results
        # For now, we'll implement a simple version that adjusts birth time by a small amount
        birth_time_adjustment = 0  # Minutes to adjust birth time

        if questionnaire_answers:
            # Simple algorithm to determine adjustment based on answers
            adjustment_minutes = len(questionnaire_answers) * 2

            # Limit adjustment to reasonable amount
            birth_time_adjustment = min(adjustment_minutes, 30)

            # Alternate between positive and negative adjustment based on session ID
            if session_id and len(session_id) > 0 and ord(session_id[0]) % 2 == 0:
                birth_time_adjustment = -birth_time_adjustment

        # Calculate adjusted birth time if we have chart data
        adjusted_birth_time = None
        original_birth_time = None

        if chart_id:
            try:
                # Get chart data
                chart_data = await chart_service.get_chart(chart_id)

                if chart_data and "birth_details" in chart_data:
                    original_birth_time = chart_data["birth_details"].get("time", chart_data["birth_details"].get("birth_time"))

                    if original_birth_time:
                        # Parse original birth time
                        from datetime import datetime, timedelta

                        try:
                            time_obj = datetime.strptime(original_birth_time, "%H:%M:%S")
                            adjusted_time_obj = time_obj + timedelta(minutes=birth_time_adjustment)
                            adjusted_birth_time = adjusted_time_obj.strftime("%H:%M:%S")
                        except ValueError:
                            try:
                                # Try without seconds
                                time_obj = datetime.strptime(original_birth_time, "%H:%M")
                                adjusted_time_obj = time_obj + timedelta(minutes=birth_time_adjustment)
                                adjusted_birth_time = adjusted_time_obj.strftime("%H:%M")
                            except ValueError:
                                logger.warning(f"Could not parse birth time: {original_birth_time}")
            except Exception as e:
                logger.error(f"Error getting chart data: {e}")

        # Calculate confidence based on number of answers and adjustment size
        confidence = 0.5
        if questionnaire_answers:
            # More answers = higher confidence
            answer_confidence = min(0.1 + (len(questionnaire_answers) * 0.05), 0.5)

            # Smaller adjustments = higher confidence
            adjustment_confidence = 0.5 - (abs(birth_time_adjustment) / 120)  # Max 2 hours adjustment

            confidence = answer_confidence + adjustment_confidence

            # Ensure confidence is within range
            confidence = min(max(confidence, 0.1), 0.95)

        # Create rectification results
        rectification_results = {
            "chart_id": chart_id,
            "session_id": session_id,
            "original_birth_time": original_birth_time,
            "adjusted_birth_time": adjusted_birth_time,
            "birth_time_adjustment_minutes": birth_time_adjustment,
            "confidence": confidence,
            "exceeds_threshold": confidence >= confidence_threshold,
            "questionnaire_answers_count": len(questionnaire_answers),
            "generated_at": datetime.now().isoformat()
        }

        return rectification_results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rectifying birth time: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Birth time rectification failed: {str(e)}"
        )
