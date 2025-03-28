"""
User-related API routes
----------------------
Handles user account management, preferences, and profile settings.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from typing import Dict, Any, Optional, List
import httpx
import os
import json
import logging
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger("api_gateway.routes.user")

# Initialize router
router = APIRouter()

# AI Service URL - configure from environment variables
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")

# Define request/response models
class UserPreferences(BaseModel):
    theme: str = Field(default="light", description="UI theme preference")
    language: str = Field(default="en", description="Language preference")
    notifications_enabled: bool = Field(default=True, description="Whether notifications are enabled")
    chart_view_mode: str = Field(default="vedic", description="Default chart view mode")

class UserProfile(BaseModel):
    name: str = Field(..., description="User's name")
    email: str = Field(..., description="User's email")
    bio: Optional[str] = Field(default=None, description="User's bio")
    birth_details: Optional[Dict[str, Any]] = Field(default=None, description="User's birth details")

# Proxy function for forwarding requests to the AI service
async def request_ai_service(endpoint: str, data: Dict[str, Any] = {}, method: str = "POST") -> Dict[str, Any]:
    """
    Forward a request to the AI service.

    Args:
        endpoint: The endpoint path on the AI service
        data: The request data to send
        method: The HTTP method to use

    Returns:
        The response from the AI service
    """
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(f"{AI_SERVICE_URL}{endpoint}", params=data, timeout=30.0)
            else:
                response = await client.post(f"{AI_SERVICE_URL}{endpoint}", json=data, timeout=30.0)

            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Error forwarding request to AI service: {e}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail=f"Error communicating with backend service: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from AI service: {e}")
            error_detail = e.response.json() if e.response.headers.get("content-type") == "application/json" else str(e)
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)

# Routes
@router.get("/preferences", status_code=status.HTTP_200_OK)
async def get_user_preferences(request: Request):
    """
    Get the current user's preferences.
    """
    session_id = request.headers.get("X-Session-ID")
    return await request_ai_service(f"/api/v1/user/preferences", {"session_id": session_id}, "GET")

@router.post("/preferences", status_code=status.HTTP_200_OK)
async def update_user_preferences(preferences: UserPreferences, request: Request):
    """
    Update the current user's preferences.
    """
    session_id = request.headers.get("X-Session-ID")
    data = {
        "session_id": session_id,
        "preferences": preferences.dict()
    }
    return await request_ai_service(f"/api/v1/user/preferences", data, "POST")

@router.get("/profile", status_code=status.HTTP_200_OK)
async def get_user_profile(request: Request):
    """
    Get the current user's profile.
    """
    session_id = request.headers.get("X-Session-ID")
    return await request_ai_service(f"/api/v1/user/profile", {"session_id": session_id}, "GET")

@router.post("/profile", status_code=status.HTTP_200_OK)
async def update_user_profile(profile: UserProfile, request: Request):
    """
    Update the current user's profile.
    """
    session_id = request.headers.get("X-Session-ID")
    data = {
        "session_id": session_id,
        "profile": profile.dict()
    }
    return await request_ai_service(f"/api/v1/user/profile", data, "POST")

@router.get("/charts", status_code=status.HTTP_200_OK)
async def get_user_charts(request: Request):
    """
    Get a list of the current user's saved charts.
    """
    session_id = request.headers.get("X-Session-ID")
    return await request_ai_service(f"/api/v1/user/charts", {"session_id": session_id}, "GET")
