"""
API Models.

This module contains Pydantic models for API requests and responses.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field

# Base models
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

# Include commonly used models
from .session import *
from .chart import *

# Define fallback imports in case files don't exist yet
try:
    from .questionnaire import *
except ImportError:
    # Create placeholder models until actual implementation
    class QuestionnaireRequest(BaseModel):
        """Placeholder for questionnaire request."""
        session_id: str

    class QuestionnaireResponse(APIResponse):
        """Placeholder for questionnaire response."""
        question_id: str = "placeholder"
        question_text: str = "Placeholder question"
        options: List[str] = []
