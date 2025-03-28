"""
Chart utilities for the consolidated chart router.

This module provides utility functions for chart operations that
are used by multiple chart-related routers.
"""

import logging
from typing import Dict, Any, Optional, List, Union
import asyncio
import json
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

async def validate_chart_data(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates chart data format and ensures all required fields are present.

    Args:
        chart_data: The chart data to validate

    Returns:
        Dictionary with validation results
    """
    validation_result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }

    # Required fields in birth details
    required_fields = ["birth_date", "birth_time", "latitude", "longitude", "timezone"]

    # Check birth details
    if "birth_details" not in chart_data:
        validation_result["valid"] = False
        validation_result["errors"].append("Missing birth_details")
    else:
        birth_details = chart_data["birth_details"]
        for field in required_fields:
            if field not in birth_details or not birth_details[field]:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Missing required field: {field}")

    return validation_result

async def format_chart_response(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats chart data into a standardized response format.

    Args:
        chart_data: The chart data to format

    Returns:
        Formatted chart response
    """
    # Ensure chart_id exists
    if "chart_id" not in chart_data:
        import uuid
        chart_data["chart_id"] = f"chrt_{uuid.uuid4().hex[:8]}"

    # Add response timestamps if not present
    if "generated_at" not in chart_data:
        chart_data["generated_at"] = datetime.now().isoformat()

    # Ensure verification data exists
    if "verification" not in chart_data:
        chart_data["verification"] = {
            "verified": False,
            "confidence": 0.0,
            "method": "none"
        }

    return chart_data
