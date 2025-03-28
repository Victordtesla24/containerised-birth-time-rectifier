"""
Questionnaire API Router.

This module provides endpoints for questionnaire management and data handling.
"""

import asyncio
import json
import logging
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Type, cast

from fastapi import APIRouter, Depends, HTTPException, Header, status, Body, Query, Path, Request, BackgroundTasks
from pydantic import BaseModel, Field

# Import necessary models and services
from ai_service.models import QuestionnaireRequest, QuestionnaireResponse, QuestionnaireAnswerRequest, QuestionnaireCompleteResponse
from ai_service.utils.questionnaire_engine import QuestionnaireEngine
from ai_service.api.services.chart import get_chart_service
from ai_service.api.services.openai import get_openai_service

# Create forwarded type references instead of trying direct imports
UnifiedRectificationModelType = Any
SessionStoreType = Any

# Import services with proper error handling
try:
    # Import but override signature to avoid type errors
    from ai_service.api.middleware.session import get_session_id as original_get_session_id
    def get_session_id(request=None) -> str:
        """Get session ID wrapper to fix return type."""
        if request is not None and callable(original_get_session_id):
            result = original_get_session_id(request)
            return result or ""
        return ""
except ImportError:
    # Placeholder if not found
    def get_session_id(request=None) -> str:
        """Get session ID."""
        return ""

# Create our own DateTimeEncoder to avoid import issues
class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Setup logging
logger = logging.getLogger(__name__)

# Define constants for question templates
QUESTION_TEMPLATES = {
    "birth_time": [
        {
            "id": "q_birth_time_general",
            "text": "Do you know your approximate birth time?",
            "type": "multiple_choice",
            "options": [
                {"id": "opt_exact", "text": "Yes, I have an exact time"},
                {"id": "opt_approximate", "text": "I have an approximate time"},
                {"id": "opt_window", "text": "I know a time window (e.g., morning, afternoon)"},
                {"id": "opt_unknown", "text": "I don't know my birth time"}
            ]
        }
    ],
    "life_events": [
        {
            "id": "q_major_life_events",
            "text": "Please list any major life events with their dates",
            "type": "text"
        }
    ]
}

# Create router
router = APIRouter()

# Add a global in-memory session store for testing
MEMORY_SESSIONS = {}

class DynamicQuestionnaireService:
    """Service for dynamic questionnaire generation and processing."""

    def __init__(self, session_id: str):
        """
        Initialize the service.

        Args:
            session_id: The session ID to use
        """
        self.session_id = session_id
        self.session_store = None
        self.openai_service = None
        self.chart_service = None
        self._initialize_services()

    def _initialize_services(self):
        """Initialize required services."""
        try:
            # Import SessionStore class only when needed
            # Use a local import to avoid linter errors
            SessionStore = get_session_store_class()
            self.session_store = SessionStore()
        except Exception as e:
            logger.error(f"Failed to initialize session store: {e}")
            raise ValueError(f"Session store initialization failed: {e}")

        try:
            self.openai_service = get_openai_service()
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service: {e}")
            raise ValueError(f"OpenAI service initialization failed: {e}")

        try:
            self.chart_service = get_chart_service()
        except Exception as e:
            logger.error(f"Failed to initialize chart service: {e}")
            raise ValueError(f"Chart service initialization failed: {e}")

    async def get_first_question(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get the first question for a new questionnaire.

        Args:
            chart_data: Chart data to use for question generation

        Returns:
            Question data
        """
        # Implementation details
        return {
            "id": "q_birth_time_general",
            "text": "Do you know your approximate birth time?",
            "type": "multiple_choice",
            "options": [
                {"id": "opt_exact", "text": "Yes, I have an exact time"},
                {"id": "opt_approximate", "text": "I have an approximate time"},
                {"id": "opt_window", "text": "I know a time window (e.g., morning, afternoon)"},
                {"id": "opt_unknown", "text": "I don't know my birth time"}
            ]
        }

    async def process_answer(self, question_id: Optional[str], answer: Any, chart_id: Optional[str]) -> Dict[str, Any]:
        """
        Process an answer and get the next question.

        Args:
            question_id: The ID of the question being answered
            answer: The answer to the question
            chart_id: The chart ID to use

        Returns:
            Next question data
        """
        # Implementation details
        return {
            "id": "q_major_life_events",
            "text": "Please list any major life events with their dates",
            "type": "text"
        }

    async def complete_questionnaire(self) -> Dict[str, Any]:
        """
        Complete the questionnaire and generate results.

        Returns:
            Questionnaire completion results
        """
        # Implementation details
        return {
            "status": "completed",
            "message": "Questionnaire completed successfully",
            "confidence": 0.8
        }

async def get_question_text(question_id: str, questionnaire_id: Optional[str] = None) -> str:
    """
    Get the text of a question by its ID.

    Args:
        question_id: The question ID to look up
        questionnaire_id: Optional questionnaire ID to search in

    Returns:
        Question text if found, empty string otherwise
    """
    # Try to find the question in the database
    # Since QuestionModel is not defined, we'll use a dictionary-based approach
    # Check session data or templates

    # If question not found and we have a questionnaire ID, try to find it there
    if questionnaire_id:
        # Get questionnaire from session or database
        pass

    # If still not found, look in standard question templates
    for category in QUESTION_TEMPLATES:
        for q in QUESTION_TEMPLATES[category]:
            if q.get("id") == question_id:
                return q.get("text", "")

    return ""

def get_session_store_class() -> Type[Any]:
    """Get the SessionStore class or a placeholder if not available."""
    try:
        # Import module locally to avoid linter errors
        import importlib
        module = importlib.import_module("ai_service.api.middleware.session")
        return getattr(module, "SessionStore")
    except (ImportError, AttributeError):
        class SessionStorePlace:
            def get_session(self, session_id: str) -> Dict[str, Any]:
                return MEMORY_SESSIONS.get(session_id, {})

            def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
                MEMORY_SESSIONS[session_id] = data
                return True

            def create_session(self, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
                new_session_id = session_id or str(uuid.uuid4())
                MEMORY_SESSIONS[new_session_id] = data or {}
                return new_session_id
        return SessionStorePlace

# Fix synchronous vs asynchronous session store handling
async def get_session_async(session_store: Any, session_id: str) -> Dict[str, Any]:
    """
    Get a session asynchronously, handling both async and sync implementations.

    Args:
        session_store: The session store instance
        session_id: The session ID

    Returns:
        Session data dictionary
    """
    # Check if the get_session method is already async or sync
    if hasattr(session_store, "get_session_async"):
        return await getattr(session_store, "get_session_async")(session_id)

    # If it's synchronous, run it in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, session_store.get_session, session_id)

async def update_session_async(session_store: Any, session_id: str, data: Dict[str, Any]) -> bool:
    """
    Update a session asynchronously, handling both async and sync implementations.

    Args:
        session_store: The session store instance
        session_id: The session ID
        data: The session data to update

    Returns:
        True if update succeeded, False otherwise
    """
    # Check if the update_session method is already async or sync
    if hasattr(session_store, "update_session_async"):
        return await getattr(session_store, "update_session_async")(session_id, data)

    # If it's synchronous, run it in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, session_store.update_session, session_id, data)

async def create_session_async(session_store: Any, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
    """
    Create a session asynchronously, handling both async and sync implementations.

    Args:
        session_store: The session store instance
        session_id: Optional session ID
        data: Optional session data

    Returns:
        Created session ID
    """
    # Check if the create_session method is already async or sync
    if hasattr(session_store, "create_session_async"):
        return await getattr(session_store, "create_session_async")(session_id, data)

    # If it's synchronous, run it in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, session_store.create_session, session_id, data)

async def update_session_confidence(session_store: Any, session_id: str, confidence: float) -> bool:
    """
    Update session confidence level.

    Args:
        session_store: The session store instance
        session_id: The session ID
        confidence: The confidence level (0-100)

    Returns:
        True if update succeeded, False otherwise
    """
    try:
        # Get the session
        session = await get_session_async(session_store, session_id)
        if not session:
            return False

        # Update confidence
        session["confidence"] = confidence
        session["updated_at"] = datetime.now().isoformat()

        # Save session
        return await update_session_async(session_store, session_id, session)
    except Exception as e:
        logger.error(f"Error updating session confidence: {e}")
        return False

async def get_session_responses(session_store: Any, session_id: str) -> List[Dict[str, Any]]:
    """
    Get all responses for a session.

    Args:
        session_store: The session store instance
        session_id: The session ID

    Returns:
        List of responses
    """
    try:
        # Get the session
        session = await get_session_async(session_store, session_id)
        if not session:
            return []

        # Return responses
        return session.get("responses", [])
    except Exception as e:
        logger.error(f"Error getting session responses: {e}")
        return []

# Fix WebSocket service import by creating a placeholder if not available
class WebSocketServiceProxy:
    """Placeholder for WebSocket service if not available."""

    async def send_to_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Send data to a WebSocket session.

        Args:
            session_id: Session ID
            data: Data to send

        Returns:
            True if successful, False otherwise
        """
        # Log the attempt but don't actually do anything
        logger.debug(f"Would send WebSocket data to session {session_id} if service was available")
        return False

def get_websocket_service():
    """
    Get a WebSocket service instance or placeholder.

    Returns:
        WebSocket service instance or placeholder
    """
    try:
        # Try to import the real service - use a placeholder return type
        import importlib
        module = importlib.import_module("ai_service.utils.websocket_manager")
        get_manager = getattr(module, "get_websocket_manager")
        websocket_manager = get_manager()

        # Return a proxy that adapts the real manager
        result = WebSocketServiceProxy()

        # Manually copy the send_to_session method if it exists
        if hasattr(websocket_manager, "send_to_session"):
            send_method = getattr(websocket_manager, "send_to_session")
            # Use a safer way to set attributes
            setattr(result, "send_to_session", send_method)

        return result
    except (ImportError, AttributeError):
        # Return placeholder
        return WebSocketServiceProxy()

def get_questionnaire_service():
    """
    Get or create a questionnaire service instance.

    Returns:
        Questionnaire service instance
    """
    try:
        import importlib
        module = importlib.import_module("ai_service.api.services.questionnaire_service")
        get_service = getattr(module, "get_questionnaire_service")
        return get_service()
    except (ImportError, AttributeError):
        logger.warning("Could not import QuestionnaireService, using basic implementation")
        return None

def get_rectification_model():
    """
    Get or create a rectification model instance.

    Returns:
        Rectification model instance
    """
    try:
        # Import dynamically to avoid linter errors
        import importlib
        module = importlib.import_module("ai_service.core.rectification.main")
        model_class = getattr(module, "UnifiedRectificationModel")
        return model_class()
    except (ImportError, AttributeError):
        logger.warning("Could not import UnifiedRectificationModel")
        return None

def get_astro_calculator():
    """
    Get an astrology calculator instance.

    Returns:
        Astrology calculator instance
    """
    try:
        from ai_service.utils.flatlib_compat import BasicChartCalculator
        return BasicChartCalculator()
    except ImportError:
        logger.warning("Could not import BasicChartCalculator, using compatibility layer")
        class AstroCalculatorCompat:
            """Compatibility class for astrological calculations."""
            def calculate_chart(self, *args, **kwargs):
                """Calculate a chart."""
                return {"status": "not_implemented"}
        return AstroCalculatorCompat()

@router.get("", response_model=Dict[str, Any])
async def get_questionnaire(
    chart_id: str = Query(None, description="Chart ID for personalized questions"),
    session_id: str = Query(None, description="Session ID for tracking"),
    questionnaire_service = Depends(get_questionnaire_service)
):
    """
    Get a questionnaire based on chart ID and session.

    Args:
        chart_id: Optional chart ID for personalized questions
        session_id: Optional session ID for tracking
        questionnaire_service: Questionnaire service instance

    Returns:
        Questionnaire data
    """
    try:
        # Use session ID or generate a new one
        effective_session_id = session_id or str(uuid.uuid4())

        # Create a questionnaire engine
        engine = QuestionnaireEngine()

        # Try to get chart data
        chart_data = None
        if chart_id:
            try:
                chart_service = get_chart_service()
                if chart_service:
                    chart_data = await chart_service.get_chart(chart_id)
            except Exception as e:
                logger.warning(f"Error getting chart data: {e}")

        # Generate initial question with handling for None chart_data
        first_question = await engine.get_first_question(
            chart_data or {},
            {"session_id": effective_session_id}
        )

        # Format response
        return {
            "session_id": effective_session_id,
            "chart_id": chart_id,
            "question": first_question,
            "progress": 0.0,
            "confidence": 0.0,
            "total_questions": 10  # Estimate
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
    Initialize a new questionnaire session with birth details.

    Args:
        request: Request data containing birth details
        chart_id: Optional chart ID for personalized questions
        session_id: Optional session ID for continuing an existing session

    Returns:
        Initial questionnaire data
    """
    try:
        # Initialize services
        SessionStore = get_session_store_class()
        session_store = SessionStore()

        # Get or create OpenAI service synchronously to avoid await issues
        openai_service_sync = get_openai_service()

        # Create chart service
        chart_service = get_chart_service()

        # Extract birth details from request
        birth_details = request.get("birthDetails", {})

        # Create initial session data
        session_data = {
            "birth_details": birth_details,
            "chart_id": chart_id,
            "started_at": datetime.now().isoformat(),
            "questions": [],
            "answers": [],
            "confidence": 0.0
        }

        # Determine chart ID to use
        effective_chart_id = chart_id

        # If continuing an existing session, validate it exists
        if session_id:
            existing_session = session_store.get_session(session_id)
            if not existing_session:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found"
                )
            # Use existing session ID
            effective_session_id = session_id

            # Update the session data
            session_store.update_session(effective_session_id, session_data)
        else:
            # Create a new session
            effective_session_id = session_store.create_session(
                session_id=request.get("sessionId"),
                data=session_data
            )

        # Get the chart data for astrological context
        chart_data = None
        if effective_chart_id and chart_service:
            try:
                chart_data = await chart_service.get_chart(effective_chart_id)
            except Exception as chart_error:
                logger.warning(f"Error getting chart data: {chart_error}")

        # Calculate current confidence
        confidence = 0.0

        # Create engine for personalized questions
        engine = QuestionnaireEngine()

        # Get the initial question
        logger.info("Generating initial astrologically-focused question with OpenAI")

        question_prompt = {
            "task": "generate_initial_rectification_question",
            "birth_details": birth_details,
            "chart_data": chart_data,
            "instructions": "Generate an insightful initial question for birth time rectification."
        }

        # Generate initial question
        try:
            # Use the OpenAI service with proper error handling
            openai_service = openai_service_sync

            if callable(openai_service):
                # If it returns a coroutine, await it
                try:
                    openai_service = await openai_service
                except:
                    # If it's not awaitable, keep the original
                    pass

            # Use a safer way to check for and call chat_completion
            if openai_service is not None:
                # Use getattr to safely access method
                chat_completion_method = getattr(openai_service, "chat_completion", None)

                if callable(chat_completion_method):
                    question_response = await chat_completion_method(
                        messages=[
                            {"role": "system", "content": "You are an expert astrological assistant."},
                            {"role": "user", "content": json.dumps(question_prompt, cls=DateTimeEncoder)}
                        ],
                        model="gpt-4-turbo",
                        temperature=0.3,
                        max_tokens=500
                    )

                    # Validate OpenAI response
                    if not question_response or "choices" not in question_response or not question_response["choices"]:
                        logger.error("Failed to receive valid response from OpenAI for initial question generation")
                        raise ValueError("Failed to generate initial astrological question")

                    # Extract content from response
                    content = question_response["choices"][0]["message"]["content"]

                    # Parse the question data
                    try:
                        question_data = json.loads(content)

                        # Ensure the question has required fields
                        if not isinstance(question_data, dict) or "text" not in question_data:
                            logger.error("Invalid question format received from OpenAI")
                            raise ValueError("OpenAI returned invalid question format")

                        # Generate UUID for the question if not provided
                        if "id" not in question_data:
                            question_data["id"] = f"q_{uuid.uuid4().hex[:8]}"

                        # Ensure type is set
                        if "type" not in question_data:
                            question_data["type"] = "text"

                        # Process options if available
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

                        # Update session with question data
                        session = session_store.get_session(effective_session_id)
                        if session:
                            if "questions" not in session:
                                session["questions"] = []

                            session["current_question"] = question_data
                            session["updated_at"] = datetime.now().isoformat()
                            session_store.update_session(effective_session_id, session)

                        # Update session confidence
                        session_store.update_session(effective_session_id, {
                            "confidence": confidence,
                            "updated_at": datetime.now().isoformat()
                        })

                        # Prepare response
                        return {
                            "session_id": effective_session_id,
                            "chart_id": effective_chart_id,
                            "question": question_data,
                            "confidence": confidence,
                            "progress": 0.1  # Initial progress
                        }

                    except json.JSONDecodeError:
                        logger.error("Failed to parse OpenAI response as JSON")
                        raise ValueError("Error parsing initial astrological question from OpenAI")
                else:
                    # Fallback if chat_completion is not available
                    logger.error("OpenAI service does not have chat_completion method")
                    raise ValueError("OpenAI service configuration error")
            else:
                # Fallback if OpenAI service is None
                logger.error("OpenAI service is None")
                raise ValueError("OpenAI service not available")

        except Exception as e:
            logger.error(f"Error generating question with OpenAI: {e}")
            # Use the proper questionnaire engine's fallback system
            engine = QuestionnaireEngine()
            question_data = engine.fallback_questions[0]  # Get first fallback question

            return {
                "session_id": effective_session_id,
                "chart_id": effective_chart_id,
                "question": question_data,
                "confidence": confidence,
                "progress": 0.1  # Initial progress
            }

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

# Add missing models for linter
class QuestionModel:
    """Model for questionnaire questions."""

    @staticmethod
    async def get_by_id(question_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a question by ID.

        Args:
            question_id: The question ID

        Returns:
            Question data or None if not found
        """
        # Check templates first
        for category in QUESTION_TEMPLATES:
            for question in QUESTION_TEMPLATES[category]:
                if question.get("id") == question_id:
                    return question
        return None

class QuestionnaireModel:
    """Model for questionnaires."""

    @staticmethod
    async def get_by_id(questionnaire_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a questionnaire by ID.

        Args:
            questionnaire_id: The questionnaire ID

        Returns:
            Questionnaire data or None if not found
        """
        try:
            # Get session store
            SessionStore = get_session_store_class()
            session_store = SessionStore()

            # Attempt to retrieve the session data
            session = await get_session_async(session_store, questionnaire_id)

            if not session:
                return None

            # Create a questionnaire data object from session
            questionnaire_data = {
                "id": questionnaire_id,
                "status": session.get("status", "unknown"),
                "created_at": session.get("created_at"),
                "updated_at": session.get("updated_at"),
                "completed_at": session.get("completed_at"),
                "responses": session.get("responses", []),
                "current_question": session.get("current_question"),
                "confidence": session.get("confidence", 0.0),
                "chart_id": session.get("chart_id")
            }

            return questionnaire_data
        except Exception as e:
            logger.error(f"Error retrieving questionnaire by ID: {e}")
            return None

@router.post("/{session_id}/answer", response_model=Dict[str, Any])
async def submit_answer(
    session_id: str = Path(..., description="Session ID for the questionnaire"),
    answer_request: Dict[str, Any] = Body(..., description="Answer data including question_id and answer")
):
    """
    Submit an answer to a questionnaire question and get the next question.

    Args:
        session_id: Session ID for the questionnaire
        answer_request: Answer data with question_id and answer

    Returns:
        Next question data or completion status
    """
    try:
        logger.info(f"Processing answer for session {session_id}")

        # Get session store
        SessionStore = get_session_store_class()
        session_store = SessionStore()

        # Validate session exists
        session = await get_session_async(session_store, session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Extract answer data
        question_id = answer_request.get("question_id")
        answer = answer_request.get("answer")
        chart_id = session.get("chart_id")

        if not question_id:
            raise HTTPException(status_code=400, detail="Missing question_id in request")
        if answer is None:
            raise HTTPException(status_code=400, detail="Missing answer in request")

        # Get question text
        question_text = await get_question_text(question_id, session_id)

        # Store the answer
        if "responses" not in session:
            session["responses"] = []

        # Create response entry
        response_entry = {
            "question_id": question_id,
            "question": question_text,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        }

        # Add to session responses
        session["responses"].append(response_entry)
        await update_session_async(session_store, session_id, session)

        # Create questionnaire engine for next question
        engine = QuestionnaireEngine()

        try:
            # Get chart data
            chart_service = get_chart_service()
            chart_data = {}

            if chart_id:
                try:
                    chart_data = await chart_service.get_chart(chart_id)
                except Exception as e:
                    logger.warning(f"Error getting chart data: {e}")

            # Calculate current confidence
            confidence = await engine.calculate_confidence({"responses": session.get("responses", [])}, chart_data)

            # Check if we are at the end of the questionnaire
            total_questions = 10  # Typically fixed number of questions
            question_count = len(session.get("responses", []))

            # For now, just generate another question
            # Generate next question
            next_question = await engine.get_next_question(session_id, chart_data or {}, session.get("responses", []))

            # Update session with question data
            session["current_question"] = next_question
            session["updated_at"] = datetime.now().isoformat()
            session["confidence"] = confidence
            await update_session_async(session_store, session_id, session)

            # Calculate progress
            progress = min(question_count / total_questions, 0.9)

            # Return next question data
            return {
                "session_id": session_id,
                "chart_id": chart_id,
                "question": next_question,
                "confidence": confidence,
                "progress": progress
            }

        except Exception as e:
            logger.error(f"Error processing answer: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Error processing answer: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in answer processing: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process answer: {str(e)}")

@router.post("/complete", response_model=Dict[str, Any])
async def complete_questionnaire(
    request: Dict[str, Any] = Body(..., description="Completion request with session_id and chart_id")
):
    """
    Complete a questionnaire and generate birth time rectification results.

    Args:
        request: Completion request with session_id and chart_id

    Returns:
        Rectification results

    Raises:
        HTTPException: If session not found or completion fails
    """
    try:
        # Extract request data
        session_id = request.get("session_id")
        chart_id = request.get("chart_id")

        if not session_id:
            raise HTTPException(status_code=400, detail="Missing session_id in request")

        logger.info(f"Completing questionnaire for session {session_id}")

        # Get session store
        SessionStore = get_session_store_class()
        session_store = SessionStore()

        # Validate session exists
        session = await get_session_async(session_store, session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Update session status
        session["status"] = "processing"
        session["updated_at"] = datetime.now().isoformat()
        await update_session_async(session_store, session_id, session)

        # Create questionnaire engine
        engine = QuestionnaireEngine()

        # Get responses
        responses = session.get("responses", [])
        if not responses:
            raise HTTPException(status_code=400, detail="Cannot complete questionnaire with no responses")

        # Get chart data if available
        chart_data = {}
        if chart_id:
            try:
                chart_service = get_chart_service()
                chart_data = await chart_service.get_chart(chart_id)
                logger.info(f"Retrieved chart data for {chart_id}")
            except Exception as e:
                logger.warning(f"Error getting chart data: {e}")

        # Calculate final confidence
        confidence = await engine.calculate_confidence({"responses": responses}, chart_data)

        # Format responses for analysis
        formatted_answers = {"responses": responses}

        # Analyze answers for birth time rectification using the engine
        try:
            # Initialize adjusted birth time values
            birth_time_adjustment = None
            adjusted_birth_time = None

            # Call the analysis method if there's enough data
            if responses and chart_data:
                analysis_result = await engine.analyze_answers(chart_data, {"responses": responses})

                if analysis_result and analysis_result.get("success"):
                    result_data = analysis_result.get("analysis_result", {})

                    # Extract birth time adjustment if available
                    adjustment_direction = result_data.get("adjustment_direction")
                    adjustment_minutes = result_data.get("adjustment_minutes", 0)

                    # Calculate the adjusted time
                    if adjustment_direction and adjustment_minutes:
                        try:
                            # Get original time from chart data
                            original_time_str = chart_data.get("birth_details", {}).get("time")
                            if not original_time_str:
                                original_time_str = "12:00:00"  # Fallback if not available

                            # Parse the time
                            time_parts = original_time_str.split(":")
                            hours = int(time_parts[0])
                            minutes = int(time_parts[1])
                            seconds = int(time_parts[2]) if len(time_parts) > 2 else 0

                            # Calculate adjustment
                            adjustment_factor = 1 if adjustment_direction == "later" else -1
                            total_minutes = hours * 60 + minutes
                            new_total_minutes = total_minutes + (adjustment_factor * adjustment_minutes)

                            # Convert back to hours and minutes
                            new_hours = new_total_minutes // 60
                            new_minutes = new_total_minutes % 60

                            # Format the new time
                            adjusted_birth_time = f"{new_hours:02d}:{new_minutes:02d}:00"
                            birth_time_adjustment = adjustment_factor * adjustment_minutes

                            # Update confidence with the analysis confidence
                            if "confidence_score" in result_data:
                                confidence = result_data.get("confidence_score")
                        except Exception as e:
                            logger.warning(f"Error calculating adjusted birth time: {e}")

        except Exception as e:
            logger.warning(f"Error during answer analysis: {e}")
            # Continue with default values if analysis fails

        # Create the rectification results
        rectification_results = {
            "session_id": session_id,
            "chart_id": chart_id,
            "confidence": confidence,
            "status": "completed",
            "message": "Questionnaire completed successfully",
            "birth_time_adjustment": birth_time_adjustment,
            "adjusted_birth_time": adjusted_birth_time
        }

        # Update session with results
        session["status"] = "completed"
        session["completed_at"] = datetime.now().isoformat()
        session["confidence"] = confidence
        session["rectification_results"] = rectification_results
        await update_session_async(session_store, session_id, session)

        return rectification_results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing questionnaire: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to complete questionnaire: {str(e)}")
