"""
Session management router for the Birth Time Rectifier API.
Handles session initialization, status checking, and management.
"""

import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks, Response
from typing import Dict, Any, Optional
import logging

from ai_service.core.config import settings
from ai_service.services.session_service import SessionService, get_session_service
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["session"])

class SessionResponse(BaseModel):
    """Session creation response."""
    session_id: str
    expires_at: int
    status: str = "active"

@router.post("/init", response_model=SessionResponse)
async def init_session():
    """
    Initialize a new session.

    Returns a session token that should be included in subsequent requests.
    """
    try:
        # Get session service
        session_service = get_session_service()

        # Create new session
        session_id = session_service.create_session()

        # Get current time plus expiry in seconds
        expires_at = int(time.time()) + session_service.session_expiry

        return {
            "session_id": session_id,
            "expires_at": expires_at,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Error initializing session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize session"
        )

@router.get("/init", response_model=SessionResponse)
async def init_session_get():
    """
    Initialize a new session (GET method).

    This is functionally identical to the POST version but supports GET requests
    for compatibility with some clients.

    Returns a session token that should be included in subsequent requests.
    """
    return await init_session()

@router.get("/status")
async def get_session_status(request: Request, session_id: str):
    """
    Get the status of the current session.

    Returns session metadata including active status and expiration time.
    """
    # Get session service
    session_service = get_session_service()

    # Get session data
    session_data = session_service.get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found"
        )

    # Return session status
    return {
        "session_id": session_id,
        "status": session_data.get("status", "active"),
        "created_at": session_data.get("created_at", time.time()),
        "expires_at": session_data.get("expires_at", time.time() + session_service.session_expiry)
    }

@router.post("/data")
async def update_session_data(
    session_id: str,
    data: Dict[str, Any]
):
    """
    Update session data.

    Adds or updates custom data in the session.
    """
    # Get session service
    session_service = get_session_service()

    # Filter out reserved keys
    filtered_data = {k: v for k, v in data.items() if k not in ["created_at", "expires_at", "status"]}

    # Update session with filtered data
    success = session_service.update_session(session_id, {"data": filtered_data})

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to update session data"
        )

    return {
        "status": "success",
        "message": "Session data updated"
    }

@router.get("/data")
async def get_session_data(session_id: str):
    """
    Get session data.

    Returns all custom data stored in the session.
    """
    # Get session service
    session_service = get_session_service()

    # Get session data
    session_data = session_service.get_session(session_id)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found"
        )

    # Return user data if it exists, otherwise empty dict
    return session_data.get("data", {})
