"""
Authentication router for the Birth Time Rectifier API.
Handles user registration, login, and profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ai_service.models.user import UserCreate, UserOut, UserLogin, UserUpdate, Token
from ai_service.services.auth import (
    create_user, authenticate_user, create_access_token, verify_token,
    get_user_by_id, convert_to_user_out, update_user_preferences,
    get_user_charts, add_chart_to_user, remove_chart_from_user
)

# Create router
auth_router = APIRouter(tags=["auth"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# Dependencies
async def get_current_user(token: str = Security(oauth2_scheme)) -> str:
    """Get the current authenticated user ID from the token."""
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


# Auth endpoints
@auth_router.post("/register", response_model=UserOut)
async def register_user(user_create: UserCreate):
    """Register a new user."""
    try:
        user = create_user(user_create)
        return convert_to_user_out(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@auth_router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login a user with username/email and password."""
    # Form data uses username field, but we support login with email
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        user_id=user.id,
        expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_at=datetime.utcnow() + access_token_expires,
        user_id=user.id
    )


@auth_router.get("/me", response_model=UserOut)
async def get_current_user_profile(user_id: str = Depends(get_current_user)):
    """Get the current user's profile."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return convert_to_user_out(user)


@auth_router.put("/me", response_model=UserOut)
async def update_current_user(
    user_update: UserUpdate,
    user_id: str = Depends(get_current_user)
):
    """Update the current user's profile."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update user
    if user_update.full_name is not None:
        user.full_name = user_update.full_name

    if user_update.preferences is not None:
        update_user_preferences(user_id, user_update.preferences)

    user.updated_at = datetime.now()

    return convert_to_user_out(user)


# Saved charts management endpoints
@auth_router.get("/me/charts", response_model=List[str])
async def get_user_saved_charts(user_id: str = Depends(get_current_user)):
    """Get all charts saved by the current user."""
    return get_user_charts(user_id)


@auth_router.post("/me/charts/{chart_id}", response_model=Dict[str, bool])
async def save_chart(
    chart_id: str,
    user_id: str = Depends(get_current_user)
):
    """Save a chart to the current user's profile."""
    success = add_chart_to_user(user_id, chart_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {"success": True}


@auth_router.delete("/me/charts/{chart_id}", response_model=Dict[str, bool])
async def remove_saved_chart(
    chart_id: str,
    user_id: str = Depends(get_current_user)
):
    """Remove a saved chart from the current user's profile."""
    success = remove_chart_from_user(user_id, chart_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found or chart not saved"
        )

    return {"success": True}
