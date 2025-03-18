# WebSocket Testing Framework

This directory contains a modular WebSocket testing framework for the Birth Time Rectifier API Gateway. The framework provides comprehensive testing capabilities for WebSocket functionality, including:

- Unit tests for WebSocket proxy functionality
- Integration tests for end-to-end WebSocket communication
- Load tests for WebSocket performance under load
- Event tests for WebSocket event-based functionality
- Interactive test client for manual testing

## Framework Components

The framework consists of the following components:

- `client.py`: WebSocket client implementation for testing
- `load_tester.py`: Load testing functionality for WebSocket performance
- `event_tester.py`: Event testing functionality for WebSocket events

## Usage

### Using the Consolidated Test Script

The easiest way to use the WebSocket testing framework is through the consolidated test script:

```bash
# Run all tests
./scripts/websocket_test.py --all

# Run specific tests
./scripts/websocket_test.py --unit --integration --load

# Run load tests with custom parameters
./scripts/websocket_test.py --load --num-clients 10 --duration 30 --interval 0.2

# Run event tests with custom API and WebSocket URLs
./scripts/websocket_test.py --event --api-url http://localhost:9000/api --ws-url ws://localhost:9000/ws

# Open the WebSocket test client in a browser
./scripts/websocket_test.py --client

# Run the bash test script for WebSocket connections
./scripts/websocket_test.py --bash

# Show help
./scripts/websocket_test.py --help
```

### Using the WebSocket Client Directly

You can also use the WebSocket client directly in your own code:

```python
import asyncio
from api_gateway.tests.websocket.client import WebSocketClient

async def main():
    # Create a WebSocket client
    client = WebSocketClient("ws://localhost:9000/ws", "test-client")

    # Connect to the WebSocket server
    if await client.connect():
        # Send a message
        await client.send_message({"type": "test", "data": "Hello, world!"})

        # Receive a message
        message = await client.receive_message()
        print(f"Received message: {message}")

        # Disconnect
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### Using the Load Tester

You can use the load tester to test WebSocket performance under load:

```python
import asyncio
from api_gateway.tests.websocket.load_tester import WebSocketLoadTester

async def main():
    # Create a load tester with 10 clients
    tester = WebSocketLoadTester("ws://localhost:9000/ws", 10, 0.5)

    # Run the load test for 30 seconds
    results = await tester.run_test(30)

    # Print the results
    print(f"Total messages sent: {results['total_sent']}")
    print(f"Total messages received: {results['total_received']}")
    print(f"Success rate: {results['success_rate']:.2f}%")
    print(f"Average latency: {results['avg_latency']:.4f}s")

if __name__ == "__main__":
    asyncio.run(main())
```

### Using the Event Tester

You can use the event tester to test WebSocket event-based functionality:

```python
import asyncio
from api_gateway.tests.websocket.event_tester import WebSocketEventTester

async def main():
    # Create an event tester
    tester = WebSocketEventTester("http://localhost:9000/api", "ws://localhost:9000/ws")

    # Run the event test
    results = await tester.run_event_test()

    # Print the results
    print(f"Expected events: {results['total_expected']}")
    print(f"Received events: {results['total_received']}")
    print(f"Success rate: {results['success_rate']:.2f}%")

if __name__ == "__main__":
    asyncio.run(main())
```

## Running Tests with pytest

The framework includes pytest tests for unit, integration, and load testing:

```bash
# Run unit tests
python -m pytest api_gateway/tests/test_websocket_proxy.py -v

# Run integration tests
python -m pytest api_gateway/tests/test_websocket_integration.py -v

# Run load tests
python -m pytest api_gateway/tests/test_websocket_load.py -v
```

## Interactive Testing

For interactive testing, you can use the WebSocket test client in your browser:

```bash
# Open the WebSocket test client
./scripts/websocket_test.py --client
```

Or you can use the bash test script for WebSocket connections:

```bash
# Run the bash test script
./scripts/websocket_test.py --bash
```

## Environment Variables

The following environment variables can be used to configure the tests:

- `WS_URL`: WebSocket URL (default: `ws://localhost:9000/ws`)
- `API_URL`: API URL (default: `http://localhost:9000/api`)
- `NUM_CLIENTS`: Number of clients for load tests (default: `5`)
- `TEST_DURATION`: Duration for load tests in seconds (default: `5`)
- `MESSAGE_INTERVAL`: Interval between messages in seconds (default: `0.5`)
