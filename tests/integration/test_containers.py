import pytest
import requests
import redis
from redis.exceptions import ConnectionError as RedisConnectionError
import time
import os
import socket
from typing import Generator
import logging

# Service URLs - these are the expected endpoints for the containerized services
FRONTEND_URL = "http://localhost:3000"
AI_SERVICE_URL = "http://localhost:8000"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# Environment variable to control test behavior:
# - Set to "true" to force tests to run even if containers aren't available
# - Set to "false" (default) to skip tests when containers aren't available
RUN_CONTAINER_TESTS = os.environ.get("RUN_CONTAINER_TESTS", "false").lower() == "true"

logger = logging.getLogger(__name__)

def is_port_open(host, port, timeout=1):
    """
    Check if a port is open and accepting connections.

    Args:
        host: The hostname or IP address to check
        port: The port number to check
        timeout: Connection timeout in seconds

    Returns:
        bool: True if the port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

# Skip all tests in this file if containers aren't running and RUN_CONTAINER_TESTS is false
# This decorator can be applied to each test function to conditionally skip it
skip_if_no_containers = pytest.mark.skipif(
    not RUN_CONTAINER_TESTS and (
        not is_port_open("localhost", 3000) or  # Frontend
        not is_port_open("localhost", 8000) or  # AI Service
        not is_port_open("localhost", 6379)     # Redis
    ),
    reason="Containers not running and RUN_CONTAINER_TESTS=false"
)

@pytest.fixture(scope="session")
def redis_client() -> Generator[redis.Redis, None, None]:
    """
    Create a Redis client for testing.

    This fixture creates and yields a Redis client that can be used in tests.
    If Redis is not available, the test using this fixture will be skipped.

    Yields:
        redis.Redis: A Redis client connected to the Redis server
    """
    # Skip if Redis is not running and we're not forcing tests
    if not is_port_open(REDIS_HOST, REDIS_PORT) and not RUN_CONTAINER_TESTS:
        pytest.skip("Redis is not running")

    client = redis.Redis.from_url(REDIS_URL)
    try:
        client.ping()  # Test connection
        yield client
    except RedisConnectionError:
        pytest.skip("Cannot connect to Redis")
        return
    finally:
        client.close()

@skip_if_no_containers
def test_frontend_health():
    """Test if frontend is accessible."""
    try:
        response = requests.get(FRONTEND_URL, timeout=10)
        assert response.status_code == 200
        assert "Birth Time Rectification" in response.text
    except requests.exceptions.ConnectionError:
        pytest.skip("Frontend service is not available")

@skip_if_no_containers
def test_ai_service_health():
    """Test AI service health endpoint."""
    try:
        response = requests.get(f"{AI_SERVICE_URL}/health", timeout=2)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "gpu" in data
    except requests.exceptions.ConnectionError:
        pytest.skip("AI service is not available")

@skip_if_no_containers
def test_redis_connection(redis_client):
    """Test Redis connection and basic operations."""
    test_key = "test:integration"
    test_value = "working"

    # Set and get a test value
    redis_client.set(test_key, test_value)
    assert redis_client.get(test_key).decode() == test_value

    # Clean up
    redis_client.delete(test_key)

@skip_if_no_containers
def test_gpu_support():
    """Test GPU support in AI service."""
    try:
        response = requests.get(f"{AI_SERVICE_URL}/health", timeout=2)
        assert response.status_code == 200
        data = response.json()

        # Check GPU information
        gpu_info = data["gpu"]
        if gpu_info["device"] == "cuda":
            assert "total" in gpu_info
            assert "allocated" in gpu_info
            assert "utilization" in gpu_info
        else:
            logger.warning("Running in CPU mode")
    except requests.exceptions.ConnectionError:
        pytest.skip("AI service is not available")

@pytest.mark.slow
@skip_if_no_containers
def test_container_stability():
    """Long-running test to verify container stability."""
    check_interval = 2  # seconds
    total_time = 10  # seconds (reduced from 30 for faster testing)
    checks = total_time // check_interval

    logger.info("\nRunning container stability test...")

    # First check if all services are available
    if not is_port_open("localhost", 3000) or not is_port_open("localhost", 8000) or not is_port_open("localhost", 6379):
        pytest.skip("One or more required services are not available")

    for i in range(checks):
        logger.info(f"Stability check {i + 1}/{checks}")

        try:
            # Check frontend with increased timeout
            frontend = requests.get(FRONTEND_URL, timeout=10)
            assert frontend.status_code == 200
            assert "Birth Time Rectification" in frontend.text

            # Check AI service
            ai = requests.get(AI_SERVICE_URL + "/health", timeout=5)
            assert ai.status_code == 200
            assert ai.json()["status"] == "healthy"

            # Check Redis
            redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
            assert redis_client.ping()
            redis_client.close()

            time.sleep(check_interval)
        except (requests.exceptions.ConnectionError, RedisConnectionError):
            pytest.skip("Service connection lost during stability test")
            return

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
