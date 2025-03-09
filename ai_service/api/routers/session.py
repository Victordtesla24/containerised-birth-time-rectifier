"""
Session management router for the Birth Time Rectifier API.
Handles session initialization, status checking, and management.
"""

import time
from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, Any

from ai_service.core.config import settings
from ai_service.api.middleware.session import get_session, save_session

router = APIRouter(tags=["session"])

@router.get("/init")
async def initialize_session(request: Request):
    """
    Initialize a new session.

    Returns session ID and metadata that can be used for subsequent requests.
    """
    # Check if a new session was created by the middleware
    if not hasattr(request.state, "new_session_id"):
        # Create a session ID (This might happen if the middleware setup isn't complete)
        return {
            "status": "error",
            "message": "Session initialization failed"
        }

    # Session was created by middleware
    session_id = request.state.new_session_id

    # Return session info
    return {
        "session_id": session_id,
        "created_at": time.time(),
        "expires_at": time.time() + settings.SESSION_TTL,
        "status": "active"
    }

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

    return {
        "session_id": session_id,
        "status": "active",
        "created_at": session_data.get("created_at", time.time()),
        "expires_at": session_data.get("expires_at", time.time() + settings.SESSION_TTL)
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
        if key not in ["created_at", "expires_at"]:
            session_data[key] = value

    # Save updated session data
    save_session(session_id, session_data)

    return {
        "status": "success",
        "message": "Session data updated"
    }
