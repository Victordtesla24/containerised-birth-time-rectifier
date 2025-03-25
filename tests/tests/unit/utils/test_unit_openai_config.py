"""
Test to verify proper OpenAI API key configuration from .env file.
"""

import os
import pytest
import asyncio
import logging
from ai_service.api.services.openai.service import OpenAIService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_openai_api_key_from_env():
    """Test that the OpenAI API key from .env file is used correctly."""

    logger.info("Testing OpenAI API key configuration from .env file")

    # Check that the API key from .env file is loaded
    api_key = os.environ.get("OPENAI_API_KEY")
    assert api_key is not None, "OPENAI_API_KEY not found in environment"
    assert api_key.startswith("sk-"), "OPENAI_API_KEY has invalid format"
    assert len(api_key) > 20, "OPENAI_API_KEY is too short"

    logger.info(f"Found API key with length {len(api_key)}")

    # Create the OpenAI service
    service = OpenAIService()

    try:
        # Verify that the service uses the API key from .env
        assert service.api_key == api_key, "Service API key doesn't match environment API key"

        # Make a simple API call to test connectivity
        prompt = "Hello! Please respond with a short greeting."

        logger.info("Making test API call to OpenAI")
        response = await service.generate_completion(
            prompt=prompt,
            task_type="general",
            max_tokens=20,
            temperature=0.3
        )

        # Verify response
        assert 'content' in response, "No content in API response"
        assert len(response['content']) > 0, "Empty content in API response"

        logger.info(f"Got response: '{response['content']}'")
        logger.info("API test completed successfully")

    finally:
        # Clean up
        await service.close()

if __name__ == "__main__":
    asyncio.run(test_openai_api_key_from_env())
