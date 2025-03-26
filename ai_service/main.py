"""
Main application entry point for the AI Service.

This module initializes the FastAPI application and includes routers.
Following the Consolidated Single-Registration Architecture with Path Rewriting.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Tuple, Type, Callable, Optional
from datetime import datetime
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Local imports
from ai_service.utils.env_loader import load_env_file
from ai_service.app_startup import initialize_application, lifespan

# Load environment variables
load_env_file()

# Initialize a clean FastAPI application
app = FastAPI(
    title="Birth Time Rectifier AI Service",
    description="AI service for astrological birth time rectification",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan  # Use the lifespan function for proper resource management
)

# Root path handler
@app.get("/")
async def root():
    return {
        "service": "Birth Time Rectifier AI Service",
        "status": "running",
        "version": "0.1.0"
    }

# Add a direct health endpoint for the healthcheck
# This endpoint is not used by the wrapper but kept for compatibility
@app.get("/health")
def health_check():
    """Check the health of the application directly.

    Note: This endpoint should not be used directly. Health checks should be made through the ASGI wrapper.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service",
        "direct_access": True
    }

# Run startup initialization
@app.on_event("startup")
async def startup_event():
    """Run additional startup tasks."""
    await initialize_application()

# Include routers
from ai_service.api.routers import router
app.include_router(router)

# Import API routers
try:
    from ai_service.api.routers.health import router as health_router
    app.include_router(health_router)
    logger.info("Health router included")
except ImportError:
    logger.warning("Health router not found")

try:
    from ai_service.api.routers.chart import router as chart_router
    app.include_router(chart_router, prefix="/api")
    logger.info("Chart router included")
except ImportError:
    logger.warning("Chart router not found")

# Import V1 API router for tests
try:
    from ai_service.api.v1.chart_api import v1_router as chart_v1_router
    app.include_router(chart_v1_router)  # No prefix as it already has /api/v1
    logger.info("V1 Chart API router included - for tests")
except ImportError:
    logger.warning("V1 Chart API router not found - tests may fail")

# Define CORS settings
cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and add path rewriter middleware
from ai_service.api.middleware.legacy_support import PathRewriterMiddleware
app.add_middleware(PathRewriterMiddleware)

# Import and add session middleware
from ai_service.api.middleware.session import session_middleware
app.add_middleware(session_middleware)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())

    # Return a generic error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if os.environ.get("DEBUG") == "true" else "An unexpected error occurred"
        }
    )

# This will only be invoked if running this file directly
if __name__ == "__main__":
    import uvicorn
    # Note: In production, the app_wrapper ASGI function is used as the entry point
    # which provides health check endpoints that bypass middleware
    uvicorn.run(
        "ai_service.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False  # Disable auto-reload to prevent middleware corruption
    )
