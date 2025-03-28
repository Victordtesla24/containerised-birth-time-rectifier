"""
Chart Models.

This module contains Pydantic models for chart-related requests and responses.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator

from . import APIResponse


class ChartRequest(BaseModel):
    """Chart generation request model."""
    session_id: str
    birth_details: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None

    @validator('birth_details')
    def validate_birth_details(cls, v):
        """Validate required birth details fields."""
        required_fields = ['birth_date', 'birth_time', 'latitude', 'longitude']
        missing = [field for field in required_fields if field not in v]
        if missing:
            raise ValueError(f"Missing required birth details fields: {', '.join(missing)}")
        return v


class ChartGenerationRequest(BaseModel):
    """Chart generation request model with detailed parameters."""
    session_id: Optional[str] = None
    birth_details: Dict[str, Any]
    options: Optional[Dict[str, Any]] = None

    @validator('birth_details')
    def validate_birth_details(cls, v):
        """Validate required birth details fields."""
        required_fields = ['birth_date', 'birth_time', 'latitude', 'longitude']
        missing = [field for field in required_fields if field not in v]
        if missing:
            raise ValueError(f"Missing required birth details fields: {', '.join(missing)}")
        return v


class ValidationResponse(BaseModel):
    """Validation response model."""
    valid: bool
    errors: Optional[Dict[str, str]] = None
    warnings: Optional[Dict[str, str]] = None


class ChartResponse(APIResponse):
    """Chart generation response model."""
    chart_id: str
    status: str = "success"
    message: Optional[str] = None
    chart_data: Dict[str, Any]
    verification: Optional[Dict[str, Any]] = None  # OpenAI verification results if requested


class Planet(BaseModel):
    """Model for a planet in an astrological chart"""
    name: str
    longitude: float
    sign: str
    sign_num: int
    degree: float
    retrograde: bool = False
    house: int = 0

class House(BaseModel):
    """Model for a house in an astrological chart"""
    number: int
    sign: str
    degree: float
    cusp: float

class Ascendant(BaseModel):
    """Model for the ascendant (rising sign) in an astrological chart"""
    sign: str
    degree: float
    longitude: float

class Aspect(BaseModel):
    """Model for an aspect between planets in an astrological chart"""
    planet1: str
    planet2: str
    aspectType: str
    orb: float
    influence: str = "neutral"

class ChartData(BaseModel):
    """Model for chart data used across the API"""
    ascendant: Optional[Ascendant] = None
    planets: Optional[List[Planet]] = None
    houses: Optional[List[House]] = None
    aspects: Optional[List[Aspect]] = None
    chart_id: Optional[str] = None

class RectificationRequest(BaseModel):
    """Request model for birth time rectification"""
    birth_details: Dict[str, Any]
    chart_id: Optional[str] = None
    answers: Optional[List[Dict[str, Any]]] = None
    birth_time_range: Optional[Dict[str, str]] = None  # Optional range to search within

class RectificationResponse(BaseModel):
    """Response model for birth time rectification"""
    original_time: str
    rectified_time: Optional[str] = None
    confidence: float
    original_chart_id: Optional[str] = None
    rectified_chart_id: Optional[str] = None
    explanation: Optional[str] = None
    detected_events: Optional[List[Dict[str, Any]]] = None
    rectification_id: Optional[str] = None
    status: str = "processing"  # Can be "processing", "completed", or "error"

class ChartComparisonRequest(BaseModel):
    """Request model for chart comparison"""
    chart1_id: str
    chart2_id: str
    comparison_type: str = "differences"
    include_significance: bool = True
