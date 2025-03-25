"""
Chart verification services.

This module contains functions for verifying astrological charts using
various methods including OpenAI verification.
"""

import logging
import json
from typing import Dict, Any, Optional
import asyncio

from ai_service.api.services.openai import get_openai_service

logger = logging.getLogger(__name__)

async def verify_chart_with_openai(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify a chart using OpenAI.

    Args:
        chart_data: Chart data to verify

    Returns:
        Verification result
    """
    try:
        # Get OpenAI service properly with await
        openai_service = await get_openai_service()

        if not openai_service:
            logger.warning("OpenAI service not available for chart verification")
            return {
                "status": "verification_skipped",
                "message": "OpenAI service not available",
                "verified_with_openai": False,
                "confidence": 0,
                "corrections_applied": False,
                "corrections": []
        }

        # Call the verify_chart method
        verification_result = await openai_service.verify_chart(chart_data)

        return verification_result
    except Exception as e:
        logger.error(f"Error verifying chart with OpenAI: {e}")
        return {
            "status": "verification_error",
            "message": f"Error during verification: {str(e)}",
            "verified_with_openai": False,
            "confidence": 0,
            "corrections_applied": False,
            "corrections": []
        }
