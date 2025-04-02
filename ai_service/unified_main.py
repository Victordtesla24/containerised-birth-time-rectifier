"""
Unified Main Application Entry Point for the AI Service.

This module implements the Consolidated Single-Registration Architecture
as described in the API architecture documentation. It provides a single point of
registration for all API routers with proper versioning.
"""

import os
import sys
import logging
import time
import json
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from fastapi import FastAPI, APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocketState
import traceback

# Import the application logic
from ai_service.app_startup import initialize_application, lifespan

# Import the WebSocket manager for direct endpoint
from ai_service.utils.websocket_manager import get_websocket_manager

# Ensure log directory exists
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "ai_service.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger("ai_service.unified_main")

# Local imports
from ai_service.utils.env_loader import load_env_file, get_env_with_fallback
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
        "architecture": "Consolidated Single-Registration"
    }

# Debug endpoint to show all registered routes
@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint that lists all registered routes."""
    routes = []
    for route in app.routes:
        route_info = {
            "path": getattr(route, "path", "unknown"),
            "name": getattr(route, "name", "unknown"),
            "methods": getattr(route, "methods", ["unknown"]),
        }
        routes.append(route_info)

    return {
        "registered_routes": routes,
        "api_prefix": API_PREFIX,
        "middleware": [m.__class__.__name__ for m in app.user_middleware]
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

# Add explicit health endpoints with v1 prefix
@app.get("/api/v1/health")
async def api_v1_health():
    """Health check endpoint with v1 prefix."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service",
        "endpoint": "api_v1_health"
    }

@app.get("/api/v1/health/ping")
async def api_v1_health_ping():
    """Simple ping health check endpoint with v1 prefix."""
    return {
        "response": "pong",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service",
        "endpoint": "api_v1_health_ping"
    }

@app.get("/api/v1/health/basic")
async def api_v1_health_basic():
    """Basic health check endpoint with v1 prefix."""
    return {
        "status": "ok",
        "service": "ai_service",
        "timestamp": datetime.now().isoformat(),
        "endpoint": "api_v1_health_basic"
    }

# API Path Convention
# This application only supports versioned API endpoints with the /api/v1/ prefix
# Any requests to non-v1 API paths will receive a 404 Not Found response
# This design choice ensures consistent API versioning and simplifies maintenance

# Import and include main router with standardized prefix
from ai_service.api.routers import router
app.include_router(router, prefix=API_PREFIX)
logger.info("Main router included with prefix: %s", API_PREFIX)

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
    logger.info(f"Request received: {request.method} {request.url.path}")

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

# Direct test WebSocket endpoint
@app.websocket("/direct-ws/{session_id}")
async def direct_websocket_endpoint(websocket: WebSocket, session_id: str):
    """Direct WebSocket endpoint for testing and direct connections."""
    # Get the WebSocket manager
    ws_manager = get_websocket_manager()

    # Log headers for debugging
    logger.info(f"Direct WebSocket headers: {dict(websocket.headers.items())}")

    # Accept the connection immediately
    try:
        await websocket.accept()
        logger.info(f"Direct WebSocket connection established for session {session_id}")

        # Register with the manager after successful acceptance
        connected = False
        try:
            await ws_manager.connect(websocket, session_id)
            connected = True
            logger.info(f"Direct session {session_id} registered with WebSocket manager")
        except Exception as connect_err:
            logger.error(f"Error connecting direct WebSocket to manager: {connect_err}")
            logger.error(traceback.format_exc())
            # Connection already accepted, so we proceed
    except Exception as e:
        logger.error(f"Error establishing direct WebSocket connection: {e}")
        logger.error(traceback.format_exc())
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Internal server error")
        return

    try:
        # Initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "message": "Direct WebSocket connection established (no auth)"
        })

        # Process messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()
                logger.info(f"Received WebSocket message: {data}")

                # Process based on message type
                message_type = data.get("type", "unknown")

                if message_type == "ping":
                    logger.info("Received ping, sending pong")
                    await websocket.send_json({
                        "type": "pong",
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    logger.info(f"Received message of type: {message_type}")
                    await websocket.send_json({
                        "type": "message_received",
                        "original_type": message_type,
                        "session_id": session_id,
                        "timestamp": datetime.now().isoformat()
                    })
            except json.JSONDecodeError:
                logger.error("Received invalid JSON")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                })
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for session {session_id}")
                break
            except Exception as msg_error:
                logger.error(f"Error processing WebSocket message: {msg_error}")
                logger.error(traceback.format_exc())
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(msg_error),
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception:
                    # Connection likely already closed
                    logger.info("Could not send error message, connection may be closed")
                    break
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Ensure the connection is properly cleaned up
        if connected:
            ws_manager.disconnect(session_id)
        logger.info(f"Cleaned up WebSocket connection for session {session_id}")

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
