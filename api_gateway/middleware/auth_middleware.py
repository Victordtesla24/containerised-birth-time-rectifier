"""
Authentication middleware for API Gateway.

This module provides utilities for JWT token verification and authentication.
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException, status, Request

# Configure logging
logger = logging.getLogger(__name__)

# JWT settings
JWT_SECRET = os.environ.get("JWT_SECRET", "insecure_jwt_secret_key_replace_in_production")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))  # 12 hours by default

def verify_token(token: str) -> Optional[str]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        User ID if token is valid

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Decode token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Extract user ID
        user_id = payload.get("sub")

        if not user_id:
            logger.warning("Token verification failed: missing sub claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.now():
            logger.warning(f"Token expired for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_id

    except jwt.PyJWTError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def authenticate_request(request: Request) -> Optional[str]:
    """
    Authenticate a request using the Authorization header.

    Args:
        request: FastAPI Request object

    Returns:
        User ID if authentication is successful, None otherwise
    """
    # Get Authorization header
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return None

    # Check for Bearer token
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    try:
        return verify_token(token)
    except HTTPException:
        return None
