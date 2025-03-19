"""
Test configuration utility module.

Provides utility functions and constants for test configuration.
"""

import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Configure logger
logger = logging.getLogger(__name__)

# Find the root directory of the project
ROOT_DIR = Path(__file__).parent.parent.parent.absolute()

def setup_test_environment():
    """
    Set up the test environment by loading environment variables from .env file.

    This function:
    1. Loads the .env file from the project root directory
    2. Ensures that OPENAI_API_KEY is set
    3. Sets up any other environment variables needed for testing

    Returns:
        bool: True if environment is set up correctly, False otherwise
    """
    # Load .env file
    dotenv_path = ROOT_DIR / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
        logger.info(f"Loaded environment variables from {dotenv_path}")
    else:
        logger.warning(f".env file not found at {dotenv_path}")
        return False

    # Verify OPENAI_API_KEY is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY environment variable is not set")
        return False

    logger.info(f"OPENAI_API_KEY is set with value: {api_key[:5]}...{api_key[-4:]}")

    # Set any additional test environment variables here if needed

    return True

# Auto-run setup when the module is imported
environment_ready = setup_test_environment()
if not environment_ready:
    logger.warning("Test environment setup failed. Tests may not run correctly.")
