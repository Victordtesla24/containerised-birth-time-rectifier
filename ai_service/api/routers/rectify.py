"""
Birth Time Rectification Router.

This module provides endpoints for birth time rectification.
Following the Unified API Gateway architecture and providing proper versioning.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header, Request
import traceback
import json
from datetime import datetime
import asyncio
import uuid
import os

# Fix circular import by importing the module instead of the specific function
import ai_service.core.rectification.main as rectification_module
from ai_service.models import RectificationRequest, RectificationResponse
from ai_service.services import get_chart_service
from ai_service.utils.websocket_manager import get_websocket_manager
from ai_service.utils.websocket_events import EventType, emit_event

# Configure logging
logger = logging.getLogger(__name__)

# Create router with appropriate tags
router = APIRouter(
    tags=["rectification"],
    responses={404: {"description": "Not found"}}
)

@router.post("", response_model=RectificationResponse)
async def rectify_birth_time(
    request: RectificationRequest,
    background_tasks: BackgroundTasks,
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> RectificationResponse:
    """
    Rectify birth time based on questionnaire answers and life events.

    Args:
        request: Rectification request containing birth details and answers
        background_tasks: FastAPI background tasks
        session_id: Optional session ID for tracking

    Returns:
        Rectification result with original and rectified birth times
    """
    try:
        logger.info("Birth time rectification requested")

        birth_details = request.birth_details

        # Extract birth details
        birth_date = birth_details.get("birth_date") or birth_details.get("date")
        birth_time = birth_details.get("birth_time") or birth_details.get("time")
        latitude = birth_details.get("latitude")
        longitude = birth_details.get("longitude")
        timezone = birth_details.get("timezone")

        # Validate required parameters
        if not birth_date or not birth_time or latitude is None or longitude is None or not timezone:
            missing = []
            if not birth_date:
                missing.append("birth_date")
            if not birth_time:
                missing.append("birth_time")
            if latitude is None:
                missing.append("latitude")
            if longitude is None:
                missing.append("longitude")
            if not timezone:
                missing.append("timezone")

            raise HTTPException(
                status_code=400,
                detail=f"Missing required parameters: {', '.join(missing)}"
            )

        # Combine date and time for the rectification function
        birth_dt = f"{birth_date}T{birth_time}"

        # Get questionnaire answers
        answers = request.answers or []

        # Perform rectification using the imported module instead of the direct function
        rectification_result = await rectification_module.comprehensive_rectification(
            birth_dt=birth_dt,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            answers=answers
        )

        # Get chart service to generate charts
        chart_service = get_chart_service()

        # Generate chart with original birth time
        original_chart = await chart_service.generate_chart(
            birth_date=birth_date,
            birth_time=birth_time,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone
        )

        # Generate chart with rectified birth time
        rectified_time = rectification_result.get("rectified_time")
        rectified_chart = await chart_service.generate_chart(
            birth_date=birth_date,
            birth_time=rectified_time if rectified_time else "12:00:00",
            latitude=latitude,
            longitude=longitude,
            timezone=timezone
        )

        # Prepare response
        response = RectificationResponse(
            original_time=birth_time if birth_time else "00:00:00",
            rectified_time=rectified_time if rectified_time else "00:00:00",
            confidence=rectification_result.get("confidence", 0.0),
            original_chart_id=original_chart.get("chart_id"),
            rectified_chart_id=rectified_chart.get("chart_id"),
            explanation=rectification_result.get("explanation", ""),
            detected_events=rectification_result.get("detected_events", [])
        )

        logger.info(f"Birth time rectification completed: {birth_time} -> {rectified_time}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rectifying birth time: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Birth time rectification failed: {str(e)}")

@router.get("/status/{rectification_id}", response_model=Dict[str, Any])
async def get_rectification_status(rectification_id: str, session_id: Optional[str] = Header(None, alias="X-Session-ID")) -> Dict[str, Any]:
    """
    Get the status of a rectification process.

    Args:
        rectification_id: ID of the rectification process
        session_id: Session ID for authentication

    Returns:
        Status information about the rectification process
    """
    try:
        logger.info(f"Getting status for rectification {rectification_id}")

        # Import database utilities
        from ai_service.database.connection import get_db_pool

        # Get database connection pool
        pool = await get_db_pool()
        if not pool:
            logger.error("Database connection pool not available")
            raise RuntimeError("Database connection unavailable")

        # Query rectification status from database
        async with pool.acquire() as conn:
            query = """
                SELECT status, progress, message, result, created_at, updated_at
                FROM rectifications
                WHERE rectification_id = $1
            """

            row = await conn.fetchrow(query, rectification_id)

            if not row:
                # If not in database, check cache
                from ai_service.services.session_service import get_session_service
                session_service = get_session_service()

                # Try to get from session data if session ID provided
                if session_id:
                    try:
                        session_data = session_service.get_session(session_id)
                        if session_data and "rectifications" in session_data:
                            # Look for this rectification in session data
                            rectification_data = session_data["rectifications"].get(rectification_id)
                            if rectification_data:
                                logger.info(f"Found rectification {rectification_id} in session cache")
                                return {
                                    "rectification_id": rectification_id,
                                    "status": rectification_data.get("status", "unknown"),
                                    "progress": rectification_data.get("progress", 0),
                                    "message": rectification_data.get("message", "Unknown status"),
                                    "timestamp": rectification_data.get("timestamp", datetime.now().isoformat()),
                                    "result": rectification_data.get("result", {})
                                }
                    except Exception as session_error:
                        logger.warning(f"Error getting rectification from session: {session_error}")

                # Not found anywhere
                logger.warning(f"Rectification {rectification_id} not found")
                raise HTTPException(
                    status_code=404,
                    detail=f"Rectification {rectification_id} not found"
                )

            # Parse result JSON if present
            result = {}
            if row['result']:
                try:
                    result = json.loads(row['result']) if isinstance(row['result'], str) else row['result']
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse result JSON for rectification {rectification_id}")

            # Construct response
            response = {
                "rectification_id": rectification_id,
                "status": row['status'],
                "progress": row['progress'],
                "message": row['message'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                "result": result
            }

            logger.info(f"Retrieved status for rectification {rectification_id}: {row['status']}")
            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rectification status: {e}")
        logger.error(traceback.format_exc())

        # Fallback to checking file storage
        try:
            import os

            # Check if status file exists
            status_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "status")
            os.makedirs(status_dir, exist_ok=True)

            status_file = os.path.join(status_dir, f"{rectification_id}.json")

            if os.path.exists(status_file):
                with open(status_file, 'r') as f:
                    status_data = json.load(f)

                logger.info(f"Retrieved status for rectification {rectification_id} from file storage")
                return status_data
        except Exception as file_error:
            logger.error(f"Error getting rectification status from file: {file_error}")

        raise HTTPException(
            status_code=500,
            detail=f"Failed to get rectification status: {str(e)}"
        )
