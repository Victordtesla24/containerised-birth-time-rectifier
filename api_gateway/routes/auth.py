"""
Authentication-related API routes
--------------------------------
Handles user authentication, session management, and authorization.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from typing import Dict, Any, Optional
import httpx
import os
import json
import logging
import secrets
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

# AI Service URL
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")

# Configure logging
logger = logging.getLogger("api_gateway.routes.auth")

# Initialize router
router = APIRouter(prefix="/auth", tags=["auth"])

# Define request/response models
class LoginRequest(BaseModel):
    username: str = Field(..., description="User's username")
    password: str = Field(..., description="User's password")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    success: bool = True

class SessionResponse(BaseModel):
    session_token: str

# Add verification function definition
def verify_credentials(username: str, password: str) -> bool:
    """
    Verify user credentials against the authentication system.

    Args:
        username: The user's username
        password: The user's password

    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        # In a production system, this would verify against a real database
        # Here we implement a simple verification for testing/development

        # Define allowed test credentials
        valid_credentials = {
            "admin": "admin123",
            "test_user": "password123",
            "demo": "demo123"
        }

        # Check if username exists and password matches
        if username in valid_credentials and valid_credentials[username] == password:
            logger.info(f"Successfully authenticated user: {username}")
            return True

        logger.warning(f"Failed authentication attempt for user: {username}")
        return False

    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return False

# Routes
@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Authenticate a user and generate an access token.
    """
    if not verify_credentials(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = secrets.token_hex(32)
    refresh_token = secrets.token_hex(32)
    expires_in = 3600  # 1 hour

    # In production, store token info in Redis or another fast database

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "success": True
    }

@router.post("/logout")
async def logout(request: Request):
    """
    Log out a user by invalidating their token.
    """
    # Get the token from the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split("Bearer ")[1]

    # In production, invalidate the token in the database

    return {"success": True, "message": "User logged out successfully"}

@router.post("/refresh")
async def refresh_token(refresh_token: str):
    """
    Generate a new access token using a refresh token.
    """
    # In production, validate the refresh token against the database

    # Generate new tokens
    access_token = secrets.token_hex(32)
    new_refresh_token = secrets.token_hex(32)
    expires_in = 3600  # 1 hour

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "refresh_token": new_refresh_token,
        "success": True
    }

@router.post("/session/init", response_model=SessionResponse)
async def init_session():
    """
    Initialize a new session for the user.

    Creates a new session in Redis and returns a session token to the client.
    This token should be included in all subsequent requests.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/session/init",
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"Failed to initialize session: {response.text}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize session"
                )

            return response.json()
    except Exception as e:
        logger.error(f"Error initializing session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize session"
        )
