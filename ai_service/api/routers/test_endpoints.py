"""
Test endpoints for integration testing
"""

from fastapi import APIRouter, Body
import random
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["test"],
    responses={404: {"description": "Not found"}},
)

@router.post("/rectify", response_model=dict)
async def test_rectify_complex(data: dict = Body(...)):
    """
    Test endpoint for complex rectification format
    """
    logger.info(f"Test rectify endpoint called with data: {data}")

    # Handle both simple and complex format
    if "birthDetails" in data and isinstance(data["birthDetails"], dict):
        # Complex format
        birth_details = data["birthDetails"]
        original_time = birth_details.get("birthTime", "12:00")
    else:
        # Simple format
        original_time = data.get("time", "12:00")

    # Parse original time
    time_parts = original_time.split(":")
    hour = int(time_parts[0])
    minute = int(time_parts[1])

    # Make a simple adjustment for testing
    adjusted_minute = (minute + random.randint(1, 5)) % 60
    adjusted_hour = (hour + (1 if adjusted_minute < minute else 0)) % 24

    suggested_time = f"{adjusted_hour:02d}:{adjusted_minute:02d}"

    # Return expected format
    return {
        "originalTime": original_time,
        "suggestedTime": suggested_time,
        "rectifiedTime": suggested_time,
        "confidence": 85.0,
        "reliability": "high",
        "explanation": "Test rectification based on provided data"
    }
