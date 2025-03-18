"""
WebSocket Events for Birth Time Rectifier API Gateway

This module provides functions for emitting events to WebSocket clients
through the WebSocket proxy.
"""

from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

from api_gateway.websocket_proxy import proxy

# Configure logging
logger = logging.getLogger("api_gateway.websocket_events")

async def emit_event(
    session_id: str,
    event_type: str,
    data: Dict[str, Any]
) -> bool:
    """
    Emit an event to a WebSocket client.

    Args:
        session_id: The session ID of the client
        event_type: The type of event to emit
        data: The data to send with the event

    Returns:
        bool: True if the event was sent, False otherwise
    """
    try:
        # Check if the session is connected
        if session_id not in proxy.active_connections:
            logger.warning(f"Session {session_id} not connected, cannot emit event")
            return False

        # Create the event payload
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        # Get the client WebSocket
        client_ws, _ = proxy.active_connections[session_id]

        # Send the event
        await client_ws.send_json(payload)
        logger.info(f"Emitted {event_type} event to session {session_id}")
        return True

    except Exception as e:
        logger.error(f"Error emitting {event_type} event to session {session_id}: {e}")
        return False

async def emit_rectification_progress(
    session_id: str,
    progress: int,
    message: str,
    chart_id: str,
    status: str = "processing",
    result: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Emit a rectification progress event to a WebSocket client.

    Args:
        session_id: The session ID of the client
        progress: The progress percentage (0-100)
        message: The progress message
        chart_id: The chart ID being rectified
        status: The status of the rectification process
        result: Optional result data for completed rectifications

    Returns:
        bool: True if the event was sent, False otherwise
    """
    try:
        # Create the event payload
        payload = {
            "progress": progress,
            "message": message,
            "chart_id": chart_id,
            "status": status
        }

        # Add result data if provided
        if result:
            payload["result"] = result

        # Emit the event
        return await emit_event(session_id, "rectification_progress", payload)

    except Exception as e:
        logger.error(f"Error emitting rectification progress event to session {session_id}: {e}")
        return False
