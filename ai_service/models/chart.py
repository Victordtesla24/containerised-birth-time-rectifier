"""
Chart Models

This module defines all Pydantic models for chart data, requests, and responses.
These models are used across the API for validation, serialization, and documentation.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ChartOptions(BaseModel):
    """Options for chart generation and calculation"""
    house_system: str = "P"
    zodiac_type: str = "sidereal"
    ayanamsa: str = "lahiri"

class ChartRequest(BaseModel):
    """Primary request model for chart generation"""
    birth_date: str
    birth_time: str
    latitude: float
    longitude: float
    timezone: str
    options: Optional[ChartOptions] = None

class ChartRequestAlt(BaseModel):
    """Alternative request model for backward compatibility"""
    birthDate: str
    birthTime: str
    latitude: float
    longitude: float
    timezone: str

class ChartRequestSimple(BaseModel):
    """Simple request model for maximum backward compatibility"""
    date: str
    time: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    timezone: Optional[str] = None
    tz: Optional[str] = None
    location: Optional[str] = None

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

class ChartResponse(BaseModel):
    """Response model for chart generation endpoints"""
    chart_id: str
    ascendant: Ascendant
    planets: List[Planet]
    houses: List[House]
    aspects: Optional[List[Aspect]] = None
    d1Chart: Optional[Dict[str, Any]] = None

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
