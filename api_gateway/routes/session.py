"""
Session management route handlers for the Birth Time Rectifier API Gateway.
"""

from fastapi import APIRouter, HTTPException, Request, status
from typing import Dict, Any, Optional
import httpx
import os
import logging
import time
import uuid
import traceback
import json

# Set up logging
logger = logging.getLogger("api_gateway.routes.session")

# Create router
router = APIRouter(prefix="/api/session", tags=["session"])

# AI Service URL
AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://localhost:8001")
if AI_SERVICE_URL and AI_SERVICE_URL.endswith("/"):
    AI_SERVICE_URL = AI_SERVICE_URL[:-1]

# Helper function to request data from the AI service
async def request_ai_service(endpoint: str, data: Dict[str, Any] = {}, method: str = "POST") -> Dict[str, Any]:
    """Send a request to the AI service for session operations"""
    ai_service_url = AI_SERVICE_URL

    url = f"{ai_service_url}/api/v1/{endpoint}"
    logger.info(f"Requesting AI service at {url}")

    try:
        # Use proper HTTP client configuration
        timeout_seconds = 15.0  # Increase timeout for reliability

        async with httpx.AsyncClient(
            verify=True,  # Explicitly enable SSL verification
            timeout=timeout_seconds
        ) as client:
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
async def initialize_session(request: Request):
    """
    Initialize a new session.
    Proxies to the AI service's session initialization endpoint.
    """
    try:
        # Construct target URL
        target_url = f"{AI_SERVICE_URL}/api/v1/session/init"

        # Extract headers
        headers = {k: v for k, v in request.headers.items()
                  if k.lower() not in ["host", "content-length"]}

        logger.info("Session initialization request")

        # Make request to AI service
        async with httpx.AsyncClient(
            verify=True,  # Explicitly enable SSL verification
            timeout=30.0
        ) as client:
            response = await client.get(target_url, headers=headers)

            # Check response status
            if response.status_code >= 400:
                logger.error(f"Error from AI service: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Error initializing session: {response.text}"
                )

            # Parse response
            try:
                result = response.json()
                logger.info(f"Session initialized successfully: {result.get('session_id', 'unknown')}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing session response: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Invalid response from session service"
                )

    except httpx.RequestError as e:
        logger.error(f"Error making request to session service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session service unavailable"
        )

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
