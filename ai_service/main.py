"""
Birth Time Rectifier API - Main Application

This is the main FastAPI application that serves the Birth Time Rectifier API.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from datetime import datetime
import os
from contextlib import asynccontextmanager
try:
    from prometheus_client import Counter, Histogram, Gauge
except ImportError:
    # Allow execution without Prometheus for development
    print("Warning: Prometheus client not installed, metrics will be disabled")
    Counter = lambda *args, **kwargs: None
    Histogram = lambda *args, **kwargs: None
    Gauge = lambda *args, **kwargs: None

# Import routers - using 'router' as the standard name for all router modules
# Import all router modules
from ai_service.api.routers.health import router as health_router
from ai_service.api.routers.chart import router as chart_router
from ai_service.api.routers.questionnaire import router as questionnaire_router
from ai_service.api.routers.geocode import router as geocode_router
from ai_service.api.routers.validate import router as validate_router
from ai_service.api.routers.rectify import router as rectify_router
from ai_service.api.routers.export import router as export_router
from ai_service.api.routers.ai_integration_test import router as ai_integration_test_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=os.path.join("logs", "ai_service.log") if os.path.exists("logs") else None,
)
logger = logging.getLogger("birth-time-rectifier")

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

# Standard API prefix for all endpoints
API_PREFIX = "/api"

# Register all routers with the /api prefix (primary endpoints)
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(validate_router, prefix=f"{API_PREFIX}/chart")
app.include_router(geocode_router, prefix=API_PREFIX)
app.include_router(chart_router, prefix=f"{API_PREFIX}/chart")
app.include_router(questionnaire_router, prefix=f"{API_PREFIX}/questionnaire")
app.include_router(rectify_router, prefix=f"{API_PREFIX}/chart")
app.include_router(export_router, prefix=f"{API_PREFIX}/chart")
app.include_router(ai_integration_test_router, prefix=f"{API_PREFIX}/ai")

# Also register routers at root level for backward compatibility (alternative endpoints)
app.include_router(health_router)
app.include_router(validate_router, prefix="/chart")
app.include_router(geocode_router)
app.include_router(chart_router, prefix="/chart")
app.include_router(questionnaire_router, prefix="/questionnaire")
app.include_router(rectify_router, prefix="/chart")
app.include_router(export_router, prefix="/chart")
app.include_router(ai_integration_test_router, prefix="/ai")

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
