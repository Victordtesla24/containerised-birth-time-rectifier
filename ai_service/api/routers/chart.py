"""
Chart Router.

This module provides endpoints for basic chart generation and retrieval.
Following the Unified API Gateway architecture with standardized prefix handling.
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, Depends
import uuid
from datetime import datetime, timedelta
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
    birth_details: Optional[BirthDetails] = None
    birth_date: Optional[str] = None
    birth_time: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    location: Optional[str] = None
    session_id: Optional[str] = Field(None, description="Session ID for tracking")

    def get_birth_details(self) -> Dict[str, Any]:
        """Extract birth details from either nested structure or top-level fields"""
        if self.birth_details:
            return {
                "birth_date": self.birth_details.birth_date,
                "birth_time": self.birth_details.birth_time,
                "latitude": self.birth_details.latitude,
                "longitude": self.birth_details.longitude,
                "timezone": self.birth_details.timezone,
                "location": self.birth_details.location
            }
        else:
            return {
                "birth_date": self.birth_date,
                "birth_time": self.birth_time,
                "latitude": self.latitude,
                "longitude": self.longitude,
                "timezone": self.timezone,
                "location": self.location
            }

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

        # Extract birth details - supporting both formats
        birth_details = request.get_birth_details()

        logger.info(f"Generating chart with birth details: {birth_details}")

        # Validate that we have all required fields
        if not all(key in birth_details and birth_details[key] is not None for key in ["birth_date", "birth_time", "latitude", "longitude"]):
            missing_fields = [key for key in ["birth_date", "birth_time", "latitude", "longitude"]
                             if key not in birth_details or birth_details[key] is None]
            raise ValueError(f"Missing required birth details: {', '.join(missing_fields)}")

        # Generate chart with verification
        chart_data = await chart_service.generate_chart(
            birth_date=birth_details["birth_date"],
            birth_time=birth_details["birth_time"],
            latitude=birth_details["latitude"],
            longitude=birth_details["longitude"],
            timezone=birth_details.get("timezone"),
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
        questionnaire_responses = []
        chart_data = None
        questionnaire_confidence = 0.0

        if session_id:
            try:
                # Import session store
                from ai_service.api.routers.questionnaire import get_session_store_class, get_session_async
                from ai_service.utils.questionnaire_engine import QuestionnaireEngine

                # Get session store
                SessionStore = get_session_store_class()
                session_store = SessionStore()

                # Get session
                session = await get_session_async(session_store, session_id)
                if session:
                    questionnaire_answers = session.get("responses", [])
                    questionnaire_responses = session.get("responses", [])
                    logger.info(f"Retrieved {len(questionnaire_answers)} answers from session {session_id}")

                    # Get confidence score from session if available
                    if "confidence_score" in session:
                        questionnaire_confidence = session.get("confidence_score", 0.0)
                        logger.info(f"Retrieved questionnaire confidence: {questionnaire_confidence}")
                    # If confidence is not stored in session, try to calculate it
                    else:
                        try:
                            # Initialize questionnaire engine
                            engine = QuestionnaireEngine()
                            # Calculate confidence based on answers
                            if chart_id:
                                chart_data = await chart_service.get_chart(chart_id)
                                questionnaire_confidence = await engine.calculate_confidence({"responses": questionnaire_answers}, chart_data)
                            else:
                                questionnaire_confidence = await engine.calculate_confidence({"responses": questionnaire_answers})
                            logger.info(f"Calculated questionnaire confidence: {questionnaire_confidence}")
                        except Exception as calc_err:
                            logger.warning(f"Error calculating questionnaire confidence: {calc_err}")
            except Exception as e:
                logger.warning(f"Error retrieving questionnaire answers: {e}")

        # Get the chart data if not already retrieved
        if chart_id and not chart_data:
            try:
                chart_data = await chart_service.get_chart(chart_id)
            except Exception as e:
                logger.error(f"Error getting chart data: {e}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Chart not found: {chart_id}"
                )

        # Extract key astrological indicators from questionnaire answers
        birth_time_indicators = {}
        life_events = []
        timing_preferences = {}
        personal_traits = {}

        # Parse questionnaire responses for astrological indicators
        for response in questionnaire_answers:
            question_id = response.get("question_id", "")
            question_text = response.get("question", "").lower() if response.get("question") else ""
            answer_text = response.get("answer", "").lower() if response.get("answer") else ""

            # Skip empty responses
            if not answer_text:
                continue

            # Extract birth time precision indicators
            if "birth time" in question_text or "birth_time" in question_id or "lagna" in question_text:
                birth_time_indicators["precision"] = answer_text

                # Analyze if there's a belief the time should be earlier or later
                if "earlier" in answer_text:
                    birth_time_indicators["adjustment_direction"] = "earlier"
                elif "later" in answer_text:
                    birth_time_indicators["adjustment_direction"] = "later"

            # Extract life events with timing information
            elif "event" in question_text or "happen" in question_text or "occurred" in question_text or "when" in question_text:
                # Look for year patterns
                import re
                years = re.findall(r'\b(19|20)\d{2}\b', answer_text)
                ages = re.findall(r'\b(age|at)\s+(\d+)\b', answer_text, re.I)

                # Only add if we found timing indicators
                if years or ages:
                    event_type = "general"

                    # Try to determine event type
                    if any(word in answer_text for word in ["marriage", "wedding", "spouse", "marry"]):
                        event_type = "marriage"
                    elif any(word in answer_text for word in ["child", "birth", "born", "pregnancy"]):
                        event_type = "child_birth"
                    elif any(word in answer_text for word in ["career", "job", "work", "employment", "promotion"]):
                        event_type = "career_change"
                    elif any(word in answer_text for word in ["move", "relocate", "moved", "relocation", "migration"]):
                        event_type = "relocation"
                    elif any(word in answer_text for word in ["health", "illness", "disease", "hospital", "recovery"]):
                        event_type = "health_crisis"
                    elif any(word in answer_text for word in ["education", "school", "college", "university", "degree"]):
                        event_type = "education"
                    elif any(word in answer_text for word in ["relationship", "breakup", "divorce"]):
                        event_type = "relationship"

                    # Add event with timing
                    life_events.append({
                        "event_type": event_type,
                        "description": answer_text,
                        "years": years,
                        "ages": [age[1] for age in ages] if ages else []
                    })

            # Extract timing preferences
            elif "rhythm" in question_text or "energy" in question_text or "time of day" in question_text:
                timing_preferences["daily_rhythm"] = answer_text

                # Try to determine preferred time of day
                if any(time in answer_text for time in ["morning", "sunrise", "early", "dawn"]):
                    timing_preferences["preferred_time"] = "morning"
                elif any(time in answer_text for time in ["afternoon", "midday", "noon"]):
                    timing_preferences["preferred_time"] = "afternoon"
                elif any(time in answer_text for time in ["evening", "sunset", "dusk"]):
                    timing_preferences["preferred_time"] = "evening"
                elif any(time in answer_text for time in ["night", "late", "midnight"]):
                    timing_preferences["preferred_time"] = "night"

            # Extract personality traits
            elif "personality" in question_text or "trait" in question_text or "describe yourself" in question_text:
                personal_traits["description"] = answer_text

                # Map traits to potential rising signs
                fire_traits = ["energetic", "enthusiastic", "passionate", "leadership", "confident"]
                earth_traits = ["practical", "reliable", "stable", "methodical", "grounded"]
                air_traits = ["intellectual", "social", "communicative", "curious", "logical"]
                water_traits = ["emotional", "intuitive", "sensitive", "compassionate", "nurturing"]

                # Count trait matches
                fire_count = sum(1 for trait in fire_traits if trait in answer_text)
                earth_count = sum(1 for trait in earth_traits if trait in answer_text)
                air_count = sum(1 for trait in air_traits if trait in answer_text)
                water_count = sum(1 for trait in water_traits if trait in answer_text)

                # Determine dominant element
                max_count = max(fire_count, earth_count, air_count, water_count)
                if max_count > 0:
                    if fire_count == max_count:
                        personal_traits["element"] = "fire"
                    elif earth_count == max_count:
                        personal_traits["element"] = "earth"
                    elif air_count == max_count:
                        personal_traits["element"] = "air"
                    elif water_count == max_count:
                        personal_traits["element"] = "water"

        # Advanced astrological calculation for birth time adjustment
        birth_time_adjustment = 0  # Minutes to adjust birth time
        confidence = 0.7  # Default confidence score

        # Get original birth time from chart data
        original_birth_time = None
        adjusted_birth_time = None
        if chart_data and "birth_details" in chart_data:
            original_birth_time = chart_data["birth_details"].get("time", chart_data["birth_details"].get("birth_time"))

        # Astrological calculation based on indicators and life events
        if questionnaire_answers:
            # Base confidence on questionnaire confidence
            # Convert questionnaire confidence from 0-100 to 0-1 scale if needed
            base_confidence = questionnaire_confidence / 100.0 if questionnaire_confidence > 1.0 else questionnaire_confidence

            # Quality modifier based on answer count and detail level
            quality_modifier = min(len(questionnaire_answers) * 0.05, 0.4)

            # Astrological indicator modifier
            astrological_modifier = 0.0

            # Add points for birth time indicators
            if birth_time_indicators:
                astrological_modifier += 0.15

                # Add more if there's a specific direction indicated
                if "adjustment_direction" in birth_time_indicators:
                    astrological_modifier += 0.05

            # Add points for life events with timing
            if life_events:
                # More events = more data points = more confidence
                astrological_modifier += min(len(life_events) * 0.05, 0.25)

            # Add points for timing preferences (correlates with rising sign)
            if timing_preferences:
                astrological_modifier += 0.1

            # Add points for personality traits (correlates with rising sign)
            if personal_traits and "element" in personal_traits:
                astrological_modifier += 0.15

            # Calculate adjusted confidence
            confidence = min(base_confidence + quality_modifier + astrological_modifier, 0.99)

            # Calculate birth time adjustment based on indicators and life events
            # Default adjustment magnitude based on confidence and answers
            adjustment_magnitude = min(len(questionnaire_answers) * 1.5, 30)

            # Apply direction based on indicators
            adjustment_direction = 1.0  # Default positive (later)

            # Use explicit direction if indicated
            if "adjustment_direction" in birth_time_indicators:
                if birth_time_indicators["adjustment_direction"] == "earlier":
                    adjustment_direction = -1.0

            # Adjust based on timing preferences if available
            if "preferred_time" in timing_preferences:
                pref_time = timing_preferences["preferred_time"]
                if original_birth_time:
                    try:
                        time_obj = datetime.strptime(original_birth_time, "%H:%M:%S")
                        hour = time_obj.hour

                        # Morning preference but evening birth or vice versa
                        if (pref_time == "morning" and 12 <= hour <= 23) or (pref_time == "night" and 5 <= hour <= 10):
                            adjustment_magnitude += 10

                        # Midday preference vs early/late birth
                        if (pref_time == "afternoon" and (hour < 10 or hour > 18)):
                            adjustment_magnitude += 5
                    except ValueError:
                        pass

            # Additional correction based on life events correlation
            if life_events and len(life_events) >= 3:
                # More events with consistent pattern increases adjustment
                adjustment_magnitude += min(len(life_events) * 0.8, 15)

            # Final calculation
            birth_time_adjustment = int(adjustment_magnitude * adjustment_direction)

            # Higher confidence should generally mean smaller adjustments
            # (unless strong indicators suggest specific large adjustment)
            if confidence > 0.9 and abs(birth_time_adjustment) > 20:
                # Scale down extreme adjustments for high confidence cases
                birth_time_adjustment = int(birth_time_adjustment * 0.7)

            logger.info(f"Calculated adjustment: {birth_time_adjustment} minutes with confidence {confidence}")
        else:
            # If no questionnaire data, use basic approach
            confidence = 0.5 if chart_data else 0.3
            birth_time_adjustment = 0

        # Boost confidence for high-quality data, but require more questions and diverse coverage
        if questionnaire_confidence > 85 and len(questionnaire_answers) >= 10:
            # Check for category diversity before boosting confidence
            categories = set()
            for answer in questionnaire_answers:
                category = answer.get("category", "")
                if category:
                    categories.add(category)

            # Only boost if we have good category coverage
            if len(categories) >= 6:
                confidence = max(confidence, 0.85)
                logger.info(f"Boosted confidence to {confidence} based on high-quality questionnaire data with {len(categories)} categories")
            else:
                logger.info(f"Not boosting confidence despite {len(questionnaire_answers)} answers due to limited category coverage ({len(categories)} categories)")

        # Further adjustments if we have enough high-quality life events
        if len(life_events) >= 5 and confidence > 0.8:
            # Check if the life events contain detailed timing information
            detailed_events = 0
            for event in life_events:
                # Count events with specific years or ages
                if event.get("years") or event.get("ages"):
                    detailed_events += 1

            # Only boost confidence if we have at least 3 detailed events
            if detailed_events >= 3:
                confidence = max(confidence, 0.90)
                logger.info(f"Boosted confidence to {confidence} based on {detailed_events} detailed life events")
            else:
                logger.info(f"Not boosting confidence despite {len(life_events)} life events due to limited timing details ({detailed_events} detailed events)")

        # Calculate adjusted birth time if we have original birth time
        if original_birth_time:
            try:
                # Parse original birth time
                time_formats = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"]
                time_obj = None

                for fmt in time_formats:
                    try:
                        time_obj = datetime.strptime(original_birth_time, fmt)
                        break
                    except ValueError:
                        continue

                if time_obj:
                    adjusted_time_obj = time_obj + timedelta(minutes=birth_time_adjustment)
                    adjusted_birth_time = adjusted_time_obj.strftime("%H:%M:%S")
                else:
                    logger.warning(f"Could not parse birth time: {original_birth_time}")
            except Exception as e:
                logger.warning(f"Error calculating adjusted birth time: {e}")

        # Create rectification results with enhanced data
        rectification_results = {
            "chart_id": chart_id,
            "session_id": session_id,
            "original_birth_time": original_birth_time,
            "adjusted_birth_time": adjusted_birth_time,
            "birth_time_adjustment_minutes": birth_time_adjustment,
            "confidence": confidence,
            "exceeds_threshold": confidence >= confidence_threshold,
            "questionnaire_answers_count": len(questionnaire_answers),
            "questionnaire_confidence": questionnaire_confidence,
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
