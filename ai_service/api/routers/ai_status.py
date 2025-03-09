"""
AI status router for the Birth Time Rectifier API.
Provides endpoints for checking AI service health and status.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional

# Setup logging
logger = logging.getLogger("birth-time-rectifier.ai-status")

# Create router
router = APIRouter(tags=["AI Status"])

# Import OpenAI service
try:
    from ai_service.api.services.openai_service import OpenAIService
except ImportError as e:
    logger.error(f"Failed to import OpenAI service: {e}")
    OpenAIService = None

def get_openai_service() -> Any:
    """
    Get or create an OpenAI service instance.
    Returns None if the service cannot be initialized.
    """
    try:
        if OpenAIService is None:
            return None
        return OpenAIService()
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI service: {e}")
        return None

@router.get("/status", summary="Check AI Service Status")
async def check_ai_status(
    openai_service: Any = Depends(get_openai_service)
) -> Dict[str, Any]:
    """
    Check if the AI service is healthy and ready to handle requests.

    Returns:
        Dict with status information about the OpenAI service.
    """
    try:
        # Basic check if the service is available
        if openai_service is None:
            return {
                "status": "warning",
                "message": "OpenAI service not initialized",
                "initialized": False,
                "available": False,
                "cache_enabled": False
            }

        # Get API key status (redacted for security)
        api_key_available = bool(openai_service.api_key) and openai_service.api_key != "sk-mock-key-for-testing"
        api_key_status = "available" if api_key_available else "mock" if openai_service.api_key == "sk-mock-key-for-testing" else "missing"

        # Check if using mock responses
        using_mock = openai_service.api_key == "sk-mock-key-for-testing"

        # Basic status information
        status_info = {
            "status": "healthy" if api_key_available else "limited",
            "message": "AI service is operational" if api_key_available else "Using mock responses",
            "initialized": True,
            "available": True,
            "api_key_status": api_key_status,
            "using_mock_responses": using_mock,
            "cache_enabled": hasattr(openai_service, "cache_expiry") and openai_service.cache_expiry > 0,
            "timeout": getattr(openai_service, "timeout", 30),
            "usage_stats": {
                "calls_made": openai_service.usage_stats.get("calls_made", 0),
                "total_tokens": openai_service.usage_stats.get("total_tokens", 0)
            }
        }

        return status_info
    except Exception as e:
        logger.error(f"Error checking AI status: {e}")
        return {
            "status": "error",
            "message": f"Error checking AI status: {str(e)}",
            "initialized": False,
            "available": False,
            "error": str(e)
        }

@router.get("/usage_statistics", summary="Get AI Usage Statistics")
async def get_usage_statistics(
    openai_service: Any = Depends(get_openai_service)
) -> Dict[str, Any]:
    """
    Get usage statistics for the OpenAI service.

    Returns:
        Dict with token usage counts and estimated costs.
    """
    try:
        if openai_service is None:
            return {
                "status": "warning",
                "message": "OpenAI service not initialized",
                "total_tokens": 0,
                "calls_made": 0,
                "estimated_cost": 0.0
            }

        # Get usage statistics
        usage_stats = openai_service.get_usage_statistics()

        return usage_stats
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}")
        return {
            "status": "error",
            "message": f"Error getting usage statistics: {str(e)}",
            "total_tokens": 0,
            "calls_made": 0,
            "estimated_cost": 0.0,
            "error": str(e)
        }
