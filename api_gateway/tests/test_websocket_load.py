"""
Load tests for the WebSocket functionality.

These tests verify that the WebSocket implementation can handle
multiple concurrent connections and maintain performance under load.
"""

import asyncio
import json
import logging
import os
import pytest
import time
import uuid
from typing import List, Dict, Any

import websockets
from websockets.exceptions import ConnectionClosed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("websocket_load_test")

# Test configuration
WS_URL = os.getenv("WS_URL", "ws://localhost:9000/ws")
NUM_CLIENTS = int(os.getenv("NUM_CLIENTS", "10"))
TEST_DURATION = int(os.getenv("TEST_DURATION", "10"))  # seconds
MESSAGE_INTERVAL = float(os.getenv("MESSAGE_INTERVAL", "0.5"))  # seconds


class WebSocketClient:
    """WebSocket client for load testing."""

    def __init__(self, url: str, client_id: str):
        """Initialize the WebSocket client."""
        self.url = url
        self.client_id = client_id
        self.connection = None
        self.connected = False
        self.messages_sent = 0
        self.messages_received = 0
        self.errors = 0
        self.latencies = []

    async def connect(self) -> bool:
        """Connect to the WebSocket server."""
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
        """Send a message to the WebSocket server."""
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

    async def receive_message(self) -> Dict[str, Any] | None:
        """Receive a message from the WebSocket server."""
        if not self.connection or not self.connected:
            logger.error(f"Client {self.client_id} not connected, cannot receive message")
            self.errors += 1
            return {}

        try:
            message_str = await asyncio.wait_for(self.connection.recv(), timeout=5.0)
            receive_time = time.time()
            message = json.loads(message_str)
            self.messages_received += 1

            # Calculate latency if the message has a timestamp
            if "timestamp" in message:
                latency = receive_time - message["timestamp"]
                self.latencies.append(latency)
                logger.debug(f"Client {self.client_id} received message with latency {latency:.4f}s")
            else:
                logger.debug(f"Client {self.client_id} received message: {message}")

            return message
        except asyncio.TimeoutError:
            logger.warning(f"Client {self.client_id} timeout waiting for message")
            self.errors += 1
            return {}
        except ConnectionClosed:
            logger.warning(f"Client {self.client_id} connection closed while receiving")
            self.connected = False
            self.errors += 1
            return {}
        except Exception as e:
            logger.error(f"Client {self.client_id} error receiving message: {e}")
            self.errors += 1
            return None

    async def run(self, duration: int):
        """Run the client for the specified duration."""
        if not await self.connect():
            return

        start_time = time.time()
        try:
            while time.time() - start_time < duration:
                # Send a test message
                message = {
                    "type": "test",
                    "client_id": self.client_id,
                    "sequence": self.messages_sent,
                    "data": f"Test message from client {self.client_id}"
                }
                if await self.send_message(message):
                    # Wait for response
                    response = await self.receive_message()
                    if not response:
                        # If no response, wait a bit before trying again
                        await asyncio.sleep(0.1)

                # Wait before sending next message
                await asyncio.sleep(MESSAGE_INTERVAL)
        except Exception as e:
            logger.error(f"Client {self.client_id} error during run: {e}")
            self.errors += 1
        finally:
            await self.disconnect()

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
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


async def run_load_test(num_clients: int, duration: int) -> Dict[str, Any]:
    """Run a load test with the specified number of clients."""
    logger.info(f"Starting load test with {num_clients} clients for {duration} seconds")

    # Create clients
    clients = []
    for i in range(num_clients):
        client_id = f"load-test-{uuid.uuid4().hex[:8]}"
        client = WebSocketClient(WS_URL, client_id)
        clients.append(client)

    # Run clients concurrently
    tasks = [client.run(duration) for client in clients]
    await asyncio.gather(*tasks)

    # Collect statistics
    total_sent = 0
    total_received = 0
    total_errors = 0
    all_latencies = []

    client_stats = []
    for client in clients:
        stats = client.get_stats()
        client_stats.append(stats)
        total_sent += stats["messages_sent"]
        total_received += stats["messages_received"]
        total_errors += stats["errors"]
        all_latencies.extend(client.latencies)

    # Calculate aggregate statistics
    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
    max_latency = max(all_latencies) if all_latencies else 0
    min_latency = min(all_latencies) if all_latencies else 0
    success_rate = (total_received / total_sent * 100) if total_sent > 0 else 0

    # Return test results
    return {
        "num_clients": num_clients,
        "duration": duration,
        "total_sent": total_sent,
        "total_received": total_received,
        "total_errors": total_errors,
        "avg_latency": avg_latency,
        "max_latency": max_latency,
        "min_latency": min_latency,
        "success_rate": success_rate,
        "client_stats": client_stats,
    }


@pytest.mark.asyncio
async def test_websocket_load():
    """Run a WebSocket load test."""
    # Skip this test in CI environments unless explicitly enabled
    if os.getenv("CI") and not os.getenv("RUN_LOAD_TESTS"):
        pytest.skip("Load tests are disabled in CI environment")

    # Run the load test
    results = await run_load_test(NUM_CLIENTS, TEST_DURATION)

    # Log the results
    logger.info(f"Load test results: {json.dumps(results, indent=2)}")

    # Verify the results
    assert results["total_sent"] > 0, "No messages were sent"
    assert results["total_received"] > 0, "No messages were received"
    assert results["success_rate"] > 90, f"Success rate too low: {results['success_rate']}%"
    assert results["avg_latency"] < 0.5, f"Average latency too high: {results['avg_latency']}s"


if __name__ == "__main__":
    """Run the load test directly."""
    asyncio.run(run_load_test(NUM_CLIENTS, TEST_DURATION))
