"""
Package for API routers.

This module contains FastAPI router modules for the API endpoints.
"""

from fastapi import APIRouter
from . import geocoding
from . import geocode
from . import chart
from . import validate
from . import rectify
from . import export
from . import health
from . import questionnaire

# Initialize the main router
router = APIRouter(prefix="/api")

# Include all sub-routers
router.include_router(geocoding.router)
router.include_router(geocode.router, prefix="/v1/geocode", tags=["Geocoding"])
router.include_router(chart.router, prefix="/v1/chart", tags=["Chart"])
router.include_router(validate.router, prefix="/v1/chart/validate", tags=["Validation"])
router.include_router(rectify.router, prefix="/v1/chart/rectify", tags=["Rectification"])
router.include_router(export.router, prefix="/v1/chart/export", tags=["Export"])
router.include_router(health.router, prefix="/v1/health", tags=["Health"])
router.include_router(questionnaire.router, prefix="/v1/questionnaire", tags=["Questionnaire"])

# Export the combined router
__all__ = ["router"]
