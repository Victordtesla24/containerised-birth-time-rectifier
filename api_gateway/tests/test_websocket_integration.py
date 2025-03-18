"""
Integration tests for the WebSocket functionality.

These tests verify that the WebSocket endpoints work correctly
in an end-to-end scenario with the API Gateway and AI Service.
"""

import asyncio
import json
import os
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
import websockets

from api_gateway.main import app
from api_gateway.websocket_proxy import proxy


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_websockets_connect():
    """Mock the websockets.connect function."""
    with patch("websockets.connect") as mock_connect:
        # Create a mock WebSocket connection
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(return_value=json.dumps({
            "type": "echo",
            "message": "Echo: test message",
            "timestamp": time.time()
        }))
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()

        # Make the mock_connect function return the mock WebSocket
        mock_connect.return_value = mock_ws

        yield mock_connect, mock_ws


def test_websocket_endpoint_exists(test_client):
    """Test that the WebSocket endpoints exist."""
    # Check for WebSocket endpoints
    websocket_routes = []
    for route in app.routes:
        # Check if it's a WebSocket route
        if str(route).startswith("WebSocketRoute"):
            # Extract path from string representation
            route_str = str(route)
            if "/ws" in route_str:
                websocket_routes.append(route_str)

    # Verify we have two WebSocket routes
    assert len(websocket_routes) == 2

    # Verify one route is for /ws and one is for /ws/{session_id}
    assert any("/ws'" in route or '"/ws"' in route for route in websocket_routes)
    assert any("/ws/{session_id}" in route for route in websocket_routes)


@pytest.mark.asyncio
async def test_websocket_connection(mock_websockets_connect):
    """
    Test WebSocket connection.

    This test simulates a client connecting to the WebSocket endpoint
    and verifies that the connection is properly established and
    messages are forwarded to the AI service.
    """
    mock_connect, mock_ai_ws = mock_websockets_connect

    # Create a mock client WebSocket
    mock_client_ws = AsyncMock()
    mock_client_ws.accept = AsyncMock()
    mock_client_ws.receive_text = AsyncMock(side_effect=[
        json.dumps({"type": "test", "message": "test message"}),
        asyncio.CancelledError()  # To break the loop
    ])
    mock_client_ws.send_text = AsyncMock()
    mock_client_ws.send_json = AsyncMock()
    mock_client_ws.close = AsyncMock()

    # Call the WebSocket endpoint directly
    session_id = "test-session"

    # Patch the proxy.connect method to use our mocks
    with patch.object(proxy, "connect", AsyncMock()) as mock_proxy_connect:
        # Set up the mock to call the real _connect_to_ai_service_with_retry but with our mock
        async def mock_connect_impl(websocket, session_id):
            # Store the original method
            original_method = proxy._connect_to_ai_service_with_retry

            # Replace it with a mock that returns our mock AI WebSocket
            proxy._connect_to_ai_service_with_retry = AsyncMock(return_value=mock_ai_ws)

            # Call the real connect method
            result = await original_method(session_id)

            # Restore the original method
            proxy._connect_to_ai_service_with_retry = original_method

            return result

        mock_proxy_connect.side_effect = mock_connect_impl

        # Create a task to simulate the WebSocket endpoint
        task = asyncio.create_task(
            proxy.connect(mock_client_ws, session_id)
        )

        # Allow the task to run
        await asyncio.sleep(0.1)

        # Verify the WebSocket was accepted
        mock_client_ws.accept.assert_called_once()

        # Verify the AI service connection was attempted
        mock_connect.assert_called_once()

        # Simulate receiving a message from the client
        await mock_client_ws.receive_text.side_effect[0]

        # Allow the message to be processed
        await asyncio.sleep(0.1)

        # Verify the message was forwarded to the AI service
        mock_ai_ws.send.assert_called_once_with(
            json.dumps({"type": "test", "message": "test message"})
        )

        # Simulate receiving a response from the AI service
        await mock_ai_ws.recv()

        # Allow the response to be processed
        await asyncio.sleep(0.1)

        # Verify the response was forwarded to the client
        mock_client_ws.send_text.assert_called_once_with(
            json.dumps({
                "type": "echo",
                "message": "Echo: test message",
                "timestamp": mock_ai_ws.recv.return_value["timestamp"]
            })
        )

        # Cancel the task to clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_websocket_disconnect(mock_websockets_connect):
    """
    Test WebSocket disconnection.

    This test simulates a client disconnecting from the WebSocket endpoint
    and verifies that the connection is properly cleaned up.
    """
    mock_connect, mock_ai_ws = mock_websockets_connect

    # Create a mock client WebSocket
    mock_client_ws = AsyncMock()
    mock_client_ws.accept = AsyncMock()
    mock_client_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
    mock_client_ws.send_json = AsyncMock()
    mock_client_ws.close = AsyncMock()

    # Call the WebSocket endpoint directly
    session_id = "test-session"

    # Patch the proxy.connect method to use our mocks
    with patch.object(proxy, "connect", AsyncMock()) as mock_proxy_connect:
        # Set up the mock to call the real _connect_to_ai_service_with_retry but with our mock
        async def mock_connect_impl(websocket, session_id):
            # Store the original method
            original_method = proxy._connect_to_ai_service_with_retry

            # Replace it with a mock that returns our mock AI WebSocket
            proxy._connect_to_ai_service_with_retry = AsyncMock(return_value=mock_ai_ws)

            # Call the real connect method
            result = await original_method(session_id)

            # Restore the original method
            proxy._connect_to_ai_service_with_retry = original_method

            return result

        mock_proxy_connect.side_effect = mock_connect_impl

        # Create a task to simulate the WebSocket endpoint
        task = asyncio.create_task(
            proxy.connect(mock_client_ws, session_id)
        )

        # Allow the task to run
        await asyncio.sleep(0.1)

        # Verify the WebSocket was accepted
        mock_client_ws.accept.assert_called_once()

        # Verify the AI service connection was attempted
        mock_connect.assert_called_once()

        # Simulate client disconnection
        with pytest.raises(WebSocketDisconnect):
            await mock_client_ws.receive_text()

        # Allow the disconnection to be processed
        await asyncio.sleep(0.1)

        # Verify the AI service connection was closed
        mock_ai_ws.close.assert_called_once()

        # Cancel the task to clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_websocket_heartbeat(mock_websockets_connect):
    """
    Test WebSocket heartbeat.

    This test verifies that heartbeat messages are sent to the client
    to keep the connection alive.
    """
    mock_connect, mock_ai_ws = mock_websockets_connect

    # Create a mock client WebSocket
    mock_client_ws = AsyncMock()
    mock_client_ws.accept = AsyncMock()
    mock_client_ws.receive_text = AsyncMock(side_effect=asyncio.TimeoutError())
    mock_client_ws.send_json = AsyncMock()
    mock_client_ws.close = AsyncMock()

    # Call the WebSocket endpoint directly
    session_id = "test-session"

    # Patch the proxy.connect method to use our mocks
    with patch.object(proxy, "connect", AsyncMock()) as mock_proxy_connect:
        # Set up the mock to call the real _connect_to_ai_service_with_retry but with our mock
        async def mock_connect_impl(websocket, session_id):
            # Store the original method
            original_method = proxy._connect_to_ai_service_with_retry

            # Replace it with a mock that returns our mock AI WebSocket
            proxy._connect_to_ai_service_with_retry = AsyncMock(return_value=mock_ai_ws)

            # Call the real connect method
            result = await original_method(session_id)

            # Restore the original method
            proxy._connect_to_ai_service_with_retry = original_method

            return result

        mock_proxy_connect.side_effect = mock_connect_impl

        # Create a task to simulate the WebSocket endpoint
        task = asyncio.create_task(
            proxy.connect(mock_client_ws, session_id)
        )

        # Allow the task to run for a short time
        await asyncio.sleep(1.5)  # WS_HEARTBEAT_INTERVAL is set to 1

        # Verify heartbeat messages were sent
        assert mock_client_ws.send_json.call_count >= 1

        # Verify the heartbeat message format
        call_args = mock_client_ws.send_json.call_args[0][0]
        assert call_args["type"] == "heartbeat"
        assert "timestamp" in call_args

        # Cancel the task to clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
