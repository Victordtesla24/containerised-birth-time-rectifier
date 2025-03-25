"""
OpenAI service package for interacting with OpenAI API.
"""

# No import at top level - we'll import only when needed to avoid circular imports

from typing import Optional

# Create a singleton instance
_openai_service_instance = None

async def get_openai_service():
    """
    Get a singleton instance of the OpenAIService asynchronously.

    Returns:
        OpenAIService: The OpenAI service instance
    """
    global _openai_service_instance
    if _openai_service_instance is None:
        # Import here to avoid circular dependency
        from ai_service.api.services.openai.service import OpenAIService
        _openai_service_instance = OpenAIService()
        # Initialize the HTTP client
        await _openai_service_instance._ensure_http_client()
    return _openai_service_instance

# Define __getattr__ to allow importing OpenAIService directly from this module
def __getattr__(name):
    """
    Dynamically import when attributes are accessed.

    Args:
        name: The name of the attribute to import

    Returns:
        The requested attribute from the module

    Raises:
        AttributeError: If the attribute doesn't exist
    """
    if name == "OpenAIService":
        from ai_service.api.services.openai.service import OpenAIService
        return OpenAIService
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['OpenAIService', 'get_openai_service']
