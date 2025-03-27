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
    birth_date: str  # Format: YYYY-MM-DD
    birth_time: str  # Format: HH:MM:SS
    latitude: float
    longitude: float
    location_name: Optional[str] = None
    timezone: Optional[str] = None  # IANA timezone name, e.g., "America/New_York"
    verify_with_openai: bool = True

    @validator('birth_date')
    def validate_birth_date(cls, v):
        """Validate birth date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('birth_date must be in YYYY-MM-DD format')

    @validator('birth_time')
    def validate_birth_time(cls, v):
        """Validate birth time format."""
        try:
            datetime.strptime(v, '%H:%M:%S')
            return v
        except ValueError:
            raise ValueError('birth_time must be in HH:MM:SS format')


class ChartResponse(APIResponse):
    """Chart generation response model."""
    chart_id: str
    birth_details: Dict[str, Any]
    planets: Dict[str, Any]
    houses: Dict[str, Any]
    aspects: List[Dict[str, Any]]
    ascendant: Dict[str, Any]
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
    birthDetails: Dict[str, Any]
    questionnaire: Dict[str, Any]

class RectificationResponse(BaseModel):
    """Response model for birth time rectification"""
    originalTime: str
    rectifiedTime: str
    confidence: float
    chart: Dict[str, Any]

class ChartComparisonRequest(BaseModel):
    """Request model for chart comparison"""
    chart1_id: str
    chart2_id: str
    comparison_type: str = "differences"
    include_significance: bool = True
