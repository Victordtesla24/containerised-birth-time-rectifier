"""
WebSocket Proxy for Birth Time Rectifier API Gateway

This module provides WebSocket proxy functionality to forward WebSocket connections
from the API Gateway to the AI service, using the canonical WebSocketManager
implementation for connection management.
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, Optional, List, Tuple, Union, TYPE_CHECKING
import uuid
from datetime import datetime
import traceback
import socket
import jsonschema
from jsonschema import ValidationError
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
import random
import re
from contextlib import asynccontextmanager

from fastapi import WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

# Import the canonical WebSocketManager and events
from ai_service.utils.websocket_manager import WebSocketManager, get_websocket_manager
from ai_service.utils.websocket_events import emit_event, EventType

# Type checking imports
if TYPE_CHECKING:
    from websockets.legacy.client import WebSocketClientProtocol

# Configure logging
logger = logging.getLogger("api_gateway.websocket_proxy")

# Configuration from environment variables
AI_SERVICE_WS_URL = os.getenv("AI_SERVICE_WS_URL", "ws://localhost:8001/ws")
WS_PING_INTERVAL = int(os.getenv("WS_PING_INTERVAL", "20"))
WS_PING_TIMEOUT = int(os.getenv("WS_PING_TIMEOUT", "20"))
WS_MAX_SIZE = int(os.getenv("WS_MAX_SIZE", "16777216"))  # 16MB
WS_MAX_QUEUE = int(os.getenv("WS_MAX_QUEUE", "32"))
WS_HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))
WS_RETRY_ATTEMPTS = int(os.getenv("WS_RETRY_ATTEMPTS", "3"))
WS_RETRY_DELAY = int(os.getenv("WS_RETRY_DELAY", "2"))

@asynccontextmanager
async def create_task_group():
    """Context manager for managing a group of tasks that are started together.

    Similar to anyio's TaskGroup but using asyncio primitives.
    """
    tasks = set()

    async def start_soon(func, *args, **kwargs):
        task = asyncio.create_task(func(*args, **kwargs))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return task

    try:
        yield type('TaskGroup', (), {'start_soon': start_soon})
    finally:
        if tasks:
            # Cancel all remaining tasks
            for task in tasks:
                if not task.done():
                    task.cancel()

            # Wait for all tasks to complete or cancel
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

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
        # Use the canonical WebSocketManager for connection management
        self.ws_manager = get_websocket_manager()

        # Additional proxy-specific attributes
        self.reconnection_tokens: Dict[str, str] = {}
        self.client_metadata: Dict[str, Dict[str, Any]] = {}
        self.connection_status: Dict[str, Dict[str, Any]] = {}
        self.failed_events: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Accept a new WebSocket connection and register it using the canonical manager.

        Args:
            websocket: The WebSocket connection to accept
            session_id: Session ID for this connection
        """
        # Use the canonical WebSocketManager
        success = await self.ws_manager.connect(websocket, session_id)

        if success:
            # Initialize connection status tracking specifically for the proxy
            self.connection_status[session_id] = {
                "client_connected": True,
                "upstream_connected": False,
                "last_client_message": time.time(),
                "last_upstream_message": time.time(),
                "reconnect_count": 0,
                "client_id": "",
                "errors": []
            }

            # Initialize client metadata
            if session_id not in self.client_metadata:
                self.client_metadata[session_id] = {
                    "connected_at": datetime.now().isoformat(),
                    "last_activity": datetime.now().isoformat(),
                    "reconnect_count": 0,
                    "client_info": {}
                }
            else:
                # Update existing metadata for reconnection
                self.client_metadata[session_id]["reconnect_count"] += 1
                self.client_metadata[session_id]["last_connected_at"] = datetime.now().isoformat()

            logger.info(f"WebSocket connection accepted for session: {session_id}")

    async def disconnect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Remove a WebSocket connection using the canonical manager.

        Args:
            websocket: The WebSocket connection to remove
            session_id: Session ID for this connection
        """
        # Use canonical WebSocketManager's disconnect method
        self.ws_manager.disconnect(session_id)

        # Update proxy-specific state
        if session_id in self.connection_status:
            self.connection_status[session_id]["client_connected"] = False

        # Update metadata
        if session_id in self.client_metadata:
            self.client_metadata[session_id]["disconnected_at"] = datetime.now().isoformat()

        logger.info(f"WebSocket connection disconnected for session: {session_id}")

    async def broadcast(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients for a specific session
        using the canonical WebSocketManager.

        Args:
            session_id: The session ID to broadcast to
            message: The message to broadcast
        """
        # Use the canonical WebSocketManager to send the update
        success = await self.ws_manager.send_update(session_id, message)

        if not success:
            logger.warning(f"Failed to send message to session {session_id}, will be queued for reconnection")
        else:
            logger.debug(f"Message sent to session {session_id}")

    async def handle_websocket(
        self,
        websocket: WebSocket,
        session_id: str,
        upstream_url: str,
        client_id: str,
        token: str,
        ping_interval: int = 20
    ) -> None:
        """
        Handle WebSocket connection between client and AI service.

        Args:
            websocket: Client WebSocket connection
            session_id: Session ID for this connection
            upstream_url: URL of the upstream AI service WebSocket
            client_id: Unique client identifier
            token: Authentication token (if any)
            ping_interval: Interval for sending ping messages (seconds)
        """
        # Initialize connection tracking
        upstream_ws = None
        is_upstream_connected = False

        # Make sure the session_id is in the URL
        if not upstream_url.endswith('/'):
            upstream_url += '/'
        if not upstream_url.endswith(f'/{session_id}'):
            upstream_url += session_id

        logger.info(f"Connecting to upstream WebSocket at {upstream_url}")

        try:
            # First notify client that we're connecting
            await websocket.send_json({
                "type": "connection_status",
                "status": "connecting",
                "message": "Connecting to upstream service...",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })

            # Connect to upstream WebSocket
            upstream_ws = await self.connect_to_upstream_ws(upstream_url, session_id, token)
            is_upstream_connected = True

            # Inform client of successful connection
            await websocket.send_json({
                "type": "connection_status",
                "status": "connected",
                "message": "Connected to upstream service",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            })

            # Create tasks for bidirectional message handling and heartbeat
            client_to_upstream = asyncio.create_task(
                self.forward_client_messages(websocket, upstream_ws, session_id)
            )
            upstream_to_client = asyncio.create_task(
                self.forward_upstream_messages(upstream_ws, websocket, session_id)
            )
            heartbeat_task = asyncio.create_task(
                self.heartbeat(websocket, upstream_ws, ping_interval)
            )

            # Wait for any task to complete (error or disconnect)
            done, pending = await asyncio.wait(
                [client_to_upstream, upstream_to_client, heartbeat_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()

            # Wait for tasks to finish cancellation
            await asyncio.gather(*pending, return_exceptions=True)

            # Log which task completed first
            logger.info(f"WebSocket session {session_id}: A task completed, closing connection")

        except WebSocketDisconnect:
            logger.info(f"Client disconnected: {session_id}")

        except Exception as e:
            logger.error(f"Error in WebSocket proxy: {e}")
            logger.error(traceback.format_exc())

            # Try to send error to client if still connected
            if websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Connection error: {str(e)}",
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception:
                    pass

        finally:
            # Clean up upstream connection if it was established
            if upstream_ws is not None:
                logger.info(f"Closing upstream connection for {session_id}")
                try:
                    await upstream_ws.close()
                except Exception as e:
                    logger.warning(f"Error closing upstream connection: {e}")

            logger.info(f"WebSocket proxy session ended: {session_id}")

    async def forward_client_messages(self, client_ws: WebSocket, upstream_ws: Any, session_id: str) -> None:
        """Forward messages from client to upstream"""
        try:
            while True:
                # Receive message from client
                message = await client_ws.receive()

                # Handle different message types
                if message["type"] == "websocket.disconnect":
                    logger.info(f"Client disconnected: {session_id}")
                    break

                if message["type"] == "websocket.receive":
                    if "text" in message:
                        # Text message
                        await upstream_ws.send(message["text"])
                    elif "bytes" in message:
                        # Binary message
                        await upstream_ws.send(message["bytes"])

        except WebSocketDisconnect:
            logger.info(f"Client disconnected during message forwarding: {session_id}")
        except Exception as e:
            logger.error(f"Error forwarding client message: {e}")

    async def forward_upstream_messages(self, upstream_ws: Any, client_ws: WebSocket, session_id: str) -> None:
        """Forward messages from upstream to client"""
        try:
            while True:
                # Receive message from upstream
                message = await upstream_ws.recv()

                # Forward to client
                if isinstance(message, str):
                    await client_ws.send_text(message)
                elif isinstance(message, bytes):
                    await client_ws.send_bytes(message)

        except ConnectionClosed:
            logger.info(f"Upstream connection closed: {session_id}")
        except Exception as e:
            logger.error(f"Error forwarding upstream message: {e}")

    async def heartbeat(self, client_ws: WebSocket, upstream_ws: Any, interval: int) -> None:
        """Send periodic heartbeat messages to keep connections alive"""
        try:
            while True:
                await asyncio.sleep(interval)

                # Send ping to upstream
                if upstream_ws:
                    try:
                        await upstream_ws.ping()
                    except Exception as e:
                        logger.warning(f"Error sending ping to upstream: {e}")
                        break

                # Send ping to client
                try:
                    await client_ws.send_json({"type": "ping", "timestamp": datetime.now().isoformat()})
                except Exception as e:
                    logger.warning(f"Error sending ping to client: {e}")
                    break

        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    async def connect_to_upstream_ws(self, upstream_url: str, session_id: str, token: str) -> Any:
        """Connect to the upstream WebSocket server"""
        logger.info(f"Connecting to upstream WebSocket at {upstream_url}")

        # Set headers for authentication
        headers = {
            "X-Session-ID": session_id,
            "X-API-Gateway-Source": "true",
            "X-Client-ID": f"api-gateway-{session_id[:8]}",
            "Origin": "http://localhost:3001",
            "User-Agent": "API-Gateway-WebSocket-Client"
        }

        # Add token if provided
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token}"

        try:
            # Connect to upstream WebSocket
            websocket = await websockets.connect(
                upstream_url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
                max_size=WS_MAX_SIZE
            )

            logger.info(f"Successfully connected to upstream WebSocket at {upstream_url}")
            return websocket

        except Exception as e:
            logger.error(f"Error connecting to upstream WebSocket: {e}")
            raise

    def _validate_message(self, message_str: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Validate WebSocket message format and content with comprehensive schema validation.

        Args:
            message_str: JSON message string to validate

        Returns:
            Tuple of (is_valid, error_message, validated_message)
        """
        try:
            # Check if message is valid JSON
            try:
                message = json.loads(message_str)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON format: {str(e)}", None

            # Check if message is a dictionary
            if not isinstance(message, dict):
                return False, "Message must be a JSON object, not a list or primitive value", None

            # Check for required fields
            if "type" not in message:
                return False, "Message missing required 'type' field", None

            # Define message schemas for different message types
            base_schema = {
                "type": "object",
                "required": ["type"],
                "properties": {
                    "type": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "message_id": {"type": "string"},
                    "session_id": {"type": "string"}
                }
            }

            event_schema = {
                **base_schema,
                "required": ["type", "event_type", "data"],
                "properties": {
                    **base_schema["properties"],
                    "event_type": {"type": "string"},
                    "data": {"type": "object"},
                    "source": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]}
                },
                "additionalProperties": True
            }

            request_schema = {
                **base_schema,
                "required": ["type", "request_id", "action"],
                "properties": {
                    **base_schema["properties"],
                    "request_id": {"type": "string"},
                    "action": {"type": "string"},
                    "parameters": {"type": "object"},
                    "timeout_ms": {"type": "integer", "minimum": 0},
                    "require_response": {"type": "boolean"}
                },
                "additionalProperties": True
            }

            response_schema = {
                **base_schema,
                "required": ["type", "request_id", "status"],
                "properties": {
                    **base_schema["properties"],
                    "request_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["success", "error", "pending"]},
                    "data": {"type": "object"},
                    "error": {"type": "object"},
                    "processing_time_ms": {"type": "integer", "minimum": 0}
                },
                "additionalProperties": True
            }

            error_schema = {
                **base_schema,
                "required": ["type", "error_code", "error_message"],
                "properties": {
                    **base_schema["properties"],
                    "error_code": {"type": "string"},
                    "error_message": {"type": "string"},
                    "error_details": {"type": "object"},
                    "recoverable": {"type": "boolean"},
                    "retry_after_ms": {"type": "integer", "minimum": 0}
                },
                "additionalProperties": True
            }

            ping_pong_schema = {
                **base_schema,
                "properties": {
                    **base_schema["properties"],
                    "seq": {"type": "integer", "minimum": 0},
                    "data": {"type": "object"}
                },
                "additionalProperties": True
            }

            # Message type specific validation
            message_type = message.get("type", "")
            schema = None

            if message_type == "event":
                schema = event_schema
            elif message_type == "request":
                schema = request_schema
            elif message_type == "response":
                schema = response_schema
            elif message_type == "error":
                schema = error_schema
            elif message_type in ["ping", "pong"]:
                schema = ping_pong_schema
            else:
                # For unknown types, use base schema with additionalProperties
                schema = {**base_schema, "additionalProperties": True}

            # Validate against schema
            try:
                jsonschema.validate(instance=message, schema=schema)
            except ValidationError as e:
                # Detailed validation failure
                return False, f"Schema validation failed: {e.message} at path: {'/'.join(str(p) for p in e.path)}", None

            # Check message size (prevent excessive messages)
            message_size = len(message_str)
            max_size = 1024 * 1024  # 1MB limit

            if message_size > max_size:
                return False, f"Message exceeds size limit of 1MB: {message_size} bytes", None

            # Check for risky payloads with more comprehensive patterns
            risky_patterns = [
                r'<script.*?>.*?</script>',  # JavaScript
                r'eval\s*\(',  # eval() calls
                r'(?:document|window|parent|self|top)\.(?:location|cookie|localStorage|sessionStorage)',  # Sensitive browser APIs
                r'(?:innerHTML|outerHTML)[\s=]',  # HTML injection
                r'(?:href|src|data|action)[\s=][\'"`](?:javascript|data):',  # Protocol handlers
                r'iframe[\s]',  # iframes
                r'onload|onerror|onmouseover|onclick|onmouseout|onkeydown|onkeypress',  # Event handlers
                r'(?:http|ws)s?://(?!api\.example\.com)',  # External URLs (except our API domain)
                r'fetch\s*\(',  # fetch API
                r'XMLHttpRequest',  # XHR
                r'__proto__|constructor|prototype',  # Prototype pollution
                r'process\.env|require\s*\(|import\s+',  # Node.js specific vectors
                r'Object\.(?:assign|create|defineProperty)',  # Object manipulation
                r'JSON\.parse\s*\(\s*[\'"]'  # JSON parsing of untrusted data
            ]

            # Apply each risky pattern but consider context
            message_json_str = json.dumps(message)
            for pattern in risky_patterns:
                if re.search(pattern, message_json_str, re.IGNORECASE | re.DOTALL):
                    # Skip certain checks for specific message types (e.g., allow URLs in certain fields)
                    skip_check = False

                    # URL check exception for specific fields
                    if pattern.startswith('(?:http|ws)s?://') and message_type == "request":
                        # Allow URLs in specific fields like "url" or "endpoint"
                        if "parameters" in message and isinstance(message["parameters"], dict):
                            params = message["parameters"]
                            if "url" in params or "endpoint" in params:
                                skip_check = True

                    if not skip_check:
                        return False, f"Message contains potentially dangerous content matching pattern: {pattern}", None

            # Add validation timestamp
            message["validation_timestamp"] = datetime.now().isoformat()

            # Message passed all validations
            return True, None, message

        except Exception as e:
            logger.error(f"Unexpected validation error: {str(e)}\n{traceback.format_exc()}")
            return False, f"Validation error: {str(e)}", None

    async def retry_failed_messages(self, session_id: str) -> None:
        """
        Retry sending failed messages for a session.

        Args:
            session_id: Session ID to retry messages for
        """
        if session_id not in self.failed_events or not self.failed_events[session_id]:
            # No failed events to retry
            return

        if session_id not in self.connection_status or not self.connection_status[session_id]["client_connected"]:
            logger.info(f"Can't retry messages for session {session_id} - not connected")
            return

        # Get the client's websocket
        websocket = self.ws_manager.get_websocket(session_id)
        if not websocket:
            logger.warning(f"Can't retry messages for session {session_id} - no websocket found")
            return

        # Copy failed events to retry
        retry_events = self.failed_events[session_id].copy()
        self.failed_events[session_id] = []

        # Retry each failed event
        success_count = 0
        for event in retry_events:
            try:
                await websocket.send_json(event)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to retry event for session {session_id}: {e}")
                # Add back to queue with increased retry count
                if "retry_count" in event:
                    event["retry_count"] += 1
                else:
                    event["retry_count"] = 1

                if event.get("retry_count", 0) < 3:  # Limit retries
                    self.failed_events[session_id].append(event)

        logger.info(f"Retried {success_count}/{len(retry_events)} failed events for session {session_id}")

    async def _send_heartbeats(self, websocket: WebSocket, session_id: str, client_id: str, interval: int) -> None:
        """
        Send periodic heartbeat messages to keep the connection alive.

        Args:
            websocket: The WebSocket connection
            session_id: The session ID
            client_id: The client ID
            interval: How often to send heartbeats (seconds)
        """
        try:
            while True:
                await asyncio.sleep(interval)
                try:
                    heartbeat_id = str(uuid.uuid4())
                    await websocket.send_json({
                        "type": "heartbeat",
                        "session_id": session_id,
                        "client_id": client_id,
                        "message_id": heartbeat_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.debug(f"Sent heartbeat to client {client_id}")

                    # After sending heartbeat, check if there are any failed messages to retry
                    if session_id in self.failed_events and self.failed_events[session_id]:
                        # Wait a short time to allow heartbeat response
                        await asyncio.sleep(1)
                        await self.retry_failed_messages(session_id)
                except Exception as e:
                    logger.warning(f"Failed to send heartbeat to client {client_id}: {str(e)}")
                    break

        except asyncio.CancelledError:
            logger.debug(f"Heartbeat task cancelled for client {client_id}")
        except Exception as e:
            logger.error(f"Error in heartbeat task for client {client_id}: {str(e)}")

    async def clean_stale_sessions(self, max_age_hours: int = 24) -> None:
        """
        Clean up stale sessions that haven't been active for the specified time.

        Args:
            max_age_hours: Maximum age in hours for session retention
        """
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        sessions_to_remove = []

        for session_id, status in self.connection_status.items():
            last_activity = status.get("last_activity", 0)
            disconnected_at = status.get("disconnected_at", 0)

            # Use most recent time between last activity and disconnect time
            last_time = max(last_activity, disconnected_at)

            if now - last_time > max_age_seconds:
                sessions_to_remove.append(session_id)

        # Remove stale sessions
        for session_id in sessions_to_remove:
            self.connection_status.pop(session_id, None)
            self.client_metadata.pop(session_id, None)
            self.reconnection_tokens.pop(session_id, None)
            self.failed_events.pop(session_id, None)

            # Use canonical WebSocketManager to disconnect
            self.ws_manager.disconnect(session_id)

        if sessions_to_remove:
            logger.info(f"Cleaned up {len(sessions_to_remove)} stale sessions")

    def _handle_special_messages(self, message: Dict[str, Any], session_id: str) -> bool:
        """
        Handle special messages (e.g., authentication) for a session.

        Args:
            message: The message dictionary to process
            session_id: The session ID

        Returns:
            True if the message was handled, False otherwise
        """
        # Implement special message handling logic here
        return False

    # Add method to handle test events
    async def send_test_event(self, session_id: str, message: str) -> bool:
        """
        Send a test event to a connected client.

        Args:
            session_id: The session ID to send the event to
            message: The message to include in the event

        Returns:
            bool: True if the event was sent successfully
        """
        try:
            # First check if the session is actually connected
            if not self._connection_exists(session_id):
                logger.warning(f"Cannot send test event: No active connection for session {session_id}")
                return False

            # Create event structure
            event = {
                "type": "test_event",
                "message": message,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "test": True,
                "id": str(uuid.uuid4())  # Add a unique ID for tracking
            }

            # Try to send via the manager with timeout for safety
            try:
                return await asyncio.wait_for(
                    self.ws_manager.send_update(session_id, event),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.error(f"Timeout sending test event to session {session_id}")
                return False
        except Exception as e:
            logger.error(f"Error sending test event to session {session_id}: {e}")
            logger.error(traceback.format_exc())
            return False

    def _connection_exists(self, session_id: str) -> bool:
        """
        Check if a connection exists for the given session ID.

        Args:
            session_id: The session ID to check

        Returns:
            True if the connection exists, False otherwise
        """
        # Check if the session ID is in the WebSocketManager's active connections
        return session_id in self.ws_manager.active_connections

# Create a global instance
proxy = WebSocketProxy()
