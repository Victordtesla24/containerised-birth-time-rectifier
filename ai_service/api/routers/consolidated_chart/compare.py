"""
Chart Comparison Router

This module provides endpoints for comparing astrological charts
and analyzing their differences.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Response, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
import logging
import uuid
from datetime import datetime

# Import utilities, models and services
from ai_service.api.routers.consolidated_chart.utils import retrieve_chart
from ai_service.api.routers.consolidated_chart.consts import ERROR_CODES
from ai_service.services.chart_comparison_service import ChartComparisonService
from ai_service.api.dependencies.services import get_chart_service
from ai_service.services.chart_service import ChartService

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["chart_comparison"],
    responses={
        500: {"description": "Internal server error"},
        404: {"description": "Chart not found"},
        400: {"description": "Bad request - invalid parameters"}
    }
)

# Models for request/response
class ChartComparisonRequest(BaseModel):
    chart1_id: str = Field(..., description="ID of the first chart")
    chart2_id: str = Field(..., description="ID of the second chart")
    comparison_type: str = Field("differences", description="Type of comparison to perform (differences, full, summary)")
    include_significance: bool = Field(True, description="Include significance ratings in the results")

class ChartComparison(BaseModel):
    comparison_id: str
    chart1_id: str
    chart2_id: str
    comparison_type: str
    differences: List[Dict[str, Any]]
    summary: Optional[str] = None
    overall_impact: Optional[float] = None

@router.get("/compare", response_model=Dict[str, Any], operation_id="compare_charts_get_api_v1_chart_compare_endpoint")
async def compare_charts_get(
    chart1_id: str = Query(..., description="ID of the first chart"),
    chart2_id: str = Query(..., description="ID of the second chart"),
    comparison_type: str = Query("differences", description="Type of comparison to perform"),
    include_significance: bool = Query(True, description="Include significance ratings")
):
    """
    Compare two astrological charts using a GET request with query parameters.

    This endpoint analyzes differences between two charts, such as planetary positions,
    house placements, and aspects. It supports different comparison types.

    Args:
        chart1_id: ID of the first chart
        chart2_id: ID of the second chart
        comparison_type: Type of comparison to perform (differences, full, summary)
        include_significance: Whether to include significance ratings

    Returns:
        A detailed comparison of the two charts
    """
    logger.info(f"GET compare request: chart1={chart1_id}, chart2={chart2_id}, type={comparison_type}")

    try:
        # Create chart service instance
        chart_service = ChartService()

        # Create chart comparison service
        comparison_service = ChartComparisonService(chart_service=chart_service)

        # Perform comparison
        result = comparison_service.compare_charts(
            chart1_id=chart1_id,
            chart2_id=chart2_id,
            comparison_type=comparison_type,
            include_significance=include_significance
        )

        # Convert Pydantic model to dict and return
        return result.model_dump()

    except ValueError as e:
        # Handle chart not found or other value errors
        error_message = str(e)
        if "not found" in error_message:
            chart_id = error_message.split(":")[-1].strip()
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ERROR_CODES["CHART_NOT_FOUND"],
                        "message": f"Chart not found: {chart_id}",
                        "details": {"chart_id": chart_id}
                    }
                }
            )
        else:
            # Other validation errors
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": ERROR_CODES["VALIDATION_ERROR"],
                        "message": error_message,
                        "details": {}
                    }
                }
            )
    except Exception as e:
        # Log the error
        logger.error(f"Error comparing charts: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ERROR_CODES["COMPARISON_FAILED"],
                    "message": f"Failed to compare charts: {str(e)}",
                    "details": {
                        "chart1_id": chart1_id,
                        "chart2_id": chart2_id,
                        "type": str(type(e).__name__)
                    }
                }
            }
        )

@router.post("/compare", response_model=Dict[str, Any], operation_id="compare_charts_post_api_v1_chart_compare_endpoint")
async def compare_charts_post(
    request: ChartComparisonRequest
):
    """
    Compare two astrological charts using a POST request with JSON body.

    This endpoint analyzes differences between two charts, such as planetary positions,
    house placements, and aspects. It supports different comparison types.

    The request body should contain:
    - chart1_id: ID of the first chart
    - chart2_id: ID of the second chart
    - comparison_type: Type of comparison to perform (differences, full, summary)
    - include_significance: Whether to include significance ratings

    Returns:
        A detailed comparison of the two charts
    """
    logger.info(f"POST compare request: chart1={request.chart1_id}, chart2={request.chart2_id}, type={request.comparison_type}")

    try:
        # Create chart service instance
        chart_service = ChartService()

        # Create chart comparison service
        comparison_service = ChartComparisonService(chart_service=chart_service)

        # Perform comparison
        result = comparison_service.compare_charts(
            chart1_id=request.chart1_id,
            chart2_id=request.chart2_id,
            comparison_type=request.comparison_type,
            include_significance=request.include_significance
        )

        # Convert Pydantic model to dict and return
        return result.model_dump()

    except ValueError as e:
        # Handle chart not found or other value errors
        error_message = str(e)
        if "not found" in error_message:
            chart_id = error_message.split(":")[-1].strip()
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ERROR_CODES["CHART_NOT_FOUND"],
                        "message": f"Chart not found: {chart_id}",
                        "details": {"chart_id": chart_id}
                    }
                }
            )
        else:
            # Other validation errors
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": ERROR_CODES["COMPARISON_FAILED"],
                        "message": error_message,
                        "details": {}
                    }
                }
            )
    except Exception as e:
        # Log the error
        logger.error(f"Error comparing charts: {str(e)}", exc_info=True)

        # Return standardized error response
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ERROR_CODES["COMPARISON_FAILED"],
                    "message": f"Failed to compare charts: {str(e)}",
                    "details": {
                        "chart1_id": request.chart1_id,
                        "chart2_id": request.chart2_id,
                        "type": str(type(e).__name__)
                    }
                }
            }
        )

# For backward compatibility, keep the old endpoint with a deprecation warning
@router.get("/chart-comparison", response_model=Dict[str, Any], deprecated=True, operation_id="compare_charts_legacy_api_v1_chart_chart_comparison_get")
async def compare_charts_legacy(
    chart1_id: str = Query(..., description="ID of the first chart"),
    chart2_id: str = Query(..., description="ID of the second chart"),
    comparison_type: str = Query("differences", description="Type of comparison to perform"),
    include_significance: bool = Query(True, description="Include significance ratings")
):
    """
    [DEPRECATED] Use /compare instead.
    Compare two astrological charts and analyze their differences.
    """
    # Add deprecation header to response
    response = Response()
    response.headers["X-Deprecated"] = "Use /compare endpoint instead"

    # Forward to the new endpoint
    result = await compare_charts_get(
        chart1_id=chart1_id,
        chart2_id=chart2_id,
        comparison_type=comparison_type,
        include_significance=include_significance
    )

    return result

# Add root endpoints to fix routing issues with the API Gateway
@router.get("/", response_model=Dict[str, Any], operation_id="compare_charts_root_get_api_v1_chart_root_get")
async def compare_charts_root_get(
    chart1_id: str = Query(..., description="ID of the first chart"),
    chart2_id: str = Query(..., description="ID of the second chart"),
    comparison_type: str = Query("differences", description="Type of comparison to perform"),
    include_significance: bool = Query(True, description="Include significance ratings")
):
    """
    Root endpoint for chart comparison (GET).
    Same as /compare but at the root path.
    """
    # Forward to the main comparison endpoint
    return await compare_charts_get(
        chart1_id=chart1_id,
        chart2_id=chart2_id,
        comparison_type=comparison_type,
        include_significance=include_significance
    )

@router.post("/", response_model=Dict[str, Any], operation_id="compare_charts_root_post_api_v1_chart_root_post")
async def compare_charts_root_post(request: ChartComparisonRequest):
    """Root endpoint for chart comparison (POST)."""
    # Forward to the main comparison endpoint
    return await compare_charts_post(request)

@router.get("/compare/root", response_model=Dict[str, Any], operation_id="compare_charts_get_compare_root_api_v1_chart_compare_root_get")
async def compare_charts_get_root(
    chart1_id: str = Query(..., description="ID of the first chart"),
    chart2_id: str = Query(..., description="ID of the second chart"),
    comparison_type: str = Query("differences", description="Type of comparison to perform"),
    include_significance: bool = Query(True, description="Include significance ratings")
):
    """
    Special endpoint for chart comparison with a dedicated path to prevent routing conflicts.
    This endpoint handles GET requests for chart comparison through the API gateway.

    The path /compare/root is designed to avoid conflicts with the dynamic chart/{chart_id} route
    that might incorrectly capture /compare as a chart_id parameter.

    Args:
        chart1_id: ID of the first chart
        chart2_id: ID of the second chart
        comparison_type: Type of comparison to perform (differences, full, summary)
        include_significance: Whether to include significance ratings

    Returns:
        A detailed comparison of the two charts
    """
    logger.info(f"GET compare/root request: chart1={chart1_id}, chart2={chart2_id}, type={comparison_type}")

    try:
        # Create chart service instance
        chart_service = ChartService()

        # Create chart comparison service
        comparison_service = ChartComparisonService(chart_service=chart_service)

        # Perform comparison
        result = comparison_service.compare_charts(
            chart1_id=chart1_id,
            chart2_id=chart2_id,
            comparison_type=comparison_type,
            include_significance=include_significance
        )

        # Convert Pydantic model to dict and return
        return result.model_dump()

    except ValueError as e:
        # Handle chart not found or other value errors
        error_message = str(e)
        if "not found" in error_message:
            chart_id = error_message.split(":")[-1].strip()
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": ERROR_CODES["CHART_NOT_FOUND"],
                        "message": f"Chart not found: {chart_id}",
                        "details": {"chart_id": chart_id}
                    }
                }
            )
        else:
            # Other validation errors
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": ERROR_CODES["VALIDATION_ERROR"],
                        "message": error_message,
                        "details": {}
                    }
                }
            )
    except Exception as e:
        logger.error(f"Error in chart comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": ERROR_CODES["INTERNAL_SERVER_ERROR"],
                    "message": f"Internal server error: {str(e)}",
                    "details": {
                        "chart1_id": chart1_id,
                        "chart2_id": chart2_id,
                        "type": str(type(e).__name__)
                    }
                }
            }
        )
