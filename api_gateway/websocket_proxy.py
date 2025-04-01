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

from fastapi import WebSocket, WebSocketDisconnect, status
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
AI_SERVICE_WS_URL = os.getenv("AI_SERVICE_WS_URL", "ws://ai_service:8001/ws")
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
        ping_interval: int = 30
    ) -> None:
        """
        Handle WebSocket connection by proxying messages between client and AI service.

        This implementation includes robust message validation, automatic reconnection,
        error recovery, and proper error reporting to ensure reliable WebSocket communication.

        Args:
            websocket: Client WebSocket connection
            session_id: Session ID for this connection
            upstream_url: URL of the upstream AI service WebSocket
            client_id: Unique client identifier
            token: Authentication token (if any)
            ping_interval: Interval for sending ping messages (seconds)
        """
        # Initialize connection state
        connection_attempt = 0
        max_reconnect_attempts = 5
        backoff_factor = 1.5
        retry_delay = 1.0
        upstream_ws = None
        pending_tasks = set()
        heartbeat_task = None
        client_receiver_task = None
        upstream_receiver_task = None
        last_connection_error = None
        is_client_connected = True
        is_upstream_connected = False
        message_queue = []
        max_queue_size = 100

        # Initialize connection metrics
        connection_start_time = time.time()
        messages_sent = 0
        messages_received = 0
        reconnection_count = 0

        # Initialize connection state tracking
        self.connection_status[session_id] = {
            "client_connected": True,
            "upstream_connected": False,
            "last_client_message": time.time(),
            "last_upstream_message": time.time(),
            "reconnect_count": 0,
            "client_id": client_id,
            "errors": [],
            "connection_quality": "initializing"
        }

        try:
            # Send initial connection status to client
            await websocket.send_json({
                "type": "connection_status",
                "status": "connecting_to_service",
                "session_id": session_id,
                "client_id": client_id,
                "timestamp": time.time()
            })

            # Main connection loop with reconnection logic
            while connection_attempt <= max_reconnect_attempts and is_client_connected:
                try:
                    # Disconnect existing connection if any
                    if upstream_ws and is_upstream_connected:
                        try:
                            await upstream_ws.close()
                        except Exception:
                            pass  # Ignore errors when closing

                    # Connect to upstream WebSocket
                    logger.info(f"Connecting to upstream WebSocket at {upstream_url} (attempt {connection_attempt+1}/{max_reconnect_attempts+1})")

                    # Send connecting status to client
                    if connection_attempt > 0:
                        try:
                            await websocket.send_json({
                                "type": "connection_status",
                                "status": "reconnecting",
                                "session_id": session_id,
                                "client_id": client_id,
                                "attempt": connection_attempt + 1,
                                "max_attempts": max_reconnect_attempts + 1,
                                "timestamp": time.time()
                            })
                        except Exception as e:
                            logger.warning(f"Failed to send reconnecting status to client: {e}")
                            is_client_connected = False
                            break

                    # Apply exponential backoff for reconnection attempts
                    if connection_attempt > 0:
                        backoff_time = retry_delay * (backoff_factor ** (connection_attempt - 1))
                        logger.info(f"Waiting {backoff_time:.2f}s before reconnection attempt")
                        await asyncio.sleep(backoff_time)

                    # Connect to upstream with timeout
                    try:
                        upstream_ws = await asyncio.wait_for(
                            self.connect_to_upstream_ws(upstream_url, session_id, token),
                            timeout=10.0
                        )
                    except asyncio.TimeoutError:
                        logger.error("Timeout connecting to upstream WebSocket")
                        last_connection_error = "connection_timeout"
                        connection_attempt += 1
                        reconnection_count += 1
                        continue

                    # Update connection state
                    is_upstream_connected = True
                    self.connection_status[session_id]["upstream_connected"] = True
                    self.connection_status[session_id]["last_upstream_message"] = time.time()
                    self.connection_status[session_id]["reconnect_count"] = reconnection_count

                    # Calculate and update connection quality
                    if reconnection_count == 0:
                        connection_quality = "excellent"
                    elif reconnection_count == 1:
                        connection_quality = "good"
                    elif reconnection_count <= 3:
                        connection_quality = "fair"
                    else:
                        connection_quality = "poor"

                    self.connection_status[session_id]["connection_quality"] = connection_quality

                    # Notify client of successful connection
                    await websocket.send_json({
                        "type": "connection_status",
                        "status": "connected",
                        "session_id": session_id,
                        "client_id": client_id,
                        "reconnection_count": reconnection_count,
                        "connection_quality": connection_quality,
                        "timestamp": time.time()
                    })

                    # Process any queued messages
                    if message_queue:
                        queued_messages = message_queue.copy()
                        message_queue = []
                        logger.info(f"Processing {len(queued_messages)} queued messages for session {session_id}")

                        for queued_message in queued_messages:
                            try:
                                # Validate message with improved validation
                                is_valid, error_message, parsed_message = self._validate_message(
                                    json.dumps(queued_message) if isinstance(queued_message, dict) else queued_message
                                )

                                if is_valid and parsed_message:
                                    # Add metadata to outgoing messages
                                    if isinstance(parsed_message, dict):
                                        if "timestamp" not in parsed_message:
                                            parsed_message["timestamp"] = time.time()
                                        if "client_id" not in parsed_message:
                                            parsed_message["client_id"] = client_id

                                    # Send message with error handling
                                    try:
                                        await upstream_ws.send_json(parsed_message)
                                        messages_sent += 1
                                        logger.debug(f"Sent queued message to upstream: {json.dumps(parsed_message)[:100]}...")
                                    except Exception as send_error:
                                        logger.error(f"Failed to send queued message: {send_error}")
                                        # Re-queue the message for next reconnection attempt
                                        if len(message_queue) < max_queue_size:
                                            message_queue.append(queued_message)
                                else:
                                    logger.warning(f"Skipping invalid queued message: {error_message}")
                            except Exception as queue_error:
                                logger.error(f"Error processing queued message: {queue_error}")

                    # Set up client message forwarding to upstream
                    client_receiver_task = asyncio.create_task(
                        self.forward_to_upstream(websocket, upstream_ws, session_id)
                    )
                    pending_tasks.add(client_receiver_task)
                    client_receiver_task.add_done_callback(pending_tasks.discard)

                    # Set up upstream message forwarding to client
                    upstream_receiver_task = asyncio.create_task(
                        self.forward_to_client(websocket, upstream_ws, session_id)
                    )
                    pending_tasks.add(upstream_receiver_task)
                    upstream_receiver_task.add_done_callback(pending_tasks.discard)

                    # Set up heartbeat task for connection monitoring
                    heartbeat_task = asyncio.create_task(
                        self._send_heartbeats(websocket, session_id, client_id, ping_interval)
                    )
                    pending_tasks.add(heartbeat_task)
                    heartbeat_task.add_done_callback(pending_tasks.discard)

                    # Wait for any task to complete (which indicates connection issue)
                    done, pending = await asyncio.wait(
                        pending_tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Check which task completed and why
                    for task in done:
                        exception = task.exception()
                        if exception:
                            logger.warning(f"Task failed with exception: {exception}")
                            # Record the error for diagnostics
                            error_type = type(exception).__name__
                            error_message = str(exception)

                            # Update connection status with error
                            self.connection_status[session_id]["errors"].append({
                                "type": error_type,
                                "message": error_message,
                                "timestamp": time.time()
                            })

                            # Determine if client connection was lost
                            if task == client_receiver_task:
                                logger.info(f"Client {client_id} disconnected")
                                is_client_connected = False

                            # Determine if upstream connection was lost
                            if task == upstream_receiver_task:
                                logger.info(f"Upstream connection lost for session {session_id}")
                                is_upstream_connected = False
                                last_connection_error = error_type

                    # Cancel all remaining tasks before reconnection attempt
                    for task in pending:
                        task.cancel()

                    # Prepare for next attempt
                    reconnection_count += 1
                    connection_attempt += 1
                    is_upstream_connected = False
                    self.connection_status[session_id]["upstream_connected"] = False

                    # Don't retry if client connection was lost
                    if not is_client_connected:
                        break

                except Exception as e:
                    logger.error(f"Error in WebSocket connection loop: {e}")
                    logger.error(traceback.format_exc())

                    # Record the error
                    self.connection_status[session_id]["errors"].append({
                        "type": type(e).__name__,
                        "message": str(e),
                        "timestamp": time.time()
                    })

                    # Prepare for next attempt
                    last_connection_error = str(e)
                    connection_attempt += 1
                    reconnection_count += 1
                    is_upstream_connected = False

                    # Wait before retry
                    await asyncio.sleep(1.0)

            # If we've exhausted all reconnection attempts, send error to client
            if connection_attempt > max_reconnect_attempts and is_client_connected:
                await websocket.send_json({
                    "type": "connection_error",
                    "error": "max_reconnect_attempts_exceeded",
                    "message": f"Failed to establish connection after {max_reconnect_attempts + 1} attempts",
                    "last_error": last_connection_error,
                    "session_id": session_id,
                    "timestamp": time.time()
                })

        except Exception as e:
            logger.error(f"WebSocket handling error for session {session_id}: {e}")
            logger.error(traceback.format_exc())

            # Try to send error to client
            try:
                if is_client_connected:
                    await websocket.send_json({
                        "type": "connection_error",
                        "error": "unhandled_exception",
                        "message": str(e),
                        "session_id": session_id,
                        "timestamp": time.time()
                    })
            except Exception:
                pass  # Ignore error sending message

        finally:
            # Clean up resources
            await self.clean_stale_sessions()

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

    async def connect_to_upstream_ws(self, upstream_url: str, session_id: str, token: str) -> Any:
        """
        Connect to the upstream WebSocket service.

        Args:
            upstream_url: The URL of the upstream WebSocket service
            session_id: The session ID for authentication
            token: The authorization token (optional)

        Returns:
            The connected WebSocket client
        """
        try:
            # Construct headers
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            headers["X-Session-ID"] = session_id
            headers["X-Client-ID"] = f"api-gateway-{uuid.uuid4().hex[:8]}"

            # Connect to the upstream WebSocket
            logger.info(f"Connecting to upstream WebSocket: {upstream_url}")
            upstream_ws = await websockets.connect(
                upstream_url,
                extra_headers=headers
            )

            logger.info(f"Connected to upstream WebSocket for session {session_id}")
            return upstream_ws
        except websockets.exceptions.InvalidStatusCode as e:
            logger.error(f"Error connecting to upstream WebSocket: {e}")

            # For 401/403 errors, try connecting without auth token as fallback
            if e.status_code in (401, 403) and token:
                logger.info("Trying to connect without authentication token")
                try:
                    headers = {
                        "X-Session-ID": session_id,
                        "X-Client-ID": f"api-gateway-{uuid.uuid4().hex[:8]}"
                    }
                    upstream_ws = await websockets.connect(
                        upstream_url,
                        extra_headers=headers
                    )
                    logger.info(f"Connected to upstream WebSocket without auth for session {session_id}")
                    return upstream_ws
                except Exception as inner_e:
                    logger.error(f"Error connecting without auth token: {inner_e}")

            # Raise the original exception
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to upstream WebSocket: {e}")
            raise

    async def forward_to_upstream(self, websocket: WebSocket, upstream_ws: Any, session_id: str) -> None:
        """
        Forward messages from client to upstream service.

        Args:
            websocket: Client WebSocket connection
            upstream_ws: Upstream WebSocket connection
            session_id: Session ID for this connection
        """
        try:
            async for message in websocket.iter_text():
                if message == "ping":
                    await websocket.send_text("pong")
                    continue

                # Update last client message timestamp
                if session_id in self.connection_status:
                    self.connection_status[session_id]["last_client_message"] = time.time()

                # Forward the message directly to upstream
                try:
                    await upstream_ws.send(message)
                    logger.debug(f"Forwarded message to upstream: {message[:100]}...")
                except Exception as e:
                    # Log the error but propagate it so connection will be reset appropriately
                    logger.error(f"Error forwarding message to upstream: {e}")
                    error_message = {
                        "type": "error",
                        "code": "UPSTREAM_ERROR",
                        "message": f"Error forwarding message: {str(e)}"
                    }
                    await websocket.send_json(error_message)
                    # Propagate the error
                    raise
        except WebSocketDisconnect:
            logger.info(f"Client disconnected for session {session_id}")
            await self._handle_disconnect(session_id, upstream_ws)
        except ConnectionClosed:
            logger.info(f"Upstream connection closed for session {session_id}")
            await self._handle_disconnect(session_id, None, websocket)
        except Exception as e:
            logger.error(f"Error in forward_to_upstream: {e}")
            logger.error(traceback.format_exc())
            await self._handle_disconnect(session_id, upstream_ws, websocket)
            # Propagate the error
            raise

    async def forward_to_client(self, websocket: WebSocket, upstream_ws: Any, session_id: str) -> None:
        """
        Forward messages from upstream service to client with validation.

        Args:
            websocket: Client WebSocket connection
            upstream_ws: Upstream WebSocket connection
            session_id: Session ID for this connection
        """
        try:
            async for message in upstream_ws.iter_json():
                # Update last upstream message timestamp
                if session_id in self.connection_status:
                    self.connection_status[session_id]["last_upstream_message"] = time.time()

                try:
                    # Validate message structure
                    is_valid, error_message, _ = self._validate_message(json.dumps(message))
                    if not is_valid:
                        logger.warning(f"Invalid message from upstream: {error_message}")
                        # Send error to client but continue processing
                        error_response = {
                            "type": "error",
                            "code": "INVALID_MESSAGE",
                            "message": f"Invalid message from upstream: {error_message}"
                        }
                        await websocket.send_json(error_response)
                        continue

                    # Process any special messages (e.g., authentication)
                    if self._handle_special_messages(message, session_id):
                        continue

                    # Forward the message to the client
                    await websocket.send_json(message)
                    logger.debug(f"Forwarded message to client: {str(message)[:100]}...")
                except Exception as e:
                    logger.error(f"Error processing upstream message: {e}")
                    # Send error to client
                    try:
                        error_response = {
                            "type": "error",
                            "code": "MESSAGE_PROCESSING_ERROR",
                            "message": f"Error processing message: {str(e)}"
                        }
                        await websocket.send_json(error_response)
                    except Exception:
                        logger.error("Failed to send error to client")

                    # Continue processing other messages
                    continue
        except WebSocketDisconnect:
            logger.info(f"Client disconnected for session {session_id}")
            await self._handle_disconnect(session_id, upstream_ws)
        except ConnectionClosed:
            logger.info(f"Upstream connection closed for session {session_id}")
            await self._handle_disconnect(session_id, None, websocket)
        except Exception as e:
            logger.error(f"Error in forward_to_client: {e}")
            logger.error(traceback.format_exc())
            await self._handle_disconnect(session_id, upstream_ws, websocket)
            # Propagate the error
            raise

    async def heartbeat(self, upstream_ws: Any, interval: int = 30) -> None:
        """
        Send periodic heartbeats to keep connections alive.

        Args:
            upstream_ws: Upstream WebSocket connection
            interval: Interval in seconds between heartbeats
        """
        try:
            while True:
                await asyncio.sleep(interval)

                # Send heartbeat to upstream
                try:
                    await upstream_ws.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat()
                    })
                    logger.debug("Sent heartbeat to upstream service")
                except Exception as e:
                    logger.error(f"Error sending heartbeat to upstream: {e}")
                    raise
        except Exception as e:
            logger.error(f"Error in heartbeat task: {e}")
            raise

    async def process_message(
        self,
        message: Dict[str, Any],
        session_id: str,
        source: str = "client"
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Process and transform messages with error recovery.

        This method handles message preprocessing, normalization, and recovery from
        various error conditions.

        Args:
            message: The message dictionary to process
            session_id: The session ID associated with this message
            source: The source of the message ('client' or 'upstream')

        Returns:
            Tuple of (success, processed_message_or_error_response)
        """
        try:
            # Ensure required base fields
            if "message_id" not in message:
                message["message_id"] = str(uuid.uuid4())

            if "timestamp" not in message:
                message["timestamp"] = datetime.now().isoformat()

            if "session_id" not in message:
                message["session_id"] = session_id

            # Apply transformations based on message type
            message_type = message.get("type", "")

            if message_type == "event":
                # Normalize event types to lowercase with underscores
                if "event_type" in message:
                    message["event_type"] = message["event_type"].lower().replace(" ", "_")

                # Ensure data is always an object
                if "data" not in message:
                    message["data"] = {}
                elif not isinstance(message["data"], dict):
                    return False, {
                        "type": "error",
                        "error_code": "invalid_data_format",
                        "error_message": "Event data must be an object",
                        "source_message_id": message.get("message_id"),
                        "timestamp": datetime.now().isoformat(),
                        "recoverable": False
                    }

            elif message_type == "request":
                # Ensure parameters is an object
                if "parameters" not in message:
                    message["parameters"] = {}
                elif not isinstance(message["parameters"], dict):
                    return False, {
                        "type": "error",
                        "error_code": "invalid_parameters_format",
                        "error_message": "Request parameters must be an object",
                        "source_message_id": message.get("message_id"),
                        "timestamp": datetime.now().isoformat(),
                        "recoverable": False
                    }

                # Add source info for tracing
                message["_source"] = source

            elif message_type == "error":
                # Ensure error_details exists
                if "error_details" not in message:
                    message["error_details"] = {}

                # Log errors for monitoring
                logger.warning(f"Error message from {source} in session {session_id}: {message.get('error_code')} - {message.get('error_message')}")

            # Track message in metrics
            self._track_message_metrics(session_id, message_type, source)

            return True, message

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}\n{traceback.format_exc()}")
            return False, {
                "type": "error",
                "error_code": "message_processing_error",
                "error_message": f"Failed to process message: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "recoverable": False
            }

    def _track_message_metrics(self, session_id: str, message_type: str, source: str) -> None:
        """
        Track message metrics for monitoring and diagnostics.

        Args:
            session_id: The session ID
            message_type: The message type
            source: The message source
        """
        # Initialize session metrics if not existing
        if session_id not in self.client_metadata:
            self.client_metadata[session_id] = {
                "connected_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "reconnect_count": 0,
                "client_info": {},
                "message_counts": {}
            }

        if "message_counts" not in self.client_metadata[session_id]:
            self.client_metadata[session_id]["message_counts"] = {}

        metrics = self.client_metadata[session_id]["message_counts"]

        # Update metrics for this message type and source
        key = f"{source}_{message_type}"
        if key not in metrics:
            metrics[key] = 0
        metrics[key] += 1

        # Update overall counts
        total_key = f"{source}_total"
        if total_key not in metrics:
            metrics[total_key] = 0
        metrics[total_key] += 1

        # Update timestamp
        self.client_metadata[session_id]["last_activity"] = datetime.now().isoformat()

    async def _handle_disconnect(self, session_id: str, upstream_ws: Optional[Any] = None, websocket: Optional[WebSocket] = None) -> None:
        """
        Handle the disconnection of a WebSocket connection.

        Args:
            session_id: The session ID
            upstream_ws: The upstream WebSocket connection (optional)
            websocket: The client WebSocket connection (optional)
        """
        try:
            # Update connection status
            if session_id in self.connection_status:
                self.connection_status[session_id]["client_connected"] = False
                self.connection_status[session_id]["upstream_connected"] = False
                self.connection_status[session_id]["disconnected_at"] = time.time()

                # Calculate session duration if we have starting data
                if "last_client_message" in self.connection_status[session_id]:
                    start_time = self.connection_status[session_id].get("connected_at", self.connection_status[session_id]["last_client_message"])
                    self.connection_status[session_id]["session_duration"] = time.time() - start_time

                # Log connection summary
                logger.info(f"WebSocket session {session_id} ended: duration={self.connection_status[session_id].get('session_duration', 0):.2f}s, "
                        f"messages_sent={self.connection_status[session_id].get('messages_sent', 0)}, messages_received={self.connection_status[session_id].get('messages_received', 0)}")

            # Clean up resources
            await self.clean_stale_sessions()

            # Notify client of disconnection if websocket is available
            if websocket:
                try:
                    await websocket.send_json({
                        "type": "connection_status",
                        "status": "upstream_disconnected",
                        "session_id": session_id,
                        "timestamp": time.time(),
                        "error": "upstream_disconnected"
                    })
                except Exception as e:
                    logger.error(f"Failed to send disconnect notification: {e}")

        except Exception as e:
            logger.error(f"Error handling disconnection: {e}")
            logger.error(traceback.format_exc())

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

# Create a global instance
proxy = WebSocketProxy()
