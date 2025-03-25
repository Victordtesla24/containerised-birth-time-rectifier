"""
AI Status Router.

This module provides endpoints for monitoring the AI service status.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from ai_service.api.services.openai import get_openai_service

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


@router.get("/status", tags=["AI Status"])
async def get_ai_status() -> Dict[str, Any]:
    """
    Get the status of the AI services including OpenAI API usage.

    Returns:
        AI service status information
    """
    try:
        # Get OpenAI service
        openai_service = get_openai_service()

        # Get usage statistics
        usage_stats = openai_service.get_usage_statistics()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "openai": {
                    "status": "connected",
                    "usage": usage_stats
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "services": {
                "openai": {
                    "status": "error",
                    "message": f"Failed to connect: {str(e)}"
                }
            }
        }
