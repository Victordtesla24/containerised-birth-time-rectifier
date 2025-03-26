"""
API package for Birth Time Rectifier API.

This package includes API routers for all endpoints including standard API and V1 API for test compatibility.
"""

# Create an API router that includes all endpoint routers
from fastapi import APIRouter

# Create a main router
router = APIRouter()

# Import and include sub-routers
from ai_service.api.routers.health import router as health_router
from ai_service.api.routers.chart import router as chart_router

# Include the standard API routers
router.include_router(health_router)
router.include_router(chart_router)

# Import V1 router for test compatibility - this can be imported directly
# from ai_service.api.v1.chart_api import v1_router

# Make selected routers available for direct import
__all__ = ["router"]
