"""
Consolidated Chart Router Package.

This package provides a unified chart router that combines all chart-related endpoints
including chart generation, validation, rectification, and export functionality.
Following the Unified API Gateway architecture with standardized prefix handling.
"""

from fastapi import APIRouter
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Create a master router
router = APIRouter()

# Import and include individual chart routers
try:
    # Import chart router
    from ai_service.api.routers.chart import router as chart_router
    router.include_router(chart_router, tags=["Chart"])
    logger.info("Chart router loaded successfully")
except Exception as e:
    logger.error(f"Error importing chart router: {e}")

try:
    # Import validate router
    from ai_service.api.routers.validate import router as validate_router
    router.include_router(validate_router, prefix="/validate", tags=["Validation"])
    logger.info("Validation router loaded successfully")
except Exception as e:
    logger.error(f"Error importing validation router: {e}")

try:
    # Import rectify router
    from ai_service.api.routers.rectify import router as rectify_router
    router.include_router(rectify_router, prefix="/rectify", tags=["Rectification"])
    logger.info("Rectification router loaded successfully")
except Exception as e:
    logger.error(f"Error importing rectification router: {e}")

try:
    # Import export router
    from ai_service.api.routers.export import router as export_router
    router.include_router(export_router, prefix="/export", tags=["Export"])
    logger.info("Export router loaded successfully")
except Exception as e:
    logger.error(f"Error importing export router: {e}")

# Export the combined router
__all__ = ["router"]
