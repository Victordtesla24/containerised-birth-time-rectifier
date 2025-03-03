"""
Questionnaire router for the Birth Time Rectifier API.
Handles all questionnaire and AI analysis related endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
import uuid

from ai_service.utils.questionnaire_engine import QuestionnaireEngine
from ai_service.models.unified_model import UnifiedRectificationModel
from ai_service.utils.astro_calculator import AstroCalculator

# Configure logging
logger = logging.getLogger(__name__)

# Create router
questionnaire_router = APIRouter(tags=["questionnaire"])

# Define models
class BirthDetails(BaseModel):
    """Birth details for questionnaire initialization"""
    birthDate: str
    birthTime: str
    birthPlace: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    additionalFactors: Optional[Dict[str, List[str]]] = None
    notes: Optional[str] = None

class ResponseData(BaseModel):
    """Response data for a question"""
    sessionId: str
    response: Dict[str, Any]

class QuestionOption(BaseModel):
    """Option for a question"""
    id: str
    text: str

class QuestionResponse(BaseModel):
    """Response model for a question"""
    id: str
    type: str
    text: str
    options: Optional[List[QuestionOption]] = None
    relevance: str

class QuestionnaireResponse(BaseModel):
    """Response model for questionnaire"""
    question: Optional[QuestionResponse] = None
    confidence: float
    isComplete: bool
    updatedChart: Optional[Dict[str, Any]] = None

# Dependency to get QuestionnaireEngine instance
def get_questionnaire_engine():
    return QuestionnaireEngine()

# Dependency to get UnifiedRectificationModel instance
def get_rectification_model():
    from ai_service.api.main import model  # Lazy import to avoid circular dependency
    if model is None:
        raise HTTPException(status_code=503, detail="Model not initialized")
    return model

# Dependency to get AstroCalculator instance
def get_astro_calculator():
    return AstroCalculator()

# Session storage - in a production app, this would be a database or Redis
# Using in-memory dictionary for simplicity
sessions = {}

@questionnaire_router.post("/initialize-questionnaire", response_model=Dict[str, Any])
async def initialize_questionnaire(
    request: BirthDetails,
    questionnaire_engine: QuestionnaireEngine = Depends(get_questionnaire_engine),
    astro_calculator: AstroCalculator = Depends(get_astro_calculator)
):
    """
    Initialize a new questionnaire session.

    Returns the first question and a session ID.
    """
    try:
        # Generate a session ID
        session_id = str(uuid.uuid4())

        # Try to geocode the birth place if coordinates are not provided
        if request.latitude is None or request.longitude is None or request.timezone is None:
            try:
                # Use geocoding service here
                # For now, we'll just use default values for demonstration
                logger.warning(f"Geocoding service not implemented. Using default values for missing coordinates.")

                if request.latitude is None:
                    request.latitude = 0.0

                if request.longitude is None:
                    request.longitude = 0.0

                if request.timezone is None:
                    request.timezone = "UTC"
            except Exception as e:
                logger.error(f"Error during geocoding: {e}")
                raise HTTPException(status_code=500, detail=f"Error during geocoding: {str(e)}")

        # Generate a birth chart
        try:
            birth_date = datetime.strptime(request.birthDate, "%Y-%m-%d").date()

            chart_data = astro_calculator.calculate_chart(
                birth_date=birth_date,
                birth_time=request.birthTime,
                latitude=request.latitude,
                longitude=request.longitude,
                timezone=request.timezone
            )
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            raise HTTPException(status_code=500, detail=f"Error generating chart: {str(e)}")

        # Store session data
        sessions[session_id] = {
            "birth_details": request.model_dump(),
            "chart_data": chart_data,
            "answers": {},
            "confidence": 0.0,
            "current_question_id": None
        }

        # Generate first question
        first_question = questionnaire_engine.get_first_question(chart_data, request.model_dump())

        # Save current question ID
        sessions[session_id]["current_question_id"] = first_question["id"]

        # Return response
        return {
            "sessionId": session_id,
            "question": first_question,
            "confidence": 0.0,
            "isComplete": False
        }

    except Exception as e:
        logger.error(f"Error initializing questionnaire: {e}")
        raise HTTPException(status_code=500, detail=f"Error initializing questionnaire: {str(e)}")

@questionnaire_router.post("/next-question", response_model=Dict[str, Any])
async def next_question(
    request: ResponseData,
    questionnaire_engine: QuestionnaireEngine = Depends(get_questionnaire_engine),
    astro_calculator: AstroCalculator = Depends(get_astro_calculator)
):
    """
    Process the response to the current question and get the next question.

    Returns the next question or completion status.
    """
    try:
        session_id = request.sessionId

        # Validate session
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

        session = sessions[session_id]

        # Validate current question
        if session["current_question_id"] is None:
            raise HTTPException(status_code=400, detail="No current question to answer")

        # Store the answer
        session["answers"][session["current_question_id"]] = request.response

        # Calculate current confidence
        current_confidence = questionnaire_engine.calculate_confidence(session["answers"])
        session["confidence"] = current_confidence

        # Check if we have enough confidence or reached the question limit
        is_complete = current_confidence >= 80 or len(session["answers"]) >= questionnaire_engine.max_questions

        if is_complete:
            # We have enough information to make a prediction
            return {
                "sessionId": session_id,
                "question": None,
                "confidence": current_confidence,
                "isComplete": True
            }
        else:
            # Generate next question
            next_question = questionnaire_engine.get_next_question(
                session["chart_data"],
                session["birth_details"],
                session["answers"],
                current_confidence
            )

            # Save current question ID
            session["current_question_id"] = next_question["id"]

            # Return response
            return {
                "sessionId": session_id,
                "question": next_question,
                "confidence": current_confidence,
                "isComplete": False
            }

    except Exception as e:
        logger.error(f"Error processing next question: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing next question: {str(e)}")

@questionnaire_router.get("/analysis", response_model=Dict[str, Any])
async def analysis(
    sessionId: str = Query(..., description="Session ID for analysis"),
    rectification_model: UnifiedRectificationModel = Depends(get_rectification_model),
    astro_calculator: AstroCalculator = Depends(get_astro_calculator)
):
    """
    Process all questionnaire responses and return birth time rectification results.
    """
    try:
        # Validate session
        if sessionId not in sessions:
            raise HTTPException(status_code=404, detail=f"Session not found: {sessionId}")

        session = sessions[sessionId]

        # Ensure we have enough data
        if len(session["answers"]) < 3:
            raise HTTPException(status_code=400, detail="Not enough questionnaire data. Please answer more questions.")

        # Get birth details
        birth_details = session["birth_details"]

        # Process answers with rectification model
        result = rectification_model.rectify_birth_time(
            birth_details=birth_details,
            questionnaire_data=session["answers"],
            original_chart=session["chart_data"]
        )

        # Get original time
        original_time = birth_details["birthTime"]

        # Format response
        response = {
            "originalTime": original_time,
            "suggestedTime": result["suggested_time"],
            "confidence": result["confidence"],
            "reliability": result["reliability"],
            "taskPredictions": {
                "time": result["task_predictions"]["time_accuracy"],
                "ascendant": result["task_predictions"]["ascendant_accuracy"],
                "houses": result["task_predictions"]["houses_accuracy"]
            },
            "explanation": result["explanation"],
            "significantEvents": result["significant_events"]
        }

        # Add rectified chart if available
        if "rectified_chart" in result:
            response["rectifiedChart"] = result["rectified_chart"]
        else:
            # Calculate rectified chart
            try:
                birth_date = datetime.strptime(birth_details["birthDate"], "%Y-%m-%d").date()

                rectified_chart = astro_calculator.calculate_chart(
                    birth_date=birth_date,
                    birth_time=result["suggested_time"],
                    latitude=birth_details["latitude"],
                    longitude=birth_details["longitude"],
                    timezone=birth_details["timezone"]
                )

                response["rectifiedChart"] = rectified_chart
            except Exception as e:
                logger.error(f"Error generating rectified chart: {e}")
                # Don't fail the whole request if chart generation fails

        return response

    except Exception as e:
        logger.error(f"Error processing analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing analysis: {str(e)}")
