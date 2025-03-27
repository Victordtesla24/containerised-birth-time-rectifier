"""
Session management router for the Birth Time Rectifier API.

This module provides endpoints for session initialization and management.
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Body
from typing import Dict, Any, Optional
import logging
import uuid
import time
from pydantic import BaseModel

from ai_service.core.config import settings
from ai_service.services.session_service import SessionService, get_session_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Models
class SessionResponse(BaseModel):
    """Session response model."""
    session_id: str
    expires_at: int
    status: str

@router.get("/init", response_model=SessionResponse)
async def initialize_session() -> Dict[str, Any]:
    """
    Initialize a new session.

    Returns a session ID that must be included in subsequent requests as the X-Session-ID header.
    """
    # Generate a unique session ID
    session_id = str(uuid.uuid4())

    # Set expiry (24 hours from now)
    session_expiry = 3600 * 24  # 1 day in seconds

    # Get current time plus expiry in seconds
    expires_at = int(time.time()) + session_expiry

    logger.info(f"Created new session: {session_id}")

    # Return the session information
    return {
        "session_id": session_id,
        "expires_at": expires_at,
        "status": "active"
    }

@router.get("/status")
async def get_session_status(
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Dict[str, Any]:
    """
    Get the status of an existing session.

    Args:
        session_id: Session ID from header

    Returns:
        Session status information
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header is required")

    # For now, return a basic status since we don't have session storage yet
    # In a real implementation, we would validate the session against storage
    return {
        "session_id": session_id,
        "status": "active",
        "last_activity": int(time.time())
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
