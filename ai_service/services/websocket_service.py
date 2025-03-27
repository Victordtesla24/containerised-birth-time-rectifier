"""
WebSocket Service for Birth Time Rectifier

This module provides a WebSocket service for real-time communication
with clients, including progress updates for long-running processes.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from fastapi import WebSocket
from starlette.websockets import WebSocketState

# Import the shared WebSocket manager and events
from ai_service.utils.websocket_manager import WebSocketManager, get_websocket_manager
from ai_service.utils.websocket_events import (
    emit_event,
    emit_rectification_progress,
    emit_rectification_complete,
    emit_rectification_error,
    EventType
)

logger = logging.getLogger(__name__)

class WebSocketService:
    """
    WebSocket service for managing client connections and sending updates.

    This service uses the canonical WebSocketManager implementation and
    delegates all event emission to the shared websocket_events module.
    """

    def __init__(self):
        """Initialize the WebSocket service."""
        # Use the shared WebSocketManager
        self.manager = get_websocket_manager()
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Accept a WebSocket connection and register it.

        Args:
            websocket: The WebSocket connection
            session_id: The session ID to associate with this connection
        """
        try:
            # Use the canonical WebSocketManager
            await self.manager.connect(websocket, session_id)

            # Keep track of connections locally as well
            self.active_connections[session_id] = websocket

            # Initialize session data if needed
            if session_id not in self.session_data:
                self.session_data[session_id] = {
                    "connected_at": datetime.now().isoformat(),
                    "progress_history": []
                }
            else:
                self.session_data[session_id]["reconnected_at"] = datetime.now().isoformat()

            logger.info(f"WebSocket connection established for session {session_id}")

            # Resend progress history if available
            await self.resend_progress_history(session_id)
        except Exception as e:
            logger.error(f"Error connecting WebSocket for session {session_id}: {e}")

    def disconnect(self, session_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            session_id: The session ID of the connection to remove
        """
        # Use the canonical WebSocketManager
        self.manager.disconnect(session_id)

        # Update local tracking
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            if session_id in self.session_data:
                self.session_data[session_id]["disconnected_at"] = datetime.now().isoformat()

        logger.info(f"WebSocket connection closed for session {session_id}")

    async def send_message(self, session_id: str, message_type: str, data: Dict[str, Any]) -> bool:
        """
        Send a message to a specific client.

        Args:
            session_id: The session ID to send the message to
            message_type: The type of message to send
            data: The message data

        Returns:
            True if the message was sent successfully, False otherwise
        """
        # Use the shared emit_event function
        return await emit_event(session_id, message_type, data)

    async def resend_progress_history(self, session_id: str) -> bool:
        """
        Resend progress history to a client after reconnection.

        Args:
            session_id: Session identifier for the client

        Returns:
            True if history was resent successfully, False otherwise
        """
        if session_id not in self.session_data or "progress_history" not in self.session_data[session_id]:
            logger.info(f"No progress history available for session {session_id}")
            return False

        progress_history = self.session_data[session_id]["progress_history"]
        if not progress_history:
            return True

        # Send all history events with a special flag
        success = True
        for progress_event in progress_history:
            event_data = {**progress_event, "is_history": True}
            if not await emit_event(session_id, "rectification_progress_history", event_data):
                success = False

        # Send the current status based on the most recent event
        latest = progress_history[-1]
        await emit_event(
            session_id,
            "rectification_current_status",
            {
                "progress": latest["progress"],
                "message": latest["message"],
                "status": latest["status"],
                "timestamp": latest["timestamp"]
            }
        )

        return success

    async def broadcast_rectification_status(
        self,
        chart_id: str,
        status_data: Dict[str, Any]
    ) -> Dict[str, bool]:
        """
        Broadcast a rectification status update to all connected clients.

        Args:
            chart_id: ID of the chart being rectified
            status_data: Status data to broadcast, containing:
                - status: Current status (e.g., "started", "analyzing", "completed")
                - message: Status message
                - progress: Progress percentage (0-100)
                - details: Optional detailed status information

        Returns:
            Dictionary mapping session IDs to success/failure status
        """
        if not chart_id:
            logger.error("Missing chart_id for rectification status broadcast")
            return {}

        # Ensure required fields are in status_data
        required_fields = ["status", "message"]
        for field in required_fields:
            if field not in status_data:
                logger.error(f"Missing required field '{field}' in status_data")
                return {}

        # Ensure progress is provided and within valid range
        progress = status_data.get("progress", 0)
        status_data["progress"] = max(0, min(100, progress))

        # Add timestamp and channel information
        status_data["timestamp"] = datetime.now().isoformat()
        status_data["channel"] = f"rectification:{chart_id}"
        status_data["chart_id"] = chart_id
        status_data["type"] = "rectification_status"

        # Add a unique sequence ID for message ordering
        status_data["sequence_id"] = str(uuid.uuid4())

        # Broadcast to all connected clients
        results = {}
        for session_id in self.active_connections:
            try:
                success = await emit_event(session_id, "rectification_status", status_data)
                results[session_id] = success

                if success:
                    logger.debug(f"Broadcast rectification status to session {session_id}")
                else:
                    logger.warning(f"Failed to broadcast rectification status to session {session_id}")
            except Exception as e:
                logger.error(f"Error broadcasting rectification status to session {session_id}: {e}")
                results[session_id] = False

        # Log summary of broadcast results
        success_count = sum(1 for success in results.values() if success)
        logger.info(f"Broadcast rectification status to {success_count}/{len(results)} connected clients")

        return results

    async def broadcast_message(self, message_type: str, data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Broadcast a message to all connected clients.

        Args:
            message_type: Type of message
            data: Message payload

        Returns:
            Dictionary mapping session IDs to send success status
        """
        results = {}
        for session_id in self.active_connections:
            results[session_id] = await emit_event(session_id, message_type, data)
        return results

# Singleton instance
_websocket_service = None

def get_websocket_service() -> WebSocketService:
    """
    Get the WebSocket service singleton instance.

    Returns:
        The WebSocket service instance
    """
    global _websocket_service
    if _websocket_service is None:
        _websocket_service = WebSocketService()
    return _websocket_service
