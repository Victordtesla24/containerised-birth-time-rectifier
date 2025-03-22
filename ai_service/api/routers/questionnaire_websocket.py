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
import traceback

from ai_service.api.websocket_events import emit_event, EventType
from ai_service.api.services.questionnaire_service import get_questionnaire_service, DynamicQuestionnaireService
from ai_service.api.services.chart import get_chart_service

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
    question: Dict[str, Any]

class QuestionAnswerRequest(BaseModel):
    question_id: str
    answer: Any

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
    and returns the first question.
    """
    try:
        # Generate a unique questionnaire ID
        questionnaire_id = f"quest_{uuid.uuid4().hex[:8]}"

        # Get chart ID from request
        chart_id = request.chart_id

        # Get the questionnaire service - use DynamicQuestionnaireService specifically
        questionnaire_service = DynamicQuestionnaireService()
        chart_service = get_chart_service()

        # Get chart data
        try:
            chart_data = await chart_service.get_chart(chart_id)
            if not chart_data:
                logger.error(f"Chart not found: {chart_id}")
                raise HTTPException(status_code=404, detail=f"Chart not found: {chart_id}")
        except Exception as chart_err:
            logger.error(f"Error retrieving chart {chart_id}: {chart_err}")
            raise HTTPException(status_code=500, detail=f"Error retrieving chart: {str(chart_err)}")

        # Initialize the questionnaire with chart data
        initial_response = await questionnaire_service.initialize_questionnaire(
            chart_id=chart_id,
            session_id=questionnaire_id
        )

        # Extract the first question from the response
        first_question = initial_response.get("question")
        if not first_question:
            logger.error(f"Failed to initialize questionnaire: No question returned")
            raise HTTPException(status_code=500, detail="Failed to initialize questionnaire")

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

        # Return the response with the first question
        return {
            "questionnaire_id": questionnaire_id,
            "total_questions": 10,  # Estimated total questions
            "question": first_question
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error starting questionnaire: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error starting questionnaire: {str(e)}")

@router.post("/answer", response_model=QuestionAnswerResponse)
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

        # Get the questionnaire service - use DynamicQuestionnaireService specifically
        questionnaire_service = DynamicQuestionnaireService()

        # Process the answer and get the next question
        response_data = await questionnaire_service.get_next_question(
            session_id=questionnaire_id,
            question_id=question_id,
            answer=answer
        )

        # Check if the questionnaire is complete
        if response_data.get("complete", False):
            # Complete the questionnaire
            completion_result = await questionnaire_service.complete_questionnaire(questionnaire_id)

            # Calculate confidence based on the completion result
            confidence = completion_result.get("confidence", 0.7)

            # Emit questionnaire completed event
            if hasattr(req.state, "session_id"):
                session_id = req.state.session_id
                background_tasks.add_task(
                    emit_event,
                    session_id,
                    EventType.QUESTIONNAIRE_COMPLETED,
                    {
                        "questionnaire_id": questionnaire_id,
                        "timestamp": datetime.now().isoformat(),
                        "confidence": confidence,
                        "status": "completed"
                    }
                )

            return {
                "next_question": None,
                "current_confidence": confidence,
                "questions_remaining": 0
            }

        # Extract next question and progress information
        next_question = response_data.get("question")
        current_progress = response_data.get("progress", {})
        current_question = current_progress.get("current", 0)
        total_questions = current_progress.get("total_estimated", 10)
        questions_remaining = max(0, total_questions - current_question)

        # Get the question's category to improve tracking
        question_category = next_question.get("category", "unknown") if next_question else "unknown"

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
                    "next_category": question_category,
                    "progress": current_progress,
                    "timestamp": datetime.now().isoformat()
                }
            )

        # Calculate current confidence based on progress and service data
        # This uses the confidence from the service if available
        service_confidence = response_data.get("confidence")
        if service_confidence is not None:
            current_confidence = service_confidence
        else:
            # Fallback calculation if service doesn't provide confidence
            base_confidence = 30.0
            progress_confidence = (current_question / total_questions) * 50.0
            current_confidence = min(95.0, base_confidence + progress_confidence)

        # Return the response with the next question
        return {
            "next_question": next_question,
            "current_confidence": current_confidence,
            "questions_remaining": questions_remaining
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error answering question: {str(e)}")
        logger.error(traceback.format_exc())
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

        # Get the questionnaire service - use DynamicQuestionnaireService specifically
        questionnaire_service = DynamicQuestionnaireService()

        # Complete the questionnaire and get the results
        completion_result = await questionnaire_service.complete_questionnaire(questionnaire_id)

        # Check that completion was successful
        if not completion_result.get("completed", False):
            raise HTTPException(status_code=400, detail="Failed to complete questionnaire")

        # Extract completion details
        confidence = completion_result.get("confidence", 0.7)
        chart_id = completion_result.get("chart_id")

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
                    "chart_id": chart_id,
                    "timestamp": datetime.now().isoformat(),
                    "confidence": confidence,
                    "status": "completed"
                }
            )

        # Return the completion status
        return {
            "status": "completed",
            "message": "Questionnaire completed successfully. Ready for birth time rectification.",
            "confidence": confidence
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error completing questionnaire: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error completing questionnaire: {str(e)}")
