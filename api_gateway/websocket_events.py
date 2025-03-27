"""
WebSocket Events for Birth Time Rectifier API Gateway

This module provides functions for emitting events to WebSocket clients
through the canonical WebSocketEvents implementation from AI service.
"""

from typing import Dict, Any, Optional, Union
import logging

# Import the shared WebSocket events implementation
from ai_service.utils.websocket_events import (
    emit_event,
    emit_rectification_progress,
    emit_rectification_complete,
    emit_rectification_error,
    emit_error,
    broadcast_system_message,
    EventType
)

# Configure logging
logger = logging.getLogger("api_gateway.websocket_events")

# Re-export the canonical functions
__all__ = [
    "emit_event",
    "emit_rectification_progress",
    "emit_rectification_complete",
    "emit_rectification_error",
    "emit_error",
    "broadcast_system_message",
    "EventType"
]
