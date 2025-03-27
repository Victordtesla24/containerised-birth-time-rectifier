"""
API test client for making HTTP and WebSocket requests in tests.

This module provides a client for making HTTP and WebSocket requests
in integration tests.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple, List, Union, Callable
import aiohttp
from aiohttp import ClientSession, WSMsgType, ClientWebSocketResponse

# Configure logging
logger = logging.getLogger(__name__)

class APITestClient:
    """
    Async API test client for making HTTP and WebSocket requests.

    This client supports:
    - HTTP requests with JSON payloads
    - WebSocket connections for real-time testing
    - Session tracking
    """

    def __init__(self, base_url: str, ws_url: Optional[str] = None):
        """
        Initialize the API test client.

        Args:
            base_url: Base URL for HTTP requests
            ws_url: Base URL for WebSocket connections (optional)
        """
        self.base_url = base_url
        self.ws_url = ws_url
        self.session_id = None
        self.headers = {"Content-Type": "application/json"}
        self._http_session = None
        self._ws_connection = None
        self._ws_messages = []
        self._ws_task = None

    def set_session_id(self, session_id: str) -> None:
        """
        Set the session ID for subsequent requests.

        Args:
            session_id: Session ID to use
        """
        self.session_id = session_id
        self.headers["X-Session-ID"] = session_id

    async def start(self) -> None:
        """Start the client session."""
        if self._http_session is None:
            self._http_session = ClientSession(headers=self.headers)

    async def stop(self) -> None:
        """Stop the client session and clean up resources."""
        if self._ws_connection and not self._ws_connection.closed:
            await self._ws_connection.close()

        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        if self._http_session:
            await self._http_session.close()
            self._http_session = None

    async def __aenter__(self) -> 'APITestClient':
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
        """
        Make a GET request to the API.

        Args:
            path: API endpoint path
            params: Query parameters (optional)

        Returns:
            Tuple of (status_code, response_data)
        """
        await self.start()
        url = f"{self.base_url}{path}"

        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        async with self._http_session.get(url, params=params) as response:
            status = response.status
            try:
                data = await response.json()
            except Exception:
                data = {"text": await response.text()}

            return status, data

    async def post(self, path: str, data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Make a POST request to the API.

        Args:
            path: API endpoint path
            data: Request body data

        Returns:
            Tuple of (status_code, response_data)
        """
        await self.start()
        url = f"{self.base_url}{path}"

        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        async with self._http_session.post(url, json=data) as response:
            status = response.status
            try:
                resp_data = await response.json()
            except Exception:
                resp_data = {"text": await response.text()}

            return status, resp_data

    async def put(self, path: str, data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Make a PUT request to the API.

        Args:
            path: API endpoint path
            data: Request body data

        Returns:
            Tuple of (status_code, response_data)
        """
        await self.start()
        url = f"{self.base_url}{path}"

        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        async with self._http_session.put(url, json=data) as response:
            status = response.status
            try:
                resp_data = await response.json()
            except Exception:
                resp_data = {"text": await response.text()}

            return status, resp_data

    async def delete(self, path: str) -> Tuple[int, Dict[str, Any]]:
        """
        Make a DELETE request to the API.

        Args:
            path: API endpoint path

        Returns:
            Tuple of (status_code, response_data)
        """
        await self.start()
        url = f"{self.base_url}{path}"

        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        async with self._http_session.delete(url) as response:
            status = response.status
            try:
                data = await response.json()
            except Exception:
                data = {"text": await response.text()}

            return status, data

    async def connect_websocket(self, path: str = "") -> None:
        """
        Connect to the WebSocket API.

        Args:
            path: WebSocket endpoint path (added to ws_url)
        """
        if not self.ws_url:
            raise ValueError("WebSocket URL not provided")

        await self.start()

        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        # Construct the WebSocket URL
        ws_url = f"{self.ws_url}{path}"
        if self.session_id and "?" not in ws_url:
            ws_url += f"?session_id={self.session_id}"
        elif self.session_id:
            ws_url += f"&session_id={self.session_id}"

        # Connect to the WebSocket
        self._ws_connection = await self._http_session.ws_connect(ws_url)

        # Start the message handler task
        self._ws_task = asyncio.create_task(self._handle_ws_messages())

        logger.info(f"Connected to WebSocket at {ws_url}")

    async def _handle_ws_messages(self) -> None:
        """Handle incoming WebSocket messages."""
        if not self._ws_connection:
            return

        async for msg in self._ws_connection:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    self._ws_messages.append(data)
                    logger.debug(f"Received WebSocket message: {data}")
                except Exception as e:
                    logger.error(f"Error parsing WebSocket message: {e}")
                    self._ws_messages.append({"error": str(e), "raw": msg.data})
            elif msg.type == WSMsgType.ERROR:
                logger.error(f"WebSocket connection error: {msg.data}")
                break

    async def send_ws_message(self, data: Dict[str, Any]) -> None:
        """
        Send a message over the WebSocket connection.

        Args:
            data: Message data to send
        """
        if not self._ws_connection or self._ws_connection.closed:
            await self.connect_websocket()

        if not self._ws_connection:
            raise RuntimeError("WebSocket connection not initialized")

        await self._ws_connection.send_json(data)
        logger.debug(f"Sent WebSocket message: {data}")

    async def get_ws_messages(self, clear: bool = False) -> List[Dict[str, Any]]:
        """
        Get all received WebSocket messages.

        Args:
            clear: Whether to clear the message buffer after returning

        Returns:
            List of received WebSocket messages
        """
        messages = list(self._ws_messages)
        if clear:
            self._ws_messages.clear()
        return messages

    async def wait_for_ws_message(self,
                                 timeout: float = 5.0,
                                 predicate: Optional[Callable[[Dict[str, Any]], bool]] = None) -> Optional[Dict[str, Any]]:
        """
        Wait for a specific WebSocket message.

        Args:
            timeout: Maximum time to wait in seconds
            predicate: Function that returns True for the desired message

        Returns:
            The received message or None if timed out
        """
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # Check existing messages first
            for msg in self._ws_messages:
                if predicate is None or predicate(msg):
                    self._ws_messages.remove(msg)
                    return msg

            # Wait a bit and check again
            await asyncio.sleep(0.1)

        return None
