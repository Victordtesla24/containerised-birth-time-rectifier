"""
Shared authentication utilities for Birth Time Rectifier.

This module provides common JWT authentication functionality
that can be used by both the AI service and API Gateway.
"""

import logging
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union, List

import jwt

# Configure logging
logger = logging.getLogger(__name__)

# JWT settings
JWT_SECRET = os.environ.get("JWT_SECRET", "development_secret_key")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

def create_access_token(
    user_id: str,
    expires_delta: Optional[timedelta] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to include in the token
        expires_delta: Optional custom expiration time
        additional_data: Optional additional data to include in the token

    Returns:
        JWT token string
    """
    # Set expiration time
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

    # Create payload
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    # Add additional data if provided
    if additional_data:
        for key, value in additional_data.items():
            if key not in payload:
                payload[key] = value

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

    Raises:
        jwt.PyJWTError: If token is invalid or expired
    """
    try:
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Extract user ID
        user_id = payload.get("sub")

        if not user_id:
            logger.warning("Token has no subject (sub) claim")
            return None

        return user_id
    except jwt.PyJWTError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        raise

def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token without verification.

    This is useful for debugging and should not be used for authentication.

    Args:
        token: JWT token to decode

    Returns:
        Token payload
    """
    try:
        # Decode token without verification
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
        return {"error": str(e)}

def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired.

    Args:
        token: JWT token to check

    Returns:
        True if token is expired, False otherwise
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp", 0)
        return exp < time.time()
    except Exception:
        # If we can't decode the token, consider it expired
        return True

def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token.

    Args:
        token: JWT token to check

    Returns:
        Expiration time as datetime, or None if not available
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        return datetime.fromtimestamp(exp) if exp else None
    except Exception:
        return None
