"""
Session management router for the Birth Time Rectifier API.
Handles session initialization, status checking, and management.
"""

import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from typing import Dict, Any, Optional
import logging

from ai_service.core.config import settings
from ai_service.api.middleware.session import get_session_id, save_session, get_session
from ai_service.api.websocket_events import emit_event, EventType
from ai_service.utils.dependency_container import get_instance
from ai_service.services.session_service import SessionService
from pydantic import BaseModel

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["session"])

class SessionResponse(BaseModel):
    """Session creation response."""
    session_id: str
    expires_at: int

@router.post("/init", response_model=SessionResponse)
async def init_session():
    """
    Initialize a new session.

    Returns a session token that should be included in subsequent requests.
    """
    try:
        # Get session service from dependency container
        session_service = get_instance(SessionService)
        if not session_service:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Session service not available"
            )

        # Create new session
        session_id = session_service.create_session()

        # Get current time plus expiry in seconds
        expires_at = int(time.time()) + session_service.session_expiry

        return {
            "session_id": session_id,
            "expires_at": expires_at
        }
    except Exception as e:
        logger.error(f"Error initializing session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize session"
        )

@router.get("/status")
async def get_session_status(request: Request):
    """
    Get the status of the current session.

    Returns session metadata including active status and expiration time.
    """
    # Check if there's an active session
    if not hasattr(request.state, "session_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session"
        )

    session_id = request.state.session_id
    session_data = request.state.session

    # Calculate TTL in seconds (convert days to seconds)
    session_ttl_seconds = settings.SESSION_EXPIRY_DAYS * 24 * 60 * 60

    return {
        "session_id": session_id,
        "status": "active",
        "created_at": session_data.get("created_at", time.time()),
        "expires_at": session_data.get("expires_at", time.time() + session_ttl_seconds)
    }

@router.post("/data")
async def update_session_data(
    request: Request,
    data: Dict[str, Any]
):
    """
    Update session data.

    Adds or updates custom data in the session.
    """
    # Check if there's an active session
    if not hasattr(request.state, "session_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session"
        )

    session_id = request.state.session_id
    session_data = request.state.session

    # Merge new data with existing session data
    for key, value in data.items():
        # Don't allow overriding reserved keys
        if key not in ["created_at", "expires_at", "status"]:
            session_data[key] = value

    # Save updated session data
    save_session(session_id, session_data)

    return {
        "status": "success",
        "message": "Session data updated"
    }

@router.get("/data")
async def get_session_data(request: Request):
    """
    Get session data.

    Returns all custom data stored in the session.
    """
    # Check if there's an active session
    if not hasattr(request.state, "session_id"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session"
        )

    session_id = request.state.session_id
    session_data = request.state.session

    # Filter out reserved keys
    reserved_keys = ["created_at", "expires_at", "status"]
    custom_data = {k: v for k, v in session_data.items() if k not in reserved_keys}

    return custom_data
