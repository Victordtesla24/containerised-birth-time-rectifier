"""
WebSocket Event Tester for Birth Time Rectifier API Gateway

This module provides functionality for testing WebSocket events
in the Birth Time Rectifier API Gateway.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional, Set

import aiohttp
from aiohttp import ClientTimeout

from api_gateway.tests.websocket.client import WebSocketClient

# Configure logging
logger = logging.getLogger("websocket.event_tester")

class WebSocketEventTester:
    """WebSocket event tester for testing event-based functionality."""

    def __init__(self, api_url: str, ws_url: str):
        """
        Initialize the WebSocket event tester.

        Args:
            api_url: The API URL for triggering events
            ws_url: The WebSocket URL for receiving events
        """
        # Ensure API URL points to the AI service for session initialization
        self.api_url = api_url.replace("/api", "")
        if not self.api_url.endswith("/"):
            self.api_url += "/"
        self.api_url += "api/v1"

        self.ws_url = ws_url
        self.session_id: Optional[str] = None
        self.client: Optional[WebSocketClient] = None
        self.expected_events: Set[str] = set()
        self.received_events: List[Dict[str, Any]] = []
        self.event_queue: Optional[asyncio.Queue] = None

    async def initialize_session(self) -> str:
        """
        Initialize a session and return the session ID.

        Returns:
            str: The session ID
        """
        logger.info("Initializing session")

        try:
            async with aiohttp.ClientSession() as session:
                try:
                    # Connect to the AI service session initialization endpoint
                    async with session.get(f"{self.api_url}/session/init", timeout=ClientTimeout(total=10)) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Error initializing session: {response.status} - {error_text}")
                            raise Exception(f"Failed to initialize session: {response.status} - {error_text}")

                        data = await response.json()
                        self.session_id = data.get("session_id")

                        if not self.session_id:
                            logger.error("No session ID returned")
                            raise Exception("No session ID returned")

                        logger.info(f"Session initialized with ID: {self.session_id}")
                        return self.session_id
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.error(f"Error connecting to API: {e}")
                    raise Exception(f"Failed to connect to API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def connect_websocket(self) -> WebSocketClient:
        """
        Connect to the WebSocket server.

        Returns:
            WebSocketClient: The WebSocket client
        """
        if not self.session_id:
            await self.initialize_session()

        ws_url = f"{self.ws_url}/{self.session_id}"
        logger.info(f"Connecting to WebSocket at {ws_url}")

        self.client = WebSocketClient(ws_url, f"event-test-{self.session_id}")
        if not await self.client.connect():
            raise Exception(f"Failed to connect to WebSocket at {ws_url}")

        logger.info("WebSocket connection established")
        return self.client

    async def start_event_listener(self):
        """Start listening for WebSocket events."""
        if not self.client or not self.client.connected:
            await self.connect_websocket()

        self.event_queue = asyncio.Queue()

        if self.event_queue is None:
            self.event_queue = asyncio.Queue()

        if self.client is not None:
            # Register event handler for all events
            async def event_handler(event: Dict[str, Any]):
                if self.event_queue is not None:
                    await self.event_queue.put(event)
                self.received_events.append(event)
                logger.info(f"Received event: {event.get('type', 'unknown')}")

            # Register the handler for all event types
            for event_type in ["geocode_completed", "validation_completed", "chart_generated",
                              "chart_retrieved", "questionnaire_started", "question_answered",
                              "questionnaire_completed", "heartbeat", "echo"]:
                self.client.register_event_handler(event_type, event_handler)

            # Start listening for events
            asyncio.create_task(self.client.listen())

    async def trigger_geocode_event(self) -> Dict[str, Any]:
        """
        Trigger a geocode event.

        Returns:
            Dict[str, Any]: The response data
        """
        logger.info("Triggering geocode event")
        self.expected_events.add("geocode_completed")

        # Real API call
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Session-ID": self.session_id
                }
                data = {
                    "query": "New York City"
                }

                async with session.post(
                    f"{self.api_url}/geocode",
                    headers=headers,
                    json=data,
                    timeout=ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error triggering geocode event: {response.status} - {error_text}")
                        return {}

                    result = await response.json()
                    logger.info("Geocode event triggered successfully")
                    return result
        except Exception as e:
            logger.error(f"Error in geocode event: {e}")
            return {}

    async def trigger_validation_event(self) -> Dict[str, Any]:
        """
        Trigger a chart validation event.

        Returns:
            Dict[str, Any]: The response data
        """
        logger.info("Triggering chart validation event")
        self.expected_events.add("validation_completed")

        # Real API call
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Session-ID": self.session_id
                }
                data = {
                    "date": "1990-01-01",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "timezone": "America/New_York"
                }

                async with session.post(
                    f"{self.api_url}/chart/validate",
                    headers=headers,
                    json=data,
                    timeout=ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error triggering validation event: {response.status} - {error_text}")
                        return {}

                    result = await response.json()
                    logger.info("Validation event triggered successfully")
                    return result
        except Exception as e:
            logger.error(f"Error in validation event: {e}")
            return {}

    async def trigger_chart_generation_event(self) -> Optional[str]:
        """
        Trigger a chart generation event and return the chart ID.

        Returns:
            Optional[str]: The chart ID, or None if the event failed
        """
        logger.info("Triggering chart generation event")
        self.expected_events.add("chart_generated")

        # Real API call
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Session-ID": self.session_id
                }
                data = {
                    "date": "1990-01-01",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "timezone": "America/New_York"
                }

                async with session.post(
                    f"{self.api_url}/chart/generate",
                    headers=headers,
                    json=data,
                    timeout=ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error triggering chart generation event: {response.status} - {error_text}")
                        return None

                    result = await response.json()
                    chart_id = result.get("chart_id")

                    if not chart_id:
                        logger.error("No chart ID returned")
                        return None

                    logger.info(f"Chart generation event triggered successfully with ID: {chart_id}")
                    return chart_id
        except Exception as e:
            logger.error(f"Error in chart generation event: {e}")
            return None

    async def trigger_chart_retrieval_event(self, chart_id: str) -> Dict[str, Any]:
        """
        Trigger a chart retrieval event.

        Args:
            chart_id: The chart ID to retrieve

        Returns:
            Dict[str, Any]: The response data
        """
        logger.info("Triggering chart retrieval event")
        self.expected_events.add("chart_retrieved")

        # Real API call
        try:
            async with aiohttp.ClientSession() as session:
                headers = {}
                if self.session_id:
                    headers["X-Session-ID"] = self.session_id

                async with session.get(
                    f"{self.api_url}/chart/{chart_id}",
                    headers=headers,
                    timeout=ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error triggering chart retrieval event: {response.status} - {error_text}")
                        return {}

                    result = await response.json()
                    logger.info("Chart retrieval event triggered successfully")
                    return result
        except Exception as e:
            logger.error(f"Error in chart retrieval event: {e}")
            return {}

    async def trigger_questionnaire_events(self, chart_id: str) -> Optional[str]:
        """
        Trigger questionnaire events and return the questionnaire ID.

        Args:
            chart_id: The chart ID to use for the questionnaire

        Returns:
            Optional[str]: The questionnaire ID, or None if the event failed
        """
        logger.info("Triggering questionnaire events")
        self.expected_events.add("questionnaire_started")
        self.expected_events.add("question_answered")
        self.expected_events.add("questionnaire_completed")

        # Real API call
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "X-Session-ID": self.session_id
                }
                data = {
                    "chart_id": chart_id
                }

                # Start questionnaire
                async with session.post(
                    f"{self.api_url}/questionnaire/ws",
                    headers=headers,
                    json=data,
                    timeout=ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error triggering questionnaire start event: {response.status} - {error_text}")
                        return None

                    result = await response.json()
                    questionnaire_id = result.get("questionnaire_id")

                    if not questionnaire_id:
                        logger.error("No questionnaire ID returned")
                        return None

                    logger.info(f"Questionnaire start event triggered successfully with ID: {questionnaire_id}")

                    # Wait a moment for the event to be processed
                    await asyncio.sleep(1)

                    # Answer a question
                    answer_data = {
                        "question_id": "q_001",
                        "answer": "yes"
                    }

                    async with session.post(
                        f"{self.api_url}/questionnaire/ws/{questionnaire_id}/answer",
                        headers=headers,
                        json=answer_data,
                        timeout=ClientTimeout(total=10)
                    ) as answer_response:
                        if answer_response.status != 200:
                            error_text = await answer_response.text()
                            logger.error(f"Error triggering question answer event: {answer_response.status} - {error_text}")
                            return questionnaire_id

                        logger.info("Question answer event triggered successfully")

                        # Wait a moment for the event to be processed
                        await asyncio.sleep(1)

                        # Complete questionnaire
                        complete_data = {
                            "questionnaire_id": questionnaire_id
                        }

                        async with session.post(
                            f"{self.api_url}/questionnaire/ws/complete",
                            headers=headers,
                            json=complete_data,
                            timeout=ClientTimeout(total=10)
                        ) as complete_response:
                            if complete_response.status != 200:
                                error_text = await complete_response.text()
                                logger.error(f"Error triggering questionnaire completion event: {complete_response.status} - {error_text}")
                                return questionnaire_id

                            logger.info("Questionnaire completion event triggered successfully")
                            return questionnaire_id
        except Exception as e:
            logger.error(f"Error in questionnaire events: {e}")
            return None

    def check_received_events(self) -> Dict[str, Any]:
        """
        Check which expected events were received.

        Returns:
            Dict[str, Any]: Statistics about received events
        """
        logger.info("Checking received events")

        received_types = {event.get("type") for event in self.received_events if event.get("type")}

        # Check each expected event
        missing_events = self.expected_events - received_types
        received_expected = self.expected_events.intersection(received_types)

        # Calculate statistics
        total_expected = len(self.expected_events)
        total_received = len(received_types)
        total_received_expected = len(received_expected)

        # Log results
        for event_type in self.expected_events:
            if event_type in received_types:
                logger.info(f"✓ Received expected event: {event_type}")
            else:
                logger.warning(f"✗ Missing expected event: {event_type}")

        logger.info(f"Summary: Received {total_received_expected}/{total_expected} expected events")

        return {
            "total_expected": total_expected,
            "total_received": total_received,
            "total_received_expected": total_received_expected,
            "success_rate": (total_received_expected / total_expected * 100) if total_expected > 0 else 0,
            "missing_events": list(missing_events),
            "received_events": list(received_types),
        }

    async def run_event_test(self) -> Dict[str, Any]:
        """
        Run a complete event test.

        Returns:
            Dict[str, Any]: Test results
        """
        try:
            # Initialize session
            await self.initialize_session()

            # Start event listener
            await self.start_event_listener()

            # Wait a moment for the WebSocket connection to establish
            await asyncio.sleep(2)

            # Trigger events
            await self.trigger_geocode_event()
            await asyncio.sleep(1)

            await self.trigger_validation_event()
            await asyncio.sleep(1)

            chart_id = await self.trigger_chart_generation_event()
            if chart_id:
                await asyncio.sleep(1)

                await self.trigger_chart_retrieval_event(chart_id)
                await asyncio.sleep(1)

                await self.trigger_questionnaire_events(chart_id)
                await asyncio.sleep(1)

            # Wait a moment for all events to be processed
            await asyncio.sleep(2)

            # Check received events
            results = self.check_received_events()

            # Clean up
            if self.client:
                await self.client.disconnect()

            return results

        except Exception as e:
            logger.error(f"Error in event test: {e}")
            if self.client:
                await self.client.disconnect()
            raise
