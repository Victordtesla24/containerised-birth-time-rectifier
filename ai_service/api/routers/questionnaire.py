"""
Questionnaire router for the Birth Time Rectifier API.
Handles all questionnaire and AI analysis related endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging
import uuid
import asyncio
import traceback

from ai_service.utils.questionnaire_engine import QuestionnaireEngine
from ai_service.models.unified_model import UnifiedRectificationModel
from ai_service.core.astro_calculator import AstroCalculator
from ai_service.api.services.questionnaire_service import get_questionnaire_service
from ai_service.api.services.chart import get_chart_service
from ai_service.utils.geocoding import get_coordinates
from ai_service.api.services.session_service import get_session_store
from ai_service.core.rectification import comprehensive_rectification

# Configure logging
logger = logging.getLogger(__name__)

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
    return AstroCalculator()

# Use the real session_store for all session-related operations
from ai_service.api.services.session_service import get_session_store

@router.get("", response_model=Dict[str, Any])
async def get_questionnaire(
    chart_id: str = Query(None, description="Chart ID for personalized questions"),
    session_id: str = Query(None, description="Session ID for tracking"),
    questionnaire_service = Depends(get_questionnaire_service)
):
    """
    Get the questionnaire questions tailored to the chart data.
    """
    try:
        # Initialize a response structure
        response = {
            "questions": [],
            "chart_id": chart_id,
            "session_id": session_id
        }

        # Get chart data using the chart service
        chart_service = get_chart_service()

        if not chart_id:
            # No chart ID provided, we can't proceed
            raise HTTPException(
                status_code=400,
                detail="Chart ID is required to generate personalized questions"
            )

        logger.info(f"Retrieving chart data for chart ID: {chart_id}")
        chart_data = await chart_service.get_chart(chart_id)

        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail=f"No chart data found for chart ID: {chart_id}"
            )

        logger.info(f"Successfully retrieved chart data with chart ID: {chart_id}")

        # Extract birth details for question generation
        birth_details = chart_data.get("birth_details", {})
        if not birth_details:
            raise HTTPException(
                status_code=400,
                detail="Birth details not found in chart data"
            )

        # Create a new session ID if none provided
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            response["session_id"] = session_id

        # Generate dynamic questions using questionnaire service
        engine = QuestionnaireEngine()

        # Initialize with OpenAI service
        from ai_service.api.services.openai import get_openai_service
        engine.openai_service = get_openai_service()

        # Generate 5 questions dynamically
        questions = []
        previous_answers = {"responses": []}

        # Get the first question
        first_question_data = await engine.get_first_question(chart_data, birth_details)
        first_question = {
            "id": first_question_data.get("id", f"q_{uuid.uuid4().hex[:8]}"),
            "type": first_question_data.get("type", "yes_no"),
            "text": first_question_data.get("text"),
            "relevance": first_question_data.get("relevance", "high"),
        }

        # Add options if available
        if "options" in first_question_data and first_question_data["options"]:
            first_question["options"] = []
            for j, opt in enumerate(first_question_data["options"]):
                if isinstance(opt, str):
                    first_question["options"].append({
                        "id": f"opt_{j}_{uuid.uuid4().hex[:4]}",
                        "text": opt
                    })
                elif isinstance(opt, dict) and "text" in opt:
                    opt_id = opt.get("id", f"opt_{j}_{uuid.uuid4().hex[:4]}")
                    first_question["options"].append({
                        "id": opt_id,
                        "text": opt["text"]
                    })

        questions.append(first_question)

        # Add to previous answers to avoid duplicates
        previous_answers["responses"].append({
            "question_id": first_question["id"],
            "question": first_question["text"],
            "answer": None
        })

        # Generate the rest of the questions
        for i in range(1, 5):  # Generate 4 more questions
            question_data = await engine.get_next_question(
                chart_data=chart_data,
                birth_details=birth_details,
                previous_answers=previous_answers,
                current_confidence=30.0 + (i * 10)  # Increasing confidence
            )

            question = {
                "id": question_data.get("id", f"q_{uuid.uuid4().hex[:8]}"),
                "type": question_data.get("type", "yes_no"),
                "text": question_data.get("text"),
                "relevance": question_data.get("relevance", "medium"),
            }

            # Add options if available
            if "options" in question_data and question_data["options"]:
                question["options"] = []
                for j, opt in enumerate(question_data["options"]):
                    if isinstance(opt, str):
                        question["options"].append({
                            "id": f"opt_{j}_{uuid.uuid4().hex[:4]}",
                            "text": opt
                        })
                    elif isinstance(opt, dict) and "text" in opt:
                        opt_id = opt.get("id", f"opt_{j}_{uuid.uuid4().hex[:4]}")
                        question["options"].append({
                            "id": opt_id,
                            "text": opt["text"]
                        })

            questions.append(question)

            # Add to previous answers to avoid duplicates
            previous_answers["responses"].append({
                "question_id": question["id"],
                "question": question["text"],
                "answer": None
            })

        response["questions"] = questions
        logger.info(f"Generated {len(response['questions'])} personalized questions based on chart data")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error in get_questionnaire: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate questions: {str(e)}"
        )

@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_questionnaire(
    request: Dict[str, Any],
    chart_id: Optional[str] = Query(None, description="Chart ID for personalized questions"),
    session_id: Optional[str] = Query(None, description="Session ID for continuing an existing session"),
    questionnaire_service: Any = Depends(get_questionnaire_service)
):
    """
    Initialize a questionnaire session with the first question.
    Create a new session or use an existing one.
    """
    try:
        session_store = get_session_store()

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

        # Get the first/next question
        session = await session_store.get_session(effective_session_id)
        previous_answers = {"responses": session.get("responses", []) if session else []}

        next_question_data = await questionnaire_service.generate_next_question(
            birth_details=birth_details,
            previous_answers=previous_answers
        )

        # Handle errors in question generation
        if "error" in next_question_data:
            return {
                "error": next_question_data.get("error"),
                "message": next_question_data.get("message", "Failed to generate question"),
                "sessionId": effective_session_id
            }

        # Extract the question and update the response
        next_question = next_question_data.get("next_question", {})
        confidence = next_question_data.get("confidence", 20.0)

        # Update session confidence
        await session_store.update_confidence(effective_session_id, confidence)

        return {
            "question": next_question,
            "sessionId": effective_session_id,
            "confidence": confidence,
            "isComplete": confidence >= 80.0
        }

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
    birth_details: Dict[str, Any],
    previous_answers: List[Dict[str, Any]],
    questionnaire_service: Any = Depends(get_questionnaire_service)
):
    """
    Generate the next most relevant question based on birth details and previous answers.

    Args:
        birth_details: Dictionary containing birth date, time, location
        previous_answers: List of previous question-answer pairs

    Returns:
        Dictionary containing the next question and metadata
    """
    try:
        # Validate input data
        if not birth_details:
            raise HTTPException(
                status_code=400,
                detail="Birth details are required"
            )

        # Generate the next question using the questionnaire service
        next_question = await questionnaire_service.generate_next_question(
            birth_details, previous_answers
        )

        return next_question
    except Exception as e:
        logger.error(f"Error generating next question: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating next question: {str(e)}")

@router.post("/{question_id}/answer", response_model=Dict[str, Any])
async def answer_individual_question(
    question_id: str = Path(..., description="Question ID to answer"),
    answer_data: Dict[str, Any] = Body(..., description="Answer data"),
    chart_id: str = Query(..., description="Chart ID for personalized questions"),
    session_id: str = Query(..., description="Session ID for tracking"),
    questionnaire_service: Any = Depends(get_questionnaire_service)
):
    """
    Answer an individual question in the questionnaire.
    """
    try:
        # Get questionnaire engine
        engine = QuestionnaireEngine()

        # Initialize session store
        session_store = get_session_store()

        # Check if session exists
        session = await session_store.get_session(session_id)
        if not session:
            # Create a new session if it doesn't exist
            await session_store.create_session(session_id, {
                "chart_id": chart_id,
                "answers": {},
                "questions_asked": set(),
                "confidence": 30.0,
                "birth_time_range": None,
                "last_question": None,
            })
            session = await session_store.get_session(session_id)
            if not session:
                # If still not available, raise an error
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create or retrieve session"
                )

        # Ensure session has necessary fields
        session_data = session.copy()  # Create a copy to avoid modifying the original
        if "answers" not in session_data:
            session_data["answers"] = {}
        if "questions_asked" not in session_data:
            session_data["questions_asked"] = set()

        # Record this answer
        answer_value = answer_data.get("answer")
        question_text = answer_data.get("question", "")

        await session_store.add_question_response(
            session_id,
            question_id,
            question_text,
            answer_value
        )

        # Get existing answers for context
        previous_answers = []
        for q_id, ans in session_data.get("answers", {}).items():
            previous_answers.append({
                "question_id": q_id,
                "question": ans.get("question", ""),
                "answer": ans.get("answer")
            })

            # Track questions asked to avoid duplicates
            if "question" in ans:
                if not isinstance(session_data.get("questions_asked"), set):
                    session_data["questions_asked"] = set()
                session_data["questions_asked"].add(ans["question"])

        # Add the current answer
        previous_answers.append({
            "question_id": question_id,
            "question": question_text,
            "answer": answer_value
        })

        # Get chart data to generate more questions
        chart_service = get_chart_service()
        chart_data = await chart_service.get_chart(chart_id)

        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail=f"No chart data found for chart ID: {chart_id}"
            )

        # Extract birth details
        birth_details = chart_data.get("birth_details", {})
        if not birth_details:
            raise HTTPException(
                status_code=400,
                detail="Birth details not found in chart data"
            )

        # Current confidence level (increases with more answers)
        current_confidence = 30.0 + (len(previous_answers) * 10)
        if current_confidence > 90:
            current_confidence = 90.0

        # Update session confidence
        await session_store.update_confidence(session_id, current_confidence)

        # Get the next question
        next_question_data = await engine.get_next_question(
            chart_data=chart_data,
            birth_details=birth_details,
            previous_answers={"responses": previous_answers},
            current_confidence=current_confidence
        )

        # Update session with birth time range if provided
        if "birth_time_range" in next_question_data:
            session_data["birth_time_range"] = next_question_data["birth_time_range"]
            await session_store.update_session(session_id, session_data)

        # Prepare the next question, avoiding duplicates
        questions_asked = session_data.get("questions_asked", set())
        next_question = None

        # Try up to 3 times to get a non-duplicate question
        for _ in range(3):
            if next_question_data.get("text") not in questions_asked:
                next_question = {
                    "id": next_question_data.get("id", f"q_{uuid.uuid4().hex[:8]}"),
                    "type": next_question_data.get("type", "open_text"),
                    "text": next_question_data.get("text"),
                    "relevance": next_question_data.get("relevance", "medium"),
                }

                # Add options if available
                if "options" in next_question_data and next_question_data["options"]:
                    next_question["options"] = []
                    for j, opt in enumerate(next_question_data["options"]):
                        next_question["options"].append({
                            "id": f"opt_{j}_{uuid.uuid4().hex[:4]}",
                            "text": opt
                        })
                break
            else:
                # If duplicate, get another question
                next_question_data = await engine.get_next_question(
                    chart_data=chart_data,
                    birth_details=birth_details,
                    previous_answers={"responses": previous_answers},
                    current_confidence=current_confidence
                )

        # If we couldn't get a non-duplicate question, use the last one
        if not next_question and next_question_data:
            next_question = {
                "id": next_question_data.get("id", f"q_{uuid.uuid4().hex[:8]}"),
                "type": next_question_data.get("type", "open_text"),
                "text": next_question_data.get("text"),
                "relevance": next_question_data.get("relevance", "medium"),
            }

        # Track the current question in the session
        session_data["last_question"] = next_question

        # Add this question to the set of questions asked
        if next_question and "text" in next_question:
            if not isinstance(session_data.get("questions_asked"), set):
                session_data["questions_asked"] = set()
            session_data["questions_asked"].add(next_question.get("text", ""))

        # Update session
        await session_store.update_session(session_id, session_data)

        # Is the questionnaire complete?
        is_complete = len(previous_answers) >= 5 or current_confidence >= 90.0

        # Birth time range for chart updates (if available)
        birth_time_range = session_data.get("birth_time_range")

        # Return the response with the next question
        if is_complete:
            # If we have enough questions or high confidence, start rectification process
            asyncio.create_task(process_rectification(chart_id, session_id, previous_answers))

        response = {
            "question": next_question,
            "confidence": current_confidence,
            "isComplete": is_complete,
            "session_id": session_id,
            "questions_answered": len(previous_answers),
            "birth_time_range": birth_time_range,
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
        await session_store.add_question_response(
            session_id,
            question_id,
            question_id,  # Using question_id as question text as a fallback
            answer
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
        previous_answers = {"responses": responses}

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
            chart_data=chart_data,
            birth_details=birth_details,
            previous_answers=previous_answers,
            current_confidence=current_confidence
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
            # Start the rectification process
            asyncio.create_task(process_rectification(chart_id, session_id, responses))

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
        logger.error(f"Error in answer_question: {str(e)}")
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
        session_id = request.get("session_id")
        chart_id = request.get("chart_id")

        if not session_id or not chart_id:
            raise HTTPException(
                status_code=400,
                detail="Session ID and Chart ID are required"
            )

        # Get session store
        session_store = get_session_store()

        # Check if session exists
        session = await session_store.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )

        # Get responses from the session
        responses = await session_store.get_responses(session_id)

        # Start the rectification process
        asyncio.create_task(process_rectification(chart_id, session_id, responses))

        current_confidence = await session_store.get_confidence(session_id)

        return {
            "session_id": session_id,
            "chart_id": chart_id,
            "isComplete": True,
            "confidence": current_confidence,
            "message": "Questionnaire completed. Birth time rectification has been started."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in complete_questionnaire: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to complete questionnaire: {str(e)}"
        )

# Check if a chart has rectified birth time
@router.get("/check-rectification", response_model=Dict[str, Any])
async def check_rectification(
    chart_id: str = Query(..., description="Chart ID to check"),
    session_id: str = Query(..., description="Session ID for the rectification process")
):
    """
    Check if birth time rectification has been completed for a chart.
    """
    try:
        # Get the chart service
        chart_service = get_chart_service()

        # Get chart data
        chart_data = await chart_service.get_chart(chart_id)
        if not chart_data:
            raise HTTPException(
                status_code=404,
                detail=f"Chart not found with ID: {chart_id}"
            )

        # Check if rectification results exist
        rectification_results = chart_data.get("rectification_results", {})
        is_rectified = bool(rectification_results)

        # Get original and rectified times if available
        birth_details = chart_data.get("birth_details", {})
        original_time = birth_details.get("birthTime", "")
        rectified_time = birth_details.get("rectifiedBirthTime", "")

        return {
            "chart_id": chart_id,
            "session_id": session_id,
            "is_rectified": is_rectified,
            "original_time": original_time,
            "rectified_time": rectified_time,
            "confidence": rectification_results.get("confidence", 0),
            "explanation": rectification_results.get("explanation", "")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking rectification status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check rectification status: {str(e)}"
        )

# Modify the process_rectification function to use a more defensive approach for chart updating
async def process_rectification(chart_id: str, session_id: str, responses: List[Dict[str, Any]]) -> None:
    """
    Process birth time rectification based on questionnaire responses.
    """
    try:
        logger.info(f"Starting rectification process for chart {chart_id}, session {session_id}")

        # Get services
        from ai_service.api.services.chart import get_chart_service

        chart_service = get_chart_service()

        # Get chart data
        chart_data = await chart_service.get_chart(chart_id)
        if not chart_data:
            logger.error(f"Chart data not found for ID: {chart_id}")
            return

        # Extract birth details
        birth_details = chart_data.get("birth_details", {})
        if not birth_details:
            logger.error("Birth details not found in chart data")
            return

        # Create datetime object from birth details
        try:
            from datetime import datetime
            birth_date_str = birth_details.get("birthDate", "")
            birth_time_str = birth_details.get("birthTime", "")

            if not birth_date_str or not birth_time_str:
                logger.error("Missing birth date or time in chart data")
                return

            # Parse datetime
            birth_dt = datetime.strptime(f"{birth_date_str} {birth_time_str}", "%Y-%m-%d %H:%M")

            # Get location data
            latitude = birth_details.get("latitude")
            longitude = birth_details.get("longitude")
            timezone = birth_details.get("timezone")

            if not latitude or not longitude or not timezone:
                logger.error("Missing location data (latitude, longitude, or timezone)")
                return

            # Format answers for rectification
            formatted_answers = []
            for response in responses:
                if response:  # Add null check for response
                    formatted_answers.append({
                        "question": response.get("question", ""),
                        "answer": response.get("answer", ""),
                        "timestamp": response.get("timestamp", datetime.now().isoformat())
                    })

            # Perform rectification
            rectification_result = await comprehensive_rectification(
                birth_dt=birth_dt,
                latitude=float(latitude),
                longitude=float(longitude),
                timezone=timezone,
                answers=formatted_answers
            )

            # Update chart with rectification results
            if rectification_result:
                rectified_time = rectification_result.get("rectified_time")
                confidence = rectification_result.get("confidence")
                explanation = rectification_result.get("explanation")

                if rectified_time:
                    # Format the rectified time for chart update
                    rectified_date_str = rectified_time.strftime("%Y-%m-%d")
                    rectified_time_str = rectified_time.strftime("%H:%M")

                    # Prepare update data
                    update_data = {
                        "birth_details": {
                            "rectifiedBirthTime": rectified_time_str,
                            "originalBirthTime": birth_time_str
                        },
                        "rectification_results": {
                            "session_id": session_id,
                            "confidence": confidence,
                            "explanation": explanation,
                            "method": "questionnaire",
                            "completed_at": datetime.now().isoformat()
                        }
                    }

                    # Check for update_chart method and call it if available
                    try:
                        # Use dynamic attribute access with getattr to satisfy type checking
                        update_chart_fn = getattr(chart_service, 'update_chart', None)

                        if update_chart_fn is not None:
                            # Call the method through the function reference
                            await update_chart_fn(
                                chart_id=chart_id,
                                update_data=update_data
                            )
                            logger.info(f"Rectification completed for chart {chart_id}: "
                                    f"Adjusted from {birth_time_str} to {rectified_time_str} "
                                    f"with {confidence:.1f}% confidence")
                        else:
                            # Try saving the chart instead if update isn't available
                            if hasattr(chart_service, 'save_chart'):
                                try:
                                    await chart_service.save_chart(update_data)
                                    logger.info(f"Saved rectified chart data for {chart_id}")
                                except Exception as save_err:
                                    logger.error(f"Error saving rectified chart: {str(save_err)}")
                            else:
                                logger.error("Chart service does not have update_chart or save_chart methods")
                    except Exception as update_err:
                        logger.error(f"Error updating chart: {str(update_err)}")
                else:
                    logger.warning(f"Rectification process completed but no rectified time was returned")
            else:
                logger.error("Rectification process failed to return results")

        except Exception as e:
            logger.error(f"Error parsing birth details or performing rectification: {str(e)}")

    except Exception as e:
        logger.error(f"Error in rectification process: {str(e)}")
        logger.error(traceback.format_exc())
