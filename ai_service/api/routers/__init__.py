"""API Router Collection.

This module collects all API routers and exposes them as a single router.
"""

from fastapi import APIRouter
import logging

# Create a master router
router = APIRouter(prefix="/api/v1")

# Configure logger
logger = logging.getLogger(__name__)

# Import and include individual routers
try:
    # Import health router first (most basic functionality)
    from ai_service.api.routers.health import router as health_router
    router.include_router(health_router, tags=["health"])

    # Try to import each router individually to isolate failures
    try:
        from ai_service.api.routers.chart import router as chart_router
        router.include_router(chart_router, prefix="/charts", tags=["chart"])
        logger.info("Chart router loaded successfully")
    except ImportError as chart_error:
        logger.error(f"Error importing chart router: {chart_error}")

    try:
        from ai_service.api.routers.ai_status import router as ai_status_router
        router.include_router(ai_status_router, prefix="/ai", tags=["ai"])
        logger.info("AI status router loaded successfully")
    except ImportError as ai_error:
        logger.error(f"Error importing AI status router: {ai_error}")

    try:
        from ai_service.api.routers.session import router as session_router
        router.include_router(session_router, prefix="/session", tags=["session"])
        logger.info("Session router loaded successfully")
    except ImportError as session_error:
        logger.error(f"Error importing session router: {session_error}")

    try:
        # Import from package to avoid circular dependencies
        from ai_service.api.routers.questionnaire import router as questionnaire_router
        router.include_router(questionnaire_router, prefix="/questionnaire", tags=["questionnaire"])
        logger.info("Questionnaire router loaded successfully")
    except ImportError as questionnaire_error:
        logger.error(f"Error importing questionnaire router: {questionnaire_error}")

    # Explicitly import and include the geocode router with correct prefix
    try:
        from ai_service.api.routers.geocode import router as geocode_router
        router.include_router(geocode_router, prefix="/geocode", tags=["geocoding"])
        logger.info("Geocode router loaded successfully")
    except ImportError as geocode_error:
        logger.error(f"Error importing geocode router: {geocode_error}")
        # Raise the error to ensure it's properly handled
        raise geocode_error

    try:
        from ai_service.api.routers.websocket import router as websocket_router
        router.include_router(websocket_router, tags=["websocket"])
        logger.info("WebSocket router loaded successfully")
    except ImportError as websocket_error:
        logger.error(f"Error importing WebSocket router: {websocket_error}")

except ImportError as e:
    # Log error but continue to allow application to start with limited functionality
    logger.error(f"Error importing base routers: {e}")

# Export the combined router
__all__ = ["router"]
