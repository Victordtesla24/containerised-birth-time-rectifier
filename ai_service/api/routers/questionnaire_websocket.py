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
from ai_service.api.services.questionnaire_service import get_questionnaire_service
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
    questions: List[Dict[str, Any]]

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
    and returns the first set of questions.
    """
    try:
        # Generate a unique questionnaire ID
        questionnaire_id = f"quest_{uuid.uuid4().hex[:8]}"

        # Get chart ID from request
        chart_id = request.chart_id

        # Get the actual services
        questionnaire_service = get_questionnaire_service()
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

        # Extract birth details
        birth_details = chart_data.get("birth_details", {})
        if not birth_details:
            logger.error(f"Chart {chart_id} missing birth details")
            raise HTTPException(status_code=400, detail="Chart missing birth details")

        # Initialize the questionnaire with real data
        initial_questions_data = await questionnaire_service.initialize_questionnaire(
            birth_details=birth_details,
            chart_data=chart_data,
            session_id=questionnaire_id
        )

        # Extract questions from the real response
        if not initial_questions_data or "questions" not in initial_questions_data:
            logger.error(f"Failed to initialize questionnaire: Invalid response from service")
            raise HTTPException(status_code=500, detail="Failed to initialize questionnaire")

        questions = initial_questions_data.get("questions", [])
        total_questions = len(questions)

        # Store questionnaire data in persistent storage
        await questionnaire_service.store_questionnaire_session(
            questionnaire_id=questionnaire_id,
            chart_id=chart_id,
            birth_details=birth_details,
            initial_questions=questions
        )

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

        # Return the actual response with real data
        return {
            "questionnaire_id": questionnaire_id,
            "total_questions": total_questions,
            "questions": questions
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error starting questionnaire: {str(e)}")
        logger.error(traceback.format_exc())
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

        # Get the questionnaire service
        questionnaire_service = get_questionnaire_service()

        # Verify the questionnaire exists
        questionnaire_data = await questionnaire_service.get_questionnaire_session(questionnaire_id)
        if not questionnaire_data:
            logger.error(f"Questionnaire not found: {questionnaire_id}")
            raise HTTPException(status_code=404, detail=f"Questionnaire not found: {questionnaire_id}")

        # Store the answer in the questionnaire session
        await questionnaire_service.store_answer(
            questionnaire_id=questionnaire_id,
            question_id=question_id,
            answer=answer
        )

        # Get the next question based on the answer
        response_data = await questionnaire_service.get_next_question(
            questionnaire_id=questionnaire_id,
            previous_question_id=question_id,
            previous_answer=answer
        )

        # Extract data from real response
        if not response_data:
            logger.error(f"Failed to get next question: Invalid response from service")
            raise HTTPException(status_code=500, detail="Failed to get next question")

        next_question = response_data.get("next_question")
        current_confidence = response_data.get("confidence", 0.0)
        questions_remaining = response_data.get("questions_remaining", 0)

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

        # Return the real response with the next question
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

        # Get the questionnaire service
        questionnaire_service = get_questionnaire_service()

        # Verify the questionnaire exists
        questionnaire_data = await questionnaire_service.get_questionnaire_session(questionnaire_id)
        if not questionnaire_data:
            logger.error(f"Questionnaire not found: {questionnaire_id}")
            raise HTTPException(status_code=404, detail=f"Questionnaire not found: {questionnaire_id}")

        # Complete the questionnaire and get the real results
        completion_result = await questionnaire_service.complete_questionnaire(questionnaire_id)

        if not completion_result:
            logger.error(f"Failed to complete questionnaire: Invalid response from service")
            raise HTTPException(status_code=500, detail="Failed to complete questionnaire")

        status = completion_result.get("status", "completed")
        message = completion_result.get("message", "Questionnaire completed successfully")
        confidence = completion_result.get("confidence", 0.0)

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
                    "confidence": confidence,
                    "status": status
                }
            )

        # Return the real result
        return {
            "status": status,
            "message": message,
            "confidence": confidence
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error completing questionnaire: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error completing questionnaire: {str(e)}")
