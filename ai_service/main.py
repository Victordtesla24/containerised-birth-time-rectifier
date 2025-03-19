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
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Local imports
from ai_service.utils.env_loader import load_env_file
from ai_service.app_startup import initialize_application

# Load environment variables
load_env_file()

# Initialize a clean FastAPI application
app = FastAPI(
    title="Birth Time Rectifier AI Service",
    description="AI service for astrological birth time rectification",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Root path handler
@app.get("/")
async def root():
    return {"message": "Welcome to Birth Time Rectifier AI Service", "version": "1.0.0"}

# Add a direct health endpoint for the healthcheck
# This endpoint is not used by the wrapper but kept for compatibility
@app.get("/health")
async def health_check():
    """
    Simple health check endpoint for the healthcheck mechanism.
    Note: This is a fallback. Health checks should go through the ASGI wrapper.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service",
        "wrapper_bypassed": True
    }

# Initialize app on startup
@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting AI Service application")
        initialize_application()
        logger.info("AI Service initialized successfully")
    except Exception as e:
        logger.critical(f"Failed to initialize application: {e}")
        # Log the full error trace
        import traceback
        logger.critical(traceback.format_exc())

# Include routers
from ai_service.api.routers import router
app.include_router(router)

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

# Error handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    # Log detailed error trace
    import traceback
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)},
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
