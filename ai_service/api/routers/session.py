"""
Session management router for the Birth Time Rectifier API.
Handles session initialization, status checking, and management.
"""

import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from typing import Dict, Any, Optional

from ai_service.core.config import settings
from ai_service.api.middleware.session import get_session_id, save_session, get_session
from ai_service.api.websocket_events import emit_event, EventType

router = APIRouter(tags=["session"])

@router.get("/init")
async def initialize_session(request: Request, background_tasks: BackgroundTasks):
    """
    Initialize a new session.

    Returns session ID and metadata that can be used for subsequent requests.
    """
    try:
        # Generate a new session ID
        session_id = str(uuid.uuid4())

        # Create session data
        session_data = {
            "created_at": time.time(),
            "expires_at": time.time() + settings.SESSION_TTL,
            "status": "active"
        }

        # Save session data
        save_session(session_id, session_data)

        # Store the new session ID in request state for middleware
        request.state.new_session_id = session_id

        # Prepare response data
        response_data = {
            "session_id": session_id,
            "created_at": session_data["created_at"],
            "expires_at": session_data["expires_at"],
            "status": "active"
        }

        # Try to emit session created event in the background
        # This is optional and the function should work even if it fails
        try:
            background_tasks.add_task(
                emit_event,
                session_id=session_id,
                event_type=EventType.SESSION_CREATED,
                data={
                    "session_id": session_id,
                    "timestamp": session_data["created_at"]
                }
            )
        except Exception as e:
            # Log but don't fail the request if websocket event emission fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to add websocket event task: {str(e)}")

        return response_data

    except Exception as e:
        # Log the error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Session initialization error: {str(e)}")

        # Return a sensible error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initializing session: {str(e)}"
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
