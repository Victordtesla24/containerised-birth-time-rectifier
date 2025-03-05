"""
Authentication service for Birth Time Rectifier API.
Handles user management, authentication, and authorization.
"""

import logging
import time
import jwt
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

from ai_service.models.user import User, UserCreate, UserUpdate, Token

# Configure logging
logger = logging.getLogger(__name__)

# Mock database for users
# In a real implementation, this would be a database connection
_users_db = {}
_user_emails = {}
_user_charts = {}

# JWT configuration
JWT_SECRET = "dev_secret_key"  # In production, use a secure environment variable
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 30

def create_user(user_create: UserCreate) -> User:
    """
    Create a new user.

    Args:
        user_create: User creation data

    Returns:
        Created user object

    Raises:
        ValueError: If email is already taken
    """
    # Check if email exists
    if user_create.email in _user_emails:
        raise ValueError("Email already registered")

    # Generate user ID
    user_id = str(uuid.uuid4())

    # Hash password - in a real implementation, use a secure hashing algorithm
    # For the mock, we'll just add a prefix to simulate hashing
    hashed_password = f"hashed_{user_create.password}"

    # Create timestamp
    now = datetime.now()

    # Create user
    user = User(
        id=user_id,
        email=user_create.email,
        full_name=user_create.full_name,
        hashed_password=hashed_password,
        created_at=now,
        updated_at=now,
        preferences={}
    )

    # Store user
    _users_db[user_id] = user
    _user_emails[user_create.email] = user_id
    _user_charts[user_id] = []

    logger.info(f"Created user: {user_id}")

    return user

def authenticate_user(email: str, password: str) -> Optional[User]:
    """
    Authenticate a user by email and password.

    Args:
        email: User email
        password: User password

    Returns:
        User object if authentication successful, None otherwise
    """
    # Check if email exists
    if email not in _user_emails:
        return None

    # Get user ID
    user_id = _user_emails[email]

    # Get user
    user = _users_db[user_id]

    # Check password - in a real implementation, verify hash
    # For the mock, just compare with our simulated hash
    expected_hash = f"hashed_{password}"

    if user.hashed_password != expected_hash:
        return None

    return user

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
        if user_id not in _users_db:
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
    return _users_db.get(user_id)

def convert_to_user_out(user: User) -> Dict[str, Any]:
    """
    Convert a User object to a UserOut model.

    Args:
        user: User object

    Returns:
        Dictionary representation of UserOut
    """
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "preferences": user.preferences
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
    # Check if user exists
    if user_id not in _users_db:
        return False

    # Get user
    user = _users_db[user_id]

    # Update preferences
    user.preferences.update(preferences)

    # Update timestamp
    user.updated_at = datetime.now()

    return True

def get_user_charts(user_id: str) -> List[str]:
    """
    Get a user's saved charts.

    Args:
        user_id: User ID

    Returns:
        List of chart IDs
    """
    # Check if user exists
    if user_id not in _user_charts:
        return []

    return _user_charts[user_id]

def add_chart_to_user(user_id: str, chart_id: str) -> bool:
    """
    Add a chart to a user's saved charts.

    Args:
        user_id: User ID
        chart_id: Chart ID

    Returns:
        True if successful, False otherwise
    """
    # Check if user exists
    if user_id not in _user_charts:
        return False

    # Check if chart already saved
    if chart_id in _user_charts[user_id]:
        return True

    # Add chart
    _user_charts[user_id].append(chart_id)

    return True

def remove_chart_from_user(user_id: str, chart_id: str) -> bool:
    """
    Remove a chart from a user's saved charts.

    Args:
        user_id: User ID
        chart_id: Chart ID

    Returns:
        True if successful, False otherwise
    """
    # Check if user exists
    if user_id not in _user_charts:
        return False

    # Check if chart exists
    if chart_id not in _user_charts[user_id]:
        return False

    # Remove chart
    _user_charts[user_id].remove(chart_id)

    return True
