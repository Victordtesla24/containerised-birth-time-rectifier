"""
Health Router.

This module provides health check endpoints for the AI service.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ai_service.api.services.openai.service import get_openai_service

# Set up logging
logger = logging.getLogger(__name__)

# Create router with explicit prefix to ensure it's accessible
router = APIRouter(
    prefix="/health",
    tags=["Health"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"},
    }
)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    environment: str = "production"
    version: str = "1.0.0"
    openai_status: str
    usage_stats: Dict[str, Any] = {}


@router.get("/", response_model=HealthResponse)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the AI service.

    Returns:
        Health status information
    """
    logger.info("Health check requested")

    try:
        # Get the OpenAI service to check its status
        openai_service = await get_openai_service()
        usage_stats = {}

        if openai_service:
            try:
                if hasattr(openai_service, 'get_usage_statistics'):
                    usage_stats = openai_service.get_usage_statistics()
                openai_status = "healthy"
            except Exception as e:
                logger.warning(f"OpenAI usage statistics unavailable: {e}")
                openai_status = "degraded"
                usage_stats = {"error": str(e)}
        else:
            logger.warning("OpenAI service not available")
            openai_status = "unavailable"
            usage_stats = {}

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


@router.get("/ping")
async def ping() -> Dict[str, str]:
    """
    Simple ping endpoint for basic connectivity checks.

    Returns:
        Simple response message
    """
    return {"response": "pong", "timestamp": datetime.now().isoformat()}


@router.get("/basic")
async def basic_health() -> Dict[str, Any]:
    """
    Basic health check that doesn't depend on any services.

    Returns:
        Basic health status
    """
    return {
        "status": "ok",
        "service": "ai_service",
        "timestamp": datetime.now().isoformat()
    }
