"""
Birth Time Rectifier API Main Entry Point

This module creates and configures the FastAPI application
following the Unified API Gateway Architecture.
"""

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ai_service.api.routers import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Birth Time Rectifier API",
    description="API for birth time rectification following the Original Sequence Diagram implementation",
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

# Include router
app.include_router(router)

# Add root endpoint to fix 404 error
@app.get("/", tags=["Info"])
async def root():
    """
    Root endpoint that returns basic service information.
    """
    return {
        "service": "Birth Time Rectifier AI Service",
        "status": "online",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "api": "/api/v1",
            "docs": "/docs"
        }
    }

# Add health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {"status": "ok"}

# Starting message
@app.on_event("startup")
async def startup_event():
    logger.info("Birth Time Rectifier API starting up")
    host = os.environ.get("API_HOST", "localhost")
    port = os.environ.get("API_PORT", "3001")
    logger.info(f"API will be accessible at http://{host}:{port}")
    logger.info("Ready to serve requests")

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("API_HOST", "localhost")
    port = int(os.environ.get("API_PORT", "3001"))
    uvicorn.run("ai_service.main:app", host=host, port=port, reload=True)
