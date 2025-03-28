"""
WebSocket Events for Birth Time Rectifier API Gateway

This module provides functions for emitting events to WebSocket clients
through the WebSocketProxy implementation.
"""

from typing import Dict, Any, Optional, Union
import logging

# Configure logging
logger = logging.getLogger("api_gateway.websocket_events")

# Import the WebSocket proxy
from api_gateway.websocket_proxy import proxy as websocket_proxy

# Event type constants
class EventType:
    """Constants for WebSocket event types"""
    PROGRESS = "progress"
    COMPLETE = "complete"
    ERROR = "error"
    MESSAGE = "message"
    SYSTEM = "system"
    STATUS = "status"
    RECTIFICATION_PROGRESS = "rectification_progress"
    RECTIFICATION_COMPLETE = "rectification_complete"
    RECTIFICATION_ERROR = "rectification_error"

async def emit_event(session_id: str, event_type: str, data: Dict[str, Any]) -> bool:
    """
    Emit an event to a WebSocket client.

    Args:
        session_id: The session ID to send the event to
        event_type: The type of event
        data: The event data

    Returns:
        bool: Whether the event was successfully sent
    """
    try:
        message = {
            "type": event_type,
            "data": data
        }
        await websocket_proxy.broadcast(session_id, message)
        return True
    except Exception as e:
        logger.error(f"Error emitting event: {e}")
        return False

async def emit_rectification_progress(session_id: str, progress: float, message: str) -> bool:
    """
    Emit a rectification progress event.

    Args:
        session_id: The session ID to send the event to
        progress: The progress value (0-100)
        message: The progress message

    Returns:
        bool: Whether the event was successfully sent
    """
    return await emit_event(session_id, EventType.RECTIFICATION_PROGRESS, {
        "progress": progress,
        "message": message
    })

async def emit_rectification_complete(session_id: str, result: Dict[str, Any]) -> bool:
    """
    Emit a rectification complete event.

    Args:
        session_id: The session ID to send the event to
        result: The rectification result data

    Returns:
        bool: Whether the event was successfully sent
    """
    return await emit_event(session_id, EventType.RECTIFICATION_COMPLETE, result)

async def emit_rectification_error(session_id: str, error: str) -> bool:
    """
    Emit a rectification error event.

    Args:
        session_id: The session ID to send the event to
        error: The error message

    Returns:
        bool: Whether the event was successfully sent
    """
    return await emit_event(session_id, EventType.RECTIFICATION_ERROR, {
        "error": error
    })

async def emit_error(session_id: str, error: str, code: Optional[str] = None) -> bool:
    """
    Emit an error event.

    Args:
        session_id: The session ID to send the event to
        error: The error message
        code: Optional error code

    Returns:
        bool: Whether the event was successfully sent
    """
    data = {
        "error": error
    }
    if code:
        data["code"] = code
    return await emit_event(session_id, EventType.ERROR, data)

async def broadcast_system_message(message: str) -> None:
    """
    Broadcast a system message to all connected clients.

    Args:
        message: The message to broadcast
    """
    try:
        # For each session in the connection_status dict, send a message
        if hasattr(websocket_proxy, 'connection_status'):
            for session_id in websocket_proxy.connection_status:
                if websocket_proxy.connection_status[session_id].get("client_connected", False):
                    await emit_event(session_id, EventType.SYSTEM, {
                        "message": message
                    })
        else:
            logger.warning("WebSocket proxy connection_status not available")
    except Exception as e:
        logger.error(f"Error broadcasting system message: {e}")
