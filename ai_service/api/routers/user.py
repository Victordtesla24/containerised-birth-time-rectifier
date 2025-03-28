"""
User Router.

This module provides endpoints for user account management, preferences, and profile settings.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field
import json
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Session directory from environment
SESSION_DIR = os.environ.get("SESSION_DIR", "sessions")

# Create router
router = APIRouter()

# Define models
class UserPreferences(BaseModel):
    """User preferences model."""
    theme: str = Field(default="light", description="UI theme preference")
    language: str = Field(default="en", description="Language preference")
    notifications_enabled: bool = Field(default=True, description="Whether notifications are enabled")
    chart_view_mode: str = Field(default="vedic", description="Default chart view mode")

class UserProfile(BaseModel):
    """User profile model."""
    name: str = Field(..., description="User's name")
    email: str = Field(..., description="User's email")
    bio: Optional[str] = Field(None, description="User's bio")
    birth_details: Optional[Dict[str, Any]] = Field(None, description="User's birth details")

# Routes
@router.get("/preferences", response_model=Dict[str, Any])
async def get_preferences(session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    """
    Get the current user's preferences.

    Args:
        session_id: The session ID to retrieve preferences for

    Returns:
        User preferences
    """
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID is required")

    try:
        # Try to load preferences from session file
        session_file = os.path.join(SESSION_DIR, f"{session_id}.json")
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session_data = json.load(f)
                preferences = session_data.get("preferences", UserPreferences().dict())
                return {
                    "success": True,
                    "preferences": preferences
                }
        else:
            # Return default preferences if not found
            return {
                "success": True,
                "preferences": UserPreferences().dict()
            }
    except Exception as e:
        logger.error(f"Error retrieving preferences for session {session_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/preferences", response_model=Dict[str, Any])
async def update_preferences(
    preferences: UserPreferences,
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Update the current user's preferences.

    Args:
        preferences: The preferences to update
        session_id: The session ID to update preferences for

    Returns:
        Updated preferences
    """
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID is required")

    try:
        # Ensure session directory exists
        os.makedirs(SESSION_DIR, exist_ok=True)

        # Load existing session data or create new
        session_file = os.path.join(SESSION_DIR, f"{session_id}.json")
        session_data = {}
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session_data = json.load(f)

        # Update preferences
        session_data["preferences"] = preferences.dict()
        session_data["updated_at"] = datetime.now().isoformat()

        # Save updated session data
        with open(session_file, 'w') as f:
            json.dump(session_data, f)

        return {
            "success": True,
            "preferences": preferences.dict()
        }
    except Exception as e:
        logger.error(f"Error updating preferences for session {session_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/profile", response_model=Dict[str, Any])
async def get_profile(session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    """
    Get the current user's profile.

    Args:
        session_id: The session ID to retrieve profile for

    Returns:
        User profile
    """
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID is required")

    try:
        # Try to load profile from session file
        session_file = os.path.join(SESSION_DIR, f"{session_id}.json")
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session_data = json.load(f)
                profile = session_data.get("profile", {
                    "name": "Anonymous User",
                    "email": f"user-{session_id[:8]}@example.com",
                    "bio": None,
                    "birth_details": None
                })
                return {
                    "success": True,
                    "profile": profile
                }
        else:
            # Return default profile if not found
            return {
                "success": True,
                "profile": {
                    "name": "Anonymous User",
                    "email": f"user-{session_id[:8]}@example.com",
                    "bio": None,
                    "birth_details": None
                }
            }
    except Exception as e:
        logger.error(f"Error retrieving profile for session {session_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/profile", response_model=Dict[str, Any])
async def update_profile(
    profile: UserProfile,
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
):
    """
    Update the current user's profile.

    Args:
        profile: The profile to update
        session_id: The session ID to update profile for

    Returns:
        Updated profile
    """
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID is required")

    try:
        # Ensure session directory exists
        os.makedirs(SESSION_DIR, exist_ok=True)

        # Load existing session data or create new
        session_file = os.path.join(SESSION_DIR, f"{session_id}.json")
        session_data = {}
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session_data = json.load(f)

        # Update profile
        session_data["profile"] = profile.dict()
        session_data["updated_at"] = datetime.now().isoformat()

        # Save updated session data
        with open(session_file, 'w') as f:
            json.dump(session_data, f)

        return {
            "success": True,
            "profile": profile.dict()
        }
    except Exception as e:
        logger.error(f"Error updating profile for session {session_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/charts", response_model=Dict[str, Any])
async def get_user_charts(session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    """
    Get a list of the current user's saved charts.

    Args:
        session_id: The session ID to retrieve charts for

    Returns:
        List of user charts
    """
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID is required")

    try:
        # Try to load charts from session file
        session_file = os.path.join(SESSION_DIR, f"{session_id}.json")
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session_data = json.load(f)
                charts = session_data.get("charts", [])
                return {
                    "success": True,
                    "charts": charts
                }
        else:
            # Return empty list if not found
            return {
                "success": True,
                "charts": []
            }
    except Exception as e:
        logger.error(f"Error retrieving charts for session {session_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
