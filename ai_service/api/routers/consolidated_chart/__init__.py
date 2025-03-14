"""
Consolidated Chart Router Package

This package consolidates all chart-related endpoints into a single router.
It follows the API Gateway architecture and provides dual-registration
for backward compatibility.
"""

from fastapi import APIRouter

# Import all router components
from ai_service.api.routers.consolidated_chart.generate import router as generate_router
from ai_service.api.routers.consolidated_chart.compare import router as compare_router
from ai_service.api.routers.consolidated_chart.export import router as export_router
from ai_service.api.routers.consolidated_chart.rectify import router as rectify_router
from ai_service.api.routers.consolidated_chart.validate import router as validate_router

# Create the consolidated router
router = APIRouter()

# Include all the chart-related routers
# Order matters! Include routers with specific paths before those with dynamic paths
router.include_router(compare_router)  # Include compare router first to prevent path conflicts
router.include_router(export_router)
router.include_router(rectify_router)
router.include_router(validate_router)
router.include_router(generate_router)  # Include generate router last due to its dynamic {chart_id} route

# Export the router for use in the main application
__all__ = ["router"]
