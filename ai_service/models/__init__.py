"""
Core Model Definitions

This module contains core model definitions for the application.
These models are used across multiple components and APIs.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator, EmailStr

# Base API models for consistent responses
class APIResponse(BaseModel):
    """Base API response model."""
    status: str = "success"
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ErrorResponse(APIResponse):
    """Error response model."""
    status: str = "error"
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

# Session models
class SessionRequest(BaseModel):
    """Session initialization request model."""
    client_id: Optional[str] = None
    version: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None

class SessionResponse(APIResponse):
    """Session initialization response model."""
    session_id: str
    token: str
    expires_at: str = Field(default_factory=lambda: (datetime.now().isoformat()))

# Questionnaire models
class QuestionOption(BaseModel):
    """Option for a questionnaire question."""
    id: str
    text: str
    value: Union[str, int, float, bool]
    description: Optional[str] = None

class QuestionnaireRequest(BaseModel):
    """Questionnaire initialization request model."""
    session_id: str
    chart_id: Optional[str] = None
    user_id: Optional[str] = None
    language: Optional[str] = "en"

class QuestionnaireResponse(APIResponse):
    """Questionnaire response model."""
    session_id: str
    question_id: str
    question_text: str
    question_type: str  # 'multiple_choice', 'date', 'text', 'boolean', etc.
    options: Optional[List[QuestionOption]] = None
    required: bool = True
    context: Optional[str] = None
    progress: Optional[float] = None  # 0.0 to 1.0
    next_question_id: Optional[str] = None
    previous_question_id: Optional[str] = None

class QuestionnaireAnswerRequest(BaseModel):
    """Request to answer a questionnaire question."""
    question_id: str = Field(..., description="ID of the question being answered")
    answer: Union[str, int, float, bool, List[str]] = Field(..., description="Answer to the question")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @validator("answer", allow_reuse=True)
    def validate_answer(cls, v):
        """Basic validation for answer format."""
        if v is None:
            raise ValueError("Answer cannot be None")
        return v

class QuestionnaireCompleteResponse(APIResponse):
    """Response model for questionnaire completion."""
    session_id: str
    completion_status: str  # 'complete', 'incomplete', 'in_progress'
    summary: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None
    rectification_id: Optional[str] = None
    confidence: Optional[float] = None  # 0.0 to 1.0

# User models
class UserCreate(BaseModel):
    """User creation model."""
    email: str = Field(..., description="User email address")
    username: str = Field(..., description="Username for display")
    password: str = Field(..., description="User password")
    full_name: Optional[str] = Field(None, description="User's full name")

    @validator("password", allow_reuse=True)
    def password_strength(cls, v):
        """Validate password strength"""
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        return v

class UserUpdate(BaseModel):
    """Model for user profile updates"""
    full_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class UserOut(BaseModel):
    """Model for user information returned to client"""
    id: str
    email: EmailStr
    full_name: str
    created_at: datetime
    updated_at: datetime
    preferences: Optional[Dict[str, Any]] = None

class Token(BaseModel):
    """Model for authentication token"""
    access_token: str
    token_type: str
    expires_at: datetime
    user_id: str

# Import specific models
from .chart import ChartRequest, ChartResponse, Planet, House, Ascendant, Aspect, ChartData, RectificationRequest, RectificationResponse, ChartComparisonRequest
from .chart_comparison import DifferenceType, PlanetaryPosition, AspectData, ChartDifference, ChartComparisonResponse
from .unified_model import UnifiedRectificationModel

# Export all models
__all__ = [
    # Base API models
    "APIResponse",
    "ErrorResponse",

    # Session models
    "SessionRequest",
    "SessionResponse",

    # Questionnaire models
    "QuestionOption",
    "QuestionnaireRequest",
    "QuestionnaireResponse",
    "QuestionnaireAnswerRequest",
    "QuestionnaireCompleteResponse",

    # User models
    "UserCreate",
    "UserUpdate",
    "UserOut",
    "Token",

    # Chart models
    "ChartRequest",
    "ChartResponse",
    "Planet",
    "House",
    "Ascendant",
    "Aspect",
    "ChartData",
    "RectificationRequest",
    "RectificationResponse",
    "ChartComparisonRequest",

    # Chart comparison models
    "DifferenceType",
    "PlanetaryPosition",
    "AspectData",
    "ChartDifference",
    "ChartComparisonResponse",

    # Unified models
    "UnifiedRectificationModel"
]
