"""
Authentication service for Birth Time Rectifier.

This module provides functions for user authentication and session management.
"""

import logging
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, TypedDict, cast

import jwt
import bcrypt
from pydantic import BaseModel

# Setup logging
logger = logging.getLogger(__name__)

# JWT settings
JWT_SECRET = os.environ.get("JWT_SECRET", "DO_NOT_USE_THIS_KEY_IN_PRODUCTION")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60 * 24  # 24 hours

# User model
class User(TypedDict):
    id: str
    email: str
    full_name: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    preferences: Dict[str, Any]

# User creation model
class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str

# Database integration
from ai_service.database.repositories import UserRepository
user_repository = UserRepository()

def create_user(user_create: UserCreate) -> User:
    """
    Create a new user.

    Args:
        user_create: User creation model

    Returns:
        Created user

    Raises:
        ValueError: If email already exists
    """
    # Check if email exists
    if user_repository.user_exists_by_email(user_create.email):
        raise ValueError("Email already registered")

    # Generate user ID
    user_id = str(uuid.uuid4())

    # Hash password using bcrypt
    password_bytes = user_create.password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

    # Create timestamp
    now = datetime.now()

    # Create user as a dictionary (compatible with UserRepository)
    user_dict = {
        "id": user_id,
        "email": user_create.email,
        "full_name": user_create.full_name,
        "hashed_password": hashed_password,
        "created_at": now,
        "updated_at": now,
        "preferences": {}
    }

    # Store user in repository
    user_repository.store_user(user_dict)
    logger.info(f"Created user: {user_id}")

    # Return as User type
    return cast(User, user_dict)

def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.

    Args:
        email: User email
        password: User password

    Returns:
        User object if authentication successful, None otherwise
    """
    # Get user by email
    user_dict = user_repository.get_user_by_email(email)
    if not user_dict:
        return None

    # Check password with bcrypt
    password_bytes = password.encode('utf-8')
    hashed_password = user_dict["hashed_password"].encode('utf-8')

    if not bcrypt.checkpw(password_bytes, hashed_password):
        return None

    # Convert to User type and return
    return cast(User, user_dict)

def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token for the user.

    Args:
        user_id: User ID
        expires_delta: Token expiration time

    Returns:
        JWT access token
    """
    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)

    # Create token payload
    payload = {
        "sub": user_id,
        "exp": expire.timestamp(),
        "iat": datetime.utcnow().timestamp()
    }

    # Create token
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return token

def verify_token(token: str) -> Optional[str]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Extract user ID
        user_id = payload.get("sub")

        # Check if user exists
        if not user_repository.user_exists(user_id):
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
