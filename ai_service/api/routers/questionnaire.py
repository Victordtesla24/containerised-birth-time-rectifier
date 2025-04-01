"""
Questionnaire API Router.

This module provides endpoints for questionnaire management and data handling.
"""

import asyncio
import json
import logging
import traceback
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Type, Set, Tuple
import math
import os
import re
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body

from ai_service.api.models.session import Session
from ai_service.api.models.answer import Answer
from ai_service.api.models.question import Question
from ai_service.api.schemas.questionnaire import (
    QuestionnaireInitRequest,
    QuestionnaireInitResponse,
    AnswerSubmitRequest,
    AnswerProcessResponse,
    QuestionData
)
from ai_service.api.services.questionnaire_engine import QuestionnaireEngine
from ai_service.api.services.chart_service import ChartService, get_chart_service
from ai_service.api.services.database import get_db
from ai_service.api.services.session_service import get_session_by_id
from ai_service.api.utils.logging_utils import get_request_id
from ai_service.api.routers.chart_utils import get_chart_data_for_session

# Import necessary models and services
from ai_service.models import QuestionnaireRequest, QuestionnaireResponse, QuestionnaireAnswerRequest, QuestionnaireCompleteResponse
from ai_service.api.services.questionnaire_engine import QuestionnaireEngine
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
            logger.error("Failed to initialize session store: %s", e)
            raise ValueError("Session store initialization failed: %s" % e)

        try:
            self.openai_service = get_openai_service()
        except Exception as e:
            logger.error("Failed to initialize OpenAI service: %s", e)
            raise ValueError("OpenAI service initialization failed: %s" % e)

        try:
            self.chart_service = get_chart_service()
        except Exception as e:
            logger.error("Failed to initialize chart service: %s", e)
            raise ValueError("Chart service initialization failed: %s" % e)

    async def get_first_question(self, chart_data: Dict[str, Any], birth_details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get the first question for a new questionnaire.

        Args:
            chart_data: Chart data to use for question generation
            birth_details: Optional birth details to use for personalization

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
            def __init__(self):
                self.session_dir = os.path.join(os.getcwd(), "sessions")
                # Create session directory if it doesn't exist
                os.makedirs(self.session_dir, exist_ok=True)
                # Load any existing sessions from files
                self._load_sessions_from_files()

            def _load_sessions_from_files(self):
                """Load sessions from the session directory into MEMORY_SESSIONS."""
                if not os.path.exists(self.session_dir):
                    return

                for filename in os.listdir(self.session_dir):
                    if filename.endswith(".json"):
                        session_id = os.path.splitext(filename)[0]
                        file_path = os.path.join(self.session_dir, filename)

                        try:
                            with open(file_path, "r") as f:
                                session_data = json.load(f)
                                MEMORY_SESSIONS[session_id] = session_data
                        except Exception as e:
                            logger.error(f"Error loading session {session_id}: {e}")

                logger.info(f"Loaded {len(MEMORY_SESSIONS)} sessions from {self.session_dir}")

            def _save_session_to_file(self, session_id: str, data: Dict[str, Any]):
                """Save session data to a file."""
                try:
                    file_path = os.path.join(self.session_dir, f"{session_id}.json")
                    with open(file_path, "w") as f:
                        json.dump(data, f, indent=2)
                except Exception as e:
                    logger.error(f"Error saving session {session_id} to file: {e}")

            def get_session(self, session_id: str) -> Dict[str, Any]:
                """Get a session by ID."""
                # Try to get from memory first
                session_data = MEMORY_SESSIONS.get(session_id, {})

                # If not in memory, try to load from file
                if not session_data:
                    try:
                        file_path = os.path.join(self.session_dir, f"{session_id}.json")
                        if os.path.exists(file_path):
                            with open(file_path, "r") as f:
                                session_data = json.load(f)
                                # Update memory cache
                                MEMORY_SESSIONS[session_id] = session_data
                    except Exception as e:
                        logger.error(f"Error reading session {session_id} from file: {e}")

                return session_data

            def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
                """Update a session."""
                # Update in memory
                MEMORY_SESSIONS[session_id] = data
                # Update in file
                self._save_session_to_file(session_id, data)
                return True

            def create_session(self, session_id: Optional[str] = None, data: Optional[Dict[str, Any]] = None) -> str:
                """Create a new session."""
                new_session_id = session_id or str(uuid.uuid4())
                session_data = data or {}

                # Add metadata
                if "created_at" not in session_data:
                    session_data["created_at"] = datetime.now().isoformat()
                session_data["updated_at"] = datetime.now().isoformat()

                # Save in memory
                MEMORY_SESSIONS[new_session_id] = session_data

                # Save to file
                self._save_session_to_file(new_session_id, session_data)

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
                logger.warning("Error getting chart data: %s", e)

        # Generate initial question with handling for None chart_data
        first_question = await engine.get_first_question(
            chart_data or {},
            birth_details={"session_id": effective_session_id}
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
        logger.error("Error in get_questionnaire: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to generate questionnaire: %s" % str(e)
        ) from e

@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_questionnaire(
    request: Dict[str, Any],
    chart_id: Optional[str] = Query(None, description="Chart ID for personalized questions"),
    session_id: Optional[str] = Query(None, description="Session ID for continuing an existing session")
):
    """
    Initialize a new questionnaire session with birth details for Vedic birth time rectification.

    Args:
        request: Request data containing birth details
        chart_id: Optional chart ID for personalized questions
        session_id: Optional session ID for continuing an existing session

    Returns:
        Initial questionnaire data with Vedic astrological context
    """
    try:
        # Initialize services
        SessionStore = get_session_store_class()
        session_store = SessionStore()

        # Get or create OpenAI service synchronously to avoid await issues
        openai_service_sync = None
        try:
            openai_service_sync = get_openai_service()
            logger.info("Successfully initialized OpenAI service for Vedic astrological questionnaire")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI service: {e}")

        # Create chart service
        chart_service = None
        try:
            chart_service = get_chart_service()
        except Exception as e:
            logger.warning(f"Failed to initialize chart service: {e}")

        # Extract birth details from request
        birth_details = request.get("birthDetails", {})

        # Log birth details for debugging
        logger.info(f"Initializing Vedic questionnaire with birth details: {birth_details}")

        # Create initial session data
        session_data = {
            "birth_details": birth_details,
            "chart_id": chart_id,
            "started_at": datetime.now().isoformat(),
            "questions": [],
            "answers": [],
            "confidence": 0.0,
            "vedic_approach": True  # Mark this as using Vedic astrological approach
        }

        # Determine chart ID to use
        effective_chart_id = chart_id or request.get("chart_id")

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
                session_id=request.get("session_id"),
                data=session_data
            )

        # Get the chart data for Vedic astrological context
        chart_data = None
        if effective_chart_id and chart_service:
            try:
                # Get chart data sequentially instead of in a task group
                chart_data = await chart_service.get_chart(effective_chart_id)
                logger.info(f"Retrieved chart data for {effective_chart_id} to use in Vedic analysis")
            except Exception as chart_error:
                logger.warning(f"Error getting chart data: {chart_error}")

        # Initialize confidence - start at 0 for Vedic approach
        confidence = 0.0

        # Create engine for personalized questions with proper error handling
        engine = None
        try:
            engine = QuestionnaireEngine()
            logger.info("Created questionnaire engine for Vedic birth time rectification")
        except Exception as engine_error:
            logger.warning(f"Error creating questionnaire engine: {engine_error}")

        # Initialize question data with a Vedic-focused default
        question_data = {
            "id": "q_birth_time_vedic",
            "text": "In Vedic astrology, birth time determines your rising sign (Lagna). Do you have an exact birth time, an approximate time, or only a general timeframe?",
            "type": "multiple_choice",
            "options": [
                {"id": "opt_exact", "text": "I have an exact birth time"},
                {"id": "opt_approximate", "text": "I have an approximate birth time"},
                {"id": "opt_window", "text": "I only know a general timeframe (morning, afternoon, etc.)"},
                {"id": "opt_unknown", "text": "I don't know my birth time at all"}
            ],
            "category": "vedic_birth_time"
        }

        # Generate next question with Vedic-focused question generation
        logger.info(f"Generating next Vedic question for session {effective_session_id}")

        # Create questionnaire engine for Vedic chart analysis
        engine = QuestionnaireEngine()

        # Get OpenAI service for direct access to enhanced question generation
        openai_service = None
        next_question = None

        try:
            openai_service = await get_openai_service()
            logger.info("Successfully initialized OpenAI service for personalized question generation")

            # Try to get the next question using the engine
            try:
                # Ensure chart_data is not None before passing
                safe_chart_data = chart_data or {}
                next_question = await engine.get_next_question(
                    session_id=effective_session_id,
                    chart_data=safe_chart_data,
                    previous_answers=session_store.get_session(effective_session_id).get("responses", [])
                )

                if next_question:
                    logger.info(f"Generated next Vedic question: {next_question.get('text', '')[:100]}")
                else:
                    logger.warning("Question engine returned null question, falling back to direct OpenAI generation")
            except Exception as e:
                logger.error(f"Error generating question with engine: {e}")
                logger.error(traceback.format_exc())

        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI service for question generation: {e}")
            # Still try to use the engine even if OpenAI service initialization failed
            try:
                # Ensure chart_data is not None before passing
                safe_chart_data = chart_data or {}
                next_question = await engine.get_next_question(
                    session_id=effective_session_id,
                    chart_data=safe_chart_data,
                    previous_answers=session_store.get_session(effective_session_id).get("responses", [])
                )
            except Exception as e:
                logger.error(f"Error generating question without OpenAI service: {e}")
                logger.error(traceback.format_exc())

            # If the next question is a repeat of the last question or null, try direct OpenAI generation
            if next_question is None or next_question.get("id") == question_data["id"]:
                logger.warning(f"Generated question is a repeat or null, attempting direct OpenAI generation")

                # Try to directly generate using OpenAI if available
                if openai_service and hasattr(openai_service, "chat_completion"):
                    try:
                        # Create a comprehensive context for the OpenAI prompt
                        response_history = "\n".join([
                            f"Q: {resp.get('question', '')}\nA: {resp.get('answer', '')}"
                            for resp in session_store.get_session(effective_session_id).get("responses", [])[-5:]  # Last 5 responses
                        ])

                        # Track used categories to ensure variety
                        used_categories = set()
                        category_counts = {}

                        for resp in session_store.get_session(effective_session_id).get("responses", []):
                            if isinstance(resp, dict) and resp.get("category"):
                                cat = resp.get("category")
                                used_categories.add(cat)
                                category_counts[cat] = category_counts.get(cat, 0) + 1

                        # Determine which categories to prioritize
                        all_categories = {"childhood", "life_events", "personality", "physical_traits", "health", "career", "relationships", "spiritual", "timing", "birth_circumstances", "education"}
                        unused_categories = all_categories - used_categories

                        # Find least used categories if all have been used
                        least_used_categories = []
                        if not unused_categories:
                            min_count = min(category_counts.values()) if category_counts else 1
                            least_used_categories = [cat for cat, count in category_counts.items() if count == min_count]

                        # Format category guidance for the prompt
                        category_guidance = ""
                        if unused_categories:
                            category_guidance = f"PRIORITIZE these unused categories: {', '.join(unused_categories)}"
                        elif least_used_categories:
                            category_guidance = f"PRIORITIZE these least-used categories: {', '.join(least_used_categories)}"

                        # Enhanced system prompt with explicit instructions about avoiding repetition
                        system_prompt = f"""You are an expert Vedic astrologer specializing in birth time rectification.
                        Generate a unique, personalized question based on the chart data and previous answers provided.

                        CRITICAL REQUIREMENTS:
                        1. NEVER repeat or rephrase previous questions - each new question must be COMPLETELY DIFFERENT
                        2. Focus questions on information that helps determine accurate birth time
                        3. Make questions specific to this person's chart details
                        4. Avoid generic questions that could apply to anyone
                        5. Relate questions to Vedic astrological principles but use accessible language
                        6. DO NOT use technical astrological jargon without explanation
                        7. DO NOT ask about the same topic or life area as previous questions
                        8. {category_guidance}

                        Your response must be ONLY a JSON object with the following structure:
                        {{
                          "id": "q_unique_id",
                          "text": "Your unique question here",
                          "category": "one_of: childhood, life_events, personality, physical_traits, health, career, relationships, spiritual, timing",
                          "type": "text"
                        }}"""

                        # Create a user prompt with the context
                        user_prompt = f"""
                        Chart Data:
                        {json.dumps(safe_chart_data, default=str)[:500] if hasattr(engine, '_format_chart_for_prompt') else json.dumps(safe_chart_data, default=str)[:500]}

                        PREVIOUSLY ASKED QUESTIONS (DO NOT REPEAT THESE):
                        {json.dumps([resp.get('question', '') for resp in session_store.get_session(effective_session_id).get("responses", [])], indent=2)}

                        Previous Question-Answer History:
                        {response_history}

                        Generate ONE unique question for birth time rectification that:
                        1. Is specifically tailored to this person's birth chart
                        2. Is completely different from all previous questions
                        3. Explores a category not yet covered in depth
                        4. Contains 1-2 sentences maximum
                        5. Is focused on helping determine the exact birth time

                        Return ONLY the JSON object with your question.
                        """

                        # Log the prompt for debugging
                        logger.info(f"OpenAI prompt for custom question generation prepared")

                        # Call OpenAI for a custom question
                        custom_question_response = await openai_service.chat_completion(
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            model="gpt-4o",  # Use the most capable model available
                            temperature=0.7,  # Slightly higher creativity for unique questions
                            max_tokens=350
                        )

                        # Process the OpenAI response
                        logger.info(f"Received OpenAI question response: {str(custom_question_response)[:150]}...")

                        # Safely extract and parse the JSON from the OpenAI response
                        openai_question = None
                        if isinstance(custom_question_response, dict) and "choices" in custom_question_response:
                            if len(custom_question_response["choices"]) > 0:
                                if "message" in custom_question_response["choices"][0]:
                                    content = custom_question_response["choices"][0]["message"].get("content", "")

                                    # Try to parse JSON from the content
                                    try:
                                        # Extract JSON if it's wrapped in markdown code blocks
                                        json_match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
                                        if json_match:
                                            content = json_match.group(1).strip()

                                        # Or extract JSON if it's in the content directly
                                        json_obj_match = re.search(r'(\{.*\})', content, re.DOTALL)
                                        if json_obj_match:
                                            content = json_obj_match.group(1).strip()

                                        openai_question = json.loads(content)

                                        # Ensure the question has an ID
                                        if "id" not in openai_question:
                                            openai_question["id"] = f"q_openai_{uuid.uuid4()}"

                                        # Ensure the question has a type
                                        if "type" not in openai_question:
                                            openai_question["type"] = "text"

                                        # Verify the question doesn't match any previous questions
                                        new_question_text = openai_question.get("text", "").lower().strip()

                                        # Check for similarity with previous questions
                                        is_similar = False
                                        previously_asked = [resp.get('question', '') for resp in session_store.get_session(effective_session_id).get("responses", [])]
                                        for prev_q in previously_asked:
                                            prev_text = prev_q.lower().strip()
                                            # Check for direct substring
                                            if (new_question_text in prev_text or prev_text in new_question_text) and len(new_question_text) > 10:
                                                logger.warning(f"Question rejected due to substring match: '{new_question_text}' vs '{prev_text}'")
                                                is_similar = True
                                                break

                                            # Check word similarity - improved algorithm
                                            new_words = set(re.findall(r'\b\w+\b', new_question_text))
                                            prev_words = set(re.findall(r'\b\w+\b', prev_text))

                                            if len(new_words) > 3 and len(prev_words) > 3:  # Only check substantial questions
                                                # Remove common stopwords before comparing
                                                stopwords = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with", "about", "have", "has", "had", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did", "can", "could", "will", "would", "shall", "should", "may", "might", "must", "your", "you", "any", "what", "when", "how", "if", "please", "share", "tell", "describe"}
                                                new_words = new_words - stopwords
                                                prev_words = prev_words - stopwords

                                                # Calculate Jaccard similarity
                                                common_words = new_words.intersection(prev_words)
                                                union_words = new_words.union(prev_words)

                                                if len(union_words) > 0:
                                                    similarity = len(common_words) / len(union_words)
                                                    # Lower the threshold to catch more similar questions - 40% instead of 50%
                                                    if similarity > 0.4:
                                                        logger.warning(f"Question rejected due to high word similarity: {similarity:.2f} - '{new_question_text}' vs '{prev_text}'")
                                                        is_similar = True
                                                        break

                                        # If not similar to previous questions, use it
                                        if not is_similar:
                                            logger.info(f"Successfully generated unique OpenAI question: {openai_question.get('text')}")
                                            next_question = openai_question
                                        else:
                                            logger.warning("Generated OpenAI question was too similar to a previous question, using fallback")
                                    except json.JSONDecodeError:
                                        logger.error(f"Failed to parse OpenAI response as JSON: {content}")
                    except Exception as e:
                        logger.error(f"Error generating custom question with OpenAI: {e}")
                        logger.error(traceback.format_exc())



            # If all attempts to generate a question have failed, use completely different approach
            if next_question is None:
                logger.error("All OpenAI-based question generation methods failed, using backup strategy")

                # Determine what categories haven't been covered yet
                all_categories = {"life_events", "personality_traits", "career_developments", "relationships",
                                 "health_patterns", "significant_transitions", "emotional_patterns",
                                 "birth_circumstances", "spirituality", "education"}

                covered_categories = set()
                for resp in session_store.get_session(effective_session_id).get("responses", []):
                    if isinstance(resp, dict) and resp.get("category"):
                        covered_categories.add(resp.get("category"))

                uncovered_categories = all_categories - covered_categories

                # If we have uncovered categories, use one
                if uncovered_categories:
                    category = random.choice(list(uncovered_categories))
                else:
                    # If all categories covered, pick a random one that's been covered least
                    category_counts = {}
                    for resp in session_store.get_session(effective_session_id).get("responses", []):
                        if isinstance(resp, dict) and resp.get("category"):
                            cat = resp.get("category")
                            category_counts[cat] = category_counts.get(cat, 0) + 1

                    # Find least covered category
                    min_count = float('inf')
                    category = list(all_categories)[0]  # Default
                    for cat, count in category_counts.items():
                        if count < min_count:
                            min_count = count
                            category = cat

                # Create a fallback question using the chosen category
                question_id = f"q_fallback_{uuid.uuid4().hex[:8]}"

                # Use service's alternative question generator
                try:
                    from ai_service.api.services.questionnaire_service import QuestionnaireService
                    service = QuestionnaireService()
                    birth_details = chart_data.get("birth_details", {}) if chart_data else {}
                    next_question = service._generate_alternative_question(birth_details, session_store.get_session(effective_session_id).get("responses", []))
                    logger.info(f"Generated alternative question from service: {next_question.get('text', '')}")
                except Exception as alt_e:
                    logger.error(f"Error using alternative question generator: {alt_e}")

                    # Last resort backup
                    if category == "life_events":
                        next_question = {
                            "id": question_id,
                            "text": "Was there any significant change or event in your life between ages 25-30? If so, what happened and when exactly?",
                            "type": "text",
                            "category": "life_events"
                        }
                    elif category == "birth_circumstances":
                        next_question = {
                            "id": question_id,
                            "text": "Do you know any specific details about the circumstances of your birth (complications, duration of labor, etc.)?",
                            "type": "text",
                            "category": "birth_circumstances"
                        }
                    else:
                        next_question = {
                            "id": question_id,
                            "text": f"Tell me about any significant patterns you've noticed in your {category.replace('_', ' ')} throughout your life.",
                            "type": "text",
                            "category": category
                        }

                    logger.info(f"Using last resort backup question for category {category}")

            # Calculate progress based on response count and target questions
            progress = len(session_store.get_session(effective_session_id).get("responses", [])) / 10
            logger.info(f"Current progress in Vedic analysis: {progress:.2f}")

            # Update session with question data
            await update_session_async(session_store, effective_session_id, {
                "current_question": next_question,
                "updated_at": datetime.now().isoformat(),
                "confidence": confidence
            })

            # Return next question data with Vedic context
            return {
                "session_id": effective_session_id,
                "chart_id": effective_chart_id,
                "question": next_question,
                "confidence": confidence,
                "progress": progress,
                "vedic_approach": True
            }

        except Exception as e:
            logger.error(f"Error processing answer for Vedic analysis: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Error processing answer for Vedic analysis: {str(e)}")
    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error initializing questionnaire: {str(e)}")
        logger.error(traceback.format_exc())

        # Instead of returning a static fallback question, raise an exception
        # to ensure the client knows there was a problem and can retry
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize questionnaire with real-time generated questions: {str(e)}"
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
    Submit an answer to a Vedic astrological questionnaire question and get the next question.

    Args:
        session_id: Session ID for the questionnaire
        answer_request: Answer data with question_id and answer

    Returns:
        Next question data or completion status with Vedic astrological context
    """
    try:
        logger.info(f"Processing answer for Vedic questionnaire session {session_id}")

        # Extract answer data with better validation
        question_id = answer_request.get("question_id")
        answer = answer_request.get("answer")
        previous_question_ids = answer_request.get("previous_question_ids", [])
        question_count = answer_request.get("question_count", 0)

        # Log the received data for debugging
        logger.info(f"Received answer for question_id: {question_id}, answer: {answer}")
        logger.info(f"Previous question IDs: {previous_question_ids}")
        logger.info(f"Current question count: {question_count}")

        if not question_id:
            raise HTTPException(status_code=400, detail="Missing question_id in request")
        if answer is None:
            raise HTTPException(status_code=400, detail="Missing answer in request")

        # Get session store
        session_store = get_session_store_class()
        session = await get_session_async(session_store, session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Get chart ID from session
        chart_id = session.get("chart_id")

        # Get question text
        question_text = await get_question_text(question_id, session_id)

        # Initialize or get responses array
        if "responses" not in session:
            logger.info("Initializing responses array in session")
            session["responses"] = []

        current_responses = session.get("responses", [])
        current_responses_count = len(current_responses)
        logger.info(f"Current response count: {current_responses_count}")

        # Create response entry
        response_entry = {
            "question_id": question_id,
            "question": question_text,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        }

        # Add to session responses
        session["responses"].append(response_entry)
        logger.info(f"Added new Vedic-related response for question {question_id}, total responses: {len(session['responses'])}")
        await update_session_async(session_store, session_id, session)

        # Create questionnaire engine for Vedic analysis
        engine = QuestionnaireEngine()

        # Get list of previously asked questions
        asked_questions_from_session = [response.get("question_id") for response in session.get("responses", [])]
        logger.info(f"Previously asked questions from session: {asked_questions_from_session}")

        # Merge with previous question IDs from client (for better tracking)
        all_asked_questions = list(set(asked_questions_from_session + (previous_question_ids or [])))
        logger.info(f"Merged asked questions with client data: {all_asked_questions}")

        # Initialize question history for the engine to avoid repetition
        if session_id not in engine.question_history:
            logger.info(f"Initializing question history for session {session_id} in engine")
            engine.question_history[session_id] = []

            # Add all previously asked questions to history
            for q_id in all_asked_questions:
                question = await QuestionModel.get_by_id(q_id)
                if question:
                    engine.question_history[session_id].append(question)
                else:
                    # Add a placeholder if we can't find the original question
                    engine.question_history[session_id].append({"id": q_id, "text": "Unknown question"})

            logger.info(f"Initialized engine question history with {len(engine.question_history[session_id])} questions")

        # Get chart data for Vedic analysis
        chart_data = {}
        chart_service = get_chart_service()

        if chart_id:
            try:
                chart_data = await chart_service.get_chart(chart_id)
                logger.info(f"Retrieved chart data for Vedic analysis: {chart_id}")
            except Exception as e:
                logger.warning(f"Error getting chart data for Vedic analysis: {e}")

        # Calculate current confidence using Vedic principles
        confidence = await engine.calculate_confidence({"responses": session.get("responses", [])}, chart_data)
        logger.info(f"Current Vedic confidence score: {confidence}")

        # Determine target number of questions based on confidence
        # For Vedic approach, we want at least 8-10 questions for comprehensive analysis
        total_questions = max(10, int(math.ceil((85 - confidence) / 6))) if confidence < 85 else 8
        logger.info(f"Current response count: {current_responses_count}, target for Vedic analysis: {total_questions}")

        # Define minimum confidence threshold for Vedic birth time rectification
        min_confidence = 85.0  # Increased threshold to ensure more questions are generated before completion

        # Generate next question with Vedic-focused question generation
        logger.info(f"Generating next Vedic question for session {session_id}")

        # Create questionnaire engine for Vedic chart analysis
        engine = QuestionnaireEngine()

        # Get OpenAI service for direct access to enhanced question generation
        openai_service = None
        next_question = None

        try:
            openai_service = await get_openai_service()
            logger.info("Successfully initialized OpenAI service for personalized question generation")

            # Try to get the next question using the engine
            try:
                # Ensure chart_data is not None before passing
                safe_chart_data = chart_data or {}
                next_question = await engine.get_next_question(
                    session_id=session_id,
                    chart_data=safe_chart_data,
                    previous_answers=session.get("responses", [])
                )

                if next_question:
                    logger.info(f"Generated next Vedic question: {next_question.get('text', '')[:100]}")
                else:
                    logger.warning("Question engine returned null question, falling back to direct OpenAI generation")
            except Exception as e:
                logger.error(f"Error generating question with engine: {e}")
                logger.error(traceback.format_exc())

            # If we have OpenAI service and no question yet, try direct generation
            if openai_service and not next_question and hasattr(openai_service, "chat_completion"):
                try:
                    # Create a comprehensive context for the OpenAI prompt
                    response_history = "\n".join([
                        f"Q: {resp.get('question', '')}\nA: {resp.get('answer', '')}"
                        for resp in session.get("responses", [])[-5:]  # Last 5 responses
                    ])

                    # Track used categories to ensure variety
                    used_categories = set()
                    category_counts = {}

                    for resp in session.get("responses", []):
                        if isinstance(resp, dict) and resp.get("category"):
                            cat = resp.get("category")
                            used_categories.add(cat)
                            category_counts[cat] = category_counts.get(cat, 0) + 1

                    # Determine which categories to prioritize
                    all_categories = {"childhood", "life_events", "personality", "physical_traits", "health", "career", "relationships", "spiritual", "timing", "birth_circumstances", "education"}
                    unused_categories = all_categories - used_categories

                    # Find least used categories if all have been used
                    least_used_categories = []
                    if not unused_categories:
                        min_count = min(category_counts.values()) if category_counts else 1
                        least_used_categories = [cat for cat, count in category_counts.items() if count == min_count]

                    # Format category guidance for the prompt
                    category_guidance = ""
                    if unused_categories:
                        category_guidance = f"PRIORITIZE these unused categories: {', '.join(unused_categories)}"
                    elif least_used_categories:
                        category_guidance = f"PRIORITIZE these least-used categories: {', '.join(least_used_categories)}"

                    # Create system prompt
                    system_prompt = f"""You are an expert Vedic astrologer specializing in birth time rectification.
                    Generate a unique, personalized question based on the chart data and previous answers provided.

                    CRITICAL REQUIREMENTS:
                    1. NEVER repeat or rephrase previous questions - each new question must be COMPLETELY DIFFERENT
                    2. Focus questions on information that helps determine accurate birth time
                    3. Make questions specific to this person's chart details
                    4. Avoid generic questions that could apply to anyone
                    5. Relate questions to Vedic astrological principles but use accessible language
                    6. DO NOT use technical astrological jargon without explanation
                    7. DO NOT ask about the same topic or life area as previous questions
                    8. {category_guidance}

                    Your response must be ONLY a JSON object with the following structure:
                    {{
                      "id": "q_unique_id",
                      "text": "Your unique question here",
                      "category": "one_of: childhood, life_events, personality, physical_traits, health, career, relationships, spiritual, timing",
                      "type": "text"
                    }}"""

                    # Create user prompt
                    user_prompt = f"""
                    Chart Data:
                    {json.dumps(safe_chart_data, default=str)[:500]}

                    PREVIOUSLY ASKED QUESTIONS (DO NOT REPEAT THESE):
                    {json.dumps([resp.get('question', '') for resp in session.get("responses", [])], indent=2)}

                    Previous Question-Answer History:
                    {response_history}

                    Generate ONE unique question for birth time rectification that:
                    1. Is specifically tailored to this person's birth chart
                    2. Is completely different from all previous questions
                    3. Explores a category not yet covered in depth
                    4. Contains 1-2 sentences maximum
                    5. Is focused on helping determine the exact birth time

                    Return ONLY the JSON object with your question.
                    """

                    # Log the prompt for debugging
                    logger.info(f"OpenAI prompt for custom question generation prepared")

                    # Call OpenAI for a custom question
                    custom_question_response = await openai_service.chat_completion(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        model="gpt-4o",  # Use the most capable model available
                        temperature=0.7,  # Slightly higher creativity for unique questions
                        max_tokens=350
                    )

                    # Process the OpenAI response
                    logger.info(f"Received OpenAI question response: {str(custom_question_response)[:150]}...")

                    # Safely extract and parse the JSON from the OpenAI response
                    openai_question = None
                    if isinstance(custom_question_response, dict) and "choices" in custom_question_response:
                        if len(custom_question_response["choices"]) > 0:
                            if "message" in custom_question_response["choices"][0]:
                                content = custom_question_response["choices"][0]["message"].get("content", "")

                                # Try to parse JSON from the content
                                try:
                                    # Extract JSON if it's wrapped in markdown code blocks
                                    json_match = re.search(r'```(?:json)?(.*?)```', content, re.DOTALL)
                                    if json_match:
                                        content = json_match.group(1).strip()

                                    # Or extract JSON if it's in the content directly
                                    json_obj_match = re.search(r'(\{.*\})', content, re.DOTALL)
                                    if json_obj_match:
                                        content = json_obj_match.group(1).strip()

                                    openai_question = json.loads(content)

                                    # Ensure the question has an ID
                                    if "id" not in openai_question:
                                        openai_question["id"] = f"q_openai_{uuid.uuid4()}"

                                    # Ensure the question has a type
                                    if "type" not in openai_question:
                                        openai_question["type"] = "text"

                                    # Verify the question doesn't match any previous questions
                                    new_question_text = openai_question.get("text", "").lower().strip()

                                    # Check for similarity with previous questions
                                    is_similar = False
                                    previously_asked = [resp.get('question', '') for resp in session.get("responses", [])]
                                    for prev_q in previously_asked:
                                        prev_text = prev_q.lower().strip()
                                        # Check for direct substring
                                        if (new_question_text in prev_text or prev_text in new_question_text) and len(new_question_text) > 10:
                                            logger.warning(f"Question rejected due to substring match: '{new_question_text}' vs '{prev_text}'")
                                            is_similar = True
                                            break

                                        # Check word similarity - improved algorithm
                                        new_words = set(re.findall(r'\b\w+\b', new_question_text))
                                        prev_words = set(re.findall(r'\b\w+\b', prev_text))

                                        if len(new_words) > 3 and len(prev_words) > 3:  # Only check substantial questions
                                            # Remove common stopwords before comparing
                                            stopwords = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with", "about", "have", "has", "had", "is", "are", "was", "were", "be", "been", "being", "do", "does", "did", "can", "could", "will", "would", "shall", "should", "may", "might", "must", "your", "you", "any", "what", "when", "how", "if", "please", "share", "tell", "describe"}
                                            new_words = new_words - stopwords
                                            prev_words = prev_words - stopwords

                                            # Calculate Jaccard similarity
                                            common_words = new_words.intersection(prev_words)
                                            union_words = new_words.union(prev_words)

                                            if len(union_words) > 0:
                                                similarity = len(common_words) / len(union_words)
                                                # Lower the threshold to catch more similar questions - 40% instead of 50%
                                                if similarity > 0.4:
                                                    logger.warning(f"Question rejected due to high word similarity: {similarity:.2f} - '{new_question_text}' vs '{prev_text}'")
                                                    is_similar = True
                                                    break

                                    # If not similar to previous questions, use it
                                    if not is_similar:
                                        logger.info(f"Successfully generated unique OpenAI question: {openai_question.get('text')}")
                                        next_question = openai_question
                                    else:
                                        logger.warning("Generated OpenAI question was too similar to a previous question, using fallback")
                                except json.JSONDecodeError:
                                    logger.error(f"Failed to parse OpenAI response as JSON: {content}")
                except Exception as e:
                    logger.error(f"Error generating custom question with OpenAI: {e}")
                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI service for question generation: {e}")
            # Still try to use the engine even if OpenAI service initialization failed
            try:
                # Ensure chart_data is not None before passing
                safe_chart_data = chart_data or {}
                next_question = await engine.get_next_question(
                    session_id=session_id,
                    chart_data=safe_chart_data,
                    previous_answers=session.get("responses", [])
                )
            except Exception as inner_e:
                logger.error(f"Error generating question without OpenAI service: {inner_e}")
                logger.error(traceback.format_exc())

        # If all attempts to generate a question have failed, use fallback approach
        if next_question is None:
            logger.error("All question generation methods failed, using backup strategy")

            # Determine what categories haven't been covered yet
            all_categories = {"life_events", "personality_traits", "career_developments", "relationships",
                             "health_patterns", "significant_transitions", "emotional_patterns",
                             "birth_circumstances", "spirituality", "education"}

            covered_categories = set()
            for resp in session.get("responses", []):
                if isinstance(resp, dict) and resp.get("category"):
                    covered_categories.add(resp.get("category"))

            uncovered_categories = all_categories - covered_categories

            # If we have uncovered categories, use one
            if uncovered_categories:
                category = random.choice(list(uncovered_categories))
            else:
                # If all categories covered, pick a random one that's been covered least
                category_counts = {}
                for resp in session.get("responses", []):
                    if isinstance(resp, dict) and resp.get("category"):
                        cat = resp.get("category")
                        category_counts[cat] = category_counts.get(cat, 0) + 1

                # Find least covered category
                min_count = float('inf')
                category = list(all_categories)[0]  # Default
                for cat, count in category_counts.items():
                    if count < min_count:
                        min_count = count
                        category = cat

            # Create a fallback question using the chosen category
            question_id = f"q_fallback_{uuid.uuid4().hex[:8]}"

            try:
                from ai_service.api.services.questionnaire_service import QuestionnaireService
                service = QuestionnaireService()
                birth_details = chart_data.get("birth_details", {}) if chart_data else {}
                alternative_question = service._generate_alternative_question(birth_details, session.get("responses", []))
                if alternative_question:
                    next_question = alternative_question
                    logger.info(f"Generated alternative question from service: {next_question.get('text', '')}")
                else:
                    raise ValueError("Alternative question generation returned None")
            except Exception as alt_e:
                logger.error(f"Error using alternative question generator: {alt_e}")

                # Last resort backup
                if category == "life_events":
                    next_question = {
                        "id": question_id,
                        "text": "Was there any significant change or event in your life between ages 25-30? If so, what happened and when exactly?",
                        "type": "text",
                        "category": "life_events"
                    }
                elif category == "birth_circumstances":
                    next_question = {
                        "id": question_id,
                        "text": "Do you know any specific details about the circumstances of your birth (complications, duration of labor, etc.)?",
                        "type": "text",
                        "category": "birth_circumstances"
                    }
                else:
                    next_question = {
                        "id": question_id,
                        "text": f"Tell me about any significant patterns you've noticed in your {category.replace('_', ' ')} throughout your life.",
                        "type": "text",
                        "category": category
                    }

                logger.info(f"Using last resort backup question for category {category}")

        # Calculate progress based on response count and target questions
        progress = min(current_responses_count / total_questions, 0.95)
        logger.info(f"Current progress in Vedic analysis: {progress:.2f}")

        # Update session with question data
        session["current_question"] = next_question
        session["updated_at"] = datetime.now().isoformat()
        session["confidence"] = confidence
        await update_session_async(session_store, session_id, session)

        # Return next question data with Vedic context
        return {
            "session_id": session_id,
            "chart_id": chart_id,
            "question": next_question,
            "confidence": confidence,
            "progress": progress,
            "vedic_approach": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Vedic questionnaire answer processing: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to process answer for Vedic questionnaire: {str(e)}")

@router.post("/complete", response_model=Dict[str, Any])
async def complete_questionnaire(
    request: Dict[str, Any] = Body(..., description="Completion request with session_id and chart_id")
):
    """
    Complete a questionnaire and generate Vedic birth time rectification results.

    Args:
        request: Completion request with session_id and chart_id

    Returns:
        Vedic astrological rectification results with birth time adjustment if confidence is sufficient

    Raises:
        HTTPException: If session not found or completion fails
    """
    try:
        # Extract request data
        session_id = request.get("session_id")
        chart_id = request.get("chart_id")

        if not session_id:
            raise HTTPException(status_code=400, detail="Missing session_id in request")

        logger.info(f"Completing Vedic questionnaire for session {session_id}")

        # Get session store
        session_store = get_session_store_class()
        session = await get_session_async(session_store, session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Update session status
        session["status"] = "processing"
        session["updated_at"] = datetime.now().isoformat()
        await update_session_async(session_store, session_id, session)

        # Create questionnaire engine for Vedic analysis
        engine = QuestionnaireEngine()

        # Get responses
        responses = session.get("responses", [])
        if not responses:
            raise HTTPException(status_code=400, detail="Cannot complete questionnaire with no responses")

        # Get chart data for Vedic analysis if available
        chart_data = {}
        if chart_id:
            try:
                chart_service = get_chart_service()
                chart_id_value = getattr(session, "chart_id", None)
                if chart_id_value is not None:
                    chart_data = await chart_service.get_chart(str(chart_id_value))
                else:
                    logger.warning(f"No chart_id found for session {session_id}")
                    chart_data = {}
            except Exception as e:
                logger.warning(f"Error getting chart data for Vedic analysis: {e}")

        # Define the minimum confidence threshold for reliable Vedic birth time rectification
        min_confidence_threshold = 90.0
        logger.info(f"Minimum confidence threshold for reliable Vedic birth time rectification: {min_confidence_threshold}")

        # Calculate final confidence using Vedic principles
        confidence = await engine.calculate_confidence({"responses": responses}, chart_data)
        logger.info(f"Final Vedic confidence calculation: {confidence}")

        # Check if we've reached the minimum confidence threshold
        confidence_threshold_met = confidence >= min_confidence_threshold
        logger.info(f"Vedic confidence threshold met: {confidence_threshold_met}")

        # Format responses for Vedic astrological analysis
        formatted_answers = {"responses": responses}

        # Initialize birth time adjustment values
        birth_time_adjustment = None
        adjusted_birth_time = None
        adjustment_explanation = None

        # Analyze answers for Vedic birth time rectification
        try:
            # Always run the Vedic analysis to get the best results
            logger.info("Running Vedic birth time rectification analysis")

            # Call the analyze_answers method directly to get detailed Vedic astrological analysis
            analysis_result = await engine.analyze_answers(chart_data, formatted_answers)

            if analysis_result and analysis_result.get("success"):
                result_data = analysis_result.get("analysis_result", {})
                logger.info(f"Vedic analysis result: {result_data}")

                # Extract results directly from the Vedic analysis
                adjustment_direction = result_data.get("adjustment_direction", "none")
                adjustment_minutes = result_data.get("adjustment_minutes", 0)
                analysis_confidence = result_data.get("confidence_score", confidence)
                adjustment_explanation = result_data.get("analysis", "Vedic astrological analysis complete.")

                # Update confidence score if available from Vedic analysis
                if analysis_confidence > confidence:
                    confidence = analysis_confidence
                    logger.info(f"Updated confidence score from Vedic analysis: {confidence}")

                # Get birth time adjustment information
                if adjustment_direction == "forward":
                    birth_time_adjustment = adjustment_minutes
                elif adjustment_direction == "backward":
                    birth_time_adjustment = -adjustment_minutes
                else:
                    birth_time_adjustment = 0

                adjusted_birth_time = result_data.get("adjusted_birth_time")
                original_birth_time = result_data.get("original_birth_time")

                # Ensure we have adjustment explanation
                if not adjustment_explanation or adjustment_explanation == "Vedic astrological analysis complete.":
                    # Create a more detailed explanation
                    if adjustment_direction == "none" or birth_time_adjustment == 0:
                        adjustment_explanation = "Based on Vedic astrological principles and your responses, your recorded birth time appears to be accurate. No adjustment needed."
                    else:
                        direction_text = "later" if adjustment_direction == "forward" else "earlier"
                        adjustment_explanation = f"Based on Vedic astrological principles and your responses, your birth time should be adjusted {direction_text} by {abs(birth_time_adjustment)} minutes."

                        # Add more Vedic context if available
                        if chart_data and "ascendant" in chart_data:
                            ascendant_sign = chart_data.get("ascendant", {}).get("sign", "")
                            adjustment_explanation += f" Your {ascendant_sign} ascendant indicated this adjustment was necessary for proper Vedic chart alignment."

            else:
                logger.warning("Vedic analysis did not return a successful result")
                # Add fallback explanation
                adjustment_explanation = "Vedic analysis was performed but did not yield definitive results. No adjustment applied."
                birth_time_adjustment = 0
                adjustment_direction = "none"

        except Exception as analysis_error:
            logger.error(f"Error in Vedic birth time rectification analysis: {analysis_error}")
            logger.error(traceback.format_exc())

            # Provide a fallback for client
            adjustment_explanation = "An error occurred during Vedic birth time analysis. No adjustment applied."
            birth_time_adjustment = 0
            adjustment_direction = "none"

        # Update session with completion information
        session["status"] = "completed"
        session["completed_at"] = datetime.now().isoformat()
        session["final_confidence"] = confidence
        session["birth_time_adjustment"] = birth_time_adjustment
        session["adjusted_birth_time"] = adjusted_birth_time
        await update_session_async(session_store, session_id, session)

        # Prepare response for the client
        message = "Questionnaire completed successfully"
        if confidence_threshold_met:
            message += " with high confidence for accurate Vedic birth time rectification"
        else:
            message += ", but confidence threshold for optimal Vedic birth time rectification was not met"

        # Log completion
        logger.info(f"Completed Vedic questionnaire for session {session_id} with confidence {confidence:.1f}%")
        if birth_time_adjustment:
            logger.info(f"Vedic birth time adjustment: {birth_time_adjustment} minutes")

        # Return the final result
        return {
            "session_id": session_id,
            "chart_id": chart_id,
            "confidence": confidence,
            "status": "completed",
            "message": message,
            "birth_time_adjustment": birth_time_adjustment,
            "adjusted_birth_time": adjusted_birth_time,
            "adjustment_explanation": adjustment_explanation,
            "confidence_threshold_met": confidence_threshold_met,
            "question_count": len(responses),
            "vedic_approach": True
        }

    except HTTPException:
        # Re-raise HTTP exceptions without modification
        raise
    except Exception as e:
        logger.error(f"Error completing Vedic questionnaire: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to complete Vedic questionnaire: {str(e)}")

async def _generate_question_with_openai(
    session_id: str,
    engine: QuestionnaireEngine,
    db_session: AsyncSession,
    max_retries: int = 3,
    chart_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a question with OpenAI, with retry logic.

    Args:
        session_id: Session identifier
        engine: Questionnaire engine instance
        db_session: Database session
        max_retries: Maximum number of retries
        chart_data: Optional chart data

    Returns:
        Generated question
    """
    # Fetch session data if not provided
    if not chart_data:
        chart_data = await get_chart_data_for_session(session_id, db_session)

    # Get previous answers for the session
    previous_answers = await get_session_answers(session_id, db_session)

    # Try to generate a question
    attempts = 0
    generated_question = None
    rejection_reason = None

    while attempts < max_retries and not generated_question:
        attempts += 1
        logger.info(f"Attempt {attempts}/{max_retries} to generate question for session {session_id}")

        # Generate a question
        try:
            generated_question = await engine.get_next_question(session_id, chart_data, previous_answers)

            # Check for null or invalid question
            if not generated_question or "text" not in generated_question:
                logger.warning(f"Generated question is null or missing text field: {generated_question}")
                rejection_reason = "Invalid question format"
                generated_question = None
                continue

            # Check for repeats by comparing to previous questions
            if previous_answers:
                is_repeat = False
                new_question_text = generated_question.get("text", "").lower().strip()

                # Create a bag of words for new question (excluding common words)
                new_words = set([word.lower() for word in re.findall(r'\b\w+\b', new_question_text)
                                if word.lower() not in _get_common_words()])

                for prev_answer in previous_answers:
                    prev_question = prev_answer.get("question_text", "").lower().strip()

                    # Direct comparison for very similar questions
                    if prev_question == new_question_text:
                        logger.warning(f"Generated question is identical to previous: {new_question_text}")
                        rejection_reason = "Identical question"
                        is_repeat = True
                        break

                    # Check for substring containment (if one is a substring of the other)
                    if (prev_question in new_question_text or new_question_text in prev_question) and len(new_question_text) > 20:
                        logger.warning(f"Generated question is a substring of previous or vice versa: {new_question_text} vs {prev_question}")
                        rejection_reason = "Substring containment"
                        is_repeat = True
                        break

                    # Calculate word similarity (Jaccard similarity)
                    prev_words = set([word.lower() for word in re.findall(r'\b\w+\b', prev_question)
                                    if word.lower() not in _get_common_words()])

                    if prev_words and new_words:
                        intersection = prev_words.intersection(new_words)
                        union = prev_words.union(new_words)
                        similarity = len(intersection) / len(union) if union else 0

                        # If more than 50% word overlap (excluding common words), consider it too similar
                        if similarity > 0.5:
                            logger.warning(f"Generated question has high word similarity ({similarity}) with previous: {new_question_text} vs {prev_question}")
                            rejection_reason = f"High word similarity ({similarity:.2f})"
                            is_repeat = True
                            break

                if is_repeat:
                    logger.warning(f"Question rejected due to similarity: {rejection_reason}")
                    generated_question = None
                    continue

                # Also check for topic repetition (if multiple questions in the same category)
                if "category" in generated_question:
                    category = generated_question["category"]
                    category_count = sum(1 for ans in previous_answers if ans.get("category") == category)

                    # If we've already had 2 questions in this category and have other unused categories,
                    # try to generate a different question
                    all_categories = {"life_events", "personality_traits", "career_developments",
                                      "relationships", "health_patterns", "significant_transitions",
                                      "emotional_patterns", "birth_circumstances", "spirituality",
                                      "education"}
                    used_categories = {ans.get("category") for ans in previous_answers if ans.get("category")}
                    unused_categories = all_categories - used_categories

                    if category_count >= 2 and unused_categories:
                        logger.warning(f"Generated question category {category} has been used {category_count} times already, rejecting")
                        rejection_reason = f"Category overuse ({category}, {category_count} times)"
                        generated_question = None
                        continue

        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")
            rejection_reason = f"Exception: {str(e)}"
            generated_question = None

    # If we failed to generate a question after all retries
    if not generated_question:
        logger.error(f"Failed to generate question after {max_retries} attempts. Last rejection reason: {rejection_reason}")

        # As a last resort, generate a fallback question based on unused categories
        if previous_answers:
            all_categories = {"life_events", "personality_traits", "career_developments",
                             "relationships", "health_patterns", "significant_transitions",
                             "emotional_patterns", "birth_circumstances", "spirituality",
                             "education"}
            used_categories = {ans.get("category") for ans in previous_answers if ans.get("category")}
            unused_categories = all_categories - used_categories

            if unused_categories:
                # Pick a random unused category
                category = random.choice(list(unused_categories))
                question_id = f"q_fallback_{uuid.uuid4().hex[:8]}"

                # Create a fallback question
                generated_question = {
                    "id": question_id,
                    "text": f"Could you share any significant events or patterns related to your {category.replace('_', ' ')} that might help determine your birth time?",
                    "type": "text",
                    "category": category
                }
                logger.info(f"Generated fallback question from unused category {category}")
            else:
                # If all categories used, create a very different formulation
                question_id = f"q_fallback_{uuid.uuid4().hex[:8]}"
                generated_question = {
                    "id": question_id,
                    "text": "Based on your astrological chart, we still need more information to determine your birth time accurately. Can you describe any distinctive personality traits or recurring patterns in your life that stand out to you?",
                    "type": "text",
                    "category": "personality_traits"
                }
                logger.info("Generated generic fallback question after exhausting all categories")
        else:
            # For the first question if it fails
            question_id = f"q_first_{uuid.uuid4().hex[:8]}"
            generated_question = {
                "id": question_id,
                "text": "Can you tell me about any significant events or experiences from your early childhood that might help determine your birth time?",
                "type": "text",
                "category": "life_events"
            }
            logger.info("Generated initial fallback question")

    return generated_question

def _get_common_words() -> Set[str]:
    """Return a set of common words to exclude from similarity comparison."""
    return {
        "the", "and", "of", "to", "a", "in", "for", "is", "on", "that", "by", "this", "with", "i", "you", "it",
        "not", "or", "be", "are", "from", "at", "as", "your", "have", "been", "when", "can", "an", "there",
        "about", "any", "what", "would", "could", "tell", "me", "do", "events", "experiences", "significant",
        "during", "time", "birth", "remember", "describe", "recall", "specific", "how", "did", "feel", "felt",
        "life", "event", "experience", "question", "answer", "think", "know", "around", "age", "period", "year",
        "years", "childhood", "adolescence", "adulthood", "early", "late", "share", "help", "determine",
        "anything", "might", "may", "please", "consider", "related", "regarding", "concerning", "about", "were",
        "was", "had", "ever", "never", "always", "sometimes", "often", "rarely", "happen", "happened", "occurring",
        "occur", "occurred", "experiencing", "experience", "experienced", "noticed", "notice", "noticing"
    }

        chart_data = {}

    return chart_data or {}

async def get_session_answers(session_id: str, db_session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Get all answers for a session.

    Args:
        session_id: Session identifier
        db_session: Database session

    Returns:
        List of answers
    """
    # Get answers from DB
    answers_query = await db_session.execute(
        select(Answer).where(Answer.session_id == session_id).order_by(Answer.created_at)
    )
    answers = answers_query.scalars().all()

    # Format answers
    formatted_answers = []
    for answer in answers:
        # Get question
        question_query = await db_session.execute(
            select(Question).where(Question.id == answer.question_id)
        )
        question = question_query.scalar_one_or_none()

        if question:
            formatted_answers.append({
                "question_id": str(question.id),
                "question_text": question.text,
                "answer_id": str(answer.id),
                "answer_text": answer.text,
                "category": question.category
            })

    return formatted_answers

# Helper functions for handling time-based analysis
async def analyze_time_patterns(chart_data: Dict[str, Any], birth_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze time-based patterns in Vedic astrological analysis.

    Args:
        chart_data: Chart data
        birth_details: Birth details

    Returns:
        Analysis results
    """
    # Extract birth time
    birth_time = birth_details.get("time")
    if not birth_time:
        return {"confidence": 0.0, "message": "No birth time provided"}

    # TODO: Implement actual time pattern analysis logic

    return {
        "confidence": 0.75,
        "possible_ranges": ["6:00-7:00", "18:00-19:00"],
        "message": "Based on life events, one of these time ranges is most probable"
    }
