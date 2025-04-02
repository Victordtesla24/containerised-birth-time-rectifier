"""
Questionnaire schemas for API validation and response models.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    """Option for multiple choice questions."""
    id: str = Field(..., description="Option ID")
    text: str = Field(..., description="Option text")


class QuestionData(BaseModel):
    """Base schema for question data."""
    id: str = Field(..., description="Question ID")
    text: str = Field(..., description="Question text")
    type: str = Field("text", description="Question type (text, multiple_choice, etc.)")
    category: str = Field("general", description="Question category")
    options: Optional[List[QuestionOption]] = Field(None, description="Options for multiple choice questions")


class QuestionnaireInitRequest(BaseModel):
    """Request model for initializing a questionnaire."""
    chart_id: Optional[str] = Field(None, description="Chart ID to use for questionnaire")
    session_id: Optional[str] = Field(None, description="Session ID if continuing an existing session")
    birth_details: Optional[Dict[str, Any]] = Field(None, description="Birth details for personalization")


class QuestionnaireInitResponse(BaseModel):
    """Response model for questionnaire initialization."""
    session_id: str = Field(..., description="Session ID for this questionnaire")
    chart_id: Optional[str] = Field(None, description="Chart ID used for this questionnaire")
    question: QuestionData = Field(..., description="First question to ask")
    confidence: float = Field(0.0, description="Initial confidence score")
    progress: float = Field(0.0, description="Initial progress percentage")


class AnswerSubmitRequest(BaseModel):
    """Request model for submitting an answer."""
    question_id: str = Field(..., description="ID of the question being answered")
    answer: Any = Field(..., description="Answer to the question")
    question_text: Optional[str] = Field(None, description="Question text for context")


class AnswerProcessResponse(BaseModel):
    """Response model after processing an answer."""
    success: bool = Field(True, description="Whether the answer was processed successfully")
    next_question: Optional[QuestionData] = Field(None, description="Next question to ask")
    confidence: float = Field(0.0, description="Updated confidence score")
    progress: float = Field(0.0, description="Updated progress percentage")
    completed: bool = Field(False, description="Whether the questionnaire is completed")
    result: Optional[Dict[str, Any]] = Field(None, description="Results if questionnaire is completed")
