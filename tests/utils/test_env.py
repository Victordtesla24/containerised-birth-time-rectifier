#!/usr/bin/env python
"""
Simple test script to verify that the .env file is loaded properly
and the OpenAI API key is available.
"""

import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("env-test")

def test_env_variables():
    """Test that environment variables are loaded from .env file"""
    # Load .env file
    load_dotenv()

    # Check if OPENAI_API_KEY is set
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        logger.info(f"OPENAI_API_KEY is set with value: {api_key[:5]}...{api_key[-4:]}")
        return True
    else:
        logger.error("OPENAI_API_KEY is not set!")
        return False

if __name__ == "__main__":
    logger.info("Testing environment variables from .env file...")
    if test_env_variables():
        logger.info("✅ Environment variables loaded successfully!")
    else:
        logger.error("❌ Failed to load environment variables!")
