"""
WebSocket Connection Manager for Birth Time Rectifier API

This module provides the core WebSocket functionality for real-time updates
across the entire application. This is the canonical implementation that should
be used by all services requiring WebSocket functionality.
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Any, Optional, Set
import logging
import json
import uuid
import time
from datetime import datetime
from starlette.websockets import WebSocketState
import asyncio
import traceback

# Configure logging
logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    WebSocket connection manager for handling real-time updates.

    This class manages WebSocket connections and provides methods
    for sending updates to specific clients or broadcasting to all.
    """

    def __init__(self):
        """Initialize the connection manager with an empty connections dictionary."""
        # Store active connections by session ID
        self.active_connections: Dict[str, WebSocket] = {}
        # Store client metadata
        self.client_metadata: Dict[str, Dict[str, Any]] = {}
        # Store message queues for disconnected clients
        self.message_queues: Dict[str, List[Dict[str, Any]]] = {}
        # Store channel subscriptions
        self.channel_subscribers: Dict[str, Set[str]] = {}
        # Dictionary mapping session ID to subscribed channels
        self.subscriptions: Dict[str, Set[str]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        # Connection tracking with timestamps
        self.connection_states: Dict[str, Dict[str, Any]] = {}
        # Automatic cleanup task
        self.cleanup_task = None
        # Pre-authorized sessions
        self.authorized_sessions = set()

    def register_session(self, session_id: str) -> None:
        """
        Pre-register a session as authorized to connect.
        This allows the AI service to accept connections for sessions that were
        authenticated by the API Gateway.

        Args:
            session_id: The session ID to authorize
        """
        self.authorized_sessions.add(session_id)
        logger.info(f"Pre-registered session for WebSocket connection: {session_id}")

    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        """
        Register a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to register
            session_id: The session ID for this connection

        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            async with self._lock:
                # Check if this session already has a connection
                if session_id in self.active_connections:
                    # Handle reconnection - close old connection if possible
                    old_websocket = self.active_connections[session_id]
                    if old_websocket != websocket:
                        logger.warning(f"Session {session_id} already has an active connection. Replacing.")
                        try:
                            await old_websocket.close(code=1000)
                        except Exception as e:
                            logger.warning(f"Error closing existing connection for {session_id}: {e}")

                # Store the new connection
                self.active_connections[session_id] = websocket

                # Initialize or update connection state
                self.connection_states[session_id] = {
                    "connected_at": datetime.now().isoformat(),
                    "last_activity": time.time(),
                    "messages_sent": 0,
                    "messages_received": 0,
                    "subscriptions": list(self.subscriptions.get(session_id, set()))
                }

                # Start cleanup task if not running
                if self.cleanup_task is None or self.cleanup_task.done():
                    self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

                # If this session was pre-registered, remove it from authorized_sessions
                # since it's now an active connection
                if session_id in self.authorized_sessions:
                    self.authorized_sessions.remove(session_id)

                logger.info(f"WebSocket connection established for session {session_id}")
                return True

        except Exception as e:
            logger.error(f"Error connecting WebSocket for session {session_id}: {e}")
            logger.error(traceback.format_exc())
            return False

    def disconnect(self, session_id: str) -> None:
        """
        Unregister a WebSocket connection.

        Args:
            session_id: The session ID to unregister
        """
        try:
            # Fast path without lock for non-existent sessions
            if session_id not in self.active_connections:
                return

            # Properly remove the connection with lock
            asyncio.create_task(self._disconnect_with_lock(session_id))
        except Exception as e:
            logger.error(f"Error in disconnect for session {session_id}: {e}")

    async def _disconnect_with_lock(self, session_id: str) -> None:
        """Helper method to disconnect with proper locking."""
        async with self._lock:
            if session_id in self.active_connections:
                # Update disconnection time in state tracking
                if session_id in self.connection_states:
                    self.connection_states[session_id]["disconnected_at"] = datetime.now().isoformat()

                # Remove connection
                self.active_connections.pop(session_id, None)
                logger.info(f"WebSocket connection closed for session {session_id}")

    def get_websocket(self, session_id: str) -> Optional[WebSocket]:
        """
        Get the WebSocket connection for a session.

        Args:
            session_id: The session ID to get the connection for

        Returns:
            WebSocket connection or None if not found
        """
        return self.active_connections.get(session_id)

    async def send_update(self, session_id: str, data: Any) -> bool:
        """
        Send an update to a specific client.

        Args:
            session_id: The session ID of the client
            data: The data to send (will be converted to JSON)

        Returns:
            bool: True if the update was sent, False if the session was not found
        """
        # Add message ID and timestamp if not present
        if isinstance(data, dict):
            if "message_id" not in data:
                data["message_id"] = str(uuid.uuid4())
            if "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()

        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                # Check if the connection is still open
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(data)

                    # Update activity timestamp
                    if session_id in self.connection_states:
                        self.connection_states[session_id]["last_activity"] = time.time()
                        self.connection_states[session_id]["messages_sent"] += 1

                    logger.info(f"Update sent to session {session_id}")
                    return True
                else:
                    logger.warning(f"WebSocket for session {session_id} is in state {websocket.client_state}")
                    self.disconnect(session_id)
                    # Queue message for reconnection
                    self._queue_message(session_id, data)
                    return False
            except Exception as e:
                logger.error(f"Error sending update to session {session_id}: {e}")
                # Connection might be broken, remove it
                self.disconnect(session_id)
                # Queue message for reconnection
                self._queue_message(session_id, data)
                return False
        else:
            logger.warning(f"Attempted to send update to unknown session {session_id}")
            # Queue message for this session
            self._queue_message(session_id, data)
            return False

    def _queue_message(self, session_id: str, data: Any) -> None:
        """Queue a message for a disconnected client."""
        if session_id not in self.message_queues:
            self.message_queues[session_id] = []
        self.message_queues[session_id].append(data)
        logger.info(f"Message queued for session {session_id}")

    async def broadcast(self, data: Any, exclude: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Broadcast an update to all connected clients.

        Args:
            data: The data to broadcast (will be converted to JSON)
            exclude: List of session IDs to exclude from broadcast

        Returns:
            Dict mapping session IDs to success status
        """
        # Add message ID and timestamp if not present
        if isinstance(data, dict):
            if "message_id" not in data:
                data["message_id"] = str(uuid.uuid4())
            if "timestamp" not in data:
                data["timestamp"] = datetime.now().isoformat()

        exclude_list = exclude or []
        disconnected_sessions = []
        success_map = {}

        for session_id, connection in self.active_connections.items():
            if session_id in exclude_list:
                continue

            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(data)
                    success_map[session_id] = True

                    # Update activity timestamp
                    if session_id in self.connection_states:
                        self.connection_states[session_id]["last_activity"] = time.time()
                        self.connection_states[session_id]["messages_sent"] += 1
                else:
                    disconnected_sessions.append(session_id)
                    success_map[session_id] = False
            except Exception as e:
                logger.error(f"Error broadcasting to session {session_id}: {e}")
                disconnected_sessions.append(session_id)
                success_map[session_id] = False

        # Clean up disconnected sessions
        for session_id in disconnected_sessions:
            self.disconnect(session_id)

        logger.info(f"Broadcast sent to {sum(1 for v in success_map.values() if v)} connections")
        return success_map

    async def subscribe(self, session_id: str, channel: str) -> bool:
        """
        Subscribe a client to a channel.

        Args:
            session_id: The session ID of the client
            channel: The channel to subscribe to

        Returns:
            bool: True if subscription was successful
        """
        if not channel:
            logger.warning(f"Empty channel name provided for session {session_id}")
            return False

        if channel not in self.channel_subscribers:
            self.channel_subscribers[channel] = set()

        self.channel_subscribers[channel].add(session_id)
        logger.info(f"Session {session_id} subscribed to channel {channel}")
        return True

    async def unsubscribe(self, session_id: str, channel: str) -> bool:
        """
        Unsubscribe a client from a channel.

        Args:
            session_id: The session ID of the client
            channel: The channel to unsubscribe from

        Returns:
            bool: True if unsubscription was successful
        """
        if not channel or channel not in self.channel_subscribers:
            logger.warning(f"Channel {channel} not found for unsubscription")
            return False

        if session_id in self.channel_subscribers[channel]:
            self.channel_subscribers[channel].remove(session_id)
            logger.info(f"Session {session_id} unsubscribed from channel {channel}")

        # Clean up empty channels
        if not self.channel_subscribers[channel]:
            del self.channel_subscribers[channel]

        return True

    async def publish_to_channel(self, channel: str, message: Dict[str, Any]) -> Dict[str, bool]:
        """
        Publish a message to all subscribers of a channel.

        Args:
            channel: The channel to publish to
            message: The message to publish

        Returns:
            Dict mapping session IDs to success status
        """
        if not channel or channel not in self.channel_subscribers:
            logger.warning(f"Channel {channel} not found for publishing")
            return {}

        # Add channel name to message
        if "channel" not in message:
            message["channel"] = channel

        # Get subscribers
        subscribers = self.channel_subscribers[channel]
        results = {}

        for session_id in subscribers:
            results[session_id] = await self.send_update(session_id, message)

        return results

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific session."""
        return self.connection_states.get(session_id)

    async def _periodic_cleanup(self, max_idle_minutes: int = 30) -> None:
        """
        Periodically clean up stale connections.

        Args:
            max_idle_minutes: Maximum idle time in minutes before removing a connection
        """
        try:
            while True:
                # Wait for cleanup interval
                await asyncio.sleep(60 * 5)  # 5 minutes

                try:
                    await self._cleanup_stale_connections(max_idle_minutes)
                except Exception as e:
                    logger.error(f"Error in periodic cleanup: {e}")
        except asyncio.CancelledError:
            logger.info("WebSocket cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in periodic cleanup task: {e}")

    async def _cleanup_stale_connections(self, max_idle_minutes: int) -> None:
        """Helper method to clean up stale connections."""
        now = time.time()
        max_idle_seconds = max_idle_minutes * 60
        stale_sessions = []

        # Identify stale sessions
        async with self._lock:
            for session_id, state in list(self.connection_states.items()):
                last_activity = state.get("last_activity", 0)
                idle_time = now - last_activity

                if idle_time > max_idle_seconds:
                    stale_sessions.append(session_id)

        # Clean up each stale session
        for session_id in stale_sessions:
            logger.info(f"Cleaning up stale connection for session {session_id}")

            # Get the websocket before locking to prevent deadlock
            websocket = self.active_connections.get(session_id)

            # Try to close the websocket connection
            if websocket:
                try:
                    await websocket.close(code=1000, reason="Connection timed out due to inactivity")
                except Exception as e:
                    logger.warning(f"Error closing stale connection for {session_id}: {e}")

            # Remove from tracking
            async with self._lock:
                self.active_connections.pop(session_id, None)
                self.subscriptions.pop(session_id, None)
                self.connection_states.pop(session_id, None)

        if stale_sessions:
            logger.info(f"Cleaned up {len(stale_sessions)} stale connections")

# Global WebSocketManager instance
_websocket_manager = None

def get_websocket_manager() -> WebSocketManager:
    """
    Get the WebSocketManager singleton instance.

    Returns:
        WebSocketManager: The singleton WebSocketManager instance
    """
    global _websocket_manager

    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()

    return _websocket_manager
