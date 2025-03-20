#!/usr/bin/env python3
"""
ASGI Wrapper for Birth Time Rectifier AI Service

This module provides a lightweight ASGI wrapper that intercepts health check
requests before they enter the middleware stack, handling them directly without
passing them to the main application at all.

Usage:
    Use as the entry point for Uvicorn in the Dockerfile:
    uvicorn ai_service.app_wrapper:app_wrapper --host 0.0.0.0 --port 8000
"""

import json
import logging
import sys
from datetime import datetime
import importlib
from typing import Dict, Any, Callable, Awaitable

# Import FastAPI for health_app to be used in tests
from fastapi import FastAPI

# Configure logging for the wrapper
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("health-check-wrapper")

# Paths that should be handled directly by this wrapper
HEALTH_CHECK_PATHS = [
    "/health",
    "/api/v1/health",
    "/system/health",
    "/health/readiness",
    "/api/v1/health/readiness",
    "/system/health/readiness",
    "/health/liveness",
    "/api/v1/health/liveness",
    "/system/health/liveness"
]

# Create a FastAPI app for health checks that can be imported for testing
health_app = FastAPI(title="Health Check API", description="API for health checks")

@health_app.get("/", tags=["Health"])
async def health():
    """Health check endpoint that returns the service status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service",
        "middleware_bypassed": True,
        "path": "/"
    }

@health_app.get("/readiness", tags=["Health"])
async def readiness():
    """Readiness check endpoint that returns if the service is ready to accept requests."""
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service"
    }

@health_app.get("/liveness", tags=["Health"])
async def liveness():
    """Liveness check endpoint that returns if the service is running."""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service"
    }

async def create_health_response(path: str, send: Callable) -> None:
    """
    Create and send a health check response.

    Args:
        path: The request path
        send: The ASGI send function
    """
    # Create appropriate response based on path
    if path.endswith("/readiness"):
        response = {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "service": "ai_service",
            "middleware_bypassed": True,
            "path": path
        }
    elif path.endswith("/liveness"):
        response = {
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
            "service": "ai_service",
            "middleware_bypassed": True,
            "path": path
        }
    else:
        # Default health response
        response = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "ai_service",
            "middleware_bypassed": True,
            "path": path
        }

    # Send HTTP response
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            [b"content-type", b"application/json"],
            [b"cache-control", b"no-cache, no-store, must-revalidate"],
            [b"x-middleware-bypass", b"true"]
        ]
    })

    await send({
        "type": "http.response.body",
        "body": json.dumps(response, indent=2).encode("utf-8")
    })

    logger.info(f"Health check response sent for {path}")

async def app_wrapper(scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
    """
    ASGI wrapper function that handles health checks directly and passes all other
    requests to the main application.

    Args:
        scope: The ASGI connection scope
        receive: The ASGI receive function
        send: The ASGI send function
    """
    # For health check paths, handle directly without involving the main app
    if scope["type"] == "http" and scope["path"] in HEALTH_CHECK_PATHS:
        # Log the health check request
        path = scope["path"]
        method = scope.get("method", "UNKNOWN")
        client = scope.get("client", ("UNKNOWN", 0))
        logger.info(f"Health check requested: {method} {path} from {client[0]}:{client[1]}")

        # Send health response directly
        await create_health_response(path, send)
        return

    # Import the main app for non-health requests
    main_app = None
    try:
        # Try to import unified_main first
        try:
            app_module = importlib.import_module("ai_service.unified_main")
            main_app = app_module.app
            logger.debug("Using unified_main.app for non-health requests")
        except ImportError:
            # Fall back to regular main
            app_module = importlib.import_module("ai_service.main")
            main_app = app_module.app
            logger.debug("Using main.app for non-health requests")
    except Exception as e:
        logger.error(f"Failed to import main application: {e}")
        # Return a 500 error
        error_response = {
            "error": "Failed to import main application",
            "detail": str(e),
            "timestamp": datetime.now().isoformat()
        }
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [[b"content-type", b"application/json"]]
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps(error_response).encode("utf-8")
        })
        return

    # Handle lifespan protocol directly by delegating to the main app
    if scope["type"] == "lifespan":
        await main_app(scope, receive, send)
        return

    # For non-health HTTP requests, pass to the main application
    if scope["type"] == "http":
        path = scope.get("path", "UNKNOWN")
        logger.debug(f"Passing request to main application: {path}")

    # Pass to the main application and handle any errors
    try:
        await main_app(scope, receive, send)
    except Exception as e:
        logger.error(f"Error in main application: {e}")

        # If this is an HTTP request and we haven't sent a response yet, send a 500 error
        if scope["type"] == "http":
            error_response = {
                "error": "Internal server error",
                "detail": str(e),
                "timestamp": datetime.now().isoformat()
            }

            try:
                await send({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        [b"content-type", b"application/json"]
                    ]
                })

                await send({
                    "type": "http.response.body",
                    "body": json.dumps(error_response).encode("utf-8")
                })
            except Exception:
                logger.critical("Failed to send error response", exc_info=True)

if __name__ == "__main__":
    print("ASGI Wrapper for Birth Time Rectifier AI Service")
    print("This module should be used as the ASGI entry point in uvicorn:")
    print("uvicorn ai_service.app_wrapper:app_wrapper --host 0.0.0.0 --port 8000")
