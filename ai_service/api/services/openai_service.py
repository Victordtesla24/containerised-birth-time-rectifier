"""
OpenAI service for interacting with OpenAI API.
This module now imports from the modular implementation in the openai package.
Maintained for backward compatibility.
"""

from ai_service.api.services.openai import OpenAIService

# Re-export the OpenAIService class for backward compatibility
__all__ = ['OpenAIService']
