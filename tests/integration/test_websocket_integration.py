"""
Integration test for WebSocket connections as described in the "Enhanced Error Handling Sequence"
and "Consolidated API Questionnaire Flow" sections in the sequence diagram.

This test verifies that WebSocket connections are properly established and that real-time updates
are properly sent during the birth time rectification process.
"""

import pytest
import asyncio
import websockets
import json
import logging
import uuid
import os
import time
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required services
from ai_service.api.services.openai.service import OpenAIService
from ai_service.services.chart_service import ChartService
from ai_service.core.rectification.main import comprehensive_rectification
from ai_service.api.services.session_service import get_session_store

# Test data
TEST_BIRTH_DETAILS = {
    "birthDate": "1990-01-15",
    "birthTime": "08:30:00",
    "birthPlace": "Mumbai, India",
    "latitude": 19.0760,
    "longitude": 72.8777,
    "timezone": "Asia/Kolkata"
}

# WebSocket connection settings
WS_HOST = os.environ.get("WS_HOST", "localhost")
WS_PORT = int(os.environ.get("WS_PORT", "9001"))
WS_URL = f"ws://{WS_HOST}:{WS_PORT}/ws"

class WebSocketClient:
    """Simple WebSocket client for testing."""

    def __init__(self, url: str, session_id: Optional[str] = None):
        """Initialize the WebSocket client."""
        self.url = url
        self.session_id = session_id
        self.connection = None
        self.received_messages = []
        self.connected = False

    async def connect(self):
        """Connect to the WebSocket server."""
        try:
            # Add session ID to the URL if provided
            url = f"{self.url}/{self.session_id}" if self.session_id else self.url
            self.connection = await websockets.connect(url)
            self.connected = True
            logger.info(f"Connected to WebSocket at {url}")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise

    async def disconnect(self):
        """Disconnect from the WebSocket server."""
        if self.connection:
            await self.connection.close()
            self.connected = False
            logger.info("Disconnected from WebSocket")

    async def send(self, message: Dict[str, Any]):
        """Send a message to the WebSocket server."""
        if not self.connected or self.connection is None:
            raise ValueError("Not connected to WebSocket server")

        await self.connection.send(json.dumps(message))
        logger.info(f"Sent message: {message}")

    async def receive(self, timeout: float = 5.0):
        """Receive a message from the WebSocket server."""
        if not self.connected or self.connection is None:
            raise ValueError("Not connected to WebSocket server")

        try:
            # Set a timeout to prevent hanging
            message = await asyncio.wait_for(self.connection.recv(), timeout=timeout)
            data = json.loads(message)
            self.received_messages.append(data)
            logger.info(f"Received message: {data}")
            return data
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for message (after {timeout}s)")
            return None

    async def listen(self, duration: float = 10.0):
        """Listen for messages for a specific duration."""
        if not self.connected or self.connection is None:
            raise ValueError("Not connected to WebSocket server")

        start_time = time.time()
        logger.info(f"Listening for messages for {duration} seconds")

        while time.time() - start_time < duration:
            try:
                message = await asyncio.wait_for(self.connection.recv(), timeout=1.0)
                data = json.loads(message)
                self.received_messages.append(data)
                logger.info(f"Received message: {data}")
            except asyncio.TimeoutError:
                # Continue listening
                pass
            except Exception as e:
                logger.error(f"Error while listening: {e}")
                break

        logger.info(f"Finished listening. Received {len(self.received_messages)} messages.")
        return self.received_messages

@pytest.mark.asyncio
async def test_websocket_realtime_updates():
    """
    Test real-time updates via WebSocket during the rectification process.
    This follows the sequence diagram showing real-time updates during long-running processes.
    """
    logger.info("Starting WebSocket real-time updates test")

    # 1. Create a test session
    session_id = str(uuid.uuid4())
    session_store = get_session_store()
    await session_store.create_session(session_id, {
        "created_at": time.time(),
        "status": "active"
    })
    logger.info(f"Created test session with ID: {session_id}")

    # 2. Set up WebSocket client
    ws_client = WebSocketClient(WS_URL, session_id)
    try:
        await ws_client.connect()

        # Verify connection by receiving initial connection message
        initial_message = await ws_client.receive()
        assert initial_message is not None, "Should receive an initial connection message"
        assert "type" in initial_message, "Message should have a type"
        assert initial_message["type"] in ["connection", "welcome"], "Initial message should be a connection/welcome message"

        # 3. Start listening for messages in the background
        listen_task = asyncio.create_task(ws_client.listen(60.0))  # Listen for up to 60 seconds

        # 4. Trigger rectification process which should send progress updates
        # Create OpenAI service
        openai_service = OpenAIService()

        # Create chart service
        from ai_service.database.repositories import ChartRepository
        import asyncpg
        from ai_service.core.config import settings

        db_pool = await asyncpg.create_pool(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        chart_repository = ChartRepository(db_pool=db_pool)
        chart_service = ChartService(
            openai_service=openai_service,
            chart_repository=chart_repository
        )

        # Generate chart
        chart_result = await chart_service.generate_chart(
            birth_date=TEST_BIRTH_DETAILS["birthDate"],
            birth_time=TEST_BIRTH_DETAILS["birthTime"],
            latitude=TEST_BIRTH_DETAILS["latitude"],
            longitude=TEST_BIRTH_DETAILS["longitude"],
            timezone=TEST_BIRTH_DETAILS["timezone"],
            location=TEST_BIRTH_DETAILS["birthPlace"]
        )

        chart_id = chart_result["chart_id"]
        logger.info(f"Generated chart with ID: {chart_id}")

        # 5. Perform birth time rectification to trigger WebSocket updates
        logger.info("Starting birth time rectification to trigger WebSocket updates")
        birth_datetime = time.strptime(
            f"{TEST_BIRTH_DETAILS['birthDate']} {TEST_BIRTH_DETAILS['birthTime']}",
            "%Y-%m-%d %H:%M:%S"
        )

        # Create sample answers for rectification
        answers = [
            {
                "questionId": "q_career_1",
                "answer": "Yes, I had a significant career change",
                "confidence": 90
            },
            {
                "questionId": "q_relationship_1",
                "answer": "Got married in 2015",
                "confidence": 85
            }
        ]

        # Perform rectification (this should trigger WebSocket updates)
        await chart_service.rectify_chart(
            chart_id=chart_id,
            questionnaire_id=session_id,
            answers=answers
        )

        # 6. Wait for all WebSocket messages
        logger.info("Waiting for WebSocket messages...")
        await asyncio.sleep(5)  # Give some time for messages to be sent

        # Cancel the listen task to get the messages received so far
        listen_task.cancel()
        try:
            await listen_task
        except asyncio.CancelledError:
            pass

        # 7. Verify we received progress updates
        messages = ws_client.received_messages
        logger.info(f"Received {len(messages)} messages")

        # Check for rectification progress messages
        progress_messages = [msg for msg in messages if msg.get("type") == "progress" or "progress" in msg.get("data", {}).get("type", "")]
        logger.info(f"Found {len(progress_messages)} progress messages")

        # We should have received at least one progress message
        assert len(progress_messages) > 0, "Should receive at least one progress message during rectification"

        # 8. Check for completion message
        completion_messages = [msg for msg in messages if "complete" in msg.get("type", "") or "complete" in msg.get("data", {}).get("type", "")]
        logger.info(f"Found {len(completion_messages)} completion messages")

        # We should have received a completion message
        assert len(completion_messages) > 0, "Should receive a completion message when rectification is done"

        logger.info("WebSocket real-time updates test completed successfully")
    finally:
        # Clean up WebSocket connection
        await ws_client.disconnect()

if __name__ == "__main__":
    # Allow running the test directly
    asyncio.run(pytest.main(["-xvs", __file__]))
