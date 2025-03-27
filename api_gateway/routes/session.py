from fastapi import APIRouter, HTTPException, Request, status
from typing import Dict, Any, Optional
import httpx
import os
import logging
import time
import uuid
import traceback

# Set up logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Helper function to request data from the AI service
async def request_ai_service(endpoint: str, data: Dict[str, Any] = {}, method: str = "POST") -> Dict[str, Any]:
    """Send a request to the AI service for session operations"""
    # Use the correct service URL with proper resolution
    ai_service_host = os.getenv("AI_SERVICE_HOST", "localhost")
    ai_service_port = os.getenv("AI_SERVICE_PORT", "8000")
    ai_service_url = f"http://{ai_service_host}:{ai_service_port}"

    url = f"{ai_service_url}/api/v1/session/{endpoint}"
    logger.info(f"Requesting AI service at {url} with method {method}")

    try:
        # Use proper HTTP client configuration
        timeout_seconds = 15.0  # Increase timeout for reliability

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            if method == "GET":
                response = await client.get(url, params=data)
            else:
                response = await client.post(url, json=data)

            if response.status_code != 200:
                logger.error(f"AI service returned error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"AI service error: {response.text}"
                )

            return response.json()
    except httpx.ConnectError as e:
        logger.error(f"Connection error to AI service: {e} - URL: {url}")
        # Don't use fallbacks - propagate the real error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service connection error: {str(e)}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error to AI service: {e} - URL: {url}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service request error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error requesting AI service: {e} - {type(e).__name__}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

@router.get("/init")
async def init_session_get():
    """
    Initialize a new session.

    Returns a session token that should be included in subsequent requests.
    """
    try:
        # Forward to AI service - no local generation
        result = await request_ai_service("init", {}, method="GET")

        # Return the session data directly from the backend service
        return result
    except Exception as e:
        logger.error(f"Error initializing session: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize session: {str(e)}"
        )

@router.post("/init")
async def init_session_post():
    """POST version of session initialization endpoint"""
    return await init_session_get()

@router.get("/status")
async def get_session_status(session_id: str):
    """
    Get the status of the current session.

    Returns session metadata including active status and expiration time.
    """
    try:
        # Forward to AI service
        result = await request_ai_service(
            "status",
            {"session_id": session_id},
            method="GET"
        )

        return result
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}"
        )

@router.post("/data")
async def update_session_data(session_id: str, data: Dict[str, Any]):
    """
    Update session data.

    Adds or updates custom data in the session.
    """
    try:
        # Forward to AI service
        result = await request_ai_service(
            "data",
            {"session_id": session_id, **data},
            method="POST"
        )

        return result
    except Exception as e:
        logger.error(f"Error updating session data: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session data: {str(e)}"
        )

@router.get("/data")
async def get_session_data(session_id: str):
    """
    Get session data.

    Returns all custom data stored in the session.
    """
    try:
        # Forward to AI service
        result = await request_ai_service(
            "data",
            {"session_id": session_id},
            method="GET"
        )

        return result
    except Exception as e:
        logger.error(f"Error getting session data: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session data: {str(e)}"
        )
