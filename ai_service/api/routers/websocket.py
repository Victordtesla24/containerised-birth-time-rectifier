"""
WebSocket Router

This module provides WebSocket endpoints for real-time communication
with clients, including progress updates during long-running processes.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException, status
from typing import Dict, Any, Optional, List
import logging
import asyncio
import json
from datetime import datetime

# Import the shared WebSocketManager and events
from ai_service.utils.websocket_manager import get_websocket_manager
from ai_service.utils.websocket_events import emit_event, EventType
from ai_service.services.session_service import SessionService

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
    responses={
        500: {"description": "Internal server error"},
        401: {"description": "Authentication failed"},
        404: {"description": "Not found"}
    }
)

# Get the session service instance
async def get_session_service() -> SessionService:
    """Get the session service instance."""
    return SessionService()

@router.websocket("/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time communication with clients.

    Args:
        websocket: The WebSocket connection
        session_id: Session identifier
        token: Optional authentication token
    """
    # Get the WebSocket manager
    websocket_manager = get_websocket_manager()
    session_service = await get_session_service()

    # Authenticate the connection if token is provided
    authenticated = token is not None

    try:
        # Accept the WebSocket connection
        await websocket.accept()

        # Send authentication status
        await websocket.send_json({
            "type": "authentication_status",
            "data": {
                "authenticated": authenticated,
                "session_id": session_id
            }
        })

        # Register the connection with the WebSocket manager
        await websocket_manager.connect(websocket, session_id)

        try:
            # Keep the connection alive by listening for messages
            while True:
                # Wait for a message from the client
                data = await websocket.receive_text()

                try:
                    # Parse the message
                    message = json.loads(data)

                    # Handle different message types
                    message_type = message.get("type", "")

                    if message_type == "ping":
                        # Respond to ping with pong
                        await emit_event(session_id, "pong", {
                            "timestamp": datetime.now().isoformat()
                        })
                    elif message_type == "client_info":
                        # Store client information
                        client_info = message.get("data", {})
                        if session_id in websocket_manager.client_metadata:
                            websocket_manager.client_metadata[session_id]["client_info"] = client_info
                            logger.info(f"Updated client info for session {session_id}: {client_info.get('user_agent', 'Unknown')}")
                    elif message_type == "request_progress_history":
                        # Client is requesting progress history after reconnection
                        try:
                            logger.info(f"Client {session_id} requested progress history")
                            # Send a response acknowledging the request
                            await emit_event(session_id, "progress_history_status", {
                                "status": "processing",
                                "message": "Retrieving progress history"
                            })

                            # In a real implementation, we would fetch from the database
                            # For now, just return an empty history
                            await emit_event(session_id, "progress_history", {
                                "entries": [],
                                "count": 0
                            })
                            logger.info(f"Empty progress history sent to client {session_id}")
                        except Exception as history_error:
                            logger.error(f"Error sending progress history: {history_error}")
                            await emit_event(session_id, "error", {
                                "message": "Failed to retrieve progress history",
                                "error_code": "HISTORY_ERROR"
                            })
                    elif message_type == "request_rectification_status":
                        # Client is requesting current rectification status
                        chart_id = message.get("chart_id")
                        rectification_id = message.get("rectification_id")

                        if not chart_id or not rectification_id:
                            await emit_event(session_id, "error", {
                                "message": "Missing chart_id or rectification_id",
                                "error_code": "INVALID_REQUEST"
                            })
                        else:
                            try:
                                # Get current status from database
                                from ai_service.database.repositories import ChartRepository
                                repository = ChartRepository()

                                # Get rectification data
                                rectification_data = await repository.get_rectification(rectification_id)

                                if rectification_data:
                                    # Send current status
                                    status = rectification_data.get("status", "unknown")
                                    progress = rectification_data.get("progress", 0)

                                    await emit_event(session_id, "rectification_status", {
                                        "chart_id": chart_id,
                                        "rectification_id": rectification_id,
                                        "status": status,
                                        "progress": progress,
                                        "message": rectification_data.get("message", ""),
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    logger.info(f"Sent current rectification status to client {session_id}: {status} ({progress}%)")
                                else:
                                    # No rectification found
                                    await emit_event(session_id, "rectification_status", {
                                        "chart_id": chart_id,
                                        "rectification_id": rectification_id,
                                        "status": "not_found",
                                        "progress": 0,
                                        "message": "Rectification not found",
                                        "timestamp": datetime.now().isoformat()
                                    })
                                    logger.warning(f"Rectification {rectification_id} not found for client {session_id}")
                            except Exception as status_error:
                                logger.error(f"Error retrieving rectification status: {status_error}")
                                await emit_event(session_id, "error", {
                                    "message": "Failed to retrieve rectification status",
                                    "error_code": "STATUS_ERROR"
                                })
                    else:
                        # Unknown message type
                        logger.debug(f"Received unknown message type: {message_type}")

                        # Send acknowledgment for any message type
                        await emit_event(session_id, "acknowledgment", {
                            "received_type": message_type,
                            "timestamp": datetime.now().isoformat(),
                            "status": "unknown_message_type"
                        })
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from client: {data[:100]}...")
                    await emit_event(session_id, "error", {
                        "message": "Invalid JSON format",
                        "error_code": "INVALID_FORMAT"
                    })
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

                    # Try to inform client of the error
                    try:
                        await emit_event(session_id, "error", {
                            "message": "Error processing message",
                            "error_code": "PROCESSING_ERROR"
                        })
                    except Exception:
                        # If we can't even send the error, there's not much we can do
                        pass

        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {session_id}")

        except asyncio.CancelledError:
            logger.info(f"WebSocket connection cancelled for session {session_id}")
            raise  # Re-raise to allow proper cleanup
        except Exception as connection_error:
            logger.error(f"Unexpected WebSocket connection error: {connection_error}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            # Unregister the connection when it's closed
            websocket_manager.disconnect(session_id)
            logger.info(f"WebSocket connection cleaned up for session {session_id}")

    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        try:
            # Try to send an error message
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except Exception:
            pass

@router.get("/clients", response_model=Dict[str, Any])
async def get_active_clients() -> Dict[str, Any]:
    """
    Get information about active WebSocket clients.

    This endpoint is for administrative purposes and provides
    information about currently connected WebSocket clients.

    Returns:
        Dictionary with client count and session IDs
    """
    websocket_manager = get_websocket_manager()
    active_count = len(websocket_manager.active_connections)

    return {
        "active_clients": active_count,
        "session_ids": list(websocket_manager.active_connections.keys())
    }
