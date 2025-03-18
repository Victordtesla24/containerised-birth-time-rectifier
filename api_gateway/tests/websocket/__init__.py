"""
WebSocket Testing Framework for Birth Time Rectifier API Gateway

This package provides a comprehensive framework for testing WebSocket functionality
in the Birth Time Rectifier API Gateway, including:

- Unit tests for WebSocket proxy functionality
- Integration tests for end-to-end WebSocket communication
- Load tests for WebSocket performance under load
- Interactive test client for manual testing
"""

from api_gateway.tests.websocket.client import WebSocketClient
from api_gateway.tests.websocket.load_tester import WebSocketLoadTester
from api_gateway.tests.websocket.event_tester import WebSocketEventTester

__all__ = [
    'WebSocketClient',
    'WebSocketLoadTester',
    'WebSocketEventTester',
]
