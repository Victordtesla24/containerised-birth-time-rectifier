"""
WebSocket integration for the Questionnaire Router

This module provides WebSocket event emission for questionnaire-related events.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body, Path, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
import logging
import uuid
from datetime import datetime

from ai_service.api.websocket_events import emit_event, EventType

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["questionnaire_websocket"],
    responses={404: {"description": "Not found"}},
)

# Models for request/response
class QuestionnaireRequest(BaseModel):
    chart_id: str

class QuestionnaireResponse(BaseModel):
    questionnaire_id: str
    total_questions: int
    questions: List[Dict[str, Any]]

class QuestionAnswerRequest(BaseModel):
    question_id: str
    answer: str

class QuestionAnswerResponse(BaseModel):
    next_question: Optional[Dict[str, Any]]
    current_confidence: float
    questions_remaining: Optional[int]

class QuestionnaireCompleteRequest(BaseModel):
    questionnaire_id: str

class QuestionnaireCompleteResponse(BaseModel):
    status: str
    message: str
    confidence: float

@router.post("", response_model=QuestionnaireResponse)
async def start_questionnaire(
    request: QuestionnaireRequest,
    req: Request,
    background_tasks: BackgroundTasks
):
    """
    Start a new questionnaire for birth time rectification.

    This endpoint initializes a new questionnaire based on the provided chart ID
    and returns the first set of questions.
    """
    try:
        # Generate a unique questionnaire ID
        questionnaire_id = f"quest_{uuid.uuid4().hex[:8]}"

        # Get chart ID from request
        chart_id = request.chart_id

        # Emit questionnaire started event if we have a session ID
        if hasattr(req.state, "session_id"):
            session_id = req.state.session_id
            # Send WebSocket event in the background
            background_tasks.add_task(
                emit_event,
                session_id,
                EventType.QUESTIONNAIRE_STARTED,
                {
                    "questionnaire_id": questionnaire_id,
                    "chart_id": chart_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

        # Forward the request to the original questionnaire endpoint
        # This is just a placeholder - in a real implementation, you would
        # call the actual questionnaire service or router

        # For now, return a mock response
        return {
            "questionnaire_id": questionnaire_id,
            "total_questions": 10,
            "questions": [
                {
                    "id": f"q_{uuid.uuid4().hex[:8]}",
                    "text": "Have you experienced any major career changes?",
                    "type": "yes_no"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Error starting questionnaire: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error starting questionnaire: {str(e)}")

@router.post("/{questionnaire_id}/answer", response_model=QuestionAnswerResponse)
async def answer_question(
    questionnaire_id: str,
    request: QuestionAnswerRequest,
    req: Request,
    background_tasks: BackgroundTasks
):
    """
    Answer a question in the questionnaire.

    This endpoint processes the answer to a question and returns the next question.
    """
    try:
        # Get question ID and answer from request
        question_id = request.question_id
        answer = request.answer

        # Emit question answered event if we have a session ID
        if hasattr(req.state, "session_id"):
            session_id = req.state.session_id
            # Send WebSocket event in the background
            background_tasks.add_task(
                emit_event,
                session_id,
                EventType.QUESTION_ANSWERED,
                {
                    "questionnaire_id": questionnaire_id,
                    "question_id": question_id,
                    "answer": answer,
                    "timestamp": datetime.now().isoformat()
                }
            )

        # Forward the request to the original questionnaire endpoint
        # This is just a placeholder - in a real implementation, you would
        # call the actual questionnaire service or router

        # For now, return a mock response
        return {
            "next_question": {
                "id": f"q_{uuid.uuid4().hex[:8]}",
                "text": "When did your most significant career change occur?",
                "type": "date"
            },
            "current_confidence": 45.0,
            "questions_remaining": 9
        }
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")

@router.post("/complete", response_model=QuestionnaireCompleteResponse)
async def complete_questionnaire(
    request: QuestionnaireCompleteRequest,
    req: Request,
    background_tasks: BackgroundTasks
):
    """
    Complete the questionnaire.

    This endpoint finalizes the questionnaire and prepares for birth time rectification.
    """
    try:
        # Get questionnaire ID from request
        questionnaire_id = request.questionnaire_id

        # Emit questionnaire completed event if we have a session ID
        if hasattr(req.state, "session_id"):
            session_id = req.state.session_id
            # Send WebSocket event in the background
            background_tasks.add_task(
                emit_event,
                session_id,
                EventType.QUESTIONNAIRE_COMPLETED,
                {
                    "questionnaire_id": questionnaire_id,
                    "timestamp": datetime.now().isoformat(),
                    "confidence": 75.0,
                    "status": "completed"
                }
            )

        # Forward the request to the original questionnaire endpoint
        # This is just a placeholder - in a real implementation, you would
        # call the actual questionnaire service or router

        # For now, return a mock response
        return {
            "status": "completed",
            "message": "Questionnaire completed successfully",
            "confidence": 75.0
        }
    except Exception as e:
        logger.error(f"Error completing questionnaire: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error completing questionnaire: {str(e)}")
