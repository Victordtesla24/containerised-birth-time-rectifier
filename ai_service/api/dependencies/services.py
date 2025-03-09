"""
Service dependencies for the Birth Time Rectifier API.
Provides dependency injection for service components.
"""

from typing import Optional
import logging

# Import services
from ai_service.api.middleware.session import get_redis_client, SESSION_TTL
from ai_service.services.auth import (
    create_access_token, verify_token, JWT_SECRET,
    JWT_ALGORITHM, JWT_EXPIRATION_MINUTES
)
from ai_service.core.config import settings

# Setup logging
logger = logging.getLogger("birth-time-rectifier.dependencies")

# Session service
class SessionService:
    """Session management service"""
    def __init__(self):
        self.redis_client = get_redis_client()
        self.ttl = SESSION_TTL

def get_session_service():
    """Dependency for session service"""
    return SessionService()

# Auth service adapter
class AuthService:
    """Authentication service adapter"""
    def __init__(self, secret_key=None, algorithm=None, token_expiry=None):
        self.secret_key = secret_key or JWT_SECRET
        self.algorithm = algorithm or JWT_ALGORITHM
        self.token_expiry = token_expiry or (JWT_EXPIRATION_MINUTES * 60)

    def create_token(self, user_id):
        """Create an access token"""
        from datetime import timedelta
        return create_access_token(
            user_id,
            timedelta(seconds=self.token_expiry)
        )

    def verify_token(self, token):
        """Verify a token and return the user ID"""
        return verify_token(token)

def get_auth_service():
    """Dependency for authentication service"""
    return AuthService(
        secret_key=settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        token_expiry=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

# Chart service
def get_chart_service():
    """Dependency for chart generation service"""
    # Import lazily to avoid circular imports
    from ai_service.services.chart_service import ChartService

    # Use a singleton pattern to ensure the same instance is used across requests
    if not hasattr(get_chart_service, "_instance"):
        get_chart_service._instance = ChartService()

    return get_chart_service._instance

# Rectification service
def get_rectification_service():
    """Dependency for birth time rectification service"""
    # This would normally be imported from a proper service
    # For now, we'll return a placeholder
    class RectificationService:
        pass
    return RectificationService()

# Interpretation service
def get_interpretation_service():
    """Dependency for chart interpretation service"""
    # This would normally be imported from a proper service
    # For now, we'll return a placeholder
    class InterpretationService:
        pass
    return InterpretationService()
