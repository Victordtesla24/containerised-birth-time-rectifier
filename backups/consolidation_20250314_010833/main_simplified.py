"""
Birth Time Rectifier API - Simplified Main Application (Maintained for Testing)

This is the simplified FastAPI application that serves the Birth Time Rectifier API
using the unified API gateway and consolidated router architecture.
"""

from fastapi import FastAPI, Request, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import time
from datetime import datetime
import os
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
from ai_service.api.middleware.legacy_support import legacy_path_middleware
from ai_service.api.middleware.error_handling import validation_exception_handler, http_exception_handler
from ai_service.api.middleware.session import session_middleware

# Import core configuration
from ai_service.core.config import settings

# Import routers
from ai_service.api.routers.health import router as health_router
from ai_service.api.routers.session import router as session_router
from ai_service.api.routers.geocode import router as geocode_router
from ai_service.api.routers.questionnaire import router as questionnaire_router

# Import the consolidated chart router
from ai_service.api.routers.consolidated_chart import router as consolidated_chart_router

# Import test routers for backward compatibility when needed
from ai_service.api.routers.ai_integration_test import router as ai_integration_test_router
from ai_service.api.routers.test_endpoints import router as test_endpoints_router
from ai_service.api.routers.ai_status import router as ai_status_router
from ai_service.api.routers.test_compatibility import router as test_compatibility_router

# Initialize metrics
REQUESTS = Counter('birth_time_rectifier_requests_total', 'Total requests processed')
PROCESSING_TIME = Histogram('birth_time_rectifier_processing_seconds', 'Time spent processing request')
GPU_MEMORY_USAGE = Gauge('birth_time_rectifier_gpu_memory_mb', 'GPU memory usage in MB')
MODEL_INFERENCE_TIME = Histogram('birth_time_rectifier_model_inference_seconds', 'Time spent on model inference')

# Create FastAPI application
app = FastAPI(
    title="Birth Time Rectifier API",
    description="API for astrological chart generation and birth time rectification",
    version="1.0.0",
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
from ai_service.test_middleware import TestMiddleware
app.add_middleware(TestMiddleware)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Error handling middleware
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

# Root endpoint for health check
@app.get("/")
async def root():
    """Root endpoint returning basic service information"""
    return {
        "service": "Birth Time Rectifier API",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }

# Add middleware
app.middleware("http")(legacy_path_middleware)
app.middleware("http")(session_middleware)

# Add exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Standard API prefix for all endpoints
API_PREFIX = "/api"
API_V1_PREFIX = "/api/v1"

# Setup v1 API router
v1_router = APIRouter(prefix=API_V1_PREFIX)

# Register standard endpoints with the v1 API router
v1_router.include_router(health_router, tags=["Health"])
v1_router.include_router(session_router, prefix="/session", tags=["Session"])
v1_router.include_router(geocode_router, prefix="/geocode", tags=["Geocoding"])
v1_router.include_router(questionnaire_router, prefix="/questionnaire", tags=["Questionnaire"])

# Register consolidated chart router at multiple paths for backward compatibility
v1_router.include_router(consolidated_chart_router, prefix="/chart", tags=["Chart"])
v1_router.include_router(consolidated_chart_router, prefix="/chart/v2", tags=["Chart"])
v1_router.include_router(consolidated_chart_router, prefix="/chart/v3", tags=["Chart"])
v1_router.include_router(consolidated_chart_router, prefix="/chart/robust", tags=["Chart"])

# Register test routers for backward compatibility
v1_router.include_router(ai_integration_test_router, prefix="/ai", tags=["AI Integration"])
v1_router.include_router(ai_status_router, prefix="/ai", tags=["AI Status"])
v1_router.include_router(test_endpoints_router, prefix="/chart", tags=["Testing"])
v1_router.include_router(test_compatibility_router, tags=["Test Compatibility"])

# Include the v1 router in the app
app.include_router(v1_router)

# DUAL ROUTER REGISTRATION PATTERN
# We also register all routers at the root level for backward compatibility
# This fulfills the API architecture requirement for dual-registration

# Register routers at /api/* for primary endpoints
api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(session_router, prefix="/session")
api_router.include_router(geocode_router, prefix="/geocode") # Add the prefix back
api_router.include_router(consolidated_chart_router, prefix="/chart")
api_router.include_router(questionnaire_router, prefix="/questionnaire")
api_router.include_router(ai_integration_test_router, prefix="/ai")
api_router.include_router(ai_status_router, prefix="/ai")
api_router.include_router(test_endpoints_router, prefix="/chart")
api_router.include_router(test_compatibility_router)
app.include_router(api_router)

# Register routers at root level for backward compatibility
app.include_router(health_router)
app.include_router(session_router, prefix="/session")
app.include_router(geocode_router, prefix="/geocode") # Add the prefix back
app.include_router(consolidated_chart_router, prefix="/chart")
app.include_router(questionnaire_router, prefix="/questionnaire")
app.include_router(ai_integration_test_router, prefix="/ai")
app.include_router(ai_status_router, prefix="/ai")
app.include_router(test_endpoints_router, prefix="/chart")
app.include_router(test_compatibility_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ai_service.main_simplified:app", host="0.0.0.0", port=8000, reload=True)
