"""
Authentication and authorization dependencies for the Birth Time Rectifier API.
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from typing import Optional

from ai_service.services.auth import verify_token
from ai_service.core.config import settings

# OAuth2 password bearer scheme for token extraction from requests
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme)
):
    """
    Dependency to get the current authenticated user.
    Raises 401 exception if the token is invalid.

    Returns:
        str: The user ID extracted from the token
    """
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id

async def get_optional_user(
    authorization: Optional[str] = Header(None)
):
    """
    Dependency to get the current user if authenticated, otherwise None.
    Does not raise an exception if the token is invalid.

    Returns:
        Optional[str]: The user ID or None if not authenticated
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")
    user_id = verify_token(token)

    return user_id
