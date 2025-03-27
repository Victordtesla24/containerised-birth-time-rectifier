"""
Shared WebSocket Events Module

This module provides common WebSocket event emission functions
that can be used by both the AI service and API Gateway.
"""

import logging
import json
import time
import uuid
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Any, List, Optional, Union, Callable

from ai_service.utils.websocket_manager import get_websocket_manager, WebSocketManager

# Configure logging
logger = logging.getLogger(__name__)

class EventType(Enum):
    """Event types for WebSocket communication"""
    # Connection events
    CONNECT = auto()
    DISCONNECT = auto()
    MESSAGE = auto()

    # Geocoding events
    GEOCODE_STARTED = auto()
    GEOCODE_COMPLETED = auto()
    REVERSE_GEOCODE_COMPLETED = auto()

    # Chart events
    BIRTH_CHART_STARTED = auto()
    BIRTH_CHART_COMPLETED = auto()
    BIRTH_CHART_ERROR = auto()
    CHART_RETRIEVED = auto()
    VALIDATION_STARTED = auto()
    VALIDATION_COMPLETED = auto()
    VALIDATION_ERROR = auto()

    # Rectification events
    RECTIFICATION_STARTED = auto()
    RECTIFICATION_PROGRESS = auto()
    RECTIFICATION_COMPLETED = auto()
    RECTIFICATION_ERROR = auto()

    # Questionnaire events
    QUESTIONNAIRE_STARTED = auto()
    QUESTIONNAIRE_COMPLETED = auto()
    QUESTIONNAIRE_QUESTION = auto()
    QUESTIONNAIRE_ANSWER = auto()
    QUESTION_ANSWERED = auto()
    QUESTIONNAIRE_ERROR = auto()

    # General events
    GENERAL_ERROR = auto()
    GENERAL_INFO = auto()

    # Status updates
    STATUS_UPDATE = auto()
    PROGRESS_UPDATE = auto()

    # Chart verification events
    VERIFICATION_STARTED = auto()
    VERIFICATION_PROGRESS = auto()
    VERIFICATION_COMPLETED = auto()
    VERIFICATION_ERROR = auto()

    # Session events
    SESSION_CREATED = auto()
    SESSION_UPDATED = auto()
    SESSION_EXPIRED = auto()

    # System events
    SYSTEM_MESSAGE = auto()
    HEARTBEAT = auto()

async def emit_event(session_id: str, event_type: Union[str, EventType], data: Dict[str, Any]) -> bool:
    """
    Emit an event to a specific session.

    Args:
        session_id: The session ID to emit to
        event_type: The type of event
        data: The event data

    Returns:
        True if the event was successfully emitted, False otherwise
    """
    # Get the WebSocket manager
    manager = get_websocket_manager()

    # Normalize event type to string
    event_type_str = event_type.name if isinstance(event_type, EventType) else str(event_type)

    # Create event payload
    event_payload = {
        "type": event_type_str.lower(),
        "timestamp": datetime.now().isoformat(),
        "event_id": str(uuid.uuid4()),
        "data": data
    }

    # Send the event
    try:
        result = await manager.send_update(session_id, event_payload)
        logger.info(f"Emitted {event_type_str} event to session {session_id}")
        return result
    except Exception as e:
        logger.error(f"Error emitting {event_type_str} event to session {session_id}: {e}")
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
    Emit a rectification progress event to a client.

    Args:
        session_id: The session ID to emit to
        progress: The progress percentage (0-100)
        message: The progress message
        chart_id: The chart ID being rectified
        status: Status of rectification (processing, completed, error)
        result: Optional result data if rectification is complete

    Returns:
        True if the event was successfully emitted, False otherwise
    """
    # Validate progress
    progress = max(0, min(100, progress))

    # Determine the stage based on progress
    stage_info = get_stage_info(progress)

    # Calculate estimated time remaining
    remaining_seconds = _calculate_estimated_time(progress)
    time_remaining = format_time_remaining(int(remaining_seconds))

    # Create event data
    event_data = {
        "progress": progress,
        "message": message,
        "chart_id": chart_id,
        "status": status,
        "stage": stage_info["name"],
        "stage_description": stage_info["description"],
        "time_remaining": time_remaining
    }

    # Add result if provided and status is completed
    if status == "completed" and result:
        event_data["result"] = extract_result_summary(result)

    # Emit the event
    return await emit_event(session_id, EventType.RECTIFICATION_PROGRESS, event_data)

async def emit_rectification_complete(
    session_id: str,
    chart_id: str,
    rectification_id: str,
    result: Dict[str, Any]
) -> bool:
    """
    Emit a rectification complete event to a client.

    Args:
        session_id: The session ID to emit to
        chart_id: The chart ID that was rectified
        rectification_id: The rectification ID
        result: The rectification result data

    Returns:
        True if the event was successfully emitted, False otherwise
    """
    # Extract key data for the event
    summary = extract_result_summary(result)

    # Create event data
    event_data = {
        "chart_id": chart_id,
        "rectification_id": rectification_id,
        "progress": 100,
        "status": "completed",
        "result": summary,
        "message": "Rectification completed successfully"
    }

    # Emit the event
    return await emit_event(session_id, EventType.RECTIFICATION_COMPLETED, event_data)

async def emit_rectification_error(
    session_id: str,
    chart_id: str,
    error_message: str,
    error_code: str = "RECTIFICATION_ERROR"
) -> bool:
    """
    Emit a rectification error event to a client.

    Args:
        session_id: The session ID to emit to
        chart_id: The chart ID that was being rectified
        error_message: The error message
        error_code: The error code

    Returns:
        True if the event was successfully emitted, False otherwise
    """
    # Create event data
    event_data = {
        "chart_id": chart_id,
        "status": "error",
        "error_code": error_code,
        "message": error_message
    }

    # Emit the event
    return await emit_event(session_id, EventType.RECTIFICATION_ERROR, event_data)

async def emit_error(
    session_id: str,
    error_code: str,
    error_message: str,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Emit a general error event to a client.

    Args:
        session_id: The session ID to emit to
        error_code: The error code
        error_message: The error message
        details: Optional error details

    Returns:
        True if the event was successfully emitted, False otherwise
    """
    # Create event data with error basics
    event_data = {
        "status": "error",
        "error_code": error_code,
        "message": error_message
    }

    # Create a completely new data structure that includes both
    # the basic error info and the details if provided
    if details:
        # Create a separate message that includes both basic info and details
        detailed_data = {
            "basic_error": {
                "code": error_code,
                "message": error_message
            },
            "details": json.dumps(details)  # Convert to JSON string
        }
        # Emit as a different event type that expects this structure
        return await emit_event(session_id, "detailed_error", detailed_data)

    # If no details, just emit the regular error event
    return await emit_event(session_id, EventType.GENERAL_ERROR, event_data)

async def broadcast_system_message(message: str, level: str = "info") -> Dict[str, bool]:
    """
    Broadcast a system message to all connected clients.

    Args:
        message: The message to broadcast
        level: The message level (info, warning, error)

    Returns:
        Dictionary mapping session IDs to success status
    """
    # Get the WebSocket manager
    manager = get_websocket_manager()

    # Create the message data
    message_data = {
        "text": message,
        "level": level,
        "timestamp": datetime.now().isoformat()
    }

    # For each active connection, emit the event
    result = {}
    for session_id in manager.active_connections.keys():
        # Type ignore needed due to persistent linter error with Dict assignment
        success = await emit_event(session_id, "system_message", message_data)  # type: ignore
        result[session_id] = success

    return result

def extract_result_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a summary of rectification results for WebSocket events.

    Args:
        result: The full rectification result

    Returns:
        A summary of the results
    """
    summary = {}

    # Extract key fields if they exist
    if "original_time" in result:
        summary["original_time"] = result["original_time"]
    if "rectified_time" in result:
        summary["rectified_time"] = result["rectified_time"]
    if "confidence" in result:
        summary["confidence"] = result["confidence"]
    if "adjustment_minutes" in result:
        summary["adjustment_minutes"] = result["adjustment_minutes"]
    if "explanation" in result:
        # Truncate explanation if it's too long
        explanation = result["explanation"]
        if len(explanation) > 500:
            summary["explanation"] = explanation[:497] + "..."
        else:
            summary["explanation"] = explanation

    # Add rectified chart ID if available
    if "rectified_chart_id" in result:
        summary["rectified_chart_id"] = result["rectified_chart_id"]

    return summary

def get_stage_info(progress: int) -> Dict[str, str]:
    """
    Get information about the current rectification stage based on progress.

    Args:
        progress: The progress percentage (0-100)

    Returns:
        Dictionary with stage name and description
    """
    if progress < 10:
        return {
            "name": "initialization",
            "description": "Preparing birth chart and initializing rectification"
        }
    elif progress < 25:
        return {
            "name": "analyzing_events",
            "description": "Analyzing life events and birth time indicators"
        }
    elif progress < 50:
        return {
            "name": "calculating_candidates",
            "description": "Calculating and evaluating candidate birth times"
        }
    elif progress < 75:
        return {
            "name": "evaluating_transits",
            "description": "Evaluating planetary transits for key life events"
        }
    elif progress < 90:
        return {
            "name": "verifying_results",
            "description": "Verifying rectification results"
        }
    else:
        return {
            "name": "finalizing",
            "description": "Finalizing rectified birth chart"
        }

def format_time_remaining(seconds_remaining: Union[int, float]) -> Dict[str, Union[int, str, float]]:
    """
    Format time remaining for progress updates.

    Args:
        seconds_remaining: Seconds remaining (can be int or float)

    Returns:
        Dictionary with formatted time remaining
    """
    # Convert to int for calculations
    seconds_int = int(seconds_remaining)

    if seconds_int <= 0:
        return {
            "text": "Almost done",
            "seconds": 0
        }

    minutes, seconds = divmod(seconds_int, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        text = f"{hours}h {minutes}m remaining"
    elif minutes > 0:
        text = f"{minutes}m {seconds}s remaining"
    else:
        text = f"{seconds}s remaining"

    return {
        "text": text,
        "seconds": seconds_int,
        "minutes": minutes + (hours * 60),
        "hours": hours
    }

def _calculate_estimated_time(progress: int) -> float:
    """
    Calculate estimated time remaining based on progress.

    Args:
        progress: The progress percentage (0-100)

    Returns:
        Estimated seconds remaining
    """
    if progress >= 100:
        return 0

    # Simple estimation based on typical rectification time of 3 minutes
    total_time = 180  # 3 minutes in seconds
    remaining_percentage = (100 - progress) / 100
    return total_time * remaining_percentage
