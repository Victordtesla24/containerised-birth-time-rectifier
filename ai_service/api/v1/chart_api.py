"""
V1 API implementation for chart generation.

This module provides a robust implementation of the chart generation API
for V1 endpoints that strictly follows the sequence diagram.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, Field

# Import chart service modules
from ai_service.api.v1.chart_service import generate_chart_v1
from ai_service.services.chart_service_verification import verify_chart_with_openai

# Set up logging
logger = logging.getLogger(__name__)

# Create API V1 router for charts
v1_router = APIRouter(prefix="/api/v1", tags=["Chart V1 API"])

# Define data models
class BirthDetailsV1(BaseModel):
    """Birth details for chart generation."""
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format")
    birth_time: str = Field(..., description="Birth time in HH:MM:SS format")
    latitude: float = Field(..., description="Birth latitude")
    longitude: float = Field(..., description="Birth longitude")
    timezone: Optional[str] = Field(None, description="Timezone string (e.g., 'America/New_York')")
    location: Optional[str] = Field(None, description="Birth location name")
    house_system: Optional[str] = Field("P", description="House system to use (e.g., 'P' for Placidus)")
    zodiac_type: Optional[str] = Field("sidereal", description="Zodiac type (sidereal or tropical)")

class ChartGenerationRequestV1(BaseModel):
    """Request body for chart generation in API v1."""
    birth_details: BirthDetailsV1 = Field(..., description="Birth details for chart generation")
    verify_with_openai: bool = Field(True, description="Whether to verify the chart with OpenAI")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    generate_visualization: bool = Field(True, description="Whether to generate chart visualization")

class ChartResponseV1(BaseModel):
    """Response body for chart endpoints in API v1."""
    status: str = Field(..., description="Status of the operation")
    message: Optional[str] = Field(None, description="Message about the operation")
    chart_id: Optional[str] = Field(None, description="Generated chart ID")
    chart_data: Optional[Dict[str, Any]] = Field(None, description="Chart data")
    verification: Optional[Dict[str, Any]] = Field(None, description="Verification results if verified")

# Background task functions
async def generate_chart_visualization_v1(chart_data: Dict[str, Any]) -> None:
    """
    Background task to generate chart visualizations for API v1.

    Args:
        chart_data: The chart data to visualize
    """
    try:
        # Import chart service directly to avoid circular imports
        from ai_service.services import get_chart_service_async

        # Get chart service asynchronously
        chart_service = await get_chart_service_async()

        # Generate Vedic chart visualization
        try:
            chart_service.generate_vedic_kundli_chart(chart_data)
            logger.info(f"Generated Vedic chart for chart_id: {chart_data.get('chart_id')}")
        except Exception as e:
            logger.error(f"Error generating Vedic chart: {e}")

        # Generate Western chart visualization
        try:
            chart_service.generate_western_chart(chart_data)
            logger.info(f"Generated Western chart for chart_id: {chart_data.get('chart_id')}")
        except Exception as e:
            logger.error(f"Error generating Western chart: {e}")

    except Exception as e:
        logger.error(f"Error in chart visualization background task: {e}")

@v1_router.post("/charts/generate", response_model=ChartResponseV1)
async def generate_chart_api_v1(
    chart_request: ChartGenerationRequestV1,
    background_tasks: BackgroundTasks,
    request: Request
) -> ChartResponseV1:
    """
    Generate a new astrological chart based on birth details for API v1.

    This endpoint strictly follows the sequence diagram flow:
    1. Validate input (done by Pydantic)
    2. Calculate initial chart
    3. Verify with OpenAI if requested
    4. Apply corrections if needed
    5. Store in database
    6. Generate visualizations in background
    7. Return chart data

    Args:
        chart_request: Birth details and options
        background_tasks: FastAPI background tasks
        request: FastAPI request object

    Returns:
        ChartResponseV1: Generated chart data with verification status
    """
    logger.info(f"V1 API: Generating chart with request: {chart_request}")

    try:
        # Get or create session ID
        session_id = request.headers.get("X-Session-ID") or chart_request.session_id

        # STEP 1: Generate the chart with the defensive v1 implementation
        chart_data = await generate_chart_v1(
            birth_date=chart_request.birth_details.birth_date,
            birth_time=chart_request.birth_details.birth_time,
            latitude=chart_request.birth_details.latitude,
            longitude=chart_request.birth_details.longitude,
            timezone=chart_request.birth_details.timezone,
            location=chart_request.birth_details.location,
            verify_with_openai=False,  # We'll verify separately
            session_id=session_id
        )

        # STEP 2: Verify with OpenAI if requested
        if chart_request.verify_with_openai:
            try:
                verification_result = await verify_chart_with_openai(chart_data, session_id)
                chart_data["verification"] = verification_result
                logger.info(f"V1 API: Chart verification completed for chart {chart_data.get('chart_id')}")
            except Exception as e:
                logger.error(f"V1 API: Error verifying chart: {e}")
                chart_data["verification"] = {
                    "status": "verification_error",
                    "message": f"Error during verification: {str(e)}",
                    "verified_with_openai": False,
                    "corrections_applied": False,
                    "corrections": []
                }
        else:
            # Skip verification as requested
            chart_data["verification"] = {
                "status": "verification_skipped",
                "message": "Verification not requested",
                "verified_with_openai": False,
                "corrections_applied": False,
                "corrections": []
            }

        # STEP 3: Generate chart visualization in the background
        if chart_request.generate_visualization:
            background_tasks.add_task(
                generate_chart_visualization_v1,
                chart_data=chart_data
            )

        # STEP 4: Return chart data with success status
        return ChartResponseV1(
            status="success",
            message="Chart generated successfully",
            chart_id=chart_data["chart_id"],
            chart_data=chart_data,
            verification=chart_data.get("verification", {})
        )

    except ValueError as e:
        # Handle validation errors
        logger.error(f"V1 API: Validation error in chart generation: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Invalid chart data: {str(e)}"
        )

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"V1 API: Error generating chart: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Chart generation failed: {str(e)}"
        )

@v1_router.post("/charts/verify", response_model=Dict[str, Any])
async def verify_chart_api_v1(
    chart_id: str = Field(..., description="Chart ID to verify"),
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify a chart using OpenAI for API v1.

    This endpoint performs comprehensive verification of an astrological chart against
    Vedic astrological principles using OpenAI's advanced language model capabilities.
    The verification process:

    1. Retrieves the existing chart data from storage
    2. Sends the chart to OpenAI with expert astrological prompts
    3. Analyzes the response to extract confidence scores and corrections
    4. Returns detailed verification results

    The confidence scoring system (0-1 scale) works as follows:
    - 0.9-1.0: High confidence - chart is accurate and well-formed
    - 0.7-0.9: Good confidence - minor discrepancies, but chart is generally accurate
    - 0.5-0.7: Moderate confidence - some issues detected, but chart is usable
    - 0.3-0.5: Low confidence - significant issues detected, chart may be unreliable
    - 0.0-0.3: Very low confidence - major issues detected, chart is likely incorrect

    Args:
        chart_id: ID of the chart to verify
        session_id: Optional session ID for tracking

    Returns:
        Verification results including confidence score and suggested corrections
    """
    logger.info(f"V1 API: Verifying chart {chart_id}")

    try:
        # First check if OpenAI service is available
        from ai_service.api.services.openai import get_openai_service

        try:
            openai_service = await get_openai_service()
            if not openai_service:
                logger.error("OpenAI service unavailable for verification")
                return {
                    "verificationId": f"ver_{uuid.uuid4().hex[:8]}",
                    "status": "service_unavailable",
                    "error": "OpenAI service unavailable",
                    "result": {
                        "confidence": 0.5,  # Moderate default confidence
                        "confidence_description": "Verification unavailable - OpenAI service not available",
                        "verified": False,
                        "verified_with_openai": False,
                        "suggestedCorrection": {
                            "adjustment": "None",
                            "newTime": "",
                            "reason": "Verification unavailable"
                        },
                        "analysis": "OpenAI verification service is currently unavailable. The chart was generated but could not be verified."
                    }
                }
        except Exception as openai_error:
            logger.error(f"Error initializing OpenAI service: {openai_error}")
            return {
                "verificationId": f"ver_{uuid.uuid4().hex[:8]}",
                "status": "service_error",
                "error": f"OpenAI service error: {str(openai_error)}",
                "result": {
                    "confidence": 0.5,  # Moderate default confidence
                    "confidence_description": "Verification unavailable - OpenAI service error",
                    "verified": False,
                    "verified_with_openai": False,
                    "suggestedCorrection": {
                        "adjustment": "None",
                        "newTime": "",
                        "reason": "Verification unavailable"
                    },
                    "analysis": f"Error connecting to OpenAI verification service: {str(openai_error)}"
                }
            }

        # Get chart repository
        from ai_service.database.repositories import ChartRepository
        chart_repository = ChartRepository()

        # Get the chart data
        try:
            chart_data = await chart_repository.get_chart(chart_id)
            if not chart_data:
                raise HTTPException(status_code=404, detail=f"Chart with ID {chart_id} not found")
        except Exception as db_error:
            logger.error(f"Database error retrieving chart {chart_id}: {db_error}")
            if "not found" in str(db_error).lower():
                raise HTTPException(status_code=404, detail=f"Chart with ID {chart_id} not found")
            else:
                raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")

        # Generate a verification ID
        verification_id = f"ver_{uuid.uuid4().hex[:8]}"

        # Import verification function
        from ai_service.services.chart_service_verification import verify_chart_with_openai

        # Verify chart with timeout handling
        try:
            import asyncio
            # Set a timeout for verification (30 seconds)
            verification_data = await asyncio.wait_for(
                verify_chart_with_openai(chart_data, session_id),
                timeout=30.0
            )

            # Get confidence score and ensure it's within 0-1 range
            confidence = verification_data.get("confidence", 0.7)  # Default moderate confidence
            confidence = max(0.0, min(1.0, confidence))  # Clamp to 0-1 range

            # Add confidence description if not present
            if "confidence_description" not in verification_data:
                if confidence >= 0.9:
                    confidence_description = "High confidence - chart is accurate and well-formed"
                elif confidence >= 0.7:
                    confidence_description = "Good confidence - minor discrepancies, but chart is generally accurate"
                elif confidence >= 0.5:
                    confidence_description = "Moderate confidence - some issues detected, but chart is usable"
                elif confidence >= 0.3:
                    confidence_description = "Low confidence - significant issues detected, chart may be unreliable"
                else:
                    confidence_description = "Very low confidence - major issues detected, chart is likely incorrect"
                verification_data["confidence_description"] = confidence_description

            # Format the verification response
            verification_result = {
                "verificationId": verification_id,
                "status": "success",
                "result": {
                    "confidence": confidence,
                    "confidence_description": verification_data.get("confidence_description", ""),
                    "verified": verification_data.get("verified", False),
                    "verified_with_openai": verification_data.get("verified_with_openai", True),
                    "suggestedCorrection": {
                        "adjustment": verification_data.get("suggested_adjustment", "None"),
                        "newTime": verification_data.get("suggested_time", chart_data.get("birth_details", {}).get("time", "")),
                        "reason": verification_data.get("adjustment_reason", "No adjustments needed")
                    },
                    "analysis": verification_data.get("verification_text", "Chart verified successfully.")
                }
            }

            # Add corrections if any
            if verification_data.get("corrections_applied", False) and "corrections" in verification_data:
                verification_result["result"]["corrections"] = verification_data["corrections"]

            # Store verification result with the chart
            try:
                # Add verification to chart data
                chart_data["verification"] = verification_data
                # Update the chart in the database
                await chart_repository.update_chart(chart_id, chart_data)
            except Exception as update_error:
                logger.error(f"Error updating chart with verification data: {update_error}")
                # Continue without failing, we can still return the verification result

        except asyncio.TimeoutError:
            logger.error(f"Verification timeout for chart {chart_id}")
            verification_result = {
                "verificationId": verification_id,
                "status": "timeout",
                "error": "Verification timeout",
                "result": {
                    "confidence": 0.5,  # Moderate default confidence
                    "confidence_description": "Verification incomplete - timeout occurred",
                    "verified": False,
                    "verified_with_openai": False,
                    "suggestedCorrection": {
                        "adjustment": "None",
                        "newTime": chart_data.get("birth_details", {}).get("time", ""),
                        "reason": "Verification timeout"
                    },
                    "analysis": "Verification process timed out after 30 seconds. This may be due to high server load or a complex chart analysis."
                }
            }
        except Exception as e:
            logger.error(f"V1 API: Error in chart verification: {e}")
            verification_result = {
                "verificationId": verification_id,
                "status": "error",
                "error": str(e),
                "result": {
                    "confidence": 0.3,  # Low confidence due to error
                    "confidence_description": "Verification failed - processing error",
                    "verified": False,
                    "verified_with_openai": False,
                    "suggestedCorrection": {
                        "adjustment": "None",
                        "newTime": chart_data.get("birth_details", {}).get("time", ""),
                        "reason": "Verification error"
                    },
                    "analysis": f"Chart verification encountered an error: {str(e)}"
                }
            }

        logger.info(f"V1 API: Chart verification completed with ID: {verification_id}")
        return verification_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"V1 API: Error verifying chart: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # Create a more detailed error response that includes error type
        error_response = {
            "verificationId": f"ver_{uuid.uuid4().hex[:8]}",
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }

        # Add recovery suggestions based on error type
        if isinstance(e, ConnectionError) or "connection" in str(e).lower():
            error_response["recovery_suggestion"] = "Check network connection and retry"
        elif isinstance(e, TimeoutError) or "timeout" in str(e).lower():
            error_response["recovery_suggestion"] = "The server may be under high load, try again later"
        elif "openai" in str(e).lower() or "api key" in str(e).lower():
            error_response["recovery_suggestion"] = "Check OpenAI API key and quota"
        else:
            error_response["recovery_suggestion"] = "Contact support if the problem persists"

        raise HTTPException(status_code=500, detail=error_response)
