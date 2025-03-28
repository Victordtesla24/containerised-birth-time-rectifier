"""
API module for the Birth Time Rectifier application.

This module initializes the FastAPI application and registers all routers.
"""

from fastapi import APIRouter
from ai_service.api.routers import router

# Export the combined router from ai_service.api.routers
__all__ = ["router"]
