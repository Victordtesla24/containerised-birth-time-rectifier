"""
WebSocket Load Tester for Birth Time Rectifier API Gateway

This module provides a load tester for WebSocket functionality
in the Birth Time Rectifier API Gateway.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional

from api_gateway.tests.websocket.client import WebSocketClient

# Configure logging
logger = logging.getLogger("websocket.load_tester")

class WebSocketLoadTester:
    """WebSocket load tester for performance testing."""

    def __init__(self, ws_url: str, num_clients: int = 10, message_interval: float = 0.5):
        """
        Initialize the WebSocket load tester.

        Args:
            ws_url: The WebSocket URL to connect to
            num_clients: Number of clients to create
            message_interval: Interval between messages in seconds
        """
        self.ws_url = ws_url
        self.num_clients = num_clients
        self.message_interval = message_interval
        self.clients: List[WebSocketClient] = []
        self.results: Dict[str, Any] = {}

    async def setup_clients(self):
        """Set up WebSocket clients."""
        self.clients = []
        for i in range(self.num_clients):
            client_id = f"load-test-{uuid.uuid4().hex[:8]}"
            client = WebSocketClient(self.ws_url, client_id)
            self.clients.append(client)

    async def run_client(self, client: WebSocketClient, duration: float):
        """
        Run a single client for the specified duration.

        Args:
            client: The WebSocket client
            duration: Duration in seconds
        """
        if not await client.connect():
            return

        start_time = time.time()
        try:
            while time.time() - start_time < duration:
                # Send a test message
                message = {
                    "type": "test",
                    "client_id": client.client_id,
                    "sequence": client.messages_sent,
                    "data": f"Test message from client {client.client_id}"
                }
                if await client.send_message(message):
                    # Wait for response
                    response = await client.receive_message()
                    if not response:
                        # If no response, wait a bit before trying again
                        await asyncio.sleep(0.1)

                # Wait before sending next message
                await asyncio.sleep(self.message_interval)
        except Exception as e:
            logger.error(f"Client {client.client_id} error during run: {e}")
        finally:
            await client.disconnect()

    async def run_test(self, duration: float) -> Dict[str, Any]:
        """
        Run a load test with the specified number of clients.

        Args:
            duration: Duration in seconds

        Returns:
            Dict[str, Any]: Test results
        """
        logger.info(f"Starting load test with {self.num_clients} clients for {duration} seconds")

        # Set up clients
        await self.setup_clients()

        # Run clients concurrently
        tasks = [self.run_client(client, duration) for client in self.clients]
        await asyncio.gather(*tasks)

        # Collect statistics
        return self.collect_stats()

    def collect_stats(self) -> Dict[str, Any]:
        """
        Collect statistics from all clients.

        Returns:
            Dict[str, Any]: Test results
        """
        total_sent = 0
        total_received = 0
        total_errors = 0
        all_latencies = []

        client_stats = []
        for client in self.clients:
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
        results = {
            "num_clients": self.num_clients,
            "total_sent": total_sent,
            "total_received": total_received,
            "total_errors": total_errors,
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "min_latency": min_latency,
            "success_rate": success_rate,
            "client_stats": client_stats,
        }

        # Log summary
        logger.info(f"Load test completed with {self.num_clients} clients")
        logger.info(f"Total messages sent: {total_sent}")
        logger.info(f"Total messages received: {total_received}")
        logger.info(f"Success rate: {success_rate:.2f}%")
        logger.info(f"Average latency: {avg_latency:.4f}s")

        return results
