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
        logger.error(f"Failed to verify ephemeris files: {e}")
        raise

    # Try multiple approaches and combine results
    methods_attempted = []

    # Method 1: Questionnaire-based rectification
    if answers and len(answers) >= 3:
        logger.info("Attempting questionnaire-based rectification")
        try:
            # Extract questionnaire answers for rectification
            questionnaire_results = await questionnaire_based_rectification(
                birth_dt, latitude, longitude, timezone, answers, use_openai
            )

            if questionnaire_results:
                quest_time, quest_conf = questionnaire_results
                methods_attempted.append(("questionnaire", quest_time, quest_conf))
                logger.info(f"Questionnaire rectification: {quest_time.strftime('%H:%M:%S')}, confidence: {quest_conf}")
        except Exception as e:
            logger.error(f"Questionnaire-based rectification failed: {e}")
            raise

    # Method 2: Chart analysis with astrological factors
    logger.info("Attempting chart-based rectification")
    try:
        chart_results = await chart_based_rectification(
            birth_dt, latitude, longitude, timezone, use_openai
        )

        if chart_results:
            chart_time, chart_conf = chart_results
            methods_attempted.append(("chart", chart_time, chart_conf))
            logger.info(f"Chart-based rectification: {chart_time.strftime('%H:%M:%S')}, confidence: {chart_conf}")
    except Exception as e:
        logger.error(f"Chart-based rectification failed: {e}")
        raise

    # Evaluate results and return the most confident prediction
    if not methods_attempted:
        raise ValueError("All rectification methods failed")

    # Sort by confidence score and get the highest
    methods_attempted.sort(key=lambda x: x[2], reverse=True)
    best_method, best_time, best_confidence = methods_attempted[0]

    logger.info(f"Best rectification method: {best_method} with confidence {best_confidence}")
    logger.info(f"Original time: {birth_dt.strftime('%H:%M:%S')}, Rectified: {best_time.strftime('%H:%M:%S')}")

    # Return the results
    return best_time, best_confidence

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
            - include_details: Whether to include detailed analysis (default: False)
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
    include_details = options.get("include_details", False)
    reporting_callback = options.get("reporting_callback", None)

    # Verify ephemeris files are available and generate a unique rectification ID
    rectification_id = f"rect_{uuid.uuid4().hex[:10]}"
    try:
        verified = await verify_ephemeris_files()
        if not verified:
            raise ValueError("Swiss Ephemeris files not available for rectification")
    except Exception as e:
        logger.error(f"Ephemeris verification failed: {e}")
        raise

    # Calculate original chart
    logger.info(f"Calculating original chart for {birth_dt}")
    original_chart = calculate_chart(birth_dt, latitude, longitude, timezone)

    # Initialize results
    method_results = []
    methods_succeeded = []

    # Report progress if callback provided
    if reporting_callback:
        await reporting_callback({"status": "calculating", "step": "original_chart"})

    # Execute primary rectification method
    rectified_time, confidence = await rectify_birth_time(
        birth_dt=birth_dt,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        answers=answers,
        options={"use_openai": use_openai, "max_retries": max_retries}
    )

    # Add to successful methods
    method_results.append({
        "method": "primary",
        "rectified_time": rectified_time,
        "confidence": confidence,
        "time_shift_minutes": int((rectified_time - birth_dt).total_seconds() / 60)
    })
    methods_succeeded.append("primary")

    logger.info(f"Primary rectification complete: {rectified_time}, confidence: {confidence}")

    # Report progress if callback provided
    if reporting_callback:
        await reporting_callback({
            "status": "complete",
            "step": "rectification",
            "rectified_time": rectified_time.isoformat(),
            "confidence": confidence
        })

    # Calculate rectified chart
    logger.info(f"Calculating rectified chart for {rectified_time}")
    rectified_chart = calculate_chart(rectified_time, latitude, longitude, timezone)

    # Generate explanation of the rectification
    explanation = await generate_rectification_explanation(
        original_time=birth_dt,
        rectified_time=rectified_time,
        original_chart=original_chart,
        rectified_chart=rectified_chart,
        confidence=confidence,
        use_openai=use_openai
    )

    # Prepare result
    result = {
        "rectification_id": rectification_id,
        "chart_id": chart_id,
        "status": "success",
        "original_time": birth_dt.isoformat(),
        "rectified_time": rectified_time.isoformat(),
        "confidence_score": confidence,
        "explanation": explanation,
        "original_chart": original_chart,
        "rectified_chart": rectified_chart,
        "method_results": method_results,
        "methods_succeeded": methods_succeeded
    }

    # Include detailed analysis if requested
    if include_details:
        details = await generate_detailed_analysis(
            original_chart=original_chart,
            rectified_chart=rectified_chart,
            original_time=birth_dt,
            rectified_time=rectified_time
        )
        result["details"] = details

    logger.info(f"Comprehensive rectification complete with confidence: {confidence}")
    return result

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

async def questionnaire_based_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    answers: List[Dict[str, Any]],
    use_openai: bool = True
) -> Optional[Tuple[datetime, float]]:
    """
    Rectify birth time based on questionnaire answers.

    Args:
        birth_dt: Birth date and time
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string
        answers: Questionnaire answers
        use_openai: Whether to use OpenAI for analysis

    Returns:
        Tuple of (rectified datetime, confidence score) or None if failed
    """
    if not answers or len(answers) < 3:
        logger.warning("Not enough questionnaire answers to perform rectification")
        return None

    logger.info(f"Analyzing {len(answers)} questionnaire answers for rectification")

    # Extract personality traits and life events from answers
    personality_traits = []
    life_events = []

    for answer in answers:
        question_type = answer.get("question_type", "")

        if "personality" in question_type.lower():
            personality_traits.append(answer)
        elif "event" in question_type.lower() or "life" in question_type.lower():
            life_events.append(answer)

    # Calculate original chart
    original_chart = calculate_chart(birth_dt, latitude, longitude, timezone)

    # Initialize variables for time adjustment
    time_shift_minutes = 0
    confidence = 60.0  # Base confidence

    # Analyze personality traits against different chart times
    if personality_traits:
        # Create a range of possible birth times to test
        candidate_times = []
        for minute_shift in range(-120, 121, 15):  # Test 4-hour range in 15-minute increments
            candidate_time = birth_dt + timedelta(minutes=minute_shift)

            # Skip if candidate time is on a different day
            if candidate_time.date() != birth_dt.date():
                continue

            candidate_times.append((candidate_time, minute_shift))

        # Score each candidate time
        candidate_scores = []
        for candidate_time, minute_shift in candidate_times:
            # Calculate chart for this candidate time
            candidate_chart = calculate_chart(candidate_time, latitude, longitude, timezone)

            # Score how well personality traits match this chart
            trait_score = await _score_personality_traits(personality_traits, candidate_chart, use_openai)

            candidate_scores.append((candidate_time, minute_shift, trait_score))

        # Get best candidate time
        if candidate_scores:
            # Sort by score (descending)
            candidate_scores.sort(key=lambda x: x[2], reverse=True)
            best_time, best_shift, best_score = candidate_scores[0]

            # If best score is good enough, use this time
            if best_score >= 70:
                logger.info(f"Personality-based rectification suggests {best_shift} minute adjustment (score: {best_score})")
                time_shift_minutes = best_shift
                confidence = best_score

    # Adjust birth time based on analysis
    rectified_time = birth_dt + timedelta(minutes=time_shift_minutes)

    # Apply life events analysis if available and confidence isn't high yet
    if life_events and confidence < 80:
        # Extract proper events format
        events = extract_life_events_from_answers(answers)

        # Look for significant transits at these event dates
        events_confidence, event_shift = await _analyze_life_events_transits(
            events, birth_dt, rectified_time, latitude, longitude, timezone
        )

        # If events analysis is more confident, use its time adjustment
        if events_confidence > confidence:
            rectified_time = birth_dt + timedelta(minutes=event_shift)
            confidence = events_confidence
            logger.info(f"Events-based rectification overrode with {event_shift} minute adjustment (confidence: {events_confidence})")

    logger.info(f"Questionnaire-based rectification complete: {rectified_time.strftime('%H:%M:%S')}, confidence: {confidence}")
    return rectified_time, confidence

async def _score_personality_traits(
    personality_traits: List[Dict[str, Any]],
    chart: Dict[str, Any],
    use_openai: bool = True
) -> float:
    """
    Score how well personality traits match a chart.

    Args:
        personality_traits: List of personality traits from questionnaire
        chart: Chart data to analyze
        use_openai: Whether to use OpenAI for analysis

    Returns:
        Confidence score (0-100)
    """
    # Default scoring without OpenAI
    if not use_openai:
        # Simple scoring based on aspects and placements
        base_score = 60.0

        # Extract significant placements from chart
        asc_sign = chart.get("angles", {}).get("Asc", {}).get("sign", "")
        sun_sign = chart.get("planets", {}).get("Sun", {}).get("sign", "")
        moon_sign = chart.get("planets", {}).get("Moon", {}).get("sign", "")
        mercury_sign = chart.get("planets", {}).get("Mercury", {}).get("sign", "")

        # Placeholder for basic chart analysis
        return base_score

    # Use OpenAI for sophisticated analysis
    try:
        from ai_service.api.services.openai import get_openai_service
        openai_service = get_openai_service()

        # Prepare prompt with personality traits and chart data
        traits_text = "\n".join([f"- {trait.get('question', '')}: {trait.get('answer', '')}" for trait in personality_traits])

        prompt = f"""
        Analyze this astrological chart and determine how well it matches the described personality traits.

        Chart data:
        - Ascendant: {chart.get("angles", {}).get("Asc", {}).get("sign", "")} {chart.get("angles", {}).get("Asc", {}).get("sign_longitude", 0):.2f}°
        - Sun: {chart.get("planets", {}).get("Sun", {}).get("sign", "")} {chart.get("planets", {}).get("Sun", {}).get("sign_longitude", 0):.2f}°
        - Moon: {chart.get("planets", {}).get("Moon", {}).get("sign", "")} {chart.get("planets", {}).get("Moon", {}).get("sign_longitude", 0):.2f}°
        - Mercury: {chart.get("planets", {}).get("Mercury", {}).get("sign", "")} {chart.get("planets", {}).get("Mercury", {}).get("sign_longitude", 0):.2f}°
        - Venus: {chart.get("planets", {}).get("Venus", {}).get("sign", "")} {chart.get("planets", {}).get("Venus", {}).get("sign_longitude", 0):.2f}°
        - Mars: {chart.get("planets", {}).get("Mars", {}).get("sign", "")} {chart.get("planets", {}).get("Mars", {}).get("sign_longitude", 0):.2f}°

        Personality traits:
        {traits_text}

        Provide a score from 0-100 indicating how well the chart matches these traits, with 100 being a perfect match.
        Also explain your reasoning. Format your response as JSON with 'score' and 'reasoning' fields.
        """

        # Call OpenAI
        response = await openai_service.generate_completion(
            prompt=prompt,
            task_type="chart_analysis",
            response_format={"type": "json_object"}
        )

        # Extract score from response
        try:
            import json
            result = json.loads(response.get("content", "{}"))
            score = float(result.get("score", 60.0))
            reasoning = result.get("reasoning", "")

            logger.info(f"OpenAI personality analysis: score {score}, reason: {reasoning[:100]}...")
            return score
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            return 60.0  # Default if parsing fails

    except Exception as e:
        logger.error(f"Error in OpenAI personality analysis: {e}")
        return 60.0  # Default if OpenAI fails

async def _analyze_life_events_transits(
    events: List[Dict[str, Any]],
    original_time: datetime,
    current_best_time: datetime,
    latitude: float,
    longitude: float,
    timezone: str
) -> Tuple[float, int]:
    """
    Analyze life events for significant transits.

    Args:
        events: List of life events
        original_time: Original birth time
        current_best_time: Current best estimated time
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string

    Returns:
        Tuple of (confidence score, time shift in minutes)
    """
    if not events:
        return 60.0, 0

    # Create a range of candidate birth times to test
    candidate_times = []

    # Start from the current best time and test variations
    for minute_shift in range(-60, 61, 15):  # Test 2-hour range in 15-minute increments
        candidate_time = current_best_time + timedelta(minutes=minute_shift)

        # Skip if candidate time is on a different day from original
        if candidate_time.date() != original_time.date():
            continue

        # Calculate absolute shift from original time
        abs_shift = int((candidate_time - original_time).total_seconds() / 60)
        candidate_times.append((candidate_time, abs_shift))

    # Score each candidate time based on transits at event dates
    candidate_scores = []

    for candidate_time, abs_shift in candidate_times:
        # Calculate natal chart for this candidate time
        natal_chart = calculate_chart(candidate_time, latitude, longitude, timezone)

        # Initialize score for this candidate
        transit_score = 0

        # Analyze each life event
        for event in events:
            event_date = event.get("date")
            if not event_date:
                continue

            # Convert event date to datetime if it's a string
            if isinstance(event_date, str):
                try:
                    event_date = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
                except ValueError:
                    continue

            # Calculate transit chart for this event date
            transit_chart = calculate_chart(event_date, latitude, longitude, timezone)

            # Score significant aspects between transit and natal
            aspect_score = _score_transit_aspects(transit_chart, natal_chart)
            transit_score += aspect_score

        # Normalize score based on number of events
        normalized_score = min(100, transit_score / len(events) * 20)
        candidate_scores.append((candidate_time, abs_shift, normalized_score))

    # Get best candidate
    if not candidate_scores:
        return 60.0, 0

    # Sort by score (descending)
    candidate_scores.sort(key=lambda x: x[2], reverse=True)
    best_time, best_shift, best_score = candidate_scores[0]

    logger.info(f"Transit analysis score: {best_score}, shift: {best_shift} minutes")
    return best_score, best_shift

def _score_transit_aspects(transit_chart: Dict[str, Any], natal_chart: Dict[str, Any]) -> float:
    """
    Score the significance of aspects between transit and natal charts.

    Args:
        transit_chart: Transit chart data
        natal_chart: Natal chart data

    Returns:
        Score indicating significance of aspects
    """
    score = 0

    # Define significant aspect angles and their orbs
    aspects = {
        0: 8,    # Conjunction (0°) with 8° orb
        60: 6,   # Sextile (60°) with 6° orb
        90: 8,   # Square (90°) with 8° orb
        120: 8,  # Trine (120°) with 8° orb
        180: 10  # Opposition (180°) with 10° orb
    }

    # Define significant planets for transit analysis
    transit_planets = ["Sun", "Moon", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    natal_points = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Asc", "MC"]

    # Get planets from charts
    t_planets = transit_chart.get("planets", {})
    n_planets = natal_chart.get("planets", {})
    n_angles = natal_chart.get("angles", {})

    # Check each transit planet against each natal point
    for t_name in transit_planets:
        if t_name not in t_planets:
            continue

        t_planet = t_planets[t_name]
        t_lon = t_planet.get("longitude", 0)

        for n_name in natal_points:
            # Get the natal point (either planet or angle)
            if n_name in n_planets:
                n_point = n_planets[n_name]
                n_lon = n_point.get("longitude", 0)
            elif n_name in n_angles:
                n_point = n_angles[n_name]
                n_lon = n_point.get("longitude", 0)
            else:
                continue

            # Calculate aspect
            diff = abs(t_lon - n_lon) % 360
            if diff > 180:
                diff = 360 - diff

            # Check for aspects
            for aspect_angle, orb in aspects.items():
                if abs(diff - aspect_angle) <= orb:
                    # Exact aspects get higher scores
                    exactness = 1 - (abs(diff - aspect_angle) / orb)

                    # Weight the aspect
                    weight = 1.0

                    # Major planets/points get higher weight
                    if t_name in ["Jupiter", "Saturn"] or n_name in ["Sun", "Moon", "Asc"]:
                        weight = 1.5

                    # Outer planets to angles get higher weight
                    if t_name in ["Uranus", "Neptune", "Pluto"] and n_name in ["Asc", "MC"]:
                        weight = 2.0

                    # Add to score
                    aspect_score = 10 * exactness * weight
                    score += aspect_score

                    break  # Only count the closest aspect

    return score

async def chart_based_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    use_openai: bool = True
) -> Optional[Tuple[datetime, float]]:
    """
    Rectify birth time based on chart factors.

    Args:
        birth_dt: Birth date and time
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string
        use_openai: Whether to use OpenAI for analysis

    Returns:
        Tuple of (rectified datetime, confidence score) or None if failed
    """
    logger.info(f"Performing chart-based rectification for {birth_dt.strftime('%Y-%m-%d %H:%M:%S')}")

    # Calculate original chart
    original_chart = calculate_chart(birth_dt, latitude, longitude, timezone)

    # Extract key chart factors
    ascendant = original_chart.get("angles", {}).get("Asc", {}).get("longitude", 0)
    midheaven = original_chart.get("angles", {}).get("MC", {}).get("longitude", 0)

    # Get planet positions
    planets = original_chart.get("planets", {})

    # Initialize time adjustment and confidence
    time_shift_minutes = 0
    confidence = 65.0  # Base confidence

    # Check for planets close to angles (within 3 degrees)
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

    # Check Ascendant at critical degrees
    asc_degree = ascendant % 30
    if 0 <= asc_degree < 1 or 29 <= asc_degree < 30:
        # Very close to sign boundary, often indicates inaccurate time
        time_shift_minutes += -30 if asc_degree < 1 else 30
        confidence -= 5
    elif 12.5 <= asc_degree <= 13.5 or 25.5 <= asc_degree <= 26.5:
        # Critical degrees, might indicate accurate time
        confidence += 5

    # Apply a time shift if needed
    if abs(time_shift_minutes) > 0:
        rectified_time = birth_dt + timedelta(minutes=time_shift_minutes)
        logger.info(f"Chart-based factors suggest {time_shift_minutes} minute adjustment")

        # Recalculate chart with adjusted time for verification
        adjusted_chart = calculate_chart(rectified_time, latitude, longitude, timezone)

        # Double-check that the adjustment improved the chart
        if use_openai:
            # Use OpenAI to evaluate if the adjusted chart is more astrologically sound
            improvement_score = await _evaluate_chart_improvement(
                original_chart, adjusted_chart, time_shift_minutes
            )

            # If OpenAI believes the adjustment improves the chart, increase confidence
            if improvement_score > 0:
                confidence += min(15, improvement_score * 0.5)
                logger.info(f"OpenAI confirms chart improvement with score {improvement_score}, increasing confidence")
            else:
                # If OpenAI suggests no improvement, reduce the time shift
                time_shift_minutes = int(time_shift_minutes * 0.5)
                rectified_time = birth_dt + timedelta(minutes=time_shift_minutes)
                logger.info(f"Reducing time shift to {time_shift_minutes} minutes based on AI evaluation")
    else:
        # No adjustment needed
        rectified_time = birth_dt
        logger.info("No chart-based adjustment needed, original time seems accurate")

    # Return the rectified time and confidence
    logger.info(f"Chart-based rectification complete: {rectified_time.strftime('%H:%M:%S')}, confidence: {confidence}")
    return rectified_time, confidence

async def _evaluate_chart_improvement(
    original_chart: Dict[str, Any],
    adjusted_chart: Dict[str, Any],
    time_shift_minutes: int
) -> float:
    """
    Evaluate if the adjusted chart is astrologically more sound than the original.

    Args:
        original_chart: Original chart data
        adjusted_chart: Adjusted chart data
        time_shift_minutes: Time shift in minutes

    Returns:
        Improvement score (-100 to 100), positive means improvement
    """
    try:
        # Get OpenAI service
        from ai_service.api.services.openai import get_openai_service
        openai_service = get_openai_service()

        # Format the chart data for comparison
        o_asc = original_chart.get("angles", {}).get("Asc", {})
        o_mc = original_chart.get("angles", {}).get("MC", {})
        a_asc = adjusted_chart.get("angles", {}).get("Asc", {})
        a_mc = adjusted_chart.get("angles", {}).get("MC", {})

        # Prepare prompt
        prompt = f"""
        Compare these two astrological charts and determine if the adjusted chart is more astrologically sound.

        Original Chart:
        - Ascendant: {o_asc.get("sign", "")} {o_asc.get("sign_longitude", 0):.2f}°
        - Midheaven: {o_mc.get("sign", "")} {o_mc.get("sign_longitude", 0):.2f}°

        Adjusted Chart ({time_shift_minutes} minutes {'later' if time_shift_minutes > 0 else 'earlier'}):
        - Ascendant: {a_asc.get("sign", "")} {a_asc.get("sign_longitude", 0):.2f}°
        - Midheaven: {a_mc.get("sign", "")} {a_mc.get("sign_longitude", 0):.2f}°

        From an astrological perspective, evaluate if the adjusted chart shows improvement in terms of:
        1. Planetary placements relative to houses and angles
        2. Critical degree considerations
        3. Overall chart coherence and balance

        Provide a score from -100 to 100:
        - Positive scores indicate the adjusted chart is better
        - Negative scores indicate the original chart is better
        - 0 indicates no significant difference

        Format your response as JSON with 'score' and 'explanation' fields.
        """

        # Call OpenAI
        response = await openai_service.generate_completion(
            prompt=prompt,
            task_type="chart_evaluation",
            response_format={"type": "json_object"}
        )

        # Extract score from response
        try:
            import json
            result = json.loads(response.get("content", "{}"))
            score = float(result.get("score", 0.0))
            explanation = result.get("explanation", "")

            logger.info(f"Chart improvement evaluation: {score}, reason: {explanation[:100]}...")
            return score
        except Exception as e:
            logger.error(f"Error parsing chart evaluation response: {e}")
            return 0.0

    except Exception as e:
        logger.error(f"Error in chart improvement evaluation: {e}")
        return 0.0

async def generate_rectification_explanation(
    original_time: datetime,
    rectified_time: datetime,
    original_chart: Dict[str, Any],
    rectified_chart: Dict[str, Any],
    confidence: float,
    use_openai: bool = True
) -> str:
    """
    Generate a human-readable explanation of the rectification results.

    Args:
        original_time: Original birth time
        rectified_time: Rectified birth time
        original_chart: Original chart data
        rectified_chart: Rectified chart data
        confidence: Confidence score
        use_openai: Whether to use OpenAI for generating explanation

    Returns:
        Explanation text
    """
    # Calculate time difference
    time_diff_minutes = int((rectified_time - original_time).total_seconds() / 60)
    time_direction = "later" if time_diff_minutes > 0 else "earlier"
    abs_diff = abs(time_diff_minutes)

    # Format times
    orig_time_str = original_time.strftime("%H:%M:%S")
    rect_time_str = rectified_time.strftime("%H:%M:%S")

    # Basic explanation without OpenAI
    if not use_openai:
        # Extract key differences
        orig_asc = original_chart.get("angles", {}).get("Asc", {})
        rect_asc = rectified_chart.get("angles", {}).get("Asc", {})
        orig_mc = original_chart.get("angles", {}).get("MC", {})
        rect_mc = rectified_chart.get("angles", {}).get("MC", {})

        explanation = (
            f"The birth time has been rectified from {orig_time_str} to {rect_time_str} "
            f"({abs_diff} minutes {time_direction}) with {confidence:.1f}% confidence.\n\n"
            f"This adjustment changes the Ascendant from {orig_asc.get('sign', '')} {orig_asc.get('sign_longitude', 0):.1f}° "
            f"to {rect_asc.get('sign', '')} {rect_asc.get('sign_longitude', 0):.1f}°, and the Midheaven from "
            f"{orig_mc.get('sign', '')} {orig_mc.get('sign_longitude', 0):.1f}° to {rect_mc.get('sign', '')} {rect_mc.get('sign_longitude', 0):.1f}°."
        )

        if abs_diff <= 10:
            explanation += "\n\nThis is a minor adjustment that refines the house cusps and positions slightly."
        elif abs_diff <= 30:
            explanation += "\n\nThis moderate adjustment shifts some planets to different houses and refines aspect patterns."
        else:
            explanation += "\n\nThis significant adjustment substantially changes the house placements and chart interpretation."

        return explanation

    # Use OpenAI for sophisticated explanation
    try:
        from ai_service.api.services.openai import get_openai_service
        openai_service = get_openai_service()

        # Format chart data for comparison
        orig_asc = original_chart.get("angles", {}).get("Asc", {})
        rect_asc = rectified_chart.get("angles", {}).get("Asc", {})
        orig_mc = original_chart.get("angles", {}).get("MC", {})
        rect_mc = rectified_chart.get("angles", {}).get("MC", {})

        # Get key planet positions that might have changed houses
        planets_data = []
        for planet in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]:
            orig_planet = original_chart.get("planets", {}).get(planet, {})
            rect_planet = rectified_chart.get("planets", {}).get(planet, {})

            if orig_planet and rect_planet:
                orig_house = orig_planet.get("house", 0)
                rect_house = rect_planet.get("house", 0)

                # Only include if house changed
                if orig_house != rect_house:
                    planets_data.append(
                        f"{planet}: House {orig_house} to House {rect_house}"
                    )

        # Prepare planets string
        planets_text = "\n".join(planets_data) if planets_data else "No significant house changes"

        # Prepare prompt
        prompt = f"""
        Generate an astrological explanation for a birth time rectification.

        Original birth time: {orig_time_str}
        Rectified birth time: {rect_time_str}
        Time difference: {abs_diff} minutes {time_direction}
        Confidence: {confidence:.1f}%

        Changes in chart:
        - Ascendant: {orig_asc.get('sign', '')} {orig_asc.get('sign_longitude', 0):.1f}° → {rect_asc.get('sign', '')} {rect_asc.get('sign_longitude', 0):.1f}°
        - Midheaven: {orig_mc.get('sign', '')} {orig_mc.get('sign_longitude', 0):.1f}° → {rect_mc.get('sign', '')} {rect_mc.get('sign_longitude', 0):.1f}°

        Planet house changes:
        {planets_text}

        Provide a detailed explanation of:
        1. Why this rectification is astrologically significant
        2. How it affects the chart interpretation
        3. What key improvements it makes to the chart accuracy

        Keep the explanation to 2-3 paragraphs and explain in clear language that a non-astrologer can understand.
        """

        # Call OpenAI
        response = await openai_service.generate_completion(
            prompt=prompt,
            task_type="rectification_explanation"
        )

        explanation = response.get("content", "")

        # If we got a reasonable explanation, return it
        if len(explanation) > 100:
            return explanation

        # Fall back to basic explanation if OpenAI fails or returns too short a response
        logger.warning("OpenAI explanation was too short or failed, using basic explanation")
        return (
            f"The birth time has been rectified from {orig_time_str} to {rect_time_str} "
            f"({abs_diff} minutes {time_direction}) with {confidence:.1f}% confidence.\n\n"
            f"This adjustment changes the Ascendant from {orig_asc.get('sign', '')} {orig_asc.get('sign_longitude', 0):.1f}° "
            f"to {rect_asc.get('sign', '')} {rect_asc.get('sign_longitude', 0):.1f}°, and the Midheaven from "
            f"{orig_mc.get('sign', '')} {orig_mc.get('sign_longitude', 0):.1f}° to {rect_mc.get('sign', '')} {rect_mc.get('sign_longitude', 0):.1f}°."
        )

    except Exception as e:
        logger.error(f"Error generating explanation: {e}")

        # Fall back to basic explanation if OpenAI fails
        return (
            f"The birth time has been rectified from {orig_time_str} to {rect_time_str} "
            f"({abs_diff} minutes {time_direction}) with {confidence:.1f}% confidence. "
            f"This adjustment refines the positions of the houses and angles in the chart."
        )

async def generate_detailed_analysis(
    original_chart: Dict[str, Any],
    rectified_chart: Dict[str, Any],
    original_time: datetime,
    rectified_time: datetime
) -> Dict[str, Any]:
    """
    Generate detailed analysis of the changes between original and rectified charts.

    Args:
        original_chart: Original chart data
        rectified_chart: Rectified chart data
        original_time: Original birth time
        rectified_time: Rectified birth time

    Returns:
        Dictionary with detailed analysis
    """
    # Calculate time difference
    time_diff_minutes = int((rectified_time - original_time).total_seconds() / 60)

    # Initialize result structure
    result = {
        "time_shift": {
            "minutes": time_diff_minutes,
            "direction": "later" if time_diff_minutes > 0 else "earlier",
            "original_time": original_time.isoformat(),
            "rectified_time": rectified_time.isoformat()
        },
        "angles_changes": [],
        "house_cusps_changes": [],
        "planets_house_changes": [],
        "aspects_changes": []
    }

    # Compare angles
    for angle_name in ["Asc", "MC"]:
        orig_angle = original_chart.get("angles", {}).get(angle_name, {})
        rect_angle = rectified_chart.get("angles", {}).get(angle_name, {})

        if orig_angle and rect_angle:
            orig_lon = orig_angle.get("longitude", 0)
            rect_lon = rect_angle.get("longitude", 0)

            result["angles_changes"].append({
                "angle": angle_name,
                "original": {
                    "sign": orig_angle.get("sign", ""),
                    "longitude": orig_lon,
                    "sign_longitude": orig_angle.get("sign_longitude", 0)
                },
                "rectified": {
                    "sign": rect_angle.get("sign", ""),
                    "longitude": rect_lon,
                    "sign_longitude": rect_angle.get("sign_longitude", 0)
                },
                "difference_degrees": min((rect_lon - orig_lon) % 360, (orig_lon - rect_lon) % 360)
            })

    # Compare house cusps
    orig_houses = original_chart.get("houses", [])
    rect_houses = rectified_chart.get("houses", [])

    for i in range(min(len(orig_houses), len(rect_houses))):
        orig_house = orig_houses[i]
        rect_house = rect_houses[i]

        house_num = i + 1
        orig_lon = orig_house.get("longitude", 0)
        rect_lon = rect_house.get("longitude", 0)

        result["house_cusps_changes"].append({
            "house": house_num,
            "original": {
                "sign": orig_house.get("sign", ""),
                "longitude": orig_lon,
                "sign_longitude": orig_house.get("sign_longitude", 0)
            },
            "rectified": {
                "sign": rect_house.get("sign", ""),
                "longitude": rect_lon,
                "sign_longitude": rect_house.get("sign_longitude", 0)
            },
            "difference_degrees": min((rect_lon - orig_lon) % 360, (orig_lon - rect_lon) % 360)
        })

    # Compare planet house placements
    for planet_name in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
        orig_planet = original_chart.get("planets", {}).get(planet_name, {})
        rect_planet = rectified_chart.get("planets", {}).get(planet_name, {})

        if orig_planet and rect_planet:
            orig_house = orig_planet.get("house", 0)
            rect_house = rect_planet.get("house", 0)

            # Only add if the house changed
            if orig_house != rect_house:
                result["planets_house_changes"].append({
                    "planet": planet_name,
                    "original_house": orig_house,
                    "rectified_house": rect_house,
                    "significance": "Major" if planet_name in ["Sun", "Moon", "Ascendant"] else "Minor"
                })

    return result
