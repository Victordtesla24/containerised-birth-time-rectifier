"""
WebSocket Event Emitter for Birth Time Rectifier API

This module provides functions for emitting events to WebSocket clients.
It defines event types and provides a consistent interface for sending
real-time updates during long-running processes.
"""

from enum import Enum, auto
from typing import Dict, Any, Optional
import logging
import asyncio

from ai_service.api.websockets import manager

# Configure logging
logger = logging.getLogger(__name__)

class EventType(Enum):
    """
    Enum defining the types of events that can be emitted.
    """
    # Session events
    SESSION_CREATED = auto()
    SESSION_EXPIRED = auto()

    # Geocoding events
    GEOCODE_COMPLETED = auto()

    # Chart events
    VALIDATION_COMPLETED = auto()
    CHART_GENERATED = auto()
    CHART_RETRIEVED = auto()

    # Questionnaire events
    QUESTIONNAIRE_STARTED = auto()
    QUESTION_ANSWERED = auto()
    QUESTIONNAIRE_COMPLETED = auto()

    # Rectification events
    RECTIFICATION_STARTED = auto()
    RECTIFICATION_PROGRESS = auto()
    RECTIFICATION_COMPLETED = auto()

    # Export events
    EXPORT_STARTED = auto()
    EXPORT_COMPLETED = auto()

async def emit_event(session_id: str, event_type: EventType, data: Dict[str, Any]) -> bool:
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
        # Create the event payload
        payload = {
            "type": event_type.name.lower(),
            "data": data,
            "timestamp": data.get("timestamp", None)
        }

        # Send the event to the client
        success = await manager.send_update(session_id, payload)

        if success:
            logger.info(f"Emitted {event_type.name} event to session {session_id}")
        else:
            logger.warning(f"Failed to emit {event_type.name} event to session {session_id}")

        return success
    except Exception as e:
        logger.error(f"Error emitting {event_type.name} event to session {session_id}: {e}")
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
            "type": "rectification_progress",
            "status": status,
            "progress": progress,
            "message": message,
            "chart_id": chart_id
        }

        # Add result data if provided
        if result:
            payload["result"] = result

        # Send the event to the client
        success = await manager.send_update(session_id, payload)

        if success:
            logger.info(f"Emitted rectification progress event ({progress}%) to session {session_id}")
        else:
            logger.warning(f"Failed to emit rectification progress event to session {session_id}")

        return success
    except Exception as e:
        logger.error(f"Error emitting rectification progress event to session {session_id}: {e}")
        return False
