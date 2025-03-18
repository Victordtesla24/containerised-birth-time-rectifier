"""
Unit tests for the WebSocket proxy functionality.

These tests verify that the WebSocket proxy correctly handles connections,
message forwarding, and error scenarios.
"""

import asyncio
import json
import os
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import WebSocket, WebSocketDisconnect, status
from fastapi.testclient import TestClient
import websockets
from websockets.exceptions import ConnectionClosed

from api_gateway.websocket_proxy import WebSocketProxy, proxy

# Set environment variables for testing
os.environ["WS_RETRY_ATTEMPTS"] = "2"
os.environ["WS_RETRY_DELAY"] = "0.1"
os.environ["WS_PING_INTERVAL"] = "1"
os.environ["WS_PING_TIMEOUT"] = "1"
os.environ["WS_HEARTBEAT_INTERVAL"] = "1"


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.receive_text = AsyncMock()
        self.send_text = AsyncMock()
        self.send_json = AsyncMock()


class MockWebSocketClientProtocol:
    """Mock WebSocketClientProtocol for testing."""

    def __init__(self):
        self.close = AsyncMock()
        self.recv = AsyncMock()
        self.send = AsyncMock()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    return MockWebSocket()


@pytest.fixture
def mock_ai_websocket():
    """Create a mock AI WebSocket."""
    return MockWebSocketClientProtocol()


@pytest.mark.asyncio
async def test_connect_success(mock_websocket, mock_ai_websocket):
    """Test successful WebSocket connection."""
    # Create a new WebSocketProxy instance for testing
    ws_proxy = WebSocketProxy()

    # Mock the connect_to_ai_service_with_retry method
    ws_proxy._connect_to_ai_service_with_retry = AsyncMock(return_value=mock_ai_websocket)

    # Call connect
    session_id = await ws_proxy.connect(mock_websocket, "test-session")

    # Verify the WebSocket was accepted
    mock_websocket.accept.assert_called_once()

    # Verify the connection was established
    assert session_id == "test-session"
    assert session_id in ws_proxy.active_connections
    assert ws_proxy.connection_status[session_id] is True

    # Verify tasks were created
    assert session_id in ws_proxy.tasks
    assert len(ws_proxy.tasks[session_id]) == 2
    assert session_id in ws_proxy.heartbeat_tasks

    # Verify connection confirmation was sent
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == "connection_status"
    assert call_args["status"] == "connected"
    assert call_args["session_id"] == "test-session"

    # Clean up
    await ws_proxy.disconnect(session_id)


@pytest.mark.asyncio
async def test_connect_failure(mock_websocket):
    """Test WebSocket connection failure."""
    # Create a new WebSocketProxy instance for testing
    ws_proxy = WebSocketProxy()

    # Mock the connect_to_ai_service_with_retry method to return None (failure)
    ws_proxy._connect_to_ai_service_with_retry = AsyncMock(return_value=None)

    # Call connect
    session_id = await ws_proxy.connect(mock_websocket, "test-session")

    # Verify the WebSocket was accepted
    mock_websocket.accept.assert_called_once()

    # Verify the WebSocket was closed with error code
    mock_websocket.close.assert_called_once_with(code=status.WS_1011_INTERNAL_ERROR)

    # Verify no connection was established
    assert session_id == "test-session"
    assert session_id not in ws_proxy.active_connections
    assert session_id not in ws_proxy.connection_status


@pytest.mark.asyncio
async def test_connect_to_ai_service_with_retry_success():
    """Test successful connection to AI service with retry."""
    # Create a new WebSocketProxy instance for testing
    ws_proxy = WebSocketProxy()

    # Mock websockets.connect
    mock_connect = AsyncMock()
    mock_ws = MockWebSocketClientProtocol()
    mock_connect.return_value = mock_ws

    # Patch websockets.connect
    with patch("websockets.connect", mock_connect):
        # Call connect_to_ai_service_with_retry
        result = await ws_proxy._connect_to_ai_service_with_retry("test-session")

        # Verify websockets.connect was called
        mock_connect.assert_called_once()
        assert result == mock_ws


@pytest.mark.asyncio
async def test_connect_to_ai_service_with_retry_failure():
    """Test connection to AI service with retry failure."""
    # Create a new WebSocketProxy instance for testing
    ws_proxy = WebSocketProxy()

    # Mock websockets.connect to raise an exception
    mock_connect = AsyncMock(side_effect=Exception("Connection failed"))

    # Patch websockets.connect
    with patch("websockets.connect", mock_connect):
        # Call connect_to_ai_service_with_retry
        result = await ws_proxy._connect_to_ai_service_with_retry("test-session")

        # Verify websockets.connect was called multiple times (retry)
        assert mock_connect.call_count == 2  # WS_RETRY_ATTEMPTS is set to 2
        assert result is None


@pytest.mark.asyncio
async def test_disconnect(mock_websocket, mock_ai_websocket):
    """Test WebSocket disconnection."""
    # Create a new WebSocketProxy instance for testing
    ws_proxy = WebSocketProxy()

    # Set up active connection
    session_id = "test-session"
    ws_proxy.active_connections[session_id] = (mock_websocket, mock_ai_websocket)
    ws_proxy.connection_status[session_id] = True

    # Create mock tasks
    mock_task1 = MagicMock()
    mock_task1.done.return_value = False
    mock_task1.cancel = MagicMock()
    mock_task2 = MagicMock()
    mock_task2.done.return_value = False
    mock_task2.cancel = MagicMock()
    ws_proxy.tasks[session_id] = [mock_task1, mock_task2]

    # Create mock heartbeat task
    mock_heartbeat_task = MagicMock()
    mock_heartbeat_task.done.return_value = False
    mock_heartbeat_task.cancel = MagicMock()
    ws_proxy.heartbeat_tasks[session_id] = mock_heartbeat_task

    # Create message queues
    ws_proxy.message_queues[f"{session_id}_client"] = asyncio.Queue()
    ws_proxy.message_queues[f"{session_id}_ai"] = asyncio.Queue()

    # Call disconnect
    await ws_proxy.disconnect(session_id)

    # Verify connections were closed
    mock_websocket.close.assert_called_once()
    mock_ai_websocket.close.assert_called_once()

    # Verify tasks were cancelled
    mock_task1.cancel.assert_called_once()
    mock_task2.cancel.assert_called_once()
    mock_heartbeat_task.cancel.assert_called_once()

    # Verify resources were cleaned up
    assert session_id not in ws_proxy.active_connections
    assert session_id not in ws_proxy.tasks
    assert session_id not in ws_proxy.heartbeat_tasks
    assert f"{session_id}_client" not in ws_proxy.message_queues
    assert f"{session_id}_ai" not in ws_proxy.message_queues
    assert session_id not in ws_proxy.connection_status


@pytest.mark.asyncio
async def test_forward_messages_client_to_ai(mock_websocket, mock_ai_websocket):
    """Test forwarding messages from client to AI service."""
    # Create a new WebSocketProxy instance for testing
    ws_proxy = WebSocketProxy()

    # Set up active connection
    session_id = "test-session"
    ws_proxy.active_connections[session_id] = (mock_websocket, mock_ai_websocket)
    ws_proxy.connection_status[session_id] = True

    # Create message queue
    message_queue = asyncio.Queue()

    # Set up mock to receive one message then raise an exception to end the loop
    mock_websocket.receive_text.side_effect = [
        asyncio.Future(),  # This future will be set to "test message" below
        WebSocketDisconnect()
    ]

    # Create a task for _forward_messages
    task = asyncio.create_task(
        ws_proxy._forward_messages(
            mock_websocket, mock_ai_websocket, message_queue, f"client-to-ai-{session_id}"
        )
    )

    # Allow the task to start and reach the first receive_text call
    await asyncio.sleep(0.1)

    # Set the result of the future to simulate receiving a message
    mock_websocket.receive_text.side_effect[0].set_result('{"type": "test", "data": "test data"}')

    # Allow the task to process the message
    await asyncio.sleep(0.1)

    # Verify the message was forwarded
    mock_ai_websocket.send.assert_called_once_with('{"type": "test", "data": "test data"}')

    # Verify the message was put in the queue
    assert message_queue.qsize() == 1
    message = await message_queue.get()
    assert message == '{"type": "test", "data": "test data"}'

    # Cancel the task to clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_heartbeat_monitor(mock_websocket, mock_ai_websocket):
    """Test heartbeat monitor."""
    # Create a new WebSocketProxy instance for testing
    ws_proxy = WebSocketProxy()

    # Set up active connection
    session_id = "test-session"
    ws_proxy.active_connections[session_id] = (mock_websocket, mock_ai_websocket)
    ws_proxy.connection_status[session_id] = True

    # Create a task for _heartbeat_monitor
    task = asyncio.create_task(
        ws_proxy._heartbeat_monitor(session_id, mock_websocket, mock_ai_websocket)
    )

    # Allow the task to run for a short time
    await asyncio.sleep(1.5)  # WS_HEARTBEAT_INTERVAL is set to 1

    # Verify heartbeat was sent
    assert mock_websocket.send_json.call_count >= 1
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == "heartbeat"
    assert "timestamp" in call_args

    # Simulate heartbeat failure
    mock_websocket.send_json.side_effect = Exception("Heartbeat failed")

    # Allow the task to run for a short time
    await asyncio.sleep(1.5)

    # Verify connection was marked as inactive
    assert ws_proxy.connection_status[session_id] is False

    # Cancel the task to clean up
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_global_proxy_instance():
    """Test that the global proxy instance is created."""
    assert proxy is not None
    assert isinstance(proxy, WebSocketProxy)
