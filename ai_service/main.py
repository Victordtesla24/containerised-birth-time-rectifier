"""
Birth Time Rectifier API - Unified Main Application

This is the consolidated FastAPI application that serves the Birth Time Rectifier API
using a single registration pattern with proper versioning.
"""

from fastapi import FastAPI, Request, APIRouter, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
import logging
import time
from datetime import datetime
import os
import uuid
import json
import tempfile
from contextlib import asynccontextmanager
from typing import cast, Any, Callable

try:
    from prometheus_client import Counter, Histogram, Gauge
except ImportError:
    # Allow execution without Prometheus for development
    print("Warning: Prometheus client not installed, metrics will be disabled")
    Counter = lambda *args, **kwargs: None
    Histogram = lambda *args, **kwargs: None
    Gauge = lambda *args, **kwargs: None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=os.path.join("logs", "ai_service.log") if os.path.exists("logs") else None,
)
logger = logging.getLogger("birth-time-rectifier")

# Import middleware
from ai_service.api.middleware.error_handling import validation_exception_handler, http_exception_handler
from ai_service.api.middleware.session import session_middleware
from ai_service.api.middleware.path_rewriter import PathRewriterMiddleware

# Import core configuration
from ai_service.core.config import settings

# Import routers
from ai_service.api.routers.health import router as health_router
from ai_service.api.routers.session import router as session_router
from ai_service.api.routers.geocode import router as geocode_router
from ai_service.api.routers.questionnaire import router as questionnaire_router

# Import the consolidated chart router
from ai_service.api.routers.consolidated_chart import router as consolidated_chart_router

# Import interpretation router
from ai_service.api.routers.interpretation import router as interpretation_router

# Import export router
from ai_service.api.routers.export import router as export_router

# Import AI integration routers
from ai_service.api.routers.ai_integration_test import router as ai_integration_test_router
from ai_service.api.routers.ai_status import router as ai_status_router

# Initialize metrics
REQUESTS = Counter('birth_time_rectifier_requests_total', 'Total requests processed')
PROCESSING_TIME = Histogram('birth_time_rectifier_processing_seconds', 'Time spent processing request')
GPU_MEMORY_USAGE = Gauge('birth_time_rectifier_gpu_memory_mb', 'GPU memory usage in MB')
MODEL_INFERENCE_TIME = Histogram('birth_time_rectifier_model_inference_seconds', 'Time spent on model inference')

# Define lifespan context manager for proper setup/cleanup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup: initialize code on startup
    logger.info("Application starting up")

    # Initialize GPU manager
    try:
        from ai_service.utils.gpu_manager import GPUMemoryManager
        # Initialize GPU manager if available
        gpu_manager = GPUMemoryManager(model_allocation=float(os.getenv("GPU_MEMORY_FRACTION", 0.7)))
        app.state.gpu_manager = gpu_manager
        logger.info("GPU memory manager initialized")
    except ImportError:
        logger.info("GPU memory manager not available")
        app.state.gpu_manager = None
    except Exception as e:
        logger.error(f"Error initializing GPU manager: {e}")
        app.state.gpu_manager = None

    # Preload AI models
    try:
        from ai_service.models.unified_model import UnifiedRectificationModel
        logger.info("Preloading AI models for continuous operation...")
        app.state.rectification_model = UnifiedRectificationModel()
        logger.info("AI models preloaded successfully")

        # Initialize global model reference for backward compatibility
        global model
        model = app.state.rectification_model
    except Exception as e:
        logger.error(f"Error preloading AI models: {e}")
        app.state.rectification_model = None

    yield

    # Cleanup: shutdown code on app exit
    logger.info("Application shutdown, cleaning up resources")
    if hasattr(app.state, 'gpu_manager') and app.state.gpu_manager:
        logger.info("Cleaning up GPU resources")
        app.state.gpu_manager.cleanup()

# Create FastAPI application with lifespan
app = FastAPI(
    title="Birth Time Rectifier API",
    description="API for astrological chart generation and birth time rectification",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add test middleware
from ai_service.api.middleware import TestMiddleware
app.add_middleware(TestMiddleware)

# Add path rewriter middleware (must be added before other middleware)
app.add_middleware(PathRewriterMiddleware)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Add session middleware
app.middleware("http")(session_middleware)

# Error handling middleware
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

# Add exception handlers - using explicit type casting to satisfy type checker
app.add_exception_handler(
    RequestValidationError,
    cast(Callable[[Request, Any], Any], validation_exception_handler)
)
app.add_exception_handler(
    HTTPException,
    cast(Callable[[Request, Any], Any], http_exception_handler)
)

# Root endpoint for basic service information
@app.get("/")
async def root():
    """Root endpoint returning basic service information"""
    return {
        "service": "Birth Time Rectifier API",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "endpoints": {
            "api_docs": "/docs",
            "health": "/api/v1/health",
            "api_base": "/api/v1"
        }
    }

# Create the v1 API router with proper prefix
v1_router = APIRouter(prefix="/api/v1")

# Register all routers with the v1 API router
v1_router.include_router(health_router, tags=["Health"])
v1_router.include_router(session_router, prefix="/session", tags=["Session"])
v1_router.include_router(geocode_router, prefix="/geocode", tags=["Geocoding"])
v1_router.include_router(consolidated_chart_router, prefix="/chart", tags=["Chart"])
v1_router.include_router(questionnaire_router, prefix="/questionnaire", tags=["Questionnaire"])
v1_router.include_router(interpretation_router, tags=["Interpretation"])
v1_router.include_router(export_router, prefix="/export", tags=["Export"])
v1_router.include_router(ai_integration_test_router, prefix="/ai", tags=["AI Integration"])
v1_router.include_router(ai_status_router, prefix="/ai", tags=["AI Status"])

# Include the v1 router in the app
app.include_router(v1_router)

# Initialize model instance for AI services
model = None

def init_model():
    """
    Initialize AI model for birth time rectification.
    This is called lazily when needed.
    """
    global model

    # Import model lazily to avoid circular imports
    from ai_service.models.unified_model import UnifiedRectificationModel

    if model is None:
        try:
            logger.info("Initializing AI model...")
            model = UnifiedRectificationModel()
            logger.info("AI model initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Error initializing AI model: {e}")
            return False

    return True

if __name__ == "__main__":
    import uvicorn
    # Initialize AI model at startup
    init_model()
    uvicorn.run("ai_service.main:app", host="0.0.0.0", port=8000, reload=True)
