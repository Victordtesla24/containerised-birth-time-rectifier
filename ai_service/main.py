"""
Birth Time Rectifier API Main Entry Point

This module creates and configures the FastAPI application
following the Unified API Gateway Architecture.
"""

import logging
import os
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from ai_service.api.routers import router
from ai_service.app_startup import lifespan  # Import the lifespan function
from typing import Dict, Any
from datetime import datetime
import traceback

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
    lifespan=lifespan,  # Add the lifespan configuration here
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

# Add WebSocket session registration endpoint
@app.post("/api/v1/ws-session/register", response_model=Dict[str, Any])
async def register_websocket_session(request: Request):
    """
    Register a session that is allowed to connect via WebSocket.
    This endpoint is called by the API Gateway when a user authenticates.
    """
    try:
        # Get the WebSocketManager
        from ai_service.utils.websocket_manager import get_websocket_manager
        manager = get_websocket_manager()

        # Check if request is from the API Gateway
        headers = {k.lower(): v for k, v in request.headers.items()}
        is_from_gateway = headers.get("x-api-gateway-source") == "true"

        if not is_from_gateway:
            logger.warning("Unauthorized attempt to register WebSocket session")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the API Gateway can register WebSocket sessions"
            )

        # Get session data from request
        data = await request.json()
        session_id = data.get("session_id")

        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id is required"
            )

        # Register the session
        manager.register_session(session_id)

        # Also store in session service for redundancy
        from ai_service.services.session_service import get_session_service
        session_service = get_session_service()
        session_service.create_session(session_id)

        logger.info(f"Registered WebSocket session: {session_id}")

        return {
            "success": True,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering WebSocket session: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register WebSocket session: {str(e)}"
        )

# Starting message
@app.on_event("startup")
async def startup_event():
    logger.info("Birth Time Rectifier API starting up")
    host = os.environ.get("API_HOST", "localhost")
    port = os.environ.get("API_PORT", "8001")
    logger.info(f"API will be accessible at http://{host}:{port}")
    try:
        # Verify socket binding
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # Just test the binding - don't actually bind since uvicorn does that
            logger.info(f"Socket options set correctly for port {port}")
        except Exception as e:
            logger.error(f"Socket setup error: {e}")
    except Exception as e:
        logger.error(f"Socket verification error: {e}")

    logger.info("Ready to serve requests")

if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("API_HOST", "localhost")
    port = int(os.environ.get("API_PORT", "8001"))
    uvicorn.run("ai_service.main:app", host=host, port=port, reload=True)
