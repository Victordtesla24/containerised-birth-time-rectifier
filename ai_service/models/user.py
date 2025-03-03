"""
User model for authentication and profile management.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


class UserBase(BaseModel):
    """Base user model with common fields."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation model with password."""
    password: str = Field(..., min_length=8)


class UserInDB(UserBase):
    """User model as stored in the database."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True
    is_verified: bool = False
    preferences: Dict[str, Any] = Field(default_factory=dict)
    saved_charts: List[str] = Field(default_factory=list)


class UserOut(UserBase):
    """User model for API responses."""
    id: str
    created_at: datetime
    preferences: Dict[str, Any]
    saved_charts: List[str]


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """User update model."""
    full_name: Optional[str] = None
    password: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class Token(BaseModel):
    """Token model for authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_id: str


class TokenData(BaseModel):
    """Token data for JWT payload."""
    user_id: str
    exp: datetime
