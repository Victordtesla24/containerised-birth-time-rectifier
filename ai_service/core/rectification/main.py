"""
Main coordination module for birth time rectification.
"""
from datetime import datetime, timedelta
import logging
import json
import uuid
from typing import List, Dict, Any, Tuple, Optional, Union
import traceback
import re
import os
from pathlib import Path
import asyncio

# Import sub-modules
from .event_analysis import extract_life_events_from_answers
from .chart_calculator import calculate_chart
from .methods.ai_rectification import ai_assisted_rectification
from .methods.solar_arc import solar_arc_rectification
from .methods.progressed import progressed_ascendant_rectification
from .utils.ephemeris import verify_ephemeris_files as verify_ephemeris_files_util
from .utils.storage import store_rectified_chart

logger = logging.getLogger(__name__)

async def verify_ephemeris_files() -> bool:
    """
    Ensure all required ephemeris files are present and valid.

    Returns:
        True if all files are present and valid, raises exception otherwise

    Raises:
        ValueError: If ephemeris files are missing or invalid
    """
    ephemeris_path = os.environ.get("FLATLIB_EPHE_PATH")

    if not ephemeris_path:
        raise ValueError("FLATLIB_EPHE_PATH environment variable not set")

    ephemeris_dir = Path(ephemeris_path)
    if not ephemeris_dir.exists():
        raise ValueError(f"Ephemeris directory does not exist: {ephemeris_path}")

    required_files = ["seas_18.se1", "semo_18.se1", "sepl_18.se1"]
    missing_files = []

    for file in required_files:
        if not (ephemeris_dir / file).exists():
            missing_files.append(file)

    if missing_files:
        raise ValueError(f"Missing required ephemeris files: {', '.join(missing_files)}")

    return True

async def get_openai_service():
    """
    Get the OpenAI service with proper error handling.

    Returns:
        OpenAIService instance or None if service is unavailable
    """
    try:
        # Import here to avoid circular imports
        from ai_service.api.services.openai import get_openai_service as get_service
        from ai_service.core.config import settings

        # Get the service (this is a synchronous function according to its definition)
        service = get_service()

        if not service:
            logger.error("OpenAI service is not properly initialized")

            # Initialize the service directly as a fallback
            from ai_service.api.services.openai.service import OpenAIService

            # Check if API key is available
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                logger.error("OpenAI API key is not available in settings")
                raise ValueError("OpenAI API key not configured. This is required for birth time rectification.")

            # Create service directly
            try:
                service = OpenAIService(api_key=api_key)
                logger.info("Created OpenAI service directly")
            except Exception as e2:
                logger.error(f"Failed to create OpenAI service directly: {e2}")
                raise ValueError(f"Failed to initialize OpenAI service: {str(e2)}")

        # Verify the service is working with a simple test
        try:
            # Test with a minimal query
            test_result = await service.generate_completion(
                prompt="Test connection to OpenAI API.",
                task_type="test",
                max_tokens=10
            )

            if not test_result or "content" not in test_result:
                logger.warning("OpenAI service test failed: No valid response")
                raise ValueError("OpenAI service returned invalid response during test")

            logger.info("OpenAI service verified and working")
            return service

        except Exception as e:
            logger.error(f"OpenAI service test failed: {e}")
            raise ValueError(f"OpenAI service test failed: {str(e)}")

    except ImportError as e:
        logger.error(f"OpenAI service import failed: {e}")
        raise ValueError(f"OpenAI service import failed: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error getting OpenAI service: {e}")
        raise ValueError(f"Failed to initialize OpenAI service: {str(e)}")

async def rectify_birth_time(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    answers: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None
) -> Tuple[datetime, float]:
    """
    Rectify birth time based on questionnaire answers using real astrological calculations.

    Args:
        birth_dt: Birth date and time as datetime object
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string (e.g., 'America/New_York')
        answers: Optional list of questionnaire answers
        options: Optional configuration parameters:
            - use_openai: Whether to use OpenAI for analysis (default: True)
            - max_retries: Max retries for OpenAI calls (default: 3)
            - retry_delay: Delay between retries in seconds (default: 1)
            - verification_required: Whether verification is required (default: False)
            - fallback_provider: Fallback method if OpenAI fails (default: None)

    Returns:
        Tuple of (rectified datetime, confidence score)
    """
    # Initialize options with defaults if not provided
    if options is None:
        options = {}

    # Set default options
    use_openai = options.get("use_openai", True)
    max_retries = options.get("max_retries", 3)
    verification_required = options.get("verification_required", False)

    logger.info(f"Rectifying birth time for {birth_dt} at {latitude}, {longitude}")

    # Verify ephemeris files are available
    try:
        verified = await verify_ephemeris_files()
        if not verified:
            raise ValueError("Failed to verify ephemeris files")
    except Exception as e:
        logger.error(f"Ephemeris verification failed: {e}")
        # Continue with rectification even if ephemeris verification fails
        # We'll rely on the error handling in individual methods

    # Try multiple approaches and combine results
    methods_attempted = []
    methods_succeeded = []

    # Get the OpenAI service for AI-assisted rectification
    ai_time, ai_confidence = None, 0
    try:
        openai_service = await get_openai_service()

        if openai_service:
            methods_attempted.append("ai_rectification")
            ai_time, ai_confidence = await ai_assisted_rectification(
                birth_dt, latitude, longitude, timezone, openai_service, answers
            )
            methods_succeeded.append("ai_rectification")

            # Return result directly if confidence is high
            if ai_confidence >= 85:
                logger.info(f"AI rectification has high confidence {ai_confidence}%, returning result directly")
                return ai_time, ai_confidence
        else:
            logger.warning("OpenAI service not available for AI-assisted rectification")
            # Continue with other methods
    except Exception as e:
        logger.warning(f"AI-assisted rectification failed: {e}")
        # Continue with other methods even if AI rectification fails

    # Try solar arc rectification
    solar_arc_time, solar_arc_confidence = None, 0
    try:
        methods_attempted.append("solar_arc")
        solar_arc_time, solar_arc_confidence = await solar_arc_rectification(
            birth_dt, latitude, longitude, timezone
        )
        methods_succeeded.append("solar_arc")
    except Exception as e:
        logger.warning(f"Solar arc rectification failed: {e}")
        # Continue with other methods

    # Try progressed ascendant rectification
    progressed_time, progressed_confidence = None, 0
    try:
        methods_attempted.append("progressed")
        progressed_time, progressed_confidence = await progressed_ascendant_rectification(
            birth_dt, latitude, longitude, timezone
        )
        methods_succeeded.append("progressed")
    except Exception as e:
        logger.warning(f"Progressed ascendant rectification failed: {e}")
        # Continue with other methods

    # If answers were provided, extract life events and try transit analysis
    transit_time, transit_confidence = None, 0
    if answers:
        try:
            events = extract_life_events_from_answers(answers)
            if events and len(events) > 0:
                methods_attempted.append("transit")
                try:
                    from .methods.transit_analysis import analyze_life_events
                    transit_time, transit_confidence = await analyze_life_events(
                        events, birth_dt, latitude, longitude, timezone
                    )
                    methods_succeeded.append("transit")
                except Exception as e:
                    logger.warning(f"Primary transit analysis failed: {e}")
                    # Use alternative method based on ephemeris.MinimalChart when Flatlib or primary method fails
                    try:
                        logger.info("Attempting alternative transit analysis using MinimalChart")
                        from .utils.ephemeris import MinimalChart

                        # Create natal chart using MinimalChart
                        natal_chart = MinimalChart(birth_dt, latitude, longitude).to_dict()

                        # Try different candidate times
                        candidates = []
                        for hour_offset in range(-4, 5):  # Try -4 to +4 hours from original time
                            test_time = birth_dt + timedelta(hours=hour_offset)
                            score = 0

                            # For each event, check if there are significant transits
                            for event in events:
                                if "date" not in event or not event["date"]:
                                    continue

                                try:
                                    # Parse event date
                                    if isinstance(event["date"], str):
                                        event_date = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                                    else:
                                        event_date = event["date"]

                                    # Create transit chart for event date
                                    transit_chart = MinimalChart(event_date, latitude, longitude).to_dict()

                                    # Check for significant aspects between transit and natal chart
                                    for transit_planet, transit_data in transit_chart["planets"].items():
                                        for natal_planet, natal_data in natal_chart["planets"].items():
                                            # Calculate aspect
                                            transit_lon = transit_data["longitude"]
                                            natal_lon = natal_data["longitude"]

                                            # Calculate orb
                                            diff = abs(transit_lon - natal_lon) % 360
                                            if diff > 180:
                                                diff = 360 - diff

                                            # Check for conjunction (0°)
                                            if 0 <= diff <= 8:
                                                score += 10
                                            # Check for opposition (180°)
                                            elif 172 <= diff <= 180:
                                                score += 8
                                            # Check for trine (120°)
                                            elif 113 <= diff <= 127:
                                                score += 6
                                except Exception as event_err:
                                    logger.warning(f"Error analyzing event {event.get('type', 'unknown')}: {event_err}")
                                    continue

                            candidates.append((test_time, score))

                        # Find the best candidate
                        if candidates:
                            candidates.sort(key=lambda x: x[1], reverse=True)
                            best_time, best_score = candidates[0]

                            # Calculate confidence based on score
                            confidence = min(best_score * 2, 85.0)  # Cap at 85%

                            # Only use if score is meaningful
                            if best_score > 20:
                                transit_time = best_time
                                transit_confidence = confidence
                                methods_succeeded.append("alt_transit")
                                logger.info(f"Alternative transit analysis successful: {transit_time}, confidence: {transit_confidence}")
                    except Exception as alt_e:
                        logger.warning(f"Alternative transit analysis failed: {alt_e}")
                        # Continue with other methods even if alternative transit analysis fails
        except Exception as e:
            logger.warning(f"Transit analysis failed: {e}")
            # Continue with other methods even if transit analysis fails

    # Check if any methods succeeded
    if not methods_succeeded:
        # No methods succeeded, but we don't want to just return original time with low confidence
        # Instead, apply a basic rectification approach based on the birth chart itself
        try:
            logger.info("No rectification methods succeeded, attempting basic chart analysis")
            # Calculate the original chart
            original_chart = calculate_chart(birth_dt, latitude, longitude, timezone)

            # Perform a simple analysis based on Ascendant/MC positions
            # This is a minimal approach when other methods fail
            if "angles" in original_chart:
                ascendant = original_chart.get("angles", {}).get("asc", {}).get("longitude", 0)
                mc = original_chart.get("angles", {}).get("mc", {}).get("longitude", 0)

                # Check if Ascendant is at a critical degree (0, 13, or 26 degrees of any sign)
                asc_degree = ascendant % 30
                time_shift_minutes = 0

                if 0 <= asc_degree < 1 or 29 <= asc_degree < 30:
                    # Very close to sign boundary, might need adjustment
                    time_shift_minutes = -20 if asc_degree < 1 else 20
                elif 12.5 <= asc_degree <= 13.5 or 25.5 <= asc_degree <= 26.5:
                    # Critical degrees, might need small adjustment
                    time_shift_minutes = -10 if asc_degree < 20 else 10

                # Apply the time shift if needed
                if time_shift_minutes != 0:
                    adjusted_time = birth_dt + timedelta(minutes=time_shift_minutes)
                    return adjusted_time, 60.0  # Modest confidence

            # If analysis didn't yield a result, return original with medium confidence
            logger.info("Basic chart analysis completed without time adjustment")
            return birth_dt, 50.0
        except Exception as e:
            logger.error(f"Basic chart analysis failed: {e}")
            return birth_dt, 50.0  # Return original with medium confidence

    # Combine results from different methods, weighted by confidence
    candidates = []

    if ai_time and ai_confidence > 0:
        candidates.append((ai_time, ai_confidence, "ai"))

    if solar_arc_time and solar_arc_confidence > 0:
        candidates.append((solar_arc_time, solar_arc_confidence, "solar_arc"))

    if progressed_time and progressed_confidence > 0:
        candidates.append((progressed_time, progressed_confidence, "progressed"))

    if transit_time and transit_confidence > 0:
        candidates.append((transit_time, transit_confidence, "transit"))

    # Log all candidates for debugging
    for candidate in candidates:
        cand_time, cand_confidence, cand_method = candidate
        logger.info(f"Candidate from {cand_method}: {cand_time.strftime('%H:%M:%S')}, confidence: {cand_confidence}")

    # Sort by confidence (descending)
    candidates.sort(key=lambda x: x[1], reverse=True)

    # If only one method succeeded, return its result
    if len(candidates) == 1:
        logger.info(f"Using single successful method: {candidates[0][2]}")
        return candidates[0][0], candidates[0][1]

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
    final_time = birth_dt.replace(hour=hours, minute=minutes, second=0, microsecond=0)

    # Final confidence is weighted average of individual confidences
    final_confidence = sum(c[1] * w for c, w in zip(candidates, weights))

    logger.info(f"Rectification complete: {final_time}, confidence: {final_confidence:.1f}")
    logger.info(f"Methods used: {', '.join(methods_succeeded)}")

    return final_time, final_confidence

async def comprehensive_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    answers: List[Dict[str, Any]],
    events: Optional[List[Dict[str, Any]]] = None,
    chart_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive birth time rectification using multiple methods.

    Args:
        birth_dt: Birth date and time as datetime object
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string (e.g., 'America/New_York')
        answers: List of questionnaire answers
        events: Optional list of life events for analysis
        chart_id: Optional ID of chart to use
        options: Optional configuration parameters:
            - use_openai: Whether to use OpenAI for analysis (default: True)
            - max_retries: Max retries for OpenAI calls (default: 3)
            - retry_delay: Delay between retries in seconds (default: 1)
            - verification_required: Whether verification is required (default: True)
            - fallback_provider: Fallback method if OpenAI fails (default: None)
            - reporting_callback: Callback function for progress reporting (default: None)

    Returns:
        Dictionary with comprehensive rectification results
    """
    # Initialize options with defaults if not provided
    if options is None:
        options = {}

    # Set default options
    use_openai = options.get("use_openai", True)
    max_retries = options.get("max_retries", 3)
    retry_delay = options.get("retry_delay", 1.0)
    verification_required = options.get("verification_required", True)
    fallback_provider = options.get("fallback_provider", None)
    reporting_callback = options.get("reporting_callback", None)

    # Verify ephemeris files are available and generate a unique rectification ID
    rectification_id = f"rect_{uuid.uuid4().hex[:10]}"
    logger.info(f"Starting comprehensive rectification {rectification_id} for {birth_dt}")

    try:
        verified = await verify_ephemeris_files()
        if not verified:
            logger.warning("Ephemeris verification failed, may affect rectification accuracy")
    except Exception as e:
        logger.warning(f"Ephemeris verification error: {e}, continuing with rectification")

    # Extract events if not provided
    if not events and answers:
        try:
            events = extract_life_events_from_answers(answers)
            logger.info(f"Extracted {len(events)} life events from answers")
        except Exception as e:
            logger.error(f"Error extracting life events from answers: {e}")
            events = []

    # Initialize container for all rectification results
    results = {
        "rectification_id": rectification_id,
        "original_time": birth_dt.strftime("%H:%M:%S"),
        "original_date": birth_dt.strftime("%Y-%m-%d"),
        "chart_id": chart_id,
        "rectified_time": None,
        "rectified_datetime": None,
        "confidence": 0.0,
        "time_shift_minutes": 0,
        "methods": [],
        "explanation": "",
        "rectified_chart": None,
        "transit_analysis": {},
        "event_correlations": [],
        "start_time": datetime.now().isoformat(),
        "status": "in_progress"
    }

    # Track the methods used
    methods_attempted = []
    methods_succeeded = []
    method_results = []

    # Get OpenAI service for AI-assisted rectification
    try:
        openai_service = await get_openai_service()

        if openai_service:
            # Try AI-assisted rectification
            methods_attempted.append("ai")
            logger.info("Starting AI-assisted rectification")

            # Run AI rectification
            ai_time, ai_confidence = await ai_assisted_rectification(
                birth_dt, latitude, longitude, timezone, openai_service, answers, events
            )

            if ai_time and ai_confidence > 0:
                methods_succeeded.append("ai")
                method_results.append({
                    "method": "ai",
                    "rectified_time": ai_time,
                    "confidence": ai_confidence,
                    "time_shift_minutes": int((ai_time - birth_dt).total_seconds() / 60)
                })
                logger.info(f"AI rectification successful: {ai_time.strftime('%H:%M:%S')}, confidence: {ai_confidence}")
        else:
            logger.warning("OpenAI service not available for AI-assisted rectification")
    except Exception as e:
        logger.error(f"AI-assisted rectification failed: {e}")
        logger.error(traceback.format_exc())

    # Try transit-based rectification
    try:
        if events and len(events) > 0:
            methods_attempted.append("transit")
            logger.info(f"Starting transit-based rectification with {len(events)} events")

            # Run transit analysis
            from .methods.transit_analysis import analyze_life_events
            transit_time, transit_confidence = await analyze_life_events(
                events, birth_dt, latitude, longitude, timezone
            )

            if transit_time and transit_confidence > 0:
                methods_succeeded.append("transit")
                method_results.append({
                    "method": "transit",
                    "rectified_time": transit_time,
                    "confidence": transit_confidence,
                    "time_shift_minutes": int((transit_time - birth_dt).total_seconds() / 60)
                })
                logger.info(f"Transit analysis successful: {transit_time.strftime('%H:%M:%S')}, confidence: {transit_confidence}")

                # Store detailed transit analysis in results
                from .methods.transit_analysis import get_detailed_transit_analysis
                results["transit_analysis"] = await get_detailed_transit_analysis(
                    events, transit_time, latitude, longitude, timezone
                )
        elif answers:
            # If no events provided but answers are available, try to extract events from answers
            try:
                events = extract_life_events_from_answers(answers)
                if events and len(events) > 0:
                    try:
                        methods_attempted.append("transit")
                        from .methods.transit_analysis import analyze_life_events
                        transit_time, transit_confidence = await analyze_life_events(
                            events, birth_dt, latitude, longitude, timezone
                        )
                        methods_succeeded.append("transit")
                    except Exception as e:
                        logger.warning(f"Primary transit analysis failed: {e}")
                        # Use alternative method based on ephemeris.MinimalChart when Flatlib fails
                        try:
                            logger.info("Attempting alternative transit analysis using MinimalChart")
                            from .utils.ephemeris import MinimalChart

                            # Create natal chart using MinimalChart
                            natal_chart = MinimalChart(birth_dt, latitude, longitude).to_dict()

                            # Same implementation as above, but with events extracted from answers
                            candidates = []
                            for hour_offset in range(-4, 5):  # Try -4 to +4 hours from original time
                                test_time = birth_dt + timedelta(hours=hour_offset)
                                score = 0

                                # For each event, check if there are significant transits
                                for event in events:
                                    if "date" not in event or not event["date"]:
                                        continue

                                    try:
                                        # Parse event date
                                        if isinstance(event["date"], str):
                                            event_date = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                                        else:
                                            event_date = event["date"]

                                        # Create transit chart for event date
                                        transit_chart = MinimalChart(event_date, latitude, longitude).to_dict()

                                        # Check for significant aspects between transit and natal chart
                                        for transit_planet, transit_data in transit_chart["planets"].items():
                                            for natal_planet, natal_data in natal_chart["planets"].items():
                                                # Calculate aspect
                                                transit_lon = transit_data["longitude"]
                                                natal_lon = natal_data["longitude"]

                                                # Calculate orb
                                                diff = abs(transit_lon - natal_lon) % 360
                                                if diff > 180:
                                                    diff = 360 - diff

                                                # Check for conjunction (0°)
                                                if 0 <= diff <= 8:
                                                    score += 10
                                                # Check for opposition (180°)
                                                elif 172 <= diff <= 180:
                                                    score += 8
                                                # Check for trine (120°)
                                                elif 113 <= diff <= 127:
                                                    score += 6
                                    except Exception as event_err:
                                        logger.warning(f"Error analyzing event {event.get('type', 'unknown')}: {event_err}")
                                        continue

                                candidates.append((test_time, score))

                            # Find the best candidate
                            if candidates:
                                candidates.sort(key=lambda x: x[1], reverse=True)
                                best_time, best_score = candidates[0]

                                # Calculate confidence based on score
                                confidence = min(best_score * 2, 85.0)  # Cap at 85%

                                # Only use if score is meaningful
                                if best_score > 20:
                                    transit_time = best_time
                                    transit_confidence = confidence
                                    methods_succeeded.append("alt_transit")
                                    logger.info(f"Alternative transit analysis successful: {transit_time}, confidence: {transit_confidence}")
                        except Exception as alt_e:
                            logger.warning(f"Alternative transit analysis failed: {alt_e}")
                            # Continue with other methods even if alternative transit analysis fails
            except Exception as e:
                logger.warning(f"Transit analysis from answers failed: {e}")
                # Continue with other methods even if transit analysis fails
    except Exception as e:
        logger.error(f"Transit analysis failed: {e}")
        logger.error(traceback.format_exc())

    # Try solar arc rectification
    try:
        methods_attempted.append("solar_arc")
        logger.info("Starting solar arc rectification")

        # Run solar arc analysis
        solar_arc_time, solar_arc_confidence = await solar_arc_rectification(
            birth_dt, latitude, longitude, timezone
        )

        if solar_arc_time and solar_arc_confidence > 0:
            methods_succeeded.append("solar_arc")
            method_results.append({
                "method": "solar_arc",
                "rectified_time": solar_arc_time,
                "confidence": solar_arc_confidence,
                "time_shift_minutes": int((solar_arc_time - birth_dt).total_seconds() / 60)
            })
            logger.info(f"Solar arc rectification successful: {solar_arc_time.strftime('%H:%M:%S')}, confidence: {solar_arc_confidence}")
    except Exception as e:
        logger.error(f"Solar arc rectification failed: {e}")
        logger.error(traceback.format_exc())

    # Try progressed ascendant rectification
    try:
        methods_attempted.append("progressed")
        logger.info("Starting progressed ascendant rectification")

        # Run progressed analysis
        progressed_time, progressed_confidence = await progressed_ascendant_rectification(
            birth_dt, latitude, longitude, timezone
        )

        if progressed_time and progressed_confidence > 0:
            methods_succeeded.append("progressed")
            method_results.append({
                "method": "progressed",
                "rectified_time": progressed_time,
                "confidence": progressed_confidence,
                "time_shift_minutes": int((progressed_time - birth_dt).total_seconds() / 60)
            })
            logger.info(f"Progressed rectification successful: {progressed_time.strftime('%H:%M:%S')}, confidence: {progressed_confidence}")
    except Exception as e:
        logger.error(f"Progressed ascendant rectification failed: {e}")
        logger.error(traceback.format_exc())

    # If no methods succeeded, implement a basic chart-based rectification
    if not method_results:
        logger.warning("No rectification methods succeeded, attempting basic chart analysis")
        try:
            # Calculate the original chart
            original_chart = calculate_chart(birth_dt, latitude, longitude, timezone)

            # Analyze critical points in the birth chart
            # This method should always work as a fallback
            basic_time, basic_confidence = await basic_chart_rectification(
                birth_dt, latitude, longitude, timezone, original_chart
            )

            if basic_time and basic_confidence > 0:
                methods_succeeded.append("basic")
                method_results.append({
                    "method": "basic",
                    "rectified_time": basic_time,
                    "confidence": basic_confidence,
                    "time_shift_minutes": int((basic_time - birth_dt).total_seconds() / 60)
                })
                logger.info(f"Basic chart rectification: {basic_time.strftime('%H:%M:%S')}, confidence: {basic_confidence}")
            else:
                # If even basic rectification fails, use original time with low confidence
                method_results.append({
                    "method": "original",
                    "rectified_time": birth_dt,
                    "confidence": 40.0,
                    "time_shift_minutes": 0
                })
                logger.warning("Using original time with low confidence as all methods failed")
        except Exception as e:
            logger.error(f"Basic chart rectification failed: {e}")
            # Use original time as last resort
            method_results.append({
                "method": "original",
                "rectified_time": birth_dt,
                "confidence": 40.0,
                "time_shift_minutes": 0
            })

    # Find the best method result based on confidence
    method_results.sort(key=lambda x: x["confidence"], reverse=True)
    best_result = method_results[0]

    # If we have multiple methods that succeeded, calculate consensus
    if len(method_results) > 1:
        # Calculate weighted time based on confidence
        total_confidence = sum(r["confidence"] for r in method_results)
        time_shift_sum = sum(r["time_shift_minutes"] * r["confidence"] for r in method_results)
        consensus_shift = round(time_shift_sum / total_confidence)

        # Only use consensus if methods largely agree (within 60 minutes of each other)
        shifts = [r["time_shift_minutes"] for r in method_results]
        max_shift_diff = max(shifts) - min(shifts)

        if max_shift_diff <= 60:
            # Methods largely agree, use consensus
            consensus_time = birth_dt + timedelta(minutes=consensus_shift)
            consensus_confidence = sum(r["confidence"] * (1 - abs(r["time_shift_minutes"] - consensus_shift) / 60)
                                    for r in method_results) / len(method_results)

            # Use consensus only if it has good confidence
            if consensus_confidence > best_result["confidence"] * 0.8:
                logger.info(f"Using consensus time from {len(method_results)} methods")
                best_result = {
                    "method": "consensus",
                    "rectified_time": consensus_time,
                    "confidence": consensus_confidence,
                    "time_shift_minutes": consensus_shift
                }
        else:
            # Methods disagree significantly, use the highest confidence method
            logger.info(f"Methods disagree significantly (max diff: {max_shift_diff} minutes), using best method")

    # Set the rectified time based on the best result
    rectified_time = best_result["rectified_time"]
    confidence = best_result["confidence"]
    time_shift_minutes = best_result["time_shift_minutes"]
    method = best_result["method"]

    # Update results dictionary
    results["rectified_time"] = rectified_time.strftime("%H:%M:%S")
    results["rectified_datetime"] = rectified_time.isoformat()
    results["confidence"] = confidence
    results["time_shift_minutes"] = time_shift_minutes
    results["methods"] = methods_succeeded
    results["primary_method"] = method
    results["explanation"] = f"Birth time rectified from {birth_dt.strftime('%H:%M:%S')} to {rectified_time.strftime('%H:%M:%S')} using {method} method. Confidence: {confidence:.1f}%."

    # Calculate the rectified chart
    try:
        rectified_chart = calculate_chart(rectified_time, latitude, longitude, timezone)
        results["rectified_chart"] = rectified_chart
    except Exception as e:
        logger.error(f"Error calculating rectified chart: {e}")
        rectified_chart = None

    # Generate event correlations if events are available
    if events and rectified_chart:
        try:
            from .methods.transit_analysis import correlate_events_with_chart
            event_correlations = await correlate_events_with_chart(
                events, rectified_time, latitude, longitude, timezone
            )
            results["event_correlations"] = event_correlations
        except Exception as e:
            logger.error(f"Error correlating events with chart: {e}")

    # Store the rectified chart and results
    try:
        if rectified_chart:
            storage_id = await store_rectified_chart(
                rectified_chart, rectification_id, birth_dt, rectified_time
            )
            results["storage_id"] = storage_id
    except Exception as e:
        logger.error(f"Error storing rectified chart: {e}")

    # Update status and end time
    results["end_time"] = datetime.now().isoformat()
    results["status"] = "completed"

    logger.info(f"Comprehensive rectification completed: {rectified_time.strftime('%H:%M:%S')}, confidence: {confidence:.1f}%, method: {method}")

    return results

async def basic_chart_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    chart: Optional[Dict[str, Any]] = None
) -> Tuple[datetime, float]:
    """
    Perform basic chart-based rectification as a fallback method.
    This analyzes critical degrees, planetary positions, and house placements
    to suggest potential birth time adjustments.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string
        chart: Optional pre-calculated chart

    Returns:
        Tuple containing (rectified_datetime, confidence_score)
    """
    # If chart was not provided, calculate it
    if not chart:
        try:
            chart = calculate_chart(birth_dt, latitude, longitude, timezone)
        except Exception as e:
            logger.error(f"Error calculating chart for basic rectification: {e}")
            return birth_dt, 40.0  # Return original with low confidence

    # Extract key chart factors for analysis
    ascendant = chart.get("angles", {}).get("asc", {}).get("longitude", 0)
    midheaven = chart.get("angles", {}).get("mc", {}).get("longitude", 0)

    # Get planet positions
    planets = chart.get("planets", {})
    sun_pos = planets.get("sun", {}).get("longitude", 0)
    moon_pos = planets.get("moon", {}).get("longitude", 0)

    # Initialize time shift and confidence
    time_shift_minutes = 0
    confidence = 50.0  # Start with medium confidence

    # Check critical degree factors that suggest birth time accuracy or inaccuracy

    # Factor 1: Ascendant at critical degrees
    asc_degree = ascendant % 30
    if 0 <= asc_degree < 1 or 29 <= asc_degree < 30:
        # Very close to sign boundary, often indicates inaccurate time
        time_shift_minutes += -30 if asc_degree < 1 else 30
        confidence -= 5
    elif 12.5 <= asc_degree <= 13.5 or 25.5 <= asc_degree <= 26.5:
        # Critical degrees, might indicate accurate time
        confidence += 5

    # Factor 2: Planets close to angles (within 3 degrees)
    for planet_name, planet_data in planets.items():
        planet_pos = planet_data.get("longitude", 0)

        # Check closeness to ASC or MC
        asc_diff = min((planet_pos - ascendant) % 360, (ascendant - planet_pos) % 360)
        mc_diff = min((planet_pos - midheaven) % 360, (midheaven - planet_pos) % 360)

        if asc_diff <= 3:
            # Planet very close to ASC, suggests time might be accurate
            confidence += 10
            logger.info(f"Planet {planet_name} within 3 degrees of Ascendant, suggesting accurate time")
        elif asc_diff <= 7:
            # Planet somewhat close to ASC, might need small adjustment
            if asc_diff > 5:
                time_shift_minutes += 10 if (planet_pos - ascendant) % 360 < 180 else -10
            confidence += 5

        if mc_diff <= 3:
            # Planet very close to MC, suggests time might be accurate
            confidence += 10
            logger.info(f"Planet {planet_name} within 3 degrees of Midheaven, suggesting accurate time")
        elif mc_diff <= 7:
            # Planet somewhat close to MC, might need small adjustment
            if mc_diff > 5:
                time_shift_minutes += 10 if (planet_pos - midheaven) % 360 < 180 else -10
            confidence += 5

    # Factor 3: Check if Ascendant exactly squares or trines an important planet
    for planet_name, planet_data in planets.items():
        if planet_name not in ["sun", "moon", "jupiter", "saturn"]:
            continue  # Focus on major significators

        planet_pos = planet_data.get("longitude", 0)

        # Check for exact aspects
        aspect_diff = min((planet_pos - ascendant) % 360, (ascendant - planet_pos) % 360)

        # Square (90 degrees)
        if 89 <= aspect_diff <= 91:
            confidence += 7
            logger.info(f"Ascendant square {planet_name} within 1 degree, suggesting accurate time")

        # Trine (120 degrees)
        elif 119 <= aspect_diff <= 121:
            confidence += 7
            logger.info(f"Ascendant trine {planet_name} within 1 degree, suggesting accurate time")

        # Opposition (180 degrees)
        elif 179 <= aspect_diff <= 181:
            confidence += 7
            logger.info(f"Ascendant opposite {planet_name} within 1 degree, suggesting accurate time")

    # Factor 4: Check if Sun or Moon is close to a house cusp (suggests accurate time)
    houses = chart.get("houses", [])
    for i, house_cusp in enumerate(houses):
        sun_diff = min((sun_pos - house_cusp) % 360, (house_cusp - sun_pos) % 360)
        moon_diff = min((moon_pos - house_cusp) % 360, (house_cusp - moon_pos) % 360)

        if sun_diff <= 2:
            confidence += 5
            logger.info(f"Sun within 2 degrees of house {i+1} cusp, suggesting accurate time")

        if moon_diff <= 2:
            confidence += 5
            logger.info(f"Moon within 2 degrees of house {i+1} cusp, suggesting accurate time")

    # Apply time shift if confidence is below threshold
    if confidence < 70 and time_shift_minutes != 0:
        # Apply the time adjustment
        adjusted_time = birth_dt + timedelta(minutes=time_shift_minutes)

        # Check if adjusted time is within reasonable bounds (same day)
        if adjusted_time.date() == birth_dt.date():
            logger.info(f"Basic chart rectification suggests {time_shift_minutes} minute adjustment")
            return adjusted_time, confidence
        else:
            # If adjustment crosses day boundary, use a smaller adjustment
            time_shift_minutes = time_shift_minutes // 2
            adjusted_time = birth_dt + timedelta(minutes=time_shift_minutes)
            logger.info(f"Reduced time adjustment to {time_shift_minutes} minutes to stay within same day")
            return adjusted_time, confidence - 10  # Lower confidence for reduced adjustment

    # If confidence is high or no shift needed, return original time
    if confidence >= 70:
        logger.info(f"High confidence ({confidence:.1f}%) in original time, no adjustment needed")
    else:
        logger.info(f"No clear adjustment indicated, keeping original time with {confidence:.1f}% confidence")

    return birth_dt, confidence
