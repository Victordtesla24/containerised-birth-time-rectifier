"""
Authentication service for the Birth Time Rectifier API.
Handles user authentication, token generation and verification.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import jwt
import bcrypt
import os
from pydantic import EmailStr
import uuid
import json
import logging

from ai_service.models.user import UserInDB, UserCreate, UserOut, TokenData

# Configure logging
logger = logging.getLogger(__name__)

# Configure bcrypt
SALT_ROUNDS = 12

# JWT settings
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "insecure-development-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Mock database for development
# In production, this would be replaced with a real database
USERS_DB: Dict[str, UserInDB] = {}
USERS_EMAIL_INDEX: Dict[str, str] = {}  # Email to user_id mapping


def get_password_hash(password: str) -> str:
    """Generate a password hash using bcrypt."""
    salt = bcrypt.gensalt(rounds=SALT_ROUNDS)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using bcrypt."""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_user_by_email(email: str) -> Optional[UserInDB]:
    """Get a user by email address."""
    user_id = USERS_EMAIL_INDEX.get(email.lower())
    if user_id:
        return USERS_DB.get(user_id)
    return None


def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Get a user by ID."""
    return USERS_DB.get(user_id)


def create_user(user_create: UserCreate) -> UserInDB:
    """Create a new user."""
    # Check if email already exists
    if get_user_by_email(user_create.email):
        raise ValueError(f"User with email {user_create.email} already exists")

    # Create user with hashed password
    user_dict = user_create.dict()
    hashed_password = get_password_hash(user_dict.pop("password"))

    user_in_db = UserInDB(
        **user_dict,
        hashed_password=hashed_password
    )

    # Add to mock DB
    USERS_DB[user_in_db.id] = user_in_db
    USERS_EMAIL_INDEX[user_in_db.email.lower()] = user_in_db.id

    return user_in_db


def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user with email and password."""
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = TokenData(user_id=user_id, exp=expire)
    encoded_jwt = jwt.encode(to_encode.dict(), SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the user ID if valid."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenData(**payload)

        # Check if token is expired
        if datetime.utcnow() > token_data.exp:
            return None

        # Check if user exists
        if not get_user_by_id(token_data.user_id):
            return None

        return token_data.user_id
    except jwt.PyJWTError:
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


def add_chart_to_user(user_id: str, chart_id: str) -> bool:
    """Add a chart to a user's saved charts."""
    user = get_user_by_id(user_id)
    if not user:
        return False

    if chart_id not in user.saved_charts:
        user.saved_charts.append(chart_id)
        user.updated_at = datetime.now()
        USERS_DB[user_id] = user

    return True


def remove_chart_from_user(user_id: str, chart_id: str) -> bool:
    """Remove a chart from a user's saved charts."""
    user = get_user_by_id(user_id)
    if not user:
        return False

    if chart_id in user.saved_charts:
        user.saved_charts.remove(chart_id)
        user.updated_at = datetime.now()
        USERS_DB[user_id] = user

    return True


def get_user_charts(user_id: str) -> List[str]:
    """Get all chart IDs saved by a user."""
    user = get_user_by_id(user_id)
    if not user:
        return []

    return user.saved_charts.copy()


def update_user_preferences(user_id: str, preferences: Dict[str, Any]) -> bool:
    """Update a user's preferences."""
    user = get_user_by_id(user_id)
    if not user:
        return False

    # Update preferences
    for key, value in preferences.items():
        user.preferences[key] = value

    user.updated_at = datetime.now()
    USERS_DB[user_id] = user

    return True


def convert_to_user_out(user: UserInDB) -> UserOut:
    """Convert an internal user model to the external response model."""
    return UserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        created_at=user.created_at,
        preferences=user.preferences,
        saved_charts=user.saved_charts
    )
