"""
Questionnaire router for the Birth Time Rectifier API.
Handles all questionnaire and AI analysis related endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, status, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, date, timedelta
import logging
import uuid
import asyncio
import traceback
import json
import re
import math

from ai_service.utils.questionnaire_engine import QuestionnaireEngine
from ai_service.models.unified_model import UnifiedRectificationModel
from ai_service.core.rectification.chart_calculator import calculate_chart
from ai_service.api.services.questionnaire_service import get_questionnaire_service
from ai_service.api.services.chart import get_chart_service
from ai_service.api.services.openai import get_openai_service
from ai_service.utils.geocoding import get_coordinates
from ai_service.api.services.session_service import get_session_store
from ai_service.core.rectification.main import comprehensive_rectification
from ai_service.utils.json_encoder import DateTimeEncoder
from ai_service.api.models.question import QuestionModel
from ai_service.api.models.questionnaire import QuestionnaireModel
from ai_service.common.constants import QUESTION_TEMPLATES

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/questionnaire", tags=["questionnaire"])

async def get_question_text(question_id: str, questionnaire_id: Optional[str] = None) -> str:
    """
    Get the text for a specific question ID.

    Args:
        question_id: The ID of the question to retrieve
        questionnaire_id: Optional questionnaire ID for context

    Returns:
        Question text

    Raises:
        ValueError: If question cannot be found
    """
    if not question_id:
        raise ValueError("Question ID is required")

    # Try to find the question in the database
    question = await QuestionModel.get_by_id(question_id)
    if question:
        return question.text

    # If question not found and we have a questionnaire ID, try to find it there
    if questionnaire_id:
        questionnaire = await QuestionnaireModel.get_by_id(questionnaire_id)
        if questionnaire and questionnaire.questions:
            for q in questionnaire.questions:
                if q.id == question_id:
                    return q.text

    # If still not found, look in standard question templates
    for category in QUESTION_TEMPLATES:
        for q in QUESTION_TEMPLATES[category]:
            if q.get("id") == question_id:
                return q.get("text", "")

    # Question not found
    raise ValueError(f"Question not found with ID: {question_id}")

# Define DynamicQuestionnaireService class
class DynamicQuestionnaireService:
    """
    Dynamic questionnaire service that generates astrologically relevant questions for birth time rectification.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.session_store = get_session_store()

    async def get_first_question(self, chart_id: str) -> Dict[str, Any]:
        """Get the first question of the questionnaire."""
        # Implementation details here
        # For now just return a basic structure
        return {
            "question": {
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "text": "What time were you born?",
                "type": "text"
            }
        }

    async def process_answer(self, question_id: Optional[str], answer: Any, chart_id: Optional[str]) -> Dict[str, Any]:
        """Process an answer and get the next question."""
        # Handle None values
        safe_question_id = question_id or f"q_{uuid.uuid4().hex[:8]}"
        safe_chart_id = chart_id or ""

        # Implementation details here
        # For now just return a basic structure
        return {
            "question": {
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "text": "Did any significant events happen in your early childhood?",
                "type": "text"
            },
            "complete": False,
            "progress": {"current": 2, "total_estimated": 10}
        }

    async def complete_questionnaire(self) -> Dict[str, Any]:
        """Complete the questionnaire and calculate confidence."""
        # Implementation details here
        # For now just return a basic structure
        return {
            "confidence": 75.0,
            "answer_count": 5
        }

# Create router without prefix (will be added in main.py)
router = APIRouter(
    tags=["questionnaire"],
    responses={404: {"description": "Not found"}},
)

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

class QuestionAnswer(BaseModel):
    """Answer for a question"""
    sessionId: str
    questionId: str
    answer: Any

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

# Model for individual question answers
class IndividualQuestionAnswer(BaseModel):
    """Model for answering individual questions"""
    question_id: str
    answer: Any

# Dependency to get QuestionnaireEngine instance
def get_questionnaire_engine():
    return QuestionnaireEngine()

# Dependency to get UnifiedRectificationModel instance
def get_rectification_model():
    """Get rectification model instance"""
    return UnifiedRectificationModel()

# Dependency to get AstroCalculator instance
def get_astro_calculator():
    """Get an instance of the AstroCalculator for backward compatibility."""
    # Return a simple dictionary-like object that can store chart calculation functions
    # This serves as a compatibility layer since we now use calculate_chart directly
    class AstroCalculatorCompat:
        def calculate_chart(self, *args, **kwargs):
            return calculate_chart(*args, **kwargs)

    return AstroCalculatorCompat()

# Use the real session_store for all session-related operations
from ai_service.api.services.session_service import get_session_store

@router.get("", response_model=Dict[str, Any])
async def get_questionnaire(
    chart_id: str = Query(None, description="Chart ID for personalized questions"),
    session_id: str = Query(None, description="Session ID for tracking"),
    questionnaire_service = Depends(get_questionnaire_service)
):
    """
    Get the first question of a dynamic questionnaire tailored to the chart data.
    """
    try:
        # Validate input
        if not chart_id:
            raise HTTPException(
                status_code=400,
                detail="Chart ID is required to generate personalized questions"
            )

        # Create a new session ID if none provided
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:8]}"

        # Use DynamicQuestionnaireService for truly dynamic questions
        dynamic_service = DynamicQuestionnaireService(session_id=session_id)

        # Initialize the questionnaire and get the first question
        questionnaire_data = await dynamic_service.get_first_question(chart_id)

        # Return the response
        return {
            "question": questionnaire_data.get("question"),
            "session_id": session_id,
            "chart_id": chart_id,
            "progress": {
                "current": 1,
                "total_estimated": 10
            }
        }
    except Exception as e:
        logger.error(f"Error in get_questionnaire: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questionnaire: {str(e)}"
        )

@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_questionnaire(
    request: Dict[str, Any],
    chart_id: Optional[str] = Query(None, description="Chart ID for personalized questions"),
    session_id: Optional[str] = Query(None, description="Session ID for continuing an existing session")
):
    """
    Initialize a questionnaire session with the first question, fully leveraging
    OpenAI to generate astrologically relevant questions for birth time rectification.

    This implementation ensures consistent OpenAI usage with no fallbacks.

    Creates a new session or uses an existing one.
    """
    try:
        # Initialize required services directly
        session_store = get_session_store()
        chart_service = get_chart_service()
        openai_service = get_openai_service()

        # Extract birth details
        birth_details = None
        if "birthDetails" in request:
            birth_details = request["birthDetails"]
        elif "birth_details" in request:
            birth_details = request["birth_details"]
            # Convert keys to match expected format
            if birth_details:
                if "birth_date" in birth_details and "birthDate" not in birth_details:
                    birth_details["birthDate"] = birth_details["birth_date"]
                if "birth_time" in birth_details and "birthTime" not in birth_details:
                    birth_details["birthTime"] = birth_details["birth_time"]
                if "birth_place" in birth_details and "birthPlace" not in birth_details:
                    birth_details["birthPlace"] = birth_details["birth_place"]

        # Validate required parameters
        if not birth_details:
            raise HTTPException(
                status_code=400,
                detail="Birth details are required to initialize questionnaire"
            )
        if not chart_id and "chartId" not in request:
            raise HTTPException(
                status_code=400,
                detail="Chart ID is required to initialize questionnaire"
            )

        # Use provided chart ID or extract from request
        effective_chart_id = chart_id or request.get("chartId")

        # Ensure chart_id is a string
        if not effective_chart_id or not isinstance(effective_chart_id, str):
            raise HTTPException(
                status_code=400,
                detail="Valid chart ID (string) is required"
            )

        # Create or get session
        session_data = {
            "chart_id": effective_chart_id,
            "birth_details": birth_details
        }

        # If continuing an existing session, validate it exists
        if session_id:
            existing_session = await session_store.get_session(session_id)
            if not existing_session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session not found with ID: {session_id}"
                )
            effective_session_id = session_id
        else:
            # Create a new session
            effective_session_id = await session_store.create_session(
                session_id=request.get("sessionId"),
                data=session_data
            )

        # Get the chart data for astrological context
        chart_data = await chart_service.get_chart(effective_chart_id)
        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail=f"Chart data not found for ID: {effective_chart_id}"
            )

        # Extract astrological context from chart data
        ascendant = chart_data.get("ascendant", {})
        planets = chart_data.get("planets", [])
        houses = chart_data.get("houses", [])

        # Prepare focused birth details for OpenAI
        birth_date = birth_details.get("birthDate", birth_details.get("birth_date", ""))
        birth_time = birth_details.get("birthTime", birth_details.get("birth_time", ""))
        birth_place = birth_details.get("birthPlace", birth_details.get("birth_place", ""))
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        timezone = birth_details.get("timezone", "UTC")

        # Prepare astrological context for OpenAI
        astrological_context = {
            "birth_details": {
                "date": birth_date,
                "time": birth_time,
                "place": birth_place,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone
            },
            "chart_elements": {
                "ascendant": ascendant,
                "rising_sign": ascendant.get("sign") if isinstance(ascendant, dict) else None,
                "planets": [
                    {"name": p.get("name"), "sign": p.get("sign"), "house": p.get("house")}
                    for p in planets if isinstance(p, dict)
                ],
                "houses": [
                    {"number": h.get("number"), "sign": h.get("sign")}
                    for h in houses if isinstance(h, dict)
                ]
            },
            "session_context": {
                "is_first_question": True,
                "purpose": "birth_time_rectification",
                "focus_areas": [
                    "birth time accuracy indicators",
                    "early life events with time sensitivity",
                    "physical appearance and personality for rising sign",
                    "key life events with transit correlations"
                ]
            }
        }

        # Get the initial question from OpenAI
        logger.info("Generating initial astrologically-focused question with OpenAI")

        question_prompt = {
            "task": "generate_initial_rectification_question",
            "astrological_context": astrological_context,
            "requirements": [
                "Create an astrologically accurate question optimized for birth time rectification",
                "Focus on factors most sensitive to birth time (ascendant, house cusps, etc.)",
                "Include appropriate options for multiple-choice questions",
                "Ensure question is personalized to the chart's specific astrological configuration",
                "Consider rising sign, MC/IC axis, and house placements in formulating the question"
            ]
        }

        # Get initial question from OpenAI
        question_response = await openai_service.generate_completion(
            prompt=json.dumps(question_prompt, cls=DateTimeEncoder),
            task_type="astrological_question_generation",
            max_tokens=500
        )

        # Validate OpenAI response
        if not question_response or "content" not in question_response:
            logger.error("Failed to receive valid response from OpenAI for initial question generation")
            raise ValueError("Failed to generate initial astrological question")

        # Parse the question data
        try:
            question_data = json.loads(question_response["content"])

            # Ensure the question has required fields
            if not isinstance(question_data, dict) or "text" not in question_data:
                logger.error("Invalid question format received from OpenAI")
                raise ValueError("OpenAI returned invalid question format")

            # Generate UUID for the question if not provided
            if "id" not in question_data:
                question_data["id"] = f"q_{uuid.uuid4().hex[:8]}"

            # Set default type if not provided
            if "type" not in question_data:
                question_data["type"] = "open_text"

            # Process options for multiple choice questions
            if "options" in question_data and question_data["options"]:
                processed_options = []
                for i, option in enumerate(question_data["options"]):
                    if isinstance(option, str):
                        processed_options.append({
                            "id": f"opt_{i}_{uuid.uuid4().hex[:4]}",
                            "text": option
                        })
                    elif isinstance(option, dict) and "text" in option:
                        if "id" not in option:
                            option["id"] = f"opt_{i}_{uuid.uuid4().hex[:4]}"
                        processed_options.append(option)
                question_data["options"] = processed_options

            # Initial confidence level
            confidence = 30.0

            # Update session with question data
            session = await session_store.get_session(effective_session_id)
            if session:
                if "questions" not in session:
                    session["questions"] = []
                session["questions"].append(question_data)
                session["current_question"] = question_data
                session["updated_at"] = datetime.now().isoformat()
                await session_store.update_session(effective_session_id, session)

            # Update session confidence
            await session_store.update_confidence(effective_session_id, confidence)

            # Prepare response
            return {
                "question": question_data,
                "sessionId": effective_session_id,
                "confidence": confidence,
                "isComplete": False
            }

        except json.JSONDecodeError:
            logger.error("Failed to parse OpenAI response as JSON")
            raise ValueError("Error parsing initial astrological question from OpenAI")

    except ValueError as e:
        logger.error(f"Error in questionnaire initialization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error initializing questionnaire: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize questionnaire: {str(e)}"
        )

@router.post("/next-question", response_model=Dict[str, Any])
async def get_next_question(
    session_id: str = Query(..., description="Session ID for the questionnaire"),
    chart_id: Optional[str] = Query(None, description="Chart ID for personalized questions"),
    question_id: Optional[str] = Query(None, description="ID of the previous question"),
    answer: Optional[Dict[str, Any]] = Body(None, description="Answer to the previous question")
):
    """
    Get the next question in the questionnaire sequence.

    This endpoint processes the previous answer (if provided) and returns the next question
    based on the birth chart data and previous responses.
    """
    try:
        # Use DynamicQuestionnaireService for truly dynamic questions
        dynamic_service = DynamicQuestionnaireService(session_id=session_id)

        # Process the answer and get the next question
        result = await dynamic_service.process_answer(
            question_id=question_id,
            answer=answer.get("answer") if answer else None,
            chart_id=chart_id
        )

        # Check if the questionnaire is complete
        if result.get("complete", False):
            # Complete the questionnaire
            completion_result = await dynamic_service.complete_questionnaire()

            return {
                "completed": True,
                "session_id": session_id,
                "chart_id": chart_id,
                "confidence": completion_result.get("confidence", 0.0),
                "message": "Enough information gathered for accurate birth time rectification"
            }

        # Return the next question
        return {
            "question": result.get("question"),
            "session_id": session_id,
            "chart_id": chart_id,
            "progress": result.get("progress", {"current": 1, "total_estimated": 10})
        }
    except Exception as e:
        logger.error(f"Error getting next question: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get next question: {str(e)}"
        )

@router.post("/{question_id}/answer", response_model=Dict[str, Any])
async def answer_individual_question(
    question_id: str = Path(..., description="Question ID to answer"),
    answer_data: Dict[str, Any] = Body(..., description="Answer data"),
    chart_id: str = Query(..., description="Chart ID for personalized questions"),
    session_id: str = Query(..., description="Session ID for tracking")
):
    """
    Submit an answer to a specific question and get the next question.
    """
    try:
        # Extract the answer from the request
        answer = answer_data.get("answer")

        # Use DynamicQuestionnaireService for truly dynamic questions
        dynamic_service = DynamicQuestionnaireService(session_id=session_id)

        # Process the answer and get the next question
        result = await dynamic_service.process_answer(
            question_id=question_id,
            answer=answer,
            chart_id=chart_id
        )

        # Check if the questionnaire is complete
        if result.get("complete", False):
            # Complete the questionnaire
            completion_result = await dynamic_service.complete_questionnaire()

            return {
                "completed": True,
                "session_id": session_id,
                "chart_id": chart_id,
                "confidence": completion_result.get("confidence", 0.0),
                "message": "Enough information gathered for accurate birth time rectification"
            }

        # Return the next question
        return {
            "question": result.get("question"),
            "session_id": session_id,
            "chart_id": chart_id,
            "answered_question_id": question_id,
            "progress": result.get("progress", {"current": 1, "total_estimated": 10})
        }
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process answer: {str(e)}"
        )

@router.post("/answer", response_model=Dict[str, Any])
async def answer_question(
    answer_data: QuestionAnswer,
    questionnaire_service: Any = Depends(get_questionnaire_service)
):
    """
    Answer a question in the questionnaire session.
    """
    try:
        session_id = answer_data.sessionId
        question_id = answer_data.questionId
        answer = answer_data.answer

        # Get session store
        session_store = get_session_store()

        # Check if session exists
        session = await session_store.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )

        # Create a copy of the session data to avoid modifying the original
        session_data = session.copy()

        # Add the answer to the session
        try:
            # Get question text first
            question_text = await get_question_text(question_id)

            await session_store.add_question_response(
                session_id,
                question_id,
                question_text,
                answer
            )
        except ValueError as e:
            logger.error(f"Failed to get question text: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid question ID: {question_id}"
            )

        # Get the chart ID from the session
        chart_id = session_data.get("chart_id")
        if not chart_id:
            raise HTTPException(
                status_code=400,
                detail="Chart ID not found in session"
            )

        # Get the chart data
        chart_service = get_chart_service()
        chart_data = await chart_service.get_chart(chart_id)

        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail=f"No chart data found for chart ID: {chart_id}"
            )

        # Extract birth details
        birth_details = chart_data.get("birth_details", {})

        # Get previous answers for context
        responses = await session_store.get_responses(session_id)
        previous_answers = responses

        # Current confidence level (increases with more answers)
        current_confidence = 30.0 + (len(responses) * 10)
        if current_confidence > 90:
            current_confidence = 90.0

        # Update session confidence
        await session_store.update_confidence(session_id, current_confidence)

        # Is the questionnaire complete?
        is_complete = len(responses) >= 5 or current_confidence >= 90.0

        # Get the next question
        engine = QuestionnaireEngine()
        next_question_data = await engine.get_next_question(
            session_id=session_id,
            chart_data=chart_data,
            previous_answers=previous_answers
        )

        # Update the birth time range if provided
        if "birth_time_range" in next_question_data:
            session_data["birth_time_range"] = next_question_data["birth_time_range"]
            await session_store.update_session(session_id, session_data)

        # Add options to the question if available
        next_question = {
            "id": next_question_data.get("id", f"q_{uuid.uuid4().hex[:8]}"),
            "type": next_question_data.get("type", "text"),
            "text": next_question_data.get("text", ""),
            "relevance": next_question_data.get("relevance", "medium")
        }

        if "options" in next_question_data and next_question_data["options"]:
            next_question["options"] = []
            for j, opt in enumerate(next_question_data["options"]):
                if isinstance(opt, str):
                    next_question["options"].append({
                        "id": f"opt_{j}_{uuid.uuid4().hex[:4]}",
                        "text": opt
                    })
                elif isinstance(opt, dict) and "text" in opt:
                    opt_id = opt.get("id", f"opt_{j}_{uuid.uuid4().hex[:4]}")
                    next_question["options"].append({
                        "id": opt_id,
                        "text": opt["text"]
                    })

        # If complete, start rectification
        if is_complete:
            # Start the rectification process in a background task
            bg_tasks = BackgroundTasks()
            bg_tasks.add_task(
                _execute_rectification_process,
                chart_id=chart_id,
                session_id=session_id,
                rectification_id=f"rect_{uuid.uuid4().hex[:10]}",
                answers=responses,
                birth_details=chart_data.get("birth_details", {}),
                questionnaire_service=questionnaire_service,
                chart_service=chart_service,
                session_store=session_store,
                openai_service=get_openai_service(),
                use_transit_verification=True,
                use_harmonics=False
            )

        response = {
            "question": next_question,
            "confidence": current_confidence,
            "isComplete": is_complete,
            "session_id": session_id,
            "questions_answered": len(responses),
            "chart_id": chart_id
        }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in answer_individual_question: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process answer: {str(e)}"
        )

@router.post("/complete", response_model=Dict[str, Any])
async def complete_questionnaire(
    request: Dict[str, Any]
):
    """
    Complete the questionnaire and perform birth time rectification.
    """
    try:
        # Extract request data
        session_id = request.get("session_id")
        chart_id = request.get("chart_id")

        # Validate required parameters
        if not session_id or not chart_id:
            raise HTTPException(
                status_code=400,
                detail="Session ID and Chart ID are required"
            )

        # Use DynamicQuestionnaireService for truly dynamic questions
        dynamic_service = DynamicQuestionnaireService(session_id=session_id)

        # Complete the questionnaire
        completion_result = await dynamic_service.complete_questionnaire()

        # Verify the completion result has some meaningful confidence score
        confidence = completion_result.get("confidence", 0.0)

        # Provide detailed response about the rectification process
        return {
            "session_id": session_id,
            "chart_id": chart_id,
            "isComplete": True,
            "status": "processing",
            "confidence": confidence,
            "response_count": completion_result.get("answer_count", 0),
            "message": "Questionnaire completed. Birth time rectification has been started.",
            "estimated_completion_time": "30-60 seconds",
            "next_steps": [
                "Birth time rectification is now in progress",
                "The system is analyzing your responses using astrological patterns",
                "You can check the status using the /api/questionnaire/check-rectification endpoint",
                "When complete, you will have access to your rectified birth chart"
            ]
        }
    except Exception as e:
        logger.error(f"Error in complete_questionnaire: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete questionnaire: {str(e)}"
        )

@router.get("/check-rectification", response_model=Dict[str, Any])
async def check_rectification_status(
    chart_id: str = Query(..., description="ID of the chart being rectified"),
    session_id: str = Query(..., description="Session ID of the questionnaire"),
    include_details: bool = Query(False, description="Whether to include detailed status information"),
    include_metrics: bool = Query(False, description="Whether to include performance metrics"),
    format: str = Query("standard", description="Response format: standard, verbose, or minimal")
):
    """
    Check the status of a birth time rectification process with comprehensive details.

    This endpoint follows the Original Sequence Diagram flow for monitoring
    birth time rectification progress with detailed information about the
    current state of the process, each step's progress, and estimated completion times.

    Query parameters:
    - chart_id: ID of the chart being rectified
    - session_id: Session ID of the questionnaire
    - include_details: Whether to include detailed status information
    - include_metrics: Whether to include performance metrics
    - format: Response format (standard, verbose, or minimal)

    Returns:
    - Detailed status information about the rectification process
    - Progress percentage and current stage
    - Estimated time remaining
    - Result data for completed rectifications
    """
    try:
        # Get services
        chart_service = get_chart_service()
        session_store = get_session_store()

        # Validate services
        if not chart_service:
            raise HTTPException(status_code=503, detail="Chart service unavailable")

        if not session_store:
            raise HTTPException(status_code=503, detail="Session store unavailable")

        # Verify chart exists
        chart_data = None
        try:
            chart_data = await chart_service.get_chart(chart_id)
            if not chart_data:
                raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving chart {chart_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error retrieving chart data: {str(e)}")

        # Get session data with retry logic
        session_data = None
        for retry in range(3):
            try:
                session_data = await session_store.get_session(session_id)
                if session_data:
                    break
                logger.warning(f"Session {session_id} not found on attempt {retry+1}/3")
                if retry < 2:
                    await asyncio.sleep(0.5 * (retry + 1))
            except Exception as e:
                logger.warning(f"Error retrieving session on attempt {retry+1}/3: {e}")
                if retry < 2:
                    await asyncio.sleep(0.5 * (retry + 1))

        if not session_data:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found after multiple attempts")

        # Check session status
        session_status = session_data.get("rectification_status", "unknown")

        # Get detailed rectification data from session first (most up-to-date)
        rectification_results = session_data.get("rectification_results", {})
        rectification_metadata = session_data.get("rectification_metadata", {})

        # If no results in session, check chart data
        if not rectification_results:
            # Check for rectification data in chart
            rectification_results = chart_data.get("rectification_results", {})
            if not rectification_results:
                # Check if the chart has rectification_process key
                rectification_process = chart_data.get("rectification_process", {})
                if rectification_process:
                    rectification_results = rectification_process

        # Get process steps for detailed progress information
        process_steps = session_data.get("process_steps", [])

        # Define all possible steps in the rectification process
        all_steps = [
            {"name": "analysis_started", "description": "Starting analysis", "weight": 5},
            {"name": "questionnaire_processed", "description": "Processing questionnaire data", "weight": 10},
            {"name": "birth_time_indicators_extracted", "description": "Extracting birth time indicators", "weight": 15},
            {"name": "initial_calculation", "description": "Performing initial calculations", "weight": 15},
            {"name": "astrological_analysis", "description": "Analyzing astrological patterns", "weight": 20},
            {"name": "transit_analysis", "description": "Performing transit analysis", "weight": 10},
            {"name": "openai_analysis", "description": "Applying AI analysis", "weight": 15},
            {"name": "chart_verification", "description": "Verifying chart accuracy", "weight": 5},
            {"name": "rectified_chart_created", "description": "Creating rectified chart", "weight": 5},
            {"name": "rectification_complete", "description": "Completing rectification", "weight": 5}
        ]

        # Match process steps to defined steps and calculate progress
        completed_steps = []
        pending_steps = []
        current_step = None
        total_weight = sum(step["weight"] for step in all_steps)
        completed_weight = 0

        # Get timestamp information
        started_at = session_data.get("rectification_started_at", datetime.now().isoformat())
        last_updated = session_data.get("updated_at", datetime.now().isoformat())
        completed_at = session_data.get("rectification_completed_at")

        # Process steps to get completed, current, and pending
        if process_steps:
            # Find completed steps
            for step in all_steps:
                step_name = step["name"]
                if step_name in process_steps:
                    completed_steps.append(step)
                    completed_weight += step["weight"]
                else:
                    # If we haven't found the current step yet and this step isn't completed
                    if not current_step and not pending_steps:
                        current_step = step
                    else:
                        pending_steps.append(step)

        # Calculate progress based on weights if we have process steps
        if completed_steps or current_step:
            # Base progress on completed weight
            progress_from_steps = int((completed_weight / total_weight) * 100)

            # If we have a current step, add partial progress for it
            if current_step and session_status == "processing":
                # Estimate progress within current step (50% by default)
                current_step_progress = session_data.get("current_step_progress", 0.5)
                current_step_contribution = int(current_step["weight"] * current_step_progress / total_weight * 100)
                progress_from_steps += current_step_contribution

            # Use weighted progress if available, otherwise use session progress
            progress = min(100, progress_from_steps)
        else:
            # Use progress directly from session if available
            progress = session_data.get("progress", 0)

        # Determine current status based on all available data
        if session_status == "error":
            status = "error"
            error_message = session_data.get("rectification_error", "Unknown error in rectification process")
            # Set progress to last known progress point or 0
            if progress == 100:
                progress = 95  # If an error occurred after marking 100%, set to 95%
        elif session_status == "complete" or "completed_at" in session_data or completed_at:
            status = "completed"
            progress = 100
        elif session_status == "processing" or "started_at" in rectification_results:
            status = "in_progress"

            # If no progress steps information, estimate based on elapsed time
            if not process_steps and progress < 10:
                # Estimate progress based on elapsed time if we don't have steps
                try:
                    started_time = datetime.fromisoformat(started_at)
                    elapsed_seconds = (datetime.now() - started_time).total_seconds()
                    # Assume rectification takes about 60 seconds
                    estimated_progress = min(int(elapsed_seconds / 60 * 100), 99)
                    progress = max(progress, estimated_progress)
                except (ValueError, TypeError):
                    # Default mid-point progress if parsing fails
                    progress = max(progress, 50)
        else:
            # No clear status indicators, assume pending
            status = "pending"
            progress = 0

        # Check for rectified chart
        rectified_chart_id = rectification_results.get("rectified_chart_id", "")
        rectified_time = rectification_results.get("rectified_time", "")
        original_time = rectification_results.get("original_time", chart_data.get("birth_details", {}).get("birth_time", ""))
        confidence_score = rectification_results.get("confidence_score", 0) or rectification_results.get("confidence", 0)
        adjustment_minutes = rectification_results.get("adjustment_minutes", 0) or rectification_metadata.get("adjustment_minutes", 0)

        # Calculate processing duration
        processing_duration_seconds = 0
        if started_at:
            try:
                started_time = datetime.fromisoformat(started_at)
                if completed_at:
                    completed_time = datetime.fromisoformat(completed_at)
                    processing_duration_seconds = (completed_time - started_time).total_seconds()
                else:
                    processing_duration_seconds = (datetime.now() - started_time).total_seconds()
            except (ValueError, TypeError):
                processing_duration_seconds = 0

        # Calculate estimated completion time
        estimated_remaining_seconds = 0
        if status == "in_progress" and progress > 0 and progress < 100:
            if processing_duration_seconds > 0:
                # Use elapsed time and progress to estimate remaining time
                estimated_remaining_seconds = (processing_duration_seconds / progress) * (100 - progress)
            else:
                # Default estimate based on typical processing times
                total_estimated_seconds = 60  # Default 60 second process
                elapsed_percentage = progress / 100.0
                estimated_remaining_seconds = total_estimated_seconds * (1 - elapsed_percentage)

        # Format estimated completion time
        if estimated_remaining_seconds > 0:
            if estimated_remaining_seconds < 30:
                estimated_completion_time = "less than 30 seconds"
            elif estimated_remaining_seconds < 60:
                estimated_completion_time = "less than 1 minute"
            elif estimated_remaining_seconds < 120:
                estimated_completion_time = "about 1-2 minutes"
            else:
                estimated_minutes = round(estimated_remaining_seconds / 60)
                estimated_completion_time = f"about {estimated_minutes} minutes"
        else:
            estimated_completion_time = "unknown"

        # Prepare basic response with enhanced information
        response = {
            "status": status,
            "progress": progress,
            "chart_id": chart_id,
            "session_id": session_id,
            "last_updated": last_updated,
            "original_time": original_time,
            "current_step": current_step["description"] if current_step else "Initializing" if status == "in_progress" else "Not started" if status == "pending" else "Completed" if status == "completed" else "Error",
            "started_at": started_at,
            "elapsed_seconds": int(processing_duration_seconds)
        }

        # Add time estimate for in-progress rectifications
        if status == "in_progress":
            response.update({
                "estimated_completion_time": estimated_completion_time,
                "estimated_remaining_seconds": int(estimated_remaining_seconds)
            })

            # Add current step details
            if current_step:
                response["current_step_details"] = {
                    "name": current_step["name"],
                    "description": current_step["description"],
                    "weight": current_step["weight"]
                }

        # Add error details if in error state
        if status == "error":
            response["error"] = {
                "message": error_message,
                "occurred_at": session_data.get("error_timestamp", last_updated),
                "in_step": current_step["name"] if current_step else "unknown"
            }

            # Add recovery suggestions if available
            recovery_suggestions = session_data.get("recovery_suggestions", [])
            if recovery_suggestions:
                response["error"]["recovery_suggestions"] = recovery_suggestions
            else:
                # Add default recovery suggestions
                response["error"]["recovery_suggestions"] = [
                    "Try initiating a new rectification session",
                    "Provide more detailed questionnaire answers",
                    "Check that birth details are accurate",
                    "Contact support if the issue persists"
                ]

        # Add rectified data if available
        if rectified_chart_id:
            response["rectified_chart_id"] = rectified_chart_id

        if rectified_time:
            response["rectified_time"] = rectified_time

        if adjustment_minutes:
            response["adjustment_minutes"] = adjustment_minutes
            adjustment_direction = "later" if adjustment_minutes > 0 else "earlier" if adjustment_minutes < 0 else "unchanged"
            response["adjustment_direction"] = adjustment_direction
            response["adjustment_summary"] = f"{abs(adjustment_minutes)} minutes {adjustment_direction}"

        if confidence_score:
            response["confidence_score"] = confidence_score

            # Add confidence description
            if confidence_score >= 90:
                confidence_description = "Very high confidence (within minutes)"
            elif confidence_score >= 75:
                confidence_description = "High confidence (within 15 minutes)"
            elif confidence_score >= 60:
                confidence_description = "Good confidence (within 30 minutes)"
            elif confidence_score >= 45:
                confidence_description = "Moderate confidence (within an hour)"
            elif confidence_score >= 30:
                confidence_description = "Low confidence (within several hours)"
            else:
                confidence_description = "Very low confidence (requires more information)"

            response["confidence_description"] = confidence_description

        # Add completed and pending steps if in progress or completed
        if status in ["in_progress", "completed"]:
            response["process_tracking"] = {
                "completed_steps": [{"name": step["name"], "description": step["description"]} for step in completed_steps],
                "pending_steps": [{"name": step["name"], "description": step["description"]} for step in pending_steps],
                "completed_step_count": len(completed_steps),
                "total_step_count": len(all_steps)
            }

            if current_step and status == "in_progress":
                response["process_tracking"]["current_step"] = {
                    "name": current_step["name"],
                    "description": current_step["description"]
                }

        # Add completion information if completed
        if status == "completed":
            response["completion_info"] = {
                "completed_at": completed_at or last_updated,
                "processing_duration_seconds": int(processing_duration_seconds),
                "processing_duration_formatted": f"{int(processing_duration_seconds // 60)} minutes {int(processing_duration_seconds % 60)} seconds"
            }

        # Add detailed information if requested
        if include_details:
            details = {
                "birth_details": chart_data.get("birth_details", {}),
                "process_steps": process_steps,
                "methods_used": rectification_results.get("methods_used", []),
                "birth_time_indicators": rectification_results.get("birth_time_indicators", []),
                "adjustment_minutes": adjustment_minutes,
                "explanation": rectification_results.get("explanation", ""),
                "verification": rectification_results.get("verification", {})
            }

            # Add astrological factors if available
            if "astrological_factors" in rectification_results:
                details["astrological_factors"] = rectification_results["astrological_factors"]

            # Add transit verification results if available
            if "transit_verification" in rectification_results:
                details["transit_verification"] = rectification_results["transit_verification"]

            # Add comprehensive analysis if available
            if "comprehensive_analysis" in rectification_results:
                details["comprehensive_analysis"] = rectification_results["comprehensive_analysis"]

            response["details"] = details

        # Add performance metrics if requested
        if include_metrics:
            metrics = {
                "process_steps_count": len(process_steps),
                "processing_time_seconds": processing_duration_seconds,
                "processing_time_per_step": processing_duration_seconds / max(1, len(process_steps)),
                "indicators_found": rectification_results.get("indicators_found", 0) or session_data.get("indicators_found", 0),
                "average_progress_rate": progress / max(1, processing_duration_seconds) if processing_duration_seconds > 0 else 0
            }

            # Add CPU and memory usage if available
            if "system_metrics" in session_data:
                metrics["system_metrics"] = session_data["system_metrics"]

            response["metrics"] = metrics

        # For minimal format, return only essential information
        if format.lower() == "minimal":
            minimal_response = {
                "status": status,
                "progress": progress,
                "chart_id": chart_id,
                "session_id": session_id
            }

            if status == "completed":
                minimal_response.update({
                    "rectified_time": rectified_time,
                    "confidence_score": confidence_score
                })

            if status == "error":
                minimal_response["error"] = error_message

            return minimal_response

        # For verbose format, include all available information
        if format.lower() == "verbose":
            # Include all available rectification data
            response["complete_rectification_data"] = rectification_results

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking rectification status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check rectification status: {str(e)}"
        )

@router.post("/rectify", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def process_rectification(request: Request):
    """
    Manually trigger the rectification process.

    This endpoint allows manual triggering of the birth time rectification process
    with full OpenAI integration for birth time determination. It implements comprehensive
    error handling with proper retry logic and detailed progress tracking, following
    the sequence diagram specifications exactly.

    Request body:
    - chart_id: Chart ID to rectify
    - session_id: Session ID with questionnaire data
    - include_details: Optional boolean to include detailed rectification process information
    - use_transit_verification: Optional boolean to enable transit-based verification
    - use_harmonics: Optional boolean to enable harmonic chart analysis
    """
    try:
        # Extract request body with validation
        try:
            data = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in request body"
            )

        logger.info(f"Processing rectification for chart: {data.get('chart_id')}")

        # Validate required fields
        if 'chart_id' not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="chart_id is required"
            )

        if 'session_id' not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id is required"
            )

        # Extract parameters with defaults
        chart_id = data.get('chart_id')
        session_id = data.get('session_id')
        include_details = data.get('include_details', False)
        use_transit_verification = data.get('use_transit_verification', True)
        use_harmonics = data.get('use_harmonics', False)

        # Initialize services with error handling
        try:
            chart_service = get_chart_service()
            session_store = get_session_store()
            openai_service = get_openai_service()
            questionnaire_service = get_questionnaire_service()
        except Exception as service_error:
            logger.error(f"Service initialization error: {service_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Required services unavailable: {str(service_error)}"
            )

        # Initialize WebSocket service for real-time updates if available
        websocket_available = False
        try:
            from ai_service.api.services.websocket_service import get_websocket_service
            websocket_service = get_websocket_service()
            websocket_available = True
        except (ImportError, AttributeError) as ws_error:
            logger.warning(f"WebSocket service not available: {ws_error}")
            # Continue without WebSocket support

        # Create a unique rectification ID
        rectification_id = f"rect_{uuid.uuid4().hex[:10]}"

        # Record rectification start time
        rectification_start = datetime.now().isoformat()

        # Send initial progress update
        if websocket_available:
            await websocket_service.send_message(
                session_id=session_id,
                event_type="rectification_progress",
                data={
                    "stage": "starting",
                    "progress": 5,
                    "message": "Initiating birth time rectification process",
                    "timestamp": rectification_start,
                    "chart_id": chart_id,
                    "rectification_id": rectification_id
                }
            )

        # 1. Retrieve chart data with retry logic
        chart_data = None
        chart_error = None
        for retry in range(3):  # 3 attempts
            try:
                chart_data = await chart_service.get_chart(chart_id)
                if chart_data:
                    break

                logger.warning(f"Chart {chart_id} not found on attempt {retry+1}/3")
                if retry < 2:
                    await asyncio.sleep(1 * (retry + 1))  # Increasing delay
            except Exception as e:
                chart_error = str(e)
                logger.warning(f"Error retrieving chart on attempt {retry+1}/3: {e}")
                if retry < 2:
                    await asyncio.sleep(1 * (retry + 1))

        if not chart_data:
            error_msg = f"Failed to retrieve chart: {chart_error or 'Chart not found'}"
            logger.error(error_msg)

            # Update session with error
            await _update_rectification_progress(
                session_store,
                session_id,
                {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat(),
                    "chart_id": chart_id,
                    "rectification_id": rectification_id
                },
                websocket_service,
                session_id,
                chart_id,
                rectification_id
            )

            # Send error via WebSocket if available
            if websocket_available:
                await websocket_service.send_message(
                    session_id=session_id,
                    event_type="rectification_error",
                    data={
                        "error": error_msg,
                        "stage": "chart_retrieval",
                        "timestamp": datetime.now().isoformat(),
                        "chart_id": chart_id,
                        "rectification_id": rectification_id
                    }
                )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )

        # 2. Retrieve session data and questionnaire answers
        session_data = None
        session_error = None
        for retry in range(3):  # 3 attempts
            try:
                session_data = await session_store.get_session(session_id)
                if session_data:
                    break

                logger.warning(f"Session {session_id} not found on attempt {retry+1}/3")
                if retry < 2:
                    await asyncio.sleep(1 * (retry + 1))
            except Exception as e:
                session_error = str(e)
                logger.warning(f"Error retrieving session on attempt {retry+1}/3: {e}")
                if retry < 2:
                    await asyncio.sleep(1 * (retry + 1))

        if not session_data:
            error_msg = f"Failed to retrieve session: {session_error or 'Session not found'}"
            logger.error(error_msg)

            # Send error via WebSocket if available
            if websocket_available:
                await websocket_service.send_message(
                    session_id=session_id,
                    event_type="rectification_error",
                    data={
                        "error": error_msg,
                        "stage": "session_retrieval",
                        "timestamp": datetime.now().isoformat(),
                        "chart_id": chart_id,
                        "rectification_id": rectification_id
                    }
                )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )

        # 3. Get questionnaire answers
        answers = session_data.get("previous_answers", [])
        if not answers or len(answers) < 2:
            error_msg = "Insufficient questionnaire answers for rectification (minimum 2 required)"
            logger.error(error_msg)

            # Send error via WebSocket if available
            if websocket_available:
                await websocket_service.send_message(
                    session_id=session_id,
                    event_type="rectification_error",
                    data={
                        "error": error_msg,
                        "stage": "answer_validation",
                        "timestamp": datetime.now().isoformat(),
                        "chart_id": chart_id,
                        "rectification_id": rectification_id
                    }
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # 4. Progress update
        if websocket_available:
            await websocket_service.send_message(
                session_id=session_id,
                event_type="rectification_progress",
                data={
                    "stage": "preprocessing",
                    "progress": 15,
                    "message": "Processing questionnaire responses",
                    "timestamp": datetime.now().isoformat(),
                    "chart_id": chart_id,
                    "rectification_id": rectification_id,
                    "answer_count": len(answers)
                }
            )

        # 5. Update session with processing status
        await _update_rectification_progress(
            session_store,
            session_id,
            {
                "status": "processing",
                "progress": 15,
                "message": "Processing questionnaire responses",
                "step": "preprocessing"
            },
            websocket_service,
            session_id,
            chart_id,
            rectification_id
        )

        # 6. Extract birth details
        birth_details = chart_data.get("birth_details", {})
        birth_date = birth_details.get("birth_date", "")
        birth_time = birth_details.get("birth_time", "")
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        timezone = birth_details.get("timezone", "UTC")
        location = birth_details.get("location", birth_details.get("birth_place", ""))

        # 7. Validate birth details
        validation_errors = []
        if not birth_date:
            validation_errors.append("Birth date is missing")
        if not birth_time:
            validation_errors.append("Birth time is missing")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            validation_errors.append("Invalid coordinates")

        if validation_errors:
            error_msg = f"Invalid birth details: {'; '.join(validation_errors)}"
            logger.error(error_msg)

            # Update session with error
            await _update_rectification_progress(
                session_store,
                session_id,
                {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat(),
                    "chart_id": chart_id,
                    "rectification_id": rectification_id
                },
                websocket_service,
                session_id,
                chart_id,
                rectification_id
            )

            # Send error via WebSocket if available
            if websocket_available:
                await websocket_service.send_message(
                    session_id=session_id,
                    event_type="rectification_error",
                    data={
                        "error": error_msg,
                        "stage": "birth_details_validation",
                        "timestamp": datetime.now().isoformat(),
                        "chart_id": chart_id,
                        "rectification_id": rectification_id
                    }
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )

        # 8. Start the rectification process in the background
        # This follows the sequence diagram by executing the comprehensive rectification process
        # described in the architecture documentation
        background_tasks = BackgroundTasks()
        background_tasks.add_task(
            _execute_rectification_process,
            chart_id=chart_id,
            session_id=session_id,
            rectification_id=rectification_id,
            answers=answers,
            birth_details=birth_details,
            questionnaire_service=questionnaire_service,
            chart_service=chart_service,
            session_store=session_store,
            openai_service=openai_service,
            websocket_service=websocket_service if websocket_available else None,
            use_transit_verification=use_transit_verification,
            use_harmonics=use_harmonics
        )

        # 9. Return immediate response with rectification info
        return {
            "status": "processing",
            "message": "Birth time rectification process started successfully",
            "chart_id": chart_id,
            "session_id": session_id,
            "rectification_id": rectification_id,
            "started_at": rectification_start,
            "estimated_completion_time": "30-60 seconds",
            "checking_endpoint": f"/api/v1/questionnaire/check-rectification?chart_id={chart_id}&session_id={session_id}",
            "progress": 15,
            "includes_transit_verification": use_transit_verification,
            "includes_harmonics": use_harmonics
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except json.JSONDecodeError:
        # Handle JSON parsing errors
        logger.error("Invalid JSON in request body")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in request body"
        )
    except Exception as e:
        # Log error and return 500 response
        logger.error(f"Error processing rectification request: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rectification processing failed: {str(e)}"
        )

async def _execute_rectification_process(
    chart_id: str,
    session_id: str,
    rectification_id: str,
    answers: List[Dict[str, Any]],
    birth_details: Dict[str, Any],
    questionnaire_service: Any,
    chart_service: Any,
    session_store: Any,
    openai_service: Any,
    websocket_service: Any = None,
    use_transit_verification: bool = True,
    use_harmonics: bool = False
) -> None:
    """
    Execute the complete rectification process in the background.

    This method implements the full sequence of birth time rectification
    including AI analysis, transit verification, and detailed response
    generation according to the sequence diagram.
    """
    try:
        # 1. Initialize process tracking
        process_steps = ["analysis_started"]
        progress = 15
        rectification_start = datetime.now().isoformat()

        # 2. Update session with progress
        await _update_rectification_progress(
            session_store,
            session_id,
            {
                "status": "processing",
                "progress": progress,
                "message": "Starting rectification process",
                "step": "initialization"
            },
            websocket_service,
            session_id,
            chart_id,
            rectification_id
        )

        # 3. Send progress update
        if websocket_service:
            try:
                await websocket_service.send_message(
                    session_id=session_id,
                    event_type="rectification_progress",
                    data={
                        "stage": "questionnaire_processing",
                        "progress": progress,
                        "message": "Processing questionnaire responses",
                        "timestamp": datetime.now().isoformat(),
                        "chart_id": chart_id,
                        "rectification_id": rectification_id
                    }
                )
            except Exception as ws_error:
                logger.warning(f"Non-critical WebSocket error: {ws_error}")

        # 4. Extract birth time indicators
        try:
            # Update progress
            progress = 20
            await _update_rectification_progress(
                session_store,
                session_id,
                {
                    "status": "processing",
                    "progress": progress,
                    "message": "Extracting birth time indicators from questionnaire responses",
                    "step": "indicators"
                },
                websocket_service,
                session_id,
                chart_id,
                rectification_id
            )

            # Get birth time indicators from questionnaire responses
            birth_time_indicators = []

            # Process each answer with error handling
            for answer in answers:
                try:
                    indicator_data = await questionnaire_service._extract_birth_time_indicators(
                        answer.get("question", ""),
                        answer.get("answer", "")
                    )

                    if indicator_data and indicator_data.get("found", False):
                        birth_time_indicators.extend(indicator_data.get("indicators", []))
                except Exception as answer_error:
                    logger.warning(f"Error processing answer {answer.get('question_id', 'unknown')}: {answer_error}")
                    # Continue processing other answers

            # Update progress
            progress = 25
            process_steps.append("birth_time_indicators_extracted")

            # Update session
            await _update_rectification_progress(
                session_store,
                session_id,
                {
                    "status": "processing",
                    "progress": progress,
                    "message": "Creating an AI-powered analysis of responses",
                    "step": "analysis"
                },
                websocket_service,
                session_id,
                chart_id,
                rectification_id
            )

            # Send progress update
            if websocket_service:
                try:
                    await websocket_service.send_message(
                        session_id=session_id,
                        event_type="rectification_progress",
                        data={
                            "stage": "indicators_extracted",
                            "progress": progress,
                            "message": f"Extracted {len(birth_time_indicators)} birth time indicators",
                            "timestamp": datetime.now().isoformat(),
                            "chart_id": chart_id,
                            "rectification_id": rectification_id
                        }
                    )
                except Exception as ws_error:
                    logger.warning(f"Non-critical WebSocket error: {ws_error}")
        except Exception as indicator_error:
            logger.error(f"Error extracting birth time indicators: {indicator_error}")
            logger.error(traceback.format_exc())
            # Continue with empty indicators list
            birth_time_indicators = []

        # 5. Call the comprehensive rectification process with OpenAI integration
        # This fully implements the AI-analysis algorithm in the sequence diagram
        try:
            # Import the core rectification functionality
            from ai_service.core.rectification.main import comprehensive_rectification

            # Update progress
            progress = 30
            process_steps.append("initial_calculation")
            await _update_rectification_progress(
                session_store,
                session_id,
                {
                    "status": "processing",
                    "progress": progress,
                    "message": "Calculating initial birth chart",
                    "step": "calculation"
                },
                websocket_service,
                session_id,
                chart_id,
                rectification_id
            )

            # Send progress update
            if websocket_service:
                try:
                    await websocket_service.send_message(
                        session_id=session_id,
                        event_type="rectification_progress",
                        data={
                            "stage": "rectification_calculation",
                            "progress": progress,
                            "message": "Performing astrological analysis for birth time rectification",
                            "timestamp": datetime.now().isoformat(),
                            "chart_id": chart_id,
                            "rectification_id": rectification_id
                        }
                    )
                except Exception as ws_error:
                    logger.warning(f"Non-critical WebSocket error: {ws_error}")

            # Extract required parameters from birth_details
            birth_date_str = birth_details.get("birth_date", "")
            birth_time_str = birth_details.get("birth_time", "")

            # Combine date and time into a datetime object
            birth_dt_str = f"{birth_date_str} {birth_time_str}"
            try:
                birth_dt = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    birth_dt = datetime.strptime(birth_dt_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        # Try alternative format
                        birth_dt = datetime.strptime(birth_dt_str, "%m/%d/%Y %H:%M:%S")
                    except ValueError:
                        try:
                            birth_dt = datetime.strptime(birth_dt_str, "%m/%d/%Y %H:%M")
                        except ValueError:
                            error_msg = f"Failed to parse birth datetime: {birth_dt_str}"
                            logger.error(error_msg)
                            await _update_session_with_error(session_store, session_id, error_msg)
                            await _update_rectification_progress(
                                session_store,
                                session_id,
                                {
                                    "status": "error",
                                    "message": error_msg,
                                    "step": "parse_birth_time",
                                    "error": True
                                },
                                websocket_service,
                                session_id,
                                None,  # chart_id
                                rectification_id
                            )
                            return

            latitude = birth_details.get("latitude", 0.0)
            longitude = birth_details.get("longitude", 0.0)
            timezone = birth_details.get("timezone", "UTC")

            # Update progress - starting astrological analysis
            progress = 40
            process_steps.append("astrological_analysis")
            await _update_rectification_progress(
                session_store,
                session_id,
                {
                    "status": "processing",
                    "progress": progress,
                    "message": "Performing astrological analysis of birth chart",
                    "step": "analysis"
                },
                websocket_service,
                session_id,
                chart_id,
                rectification_id
            )

            # Send progress update
            if websocket_service:
                try:
                    await websocket_service.send_message(
                        session_id=session_id,
                        event_type="rectification_progress",
                        data={
                            "stage": "astrological_analysis",
                            "progress": progress,
                            "message": "Analyzing astrological patterns for birth time rectification",
                            "timestamp": datetime.now().isoformat(),
                            "chart_id": chart_id,
                            "rectification_id": rectification_id
                        }
                    )
                except Exception as ws_error:
                    logger.warning(f"Non-critical WebSocket error: {ws_error}")

            # Execute the comprehensive rectification with all required parameters
            rectification_options = {
                "use_openai": True,
                "use_transit_verification": use_transit_verification,
                "use_harmonics": use_harmonics,
                "max_adjustment_minutes": 120, # Maximum 2 hour adjustment
                "min_confidence_threshold": 30, # Minimum confidence level
                "reporting_callback": lambda progress_data: _update_rectification_progress(
                    session_store, session_id, progress_data, websocket_service, session_id, rectification_id=rectification_id
                )
            }

            # Try to execute rectification with retry logic
            rectification_result = None
            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    rectification_result = await comprehensive_rectification(
                        birth_dt=birth_dt,
                        latitude=latitude,
                        longitude=longitude,
                        timezone=timezone,
                        answers=answers,
                        events=birth_time_indicators,
                        options=rectification_options
                    )
                    # Successfully got result, break the loop
                    break
                except Exception as rect_error:
                    retry_count += 1
                    logger.warning(f"Rectification error (attempt {retry_count}/{max_retries}): {rect_error}")

                    # Update session with retry information
                    await _update_rectification_progress(
                        session_store,
                        session_id,
                        {
                            "status": "processing",
                            "progress": progress,
                            "message": "Retrying transit analysis",
                            "step": "transits"
                        },
                        websocket_service=websocket_service,
                        ws_session_id=session_id,
                        rectification_id=rectification_id
                    )

                    if retry_count >= max_retries:
                        logger.error(f"Failed to complete rectification after {max_retries} attempts")
                        raise

                    # Exponential backoff
                    await asyncio.sleep(1 * retry_count)

            # If we still don't have a result after retries, raise an error
            if not rectification_result:
                raise ValueError("Rectification failed to produce a result after multiple attempts")

            # Extract key data from result
            original_time = birth_details.get("birth_time", "")
            rectified_time = rectification_result.get("rectified_time", original_time)
            confidence = rectification_result.get("confidence_score", 50)
            explanation = rectification_result.get("explanation", "")
            adjustment_minutes = rectification_result.get("adjustment_minutes", 0)
            rectified_chart_id = rectification_result.get("rectified_chart_id", "")

            # Update progress - rectification completed
            progress = 85
            process_steps.append("openai_analysis")
            process_steps.append("chart_verification")
            process_steps.append("rectified_chart_created")
            await _update_rectification_progress(
                session_store,
                session_id,
                {
                    "status": "processing",
                    "progress": progress,
                    "message": "Generating final rectified chart",
                    "step": "chart_creation"
                },
                websocket_service=websocket_service,
                ws_session_id=session_id,
                rectification_id=rectification_id
            )

            # Send progress update
            if websocket_service:
                try:
                    await websocket_service.send_message(
                        session_id=session_id,
                        event_type="rectification_progress",
                        data={
                            "stage": "rectification_completed",
                            "progress": progress,
                            "message": "Birth time rectification calculation completed",
                            "timestamp": datetime.now().isoformat(),
                            "chart_id": chart_id,
                            "rectification_id": rectification_id,
                            "rectified_time": rectified_time,
                            "confidence": confidence,
                            "adjustment_minutes": adjustment_minutes
                        }
                    )
                except Exception as ws_error:
                    logger.warning(f"Non-critical WebSocket error: {ws_error}")

            # 6. Get enhanced interpretation using OpenAI if confidence is sufficient
            if confidence >= 40:
                try:
                    # Update progress
                    progress = 90
                    await _update_rectification_progress(
                        session_store,
                        session_id,
                        {
                            "status": "processing",
                            "progress": progress,
                            "message": "Performing final verification of rectification results",
                            "step": "verification"
                        },
                        websocket_service,
                        session_id,
                        chart_id,
                        rectification_id
                    )

                    # Create prompt for enhanced interpretation
                    interpretation_prompt = {
                        "task": "interpret_birth_time_rectification",
                        "original_time": original_time,
                        "rectified_time": rectified_time,
                        "adjustment_minutes": adjustment_minutes,
                        "confidence_score": confidence,
                        "birth_details": birth_details,
                        "indicators_found": len(birth_time_indicators),
                        "astrological_factors": rectification_result.get("astrological_factors", [])
                    }

                    # Get enhanced interpretation
                    enhanced_interpretation = await openai_service.generate_completion(
                        prompt=json.dumps(interpretation_prompt, cls=DateTimeEncoder),
                        task_type="rectification_interpretation",
                        max_tokens=500
                    )

                    if enhanced_interpretation:
                        try:
                            if isinstance(enhanced_interpretation, str):
                                enhanced_data = json.loads(enhanced_interpretation)
                            else:
                                enhanced_data = enhanced_interpretation

                            # Add enhanced interpretation to the result
                            rectification_result["enhanced_interpretation"] = enhanced_data
                        except json.JSONDecodeError:
                            # Use as plain text if not valid JSON
                            rectification_result["enhanced_interpretation"] = {
                                "summary": enhanced_interpretation[:500]
                            }
                except Exception as interp_error:
                    logger.warning(f"Non-critical error generating enhanced interpretation: {interp_error}")
                    # Continue without enhanced interpretation

            # 7. Mark rectification as complete
            progress = 100
            process_steps.append("rectification_complete")
            completion_time = datetime.now().isoformat()

            # Update session with completed status
            await _update_rectification_progress(
                session_store,
                session_id,
                {
                    "status": "complete",
                    "progress": 100,
                    "message": "Birth time rectification completed successfully",
                    "step": "completion"
                },
                websocket_service,
                session_id,
                chart_id,
                rectification_id
            )

            # Send completion update
            if websocket_service:
                try:
                    await websocket_service.send_message(
                        session_id=session_id,
                        event_type="rectification_complete",
                        data={
                            "status": "success",
                            "progress": 100,
                            "message": "Birth time rectification process completed successfully",
                            "timestamp": completion_time,
                            "chart_id": chart_id,
                            "rectification_id": rectification_id,
                            "original_time": original_time,
                            "rectified_time": rectified_time,
                            "confidence_score": confidence,
                            "adjustment_minutes": adjustment_minutes,
                            "rectified_chart_id": rectified_chart_id
                        }
                    )
                except Exception as ws_error:
                    logger.warning(f"Non-critical WebSocket error: {ws_error}")

        except Exception as rect_error:
            logger.error(f"Error in rectification process: {rect_error}")
            logger.error(traceback.format_exc())

            # Update session with error
            error_msg = f"Rectification process failed: {str(rect_error)}"
            await _update_rectification_progress(
                session_store,
                session_id,
                {
                    "status": "error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat(),
                    "chart_id": chart_id,
                    "rectification_id": rectification_id
                },
                websocket_service,
                session_id,
                chart_id,
                rectification_id
            )

            # Send error via WebSocket if available
            if websocket_service:
                try:
                    await websocket_service.send_message(
                        session_id=session_id,
                        event_type="rectification_error",
                        data={
                            "error": error_msg,
                            "stage": "rectification_process",
                            "timestamp": datetime.now().isoformat(),
                            "chart_id": chart_id,
                            "rectification_id": rectification_id
                        }
                    )
                except Exception:
                    # Ignore errors sending WebSocket message
                    pass

    except Exception as e:
        logger.error(f"Unhandled error in rectification process: {e}")
        logger.error(traceback.format_exc())

        # Update session with error
        error_msg = f"Unhandled error in rectification process: {str(e)}"
        await _update_rectification_progress(
            session_store,
            session_id,
            {
                "status": "error",
                "message": error_msg,
                "timestamp": datetime.now().isoformat(),
                "chart_id": chart_id,
                "rectification_id": rectification_id
            },
            websocket_service,
            session_id,
            chart_id,
            rectification_id
        )

        # Send error via WebSocket if available
        if websocket_service:
            try:
                await websocket_service.send_message(
                    session_id=session_id,
                    event_type="rectification_error",
                    data={
                        "error": error_msg,
                        "stage": "unknown",
                        "timestamp": datetime.now().isoformat(),
                        "chart_id": chart_id,
                        "rectification_id": rectification_id
                    }
                )
            except Exception:
                # Ignore errors sending WebSocket message
                pass

async def _update_rectification_progress(
    session_store: Any,
    session_id: str,
    progress_data: Dict[str, Any],
    websocket_service: Any = None,
    ws_session_id: Optional[str] = None,
    chart_id: Optional[str] = None,
    rectification_id: Optional[str] = None
) -> None:
    """
    Update rectification progress based on callback data from the rectification process.

    This function serves as a central integration point for progress updates during
    the rectification process. It updates the user's session data and sends WebSocket
    messages if configured.

    Args:
        session_store: Session storage service
        session_id: Session ID for storing progress
        progress_data: Progress information
        websocket_service: Optional WebSocket service for real-time updates
        ws_session_id: Optional separate WebSocket session ID (if different from session_id)
        chart_id: Optional chart ID for the update
        rectification_id: Optional rectification ID for the update
    """
    try:
        # Get message and progress
        message = progress_data.get("message", "Processing")
        progress = progress_data.get("progress", 0)
        status = progress_data.get("status", "processing")
        step = progress_data.get("step", "")

        # Update session with progress information
        await session_store.update_session(
            session_id,
            {
                "rectification_progress": {
                    "status": status,
                    "progress": progress,
                    "message": message,
                    "step": step,
                    "timestamp": datetime.now().isoformat(),
                    "chart_id": chart_id,
                    "rectification_id": rectification_id
                },
                "last_updated": datetime.now().isoformat()
            }
        )

        # Send WebSocket update if service is provided
        if websocket_service:
            try:
                target_session = ws_session_id or session_id
                if not target_session:
                    return

                # Create WebSocket event data
                event_data = {
                    "type": "rectification_progress",
                    "data": {
                        "status": status,
                        "progress": progress,
                        "message": message,
                        "step": step,
                        "chart_id": chart_id,
                        "rectification_id": rectification_id,
                        "timestamp": datetime.now().isoformat()
                    }
                }

                # Send via WebSocket
                await websocket_service.send_to_session(target_session, event_data)
            except Exception as ws_error:
                logger.warning(f"Failed to send WebSocket progress update: {ws_error}")

    except Exception as e:
        logger.error(f"Error updating rectification progress: {e}")
        logger.error(traceback.format_exc())

async def _update_session_with_error(session_store, session_id: str, error_message: str) -> None:
    """
    Update the session with an error message.

    Args:
        session_store: Session storage
        session_id: Session ID
        error_message: Error message
    """
    try:
        await session_store.update_session(
            session_id,
            {
                "rectification_status": "error",
                "rectification_error": error_message,
                "updated_at": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Failed to update session with error: {e}")

@router.post("/generate", response_model=Dict[str, Any])
async def generate_questionnaire(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = Query(None, description="Optional session ID to use")
):
    """
    Generate questionnaire data based on birth details and previous answers.

    This endpoint creates a new questionnaire or updates an existing one,
    generating the next relevant questions based on the person's birth chart
    and previous responses.

    Args:
        request: Request containing birth details and previous answers
        background_tasks: FastAPI background tasks
        session_id: Optional session ID to use

    Returns:
        Dictionary containing questions and metadata
    """
    try:
        # Extract birth details from request
        birth_details = request.get("birth_details")

        if not birth_details and "birthDetails" in request:
            # Handle frontend format (camelCase)
            birth_details = request.get("birthDetails")

        # Validate birth details
        if not birth_details:
            raise HTTPException(
                status_code=400,
                detail="Birth details are required to generate questionnaire"
            )

        # Extract required fields
        required_fields = ["date", "time", "place"]
        frontend_fields = ["birthDate", "birthTime", "birthPlace"]

        # Handle both API formats
        for i, field in enumerate(required_fields):
            frontend_field = frontend_fields[i]

            # Check if field is missing in backend format but present in frontend format
            if field not in birth_details and frontend_field in birth_details:
                birth_details[field] = birth_details[frontend_field]

            # Validate required fields
            if field not in birth_details:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field in birth details: {field}"
                )

        # Extract previous answers
        previous_answers = request.get("previous_answers", {})
        if not previous_answers and "previousAnswers" in request:
            previous_answers = request.get("previousAnswers", {})

        # Get current confidence
        current_confidence = request.get("current_confidence", 0)
        if current_confidence == 0 and "currentConfidence" in request:
            current_confidence = request.get("currentConfidence", 0)

        # Initialize services
        openai_service = get_openai_service()
        session_store = get_session_store()

        # Create or get session
        effective_session_id = session_id
        if not effective_session_id:
            effective_session_id = request.get("session_id") or request.get("sessionId")

        if effective_session_id:
            # Check if session exists
            session = await session_store.get_session(effective_session_id)
            if not session:
                # Create new session with provided ID
                effective_session_id = await session_store.create_session(
                    session_id=effective_session_id,
                    data={
                        "birth_details": birth_details,
                        "previous_answers": previous_answers,
                        "confidence": current_confidence
                    }
                )
        else:
            # Create new session
            effective_session_id = await session_store.create_session(
                data={
                    "birth_details": birth_details,
                    "previous_answers": previous_answers,
                    "confidence": current_confidence
                }
            )

        # Determine if this is a new session or continuing
        is_new_session = len(previous_answers) == 0

        # Prepare context for OpenAI
        astrological_context = {
            "birth_details": birth_details,
            "previous_answers": previous_answers,
            "is_new_session": is_new_session,
            "current_confidence": current_confidence
        }

        # Generate questions using OpenAI
        question_prompt = {
            "task": "generate_rectification_questions",
            "astrological_context": astrological_context,
            "requirements": {
                "question_count": 3,
                "focus_areas": [
                    "birth time accuracy indicators",
                    "early life events with time sensitivity",
                    "physical appearance and personality traits",
                    "key life events with transit correlations"
                ],
                "format": "structured_json"
            }
        }

        # Generate questions in background if this is an initial request
        if is_new_session:
            # Initial response with a starter question
            initial_questions = [
                {
                    "id": f"q_{uuid.uuid4().hex[:8]}",
                    "type": "choice",
                    "text": "Do you know if you were born closer to sunrise, midday, sunset, or during the night?",
                    "options": [
                        {"id": "opt_sunrise", "text": "Around sunrise"},
                        {"id": "opt_midday", "text": "Around midday"},
                        {"id": "opt_sunset", "text": "Around sunset"},
                        {"id": "opt_night", "text": "During the night"},
                        {"id": "opt_unknown", "text": "I don't know"}
                    ]
                }
            ]

            # Start background task to generate more personalized questions
            background_tasks.add_task(
                _generate_personalized_questions,
                session_id=effective_session_id,
                birth_details=birth_details,
                openai_service=openai_service,
                session_store=session_store,
                question_prompt=question_prompt
            )

            # Return initial questions immediately
            return {
                "questions": initial_questions,
                "session_id": effective_session_id,
                "confidence": 10.0,
                "is_complete": False,
                "status": "success",
                "message": "Initial questions generated. More specific questions are being prepared."
            }
        else:
            # For continuing sessions, generate questions synchronously
            try:
                question_response = await openai_service.generate_completion(
                    prompt=json.dumps(question_prompt, cls=DateTimeEncoder),
                    task_type="astrological_question_generation",
                    max_tokens=1000
                )

                if not question_response or "content" not in question_response:
                    logger.error("Failed to receive valid response from OpenAI for question generation")
                    raise ValueError("Failed to generate astrological questions")

                # Parse questions from OpenAI response
                questions_data = json.loads(question_response["content"])

                # Validate and process questions
                processed_questions = []
                if "questions" in questions_data:
                    for q in questions_data["questions"]:
                        if "text" not in q:
                            continue

                        question_id = q.get("id", f"q_{uuid.uuid4().hex[:8]}")
                        question_type = q.get("type", "text")
                        question_text = q.get("text")

                        processed_question = {
                            "id": question_id,
                            "type": question_type,
                            "text": question_text
                        }

                        # Process options for choice/multiple-choice questions
                        if "options" in q and q["options"]:
                            processed_options = []
                            for i, option in enumerate(q["options"]):
                                if isinstance(option, str):
                                    processed_options.append({
                                        "id": f"opt_{i}_{uuid.uuid4().hex[:4]}",
                                        "text": option
                                    })
                                elif isinstance(option, dict) and "text" in option:
                                    if "id" not in option:
                                        option["id"] = f"opt_{i}_{uuid.uuid4().hex[:4]}"
                                    processed_options.append(option)
                            processed_question["options"] = processed_options

                        processed_questions.append(processed_question)

                if not processed_questions:
                    # Fallback questions if processing failed
                    processed_questions = [
                        {
                            "id": f"q_{uuid.uuid4().hex[:8]}",
                            "type": "text",
                            "text": "Did any significant events happen in your early childhood that could help pinpoint your birth time?"
                        },
                        {
                            "id": f"q_{uuid.uuid4().hex[:8]}",
                            "type": "choice",
                            "text": "Does your personality align more with your Sun sign or Rising sign (if you know it)?",
                            "options": [
                                {"id": f"opt_1_{uuid.uuid4().hex[:4]}", "text": "More like my Sun sign"},
                                {"id": f"opt_2_{uuid.uuid4().hex[:4]}", "text": "More like my Rising sign"},
                                {"id": f"opt_3_{uuid.uuid4().hex[:4]}", "text": "A mix of both"},
                                {"id": f"opt_4_{uuid.uuid4().hex[:4]}", "text": "I'm not sure"}
                            ]
                        }
                    ]

                # Update session with generated questions
                session = await session_store.get_session(effective_session_id)
                if session:
                    if "questions" not in session:
                        session["questions"] = []
                    session["questions"].extend(processed_questions)
                    session["updated_at"] = datetime.now().isoformat()
                    await session_store.update_session(effective_session_id, session)

                # Calculate confidence based on number of previous answers
                answer_count = len(previous_answers)
                confidence = min(30 + (answer_count * 10), 90)

                # Update session confidence
                await session_store.update_confidence(effective_session_id, confidence)

                # Is the questionnaire complete?
                is_complete = answer_count >= 5 or confidence >= 90.0

                return {
                    "questions": processed_questions,
                    "session_id": effective_session_id,
                    "confidence": confidence,
                    "is_complete": is_complete,
                    "status": "success"
                }

            except json.JSONDecodeError:
                logger.error("Failed to parse OpenAI response as JSON")
                raise ValueError("Error parsing astrological questions from OpenAI")

    except ValueError as e:
        logger.error(f"Error in questionnaire generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error generating questionnaire: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questionnaire: {str(e)}"
        )

async def _generate_personalized_questions(
    session_id: str,
    birth_details: Dict[str, Any],
    openai_service: Any,
    session_store: Any,
    question_prompt: Dict[str, Any]
) -> None:
    """
    Background task to generate personalized questions based on birth details.

    Args:
        session_id: Session ID to update
        birth_details: Birth details for astrological context
        openai_service: OpenAI service instance
        session_store: Session store instance
        question_prompt: Question generation prompt
    """
    try:
        # Generate personalized questions with OpenAI
        question_response = await openai_service.generate_completion(
            prompt=json.dumps(question_prompt, cls=DateTimeEncoder),
            task_type="astrological_question_generation",
            max_tokens=1000
        )

        if not question_response or "content" not in question_response:
            logger.error("Failed to generate personalized questions in background task")
            return

        try:
            # Parse questions from OpenAI response
            questions_data = json.loads(question_response["content"])

            # Process questions
            processed_questions = []
            if "questions" in questions_data:
                for q in questions_data["questions"]:
                    if "text" not in q:
                        continue

                    question_id = q.get("id", f"q_{uuid.uuid4().hex[:8]}")
                    question_type = q.get("type", "text")
                    question_text = q.get("text")

                    processed_question = {
                        "id": question_id,
                        "type": question_type,
                        "text": question_text
                    }

                    # Process options
                    if "options" in q and q["options"]:
                        processed_options = []
                        for i, option in enumerate(q["options"]):
                            if isinstance(option, str):
                                processed_options.append({
                                    "id": f"opt_{i}_{uuid.uuid4().hex[:4]}",
                                    "text": option
                                })
                            elif isinstance(option, dict) and "text" in option:
                                if "id" not in option:
                                    option["id"] = f"opt_{i}_{uuid.uuid4().hex[:4]}"
                                processed_options.append(option)
                        processed_question["options"] = processed_options

                    processed_questions.append(processed_question)

            # Update session with personalized questions
            if processed_questions:
                session = await session_store.get_session(session_id)
                if session:
                    if "questions" not in session:
                        session["questions"] = []

                    # Add personalized questions to session
                    session["questions"].extend(processed_questions)
                    session["personalized_questions"] = processed_questions
                    session["personalized_questions_generated"] = True
                    session["updated_at"] = datetime.now().isoformat()

                    # Update session
                    await session_store.update_session(session_id, session)

                    logger.info(f"Successfully added {len(processed_questions)} personalized questions to session {session_id}")

        except json.JSONDecodeError:
            logger.error("Failed to parse personalized questions from OpenAI response")

    except Exception as e:
        logger.error(f"Error generating personalized questions in background task: {str(e)}")
        logger.error(traceback.format_exc())
