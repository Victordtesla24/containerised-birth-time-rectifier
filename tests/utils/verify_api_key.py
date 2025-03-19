#!/usr/bin/env python3
"""
OpenAI API Key Verification Script

This script verifies that your OpenAI API key is properly configured
by making a test API call without using any mockups or fallbacks.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api_verifier")

# Make sure the ai_service module is in the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the required modules
try:
    from ai_service.utils.env_loader import load_env_file, get_openai_api_key
    from ai_service.api.services.openai.service import OpenAIService
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure you're running this script from the project root")
    sys.exit(1)

async def verify_api_key():
    """Verify the OpenAI API key by making a real API call."""
    # Load environment variables from .env
    load_env_file()

    try:
        # Get the API key (this will raise an error if not set)
        api_key = get_openai_api_key()
        logger.info(f"Found OpenAI API key: {api_key[:5]}...{api_key[-4:]}")

        # Create a real OpenAI service (no mocks)
        service = OpenAIService(api_key=api_key)
        logger.info("Created OpenAI service")

        # Make a simple test API call
        logger.info("Making test API call...")
        result = await service.generate_completion(
            prompt="Hello, this is a test prompt. Please respond with 'API key is working!'",
            task_type="test",
            max_tokens=20,
            temperature=0.7
        )

        # Log the result
        logger.info(f"API Response: {result['content']}")
        logger.info(f"Tokens Used: {result['tokens']['total']}")
        logger.info(f"Estimated Cost: ${result.get('cost', 0):.6f}")

        logger.info("✅ API key verification successful!")
        return True

    except Exception as e:
        logger.error(f"❌ API key verification failed: {e}")
        return False

def main():
    """Main entry point for the script."""
    logger.info("OpenAI API Key Verification Script")
    logger.info("==================================")

    # Run the async verification function
    success = asyncio.run(verify_api_key())

    # Exit with appropriate code
    if success:
        sys.exit(0)
    else:
        logger.error("Please check your .env file and make sure OPENAI_API_KEY is set correctly")
        sys.exit(1)

if __name__ == "__main__":
    main()
