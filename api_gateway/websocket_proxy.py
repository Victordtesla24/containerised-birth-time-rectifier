"""
WebSocket Proxy for Birth Time Rectifier API Gateway

This module provides WebSocket proxy functionality to forward WebSocket connections
from the API Gateway to the AI service.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, Optional, List, Tuple, Union, TYPE_CHECKING
import uuid

from fastapi import WebSocket, WebSocketDisconnect, status
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

# Type checking imports
if TYPE_CHECKING:
    from websockets.legacy.client import WebSocketClientProtocol

# Configure logging
logger = logging.getLogger("api_gateway.websocket_proxy")

# Configuration from environment variables
AI_SERVICE_WS_URL = os.getenv("AI_SERVICE_WS_URL", "ws://ai_service:8000/ws")
WS_PING_INTERVAL = int(os.getenv("WS_PING_INTERVAL", "20"))
WS_PING_TIMEOUT = int(os.getenv("WS_PING_TIMEOUT", "20"))
WS_MAX_SIZE = int(os.getenv("WS_MAX_SIZE", "16777216"))  # 16MB
WS_MAX_QUEUE = int(os.getenv("WS_MAX_QUEUE", "32"))
WS_HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
WS_RETRY_ATTEMPTS = int(os.getenv("WS_RETRY_ATTEMPTS", "3"))
WS_RETRY_DELAY = int(os.getenv("WS_RETRY_DELAY", "2"))

class WebSocketProxy:
    """
    WebSocket proxy that forwards connections between clients and the AI service.

    This class manages WebSocket connections and proxies messages between
    the client and the AI service, with support for:
    - Connection retries
    - Heartbeat monitoring
    - Error handling and recovery
    - Resource cleanup
    """

    def __init__(self):
        """Initialize the WebSocket proxy."""
        # Store active connections by session ID
        self.active_connections: Dict[str, Tuple[WebSocket, Any]] = {}
        # Store message queues for each connection
        self.message_queues: Dict[str, asyncio.Queue] = {}
        # Store tasks for each connection
        self.tasks: Dict[str, List[asyncio.Task]] = {}
        # Store heartbeat tasks
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        # Store connection status
        self.connection_status: Dict[str, bool] = {}
        # Lock for thread safety
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, session_id: Optional[str] = None) -> str:
        """
        Accept a WebSocket connection and establish a proxy connection to the AI service.

        Args:
            websocket: The client WebSocket connection
            session_id: Optional session ID. If not provided, a new one will be generated.

        Returns:
            str: The session ID used for the connection
        """
        # Generate a session ID if not provided
        if not session_id:
            session_id = f"proxy-{uuid.uuid4().hex[:8]}"

        # Accept the client connection
        await websocket.accept()

        try:
            # Connect to the AI service with retry logic
            ai_websocket = await self._connect_to_ai_service_with_retry(session_id)
            if not ai_websocket:
                logger.error(f"Failed to connect to AI service after {WS_RETRY_ATTEMPTS} attempts")
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                return session_id

            # Acquire lock for thread safety
            async with self.lock:
                # Store the connections
                self.active_connections[session_id] = (websocket, ai_websocket)
                self.connection_status[session_id] = True

                # Create message queues with size limit to prevent memory issues
                client_queue = asyncio.Queue(maxsize=WS_MAX_QUEUE)
                ai_queue = asyncio.Queue(maxsize=WS_MAX_QUEUE)
                self.message_queues[f"{session_id}_client"] = client_queue
                self.message_queues[f"{session_id}_ai"] = ai_queue

                # Create tasks for message forwarding
                client_to_ai_task = asyncio.create_task(
                    self._forward_messages(websocket, ai_websocket, client_queue, f"client-to-ai-{session_id}")
                )
                ai_to_client_task = asyncio.create_task(
                    self._forward_messages(ai_websocket, websocket, ai_queue, f"ai-to-client-{session_id}")
                )

                # Create heartbeat task
                heartbeat_task = asyncio.create_task(
                    self._heartbeat_monitor(session_id, websocket, ai_websocket)
                )

                # Store tasks
                self.tasks[session_id] = [client_to_ai_task, ai_to_client_task]
                self.heartbeat_tasks[session_id] = heartbeat_task

            # Send connection confirmation to client
            try:
                await websocket.send_json({
                    "type": "connection_status",
                    "status": "connected",
                    "session_id": session_id,
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Error sending connection confirmation to client for session {session_id}: {e}")

            logger.info(f"WebSocket proxy established for session {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Error establishing WebSocket proxy for session {session_id}: {e}")
            try:
                await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            except Exception:
                pass  # Already closed
            return session_id

    async def _connect_to_ai_service_with_retry(self, session_id: str) -> Optional[Any]:
        """
        Connect to the AI service with retry logic.

        Args:
            session_id: The session ID for the connection

        Returns:
            Optional[websockets.WebSocketClientProtocol]: The WebSocket connection to the AI service, or None if failed
        """
        ai_service_url = f"{AI_SERVICE_WS_URL}/{session_id}"
        logger.info(f"Connecting to AI service at {ai_service_url}")

        # Try to connect to the AI service with retries
        for attempt in range(WS_RETRY_ATTEMPTS):
            try:
                # Connect with proper configuration
                ai_websocket = await websockets.connect(
                    ai_service_url,
                    ping_interval=WS_PING_INTERVAL,
                    ping_timeout=WS_PING_TIMEOUT,
                    max_size=WS_MAX_SIZE,
                    close_timeout=WS_PING_TIMEOUT
                )
                logger.info(f"Connected to AI service at {ai_service_url} (attempt {attempt + 1})")
                return ai_websocket
            except Exception as e:
                logger.warning(f"Failed to connect to AI service (attempt {attempt + 1}): {e}")
                if attempt < WS_RETRY_ATTEMPTS - 1:
                    # Exponential backoff
                    delay = WS_RETRY_DELAY * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to connect to AI service after {WS_RETRY_ATTEMPTS} attempts")
                    # Return None to indicate connection failure
                    return None

    async def disconnect(self, session_id: str):
        """
        Disconnect a WebSocket proxy connection.

        Args:
            session_id: The session ID of the connection to disconnect
        """
        # Acquire lock for thread safety
        async with self.lock:
            if session_id in self.active_connections:
                # Update connection status
                self.connection_status[session_id] = False

                # Get the connections
                client_ws, ai_ws = self.active_connections[session_id]

                # Cancel tasks
                if session_id in self.tasks:
                    for task in self.tasks[session_id]:
                        if not task.done():
                            task.cancel()
                    del self.tasks[session_id]

                # Cancel heartbeat task
                if session_id in self.heartbeat_tasks:
                    if not self.heartbeat_tasks[session_id].done():
                        self.heartbeat_tasks[session_id].cancel()
                    del self.heartbeat_tasks[session_id]

                # Close connections
                try:
                    await ai_ws.close()
                except Exception as e:
                    logger.error(f"Error closing AI service connection for session {session_id}: {e}")

                try:
                    await client_ws.close()
                except Exception as e:
                    logger.error(f"Error closing client connection for session {session_id}: {e}")

                # Clean up resources
                del self.active_connections[session_id]
                if f"{session_id}_client" in self.message_queues:
                    del self.message_queues[f"{session_id}_client"]
                if f"{session_id}_ai" in self.message_queues:
                    del self.message_queues[f"{session_id}_ai"]
                if session_id in self.connection_status:
                    del self.connection_status[session_id]

                logger.info(f"WebSocket proxy disconnected for session {session_id}")

    async def _forward_messages(
        self,
        source_ws: Any,
        target_ws: Any,
        message_queue: asyncio.Queue,
        task_name: str
    ):
        """
        Forward messages from source to target WebSocket.

        Args:
            source_ws: The source WebSocket connection
            target_ws: The target WebSocket connection
            message_queue: Queue for messages
            task_name: Name of the task for logging
        """
        # Extract session_id from task_name for later use
        parts = task_name.split('-')
        session_id = parts[2] if len(parts) >= 3 else "unknown"

        try:
            while True:
                # Check if connection is still active
                if session_id in self.connection_status and not self.connection_status[session_id]:
                    logger.info(f"[{task_name}] Connection marked as inactive, stopping message forwarding")
                    break

                try:
                    # Receive message from source with timeout to allow for checking connection status
                    if isinstance(source_ws, WebSocket):
                        # FastAPI WebSocket
                        message = await asyncio.wait_for(source_ws.receive_text(), timeout=WS_PING_INTERVAL)
                    else:
                        # websockets WebSocket
                        message = await asyncio.wait_for(source_ws.recv(), timeout=WS_PING_INTERVAL)

                    # Try to parse JSON to check if it's a valid message
                    try:
                        json_data = json.loads(message)
                        # Log message type for debugging
                        msg_type = json_data.get("type", "unknown")
                        logger.debug(f"[{task_name}] Received message type: {msg_type}")
                    except json.JSONDecodeError:
                        # Not JSON, just log the first part
                        logger.debug(f"[{task_name}] Received non-JSON message: {message[:50]}...")

                    # Forward message to target
                    try:
                        if isinstance(target_ws, WebSocket):
                            # FastAPI WebSocket
                            await target_ws.send_text(message)
                        else:
                            # websockets WebSocket
                            await target_ws.send(message)
                    except Exception as e:
                        logger.error(f"[{task_name}] Error forwarding message to target: {e}")
                        raise  # Re-raise to trigger connection cleanup

                    # Put message in queue for other tasks to use if needed
                    try:
                        # Use put_nowait with a timeout to avoid blocking indefinitely
                        await asyncio.wait_for(
                            asyncio.shield(message_queue.put(message)),
                            timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"[{task_name}] Message queue full, dropping message")
                    except Exception as e:
                        logger.error(f"[{task_name}] Error putting message in queue: {e}")

                except asyncio.TimeoutError:
                    # This is expected due to the timeout in receive_text/recv
                    # Just continue the loop to check connection status
                    continue

        except WebSocketDisconnect:
            logger.info(f"[{task_name}] WebSocket disconnected")
        except ConnectionClosed:
            logger.info(f"[{task_name}] Connection closed")
        except asyncio.CancelledError:
            logger.info(f"[{task_name}] Task cancelled")
        except Exception as e:
            logger.error(f"[{task_name}] Error forwarding messages: {e}")
        finally:
            # Only disconnect if this is the client-to-ai task to avoid duplicate disconnects
            if task_name.startswith("client-to-ai"):
                await self.disconnect(session_id)

    async def _heartbeat_monitor(self, session_id: str, client_ws: WebSocket, ai_ws: Any):
        """
        Monitor the connection health with periodic heartbeats.

        Args:
            session_id: The session ID
            client_ws: The client WebSocket connection
            ai_ws: The AI service WebSocket connection
        """
        try:
            while session_id in self.connection_status and self.connection_status[session_id]:
                try:
                    # Send heartbeat to client
                    await client_ws.send_json({
                        "type": "heartbeat",
                        "timestamp": time.time()
                    })

                    # For the AI service connection, we rely on the built-in ping/pong of websockets
                    # which is configured through ping_interval and ping_timeout

                    # Wait for next heartbeat interval
                    await asyncio.sleep(WS_HEARTBEAT_INTERVAL)

                except Exception as e:
                    logger.error(f"Heartbeat failed for session {session_id}: {e}")
                    # If heartbeat fails, mark connection for cleanup
                    self.connection_status[session_id] = False
                    break

        except asyncio.CancelledError:
            logger.info(f"Heartbeat monitor cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Error in heartbeat monitor for session {session_id}: {e}")
            # Mark connection for cleanup
            if session_id in self.connection_status:
                self.connection_status[session_id] = False

# Create a global instance
proxy = WebSocketProxy()
