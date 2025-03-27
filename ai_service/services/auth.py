"""
Authentication service for Birth Time Rectifier AI Service.

This module provides authentication functionality for the AI service
using the shared authentication utilities in ai_service/utils/auth_utils.py.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, cast, Union

import jwt

# Import the repository
from ai_service.services import user_repository

# Import shared authentication utilities
from ai_service.utils.auth_utils import (
    create_access_token as shared_create_access_token,
    verify_token as shared_verify_token,
    JWT_SECRET,
    JWT_ALGORITHM
)

# Configure logging
logger = logging.getLogger(__name__)

# User type
User = Dict[str, Any]

def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Authenticate a user with email and password.

    Args:
        email: User's email
        password: User's password

    Returns:
        User object if authentication is successful, None otherwise
    """
    # Get user from repository
    user = user_repository.get_user_by_email(email)

    # Check if user exists
    if not user:
        return None

    # Verify password
    if not verify_password(password, user["password"]):
        return None

    return cast(User, user)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password is correct, False otherwise
    """
    from ai_service.utils.dependency_container import get_container
    container = get_container()
    password_service = container.get("password_service")
    return password_service.verify_password(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    from ai_service.utils.dependency_container import get_container
    container = get_container()
    password_service = container.get("password_service")
    return password_service.hash_password(password)

def create_user(email: str, password: str, full_name: str) -> Optional[User]:
    """
    Create a new user.

    Args:
        email: User's email
        password: User's password
        full_name: User's full name

    Returns:
        Created user object if successful, None if user already exists
    """
    # Check if user already exists
    if user_repository.get_user_by_email(email):
        return None

    # Hash password
    hashed_password = hash_password(password)

    # Create user
    user = {
        "email": email,
        "password": hashed_password,
        "full_name": full_name,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "preferences": {}
    }

    # Save user
    user_id = user_repository.create_user(user)
    if not user_id:
        return None

    # Add ID to user object
    user["id"] = user_id

    return cast(User, user)

def create_access_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token using the shared implementation.

    Args:
        user_id: User ID to include in the token
        expires_delta: Optional custom expiration time
        additional_data: Optional additional data to include in the token

    Returns:
        JWT token string
    """
    return shared_create_access_token(user_id, expires_delta, additional_data)

def verify_token(token: str) -> Optional[str]:
    """
    Verify and decode a JWT token using the shared implementation.

    Args:
        token: JWT token to verify

    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        # Use shared implementation
        user_id = shared_verify_token(token)

        # Additional check: verify that user exists in our database
        if user_id and not user_repository.user_exists(user_id):
            logger.warning(f"User ID {user_id} from token does not exist in database")
            return None

        return user_id
    except jwt.PyJWTError:
        return None

def get_user_by_id(user_id: str) -> Optional[User]:
    """
    Get a user by ID.

    Args:
        user_id: User ID

    Returns:
        User object if found, None otherwise
    """
    user_dict = user_repository.get_user(user_id)
    return cast(User, user_dict) if user_dict else None

def convert_to_user_out(user: User) -> Dict[str, Any]:
    """
    Convert a User object to a UserOut model.

    Args:
        user: User object

    Returns:
        Dictionary representation of UserOut
    """
    return {
        "id": user["id"],
        "email": user["email"],
        "full_name": user["full_name"],
        "created_at": user["created_at"],
        "updated_at": user["updated_at"],
        "preferences": user["preferences"]
    }

def update_user_preferences(user_id: str, preferences: Dict[str, Any]) -> bool:
    """
    Update a user's preferences.

    Args:
        user_id: User ID
        preferences: New or updated preferences

    Returns:
        True if successful, False otherwise
    """
    return user_repository.update_preferences(user_id, preferences)

def get_user_charts(user_id: str) -> List[str]:
    """
    Get a user's saved charts.

    Args:
        user_id: User ID

    Returns:
        List of chart IDs
    """
    return user_repository.get_user_charts(user_id)

def add_chart_to_user(user_id: str, chart_id: str) -> bool:
    """
    Add a chart to a user's saved charts.

    Args:
        user_id: User ID
        chart_id: Chart ID

    Returns:
        True if successful, False otherwise
    """
    return user_repository.add_chart(user_id, chart_id)

def remove_chart_from_user(user_id: str, chart_id: str) -> bool:
    """
    Remove a chart from a user's saved charts.

    Args:
        user_id: User ID
        chart_id: Chart ID

    Returns:
        True if successful, False otherwise
    """
    return user_repository.remove_chart(user_id, chart_id)
