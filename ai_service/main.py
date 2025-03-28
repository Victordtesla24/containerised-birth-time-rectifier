"""
Birth Time Rectifier API Main Entry Point

This module creates and configures the FastAPI application
following the Unified API Gateway Architecture.
"""

import logging
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import os

# Import the application startup and lifespan contexts
from ai_service.app_startup import lifespan, initialize_services
from ai_service.core.config import settings

# Import custom middleware
from ai_service.api.middleware.legacy_support import PathRewriterMiddleware
from ai_service.api.middleware.error_handling import validation_exception_handler, http_exception_handler

# Import all API routers
from ai_service.api.routers.consolidated_chart import router as consolidated_chart_router
from ai_service.api.routers.health import router as health_router
from ai_service.api.routers.geocode import router as geocode_router
from ai_service.api.routers.session import router as session_router
from ai_service.api.routers.questionnaire import router as questionnaire_router
from ai_service.api.routers.ai_status import router as ai_status_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ai_service")

# Create FastAPI application with lifespan context
app = FastAPI(
    title="Birth Time Rectifier API",
    description="API for astrological birth time rectification",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add legacy path rewriter middleware
app.add_middleware(PathRewriterMiddleware)

# Register error handlers
app.add_exception_handler(Exception, validation_exception_handler)
app.add_exception_handler(Exception, http_exception_handler)

# Initialize services at startup
initialize_services()

# Create the v1 API router with proper prefix
v1_router = APIRouter(prefix="/api/v1")

# Register all routers with the v1 API router
v1_router.include_router(health_router, tags=["Health"])
v1_router.include_router(session_router, prefix="/session", tags=["Session"])
v1_router.include_router(geocode_router, prefix="/geocode", tags=["Geocoding"])
v1_router.include_router(consolidated_chart_router, prefix="/chart", tags=["Chart"])
v1_router.include_router(questionnaire_router, prefix="/questionnaire", tags=["Questionnaire"])
v1_router.include_router(ai_status_router, prefix="/ai", tags=["AI Status"])

# Include the v1 router in the app
app.include_router(v1_router)

# Add root redirect
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint that redirects to documentation."""
    return {"message": "Birth Time Rectifier API. See /docs for documentation."}
