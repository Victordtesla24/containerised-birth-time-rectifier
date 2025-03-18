#!/usr/bin/env python3
"""
Consolidated WebSocket Test Script for Birth Time Rectifier API Gateway

This script provides a unified interface for testing WebSocket functionality
in the Birth Time Rectifier API Gateway, including:

- Unit tests for WebSocket proxy functionality
- Integration tests for end-to-end WebSocket communication
- Load tests for WebSocket performance under load
- Event tests for WebSocket event-based functionality
- Interactive test client for manual testing
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from typing import Dict, Any, List, Optional

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("websocket-test")

# Default configuration
DEFAULT_API_URL = "http://localhost:9000/api"
DEFAULT_WS_URL = "ws://localhost:9000/ws"
DEFAULT_NUM_CLIENTS = 5
DEFAULT_TEST_DURATION = 5
DEFAULT_MESSAGE_INTERVAL = 0.5

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(color: str, message: str):
    """Print a message with color"""
    print(f"{color}{message}{Colors.ENDC}")

def print_header(message: str):
    """Print a header message"""
    print_colored(Colors.BLUE, f"\n{'=' * 50}")
    print_colored(Colors.BLUE, f"  {message}")
    print_colored(Colors.BLUE, f"{'=' * 50}\n")

def check_api_gateway():
    """Check if the API Gateway is running"""
    print_header("Checking API Gateway Status")

    try:
        import requests
        response = requests.get("http://localhost:9000/health", timeout=5)
        if response.status_code == 200:
            print_colored(Colors.GREEN, "API Gateway is running")
            return True
        else:
            print_colored(Colors.RED, f"API Gateway returned status code {response.status_code}")
            return False
    except Exception as e:
        print_colored(Colors.RED, f"Error connecting to API Gateway: {e}")
        print_colored(Colors.YELLOW, "Please start the API Gateway with:")
        print_colored(Colors.YELLOW, "  docker-compose up -d api_gateway")
        return False

def run_unit_tests():
    """Run WebSocket unit tests"""
    print_header("Running WebSocket Unit Tests")

    result = subprocess.run(
        ["python", "-m", "pytest", "api_gateway/tests/test_websocket_proxy.py", "-v"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print_colored(Colors.RED, "Errors:")
        print(result.stderr)

    if result.returncode == 0:
        print_colored(Colors.GREEN, "Unit tests passed")
        return True
    else:
        print_colored(Colors.RED, "Unit tests failed")
        return False

def run_integration_tests():
    """Run WebSocket integration tests"""
    print_header("Running WebSocket Integration Tests")

    result = subprocess.run(
        ["python", "-m", "pytest", "api_gateway/tests/test_websocket_integration.py", "-v"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print_colored(Colors.RED, "Errors:")
        print(result.stderr)

    if result.returncode == 0:
        print_colored(Colors.GREEN, "Integration tests passed")
        return True
    else:
        print_colored(Colors.RED, "Integration tests failed")
        return False

def run_load_tests(num_clients: int, duration: int, message_interval: float):
    """Run WebSocket load tests"""
    print_header(f"Running WebSocket Load Tests with {num_clients} clients for {duration} seconds")

    # Set environment variables for the test
    env = os.environ.copy()
    env["WS_URL"] = DEFAULT_WS_URL
    env["NUM_CLIENTS"] = str(num_clients)
    env["TEST_DURATION"] = str(duration)
    env["MESSAGE_INTERVAL"] = str(message_interval)

    result = subprocess.run(
        ["python", "-m", "pytest", "api_gateway/tests/test_websocket_load.py", "-v"],
        env=env,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print_colored(Colors.RED, "Errors:")
        print(result.stderr)

    if result.returncode == 0:
        print_colored(Colors.GREEN, "Load tests passed")
        return True
    else:
        print_colored(Colors.RED, "Load tests failed")
        return False

async def run_event_tests(api_url: str, ws_url: str):
    """Run WebSocket event tests"""
    print_header("Running WebSocket Event Tests")

    try:
        # Import the WebSocketEventTester class
        from api_gateway.tests.websocket.event_tester import WebSocketEventTester

        # Create an event tester
        tester = WebSocketEventTester(api_url, ws_url)

        # Run the event test
        results = await tester.run_event_test()

        # Print the results
        print_colored(Colors.CYAN, f"Expected events: {results['total_expected']}")
        print_colored(Colors.CYAN, f"Received events: {results['total_received']}")
        print_colored(Colors.CYAN, f"Received expected events: {results['total_received_expected']}")
        print_colored(Colors.CYAN, f"Success rate: {results['success_rate']:.2f}%")

        if results["missing_events"]:
            print_colored(Colors.YELLOW, "Missing events:")
            for event in results["missing_events"]:
                print_colored(Colors.YELLOW, f"  - {event}")

        if results["success_rate"] >= 90:
            print_colored(Colors.GREEN, "Event tests passed")
            return True
        else:
            print_colored(Colors.RED, "Event tests failed")
            return False
    except Exception as e:
        print_colored(Colors.RED, f"Error running event tests: {e}")
        return False

def open_test_client():
    """Open the WebSocket test client in a browser"""
    print_header("Opening WebSocket Test Client")

    url = "http://localhost:9000/websocket_test.html"
    print_colored(Colors.CYAN, f"Opening {url} in your browser")

    if sys.platform == "darwin":  # macOS
        subprocess.run(["open", url])
    elif sys.platform == "win32":  # Windows
        subprocess.run(["start", url], shell=True)
    elif sys.platform.startswith("linux"):  # Linux
        subprocess.run(["xdg-open", url])
    else:
        print_colored(Colors.YELLOW, f"Please open {url} in your browser")

def run_bash_test_script():
    """Run the bash test script for WebSocket connections"""
    print_header("Running Bash Test Script for WebSocket Connections")

    result = subprocess.run(
        ["bash", "test_scripts/test_websocket_connection.sh"],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print_colored(Colors.RED, "Errors:")
        print(result.stderr)

    if result.returncode == 0:
        print_colored(Colors.GREEN, "Bash test script completed successfully")
        return True
    else:
        print_colored(Colors.RED, "Bash test script failed")
        return False

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="WebSocket Test Script")
    parser.add_argument("--unit", action="store_true", help="Run unit tests")
    parser.add_argument("--integration", action="store_true", help="Run integration tests")
    parser.add_argument("--load", action="store_true", help="Run load tests")
    parser.add_argument("--event", action="store_true", help="Run event tests")
    parser.add_argument("--client", action="store_true", help="Open test client in browser")
    parser.add_argument("--bash", action="store_true", help="Run bash test script")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API URL")
    parser.add_argument("--ws-url", default=DEFAULT_WS_URL, help="WebSocket URL")
    parser.add_argument("--num-clients", type=int, default=DEFAULT_NUM_CLIENTS, help="Number of clients for load tests")
    parser.add_argument("--duration", type=int, default=DEFAULT_TEST_DURATION, help="Duration for load tests")
    parser.add_argument("--interval", type=float, default=DEFAULT_MESSAGE_INTERVAL, help="Message interval for load tests")

    args = parser.parse_args()

    # Print header
    print_colored(Colors.BOLD, "Birth Time Rectifier WebSocket Test")
    print_colored(Colors.BOLD, "===================================")

    # Check if the API Gateway is running
    if not check_api_gateway():
        return 1

    # Determine which tests to run
    run_all = args.all or not (args.unit or args.integration or args.load or args.event or args.client or args.bash)

    # Run the selected tests
    if args.unit or run_all:
        run_unit_tests()

    if args.integration or run_all:
        run_integration_tests()

    if args.load or run_all:
        run_load_tests(args.num_clients, args.duration, args.interval)

    if args.event or run_all:
        await run_event_tests(args.api_url, args.ws_url)

    if args.client or run_all:
        open_test_client()

    if args.bash or run_all:
        run_bash_test_script()

    print_colored(Colors.BOLD, "\nAll tests completed!")
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
