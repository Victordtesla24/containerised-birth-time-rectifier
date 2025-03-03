"""
Health check router for the Birth Time Rectifier API.
Handles all health check related endpoints.
"""

from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from datetime import datetime
import platform
import psutil

# Create router
router = APIRouter(
    prefix="/health",
    tags=["Health"],
    responses={404: {"description": "Not found"}},
)

@router.get("")
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Birth Time Rectifier API",
    }

@router.get("/details")
async def health_details():
    """
    Detailed health check with system information.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Birth Time Rectifier API",
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
        }
    }

@router.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Root health endpoint is defined in main.py to ensure it's available at the root level
