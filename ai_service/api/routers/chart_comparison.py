"""
Chart comparison router for the Birth Time Rectifier API.
Provides endpoints for comparing original and rectified charts.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import Optional

from ai_service.models.chart_comparison import (
    ChartComparisonRequest, ChartComparisonResponse
)
from ai_service.services.chart_comparison_service import ChartComparisonService
from ai_service.api.dependencies.services import get_chart_service

# Setup logging
logger = logging.getLogger("birth-time-rectifier.chart-comparison")

# Create router
router = APIRouter()

@router.get(
    "/compare",
    response_model=ChartComparisonResponse,
    summary="Compare Two Charts",
    description="Compare an original chart with a rectified chart to identify differences"
)
async def compare_charts(
    chart1_id: str = Query(..., description="ID of the first chart (usually original)"),
    chart2_id: str = Query(..., description="ID of the second chart (usually rectified)"),
    comparison_type: str = Query(
        "differences",
        description="Type of comparison (differences, full, or summary)"
    ),
    include_significance: bool = Query(
        True,
        description="Include significance scores for each difference"
    ),
    chart_service = Depends(get_chart_service)
):
    """
    Compare two astrological charts to identify differences.

    This endpoint allows for comparing:
    - An original birth chart with a rectified chart
    - Two different rectification results
    - Any two charts to see how they differ

    The response includes a detailed breakdown of all significant differences
    between the charts, including position shifts, sign changes, house transitions,
    and aspect formations/dissolutions.
    """
    try:
        # Create chart comparison service with the chart service dependency
        comparison_service = ChartComparisonService(chart_service)

        # Perform comparison
        result = comparison_service.compare_charts(
            chart1_id=chart1_id,
            chart2_id=chart2_id,
            comparison_type=comparison_type,
            include_significance=include_significance
        )

        return result
    except ValueError as e:
        logger.error(f"Chart comparison error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in chart comparison: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while comparing charts"
        )

@router.post(
    "/compare",
    response_model=ChartComparisonResponse,
    summary="Compare Two Charts (POST)",
    description="Compare charts with advanced options"
)
async def compare_charts_post(
    request: ChartComparisonRequest,
    chart_service = Depends(get_chart_service)
):
    """
    Compare two astrological charts using POST with additional options.

    This endpoint is similar to the GET version but accepts a JSON request body
    with additional configuration options for the comparison.
    """
    try:
        # Create chart comparison service with the chart service dependency
        comparison_service = ChartComparisonService(chart_service)

        # Perform comparison
        result = comparison_service.compare_charts(
            chart1_id=request.chart1_id,
            chart2_id=request.chart2_id,
            comparison_type=request.comparison_type,
            include_significance=request.include_significance
        )

        return result
    except ValueError as e:
        logger.error(f"Chart comparison error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error in chart comparison: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while comparing charts"
        )
