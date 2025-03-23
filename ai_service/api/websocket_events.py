"""
WebSocket Event Emitter for Birth Time Rectifier API

This module provides functions for emitting events to WebSocket clients.
It defines event types and provides a consistent interface for sending
real-time updates during long-running processes.
"""

from enum import Enum, auto
from typing import Dict, Any, Optional, List, Set, Union
import logging
import asyncio
import json
from datetime import datetime, timedelta
import uuid

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

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

class WebSocketManager:
    """Manager for WebSocket connections."""

    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict[str, Any]] = {}
        self.session_subscriptions: Dict[str, Set[str]] = {}
        self.channel_subscribers: Dict[str, Set[str]] = {}
        self.reconnection_tokens: Dict[str, str] = {}
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self.sessions: Dict[str, WebSocket] = {}
        logger.info("WebSocket manager initialized")

    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        """
        Register a WebSocket connection.

        Args:
            websocket: WebSocket connection
            session_id: Session identifier

        Returns:
            True if connection was accepted, False otherwise
        """
        try:
            await websocket.accept()
            self.active_connections[session_id] = websocket
            self.sessions[session_id] = websocket
            self.session_data[session_id] = {
                "connected_at": datetime.now().isoformat(),
                "last_message": datetime.now().isoformat(),
                "user_agent": getattr(websocket, "headers", {}).get("user-agent", "Unknown"),
                "ip": getattr(websocket, "client", {}).get("host", "Unknown"),
                "subscriptions": []
            }
            self.session_subscriptions[session_id] = set()

            # Generate reconnection token
            reconnection_token = str(uuid.uuid4())
            self.reconnection_tokens[session_id] = reconnection_token

            # Start health check task
            self.health_check_tasks[session_id] = asyncio.create_task(
                self._health_check(session_id, websocket)
            )

            logger.info(f"Client connected: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            return False

    async def disconnect(self, session_id: str) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            session_id: Session identifier
        """
        # Remove from active connections
        if session_id in self.active_connections:
            # Get WebSocket connection
            websocket = self.active_connections[session_id]

            # Try to close WebSocket gracefully
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket for session {session_id}: {e}")

            # Remove from active connections
            self.active_connections.pop(session_id, None)

        # Remove from sessions
        self.sessions.pop(session_id, None)

        # Clean up health check task
        if session_id in self.health_check_tasks:
            task = self.health_check_tasks.pop(session_id)
            if not task.done():
                task.cancel()

        # Remove subscriptions
        if session_id in self.session_subscriptions:
            subscriptions = self.session_subscriptions.pop(session_id, set())

            # Remove session from channel subscribers
            for channel in subscriptions:
                if channel in self.channel_subscribers:
                    self.channel_subscribers[channel].discard(session_id)

                    # Remove channel if no subscribers left
                    if not self.channel_subscribers[channel]:
                        self.channel_subscribers.pop(channel, None)

        # Keep session data for reconnection
        if session_id in self.session_data:
            self.session_data[session_id]["disconnected_at"] = datetime.now().isoformat()
            self.session_data[session_id]["connected"] = False

        logger.info(f"Client disconnected: {session_id}")

    async def send_update(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a client.

        Args:
            session_id: Session identifier
            message: Message to send

        Returns:
            True if message was sent, False otherwise
        """
        if session_id not in self.active_connections:
            logger.warning(f"Attempt to send message to unknown session: {session_id}")
            return False

        websocket = self.active_connections[session_id]

        try:
            # Add message ID
            if "id" not in message:
                message["id"] = str(uuid.uuid4())

            # Add timestamp
            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()

            # Send message
            await websocket.send_json(message)

            # Update last message time
            if session_id in self.session_data:
                self.session_data[session_id]["last_message"] = datetime.now().isoformat()

            return True
        except WebSocketDisconnect:
            logger.warning(f"WebSocket disconnected while sending message to session {session_id}")
            await self.disconnect(session_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to session {session_id}: {e}")
            return False

    async def broadcast(self, message: Dict[str, Any], exclude: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message to broadcast
            exclude: Optional list of session IDs to exclude

        Returns:
            Dictionary mapping session IDs to send status
        """
        exclude = exclude or []
        results = {}

        for session_id, websocket in self.active_connections.items():
            if session_id in exclude:
                continue

            try:
                # Add message ID if not present
                message_copy = message.copy()
                if "id" not in message_copy:
                    message_copy["id"] = str(uuid.uuid4())

                # Add timestamp if not present
                if "timestamp" not in message_copy:
                    message_copy["timestamp"] = datetime.now().isoformat()

                # Send message
                await websocket.send_json(message_copy)
                results[session_id] = True

                # Update last message time
                if session_id in self.session_data:
                    self.session_data[session_id]["last_message"] = datetime.now().isoformat()
            except WebSocketDisconnect:
                logger.warning(f"WebSocket disconnected while broadcasting to session {session_id}")
                await self.disconnect(session_id)
                results[session_id] = False
            except Exception as e:
                logger.error(f"Error broadcasting message to session {session_id}: {e}")
                results[session_id] = False

        return results

    async def subscribe(self, session_id: str, channel: str) -> bool:
        """
        Subscribe a client to a channel.

        Args:
            session_id: Session identifier
            channel: Channel to subscribe to

        Returns:
            True if subscription was successful, False otherwise
        """
        if session_id not in self.active_connections:
            logger.warning(f"Attempt to subscribe unknown session {session_id} to channel {channel}")
            return False

        # Add session to channel subscribers
        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()

        self.channel_subscribers[channel].add(session_id)

        # Add channel to session subscriptions
        if session_id not in self.session_subscriptions:
            self.session_subscriptions[session_id] = set()

        self.session_subscriptions[session_id].add(channel)

        # Update session data
        if session_id in self.session_data:
            if "subscriptions" not in self.session_data[session_id]:
                self.session_data[session_id]["subscriptions"] = []

            if channel not in self.session_data[session_id]["subscriptions"]:
                self.session_data[session_id]["subscriptions"].append(channel)

        logger.info(f"Session {session_id} subscribed to channel {channel}")
        return True

    async def unsubscribe(self, session_id: str, channel: str) -> bool:
        """
        Unsubscribe a client from a channel.

        Args:
            session_id: Session identifier
            channel: Channel to unsubscribe from

        Returns:
            True if unsubscription was successful, False otherwise
        """
        # Remove session from channel subscribers
        if channel in self.channel_subscribers:
            self.channel_subscribers[channel].discard(session_id)

            # Remove channel if no subscribers left
            if not self.channel_subscribers[channel]:
                self.channel_subscribers.pop(channel, None)

        # Remove channel from session subscriptions
        if session_id in self.session_subscriptions:
            self.session_subscriptions[session_id].discard(channel)

        # Update session data
        if session_id in self.session_data and "subscriptions" in self.session_data[session_id]:
            if channel in self.session_data[session_id]["subscriptions"]:
                self.session_data[session_id]["subscriptions"].remove(channel)

        logger.info(f"Session {session_id} unsubscribed from channel {channel}")
        return True

    async def publish_to_channel(self, channel: str, message: Dict[str, Any]) -> Dict[str, bool]:
        """
        Publish a message to a channel.

        Args:
            channel: Channel to publish to
            message: Message to publish

        Returns:
            Dictionary mapping session IDs to send status
        """
        if channel not in self.channel_subscribers:
            logger.warning(f"Attempt to publish to channel with no subscribers: {channel}")
            return {}

        results = {}

        for session_id in self.channel_subscribers[channel]:
            if session_id not in self.active_connections:
                continue

            try:
                # Add message ID if not present
                message_copy = message.copy()
                if "id" not in message_copy:
                    message_copy["id"] = str(uuid.uuid4())

                # Add timestamp if not present
                if "timestamp" not in message_copy:
                    message_copy["timestamp"] = datetime.now().isoformat()

                # Add channel
                message_copy["channel"] = channel

                # Send message
                await self.active_connections[session_id].send_json(message_copy)
                results[session_id] = True

                # Update last message time
                if session_id in self.session_data:
                    self.session_data[session_id]["last_message"] = datetime.now().isoformat()
            except WebSocketDisconnect:
                logger.warning(f"WebSocket disconnected while publishing to session {session_id}")
                await self.disconnect(session_id)
                results[session_id] = False
            except Exception as e:
                logger.error(f"Error publishing message to session {session_id}: {e}")
                results[session_id] = False

        return results

    async def _health_check(self, session_id: str, websocket: WebSocket) -> None:
        """
        Perform periodic health check for a WebSocket connection.

        Args:
            session_id: Session identifier
            websocket: WebSocket connection
        """
        try:
            health_check_interval = 30  # seconds
            missed_checks = 0
            max_missed_checks = 3

            while session_id in self.active_connections and websocket in self.active_connections.values():
                try:
                    # Send ping message
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.now().isoformat(),
                        "id": str(uuid.uuid4())
                    })

                    # Wait for health check interval
                    await asyncio.sleep(health_check_interval)

                    # Reset missed checks if successful
                    missed_checks = 0
                except WebSocketDisconnect:
                    logger.warning(f"WebSocket disconnected during health check for session {session_id}")
                    await self.disconnect(session_id)
                    break
                except Exception as e:
                    logger.error(f"Error during health check for session {session_id}: {e}")
                    missed_checks += 1

                    # Disconnect if too many missed checks
                    if missed_checks >= max_missed_checks:
                        logger.warning(f"Too many missed health checks for session {session_id}, disconnecting")
                        await self.disconnect(session_id)
                        break

                    # Wait before retrying
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info(f"Health check task cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Unexpected error in health check task for session {session_id}: {e}")
            await self.disconnect(session_id)

async def get_manager() -> WebSocketManager:
    """
    Get the WebSocket manager instance.

    Returns:
        WebSocket manager instance
    """
    global manager
    if not isinstance(manager, WebSocketManager):
        manager = WebSocketManager()
    return manager

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
        chart_id: The chart ID
        status: The status (processing, complete, error)
        result: Optional result data

    Returns:
        True if the event was emitted successfully, False otherwise
    """
    ws_mgr = await get_manager()

    # Create event payload
    data = {
        "type": "rectification_progress",
        "chart_id": chart_id,
        "progress": progress,
        "message": message,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }

    if result:
        data["result"] = extract_result_summary(result)

    # Add stage information based on progress
    stage_info = get_stage_info(progress)
    data["stage"] = stage_info["stage"]
    data["stage_description"] = stage_info["description"]

    # Add estimated time remaining if available
    if isinstance(result, dict) and "estimated_seconds_remaining" in result:
        time_data = format_time_remaining(result["estimated_seconds_remaining"])
        data["time_remaining"] = time_data

    # Emit the event
    success = await ws_mgr.send_update(session_id, data)
    return success

async def emit_rectification_complete(
    session_id: str,
    chart_id: str,
    rectification_id: str,
    result: Dict[str, Any]
) -> bool:
    """
    Emit a rectification complete event to a WebSocket client.

    Args:
        session_id: The session ID of the client
        chart_id: The chart ID that was rectified
        rectification_id: The ID of the rectification process
        result: The rectification result data

    Returns:
        bool: True if the event was sent, False otherwise
    """
    try:
        # Create the event payload
        payload = {
            "type": "rectification_complete",
            "status": "complete",
            "progress": 100,
            "chart_id": chart_id,
            "rectification_id": rectification_id,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "channel": f"rectification:{chart_id}"
        }

        # Get WebSocket manager
        ws_manager = await get_manager()

        # Send the event
        success = await ws_manager.send_update(session_id, payload)

        if success:
            logger.info(f"Emitted rectification complete event to session {session_id}")
        else:
            logger.warning(f"Failed to emit rectification complete event to session {session_id}")

        return success
    except Exception as e:
        logger.error(f"Error emitting rectification complete event to session {session_id}: {e}")
        return False

async def emit_error(
    session_id: str,
    error_code: str,
    error_message: str,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Emit an error event to a WebSocket client.

    Args:
        session_id: The session ID of the client
        error_code: The error code
        error_message: The error message
        details: Optional error details

    Returns:
        bool: True if the event was sent, False otherwise
    """
    try:
        # Create the event payload
        payload = {
            "type": "error",
            "error": {
                "code": error_code,
                "message": error_message
            },
            "timestamp": datetime.now().isoformat()
        }

        # Add details if provided
        if details:
            payload["error"]["details"] = details

        # Get WebSocket manager
        ws_manager = await get_manager()

        # Send the event
        success = await ws_manager.send_update(session_id, payload)

        if success:
            logger.info(f"Emitted error event to session {session_id}: {error_code}")
        else:
            logger.warning(f"Failed to emit error event to session {session_id}")

        return success
    except Exception as e:
        logger.error(f"Error emitting error event to session {session_id}: {e}")
        return False

async def broadcast_system_message(message: str, level: str = "info") -> Dict[str, bool]:
    """
    Broadcast a system message to all connected clients.

    Args:
        message: The message to broadcast
        level: The message level (info, warning, error)

    Returns:
        Dictionary mapping session IDs to send status
    """
    try:
        # Create the event payload
        payload = {
            "type": "system_message",
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }

        # Get WebSocket manager
        ws_manager = await get_manager()

        # Broadcast the message
        results = await ws_manager.broadcast(payload)

        logger.info(f"Broadcast system message to {len(results)} clients")
        return results
    except Exception as e:
        logger.error(f"Error broadcasting system message: {e}")
        return {}

def extract_result_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key summary information from rectification results.

    Args:
        result: Complete rectification result data

    Returns:
        Summary of the most important result data
    """
    if not result or not isinstance(result, dict):
        return {}

    # Extract only necessary fields to keep message size manageable
    summary = {}
    key_fields = [
        "rectified_time", "confidence_score", "chart_id",
        "original_time", "time_difference", "rectification_method",
        "primary_factors", "summary"
    ]

    for field in key_fields:
        if field in result:
            summary[field] = result[field]

    # Ensure we have at least a minimal set of fields
    if "rectified_time" not in summary and "time" in result:
        summary["rectified_time"] = result["time"]

    if "confidence_score" not in summary and "confidence" in result:
        summary["confidence_score"] = result["confidence"]

    return summary

def get_stage_info(progress: int) -> Dict[str, str]:
    """
    Get stage information based on progress percentage.

    Args:
        progress: Current progress percentage (0-100)

    Returns:
        Dictionary with stage name and description
    """
    if progress < 20:
        return {
            "stage": "initialization",
            "description": "Setting up rectification process and analyzing birth data"
        }
    elif progress < 40:
        return {
            "stage": "analysis",
            "description": "Analyzing astrological factors and life events"
        }
    elif progress < 60:
        return {
            "stage": "calculation",
            "description": "Calculating potential birth time candidates"
        }
    elif progress < 80:
        return {
            "stage": "verification",
            "description": "Verifying potential birth times against astrological rules"
        }
    else:
        return {
            "stage": "finalization",
            "description": "Finalizing rectified birth time and generating chart"
        }

def format_time_remaining(seconds_remaining: int) -> Dict[str, Union[int, str]]:
    """
    Format time remaining for progress updates.

    Args:
        seconds_remaining: Estimated seconds remaining

    Returns:
        Dictionary with formatted time remaining information
    """
    # Define with explicit typing
    time_info: Dict[str, Union[int, str]] = {
        "seconds": seconds_remaining
    }

    # Add human-readable time estimate
    if seconds_remaining < 60:
        time_info["text"] = "Less than a minute remaining"
    elif seconds_remaining < 120:
        time_info["text"] = "About a minute remaining"
    elif seconds_remaining < 3600:
        minutes = seconds_remaining // 60
        time_info["text"] = f"About {minutes} minutes remaining"
    else:
        hours = seconds_remaining // 3600
        minutes = (seconds_remaining % 3600) // 60
        if minutes > 0:
            time_info["text"] = f"About {hours} hour{'s' if hours > 1 else ''} and {minutes} minute{'s' if minutes > 1 else ''} remaining"
        else:
            time_info["text"] = f"About {hours} hour{'s' if hours > 1 else ''} remaining"

    # Add estimated completion time
    completion_time = datetime.now() + timedelta(seconds=seconds_remaining)
    time_info["estimated_completion_time"] = completion_time.isoformat()

    return time_info
