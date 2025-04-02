"""
Package for API routers.

This module contains FastAPI router modules for the API endpoints.
"""

from fastapi import APIRouter
from . import geocode
from . import chart
from . import validate
from . import rectify
from . import export
from . import health
from . import questionnaire
from . import session
from . import websocket

# Initialize the main router without prefix to avoid double prefixing
# The prefix will be added in unified_main.py
router = APIRouter()

# Include all sub-routers without the v1/ prefix since it's already added in unified_main.py
router.include_router(geocode.router, prefix="/geocode", tags=["Geocoding"])
router.include_router(chart.router, prefix="/chart", tags=["Chart"])
router.include_router(validate.router, prefix="/chart/validate", tags=["Validation"])
router.include_router(rectify.router, prefix="/chart/rectify", tags=["Rectification"])
router.include_router(export.router, prefix="/chart/export", tags=["Export"])
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(questionnaire.router, prefix="/questionnaire", tags=["Questionnaire"])
router.include_router(session.router, prefix="/session", tags=["Session"])
# The websocket router already has a /ws prefix in the router definition
router.include_router(websocket.router, tags=["WebSocket"])

# Export the combined router
__all__ = ["router"]
