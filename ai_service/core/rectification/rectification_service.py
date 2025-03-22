"""
Enhanced Rectification Service for Birth Time Analysis

This module provides advanced birth time rectification services
using multiple astrological methods and AI assistance.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import uuid
import json
import os

from .methods.ai_rectification import ai_assisted_rectification
from .methods.solar_arc import solar_arc_rectification
from .methods.progressed import progressed_ascendant_rectification
from .methods.transit_analysis import analyze_life_events
from .event_analysis import extract_life_events_from_answers
from .chart_calculator import calculate_chart
from .utils.ephemeris import verify_ephemeris_files
from .utils.storage import store_rectified_chart

# Setup logging
logger = logging.getLogger(__name__)

class EnhancedRectificationService:
    """
    Service for birth time rectification using multiple astrological methods.
    Implements comprehensive analysis of birth time using a combination of:
    - AI-assisted analysis
    - Solar arc directions
    - Progressed ascendant method
    - Transit analysis of life events
    """

    def __init__(self, openai_service=None, chart_repository=None):
        """
        Initialize the rectification service.

        Args:
            openai_service: Optional OpenAI service for AI-assisted rectification
            chart_repository: Optional chart repository for storing results
        """
        self.openai_service = openai_service
        self.chart_repository = chart_repository
        logger.info("Enhanced rectification service initialized")

    async def process_rectification(
        self,
        birth_dt: datetime,
        latitude: float,
        longitude: float,
        timezone: str,
        answers: List[Dict[str, Any]],
        chart_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process birth time rectification using questionnaire answers.
        This is a wrapper method that delegates to rectify_birth_time.

        Args:
            birth_dt: Original birth datetime
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees
            timezone: Timezone string (e.g., 'Asia/Kolkata')
            answers: List of questionnaire answers for analysis
            chart_id: Optional chart ID to associate with this rectification

        Returns:
            Dictionary with rectification results
        """
        logger.info(f"Processing rectification for birth time {birth_dt} with {len(answers)} answers")

        # Extract life events from answers if provided
        events = extract_life_events_from_answers(answers) if answers else None

        # Delegate to the actual rectification method
        result = await self.rectify_birth_time(
            birth_dt=birth_dt,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            answers=answers,
            events=events,
            chart_id=chart_id
        )

        return result

    async def rectify_birth_time(
        self,
        birth_dt: datetime,
        latitude: float,
        longitude: float,
        timezone: str,
        answers: Optional[List[Dict[str, Any]]] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        chart_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rectify birth time using comprehensive analysis of multiple methods.

        Args:
            birth_dt: Original birth datetime
            latitude: Birth latitude in decimal degrees
            longitude: Birth longitude in decimal degrees
            timezone: Timezone string (e.g., 'Asia/Kolkata')
            answers: List of questionnaire answers, each as a dictionary
            events: Optional pre-extracted life events
            chart_id: Optional chart ID to associate with this rectification

        Returns:
            Dictionary with rectification results
        """
        # Generate a rectification ID for tracking
        rectification_id = f"rect_{uuid.uuid4().hex[:8]}"

        logger.info(f"Starting rectification {rectification_id} for {birth_dt} at {latitude}, {longitude}")

        # Verify ephemeris files are available
        if not verify_ephemeris_files():
            logger.warning("Proceeding with rectification but ephemeris files may be incomplete")

        # Extract life events from answers if not provided
        if not events and answers:
            events = extract_life_events_from_answers(answers)

        # Ensure we have at least an empty list of events
        if not events:
            events = []
            logger.warning("No life events found in answers, this reduces rectification accuracy")

        # Initialize results tracking
        methods_attempted = []
        methods_succeeded = []
        candidates = []

        # Try AI-assisted rectification if OpenAI service is available
        if self.openai_service:
            try:
                methods_attempted.append("ai_rectification")
                ai_time, ai_confidence = await ai_assisted_rectification(
                    birth_dt, latitude, longitude, timezone, self.openai_service,
                    answers=answers, events=events
                )
                methods_succeeded.append("ai_rectification")
                candidates.append((ai_time, ai_confidence, "ai"))
            except Exception as e:
                logger.warning(f"AI-assisted rectification failed: {e}")

        # Try solar arc rectification
        try:
            methods_attempted.append("solar_arc")
            solar_arc_time, solar_arc_confidence = await solar_arc_rectification(
                birth_dt, latitude, longitude, timezone
            )
            methods_succeeded.append("solar_arc")
            candidates.append((solar_arc_time, solar_arc_confidence, "solar_arc"))
        except Exception as e:
            logger.warning(f"Solar arc rectification failed: {e}")

        # Try progressed ascendant rectification
        try:
            methods_attempted.append("progressed")
            progressed_time, progressed_confidence = await progressed_ascendant_rectification(
                birth_dt, latitude, longitude, timezone
            )
            methods_succeeded.append("progressed")
            candidates.append((progressed_time, progressed_confidence, "progressed"))
        except Exception as e:
            logger.warning(f"Progressed ascendant rectification failed: {e}")

        # If we have events, try transit analysis
        if events:
            try:
                methods_attempted.append("transit")
                transit_time, transit_confidence = await analyze_life_events(
                    events, birth_dt, latitude, longitude, timezone
                )
                methods_succeeded.append("transit")
                candidates.append((transit_time, transit_confidence, "transit"))
            except Exception as e:
                logger.warning(f"Transit analysis failed: {e}")

        # If no methods succeeded, return original time with low confidence
        if not candidates:
            logger.warning("No rectification methods succeeded")
            result = {
                "rectification_id": rectification_id,
                "original_time": birth_dt,
                "rectified_time": birth_dt,
                "confidence_score": 50.0,
                "methods_attempted": methods_attempted,
                "methods_succeeded": [],
                "time_difference": "00:00:00",
                "explanation": "No rectification methods succeeded, returning original time"
            }
            return result

        # Sort by confidence (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)

        # If only one method succeeded, return its result
        if len(candidates) == 1:
            rectified_time = candidates[0][0]
            confidence = candidates[0][1]
            method = candidates[0][2]
        else:
            # Calculate weighted average time
            total_confidence = sum(c[1] for c in candidates)
            weights = [c[1]/total_confidence for c in candidates]

            # Convert times to minutes since midnight
            midnight = birth_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            time_minutes = []

            for candidate in candidates:
                cand_time = candidate[0]
                minutes = (cand_time.hour * 60) + cand_time.minute
                time_minutes.append(minutes)

            # Calculate weighted average minutes
            weighted_minutes = sum(minutes * weight for minutes, weight in zip(time_minutes, weights))
            weighted_minutes = round(weighted_minutes)

            # Convert back to hours and minutes
            hours = weighted_minutes // 60
            minutes = weighted_minutes % 60

            # Create final datetime
            rectified_time = birth_dt.replace(hour=hours, minute=minutes, second=0, microsecond=0)

            # Final confidence is weighted average of individual confidences
            confidence = sum(c[1] * w for c, w in zip(candidates, weights))
            method = "combined"

        # Calculate time difference
        time_diff = rectified_time - birth_dt
        hours, remainder = divmod(abs(time_diff.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_difference = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

        # Add sign to indicate earlier or later
        if time_diff.total_seconds() < 0:
            time_difference = f"-{time_difference}"
        else:
            time_difference = f"+{time_difference}"

        # Generate explanation
        if method == "combined":
            explanation = f"Birth time rectified using multiple methods ({', '.join(methods_succeeded)}). "
            explanation += f"The weighted analysis suggests a time adjustment of {time_difference}."
        else:
            explanation = f"Birth time rectified using {method}. "
            explanation += f"Analysis suggests a time adjustment of {time_difference}."

        # Calculate the rectified chart
        try:
            rectified_chart = calculate_chart(
                birth_dt=rectified_time,
                latitude=latitude,
                longitude=longitude,
                timezone_str=timezone
            )
            rectified_chart_id = rectified_chart.get("chart_id", f"chart_{uuid.uuid4().hex[:8]}")
        except Exception as e:
            logger.error(f"Failed to calculate rectified chart: {e}")
            rectified_chart = None
            rectified_chart_id = None

        # Prepare result
        result = {
            "rectification_id": rectification_id,
            "original_time": birth_dt,
            "rectified_time": rectified_time,
            "confidence_score": round(confidence, 1),
            "methods_attempted": methods_attempted,
            "methods_succeeded": methods_succeeded,
            "time_difference": time_difference,
            "explanation": explanation,
            "rectified_chart_id": rectified_chart_id
        }

        # Store result if chart repository is available
        if self.chart_repository and chart_id:
            try:
                await self.chart_repository.store_rectification_result(
                    rectification_id, result, chart_id
                )
                logger.info(f"Stored rectification result {rectification_id} for chart {chart_id}")
            except Exception as e:
                logger.error(f"Failed to store rectification result: {e}")

        # Store rectified chart if available
        if rectified_chart and self.chart_repository:
            try:
                await store_rectified_chart(
                    chart_data=rectified_chart,
                    rectification_id=rectification_id,
                    birth_dt=birth_dt,
                    rectified_time_dt=rectified_time
                )
                logger.info(f"Stored rectified chart {rectified_chart_id}")
            except Exception as e:
                logger.error(f"Failed to store rectified chart: {e}")

        logger.info(f"Rectification complete: {rectified_time}, confidence: {confidence:.1f}")
        return result

    async def save_rectification_result(self, result: Dict[str, Any]) -> None:
        """
        Save the rectification result to the repository.

        Args:
            result: Dictionary with rectification results
        """
        try:
            if self.chart_repository:
                # Store rectification results in the database
                await self.chart_repository.store_rectification_result(result)
                logger.info(f"Saved rectification result with ID {result.get('rectification_id')}")
            else:
                # Fallback to storing in a JSON file
                # Create directory if it doesn't exist
                os.makedirs("data/rectifications", exist_ok=True)

                # Write to file named by rectification ID
                rectification_id = result.get("rectification_id", "unknown")
                filepath = f"data/rectifications/{rectification_id}.json"

                with open(filepath, "w") as f:
                    json.dump(result, f, indent=2)

                logger.info(f"Saved rectification result to file: {filepath}")
        except Exception as e:
            logger.error(f"Error saving rectification result: {e}")
            # Continue execution rather than failing
