"""
Questionnaire Models.

This module contains Pydantic models for questionnaire-related requests and responses.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

from . import APIResponse


class QuestionnaireRequest(BaseModel):
    """Questionnaire initialization request model."""
    session_id: str
    chart_id: Optional[str] = None
    user_id: Optional[str] = None
    language: Optional[str] = "en"


class QuestionOption(BaseModel):
    """Option for a questionnaire question."""
    id: str
    text: str
    value: Union[str, int, float, bool]
    description: Optional[str] = None


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
    """Request model for submitting an answer to a questionnaire question."""
    session_id: str
    question_id: str
    answer: Union[str, int, float, bool, List[str], Dict[str, Any]]

    @validator('answer')
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
