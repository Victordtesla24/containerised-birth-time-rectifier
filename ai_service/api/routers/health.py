"""
Health Router.

This module provides health check endpoints for the AI service.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ai_service.api.services.openai.service import get_openai_service

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    environment: str = "production"
    version: str = "1.0.0"
    openai_status: str
    usage_stats: Dict[str, Any] = {}


@router.get("/", response_model=HealthResponse, tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the AI service.

    Returns:
        Health status information
    """
    logger.info("Health check requested")

    try:
        # Get the OpenAI service to check its status
        openai_service = get_openai_service()
        usage_stats = openai_service.get_usage_statistics()
        openai_status = "healthy"
    except Exception as e:
        logger.error(f"OpenAI service health check failed: {e}")
        openai_status = "degraded"
        usage_stats = {}

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": "production",
        "version": "1.0.0",
        "openai_status": openai_status,
        "usage_stats": usage_stats
    }


@router.get("/ping", tags=["Health"])
async def ping() -> Dict[str, str]:
    """
    Simple ping endpoint for basic connectivity checks.

    Returns:
        Simple response message
    """
    return {"response": "pong", "timestamp": datetime.now().isoformat()}
