"""
OpenAI service package for interacting with OpenAI API.
"""

from ai_service.api.services.openai.service import OpenAIService

# Create a singleton instance
_openai_service_instance = None

def get_openai_service():
    """
    Get a singleton instance of the OpenAIService.

    Returns:
        OpenAIService: The OpenAI service instance
    """
    global _openai_service_instance
    if _openai_service_instance is None:
        _openai_service_instance = OpenAIService()
    return _openai_service_instance

__all__ = ['OpenAIService', 'get_openai_service']
