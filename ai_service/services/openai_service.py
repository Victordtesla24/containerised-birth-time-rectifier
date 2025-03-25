"""
OpenAI service module that provides access to the OpenAI API.

This module re-exports the OpenAIService class for backward compatibility
while avoiding circular imports.
"""

# Re-export the OpenAIService class from the API module
from ai_service.api.services.openai import get_openai_service

# Define __getattr__ to allow direct imports of OpenAIService
def __getattr__(name):
    """
    Dynamically import when attributes are accessed.

    Args:
        name: The name of the attribute being accessed

    Returns:
        The requested attribute or raises AttributeError
    """
    if name == "OpenAIService":
        # Import only when needed to avoid circular dependency
        from ai_service.api.services.openai import OpenAIService as _OpenAIService
        return _OpenAIService

    raise AttributeError(f"module {__name__} has no attribute {name}")

# For backward compatibility, provide the get_openai_service function
async def get_openai_service():
    """
    Get a singleton instance of the OpenAIService.
    This is a compatibility wrapper around the main implementation.

    Returns:
        OpenAIService: The OpenAI service instance
    """
    # Now the imported function is also async so we need to await it
    from ai_service.api.services.openai import get_openai_service as _get_openai_service
    return await _get_openai_service()

__all__ = ["OpenAIService", "get_openai_service"]
