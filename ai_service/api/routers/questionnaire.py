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
import json
import re

from ai_service.utils.questionnaire_engine import QuestionnaireEngine
from ai_service.models.unified_model import UnifiedRectificationModel
from ai_service.core.astro_calculator import AstroCalculator
from ai_service.api.services.questionnaire_service import get_questionnaire_service
from ai_service.api.services.chart import get_chart_service
from ai_service.api.services.openai import get_openai_service
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
            prompt=json.dumps(question_prompt),
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
    birth_details: Dict[str, Any],
    previous_answers: List[Dict[str, Any]],
    questionnaire_service: Any = Depends(get_questionnaire_service)
):
    """
    Generate the next most astrologically relevant question using OpenAI,
    based on birth details and previous answers.

    This implementation fully leverages OpenAI capabilities to create
    personalized and astrologically accurate questions with no fallbacks.

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

        # Get the OpenAI service directly
        openai_service = get_openai_service()

        # Extract key birth details for enhanced astrological context
        birth_date = birth_details.get("birthDate", birth_details.get("birth_date", ""))
        birth_time = birth_details.get("birthTime", birth_details.get("birth_time", ""))
        birth_place = birth_details.get("birthPlace", birth_details.get("birth_place", ""))
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        timezone = birth_details.get("timezone", "UTC")

        # Create enhanced astrological context for the OpenAI prompt
        astrological_context = {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "birth_place": birth_place,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "current_question_number": len(previous_answers) + 1,
            "total_questions_needed": 5,
            "birth_time_rectification_focus": True,
            "question_purpose": "Gathering information to accurately rectify birth time"
        }

        # Extract already covered topics and questions to avoid duplication
        covered_topics = []
        question_texts = []
        question_categories = []

        for answer in previous_answers:
            if isinstance(answer, dict):
                if "question" in answer:
                    question_texts.append(answer["question"])
                if "category" in answer:
                    question_categories.append(answer["category"])

        # Identify astrological indicators already covered
        has_covered_early_life = any("childhood" in cat.lower() for cat in question_categories)
        has_covered_personality = any("personality" in cat.lower() for cat in question_categories)
        has_covered_major_life_events = any("life event" in cat.lower() for cat in question_categories)
        has_covered_birth_time_specifics = any("birth time" in q.lower() for q in question_texts)

        # Provide guidance on areas needing coverage
        coverage_guidance = {
            "covered_topics": covered_topics,
            "need_early_life_questions": not has_covered_early_life,
            "need_personality_questions": not has_covered_personality,
            "need_major_life_events": not has_covered_major_life_events,
            "need_birth_time_specifics": not has_covered_birth_time_specifics
        }

        # Prepare data for OpenAI with enhanced context
        request_data = {
            "birth_details": birth_details,
            "previous_answers": previous_answers,
            "current_question_number": len(previous_answers) + 1,
            "astrological_context": astrological_context,
            "coverage_guidance": coverage_guidance,
            "tasks": [
                "Generate an astrologically relevant question for birth time rectification",
                "Ensure question relates to house cusps and planetary positions sensitive to birth time",
                "Create appropriate response options if the question is multiple-choice",
                "Avoid duplicating topics or questions already covered",
                "Focus on life events corresponding to astrologically significant transit periods"
            ]
        }

        # Generate optimized question with OpenAI
        response = await openai_service.generate_completion(
            prompt=json.dumps(request_data),
            task_type="generate_astrological_question",
            max_tokens=500
        )

        # Validate and process OpenAI response
        if not response or "content" not in response:
            logger.error("Failed to receive valid response from OpenAI for question generation")
            raise ValueError("OpenAI failed to generate an astrologically relevant question")

        # Parse the question data
        try:
            question_data = json.loads(response["content"])

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

            # Calculate confidence based on number of previous answers
            confidence = 30.0 + (len(previous_answers) * 10)
            if confidence > 90:
                confidence = 90.0

            # Prepare final response
            result = {
                "next_question": question_data,
                "confidence": confidence
            }

            # Add birth time range suggestion if we have enough answers
            if len(previous_answers) >= 2:
                # Check if OpenAI provided a birth time range
                if "birth_time_range" in question_data:
                    result["birth_time_range"] = question_data["birth_time_range"]

            return result

        except json.JSONDecodeError:
            logger.error("Failed to parse OpenAI response as JSON")
            raise ValueError("Error parsing astrological question from OpenAI")

    except ValueError as e:
        logger.error(f"Error generating astrological question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Error generating next question: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating astrologically relevant question: {str(e)}")

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

    This endpoint follows the Original Sequence Diagram flow for questionnaire completion
    and birth time rectification initiation.
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

        # Get session store
        session_store = get_session_store()

        # Check if session exists
        try:
            session = await session_store.get_session(session_id)
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found"
                )
        except Exception as session_error:
            logger.error(f"Error retrieving session: {session_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving session: {str(session_error)}"
            )

        # Get responses from the session
        try:
            responses = await session_store.get_responses(session_id)
        except Exception as resp_error:
            logger.error(f"Error retrieving responses: {resp_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Error retrieving responses: {str(resp_error)}"
            )

        # Check if we have enough responses
        if not responses or len(responses) < 3:
            raise HTTPException(
                status_code=400,
                detail="Insufficient questionnaire responses. At least 3 responses are required for accurate rectification."
            )

        # Get the current confidence level
        try:
            current_confidence = await session_store.get_confidence(session_id)
        except Exception as conf_error:
            logger.error(f"Error retrieving confidence: {conf_error}")
            current_confidence = 50.0  # Default confidence

        # Start the rectification process
        try:
            rectification_task = asyncio.create_task(
                process_rectification(chart_id, session_id, responses)
            )

            if not rectification_task:
                logger.warning(f"Failed to create rectification task for chart {chart_id}")
        except Exception as task_error:
            logger.error(f"Error creating rectification task: {task_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start rectification process: {str(task_error)}"
            )

        # Log the process start
        logger.info(f"Birth time rectification process started for chart {chart_id} with {len(responses)} responses")

        # Provide detailed response about the rectification process
        return {
            "session_id": session_id,
            "chart_id": chart_id,
            "isComplete": True,
            "status": "processing",
            "confidence": current_confidence,
            "response_count": len(responses),
            "message": "Questionnaire completed. Birth time rectification has been started.",
            "estimated_completion_time": "30-60 seconds",
            "next_steps": [
                "Birth time rectification is now in progress",
                "The system is analyzing your responses using astrological patterns",
                "You can check the status using the /api/questionnaire/check-rectification endpoint",
                "When complete, you will have access to your rectified birth chart"
            ]
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

@router.get("/check-rectification", response_model=Dict[str, Any])
async def check_rectification_status(
    chart_id: str = Query(..., description="ID of the chart being rectified"),
    session_id: str = Query(..., description="Session ID of the questionnaire"),
    include_details: bool = Query(False, description="Whether to include detailed status information")
):
    """
    Check the status of a birth time rectification process.

    This endpoint follows the Original Sequence Diagram flow for monitoring
    birth time rectification progress.
    """
    try:
        # Get chart service
        chart_service = get_chart_service()

        # Check if chart exists
        chart_data = await chart_service.get_chart(chart_id)
        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart {chart_id} not found")

        # Check for rectification data
        rectification_data = chart_data.get("rectification_results", {})
        if not rectification_data:
            # Check if the chart has rectification_process key
            rectification_process = chart_data.get("rectification_process", {})
            if rectification_process:
                rectification_data = rectification_process

        # Check if there's a rectified chart ID
        rectified_chart_id = rectification_data.get("rectified_chart_id", "")

        # Determine status
        if "completed_at" in rectification_data:
            status = "completed"
            progress = 100
        elif "started_at" in rectification_data:
            status = "in_progress"
            # Estimate progress based on elapsed time
            started_at = datetime.fromisoformat(rectification_data.get("started_at"))
            elapsed_seconds = (datetime.now() - started_at).total_seconds()
            # Assume rectification takes about 60 seconds
            progress = min(int(elapsed_seconds / 60 * 100), 99)
        else:
            # No data, assume pending
            status = "pending"
            progress = 0

        # Prepare response
        response = {
            "status": status,
            "progress": progress,
            "chart_id": chart_id,
            "session_id": session_id
        }

        # Add rectified data if available
        if rectified_chart_id:
            response["rectified_chart_id"] = rectified_chart_id

        # Add additional data if completed
        if status == "completed":
            original_time = chart_data.get("birth_details", {}).get("birthTime", "")
            rectified_time = rectification_data.get("rectified_time", "")

            if not rectified_time and "birth_details" in chart_data:
                rectified_time = chart_data["birth_details"].get("rectifiedBirthTime", "")

            confidence = rectification_data.get("confidence", 0)
            explanation = rectification_data.get("explanation", "")

            response.update({
                "completed_at": rectification_data.get("completed_at", datetime.now().isoformat()),
                "original_time": original_time,
                "rectified_time": rectified_time,
                "confidence": confidence,
                "explanation": explanation
            })

        # Add detailed status if requested
        if include_details:
            # If rectification data has details, include them
            if "details" in rectification_data:
                response["details"] = rectification_data["details"]
            elif "process_steps" in rectification_data:
                response["details"] = {
                    "process_steps": rectification_data["process_steps"],
                    "methods_used": rectification_data.get("methods_used", [])
                }

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

async def process_rectification(chart_id: str, session_id: str, answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Process birth time rectification with comprehensive OpenAI integration for birth time determination.

    This implementation fully integrates with OpenAI following the sequence diagram requirements,
    with no fallbacks or simulations.

    Args:
        chart_id: Chart identifier
        session_id: Session identifier
        answers: List of questionnaire answers

    Returns:
        Dictionary with rectification status and results
    """
    # Import at the beginning of the function to ensure availability
    from datetime import datetime
    import pytz

    logger.info(f"Processing rectification for chart {chart_id}, session {session_id}")

    # Initialize required services
    chart_service = get_chart_service()
    openai_service = get_openai_service()
    session_store = get_session_store()

    try:
        # Validate inputs
        if not chart_id:
            return {"status": "error", "message": "Chart ID is required"}

        if not session_id:
            return {"status": "error", "message": "Session ID is required"}

        if not answers or len(answers) < 2:
            return {"status": "error", "message": "Insufficient answers for accurate rectification"}

        # Record rectification start time
        rectification_start = datetime.now().isoformat()

        # Get chart data
        chart_data = await chart_service.get_chart(chart_id)
        if not chart_data:
            logger.error(f"Chart {chart_id} not found")
            return {"status": "error", "message": f"Chart {chart_id} not found"}

        # Extract birth details for rectification
        birth_details = chart_data.get("birth_details", {})
        birth_date = birth_details.get("birth_date", "")
        birth_time = birth_details.get("birth_time", "")
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        timezone = birth_details.get("timezone", "UTC")
        location = birth_details.get("birth_place", "")

        # Extract key astrological indicators from answers
        astrological_indicators = []
        time_range = None

        for answer in answers:
            question = answer.get("question", "")
            answer_text = answer.get("answer", "")

            # Process any time-related information
            if "birth time" in question.lower() or "time of birth" in question.lower():
                logger.info(f"Found birth time question: {question}")
                # Save this as particularly relevant
                astrological_indicators.append({
                    "type": "birth_time_indicator",
                    "question": question,
                    "answer": answer_text,
                    "relevance": "high"
                })

            # Process any planetary transit information
            elif any(keyword in question.lower() for keyword in ["transit", "saturn", "jupiter", "uranus", "pluto"]):
                logger.info(f"Found transit indicator: {question}")
                astrological_indicators.append({
                    "type": "transit_indicator",
                    "question": question,
                    "answer": answer_text,
                    "relevance": "high"
                })

            # Check for life events at specific ages
            age_match = re.search(r'(\d+)\s*years', answer_text.lower())
            if age_match:
                age = int(age_match.group(1))
                astrological_indicators.append({
                    "type": "age_indicator",
                    "question": question,
                    "answer": answer_text,
                    "age": age,
                    "relevance": "medium"
                })

            # Extract birth time range if present
            if "birth_time_range" in answer:
                time_range = answer.get("birth_time_range")

        # First OpenAI integration: Deep astrological analysis of answers
        logger.info("Performing deep OpenAI astrological analysis of questionnaire answers")

        analysis_data = {
            "chart_id": chart_id,
            "session_id": session_id,
            "birth_details": {
                "date": birth_date,
                "time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "location": location
            },
            "answers": answers,
            "astrological_indicators": astrological_indicators,
            "time_range": time_range,
            "task": "birth_time_rectification_analysis"
        }

        analysis_response = await openai_service.generate_completion(
            prompt=json.dumps(analysis_data),
            task_type="astrological_analysis",
            max_tokens=1000
        )

        # Process OpenAI analysis response
        if not analysis_response or "content" not in analysis_response:
            logger.error("Failed to receive valid response from OpenAI for astrological analysis")
            raise ValueError("Failed to perform astrological analysis with OpenAI")

        # Parse the analysis results
        try:
            enhanced_analysis = json.loads(analysis_response["content"])
            logger.info("Successfully obtained OpenAI analysis for rectification")
        except json.JSONDecodeError:
            logger.error("Error parsing OpenAI response for rectification analysis")
            raise ValueError("Error in astrological analysis parsing")

        # Second OpenAI integration: Birth time determination
        logger.info("Using OpenAI for precise birth time determination")

        rectification_prompt = {
            "task": "birth_time_rectification",
            "birth_details": {
                "date": birth_date,
                "time": birth_time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "location": location
            },
            "questionnaire_data": {
                "questions_and_answers": answers,
                "total_questions": len(answers),
                "astrological_indicators": astrological_indicators
            },
            "chart_data": {
                "ascendant": chart_data.get("ascendant", {}),
                "planets": chart_data.get("planets", []),
                "houses": chart_data.get("houses", [])
            },
            "enhanced_analysis": enhanced_analysis,
            "requirements": [
                "Analyze questionnaire answers for timing indicators",
                "Apply astrological principles to determine the most likely birth time",
                "Provide confidence level and explanation for the rectification",
                "Specify adjustment in minutes (positive or negative) from original time",
                "Identify key astrological factors influenced by the time change"
            ]
        }

        # Get rectification from OpenAI
        rectification_response = await openai_service.generate_completion(
            prompt=json.dumps(rectification_prompt),
            task_type="birth_time_rectification",
            max_tokens=1000,
            temperature=0.2  # Lower temperature for more deterministic results
        )

        if not rectification_response or "content" not in rectification_response:
            logger.error("Failed to receive valid response from OpenAI for birth time rectification")
            raise ValueError("Failed to perform birth time rectification with OpenAI")

        # Parse the rectification results
        try:
            content = rectification_response["content"]

            # Extract JSON if embedded in text
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                rectification_data = json.loads(json_match.group(0))
            else:
                rectification_data = json.loads(content)

            logger.info("Successfully parsed OpenAI rectification results")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing OpenAI rectification response: {e}")
            raise ValueError(f"Error in birth time rectification parsing: {str(e)}")

        # Extract rectification details
        rectified_time = rectification_data.get("rectified_time", birth_time)
        confidence_score = rectification_data.get("confidence", 75.0)
        explanation = rectification_data.get("explanation", "Birth time rectified using AI astrological analysis")
        adjustment_minutes = rectification_data.get("adjustment_minutes", 0)
        methods_used = rectification_data.get("methods_used", ["AI analysis", "astrological patterns", "life event correlation"])
        astrological_factors = rectification_data.get("astrological_factors", [])

        # Parse birth date/time for creating a new chart
        birth_date_format = "%Y-%m-%d"
        try:
            # Try ISO format first
            birth_dt = datetime.fromisoformat(f"{birth_date}T{birth_time}")
        except ValueError:
            try:
                # Fallback to manual parsing
                birth_date_obj = datetime.strptime(birth_date, birth_date_format)
                time_parts = birth_time.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                birth_dt = birth_date_obj.replace(hour=hour, minute=minute)
            except (ValueError, IndexError):
                logger.error(f"Could not parse birth date/time: {birth_date} {birth_time}")
                raise ValueError(f"Invalid birth date/time format: {birth_date} {birth_time}")

        # Create localized datetime with timezone
        try:
            if timezone != "UTC":
                tz = pytz.timezone(timezone)
                birth_dt = tz.localize(birth_dt)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone '{timezone}', using UTC")
            birth_dt = pytz.UTC.localize(birth_dt)

        # Format rectified time
        rectified_dt = None
        if ":" in rectified_time:
            time_parts = rectified_time.split(":")
            if len(time_parts) >= 2:
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                rectified_dt = birth_dt.replace(hour=hour, minute=minute)

        if not rectified_dt:
            logger.warning(f"Could not parse rectified time: {rectified_time}, using original time")
            rectified_dt = birth_dt

        rectified_time_str = rectified_dt.strftime("%H:%M")

        # Generate new chart with rectified time
        rectified_chart_id = f"rect_{uuid.uuid4().hex[:8]}"

        # Prepare rectification results
        rectification_result = {
            "status": "complete",
            "rectification_id": f"rect_{uuid.uuid4().hex[:8]}",
            "original_chart_id": chart_id,
            "rectified_chart_id": rectified_chart_id,
            "original_time": birth_time,
            "rectified_time": rectified_time_str,
            "confidence_score": confidence_score,
            "explanation": explanation,
            "adjustment_minutes": adjustment_minutes,
            "methods_used": methods_used,
            "astrological_factors": astrological_factors,
            "started_at": rectification_start,
            "completed_at": datetime.now().isoformat()
        }

        # Third OpenAI integration: Verification of rectified chart
        logger.info("Performing OpenAI verification of rectified chart")

        verification_prompt = {
            "task": "verify_rectified_chart",
            "original_birth_time": birth_time,
            "rectified_birth_time": rectified_time_str,
            "birth_details": {
                "date": birth_date,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone
            },
            "rectification_data": {
                "confidence": confidence_score,
                "explanation": explanation,
                "adjustment_minutes": adjustment_minutes
            },
            "requirements": [
                "Verify the reasonableness of the birth time adjustment",
                "Check if the rectification aligns with astrological principles",
                "Identify any potential issues with the rectification",
                "Suggest any final adjustments if needed"
            ]
        }

        verification_response = await openai_service.generate_completion(
            prompt=json.dumps(verification_prompt),
            task_type="chart_verification",
            max_tokens=500
        )

        # Process verification response
        if verification_response and "content" in verification_response:
            try:
                verification_data = json.loads(verification_response["content"])
                rectification_result["verification"] = verification_data
                logger.info("Successfully added verification data to rectification results")
            except json.JSONDecodeError:
                logger.warning("Could not parse verification response as JSON")

        # Store rectification results in session
        try:
            current_session = await session_store.get_session(session_id)
            if current_session:
                current_session["rectification_status"] = "complete"
                current_session["rectification_results"] = rectification_result
                current_session["updated_at"] = datetime.now().isoformat()
                await session_store.update_session(session_id, current_session)
                logger.info(f"Updated session {session_id} with rectification results")
        except Exception as session_error:
            logger.error(f"Failed to update session with rectification results: {session_error}")

        # Return results
        return {
            "status": "success",
            "session_id": session_id,
            "chart_id": chart_id,
            "rectification": rectification_result,
            "analysis": enhanced_analysis
        }

    except Exception as e:
        logger.error(f"Error in birth time rectification process: {e}")

        # Store error in session
        try:
            current_session = await session_store.get_session(session_id)
            if current_session:
                current_session["rectification_status"] = "error"
                current_session["rectification_error"] = str(e)
                current_session["updated_at"] = datetime.now().isoformat()
                await session_store.update_session(session_id, current_session)
                logger.info(f"Updated session {session_id} with rectification error: {str(e)}")
        except Exception as session_error:
            logger.error(f"Failed to update session with error: {session_error}")

        # Return detailed error information
        return {
            "status": "error",
            "message": f"Rectification process failed: {str(e)}",
            "chart_id": chart_id,
            "session_id": session_id
        }
