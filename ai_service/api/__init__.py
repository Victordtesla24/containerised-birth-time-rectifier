"""
API module for the Birth Time Rectifier application.

This module initializes the FastAPI application and registers all routers.
"""

from fastapi import APIRouter
from ai_service.api.routers import (
    chart,
    geocode,
    session
)

# Create main router
router = APIRouter()

# Register routers
router.include_router(chart.router, prefix="/v1/charts", tags=["charts"])
router.include_router(geocode.router, prefix="/v1/geocode", tags=["geocoding"])
router.include_router(session.router, prefix="/v1/session", tags=["session"])

__all__ = ["router"]
