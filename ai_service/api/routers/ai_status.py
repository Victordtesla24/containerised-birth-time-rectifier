"""
AI Status Router.

This module provides endpoints for monitoring the AI service status.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from ai_service.api.services.openai.service import get_openai_service

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


@router.post("/test", tags=["AI Status"])
async def test_ai_connection(prompt: str = "Hello, how are you today?") -> Dict[str, Any]:
    """
    Test the connection to the OpenAI API by sending a simple prompt.

    Args:
        prompt: Test prompt to send (defaults to a simple greeting)

    Returns:
        Test results including the model response
    """
    try:
        # Get OpenAI service
        openai_service = get_openai_service()

        # Send a test prompt
        start_time = datetime.now()
        response = await openai_service.generate_completion(
            prompt=prompt,
            task_type="test",
            max_tokens=50,
            temperature=0.7
        )
        end_time = datetime.now()
        elapsed_time = (end_time - start_time).total_seconds()

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "test_results": {
                "prompt": prompt,
                "response": response.get("content", ""),
                "model": response.get("model", "unknown"),
                "tokens": response.get("tokens", {}),
                "elapsed_time_seconds": elapsed_time
            }
        }
    except Exception as e:
        logger.error(f"Error testing AI connection: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing AI connection: {str(e)}")
