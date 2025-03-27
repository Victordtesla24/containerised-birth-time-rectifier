"""
Authentication middleware for Birth Time Rectifier API Gateway.

This module provides JWT authentication for the API Gateway.
It delegates JWT verification to the shared authentication service.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union

import jwt
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Import shared auth service from ai_service
from ai_service.services.auth import (
    verify_token as canonical_verify_token,
    create_access_token,
    JWT_SECRET,
    JWT_ALGORITHM
)

# Configure logging
logger = logging.getLogger(__name__)

def verify_token(token: str) -> str:
    """
    Verify and decode a JWT token, raising appropriate HTTP exceptions.

    This function adapts the canonical verify_token implementation to throw
    appropriate HTTP exceptions for the API gateway.

    Args:
        token: JWT token to verify

    Returns:
        User ID if token is valid

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        # Use the canonical implementation which returns None for invalid tokens
        user_id = canonical_verify_token(token)

        if not user_id:
            logger.warning("Token verification failed: invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
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

# Security scheme for Swagger docs
security = HTTPBearer(auto_error=False)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = None) -> str:
    """
    Get the current user from credentials.

    This dependency can be used in FastAPI routes to require authentication.

    Args:
        credentials: HTTPAuthorizationCredentials from security scheme

    Returns:
        User ID if authentication is successful

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = verify_token(credentials.credentials)
    return user_id

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[str]:
    """
    Get the current user from credentials if available.

    This dependency can be used in FastAPI routes where authentication is optional.

    Args:
        credentials: HTTPAuthorizationCredentials from security scheme

    Returns:
        User ID if authentication is successful, None otherwise
    """
    if not credentials:
        return None

    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None
