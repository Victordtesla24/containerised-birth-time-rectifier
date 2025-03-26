"""
V1 API Chart Service - Robust implementation for tests.

This module provides a defensive implementation of chart generation
that doesn't rely on ChartService attributes being initialized.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import traceback
from fastapi import HTTPException

# Import from services directly
from ai_service.services import get_chart_service_async

# Set up logging
logger = logging.getLogger(__name__)

async def generate_chart(
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: Optional[str] = None,
    location: Optional[str] = None,
    verify_with_openai: bool = True,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an astrological chart based on birth details.

    Args:
        birth_date: Birth date (YYYY-MM-DD)
        birth_time: Birth time (HH:MM:SS)
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string (optional)
        location: Birth location name (optional)
        verify_with_openai: Whether to verify the chart with OpenAI
        session_id: Optional session ID for WebSocket updates

    Returns:
        Generated chart data

    Raises:
        HTTPException: If chart generation fails
    """
    try:
        # Get chart service
        chart_service = await get_chart_service_async()
        if not chart_service:
            raise RuntimeError("Chart service not available")

        # Generate chart
        chart_data = await chart_service.generate_chart(
            birth_date=birth_date,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            location=location,
            verify_with_openai=verify_with_openai,
            session_id=session_id
        )

        return chart_data
    except ValueError as e:
        # Re-raise as HTTPException for API error handling
        logger.error(f"Invalid input for chart generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Service unavailable
        logger.error(f"Service error in chart generation: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in chart generation: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {str(e)}")

async def verify_chart(
    chart_data: Dict[str, Any],
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify an astrological chart for accuracy.

    Args:
        chart_data: Chart data to verify
        session_id: Optional session ID for WebSocket updates

    Returns:
        Verification results

    Raises:
        HTTPException: If chart verification fails
    """
    try:
        # Import verification function
        from ai_service.services.chart_verification import verify_chart as verify_chart_func

        # Verify chart
        verification_result = await verify_chart_func(
            chart_data=chart_data,
            session_id=session_id,
            verify_with_openai=True
        )

        return verification_result
    except ValueError as e:
        # Input validation error
        logger.error(f"Invalid chart data for verification: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Service unavailable
        logger.error(f"Service error in chart verification: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error in chart verification: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Chart verification failed: {str(e)}")

async def get_chart(chart_id: str) -> Dict[str, Any]:
    """
    Get a chart by ID.

    Args:
        chart_id: Chart ID

    Returns:
        Chart data

    Raises:
        HTTPException: If chart retrieval fails
    """
    try:
        # Get chart service
        chart_service = await get_chart_service_async()
        if not chart_service:
            raise RuntimeError("Chart service not available")

        # Get chart
        chart_data = await chart_service.get_chart(chart_id)

        if not chart_data:
            raise HTTPException(status_code=404, detail=f"Chart not found: {chart_id}")

        return chart_data
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log error and wrap in HTTP exception
        logger.error(f"Error retrieving chart {chart_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chart: {str(e)}")
