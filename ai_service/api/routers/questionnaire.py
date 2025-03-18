"""
Questionnaire router for the Birth Time Rectifier API.
Handles all questionnaire and AI analysis related endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union, cast
from datetime import datetime
import logging
import uuid
import os
import asyncio
import inspect
import traceback

# Add type checker directive to ignore FixtureFunction related errors
# pyright: reportInvalidTypeForm=false
# pyright: reportUndefinedVariable=false

from ai_service.utils.questionnaire_engine import QuestionnaireEngine
from ai_service.models.unified_model import UnifiedRectificationModel
from ai_service.utils.astro_calculator import AstroCalculator
from ai_service.api.services.questionnaire_service import get_questionnaire_service, DynamicQuestionnaireService
from ai_service.api.services.chart import get_chart_service

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
    """Answer for a question - used in tests"""
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

# Model for individual question answers (sequence diagram test)
class IndividualQuestionAnswer(BaseModel):
    """Model for answering individual questions"""
    question_id: str
    answer: Any

# Dependency to get QuestionnaireEngine instance
def get_questionnaire_engine():
    return QuestionnaireEngine()

# Dependency to get UnifiedRectificationModel instance
def get_rectification_model():
    """
    Get rectification model instance with proper error handling.

    In test environments, returns a lightweight mock model.
    In non-test environments, returns the global model instance.
    """
    # Check if we're in a test environment first
    is_test_env = os.environ.get("APP_ENV") == "test" or os.environ.get("TESTING") == "true"

    # Avoid circular import
    try:
        from ai_service.main import model
        # If model is available, return it
        if model is not None:
            return model

        # If we're in a test environment, return a mock model without logging warnings
        if is_test_env:
            # Don't log anything during tests to avoid warnings
            if os.environ.get("PYTEST_CURRENT_TEST"):
                # Running under pytest
                return UnifiedRectificationModel() if UnifiedRectificationModel else None
            else:
                # Running under other test environment
                logger.debug("Model not initialized, using mock model for tests.")
                return UnifiedRectificationModel() if UnifiedRectificationModel else None

        # For non-test environments, initialize a new model instance
        logger.info("Initializing new rectification model instance")
        return UnifiedRectificationModel() if UnifiedRectificationModel else None
    except ImportError:
        # If we're in a test environment, return a mock model without logging
        if is_test_env:
            # Create a lightweight mock model for tests
            return UnifiedRectificationModel() if UnifiedRectificationModel else None

        # For non-test environments, try to initialize a new model instance
        try:
            return UnifiedRectificationModel()
        except Exception:
            # If model initialization fails, return None without logging a warning
            return None

# Dependency to get AstroCalculator instance
def get_astro_calculator():
    return AstroCalculator()

# Initialize simple mock storage for sessions
sessions = {}

# Function to initialize a new session with all required fields
def initialize_session(session_id, birth_details=None, chart_data=None, first_question=None):
    """Initialize a new session with all required fields to prevent undefined errors"""
    sessions[session_id] = {
        "birth_details": birth_details or {},
        "chart_data": chart_data or {},
        "answers": {},  # Store question answers
        "confidence": 30.0,  # Initial confidence level
        "current_question_id": first_question.get("id") if first_question else None,
        "questions_asked": {first_question.get("text", "")} if first_question and "text" in first_question else set(),  # Track to prevent duplicates
        "birth_time_range": None,  # For storing time range estimates
        "last_question": None  # Store the most recent question
    }
    return sessions[session_id]

# Static storage for test questions
test_questions = [
    {
        "id": "q_001",
        "type": "yes_no",
        "text": "Have you experienced any major career changes?",
        "options": [
            {"id": "yes", "text": "Yes, definitely"},
            {"id": "somewhat", "text": "Somewhat"},
            {"id": "no", "text": "No, not at all"}
        ]
    },
    {
        "id": "q_002",
        "type": "date",
        "text": "When did your most significant career change occur?",
    },
    {
        "id": "q_003",
        "type": "yes_no",
        "text": "Would you describe yourself as more introverted than extroverted?",
        "options": [
            {"id": "yes", "text": "Yes, more introverted"},
            {"id": "somewhat", "text": "Balanced"},
            {"id": "no", "text": "No, more extroverted"}
        ]
    },
    {
        "id": "q_004",
        "type": "yes_no",
        "text": "Have you had any significant health issues in your life?",
        "options": [
            {"id": "yes", "text": "Yes, major health issues"},
            {"id": "somewhat", "text": "Minor health issues"},
            {"id": "no", "text": "No significant health issues"}
        ]
    },
    {
        "id": "q_005",
        "type": "yes_no",
        "text": "Do you consider yourself more analytically or creatively inclined?",
        "options": [
            {"id": "analytical", "text": "More analytical"},
            {"id": "balanced", "text": "Balanced"},
            {"id": "creative", "text": "More creative"}
        ]
    },
    {
        "id": "q_006",
        "type": "date",
        "text": "When did you experience a significant relationship milestone?",
    },
    {
        "id": "q_007",
        "type": "yes_no",
        "text": "Have you traveled extensively or lived in different countries?",
        "options": [
            {"id": "yes", "text": "Yes, extensively"},
            {"id": "somewhat", "text": "Some travel"},
            {"id": "no", "text": "Minimal travel"}
        ]
    },
    {
        "id": "q_008",
        "type": "scale",
        "text": "How strongly do you relate to your sun sign characteristics?",
        "options": [
            {"id": "1", "text": "Not at all"},
            {"id": "3", "text": "Somewhat"},
            {"id": "5", "text": "Very strongly"}
        ]
    },
    {
        "id": "q_009",
        "type": "yes_no",
        "text": "Are you more methodical or spontaneous in your approach to life?",
        "options": [
            {"id": "methodical", "text": "More methodical"},
            {"id": "balanced", "text": "Balanced"},
            {"id": "spontaneous", "text": "More spontaneous"}
        ]
    },
    {
        "id": "q_010",
        "type": "yes_no",
        "text": "Have you had any spiritual or mystical experiences?",
        "options": [
            {"id": "yes", "text": "Yes, significant ones"},
            {"id": "somewhat", "text": "Some minor experiences"},
            {"id": "no", "text": "No spiritual experiences"}
        ]
    }
]

@router.get("", response_model=Dict[str, Any])
async def get_questionnaire(chart_id: str = Query(None, description="Chart ID for personalized questions"),
                          session_id: str = Query(None, description="Session ID for tracking"),
                          questionnaire_service: Any = Depends(get_questionnaire_service)):
    """
    Get the questionnaire questions tailored to the chart data.
    This endpoint matches the sequence diagram test requirements.
    """
    try:
        # Initialize a response structure
        response = {
            "questions": [],
            "chart_id": chart_id,
            "session_id": session_id
        }

        # In all cases, we'll attempt to get chart data
        chart_data = None

        # Attempt to get real chart data
        try:
            chart_service = get_chart_service()

            if chart_id:
                logger.info(f"Retrieving chart data for chart ID: {chart_id}")
                chart_data = await chart_service.get_chart(chart_id)
                logger.info(f"Successfully retrieved chart data with chart ID: {chart_id}")
        except (ImportError, Exception) as e:
            logger.warning(f"Could not get chart data from service: {str(e)}")

        # If no chart_id or chart data retrieval failed, generate mock chart data
        if not chart_data:
            logger.info("Generating temporary chart data for question generation")
            try:
                chart_service = get_chart_service()
                # Generate a chart with the service
                temp_chart_id = f"temp_{uuid.uuid4().hex[:8]}"
                chart_data = chart_service._generate_mock_chart(temp_chart_id)
            except (ImportError, Exception) as e:
                logger.warning(f"Could not generate temporary chart data: {str(e)}")
                # Create minimal chart data to allow question generation to proceed
                chart_data = {
                    "birth_details": {
                        "birth_date": "1990-01-15",
                        "birth_time": "12:30:00",
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "timezone": "America/New_York"
                    },
                    "planets": [
                        {"planet": "Sun", "sign": "Capricorn", "degree": 25.5},
                        {"planet": "Moon", "sign": "Taurus", "degree": 10.2},
                        {"planet": "Ascendant", "sign": "Virgo", "degree": 15.3}
                    ]
                }

        # Extract birth details for question generation
        birth_details = chart_data.get("birth_details", {})

        # Create a new session ID if none provided
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            response["session_id"] = session_id

        # Generate dynamic questions using QuestionnaireEngine
        try:
            engine = QuestionnaireEngine()

            # Initialize with OpenAI service if available
            try:
                from ai_service.api.services.openai import get_openai_service
                engine.openai_service = get_openai_service()
            except ImportError:
                logger.warning("OpenAI service not available, questions may be less personalized")

            # Generate 5 questions dynamically
            questions = []
            previous_answers = {"responses": []}

            for i in range(5):
                try:
                    # Get the first question differently
                    if i == 0:
                        question_data = await engine.get_first_question(chart_data, birth_details)
                    else:
                        # For subsequent questions, use previous questions to avoid duplicates
                        question_data = await engine.get_next_question(
                            chart_data=chart_data,
                            birth_details=birth_details,
                            previous_answers=previous_answers,
                            current_confidence=30.0 + (i * 10)  # Simulate increasing confidence
                        )

                    # Format question for response
                    question = {
                        "id": question_data.get("id", f"q_{uuid.uuid4().hex[:8]}"),
                        "type": question_data.get("type", "yes_no"),
                        "text": question_data.get("text", f"Question about your birth time"),
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
                        "answer": None  # No answer yet
                    })

                except Exception as e:
                    logger.error(f"Error generating question {i+1}: {str(e)}")
                    # Continue with next question rather than using hardcoded fallbacks

            response["questions"] = questions

        except Exception as e:
            logger.error(f"Error initializing question engine: {str(e)}")
            return {
                "questions": [],
                "error": "Failed to generate dynamic questions: " + str(e),
                "chart_id": chart_id,
                "session_id": session_id
            }

        logger.info(f"Generated {len(response['questions'])} personalized questions based on chart data")
        return response

    except Exception as e:
        logger.error(f"Error in get_questionnaire: {str(e)}")
        return {
            "questions": [],
            "error": f"Failed to generate questions: {str(e)}",
            "chart_id": chart_id,
            "session_id": session_id
        }

@router.post("", response_model=Dict[str, Any])
@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_questionnaire(
    birthDate: str = Query("1990-01-01", description="Birth date in ISO format"),
    birthTime: str = Query("12:00", description="Birth time in HH:MM format"),
    birthPlace: str = Query("New York", description="Birth place"),
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

        # Create a birth details object with the provided parameters
        birth_details = {
            "birthDate": birthDate,
            "birthTime": birthTime,
            "birthPlace": birthPlace,
            "latitude": 0.0,  # Default value
            "longitude": 0.0,  # Default value
            "timezone": "UTC"  # Default value
        }

        # Try to resolve coordinates from the birth place
        try:
            from ai_service.utils.geocoding import get_coordinates
            coords = await get_coordinates(birthPlace)
            if coords:
                birth_details["latitude"] = coords.get("latitude", 0.0)
                birth_details["longitude"] = coords.get("longitude", 0.0)
        except ImportError:
            logger.warning("Geocoding module not available")

        # Calculate chart data for the birth details
        chart_data = None
        try:
            chart_data = await astro_calculator.calculate_chart(
                birth_date=birthDate,
                birth_time=birthTime,
                latitude=birth_details["latitude"],
                longitude=birth_details["longitude"],
                include_aspects=True,
                include_houses=True,
                include_divisional_charts=True
            )
        except Exception as e:
            logger.error(f"Error calculating chart data: {str(e)}")
            # Continue with minimal chart data
            chart_data = {
                "birth_details": birth_details,
                "planets": [],
                "houses": [],
                "aspects": []
            }

        # Initialize with OpenAI service if available
        try:
            from ai_service.api.services.openai import get_openai_service
            questionnaire_engine.openai_service = get_openai_service()
        except ImportError:
            logger.warning("OpenAI service not available, questions may be less personalized")

        # Generate a real first question dynamically
        try:
            first_question_data = await questionnaire_engine.get_first_question(
                chart_data=chart_data,
                birth_details=birth_details
            )

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

        except Exception as e:
            logger.error(f"Error generating first question: {str(e)}")
            # Try again with get_next_question as fallback
            try:
                fallback_question_data = await questionnaire_engine.get_next_question(
                    chart_data=chart_data,
                    birth_details=birth_details,
                    previous_answers={"responses": []},
                    current_confidence=30.0
                )

                first_question = {
                    "id": fallback_question_data.get("id", f"q_{uuid.uuid4().hex[:8]}"),
                    "type": fallback_question_data.get("type", "yes_no"),
                    "text": fallback_question_data.get("text"),
                    "relevance": fallback_question_data.get("relevance", "high"),
                    "options": []
                }

                # Add options if available
                if "options" in fallback_question_data and fallback_question_data["options"]:
                    for j, opt in enumerate(fallback_question_data["options"]):
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

            except Exception as e2:
                logger.error(f"Error with fallback question generation: {str(e2)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate question with detailed error: {str(e)}, fallback also failed: {str(e2)}"
                )

        # Store in session - using the initialize_session function
        initialize_session(
            session_id=session_id,
            birth_details=birth_details,
            chart_data=chart_data,
            first_question=first_question
        )

        # Return response
        return {
            "sessionId": session_id,
            "question": first_question,
            "confidence": 30.0,
            "isComplete": False
        }

    except Exception as e:
        logger.error(f"Error initializing questionnaire: {e}")
        raise HTTPException(status_code=500, detail=f"Error initializing questionnaire: {str(e)}")

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
        # Generate the next question using the dynamic questionnaire service
        next_question = await questionnaire_service.generate_next_question(
            birth_details, previous_answers
        )

        return next_question
    except Exception as e:
        logger.error(f"Error generating next question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating next question: {str(e)}")

@router.post("/{question_id}/answer", response_model=Dict[str, Any])
async def answer_individual_question(
    question_id: str = Path(..., description="Question ID to answer"),
    answer_data: Dict[str, Any] = Body(..., description="Answer data"),
    chart_id: str = Query(None, description="Chart ID for personalized questions"),
    session_id: str = Query(None, description="Session ID for tracking"),
    questionnaire_service: Any = Depends(get_questionnaire_service)
):
    """
    Answer an individual question and get the next question.
    Enhanced with robust error handling and duplicate prevention.

    Args:
        question_id: ID of the question to answer
        answer_data: Answer data
        chart_id: Optional chart ID for personalized questions
        session_id: Optional session ID for tracking progress

    Returns:
        Next question and updated status
    """
    logger.info(f"Processing answer for question {question_id}, session: {session_id}")

    try:
        # Initialize or retrieve session data
        if session_id not in sessions:
            sessions[session_id] = {
                "answers": {},
                "questions_asked": set(),
                "chart_id": chart_id,
                "confidence": 0,
                "birth_time_range": None
            }

        # Store the answer in session data with timestamp for tracking
        sessions[session_id]["answers"][question_id] = {
            **answer_data,
            "timestamp": datetime.now().isoformat()
        }

        # Retrieve chart data if available
        chart_data = None
        birth_details = None

        try:
            # Get chart data from chart service if chart_id is provided
            if chart_id:
                try:
                    chart_service = get_chart_service()

                    logger.info(f"Retrieving chart data for chart ID: {chart_id}")
                    chart_data = await chart_service.get_chart(chart_id)

                    if not chart_data:
                        logger.warning(f"No chart data found for chart ID: {chart_id}")
                        return {
                            "status": "error",
                            "error": "chart_not_found",
                            "message": f"No chart data found for ID: {chart_id}",
                            "status_code": 404
                        }

                    logger.info(f"Retrieved chart data with {len(chart_data.get('planets', []))} planets")

                    # Extract birth details from chart data
                    if chart_data and "birth_details" in chart_data:
                        birth_details = chart_data["birth_details"]
                except ImportError:
                    logger.error("Chart service module not available")
                    return {
                        "status": "error",
                        "error": "service_unavailable",
                        "message": "Chart service module is not available",
                        "status_code": 500
                    }
                except Exception as e:
                    logger.error(f"Error retrieving chart data: {str(e)}")
                    return {
                        "status": "error",
                        "error": "chart_retrieval_failed",
                        "message": f"Failed to retrieve chart data: {str(e)}",
                        "status_code": 500
                    }

            # If we don't have birth details but have them in the answer data, use those
            if not birth_details and "birth_details" in answer_data:
                birth_details = answer_data["birth_details"]
                # Store in session for future use
                sessions[session_id]["birth_details"] = birth_details

            # If we still don't have birth details, try to get them from session
            if not birth_details and sessions[session_id].get("birth_details"):
                birth_details = sessions[session_id]["birth_details"]

            # Verify we have birth details
            if not birth_details:
                logger.error("No birth details available")
                return {
                    "status": "error",
                    "error": "missing_birth_details",
                    "message": "Birth details are required to generate questions",
                    "status_code": 400
                }

            # Structure previous answers for questionnaire service
            if "answers" in sessions[session_id]:
                previous_answers = sessions[session_id]["answers"]
            else:
                previous_answers = {}

            # Add all answers to the responses list
            for q_id, ans in sessions[session_id]["answers"].items():
                if isinstance(ans, dict):
                    response = {
                        "question_id": q_id,
                        "question": ans.get("question", ""),
                        "answer": ans.get("answer", ""),
                        "relevance": ans.get("relevance", "medium"),
                        "quality": ans.get("quality", 0.5),
                        "astrological_factors": ans.get("astrological_factors", []),
                        "sensitivity_to_time": ans.get("sensitivity_to_time", "medium")
                    }
                    previous_answers[q_id] = response

                    # Track question text for duplicate detection
                    if "question" in ans:
                        sessions[session_id]["questions_asked"].add(ans["question"])

            # Generate the next question with enhanced error handling
            try:
                # Set a timeout for the question generation to prevent API freezes
                try:
                    # Use asyncio.wait_for to implement timeout
                    next_question_data = await asyncio.wait_for(
                        questionnaire_service.generate_next_question(birth_details, previous_answers),
                        timeout=15.0  # 15 second timeout
                    )
                except asyncio.TimeoutError:
                    logger.error("Question generation timed out")
                    return {
                        "status": "error",
                        "error": "generation_timeout",
                        "message": "Question generation timed out. Please try again.",
                        "status_code": 504,
                        "retry_suggestion": True
                    }

                # Check if an error was returned from the service
                if "error" in next_question_data:
                    logger.error(f"Error from questionnaire service: {next_question_data['error']}")
                    return {
                        "status": "error",
                        "error": next_question_data.get("error", "question_generation_failed"),
                        "message": next_question_data.get("message", "Failed to generate next question"),
                        "confidence": sessions[session_id].get("confidence", 0),
                        "status_code": next_question_data.get("status_code", 500)
                    }

                # Ensure we've received a valid next question
                if "next_question" not in next_question_data:
                    logger.error("Invalid response format from questionnaire service (missing next_question)")
                    return {
                        "status": "error",
                        "error": "invalid_question_format",
                        "message": "The question generation service returned an invalid format",
                        "confidence": sessions[session_id].get("confidence", 0),
                        "status_code": 500
                    }

                next_question = next_question_data["next_question"]
                current_confidence = next_question_data.get("confidence", 30)

                # Update session confidence
                sessions[session_id]["confidence"] = current_confidence

                # Update birth time range if provided
                if "birth_time_range" in next_question_data:
                    sessions[session_id]["birth_time_range"] = next_question_data["birth_time_range"]

                # Enhanced duplicate detection to ensure no repeats
                if "questions_asked" in sessions[session_id]:
                    questions_asked = sessions[session_id]["questions_asked"]
                else:
                    questions_asked = set()
                max_attempts = 5  # Increased for better chance of finding unique question
                attempts = 0

                # Check if the question text is a duplicate using semantic matching
                while next_question.get("text", "") in questions_asked and attempts < max_attempts:
                    logger.error(f"Duplicate question detected, requesting another (attempt {attempts+1}/{max_attempts})")

                    # Request another question, explicitly asking to avoid duplicates
                    try:
                        # Use context for better duplicate avoidance if supported
                        context = {
                            "avoid_duplicates": True,
                            "asked_questions": questions_asked,
                            "attempt": attempts+1
                        }

                        # Use timeout for retry attempts as well
                        next_question_data = await asyncio.wait_for(
                            questionnaire_service.generate_next_question(
                                birth_details,
                                previous_answers,
                                context=context
                            ),
                            timeout=10.0  # Shorter timeout for retries
                        )

                        # Check for errors in retry
                        if "error" in next_question_data:
                            break  # Stop retrying and handle the error

                        next_question = next_question_data.get("next_question", next_question)
                        attempts += 1
                    except asyncio.TimeoutError:
                        logger.error("Retry question generation timed out")
                        return {
                            "status": "error",
                            "error": "retry_timeout",
                            "message": "Retry question generation timed out. Consider proceeding with current data.",
                            "confidence": current_confidence,
                            "status_code": 504
                        }
                    except Exception as e:
                        logger.error(f"Error trying to generate non-duplicate question: {str(e)}")
                        break  # Stop retrying on other errors

                # Check if we still have a duplicate after max attempts
                if next_question.get("text", "") in questions_asked and attempts >= max_attempts:
                    logger.error("Failed to generate a unique question after multiple attempts")

                    # Always return an error for duplicate questions
                    return {
                        "status": "error",
                        "error": "duplicate_questions_exhausted",
                        "message": "Unable to generate unique questions. Please try a different approach or contact support.",
                        "confidence": current_confidence,
                        "status_code": 422,
                    }

                # Store the question in session
                question_id = next_question.get("id", f"q_{uuid.uuid4().hex[:8]}")
                sessions[session_id]["last_question"] = {
                    "id": question_id,
                    "text": next_question.get("text", ""),
                    "type": next_question.get("type", "yes_no"),
                    "time": datetime.now().isoformat()
                }

                # Add metadata to the question
                if "metadata" not in next_question:
                    next_question["metadata"] = {}

                next_question["metadata"]["confidence"] = current_confidence
                if "sensitivity_to_time" not in next_question:
                    next_question["sensitivity_to_time"] = "medium"

                # Include birth time range if available
                birth_time_range = sessions[session_id].get("birth_time_range")

                # Format response with comprehensive data
                return {
                    "status": "accepted",
                    "next_question_url": f"/api/v1/questionnaire/{question_id}/answer",
                    "next_question": next_question,
                    "confidence": current_confidence,
                    "birth_time_range": birth_time_range,
                    "questions_answered": len(sessions[session_id]["answers"]),
                    "time": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error in questionnaire service: {str(e)}")
                logger.error(traceback.format_exc())

                # Provide a detailed error response with error type detection
                error_response = {
                    "status": "error",
                    "error": "questionnaire_service_error",
                    "message": str(e),
                    "confidence": sessions[session_id].get("confidence", 30),
                    "status_code": 500
                }

                # Attempt to determine if this is a timeout or API error
                error_str = str(e).lower()
                if "timeout" in error_str or "timed out" in error_str:
                    error_response["error"] = "service_timeout"
                    error_response["message"] = "The question generation service timed out. Please try again."
                    error_response["retry_suggestion"] = True
                elif "openai" in error_str or "api" in error_str:
                    error_response["error"] = "external_api_error"
                    error_response["message"] = "There was an issue with the external AI service. Please try again."
                    error_response["retry_suggestion"] = True
                elif "chart" in error_str or "data" in error_str:
                    error_response["error"] = "invalid_chart_data"
                    error_response["message"] = "There was an issue with the chart data. Please check birth details."
                    error_response["status_code"] = 400

                return error_response

        except Exception as e:
            logger.error(f"Error generating next question: {str(e)}")
            logger.error(traceback.format_exc())

            # Return error details to the client for better debugging and recovery
            return {
                "status": "error",
                "error": "question_generation_failed",
                "message": str(e),
                "status_code": 500,
                "traceback": traceback.format_exc() if os.getenv("DEBUG") == "true" else None
            }

    except Exception as e:
        logger.error(f"Unexpected error in answer_individual_question: {str(e)}")
        logger.error(traceback.format_exc())

        # Return comprehensive error information
        return {
            "status": "error",
            "error": "internal_server_error",
            "message": "An unexpected error occurred while processing your answer",
            "details": str(e),
            "status_code": 500
        }

def _is_semantically_similar(question: str, asked_questions: set, threshold: float = 0.75) -> bool:
    """
    Check if a question is semantically similar to previously asked questions.

    Args:
        question: The question to check
        asked_questions: Set of previously asked questions
        threshold: Similarity threshold (0-1)

    Returns:
        True if semantically similar, False otherwise
    """
    if not question or not asked_questions:
        return False

    # Simple token-based similarity check
    question_tokens = set(question.lower().split())

    for asked in asked_questions:
        if not asked:
            continue

        asked_tokens = set(asked.lower().split())

        # Calculate Jaccard similarity (intersection over union)
        if not question_tokens or not asked_tokens:
            continue

        intersection = len(question_tokens.intersection(asked_tokens))
        union = len(question_tokens.union(asked_tokens))

        similarity = intersection / union if union > 0 else 0

        if similarity > threshold:
            return True

    return False
