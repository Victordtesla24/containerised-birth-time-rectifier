#!/usr/bin/env python3
"""
Integration test for real-time WebSocket API endpoints via API Gateway.
Tests the WebSocket communication for birth chart generation and verification.
"""

import os
import json
import pytest
import logging
import asyncio
import websockets
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Import test utilities
from tests.utils.test_helpers import get_test_sequence, update_test_sequence

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_websocket")

# Load test data
TEST_DATA_PATH = Path(__file__).parents[2] / "test_data" / "birth_rectification" / "test_data.json"
with open(TEST_DATA_PATH, "r") as f:
    TEST_DATA = json.load(f)


class WebSocketClient:
    """Simple WebSocket client for testing API Gateway WebSocket endpoints."""

    def __init__(self, ws_url: str):
        """Initialize the WebSocket client."""
        self.ws_url = ws_url
        self.session_id = None
        self.connected = False
        self.websocket = None
        self.response_queue = asyncio.Queue()
        self.message_handler_task = None

    async def connect(self, session_id: Optional[str] = None):
        """Connect to the WebSocket server with optional session ID."""
        self.session_id = session_id
        if session_id:
            connect_url = f"{self.ws_url}?session_id={session_id}"
        else:
            connect_url = self.ws_url

        try:
            self.websocket = await websockets.connect(connect_url)
            self.connected = True
            # Start message handler
            self.message_handler_task = asyncio.create_task(self._message_handler())
            logger.info(f"Connected to WebSocket at {connect_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.websocket:
            if self.message_handler_task:
                self.message_handler_task.cancel()
                try:
                    await self.message_handler_task
                except asyncio.CancelledError:
                    pass
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from WebSocket")

    async def _message_handler(self):
        """Background task to handle incoming messages."""
        try:
            if self.websocket is None:
                logger.error("Cannot handle messages: WebSocket is None")
                return

            while True:
                message = await self.websocket.recv()
                await self.response_queue.put(message)
        except asyncio.CancelledError:
            logger.debug("Message handler cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in message handler: {e}")

    async def send_message(self, message_type: str, data: Dict[str, Any]):
        """Send a message to the WebSocket server."""
        if not self.connected or self.websocket is None:
            logger.error("Cannot send message: Not connected or WebSocket is None")
            return False

        message = {
            "type": message_type,
            "data": data
        }

        try:
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent message: {message_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def wait_for_message(self, message_type: Optional[str] = None, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Wait for a message of specified type from the WebSocket server."""
        try:
            start_time = asyncio.get_event_loop().time()
            while True:
                remaining_time = start_time + timeout - asyncio.get_event_loop().time()
                if remaining_time <= 0:
                    logger.warning(f"Timeout waiting for message type: {message_type}")
                    return None

                try:
                    message_json = await asyncio.wait_for(self.response_queue.get(), timeout=remaining_time)
                except asyncio.TimeoutError:
                    return None

                try:
                    message = json.loads(message_json)
                    if message_type is None or message.get("type") == message_type:
                        logger.debug(f"Received expected message: {message.get('type')}")
                        return message
                    logger.debug(f"Skipping message of type: {message.get('type')}")
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON message: {message_json}")
        except Exception as e:
            logger.error(f"Error waiting for message: {e}")
            return None


@pytest.mark.asyncio
async def test_websocket_chart_generation():
    """
    Test WebSocket integration for chart generation and verification.

    This test:
    1. Connects to the WebSocket API gateway
    2. Creates a session
    3. Sends birth details to generate a chart
    4. Receives chart generation progress updates
    5. Validates the final chart data
    """
    # Arrange
    test_sequence = get_test_sequence()
    birth_details = test_sequence.get("birth_details", TEST_DATA["birth_details"])

    # Get the WebSocket URL from environment or use localhost
    ws_url = os.environ.get("WS_URL", "ws://localhost:8000/ws")

    # Create a client and connect
    client = WebSocketClient(ws_url)
    connected = await client.connect()
    assert connected, "Failed to connect to WebSocket"

    try:
        # Step 1: Initialize session if we don't have one
        if not test_sequence.get("session_id"):
            await client.send_message("session.init", {})
            response = await client.wait_for_message("session.initialized")
            assert response, "No session initialization response received"
            assert "data" in response, "Session response missing data"
            assert "session_id" in response["data"], "Session response missing session_id"

            session_id = response["data"]["session_id"]
            logger.info(f"WebSocket session initialized with ID: {session_id}")

            # Update test sequence with session ID
            test_sequence["session_id"] = session_id
            update_test_sequence(test_sequence, persist=True)
        else:
            session_id = test_sequence["session_id"]
            logger.info(f"Using existing session ID: {session_id}")

        # Step 2: Send chart generation request
        chart_request = {
            "birth_details": {
                "birth_date": birth_details["date"],
                "birth_time": birth_details["time"],
                "latitude": birth_details["latitude"],
                "longitude": birth_details["longitude"],
                "timezone": birth_details["timezone"],
                "location": birth_details["place"]
            },
            "verify_with_openai": True,
            "use_mock_openai": False,
            "session_id": session_id
        }

        logger.info(f"Generating chart via WebSocket for {birth_details['place']} at {birth_details['date']} {birth_details['time']}")
        await client.send_message("chart.generate", chart_request)

        # Step 3: Wait for chart generation progress updates
        chart_started = False
        chart_data = None
        timeout_seconds = 30  # Set a reasonable timeout

        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            response = await client.wait_for_message(timeout=5.0)
            if not response:
                continue

            message_type = response.get("type")

            if message_type == "chart.generation.started":
                chart_started = True
                logger.info("Chart generation started")
            elif message_type == "chart.generation.progress":
                progress = response.get("data", {}).get("progress", 0)
                status = response.get("data", {}).get("status", "")
                logger.info(f"Chart generation progress: {progress}% - {status}")
            elif message_type == "chart.generation.completed":
                logger.info("Chart generation completed successfully")
                chart_data = response.get("data", {})
                break
            elif message_type == "chart.generation.failed":
                error = response.get("data", {}).get("error", "Unknown error")
                assert False, f"Chart generation failed: {error}"

        # Step 4: Validate the chart data
        assert chart_started, "Chart generation was never started"
        assert chart_data, "No chart data was received"
        assert "chart_id" in chart_data, "Chart data missing chart_id"

        # Check if chart data is nested
        actual_chart_data = chart_data.get("chart_data", chart_data)

        # Validate essential chart components
        assert "planets" in actual_chart_data, "Chart data missing planets"
        assert "angles" in actual_chart_data, "Chart data missing angles"

        # Check for verification info if present
        if "verification" in actual_chart_data:
            verification = actual_chart_data["verification"]
            logger.info(f"Chart verification status: {verification.get('status')}")
            logger.info(f"Verification confidence: {verification.get('confidence')}")

        # Store chart data for subsequent tests
        test_sequence.update({
            "chart_id": chart_data["chart_id"],
            "websocket_chart": chart_data,
            "test_stage": 5
        })
        update_test_sequence(test_sequence, persist=True)

        logger.info(f"Successfully generated chart via WebSocket with ID: {chart_data['chart_id']}")

    finally:
        # Disconnect the WebSocket client
        await client.disconnect()


@pytest.mark.asyncio
async def test_websocket_chart_verification():
    """
    Test WebSocket integration for stand-alone chart verification.

    This test:
    1. Connects to the WebSocket API gateway
    2. Retrieves an existing chart
    3. Requests OpenAI verification of the chart
    4. Receives verification progress updates
    5. Validates the verification results
    """
    # Arrange
    test_sequence = get_test_sequence()
    session_id = test_sequence.get("session_id")
    chart_id = test_sequence.get("chart_id")

    # Skip if we don't have a chart ID
    if not chart_id:
        pytest.skip("No chart ID from previous tests")

    # Get the WebSocket URL from environment or use localhost
    ws_url = os.environ.get("WS_URL", "ws://localhost:8000/ws")

    # Create a client and connect
    client = WebSocketClient(ws_url)
    if session_id:
        connected = await client.connect(session_id)
    else:
        connected = await client.connect()
    assert connected, "Failed to connect to WebSocket"

    try:
        # Step 1: Request verification for the existing chart
        verify_request = {
            "chart_id": chart_id,
            "session_id": session_id,
            "use_mock_openai": False
        }

        logger.info(f"Requesting verification for chart {chart_id} via WebSocket")
        await client.send_message("chart.verify", verify_request)

        # Step 2: Wait for verification progress updates
        verification_started = False
        verification_data = None
        timeout_seconds = 60  # Allow more time for OpenAI verification

        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            response = await client.wait_for_message(timeout=5.0)
            if not response:
                continue

            message_type = response.get("type")

            if message_type == "chart.verification.started":
                verification_started = True
                logger.info("Chart verification started")
            elif message_type == "chart.verification.progress":
                progress = response.get("data", {}).get("progress", 0)
                status = response.get("data", {}).get("status", "")
                logger.info(f"Verification progress: {progress}% - {status}")
            elif message_type == "chart.verification.completed":
                logger.info("Chart verification completed successfully")
                verification_data = response.get("data", {})
                break
            elif message_type == "chart.verification.failed":
                error = response.get("data", {}).get("error", "Unknown error")
                assert False, f"Chart verification failed: {error}"

        # Step 3: Validate the verification data
        assert verification_started, "Chart verification was never started"
        assert verification_data, "No verification data was received"

        # Check the verification results
        verification = verification_data.get("verification", {})
        assert "status" in verification, "Verification missing status"

        logger.info(f"Final verification status: {verification.get('status')}")

        # If OpenAI verification was successful, check the details
        if verification.get("verified_with_openai", False):
            assert "confidence" in verification, "Verification missing confidence score"
            assert "corrections_applied" in verification, "Verification missing corrections_applied flag"

            confidence = verification.get("confidence", 0)
            logger.info(f"Verification confidence: {confidence}")

            if verification.get("corrections_applied", False):
                assert "corrections" in verification, "Verification missing corrections list"
                corrections = verification.get("corrections", [])
                for correction in corrections:
                    logger.info(f"Correction applied: {correction}")

        # Store verification results for subsequent tests
        test_sequence.update({
            "websocket_verification": verification_data,
            "test_stage": 6
        })
        update_test_sequence(test_sequence, persist=True)

        logger.info("Successfully completed WebSocket chart verification test")

    finally:
        # Disconnect the WebSocket client
        await client.disconnect()


if __name__ == "__main__":
    # Run these tests standalone for debugging
    asyncio.run(test_websocket_chart_generation())
    asyncio.run(test_websocket_chart_verification())
