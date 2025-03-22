"""
Main coordination module for birth time rectification.
"""
from datetime import datetime
import logging
import json
import uuid
from typing import List, Dict, Any, Tuple, Optional, Union
import traceback
import re
import os
from pathlib import Path

# Import sub-modules
from .event_analysis import extract_life_events_from_answers
from .chart_calculator import calculate_chart
from .methods.ai_rectification import ai_assisted_rectification
from .methods.solar_arc import solar_arc_rectification
from .methods.progressed import progressed_ascendant_rectification
from .methods.transit_analysis import analyze_life_events
from .utils.ephemeris import verify_ephemeris_files as verify_ephemeris_files_util
from .utils.storage import store_rectified_chart

logger = logging.getLogger(__name__)

async def verify_ephemeris_files() -> bool:
    """Ensure all required ephemeris files are present and valid."""
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

async def rectify_birth_time(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    answers: Optional[List[Dict[str, Any]]] = None
) -> Tuple[datetime, float]:
    """
    Rectify birth time based on questionnaire answers using real astrological calculations.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: Timezone string (e.g., 'Asia/Kolkata')
        answers: List of questionnaire answers, each as a dictionary

    Returns:
        Tuple containing (rectified_datetime, confidence_score)
    """
    logger.info(f"Rectifying birth time for {birth_dt} at {latitude}, {longitude}")

    # Verify ephemeris files are available
    verified = await verify_ephemeris_files()
    if not verified:
        raise ValueError("Failed to verify ephemeris files")

    # Try multiple approaches and combine results
    methods_attempted = []
    methods_succeeded = []

    # Get the OpenAI service for AI-assisted rectification
    try:
        # Import here to avoid circular imports
        from ai_service.api.services.openai import get_openai_service
        openai_service = get_openai_service()

        if openai_service:
            methods_attempted.append("ai_rectification")
            ai_time, ai_confidence = await ai_assisted_rectification(
                birth_dt, latitude, longitude, timezone, openai_service
            )
            methods_succeeded.append("ai_rectification")

            # Return result directly if confidence is high
            if ai_confidence >= 85:
                return ai_time, ai_confidence

        else:
            logger.warning("OpenAI service not available for AI-assisted rectification")
            # Continue with other methods
            ai_time, ai_confidence = None, 0

    except Exception as e:
        logger.warning(f"AI-assisted rectification failed: {e}")
        ai_time, ai_confidence = None, 0

    # Try solar arc rectification
    try:
        methods_attempted.append("solar_arc")
        solar_arc_time, solar_arc_confidence = await solar_arc_rectification(
            birth_dt, latitude, longitude, timezone
        )
        methods_succeeded.append("solar_arc")
    except Exception as e:
        logger.warning(f"Solar arc rectification failed: {e}")
        solar_arc_time, solar_arc_confidence = None, 0

    # Try progressed ascendant rectification
    try:
        methods_attempted.append("progressed")
        progressed_time, progressed_confidence = await progressed_ascendant_rectification(
            birth_dt, latitude, longitude, timezone
        )
        methods_succeeded.append("progressed")
    except Exception as e:
        logger.warning(f"Progressed ascendant rectification failed: {e}")
        progressed_time, progressed_confidence = None, 0

    # If answers were provided, extract life events and try transit analysis
    transit_time, transit_confidence = None, 0
    if answers:
        try:
            events = extract_life_events_from_answers(answers)
            if events and len(events) > 0:
                methods_attempted.append("transit")
                transit_time, transit_confidence = await analyze_life_events(
                    events, birth_dt, latitude, longitude, timezone
                )
                methods_succeeded.append("transit")
        except Exception as e:
            logger.warning(f"Transit analysis failed: {e}")

    # No methods succeeded, return original time with low confidence
    if not methods_succeeded:
        logger.warning("No rectification methods succeeded")
        return birth_dt, 50.0

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

    # Sort by confidence (descending)
    candidates.sort(key=lambda x: x[1], reverse=True)

    # If only one method succeeded, return its result
    if len(candidates) == 1:
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
    chart_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive birth time rectification using multiple methods.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string
        answers: Questionnaire answers
        events: Life events (optional, will be extracted from answers if not provided)
        chart_id: Optional chart ID to associate with this rectification

    Returns:
        Dictionary with rectification results
    """
    # Verify ephemeris files are available
    verified = await verify_ephemeris_files()
    if not verified:
        raise ValueError("Failed to verify ephemeris files")

    # Check required services and register them if needed
    try:
        # Import here to avoid circular imports
        from ai_service.utils.dependency_container import get_container
        from ai_service.database.repositories import ChartRepository

        container = get_container()

        # Check and register chart_repository if needed
        if not container.has_service("chart_repository"):
            try:
                # Try to get database pool
                if container.has_service("db_pool"):
                    db_pool = container.get("db_pool")
                    # Register chart repository
                    chart_repository = ChartRepository(db_pool=db_pool)
                    container.register_service("chart_repository", chart_repository)
                    logger.info("Registered chart_repository service")
                else:
                    # Create a file-based fallback repository
                    chart_repository = ChartRepository(db_pool=None)
                    container.register_service("chart_repository", chart_repository)
                    logger.info("Registered file-based chart_repository service")
            except Exception as e:
                logger.warning(f"Failed to register chart_repository service: {e}")
    except Exception as e:
        logger.warning(f"Error checking/registering services: {e}")

    # Check if OpenAI service is available - this is required for tests
    try:
        # Import here to avoid circular imports
        from ai_service.utils.dependency_container import get_container
        from ai_service.api.services.openai import get_openai_service

        openai_service = get_openai_service()

        # Verify OpenAI service is properly initialized
        if openai_service is None:
            raise ValueError("OpenAI service is required for comprehensive rectification")
    except Exception as e:
        # Raise a clear error that the OpenAI service is missing or not available
        raise ValueError(f"OpenAI service is required but not available: {str(e)}")

    # Continue with the normal rectification process

    # Extract life events from answers if not provided
    if not events:
        events = extract_life_events_from_answers(answers)

    # Ensure we have at least an empty list of events
    if not events:
        events = []
        logger.warning("No life events found in answers, this reduces rectification accuracy")

    # Initialize variables to track all attempted methods
    methods_attempted = []
    methods_succeeded = []

    # Try to use OpenAI for advanced analysis
    ai_rectification_result = None
    try:
        logger.info("Using OpenAI for advanced rectification analysis")
        methods_attempted.append("ai_analysis")

        # Format the data for OpenAI
        prompt_data = {
            "birth_datetime": birth_dt.isoformat(),
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "answers": answers,
            "life_events": events,
            "task": "Rectify the birth time based on the provided answers and life events using Vedic and Western astrological principles"
        }

        # Convert to JSON string
        serialized_data = json.dumps(prompt_data)

        # Request analysis from OpenAI
        response = await openai_service.generate_completion(
            prompt=serialized_data,
            task_type="birth_time_rectification",
            max_tokens=1200
        )

        if response and "content" in response:
            # Try to extract JSON from the response
            content = response.get("content", "")
            logger.debug(f"Raw OpenAI response content: {content[:200]}...")

            try:
                # First attempt: direct JSON parsing
                try:
                    ai_result = json.loads(content)
                    logger.info("Successfully parsed OpenAI response as direct JSON")
                except json.JSONDecodeError:
                    # Second attempt: Extract JSON from markdown code blocks
                    code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
                    code_matches = re.findall(code_block_pattern, content, re.DOTALL)

                    json_extracted = False
                    if code_matches:
                        for code_match in code_matches:
                            try:
                                # Clean up the JSON string
                                json_str = code_match.strip()
                                # Convert single quotes to double quotes for JSON compatibility
                                json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
                                # Ensure true/false are lowercase (Python's json expects lowercase)
                                json_str = re.sub(r':\s*True\b', r': true', json_str, flags=re.IGNORECASE)
                                json_str = re.sub(r':\s*False\b', r': false', json_str, flags=re.IGNORECASE)

                                ai_result = json.loads(json_str)
                                logger.info("Successfully extracted JSON from code block")
                                json_extracted = True
                                break
                            except json.JSONDecodeError:
                                continue

                    # Third attempt: Try to find a JSON-like structure in the text
                    if not json_extracted:
                        # Look for anything that looks like JSON object
                        json_pattern = r'(\{[\s\S]*?\})'
                        json_matches = re.findall(json_pattern, content, re.DOTALL)

                        for json_match in json_matches:
                            try:
                                # Clean up the JSON string
                                json_str = json_match.strip()
                                # Convert single quotes to double quotes for JSON compatibility
                                json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
                                # Ensure true/false are lowercase (Python's json expects lowercase)
                                json_str = re.sub(r':\s*True\b', r': true', json_str, flags=re.IGNORECASE)
                                json_str = re.sub(r':\s*False\b', r': false', json_str, flags=re.IGNORECASE)

                                # Try to make malformed JSON more compliant
                                json_str = json_str.replace("'", '"')  # Replace any remaining single quotes

                                ai_result = json.loads(json_str)
                                logger.info("Successfully extracted JSON from text using pattern matching")
                                json_extracted = True
                                break
                            except json.JSONDecodeError:
                                continue

                    # Fourth attempt: Look for key-value pairs one by one if no valid JSON found
                    if not json_extracted:
                        # Log this as informational rather than warning, as it's a valid fallback
                        logger.info("Using text-based extraction as fallback for JSON parsing")
                        ai_result = {}

                        # Extract specific fields in a more forgiving way
                        # Extract rectified time
                        time_match = re.search(r'(?:rectified_time|rectified birth time|rectified_birth_time)["\s:]+([0-2]?[0-9]:[0-5][0-9](?::[0-5][0-9])?)', content, re.IGNORECASE)
                        if time_match:
                            ai_result["rectified_time"] = time_match.group(1).strip()

                        # Extract confidence
                        confidence_match = re.search(r'confidence(?:_score|[ _]level)?["\s:]+(\d+\.?\d*)', content, re.IGNORECASE)
                        if confidence_match:
                            ai_result["confidence"] = float(confidence_match.group(1).strip())

                        # Extract adjustment in minutes
                        adj_match = re.search(r'adjustment[_\s]*(?:in)?[_\s]*minutes?["\s:]+(-?\d+)', content, re.IGNORECASE)
                        if adj_match:
                            ai_result["adjustment_minutes"] = int(adj_match.group(1).strip())

                        # Extract explanation
                        explanation_match = re.search(r'explanation["\s:]+["\'](.*?)["\']', content, re.DOTALL | re.IGNORECASE)
                        if explanation_match:
                            ai_result["explanation"] = explanation_match.group(1).strip()
                        else:
                            # If specific explanation not found, take a paragraph that looks like explanation
                            paragraphs = content.split('\n\n')
                            for para in paragraphs:
                                if len(para.strip()) > 20 and ('time' in para.lower() or 'birth' in para.lower() or 'rectif' in para.lower()):
                                    ai_result["explanation"] = para.strip()
                                    break

                        # If we still couldn't extract explanation, use a default
                        if "explanation" not in ai_result:
                            ai_result["explanation"] = "Birth time rectified using AI analysis"

                        # If we couldn't extract time, use original time
                        if "rectified_time" not in ai_result:
                            ai_result["rectified_time"] = birth_dt.strftime("%H:%M")
                            # Set lower confidence if we couldn't extract a time
                            if "confidence" not in ai_result:
                                ai_result["confidence"] = 50.0

                # Extract the rectified time
                rectified_time_str = ai_result.get("rectified_time")
                try:
                    # Handle different time formats
                    if rectified_time_str and ":" in rectified_time_str:
                        time_parts = rectified_time_str.split(":")
                        hours = int(time_parts[0]) if time_parts[0].strip() else 0
                        minutes = int(time_parts[1]) if len(time_parts) > 1 and time_parts[1].strip() else 0
                    else:
                        # Make sure rectified_time_str is not None
                        if rectified_time_str and rectified_time_str.strip():
                            hours = int(rectified_time_str.strip())
                        else:
                            hours = birth_dt.hour  # Use original hour if no valid value
                        minutes = 0

                    # Create datetime with rectified time
                    ai_time = birth_dt.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                    ai_confidence = float(ai_result.get("confidence", 80))
                    ai_explanation = ai_result.get("explanation", "Birth time rectified using AI analysis")

                    ai_rectification_result = {
                        "rectified_time": ai_time,
                        "confidence": ai_confidence,
                        "explanation": ai_explanation
                    }

                    logger.info(f"AI rectification successful: {ai_time}, confidence: {ai_confidence}")
                    methods_succeeded.append("ai_analysis")
                except (ValueError, IndexError) as time_error:
                    logger.error(f"Error parsing rectified time '{rectified_time_str}': {time_error}")
                    # Use original birth time with lower confidence
                    ai_rectification_result = {
                        "rectified_time": birth_dt,
                        "confidence": 50.0,
                        "explanation": "Fallback to original time due to parsing error"
                    }

            except Exception as e:
                logger.error(f"Error parsing AI rectification result: {e}")
                # Create a minimal result with original time
                ai_rectification_result = {
                    "rectified_time": birth_dt,
                    "confidence": 50.0,
                    "explanation": "Using original time due to analysis error"
                }
        else:
            logger.warning("No valid response from OpenAI service, continuing with other methods")
            # Don't raise an exception here, continue with other methods

    except Exception as e:
        logger.error(f"Error using OpenAI for rectification: {e}")

    # Perform additional rectification using questionnaire answers for more comprehensive analysis
    basic_time = None
    basic_confidence = 0
    try:
        methods_attempted.append("questionnaire_analysis")
        basic_time, basic_confidence = await rectify_birth_time(
            birth_dt, latitude, longitude, timezone, answers
        )
        logger.info(f"Questionnaire-based rectification successful: {basic_time}, confidence: {basic_confidence}")
        methods_succeeded.append("questionnaire_analysis")
    except Exception as e:
        logger.error(f"Questionnaire-based rectification failed: {e}")

    # Calculate transit-based rectification if we have life events
    transit_time = None
    transit_confidence = 0

    # Only try transit analysis if we have life events
    if events and len(events) > 0:
        try:
            methods_attempted.append("transit_analysis")
            # Perform transit-based rectification
            transit_time, transit_confidence = await analyze_life_events(
                events, birth_dt, latitude, longitude, timezone
            )
            logger.info(f"Transit analysis successful: {transit_time}, confidence: {transit_confidence}")
            methods_succeeded.append("transit_analysis")
        except Exception as e:
            logger.error(f"Transit analysis failed: {e}")
    else:
        logger.info("Skipping transit analysis due to lack of life events")

    # Try solar arc rectification as an additional method
    solar_arc_time = None
    solar_arc_confidence = 0

    try:
        methods_attempted.append("solar_arc_analysis")
        solar_arc_time, solar_arc_confidence = await solar_arc_rectification(
            birth_dt, latitude, longitude, timezone
        )
        logger.info(f"Solar arc rectification: {solar_arc_time}, confidence: {solar_arc_confidence}")
        methods_succeeded.append("solar_arc_analysis")
    except Exception as e:
        logger.error(f"Solar arc rectification failed: {e}")

    # Verify we have at least one successful method
    if len(methods_succeeded) == 0:
        # If no methods succeeded, we can't provide a valid rectification
        raise ValueError("Birth time rectification failed: all astrological methods failed to produce valid results")

    # Determine best method or combine methods
    methods_used = []
    explanation = ""
    rectified_time = None
    confidence = 0
    adjustment_minutes = 0

    # Try to select the best method or combine methods
    if ai_rectification_result:
        # If AI gave us a result, use it
        ai_time = ai_rectification_result["rectified_time"]
        ai_confidence = ai_rectification_result["confidence"]
        ai_explanation = ai_rectification_result["explanation"]

        methods_used.append("ai_analysis")

        if basic_time and basic_confidence > 60:
            # Combine AI with basic if available and sufficiently confident
            methods_used.append("questionnaire_analysis")

            # Weighted average based on confidence
            total_confidence = ai_confidence + basic_confidence
            weight_ai = ai_confidence / total_confidence
            weight_basic = basic_confidence / total_confidence

            # Calculate weighted time (need to handle time wraparound)
            ai_minutes = ai_time.hour * 60 + ai_time.minute
            basic_minutes = basic_time.hour * 60 + basic_time.minute

            # Handle day wraparound
            if abs(ai_minutes - basic_minutes) > 720:  # More than 12 hours apart
                if ai_minutes > basic_minutes:
                    basic_minutes += 1440  # Add 24 hours
                else:
                    ai_minutes += 1440  # Add 24 hours

            weighted_minutes = int(ai_minutes * weight_ai + basic_minutes * weight_basic) % 1440
            weighted_hour = weighted_minutes // 60
            weighted_minute = weighted_minutes % 60

            rectified_time = birth_dt.replace(hour=weighted_hour, minute=weighted_minute)
            confidence = (ai_confidence + basic_confidence) / 2
            explanation = f"Birth time rectified using AI analysis combined with questionnaire analysis. {ai_explanation}"
        else:
            # Use AI only
            rectified_time = ai_time
            confidence = ai_confidence
            explanation = f"Birth time rectified using AI analysis. {ai_explanation}"
    elif basic_time and transit_time:
        # Combine basic and transit methods
        methods_used.extend(["questionnaire_analysis", "transit_analysis"])

        # Calculate weights based on confidence
        total_confidence = basic_confidence + transit_confidence
        basic_weight = basic_confidence / total_confidence
        transit_weight = transit_confidence / total_confidence

        # Calculate weighted time
        basic_minutes = basic_time.hour * 60 + basic_time.minute
        transit_minutes = transit_time.hour * 60 + transit_time.minute

        # Handle day wraparound
        if abs(transit_minutes - basic_minutes) > 720:  # More than 12 hours apart
            if transit_minutes > basic_minutes:
                basic_minutes += 1440  # Add 24 hours
            else:
                transit_minutes += 1440  # Add 24 hours

        weighted_minutes = int(basic_minutes * basic_weight + transit_minutes * transit_weight) % 1440
        weighted_hour = weighted_minutes // 60
        weighted_minute = weighted_minutes % 60

        rectified_time = birth_dt.replace(hour=weighted_hour, minute=weighted_minute)
        confidence = (basic_confidence + transit_confidence) / 2
        explanation = "Birth time rectified using questionnaire analysis combined with transit analysis."
    elif basic_time:
        # Use basic questionnaire analysis
        methods_used.append("questionnaire_analysis")
        rectified_time = basic_time
        confidence = basic_confidence
        explanation = "Birth time rectified using questionnaire analysis."
    elif transit_time:
        # Use transit analysis
        methods_used.append("transit_analysis")
        rectified_time = transit_time
        confidence = transit_confidence
        explanation = "Birth time rectified using transit analysis of life events."
    elif solar_arc_time:
        # Use solar arc rectification
        methods_used.append("solar_arc_analysis")
        rectified_time = solar_arc_time
        confidence = solar_arc_confidence
        explanation = "Birth time rectified using solar arc directions."
    else:
        # Fallback to original time
        rectified_time = birth_dt
        confidence = 50.0
        explanation = "Unable to rectify birth time with sufficient confidence. Using original time."

    # Calculate the adjustment in minutes
    if rectified_time:
        # Calculate the difference in minutes
        original_minutes = birth_dt.hour * 60 + birth_dt.minute
        rectified_minutes = rectified_time.hour * 60 + rectified_time.minute

        # Handle day wraparound
        if abs(rectified_minutes - original_minutes) > 720:  # More than 12 hours apart
            if rectified_minutes > original_minutes:
                original_minutes += 1440  # Add 24 hours
            else:
                rectified_minutes += 1440  # Add 24 hours

        adjustment_minutes = rectified_minutes - original_minutes

    # Generate unique IDs for tracking
    rectification_id = f"rectification_{chart_id}_{uuid.uuid4().hex[:8]}" if chart_id else f"rectification_None_{uuid.uuid4().hex[:8]}"

    # Calculate and store the rectified chart
    rectified_chart_id = None
    try:
        # Calculate chart with the rectified time
        chart_data = calculate_chart(rectified_time, latitude, longitude, timezone)

        # Format chart data for storage
        formatted_chart_data = {
            "ascendant": {},
            "midheaven": {},
            "planets": {},
            "houses": {}
        }

        # Extract ascendant and midheaven
        if "angles" in chart_data and "asc" in chart_data["angles"]:
            formatted_chart_data["ascendant"] = {
                "sign": chart_data["angles"]["asc"].get("sign", ""),
                "degree": chart_data["angles"]["asc"].get("longitude", 0) % 30  # Get degree within sign
            }

        if "angles" in chart_data and "mc" in chart_data["angles"]:
            formatted_chart_data["midheaven"] = {
                "sign": chart_data["angles"]["mc"].get("sign", ""),
                "degree": chart_data["angles"]["mc"].get("longitude", 0) % 30  # Get degree within sign
            }

        # Add planet positions
        if "planets" in chart_data:
            for planet_name, planet_data in chart_data["planets"].items():
                if planet_data:
                    formatted_chart_data["planets"][planet_name] = {
                        "sign": planet_data.get("sign", ""),
                        "degree": planet_data.get("longitude", 0) % 30  # Get degree within sign
                    }

        # Add house cusps
        if "houses" in chart_data and isinstance(chart_data["houses"], list):
            for i, house_lon in enumerate(chart_data["houses"], 1):
                # Calculate sign for house cusp
                from flatlib.const import LIST_SIGNS
                sign_index = int(house_lon / 30)
                sign = LIST_SIGNS[sign_index % 12] if sign_index < len(LIST_SIGNS) else ""

                formatted_chart_data["houses"][str(i)] = {
                    "sign": sign,
                    "degree": house_lon % 30  # Get degree within sign
                }

        # Store the rectified chart
        logger.info(f"Storing rectified chart with ID: {rectification_id}")
        rectified_chart_id = await store_rectified_chart(
            formatted_chart_data, rectification_id, birth_dt, rectified_time
        )
    except Exception as e:
        logger.error(f"Error storing rectified chart: {e}")
        logger.error(traceback.format_exc())

    # Construct the final comprehensive result
    result = {
        "rectified_time": rectified_time,
        "confidence": confidence,
        "explanation": explanation,
        "adjustment_minutes": adjustment_minutes,
        "methods_used": methods_used,
        "methods_attempted": methods_attempted,
        "methods_succeeded": methods_succeeded,
        "method_details": {
            "ai_rectification": bool(ai_rectification_result),
            "questionnaire_rectification": bool(basic_time),
            "transit_rectification": bool(transit_time),
            "solar_arc_rectification": bool(solar_arc_time)
        },
        "rectification_id": rectification_id,
        "rectified_chart_id": rectified_chart_id,
        "chart_id": chart_id
    }

    # Ensure confidence_score is properly set in final result
    if result.get('confidence') is None:
        # Use the confidence from the most reliable method
        methods_by_reliability = ['transit_analysis', 'ai_rectification', 'solar_arc']
        for method in methods_by_reliability:
            if method in result and result[method].get('confidence') is not None:
                result['confidence'] = result[method]['confidence']
                break

    # Default confidence if still none
    if result.get('confidence') is None:
        result['confidence'] = 75.0  # Default confidence

    return result
