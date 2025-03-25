from typing import Optional, Dict, Any, List, Union, Callable
import os
import json
import logging
import time
import asyncio
import traceback
from datetime import datetime, timedelta

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

# Global instance
_openai_service_instance = None

# OpenAI service implementation
class OpenAIService:
    def __init__(self, api_key: str):
        """
        Initialize the OpenAI service with an API key.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self._http_client = None
        self.logger = logging.getLogger(__name__)

    async def _ensure_http_client(self):
        """Ensure HTTP client is initialized."""
        if self._http_client is None and AIOHTTP_AVAILABLE:
            self._http_client = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._http_client is not None

async def get_openai_service() -> Optional[OpenAIService]:
    """
    Get the global OpenAI service instance asynchronously.

    Returns:
        OpenAI service instance
    """
    global _openai_service_instance

    if _openai_service_instance is None:
        # Create a new instance
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            _openai_service_instance = OpenAIService(api_key)
            # Ensure the HTTP client is initialized
            await _openai_service_instance._ensure_http_client()

    return _openai_service_instance
