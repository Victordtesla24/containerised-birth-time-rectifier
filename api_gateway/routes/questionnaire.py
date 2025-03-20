"""
Questionnaire API Routes
-----------------------
Handles questionnaire-related API endpoints including initialization,
question generation, answer submission, and birth time rectification.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status, Query
from typing import Dict, Any, Optional, List
import httpx
import os
import json
import logging
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger("api_gateway.routes.questionnaire")

# Initialize router
router = APIRouter()

# Define request/response models
class QuestionnaireInitRequest(BaseModel):
    birth_details: Dict[str, Any] = Field(..., description="Birth details including date, time, and location")
    session_id: Optional[str] = Field(None, description="Optional session ID to associate with this questionnaire")

class QuestionnaireAnswerRequest(BaseModel):
    session_id: str = Field(..., description="Session ID for this questionnaire")
    question_id: str = Field(..., description="ID of the question being answered")
    answer: Any = Field(..., description="Answer to the question")
    question_text: Optional[str] = Field(None, description="Optional question text for context")

class QuestionnaireCompleteRequest(BaseModel):
    session_id: str = Field(..., description="Session ID for this questionnaire")
    chart_id: str = Field(..., description="Chart ID to associate with rectification")

# Helper function to request data from the AI service
async def request_ai_service(endpoint: str, data: Dict[str, Any] = {}, method: str = "POST") -> Dict[str, Any]:
    """Send a request to the AI service"""
    ai_service_url = os.getenv("AI_SERVICE_URL", "http://ai_service:8000")

    url = f"{ai_service_url}/api/v1/{endpoint}"
    logger.info(f"Requesting AI service at {url}")

    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, params=data, timeout=60.0)
            else:
                response = await client.post(url, json=data, timeout=60.0)

            if response.status_code != 200:
                logger.error(f"AI service returned error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"AI service error: {response.text}"
                )

            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error requesting AI service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service unavailable"
        )

# Initialize questionnaire endpoint
@router.post("/initialize", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def initialize_questionnaire(request: QuestionnaireInitRequest):
    """
    Initialize a new questionnaire for birth time rectification.

    This endpoint sets up a new questionnaire session and returns the initial questions.

    Request body:
    - birth_details: Birth details including date, time, and location
    - session_id: Optional session ID to associate with this questionnaire
    """
    try:
        logger.info(f"Initializing questionnaire with birth details: {request.birth_details}")

        # Use the correct endpoint path for the AI service
        result = await request_ai_service("questionnaire/initialize", request.dict())

        return result
    except Exception as exc:
        logger.error(f"Error initializing questionnaire: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Questionnaire initialization failed: {str(exc)}"
        )

# Get next question endpoint
@router.get("/{session_id}/next", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def get_next_question(session_id: str):
    """
    Get the next question in the questionnaire sequence.

    This endpoint retrieves the next astrologically relevant question for the user.

    Path parameters:
    - session_id: The session ID for this questionnaire
    """
    try:
        logger.info(f"Getting next question for session: {session_id}")

        # Use the correct endpoint path for the AI service
        result = await request_ai_service(f"questionnaire/{session_id}/next", {}, method="GET")

        return result
    except Exception as exc:
        logger.error(f"Error getting next question: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get next question: {str(exc)}"
        )

# Submit answer endpoint
@router.post("/{session_id}/answer", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def submit_answer(session_id: str, request: QuestionnaireAnswerRequest):
    """
    Submit an answer to a question in the questionnaire.

    This endpoint processes the user's answer and analyzes it for astrological insights.

    Path parameters:
    - session_id: The session ID for this questionnaire

    Request body:
    - question_id: ID of the question being answered
    - answer: The user's answer
    - question_text: Optional question text for context
    """
    try:
        logger.info(f"Submitting answer for session {session_id}, question {request.question_id}")

        # Use the correct endpoint path for the AI service
        result = await request_ai_service(f"questionnaire/{session_id}/answer", request.dict())

        return result
    except Exception as exc:
        logger.error(f"Error submitting answer: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer submission failed: {str(exc)}"
        )

# Complete questionnaire endpoint
@router.post("/complete", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def complete_questionnaire(request: QuestionnaireCompleteRequest):
    """
    Complete the questionnaire and start the rectification process.

    This endpoint finalizes the questionnaire and begins the birth time rectification process
    using OpenAI integration and astrological analysis.

    Request body:
    - session_id: The session ID for this questionnaire
    - chart_id: Chart ID to associate with rectification
    """
    try:
        logger.info(f"Completing questionnaire for session {request.session_id}, chart {request.chart_id}")

        # Use the correct endpoint path for the AI service
        result = await request_ai_service("questionnaire/complete", request.dict())

        return result
    except Exception as exc:
        logger.error(f"Error completing questionnaire: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Questionnaire completion failed: {str(exc)}"
        )

# Get rectification status endpoint
@router.get("/{session_id}/rectification/status", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def get_rectification_status(session_id: str):
    """
    Get the status of a rectification process.

    This endpoint checks the current status of an ongoing or completed rectification.

    Path parameters:
    - session_id: The session ID for this questionnaire
    """
    try:
        logger.info(f"Getting rectification status for session: {session_id}")

        # Use the correct endpoint path for the AI service
        result = await request_ai_service(f"questionnaire/{session_id}/rectification/status", {}, method="GET")

        return result
    except Exception as exc:
        logger.error(f"Error getting rectification status: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rectification status: {str(exc)}"
        )

# Process rectification endpoint
@router.post("/rectify", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def process_rectification(request: Request):
    """
    Manually trigger the rectification process.

    This endpoint allows manual triggering of the rectification process
    with full OpenAI integration for birth time determination.

    Request body:
    - chart_id: Chart ID to rectify
    - session_id: Session ID with questionnaire data
    """
    try:
        # Extract request body
        data = await request.json()
        logger.info(f"Processing rectification for chart: {data.get('chart_id')}")

        # Validate required fields
        if 'chart_id' not in data or 'session_id' not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both chart_id and session_id are required"
            )

        # Use the correct endpoint path for the AI service
        result = await request_ai_service("questionnaire/rectify", data)

        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error processing rectification: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rectification processing failed: {str(exc)}"
        )
