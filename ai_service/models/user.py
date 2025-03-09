"""
User models for Birth Time Rectifier API.
Handles user data structures and validation.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, EmailStr, Field, field_validator

class UserCreate(BaseModel):
    """Model for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)

    @field_validator('password', mode='after')
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

class User:
    """User model for internal use"""
    def __init__(self, id: str, email: str, full_name: str,
                 hashed_password: str, created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None, preferences: Optional[Dict[str, Any]] = None):
        self.id = id
        self.email = email
        self.full_name = full_name
        self.hashed_password = hashed_password
        self.created_at = created_at if created_at is not None else datetime.now()
        self.updated_at = updated_at if updated_at is not None else datetime.now()
        self.preferences = preferences if preferences is not None else {}
        self.saved_charts = []
