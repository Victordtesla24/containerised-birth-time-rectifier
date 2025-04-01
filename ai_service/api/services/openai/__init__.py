"""
OpenAI service package for interacting with OpenAI API.
"""

# No import at top level - we'll import only when needed to avoid circular imports

from typing import Optional
import os
import logging
import asyncio

# Set up logging
logger = logging.getLogger(__name__)

# Create a singleton instance
_openai_service_instance = None
_init_lock = asyncio.Lock()

# Import the OpenAIService class
# We use a try-except to handle potential import errors
try:
    from ai_service.api.services.openai.service import OpenAIService as _OpenAIService
    # Create an alias to avoid name conflicts
    OpenAIService = _OpenAIService
except ImportError:
    # We'll define OpenAIService for the __all__ to avoid errors
    # but it will be properly loaded in __getattr__ if not available here
    OpenAIService = None
    logger.debug("OpenAIService could not be imported at module load time. It will be imported on demand.")

def get_api_key() -> str:
    """
    Get the OpenAI API key from environment variables with fallback to .env file.

    Returns:
        str: The OpenAI API key

    Raises:
        ValueError: If the API key is not found
    """
    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")

    # If not found in environment, try to load from .env file
    if not api_key:
        try:
            from ai_service.utils.env_loader import load_env_file
            env_vars = load_env_file()
            api_key = env_vars.get("OPENAI_API_KEY")
            if api_key:
                logger.info("OpenAI API key loaded from .env file")
        except Exception as e:
            logger.warning(f"Failed to load .env file: {e}")

    # Check if API key was found
    if not api_key:
        logger.error("OPENAI_API_KEY not found in environment or .env file")
        raise ValueError("OPENAI_API_key is required but was not found in environment variables or .env file")

    return api_key

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

    # Use lock to prevent multiple initializations
    async with _init_lock:
        # Check again in case another task initialized while waiting
        if _openai_service_instance is not None:
            return _openai_service_instance

        try:
            # Import OpenAI service class
            from ai_service.api.services.openai.service import OpenAIService

            # Get API key from environment
            try:
                api_key = get_api_key()
            except ValueError as e:
                logger.warning(f"OpenAI API key not available: {e}")
                return None

            # Create a new service instance
            _openai_service_instance = OpenAIService(api_key=api_key)

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

__all__ = ['OpenAIService', 'get_openai_service', 'get_api_key']
