"""
Authentication service for Birth Time Rectifier AI Service.

This module provides authentication functionality for the AI service
using the shared authentication utilities in ai_service/utils/auth_utils.py.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, cast, Union
import json

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

async def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Authenticate a user with email and password.

    Args:
        email: User's email
        password: User's password

    Returns:
        User object if authentication is successful, None otherwise
    """
    if not email or not password:
        logger.warning("Authentication attempt with empty credentials")
        return None

    try:
        # Get user from repository
        try:
            user = await user_repository["get_user_by_email"](email)
        except KeyError:
            logger.error("User repository missing method 'get_user_by_email'")
            return None
        except Exception as e:
            logger.error(f"Error retrieving user by email: {e}")
            return None

        # Check if user exists
        if not user:
            logger.info(f"Authentication failed: No user found with email {email}")
            return None

        # Verify password
        try:
            if not verify_password(password, user["password_hash"]):
                logger.info(f"Authentication failed: Invalid password for user {email}")
                return None
        except KeyError:
            logger.error(f"User data missing password_hash field")
            return None
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return None

        return cast(User, user)
    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}")
        return None

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

async def create_user(email: str, password: str, full_name: str) -> Optional[User]:
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
    existing_user = await user_repository["get_user_by_email"](email)
    if existing_user:
        return None

    # Hash password
    hashed_password = hash_password(password)

    # Create user with all required fields
    user = {
        "email": email,
        "username": email.split('@')[0],  # Use first part of email as username
        "password_hash": hashed_password,
        "full_name": full_name,
        "preferences": json.dumps({}),  # Store empty dict as JSON string
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # Save user
    user_id = await user_repository["create_user"](user)
    if not user_id:
        return None

    # Add ID to user object
    user["user_id"] = user_id

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

async def verify_token(token: str) -> Optional[str]:
    """
    Verify and decode a JWT token using the shared implementation.

    Args:
        token: JWT token to verify

    Returns:
        User ID if token is valid, None otherwise
    """
    if not token:
        logger.warning("Empty token received for verification")
        return None

    try:
        # Use shared implementation
        user_id = shared_verify_token(token)

        if not user_id:
            logger.warning("Token verification failed: No user ID returned")
            return None

        # Additional check: verify that user exists in our database
        try:
            user_exists = await user_repository["user_exists"](user_id)
            if not user_exists:
                logger.warning(f"User ID {user_id} from token does not exist in database")
                return None
        except KeyError:
            logger.error("User repository missing method 'user_exists'")
            return None
        except Exception as e:
            logger.error(f"Error checking user existence: {e}")
            return None

        return user_id
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Token verification failed: Invalid token format")
        return None
    except jwt.PyJWTError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        return None

async def get_user_by_id(user_id: str) -> Optional[User]:
    """
    Get a user by ID.

    Args:
        user_id: User ID

    Returns:
        User object if found, None otherwise
    """
    user_dict = await user_repository["get_user"](user_id)
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
        "id": user.get("user_id", ""),
        "email": user.get("email", ""),
        "full_name": user.get("full_name", ""),
        "created_at": user.get("created_at", ""),
        "updated_at": user.get("updated_at", ""),
        "preferences": user.get("preferences", {})
    }

async def update_user_preferences(user_id: str, preferences: Dict[str, Any]) -> bool:
    """
    Update a user's preferences.

    Args:
        user_id: User ID
        preferences: New or updated preferences

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if user exists before updating preferences
        if not await user_repository["user_exists"](user_id):
            logger.error(f"Cannot update preferences: User ID {user_id} does not exist")
            return False

        # Convert preferences to JSON string if needed by the repository
        preferences_data = json.dumps(preferences) if isinstance(preferences, dict) else preferences

        return await user_repository["update_preferences"](user_id, preferences_data)
    except KeyError as ke:
        logger.error(f"Repository method error: {ke}")
        return False
    except json.JSONDecodeError as je:
        logger.error(f"JSON serialization error: {je}")
        return False
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        return False

async def get_user_charts(user_id: str) -> List[str]:
    """
    Get a user's saved charts.

    Args:
        user_id: User ID

    Returns:
        List of chart IDs
    """
    return await user_repository["get_user_charts"](user_id)

async def add_chart_to_user(user_id: str, chart_id: str) -> bool:
    """
    Add a chart to a user's saved charts.

    Args:
        user_id: User ID
        chart_id: Chart ID

    Returns:
        True if successful, False otherwise
    """
    return await user_repository["add_chart"](user_id, chart_id)

async def remove_chart_from_user(user_id: str, chart_id: str) -> bool:
    """
    Remove a chart from a user's saved charts.

    Args:
        user_id: User ID
        chart_id: Chart ID

    Returns:
        True if successful, False otherwise
    """
    return await user_repository["remove_chart"](user_id, chart_id)
