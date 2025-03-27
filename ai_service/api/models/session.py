"""
Session Models.

This module contains Pydantic models for session-related requests and responses.
"""

from typing import Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from . import APIResponse


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
