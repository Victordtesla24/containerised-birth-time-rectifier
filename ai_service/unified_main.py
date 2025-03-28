"""
Unified Main Application Entry Point for the AI Service.

This module implements the Consolidated Single-Registration Architecture with Path Rewriting
pattern as described in the API architecture documentation. It provides a single point of
registration for all API routers with proper versioning and path rewriting for backward compatibility.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from ai_service.utils.env_loader import load_env_file, get_env_with_fallback
from ai_service.app_startup import initialize_application, lifespan
from ai_service.core.config import settings

# Load environment variables
load_env_file()

# Define API prefix
API_PREFIX = "/api/v1"

# Create the FastAPI application
app = FastAPI(
    title="Birth Time Rectifier AI Service",
    description="AI service for astrological birth time rectification",
    version="1.0.0",
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json",
    lifespan=lifespan  # Use the lifespan function for proper resource management
)

# Root path handler
@app.get("/")
async def root():
    """Root endpoint that returns basic service information."""
    return {
        "service": "Birth Time Rectifier AI Service",
        "status": "running",
        "version": "1.0.0",
        "architecture": "Consolidated Single-Registration with Path Rewriting"
    }

# Health check endpoint - for direct access
@app.get("/health")
def health_check():
    """
    Health check endpoint for the application.

    Note: This endpoint should not be used directly in production.
    Health checks should be made through the ASGI wrapper for better performance.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service",
        "direct_access": True
    }

# Import and include main router with standardized prefix
from ai_service.api.routers import router
app.include_router(router, prefix=API_PREFIX)
logger.info("Main router included with prefix: %s", API_PREFIX)

# Add path rewriter middleware for legacy route support
from ai_service.api.middleware.legacy_support import PathRewriterMiddleware
app.add_middleware(PathRewriterMiddleware)

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

# Import and add session middleware
try:
    from ai_service.api.middleware.session import SimpleSessionMiddleware
    app.add_middleware(SimpleSessionMiddleware)
    logger.info("Session middleware added")

    # Create the sessions directory if it doesn't exist
    sessions_dir = os.environ.get("SESSION_DIR", "sessions")
    if not os.path.exists(sessions_dir):
        os.makedirs(sessions_dir, exist_ok=True)
        logger.info(f"Created sessions directory: {sessions_dir}")
except Exception as e:
    logger.error(f"Failed to add session middleware: {e}")

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming HTTP requests with timing information."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Add global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions across the application."""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())

    # Return a standardized error response
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc) if os.environ.get("DEBUG") == "true" else "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        }
    )

# Run startup initialization
@app.on_event("startup")
async def startup_event():
    """Run additional startup tasks."""
    await initialize_application()
    logger.info("Application startup completed")

# Only used when running this file directly
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting AI Service via unified_main.py direct execution")
    uvicorn.run(
        "ai_service.unified_main:app",
        host="0.0.0.0",
        port=8000,
        reload=False  # Disable auto-reload to prevent middleware corruption
    )
