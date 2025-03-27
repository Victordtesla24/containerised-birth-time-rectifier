"""
WebSocket Connection Manager for Birth Time Rectifier API

This module provides the core WebSocket functionality for real-time updates
across the entire application. This is the canonical implementation that should
be used by all services requiring WebSocket functionality.
"""

from fastapi import WebSocket
from typing import Dict, List, Any, Optional, Set
import logging
import json
import uuid
import time
from datetime import datetime
from starlette.websockets import WebSocketState

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

    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        """
        Accept a WebSocket connection and store it.

        Args:
            websocket: The WebSocket connection
            session_id: The session ID to associate with this connection

        Returns:
            bool: True if connection was successful
        """
        try:
            # Accept the connection
            await websocket.accept()

            # Store connection
            self.active_connections[session_id] = websocket

            # Initialize client metadata
            self.client_metadata[session_id] = {
                "connected_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "client_info": {}
            }

            logger.info(f"WebSocket connection established for session {session_id}")

            # Send initial connection confirmation
            await websocket.send_json({
                "type": "connection_status",
                "status": "connected",
                "session_id": session_id,
                "message": "WebSocket connection established",
                "timestamp": time.time()
            })

            # Send any queued messages upon connection
            if session_id in self.message_queues and self.message_queues[session_id]:
                queued_messages = self.message_queues[session_id].copy()
                self.message_queues[session_id] = []

                for message in queued_messages:
                    try:
                        await websocket.send_json(message)
                        logger.info(f"Sent queued message to connected client {session_id}")
                    except Exception as e:
                        logger.error(f"Failed to send queued message: {e}")
                        # Re-queue the message
                        if session_id not in self.message_queues:
                            self.message_queues[session_id] = []
                        self.message_queues[session_id].append(message)

            return True
        except Exception as e:
            logger.error(f"Error connecting WebSocket for session {session_id}: {e}")
            return False

    def disconnect(self, session_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            session_id: The session ID of the connection to remove
        """
        if session_id in self.active_connections:
            # Update metadata before removing
            if session_id in self.client_metadata:
                self.client_metadata[session_id]["disconnected_at"] = datetime.now().isoformat()

            # Remove connection
            del self.active_connections[session_id]
            logger.info(f"WebSocket connection closed for session {session_id}")

            # Don't remove from channel subscribers to allow reconnection

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
                    if session_id in self.client_metadata:
                        self.client_metadata[session_id]["last_activity"] = datetime.now().isoformat()

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
                    if session_id in self.client_metadata:
                        self.client_metadata[session_id]["last_activity"] = datetime.now().isoformat()
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
        return self.client_metadata.get(session_id)

# Create a global instance
manager = WebSocketManager()

def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    return manager
