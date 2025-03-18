"""
Chart Rectification Router

This module provides endpoints for birth time rectification using
questionnaire answers and AI techniques.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Response, Header, Depends
from starlette.background import BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union, cast
import logging
import uuid
from datetime import datetime

# Import utilities and models
from ai_service.api.routers.consolidated_chart.utils import retrieve_chart, store_chart
from ai_service.api.routers.consolidated_chart.consts import ERROR_CODES
from ai_service.models.unified_model import UnifiedRectificationModel
from ai_service.core.chart_calculator import calculate_verified_chart
from ai_service.api.websocket_events import emit_event, emit_rectification_progress, EventType
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the UnifiedRectificationModel
rectification_model = UnifiedRectificationModel()

# Create router with appropriate tags
router = APIRouter(
    tags=["chart_rectification"],
    responses={
        500: {"description": "Internal server error"},
        404: {"description": "Chart not found"},
        400: {"description": "Bad request - invalid parameters"}
    }
)

# Models for request/response
class Answer(BaseModel):
    question_id: str
    answer: str

class TimeRange(BaseModel):
    min_hours: int
    min_minutes: int
    max_hours: int
    max_minutes: int

class RectificationRequest(BaseModel):
    chart_id: str
    answers: List[Answer]
    birth_time_range: Optional[TimeRange] = None

class RectificationResponse(BaseModel):
    rectified_time: str
    confidence_score: float
    original_time: str
    rectified_chart_id: str
    explanation: Optional[str] = None

@router.post("/rectify", response_model=RectificationResponse)
async def rectify_birth_time(
    background_tasks: BackgroundTasks,
    request: RectificationRequest,
    response: Response,
    session_id: Optional[str] = Header(None)
):
    """
    Rectify birth time based on questionnaire answers.

    This endpoint takes questionnaire answers and calculates the most likely
    birth time using AI analysis and astrological techniques.
    """
    try:
        # Retrieve the original chart
        chart_id = request.chart_id
        chart_data = retrieve_chart(chart_id)

        # Check if chart exists
        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ERROR_CODES["CHART_NOT_FOUND"],
                        "message": f"Chart not found: {chart_id}",
                        "details": {"chart_id": chart_id}
                    }
                }
            )

        # Log the rectification request
        logger.info(f"Rectifying birth time for chart: {chart_id} with {len(request.answers)} answers")

        # Send initial progress update via WebSocket if session_id is provided
        if session_id:
            await emit_rectification_progress(
                session_id,
                0,
                "Starting birth time rectification process",
                chart_id,
                "started"
            )

        # Get the original birth details
        birth_details = chart_data.get("birth_details", {})
        original_time = birth_details.get("time", "00:00:00")

        # Extract birth date with comprehensive fallback options
        birth_date = birth_details.get("date",
                                    birth_details.get("birth_date",
                                                   birth_details.get("birthDate", "")))

        # Log the birth details for debugging
        logger.info(f"Original birth details - date: '{birth_date}', time: '{original_time}'")

        latitude = birth_details.get("latitude", 0.0)
        longitude = birth_details.get("longitude", 0.0)
        location = birth_details.get("location", "")
        timezone = birth_details.get("timezone", "UTC")

        # Convert answers to the format expected by the UnifiedRectificationModel
        questionnaire_data = {
            "answers": [{"id": answer.question_id, "response": answer.answer} for answer in request.answers],
            "birth_time_range": None
        }

        if request.birth_time_range:
            questionnaire_data["birth_time_range"] = {
                "min_hours": request.birth_time_range.min_hours,
                "min_minutes": request.birth_time_range.min_minutes,
                "max_hours": request.birth_time_range.max_hours,
                "max_minutes": request.birth_time_range.max_minutes
            }

        # Prepare birth details for the model
        model_birth_details = {
            "birth_date": birth_date,
            "birth_time": original_time,
            "latitude": latitude,
            "longitude": longitude,
            "location": location,
            "timezone": timezone
        }

        # Check birth date before proceeding with AI rectification
        if not birth_date or not birth_date.strip():
            error_msg = "Birth date is missing, cannot proceed with rectification"
            logger.error(error_msg)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": ERROR_CODES["INVALID_REQUEST"],
                        "message": error_msg,
                        "details": {"required_field": "birth_date"}
                    }
                }
            )

        try:
            # Validate birth date format (YYYY-MM-DD)
            datetime.strptime(birth_date, "%Y-%m-%d")
        except ValueError as e:
            error_msg = f"Invalid birth date format: {birth_date}. Expected format: YYYY-MM-DD"
            logger.error(f"{error_msg}. Error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": ERROR_CODES["INVALID_REQUEST"],
                        "message": error_msg,
                        "details": {"birth_date": birth_date}
                    }
                }
            )

        # Perform AI-based birth time rectification with progress updates
        logger.info("Performing AI-based birth time rectification")

        # Send progress update - Analyzing questionnaire answers
        if session_id:
            await emit_rectification_progress(
                session_id,
                25,
                "Analyzing questionnaire answers",
                chart_id,
                "processing"
            )
            # Small delay to simulate processing time
            await asyncio.sleep(0.5)

        # Send progress update - Calculating planetary positions
        if session_id:
            await emit_rectification_progress(
                session_id,
                50,
                "Calculating planetary positions",
                chart_id,
                "processing"
            )
            # Small delay to simulate processing time
            await asyncio.sleep(0.5)

        rectification_result = await rectification_model.rectify_birth_time(
            birth_details=model_birth_details,
            questionnaire_data=questionnaire_data,
            original_chart=chart_data
        )

        # Send progress update - Finalizing rectification
        if session_id:
            await emit_rectification_progress(
                session_id,
                75,
                "Finalizing rectification",
                chart_id,
                "processing"
            )
            # Small delay to simulate processing time
            await asyncio.sleep(0.5)

        # Extract rectified time and confidence
        rectified_time = rectification_result.get("suggested_time", original_time)
        if ":" in rectified_time and len(rectified_time.split(":")) == 2:
            rectified_time = f"{rectified_time}:00"
        elif not rectified_time or rectified_time == "00:00":
            rectified_time = original_time

        confidence_score = rectification_result.get("confidence", 70.0)
        explanation = rectification_result.get("explanation", "")

        # Create a copy of the chart with the rectified time
        rectified_chart = dict(chart_data)

        # Update the birth time
        if "birth_details" in rectified_chart:
            rectified_chart["birth_details"]["time"] = rectified_time

        # Generate new chart data with the rectified time
        logger.info(f"Generating new chart with rectified time: {rectified_time}")

        new_chart_data = await calculate_verified_chart(
            birth_date=birth_date,
            birth_time=rectified_time,
            latitude=latitude,
            longitude=longitude,
            location=location,
            verify_with_openai=True
        )

        # Merge new chart data with rectified chart
        for key, value in new_chart_data.items():
            if key not in ["birth_details"]:
                rectified_chart[key] = value

        # Add rectification metadata
        rectified_chart["rectification"] = {
            "original_time": original_time,
            "rectified_time": rectified_time,
            "confidence_score": confidence_score,
            "answers_used": len(request.answers),
            "significant_events": rectification_result.get("significant_events", []),
            "rectified_at": datetime.now().isoformat()
        }

        # Store the rectified chart
        rectified_chart_id = f"rect_{uuid.uuid4().hex[:8]}"
        rectified_chart["chart_id"] = rectified_chart_id
        store_chart(rectified_chart)

        # Send completion update via WebSocket
        if session_id:
            await emit_rectification_progress(
                session_id,
                100,
                "Rectification process completed",
                chart_id,
                "completed",
                {
                    "rectified_time": rectified_time,
                    "confidence_score": confidence_score,
                    "original_time": original_time,
                    "rectified_chart_id": rectified_chart_id
                }
            )

            # Also emit a separate rectification completed event
            if background_tasks:
                background_tasks.add_task(
                    emit_event,
                    session_id,
                    EventType.RECTIFICATION_COMPLETED,
                    {
                        "chart_id": chart_id,
                        "rectified_chart_id": rectified_chart_id,
                        "rectified_time": rectified_time,
                        "confidence_score": confidence_score,
                        "original_time": original_time
                    }
                )

        # Prepare the response
        result = {
            "rectified_time": rectified_time,
            "confidence_score": confidence_score,
            "original_time": original_time,
            "rectified_chart_id": rectified_chart_id,
            "explanation": explanation
        }

        return cast(RectificationResponse, result)

    except HTTPException:
        # Pass through HTTP exceptions
        raise
    except Exception as e:
        # Log the error
        logger.error(f"Error rectifying birth time: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ERROR_CODES["RECTIFICATION_FAILED"],
                    "message": f"Failed to rectify birth time: {str(e)}",
                    "details": {
                        "chart_id": request.chart_id,
                        "type": str(type(e).__name__)
                    }
                }
            }
        )
