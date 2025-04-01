"""
Questionnaire API Routes
-----------------------
Handles questionnaire-related API endpoints including initialization,
question generation, answer submission, and birth time rectification.
"""

import os
import logging
import time
from typing import Dict, Any, Optional
import jwt
import uuid
import traceback

from fastapi import APIRouter, HTTPException, Request, status, Query
import httpx
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

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

# Add a new request model for generating questionnaire
class QuestionnaireGenerateRequest(BaseModel):
    birth_details: Dict[str, Any] = Field(..., description="Birth details including date, time, and location")
    previous_answers: Optional[Dict[str, Any]] = Field(None, description="Previous answers from the questionnaire")
    current_confidence: Optional[float] = Field(0.0, description="Current confidence level from previous answers")
    session_id: Optional[str] = Field(None, description="Optional session ID to use for this request")

# Helper function to request data from the AI service
async def request_ai_service(endpoint: str, data: Optional[Dict[str, Any]] = None, method: str = "POST") -> Dict[str, Any]:
    """Send a request to the AI service"""
    ai_service_url = os.getenv("AI_SERVICE_URL", "http://ai_service:8001")

    # Initialize data to empty dict if None
    if data is None:
        data = {}

    url = f"{ai_service_url}/api/v1/{endpoint}"
    logger.info("Requesting AI service at %s", url)

    try:
        async with httpx.AsyncClient(
            verify=True,  # Explicitly enable SSL verification
            timeout=60.0
        ) as client:
            if method == "GET":
                response = await client.get(url, params=data)
            else:
                response = await client.post(url, json=data)

            # Check response
            if response.status_code != 200:
                logger.error("AI service returned error: %s - %s", response.status_code, response.text)
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"AI service error: {response.text}"
                )

            # Parse the response
            return response.json()

    except httpx.RequestError as e:
        logger.error("Error requesting AI service: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unavailable: {str(e)}"
        ) from e
    except Exception as e:
        logger.error("Unexpected error in request_ai_service: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e

async def proxy_request_to_ai(request: Request, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Proxy a request to the AI service.

    Args:
        request: The FastAPI request
        endpoint: The endpoint to call on the AI service
        method: The HTTP method to use
        data: The data to send (for POST/PUT)

    Returns:
        The JSON response from the AI service
    """
    # Get AI service URL from environment
    ai_service_url = os.environ.get("AI_SERVICE_URL", "http://localhost:8001")

    # Normalize endpoint path
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    # Construct full URL
    url = f"{ai_service_url}{endpoint}"

    # Forward any headers except host-specific ones
    headers = {k: v for k, v in request.headers.items()
              if k.lower() not in ["host", "content-length"]}

    # Log the request
    logger.info(f"Proxying {method} request to AI service: {url}")

    try:
        # Create HTTP client with timeout
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Make the request based on method
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = await client.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                raise HTTPException(status_code=500, detail=f"Unsupported HTTP method: {method}")

            # Check for successful response
            response.raise_for_status()

            # Return JSON response
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error when calling AI service: {e.response.status_code} - {e.response.text}")
        # Try to parse error response
        try:
            error_data = e.response.json()
            raise HTTPException(status_code=e.response.status_code, detail=error_data)
        except (ValueError, KeyError):
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except httpx.RequestError as e:
        logger.error(f"Error when calling AI service: {e}")
        raise HTTPException(status_code=503, detail=f"Error communicating with AI service: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error when calling AI service: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# Initialize questionnaire endpoint
@router.post("/initialize", response_model=Dict[str, Any])
async def initialize_questionnaire(request: Request):
    """Initialize a new questionnaire and get the first question"""
    try:
        logger.info("Starting initialization of questionnaire")

        # Parse the request body
        body = await request.json()
        logger.info("Received body: %s", body)

        # Validate required fields
        required_fields = ["birth_details"]
        for field in required_fields:
            if field not in body:
                logger.error("Missing required field: %s", field)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required field: {field}"
                )

        # Extract session ID if provided, or use the one from state
        session_id = body.get("session_id") or getattr(request.state, "session_id", None)
        if not session_id:
            # Generate a new session ID if not provided or in state
            session_id = str(uuid.uuid4())
            logger.info("Generated new session ID: %s", session_id)

        # Add session ID to the body
        body["session_id"] = session_id

        # Extract chart ID if provided (optional)
        chart_id = body.get("chart_id")
        if chart_id:
            logger.info("Using provided chart ID: %s", chart_id)

        # Forward the request to the AI service
        logger.info("Forwarding initialization request to AI service")
        result = await request_ai_service("questionnaire/initialize", body)

        # If we got a successful response, return it
        logger.info("Questionnaire initialized successfully")
        return result

    except HTTPException as e:
        # Re-raise HTTP exceptions
        logger.error("HTTP exception during initialization: %s", e.detail)
        raise e
    except Exception as e:
        # Log the error
        logger.error(f"Error initializing questionnaire: {e}")
        logger.error(traceback.format_exc())
        # Return HTTP 500 with detailed error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize questionnaire: {str(e)}"
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
        logger.info("Getting next question for session: %s", session_id)

        # Use the correct endpoint path for the AI service
        result = await request_ai_service(f"questionnaire/{session_id}/next", {}, method="GET")

        return result
    except Exception as exc:
        logger.error("Error getting next question: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get next question: {str(exc)}"
        ) from exc

# Submit answer endpoint
@router.post("/{session_id}/answer", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def submit_answer(session_id: str, request: Request):
    """
    Submit an answer to the current question and get the next question.

    This endpoint processes the user's answer and returns the next question based on it.

    Path parameters:
    - session_id: The session ID for this questionnaire

    Request body:
    - question_id: ID of the question being answered
    - answer: The user's answer (text, option ID, or list of option IDs)
    """
    try:
        logger.info("Processing answer for session: %s", session_id)

        # Parse the request body
        body = await request.json()

        # Extract required fields
        question_id = body.get("question_id")
        answer = body.get("answer")

        # Check session_id is valid before continuing
        if not session_id:
            logger.error("No valid session ID provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Valid session ID is required"
            )

        # Check required fields
        if not question_id:
            logger.error("No question_id provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="question_id is required"
            )

        if answer is None:
            logger.error("No answer provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="answer is required"
            )

        # Forward the request to the AI service
        result = await request_ai_service(f"questionnaire/{session_id}/answer", {
            "question_id": question_id,
            "answer": answer,
            "question_text": body.get("question_text"),
            "previous_question_ids": body.get("previous_question_ids", []),
            "question_count": body.get("question_count", 0)
        })
        return result

    except HTTPException as e:
        # Re-raise HTTP exceptions
        logger.error("HTTP exception in submit_answer: %s", e.detail)
        raise e
    except Exception as e:
        logger.error("Unhandled error in submit_answer: %s", e)
        logger.error(traceback.format_exc())
        # Return HTTP 500 with detailed error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process answer: {str(e)}"
        )

# Complete questionnaire endpoint
@router.post("/complete", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def complete_questionnaire(request: Request):
    """
    Complete the questionnaire and prepare for birth time rectification.

    This endpoint finalizes the questionnaire and returns summary data
    necessary for starting the rectification process.

    Request body:
    - session_id: The questionnaire session ID to complete
    - chart_id: The chart ID to associate with this questionnaire
    """
    try:
        logger.info("Starting questionnaire completion")

        # Parse the request body
        body = await request.json()

        # Extract required fields
        session_id = body.get("session_id")
        chart_id = body.get("chart_id")

        # Validate required fields
        if not session_id:
            logger.error("No session_id provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id is required"
            )

        if not chart_id:
            logger.error("No chart_id provided")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="chart_id is required"
            )

        logger.info("Completing questionnaire for session %s, chart %s", session_id, chart_id)

        # Forward request to the AI service
        result = await request_ai_service("questionnaire/complete", {
            "session_id": session_id,
            "chart_id": chart_id,
            # Include any additional fields from the request
            "question_count": body.get("question_count"),
            "confidence": body.get("confidence")
        })

        logger.info("Questionnaire completed successfully for session %s", session_id)
        return result

    except HTTPException as e:
        # Re-raise HTTP exceptions
        logger.error("HTTP exception in complete_questionnaire: %s", e.detail)
        raise e
    except Exception as e:
        logger.error("Unhandled error in complete_questionnaire: %s", e)
        logger.error(traceback.format_exc())
        # Return HTTP 500 with detailed error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete questionnaire: {str(e)}"
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
        logger.info("Getting rectification status for session: %s", session_id)

        # Use the correct endpoint path for the AI service
        result = await request_ai_service(f"questionnaire/{session_id}/rectification/status", {}, method="GET")

        return result
    except Exception as exc:
        logger.error("Error getting rectification status: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rectification status: {str(exc)}"
        ) from exc

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
        logger.info("Processing rectification for chart: %s", data.get('chart_id'))

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
        logger.error("Error processing rectification: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rectification processing failed: {str(exc)}"
        ) from exc

# Add the generate endpoint
@router.post("/generate", status_code=status.HTTP_200_OK, response_model=Dict[str, Any])
async def generate_questionnaire(request: QuestionnaireGenerateRequest):
    """
    Generate questionnaire data based on birth details and previous answers.

    This endpoint creates an AI-powered, personalized questionnaire for
    birth time rectification based on astrological principles.

    Request body:
    - birth_details: Birth details including date, time, and location
    - previous_answers: Previous answers from the questionnaire (optional)
    - current_confidence: Current confidence level (optional)
    - session_id: Optional session ID to use
    """
    try:
        logger.info("Generating questionnaire with birth details: %s", request.birth_details)

        # Prepare request data for the AI service
        request_data = {
            "birth_details": request.birth_details,
            "previous_answers": request.previous_answers,
            "current_confidence": request.current_confidence
        }

        # Add session_id if provided
        if request.session_id:
            request_data["session_id"] = request.session_id

        # Use the correct endpoint path for the AI service
        result = await request_ai_service("questionnaire/generate", request_data)

        return result
    except Exception as exc:
        logger.error("Error generating questionnaire: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Questionnaire generation failed: {str(exc)}"
        ) from exc
