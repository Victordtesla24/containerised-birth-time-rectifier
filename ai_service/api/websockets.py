"""
WebSocket Connection Manager for Birth Time Rectifier API

This module provides WebSocket functionality for real-time updates
during long-running processes like birth time rectification.
"""

from fastapi import WebSocket
from typing import Dict, List, Any
import logging
import asyncio
import json

# Configure logging
logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket connection manager for handling real-time updates.

    This class manages WebSocket connections and provides methods
    for sending updates to specific clients or broadcasting to all.
    """

    def __init__(self):
        """Initialize the connection manager with an empty connections dictionary."""
        # Store active connections by session ID
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept a WebSocket connection and store it.

        Args:
            websocket: The WebSocket connection
            session_id: The session ID to associate with this connection
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connection established for session {session_id}")

        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_status",
            "status": "connected",
            "session_id": session_id,
            "message": "WebSocket connection established"
        })

    def disconnect(self, session_id: str):
        """
        Remove a WebSocket connection.

        Args:
            session_id: The session ID of the connection to remove
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket connection closed for session {session_id}")

    async def send_update(self, session_id: str, data: Any):
        """
        Send an update to a specific client.

        Args:
            session_id: The session ID of the client
            data: The data to send (will be converted to JSON)

        Returns:
            bool: True if the update was sent, False if the session was not found
        """
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(data)
                logger.info(f"Update sent to session {session_id}")
                return True
            except Exception as e:
                logger.error(f"Error sending update to session {session_id}: {e}")
                # Connection might be broken, remove it
                self.disconnect(session_id)
                return False
        else:
            logger.warning(f"Attempted to send update to unknown session {session_id}")
            return False

    async def broadcast(self, data: Any):
        """
        Broadcast an update to all connected clients.

        Args:
            data: The data to broadcast (will be converted to JSON)

        Returns:
            int: The number of clients that received the update
        """
        disconnected_sessions = []
        successful_broadcasts = 0

        for session_id, connection in self.active_connections.items():
            try:
                await connection.send_json(data)
                successful_broadcasts += 1
            except Exception as e:
                logger.error(f"Error broadcasting to session {session_id}: {e}")
                disconnected_sessions.append(session_id)

        # Clean up disconnected sessions
        for session_id in disconnected_sessions:
            self.disconnect(session_id)

        logger.info(f"Broadcast sent to {successful_broadcasts} connections")
        return successful_broadcasts

# Create a global instance
manager = ConnectionManager()
