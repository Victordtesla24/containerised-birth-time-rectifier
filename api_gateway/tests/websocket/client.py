"""
WebSocket Client for Birth Time Rectifier API Gateway

This module provides a WebSocket client for testing WebSocket functionality
in the Birth Time Rectifier API Gateway.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable

import websockets
from websockets.exceptions import ConnectionClosed

# Configure logging
logger = logging.getLogger("websocket.client")

class WebSocketClient:
    """WebSocket client for testing."""

    def __init__(self, url: str, client_id: Optional[str] = None):
        """
        Initialize the WebSocket client.

        Args:
            url: The WebSocket URL to connect to
            client_id: Optional client ID for identification
        """
        self.url = url
        self.client_id = client_id or f"client-{int(time.time())}"
        self.connection = None
        self.connected = False
        self.messages_sent = 0
        self.messages_received = 0
        self.errors = 0
        self.latencies = []
        self.received_events = []
        self.event_handlers = {}

    async def connect(self) -> bool:
        """
        Connect to the WebSocket server.

        Returns:
            bool: True if connection was successful, False otherwise
        """
        try:
            self.connection = await websockets.connect(self.url)
            self.connected = True
            logger.info(f"Client {self.client_id} connected to {self.url}")
            return True
        except Exception as e:
            logger.error(f"Client {self.client_id} failed to connect: {e}")
            self.errors += 1
            return False

    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.connection and self.connected:
            try:
                await self.connection.close()
                logger.info(f"Client {self.client_id} disconnected")
            except Exception as e:
                logger.error(f"Client {self.client_id} error during disconnect: {e}")
                self.errors += 1
            finally:
                self.connected = False

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a message to the WebSocket server.

        Args:
            message: The message to send

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        if not self.connection or not self.connected:
            logger.error(f"Client {self.client_id} not connected, cannot send message")
            self.errors += 1
            return False

        try:
            # Add timestamp for latency calculation
            message["timestamp"] = time.time()
            await self.connection.send(json.dumps(message))
            self.messages_sent += 1
            return True
        except Exception as e:
            logger.error(f"Client {self.client_id} error sending message: {e}")
            self.errors += 1
            return False

    async def receive_message(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Receive a message from the WebSocket server.

        Args:
            timeout: Timeout in seconds

        Returns:
            Optional[Dict[str, Any]]: The received message, or None if no message was received
        """
        if not self.connection or not self.connected:
            logger.error(f"Client {self.client_id} not connected, cannot receive message")
            self.errors += 1
            return None

        try:
            message_str = await asyncio.wait_for(self.connection.recv(), timeout=timeout)
            receive_time = time.time()
            message = json.loads(message_str)
            self.messages_received += 1
            self.received_events.append(message)

            # Calculate latency if the message has a timestamp
            if "timestamp" in message:
                latency = receive_time - message["timestamp"]
                self.latencies.append(latency)
                logger.debug(f"Client {self.client_id} received message with latency {latency:.4f}s")
            else:
                logger.debug(f"Client {self.client_id} received message: {message}")

            # Process event handlers
            event_type = message.get("type")
            if event_type and event_type in self.event_handlers:
                await self.event_handlers[event_type](message)

            return message
        except asyncio.TimeoutError:
            logger.warning(f"Client {self.client_id} timeout waiting for message")
            self.errors += 1
            return None
        except ConnectionClosed:
            logger.warning(f"Client {self.client_id} connection closed while receiving")
            self.connected = False
            self.errors += 1
            return None
        except Exception as e:
            logger.error(f"Client {self.client_id} error receiving message: {e}")
            self.errors += 1
            return None

    def register_event_handler(self, event_type: str, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        """
        Register an event handler for a specific event type.

        Args:
            event_type: The event type to handle
            handler: The handler function
        """
        self.event_handlers[event_type] = handler

    async def listen(self, duration: Optional[float] = None):
        """
        Listen for messages from the WebSocket server.

        Args:
            duration: Optional duration in seconds to listen for
        """
        if not self.connected:
            if not await self.connect():
                return

        start_time = time.time()
        try:
            while self.connected and (duration is None or time.time() - start_time < duration):
                try:
                    message = await self.receive_message()
                    if not message and self.connected:
                        # If no message, wait a bit before trying again
                        await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Client {self.client_id} error receiving message: {e}")
                    self.errors += 1
                    # If we're disconnected, break the loop
                    if not self.connected:
                        break
                    await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Client {self.client_id} error during listen: {e}")
            self.errors += 1
        finally:
            if duration is not None or not self.connected:
                await self.disconnect()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.

        Returns:
            Dict[str, Any]: Client statistics
        """
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        max_latency = max(self.latencies) if self.latencies else 0
        min_latency = min(self.latencies) if self.latencies else 0

        return {
            "client_id": self.client_id,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "errors": self.errors,
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "min_latency": min_latency,
        }

    def get_received_events(self) -> List[Dict[str, Any]]:
        """
        Get all received events.

        Returns:
            List[Dict[str, Any]]: List of received events
        """
        return self.received_events
