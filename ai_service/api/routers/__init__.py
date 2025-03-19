"""
API Router Collection.

This module collects all API routers and exposes them as a single router.
"""

from fastapi import APIRouter

# Create a master router
router = APIRouter(prefix="/api/v1")

# Import and include individual routers
try:
    # Import all routers
    from ai_service.api.routers.health import router as health_router
    from ai_service.api.routers.chart import router as chart_router
    from ai_service.api.routers.ai_status import router as ai_status_router
    from ai_service.api.routers.session import router as session_router
    from ai_service.api.routers.questionnaire import router as questionnaire_router
    from ai_service.api.routers.geocode import router as geocode_router

    # Include routers with appropriate prefixes and tags
    router.include_router(health_router, tags=["health"])
    router.include_router(chart_router, prefix="/chart", tags=["chart"])
    router.include_router(ai_status_router, prefix="/ai", tags=["ai"])
    router.include_router(session_router, prefix="/session", tags=["session"])
    router.include_router(questionnaire_router, prefix="/questionnaire", tags=["questionnaire"])
    router.include_router(geocode_router, prefix="/geocode", tags=["geocoding"])

    # Additional routers would be included here

except ImportError as e:
    # Log error but continue to allow application to start with limited functionality
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing routers: {e}")

# Export the combined router
__all__ = ["router"]
