"""
Test configuration utilities.

This module provides functions for configuring the test environment,
including setting up necessary URLs and environment variables.
"""

import os
import logging
from typing import Dict, Any, Optional

# Configure logger
logger = logging.getLogger(__name__)

def setup_test_environment() -> str:
    """
    Set up the test environment with appropriate configuration.

    This function configures URLs and environment variables for testing,
    and returns the base API URL to use for tests.

    Returns:
        Base API URL to use for tests
    """
    # Determine environment (local or containerized)
    is_container = os.environ.get("CONTAINER_ENV", "0") == "1"

    # Set up API URL
    if is_container:
        # Inside a container, use internal URLs
        api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
        ws_base_url = os.environ.get("WS_URL", "ws://localhost:8000/ws")
    else:
        # Outside container, use exposed ports
        api_base_url = os.environ.get("API_BASE_URL", "http://localhost:9000")
        ws_base_url = os.environ.get("WS_URL", "ws://localhost:9001/ws")

    # Set these in environment for other parts of the test that might need them
    os.environ["API_BASE_URL"] = api_base_url
    os.environ["WS_URL"] = ws_base_url

    logger.info(f"Test environment configured with API URL: {api_base_url}")

    return api_base_url

def get_test_data_path() -> str:
    """
    Get the path to the test data directory.

    Returns:
        Path to test data directory
    """
    # Default test data directory is in the tests directory
    return os.environ.get("TEST_DATA_PATH", os.path.join("tests", "test_data"))

def get_test_config() -> Dict[str, Any]:
    """
    Get the test configuration values.

    Returns:
        Dictionary with test configuration
    """
    config = {
        "api_base_url": os.environ.get("API_BASE_URL", "http://localhost:8000"),
        "ws_url": os.environ.get("WS_URL", "ws://localhost:8000/ws"),
        "test_data_path": get_test_data_path(),
        "timeout": int(os.environ.get("TEST_TIMEOUT", "30")),
        "log_level": os.environ.get("LOG_LEVEL", "INFO"),
    }

    return config
