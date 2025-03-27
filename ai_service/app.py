"""
Application factory for the Birth Time Rectifier API

This module creates the FastAPI application and configures middleware,
WebSocket handlers, and other global components.
"""

import logging
import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from ai_service.utils.websocket_manager import manager

# Configure logging
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the FastAPI application"""

    # Create the FastAPI application
    app = FastAPI(
        title="Birth Time Rectifier API",
        description="API for astrological birth time rectification",
        version="1.0.0"
    )

    # Configure CORS for all origins (can be restricted in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add WebSocket endpoint
    @app.websocket("/ws/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        """
        WebSocket endpoint for real-time birth time rectification updates.

        Args:
            websocket: The WebSocket connection
            session_id: The session ID for authentication and association
        """
        await manager.connect(websocket, session_id)
        try:
            # Main message processing loop
            while True:
                data = await websocket.receive_text()
                try:
                    # Parse and process the message
                    message = json.loads(data)
                    message_type = message.get("type", "")

                    # Handle ping messages
                    if message_type == "ping":
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": time.time(),
                            "message": "Server is alive"
                        })
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {data}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": time.time()
                    })
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                        "timestamp": time.time()
                    })
        except WebSocketDisconnect:
            # Handle normal client disconnection
            manager.disconnect(session_id)
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"WebSocket error for session {session_id}: {e}")
            manager.disconnect(session_id)

    return app

# Create a global app instance
app = create_app()
