"""
WebSocket router for real-time updates.

This module provides WebSocket endpoints for real-time updates during
long-running processes like birth time rectification.
"""

import logging
from typing import Dict, Any, Optional, List
import json
import time
from datetime import datetime
import asyncio
import traceback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from starlette.websockets import WebSocketState, WebSocket as StarletteWebSocket

from ai_service.utils.websocket_manager import get_websocket_manager, WebSocketManager
from ai_service.services.session_service import SessionService, get_session_service
from ai_service.api.services.chart.service import get_chart_service
from ai_service.utils.websocket_events import EventType
from ai_service.api.dependencies.auth import verify_token as auth_verify_token

# Configure logging
logger = logging.getLogger(__name__)

# Setup router
router = APIRouter(prefix="/ws", tags=["websocket"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Global references to services
_chart_service = None
_websocket_manager = None

# Active connections store
active_connections: Dict[str, WebSocket] = {}

async def get_session_service_async() -> SessionService:
    """Get the session service for async contexts."""
    # This is actually a synchronous call, but we wrap it
    # in an async function for consistency in this file
    return get_session_service()

async def get_manager() -> WebSocketManager:
    """Get the WebSocket manager singleton."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = get_websocket_manager()
    return _websocket_manager

@router.websocket("/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time updates.

    This endpoint follows the sequence diagram flow for WebSocket communication,
    maintaining a connection that can receive progress updates for long-running
    processes like birth time rectification.

    Args:
        websocket: The WebSocket connection
        session_id: The session ID for authentication and association
        token: Optional authentication token
    """
    # Get the WebSocket manager
    manager = await get_manager()

    # Get the session service for authentication
    session_service = await get_session_service_async()

    # Validate session if token provided
    if token:
        try:
            # Verify token
            user_id = auth_verify_token(token)
            if not user_id:
                await websocket.close(code=4001, reason="Invalid authentication token")
                return
        except Exception as e:
            logger.error(f"Error validating WebSocket token: {e}")
            await websocket.close(code=4001, reason="Authentication error")
            return

    # Accept the connection
    try:
        await manager.connect(websocket, session_id)
    except Exception as e:
        logger.error(f"Error establishing WebSocket connection: {e}")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=1011, reason="Internal server error")
        return

    try:
        # Initial status message upon connection
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "message": "WebSocket connection established"
        })

        # Check if session exists
        try:
            # Get the session service
            session_service = get_session_service()

            # Call get_session directly (it's a synchronous method)
            session_data = session_service.get_session(session_id)

            if not session_data:
                # Create a new session
                session_service.create_session(session_id=session_id)
                logger.info(f"Created new session: {session_id}")
        except Exception as e:
            logger.error(f"Error working with session: {e}")
            # Continue without session data

        # Main message processing loop
        while True:
            # Wait for message from client
            try:
                data = await websocket.receive_json()
            except json.JSONDecodeError:
                try:
                    text_data = await websocket.receive_text()
                    # Try to parse as JSON
                    data = json.loads(text_data)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Invalid WebSocket message format: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid message format. Expected JSON.",
                        "timestamp": datetime.now().isoformat()
                    })
                    continue
                except Exception as e:
                    logger.error(f"Error receiving WebSocket message: {e}")
                    break

            try:
                # Log activity
                logger.info(f"WebSocket message from {session_id}: {data.get('type', 'unknown')}")

                # Process message based on type
                message_type = data.get("type", "")

                if message_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })

                elif message_type == "subscribe":
                    # Subscribe to a specific channel
                    channel = data.get("channel", "")
                    if channel:
                        await manager.subscribe(session_id, channel)
                        await websocket.send_json({
                            "type": "subscription_confirmed",
                            "channel": channel,
                            "timestamp": datetime.now().isoformat()
                        })

                elif message_type == "unsubscribe":
                    # Unsubscribe from a specific channel
                    channel = data.get("channel", "")
                    if channel:
                        await manager.unsubscribe(session_id, channel)
                        await websocket.send_json({
                            "type": "unsubscription_confirmed",
                            "channel": channel,
                            "timestamp": datetime.now().isoformat()
                        })

                elif message_type == "status":
                    # Send current session status
                    try:
                        # Get the session service directly (synchronous)
                        session_service = get_session_service()

                        # Call get_session directly (it's a synchronous method)
                        session_data = session_service.get_session(session_id)

                        await websocket.send_json({
                            "type": "status",
                            "session_id": session_id,
                            "status": "active" if session_data else "inactive",
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"Error getting session status: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Failed to retrieve session status",
                            "timestamp": datetime.now().isoformat()
                        })

                elif message_type == "rectification_progress":
                    # Client requesting current rectification progress
                    chart_id = data.get("chart_id")
                    if not chart_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing chart_id parameter",
                            "timestamp": datetime.now().isoformat()
                        })
                        continue

                    # Get chart service
                    chart_service = get_chart_service()
                    if not chart_service:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Chart service unavailable",
                            "timestamp": datetime.now().isoformat()
                        })
                        continue

                    # Get status directly from the imported function
                    try:
                        # Create a default status result as fallback
                        status_result = {
                            "status": "unknown",
                            "progress": 0,
                            "message": "Status unavailable"
                        }

                        try:
                            # Import directly to avoid circular imports
                            from ai_service.api.routers.rectify import get_rectification_status

                            # Call the function with proper parameters
                            status_result = await get_rectification_status(
                                rectification_id=chart_id,
                                session_id=session_id
                            )
                        except ImportError:
                            logger.error("Could not import rectify module")
                        except Exception as e:
                            logger.error(f"Error calling get_rectification_status: {e}")

                        # Send status back to client with whatever we got
                        await websocket.send_json({
                            "type": "rectification_progress",
                            "chart_id": chart_id,
                            **status_result,
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        logger.error(f"Error handling status request: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Error retrieving rectification status: {str(e)}",
                            "timestamp": datetime.now().isoformat()
                        })

                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": datetime.now().isoformat()
                    })

            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Server error: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception:
                    break  # Connection likely broken, exit loop

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        # Ensure the connection is properly closed and removed from manager
        manager.disconnect(session_id)
        logger.info(f"Closed WebSocket connection for session {session_id}")

@router.get("/clients", response_model=Dict[str, Any])
async def get_active_clients() -> Dict[str, Any]:
    """
    Get information about active WebSocket clients.

    Returns:
        Dictionary with active client information
    """
    try:
        manager = await get_manager()

        # Check if manager is None
        if manager is None:
            return {
                "active_connections": [],
                "count": 0,
                "timestamp": datetime.now().isoformat(),
                "error": "WebSocket manager not available"
            }

        return {
            "active_connections": manager.active_connections,
            "count": len(manager.active_connections),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting active clients: {e}")
        return {
            "active_connections": [],
            "count": 0,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
