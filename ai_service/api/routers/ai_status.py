"""
AI status router for the Birth Time Rectifier API.
Provides endpoints for checking AI service health and status.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, Optional

# Import OpenAI service
from ai_service.api.services.openai import get_openai_service

# Setup logging
logger = logging.getLogger("birth-time-rectifier.ai-status")

# Create router
router = APIRouter(tags=["AI Status"])

@router.get("/status", summary="Check AI Service Status")
async def check_ai_status() -> Dict[str, Any]:
    """
    Check if the AI service is healthy and ready to handle requests.

    Returns:
        Dict with status information about the OpenAI service.
    """
    try:
        # Get real OpenAI service instance
        openai_service = get_openai_service()

        # Verify service is initialized
        if not openai_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI service not available"
            )

        # Get API key status (redacted for security)
        api_key_available = bool(openai_service.api_key)

        if not api_key_available:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OpenAI API key not configured"
            )

        # Return real service status
        status_info = {
            "status": "healthy",
            "message": "AI service is operational",
            "initialized": True,
            "available": True,
            "cache_enabled": hasattr(openai_service, "cache_expiry") and openai_service.cache_expiry > 0,
            "timeout": getattr(openai_service, "timeout", 30),
            "usage_stats": {
                "calls_made": openai_service.usage_stats.get("calls_made", 0),
                "total_tokens": openai_service.usage_stats.get("total_tokens", 0)
            }
        }

        return status_info
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error checking AI status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking AI status: {str(e)}"
        )

@router.get("/usage_statistics", summary="Get AI Usage Statistics")
async def get_usage_statistics() -> Dict[str, Any]:
    """
    Get usage statistics for the OpenAI service.

    Returns:
        Dict with token usage counts and estimated costs.
    """
    try:
        # Get real OpenAI service instance
        openai_service = get_openai_service()

        # Verify service is initialized
        if not openai_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenAI service not available"
            )

        # Get real usage statistics from the service
        usage_stats = openai_service.get_usage_statistics()

        # Validate we have actual stats
        if not usage_stats:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve usage statistics"
            )

        return usage_stats
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting usage statistics: {str(e)}"
        )
