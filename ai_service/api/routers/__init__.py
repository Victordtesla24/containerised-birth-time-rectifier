"""
API Routers Package for Birth Time Rectifier

This package consolidates all routers for the API, following the
Unified API Gateway Architecture.
"""

import logging
from fastapi import APIRouter

# Configure logging
logger = logging.getLogger(__name__)

# Create a master router
router = APIRouter()

# Import and include all router components
try:
    # Health router
    from ai_service.api.routers.health import router as health_router
    router.include_router(health_router, tags=["Health"])
    logger.info("Health router loaded successfully")
except Exception as e:
    logger.error(f"Error importing health router: {e}")

try:
    # Session router
    from ai_service.api.routers.session import router as session_router
    router.include_router(session_router, prefix="/session", tags=["Session"])
    logger.info("Session router loaded successfully")
except Exception as e:
    logger.error(f"Error importing session router: {e}")

try:
    # Geocode router
    from ai_service.api.routers.geocode import router as geocode_router
    router.include_router(geocode_router, prefix="/geocode", tags=["Geocoding"])
    logger.info("Geocode router loaded successfully")
except Exception as e:
    logger.error(f"Error importing geocode router: {e}")

try:
    # Chart router (consolidated)
    from ai_service.api.routers.consolidated_chart import router as consolidated_chart_router
    router.include_router(consolidated_chart_router, prefix="/chart", tags=["Chart"])
    logger.info("Consolidated chart router loaded successfully")
except Exception as e:
    logger.error(f"Error importing consolidated chart router: {e}")

try:
    # Questionnaire router
    from ai_service.api.routers.questionnaire import router as questionnaire_router
    router.include_router(questionnaire_router, prefix="/questionnaire", tags=["Questionnaire"])
    logger.info("Questionnaire router loaded successfully")
except Exception as e:
    logger.error(f"Error importing questionnaire router: {e}")

try:
    # AI Status router
    from ai_service.api.routers.ai_status import router as ai_status_router
    router.include_router(ai_status_router, prefix="/ai", tags=["AI Status"])
    logger.info("AI Status router loaded successfully")
except Exception as e:
    logger.error(f"Error importing AI status router: {e}")

try:
    # WebSocket router
    from ai_service.api.routers.websocket import router as websocket_router
    router.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
    logger.info("WebSocket router loaded successfully")
except Exception as e:
    logger.error(f"Error importing WebSocket router: {e}")

# Export the combined router
__all__ = ["router"]
