"""
OpenAI service package for interacting with OpenAI API.
"""

# No import at top level - we'll import only when needed to avoid circular imports

from typing import Optional
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Create a singleton instance
_openai_service_instance = None

async def get_openai_service():
    """
    Get a singleton instance of the OpenAIService asynchronously.

    This function ensures the OpenAI service is properly initialized with
    an API key and HTTP client. If no API key is available, it returns None.

    Returns:
        OpenAIService: The OpenAI service instance or None if not available
    """
    global _openai_service_instance

    # Return existing instance if available
    if _openai_service_instance is not None:
        return _openai_service_instance

    try:
        # Import OpenAI service class
        from ai_service.api.services.openai.service import OpenAIService

        # Get API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY environment variable is not set. OpenAI features will be disabled.")
            return None

        # Create a new service instance
        _openai_service_instance = OpenAIService(api_key=api_key)

        # Ensure HTTP client is initialized
        await _openai_service_instance._ensure_http_client()

        # Successfully initialized
        logger.info("OpenAI service initialized successfully")

        # Register in container if available
        try:
            from ai_service.utils.dependency_container import get_container
            container = get_container()
            container.register_instance("openai_service", _openai_service_instance)
            logger.info("OpenAI service registered in dependency container")
        except (ImportError, Exception) as e:
            logger.debug(f"Could not register OpenAI service in container: {e}")

        return _openai_service_instance

    except Exception as e:
        logger.error(f"Failed to initialize OpenAI service: {e}")
        return None

def get_openai_service_sync():
    """
    Get the OpenAI service synchronously without initialization.

    This is useful when you're in a sync context and just want to check
    if the service is available, without initializing it.

    Returns:
        OpenAIService: The existing OpenAI service instance or None
    """
    return _openai_service_instance

# Define __getattr__ to allow importing OpenAIService directly from this module
def __getattr__(name):
    """
    Dynamically import when attributes are accessed to avoid circular imports.

    Args:
        name: The name of the attribute to load

    Returns:
        The requested attribute

    Raises:
        AttributeError: If the attribute doesn't exist
    """
    if name == "OpenAIService":
        from ai_service.api.services.openai.service import OpenAIService as _OpenAIService
        return _OpenAIService

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['OpenAIService', 'get_openai_service']
