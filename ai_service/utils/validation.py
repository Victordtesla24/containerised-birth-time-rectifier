"""
Shared validation utilities for Birth Time Rectifier application.

This module provides common validation models and functions that can be
used across both the AI service and API Gateway to ensure consistent validation.
"""

import logging
import re
from datetime import datetime, date, time
from typing import Dict, Any, Optional, List, Union, Tuple
from enum import Enum

from pydantic import BaseModel, Field, validator, root_validator, constr, confloat

# Configure logging
logger = logging.getLogger(__name__)

# Constants for validation
MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0
DATE_REGEX = r"^\d{4}-\d{2}-\d{2}$"
TIME_REGEX = r"^\d{2}:\d{2}(:\d{2})?$"

# Enums for validation
class ZodiacType(str, Enum):
    """Zodiac type enum."""
    TROPICAL = "tropical"
    SIDEREAL = "sidereal"

class HouseSystem(str, Enum):
    """House system enum."""
    PLACIDUS = "placidus"
    KOCH = "koch"
    EQUAL = "equal"
    WHOLE_SIGN = "whole_sign"
    REGIOMONTANUS = "regiomontanus"
    CAMPANUS = "campanus"
    ALCABITIUS = "alcabitius"
    PORPHYRY = "porphyry"

    # API format mappings
    P = "placidus"
    K = "koch"
    E = "equal"
    W = "whole_sign"
    R = "regiomontanus"
    C = "campanus"
    A = "alcabitius"
    B = "equal"  # Bharatiya Jyotish uses equal houses

class NodeType(str, Enum):
    """Node type enum."""
    TRUE = "true"
    MEAN = "mean"

class ChartType(str, Enum):
    """Chart type enum."""
    BIRTH = "birth"
    TRANSIT = "transit"
    PROGRESSION = "progression"
    SOLAR_RETURN = "solar_return"
    LUNAR_RETURN = "lunar_return"

# Base coordinate models
class Coordinates(BaseModel):
    """Geographic coordinates model."""
    latitude: float = Field(..., ge=MIN_LATITUDE, le=MAX_LATITUDE, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=MIN_LONGITUDE, le=MAX_LONGITUDE, description="Longitude in decimal degrees")

    @validator("latitude")
    def validate_latitude(cls, v: float) -> float:
        """Validate latitude."""
        if v < MIN_LATITUDE or v > MAX_LATITUDE:
            raise ValueError(f"Latitude must be between {MIN_LATITUDE} and {MAX_LATITUDE}")
        return round(v, 6)

    @validator("longitude")
    def validate_longitude(cls, v: float) -> float:
        """Validate longitude."""
        if v < MIN_LONGITUDE or v > MAX_LONGITUDE:
            raise ValueError(f"Longitude must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}")
        return round(v, 6)

class Location(BaseModel):
    """Location model with coordinates and description."""
    coordinates: Coordinates
    name: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None

# Birth details models
class BirthDateTime(BaseModel):
    """Birth date and time model."""
    date: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    time: str = Field(..., description="Time of birth in HH:MM:SS format")

    @validator("date")
    def validate_date(cls, v: str) -> str:
        """Validate date format."""
        if not re.match(DATE_REGEX, v):
            raise ValueError("Date must be in YYYY-MM-DD format")
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Invalid date")

    @validator("time")
    def validate_time(cls, v: str) -> str:
        """Validate time format."""
        if not re.match(TIME_REGEX, v):
            raise ValueError("Time must be in HH:MM:SS or HH:MM format")

        # Add seconds if needed
        if len(v.split(":")) == 2:
            v = f"{v}:00"

        try:
            time.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Invalid time")

class BirthDetails(BaseModel):
    """Complete birth details model."""
    date_time: BirthDateTime
    location: Location

# Chart calculation models
class ChartCalculationRequest(BaseModel):
    """Request model for chart calculation."""
    birth_date: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    birth_time: str = Field(..., description="Time of birth in HH:MM:SS format")
    latitude: float = Field(..., ge=MIN_LATITUDE, le=MAX_LATITUDE, description="Birth latitude")
    longitude: float = Field(..., ge=MIN_LONGITUDE, le=MAX_LONGITUDE, description="Birth longitude")
    timezone: str = Field(..., description="IANA timezone identifier")
    location: Optional[str] = Field(None, description="Birth location name")
    house_system: str = Field("placidus", description="House system to use")
    zodiac_type: ZodiacType = Field(ZodiacType.SIDEREAL, description="Zodiac type")
    ayanamsa: Optional[float] = Field(None, description="Ayanamsa value for sidereal calculations")
    verify_with_openai: bool = Field(False, description="Whether to verify chart with OpenAI")
    node_type: NodeType = Field(NodeType.TRUE, description="Node type")
    chart_id: Optional[str] = Field(None, description="Optional chart ID to use")

    @validator("house_system")
    def validate_house_system(cls, v: str) -> str:
        """Validate and normalize house system."""
        # Handle both API format (single letter) and full names
        if len(v) == 1 and v.upper() in HouseSystem.__members__:
            return HouseSystem[v.upper()].value

        # Convert to lowercase for case-insensitive comparison
        v_lower = v.lower()

        # Check against enum values
        for system in HouseSystem:
            if v_lower == system.value:
                return system.value

        # Not found, raise error
        valid_systems = ", ".join([s.value for s in HouseSystem])
        raise ValueError(f"Invalid house system. Valid options: {valid_systems}")

    @validator("birth_date")
    def validate_birth_date(cls, v: str) -> str:
        """Validate birth date."""
        if not re.match(DATE_REGEX, v):
            raise ValueError("Birth date must be in YYYY-MM-DD format")
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Invalid birth date")

    @validator("birth_time")
    def validate_birth_time(cls, v: str) -> str:
        """Validate birth time."""
        if not re.match(TIME_REGEX, v):
            raise ValueError("Birth time must be in HH:MM:SS or HH:MM format")

        # Add seconds if needed
        if len(v.split(":")) == 2:
            v = f"{v}:00"

        try:
            time.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError("Invalid birth time")

    @validator("timezone")
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone."""
        # Simple validation for now
        if not v or len(v) < 2:
            raise ValueError("Invalid timezone")
        return v

class ChartQueryRequest(BaseModel):
    """Request model for chart lookup."""
    chart_id: str = Field(..., description="Chart ID to lookup")

# User models
class UserBase(BaseModel):
    """Base user model."""
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")

class UserLogin(BaseModel):
    """User login model."""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")

class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., description="User password")

class UserResponse(UserBase):
    """User response model."""
    id: str = Field(..., description="User ID")
    created_at: str = Field(..., description="User creation timestamp")
    updated_at: str = Field(..., description="User last update timestamp")

# Validation functions
def validate_coordinates(latitude: float, longitude: float) -> Tuple[float, float]:
    """
    Validate latitude and longitude.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees

    Returns:
        Tuple of validated latitude and longitude

    Raises:
        ValueError: If coordinates are invalid
    """
    if latitude < MIN_LATITUDE or latitude > MAX_LATITUDE:
        raise ValueError(f"Latitude must be between {MIN_LATITUDE} and {MAX_LATITUDE}")

    if longitude < MIN_LONGITUDE or longitude > MAX_LONGITUDE:
        raise ValueError(f"Longitude must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}")

    return round(latitude, 6), round(longitude, 6)

def validate_date_string(date_str: str) -> str:
    """
    Validate a date string.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Validated date string

    Raises:
        ValueError: If date is invalid
    """
    if not re.match(DATE_REGEX, date_str):
        raise ValueError("Date must be in YYYY-MM-DD format")

    try:
        date.fromisoformat(date_str)
        return date_str
    except ValueError:
        raise ValueError("Invalid date")

def validate_time_string(time_str: str) -> str:
    """
    Validate a time string.

    Args:
        time_str: Time string in HH:MM:SS or HH:MM format

    Returns:
        Validated time string with seconds

    Raises:
        ValueError: If time is invalid
    """
    if not re.match(TIME_REGEX, time_str):
        raise ValueError("Time must be in HH:MM:SS or HH:MM format")

    # Add seconds if needed
    if len(time_str.split(":")) == 2:
        time_str = f"{time_str}:00"

    try:
        time.fromisoformat(time_str)
        return time_str
    except ValueError:
        raise ValueError("Invalid time")

def normalize_house_system(house_system: str) -> str:
    """
    Normalize house system identifier.

    Args:
        house_system: House system identifier

    Returns:
        Normalized house system name

    Raises:
        ValueError: If house system is invalid
    """
    # Handle both API format (single letter) and full names
    if len(house_system) == 1 and house_system.upper() in HouseSystem.__members__:
        return HouseSystem[house_system.upper()].value

    # Convert to lowercase for case-insensitive comparison
    house_system_lower = house_system.lower()

    # Check against enum values
    for system in HouseSystem:
        if house_system_lower == system.value:
            return system.value

    # Not found, raise error
    valid_systems = ", ".join([s.value for s in HouseSystem])
    raise ValueError(f"Invalid house system. Valid options: {valid_systems}")

def normalize_coordinates(latitude: float, longitude: float) -> Tuple[float, float]:
    """
    Normalize coordinates by rounding to 6 decimal places.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees

    Returns:
        Tuple of normalized latitude and longitude
    """
    return round(latitude, 6), round(longitude, 6)
