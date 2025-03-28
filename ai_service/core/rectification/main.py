"""
Main coordination module for birth time rectification.
"""
from datetime import datetime, timedelta
import logging
import json
import uuid
import re
from typing import List, Dict, Any, Tuple, Optional, Union, cast
import traceback
import os
from pathlib import Path
import asyncio

# pylint: disable=no-member,access-member-before-definition,attribute-defined-outside-init

# Import sub-modules
from .event_analysis import extract_life_events_from_answers
from .chart_calculator import calculate_chart, EnhancedChartCalculator
from .methods.ai_rectification import ai_assisted_rectification
from .methods.solar_arc import solar_arc_rectification
from .methods.progressed import progressed_ascendant_rectification
from .utils.ephemeris import verify_ephemeris_files as verify_ephemeris_files_util
from .utils.storage import store_rectified_chart
from .time_indicators import extract_birth_time_indicators

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
    Get or create an instance of the OpenAI service.

    Returns:
        OpenAI service instance or None if not available

    Raises:
        ValueError: If OpenAI service cannot be initialized
    """
    # Try to get from dependency container first
    try:
        from ai_service.utils.dependency_container import get_container
        container = get_container()
        try:
            return await container.get("openai_service")
        except ValueError:
            # Not registered yet
            pass
    except Exception as e:
        logger.error(f"Error getting container: {e}")

    # Try direct import
    try:
        from ai_service.api.services.openai import get_openai_service as get_service
        return await get_service()
    except Exception as e:
        logger.error(f"Error importing OpenAI service: {e}")
        return None

    # Warning instead of error to allow fallback behavior
    logger.warning("Failed to initialize OpenAI service for rectification")
    return None

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
    birth_dt: Union[datetime, str],
    latitude: float,
    longitude: float,
    timezone: str,
    answers: Optional[List[Dict[str, Any]]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive birth time rectification.

    Args:
        birth_dt: Birth datetime (original estimate)
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Birth timezone name
        answers: Questionnaire answers (optional)
        events: Life events data (optional)
        options: Rectification options

    Returns:
        Dictionary with rectification results

    Raises:
        ValueError: If parameters are invalid or services unavailable
        RuntimeError: If rectification fails
    """
    # Validate parameters
    if not birth_dt:
        raise ValueError("Birth datetime is required for rectification")

    if not timezone:
        raise ValueError("Timezone is required for rectification")

    # Normalize the birth_dt to a datetime object if it's a string
    if isinstance(birth_dt, str):
        try:
            birth_dt = datetime.fromisoformat(birth_dt.replace('Z', '+00:00'))
        except Exception as e:
            raise ValueError(f"Invalid birth datetime format: {e}")

    # Apply default options if not provided
    if options is None:
        options = {}

    # Initialize empty lists for None values
    if answers is None:
        answers = []

    if events is None:
        events = []

    # Create options object to avoid changing the original
    rectification_opts = options.copy()

    # Get or create the OpenAI service if needed
    openai_service = None
    if rectification_opts.get("use_openai", True):
        try:
            from ai_service.api.services.openai import get_openai_service
            # Properly await the async function
            openai_service = await get_openai_service()
            if not openai_service:
                raise ValueError("OpenAI service is required but not available")
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI service: {e}")

    # Initialize the enhanced chart calculator with a Swiss Ephemeris proxy
    try:
        # Use the same SwissEphemerisProxy class as used in the chart calculator
        from ai_service.core.rectification.chart_calculator import SwissEphemerisProxy
        swisseph = SwissEphemerisProxy()
        calculator = EnhancedChartCalculator(swisseph)
    except Exception as e:
        raise ValueError(f"Failed to initialize chart calculator: {e}")

    try:
        # Step 1: Analyze questionnaire answers for birth time indicators
        time_indicators = []
        if answers:
            # Get OpenAI service for analysis if needed
            # We need to adapt how we call extract_birth_time_indicators
            # since it expects chart data, not questionnaire answers

            # First calculate a chart with the provided details
            from ai_service.core.rectification.chart_calculator import calculate_chart
            chart_data = calculate_chart(
                birth_dt=birth_dt,
                latitude=latitude,
                longitude=longitude,
                timezone_str=timezone
            )

            # Then extract the time indicators from the chart
            chart_indicators = extract_birth_time_indicators(chart_data)

            # Convert chart indicators to list format expected by ai_assisted_rectification
            for indicator_type, data in chart_indicators.items():
                time_indicators.append({
                    "type": indicator_type,
                    "data": data
                })

            # Add questionnaire data if available
            if answers:
                time_indicators.append({
                    "type": "questionnaire_answers",
                    "data": answers
                })

        # Step 2: AI-assisted rectification
        rectification_result = await ai_assisted_rectification(
            birth_dt=birth_dt,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            openai_service=openai_service,
            time_indicators=time_indicators,
            events=events,
            swisseph_proxy=swisseph,
            max_retries=rectification_opts.get("max_retries", 3)
        )

        return rectification_result

    except Exception as e:
        error_msg = f"Comprehensive rectification failed: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

async def basic_chart_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    chart: Optional[Dict[str, Any]] = None
) -> Tuple[datetime, float]:
    """


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

async def _are_compatible_signs(sign1: str, sign2: str) -> bool:
    """
    Check if two zodiac signs are compatible.

    Args:
        sign1: First zodiac sign
        sign2: Second zodiac sign

    Returns:
        True if signs are compatible, False otherwise
    """
    # Element-based compatibility
    fire_signs = ["Aries", "Leo", "Sagittarius"]
    earth_signs = ["Taurus", "Virgo", "Capricorn"]
    air_signs = ["Gemini", "Libra", "Aquarius"]
    water_signs = ["Cancer", "Scorpio", "Pisces"]

    # Signs of the same element are compatible
    if (sign1 in fire_signs and sign2 in fire_signs) or \
       (sign1 in earth_signs and sign2 in earth_signs) or \
       (sign1 in air_signs and sign2 in air_signs) or \
       (sign1 in water_signs and sign2 in water_signs):
        return True

    # Fire and Air signs are compatible
    if (sign1 in fire_signs and sign2 in air_signs) or \
       (sign1 in air_signs and sign2 in fire_signs):
        return True

    # Earth and Water signs are compatible
    if (sign1 in earth_signs and sign2 in water_signs) or \
       (sign1 in water_signs and sign2 in earth_signs):
        return True

    return False

def _check_aspect(longitude1: float, longitude2: float) -> Optional[str]:
    """
    Check if two planetary positions form an aspect.

    Args:
        longitude1: Longitude of first planet (0-360)
        longitude2: Longitude of second planet (0-360)

    Returns:
        Name of the aspect or None if no aspect is formed
    """
    # Calculate the angular difference
    diff = abs(longitude1 - longitude2) % 360
    if diff > 180:
        diff = 360 - diff

    # Define aspects with orbs
    aspects = {
        0: ("conjunction", 8),    # 0° with 8° orb
        60: ("sextile", 6),       # 60° with 6° orb
        90: ("square", 8),        # 90° with 8° orb
        120: ("trine", 8),        # 120° with 8° orb
        180: ("opposition", 10)   # 180° with 10° orb
    }

    # Check for aspects
    for angle, (aspect_name, orb) in aspects.items():
        if abs(diff - angle) <= orb:
            return aspect_name

    return None

async def _score_personality_traits(
    personality_traits: List[Dict[str, Any]],
    chart: Dict[str, Any],
    use_openai: bool = True
) -> float:
    """
    Score how well a chart matches personality traits.

    Args:
        personality_traits: List of personality traits
        chart: Chart data to score
        use_openai: Whether to use OpenAI for scoring

    Returns:
        Score from 0-100 indicating match quality

    Raises:
        RuntimeError: If personality analysis fails
    """
    try:
        if not use_openai:
            logger.info("OpenAI analysis disabled, using heuristic matching")
            return 50.0  # Default to neutral score

        # Get OpenAI service
        openai_service = await get_openai_service()
        if openai_service is None:
            logger.warning("OpenAI service not available, using fallback scoring")
            return 50.0  # Default to neutral score

        # Extract traits as text
        trait_text = "\n".join([
            f"- {trait.get('name', 'Unknown trait')}: {trait.get('value', 'Unknown value')}"
            for trait in personality_traits
        ])

        # Create prompt
        prompt = f"""
        You are an expert in Vedic astrology analyzing how well a birth chart matches personality traits.

        PERSONALITY TRAITS:
        {trait_text}

        CHART DATA:
        {json.dumps(chart, indent=2)}

        Provide a score from 0-100 indicating how well the chart matches these traits, with 100 being a perfect match.
        Also explain your reasoning. Format your response as JSON with 'score' and 'reasoning' fields.
        """

        # Check if openai_service is None before accessing chat_completion
        if openai_service is None:
            logger.warning("OpenAI service is None, returning default score")
            return 50.0  # Default score

        # Check if chat_completion method exists
        if not hasattr(openai_service, 'chat_completion'):
            logger.warning("OpenAI service missing chat_completion method")
            return 50.0  # Default score

        # Call OpenAI
        response = await openai_service.chat_completion(
            messages=[
                {"role": "system", "content": "You are an expert astrologer evaluating birth charts."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4-turbo",
            temperature=0.3
        )

        # Extract score from response
        try:
            content = response.get("content", "{}")
            # Attempt to find a JSON object in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            result = json.loads(content)
            score = float(result.get("score", 0.0))
            reasoning = result.get("reasoning", "")

            logger.info(f"OpenAI personality analysis: score {score}, reason: {reasoning[:100]}...")
            return score
        except Exception as e:
            logger.error(f"Error parsing personality analysis response: {e}")
            return 0.0

    except Exception as e:
        logger.error(f"Error in personality analysis: {e}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Personality analysis with OpenAI failed: {str(e)}")

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

    Raises:
        ValueError: If no events are provided
        RuntimeError: If transit analysis fails
    """
    if not events:
        logger.error("No life events provided for transit analysis")
        raise ValueError("No life events provided for transit analysis")

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
        logger.error("No valid transit aspects found for candidate birth times")
        raise RuntimeError("Transit analysis failed: no valid aspects found for any candidate birth times")

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
        openai_service = await get_openai_service()  # Properly await this async function

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

        # Check if openai_service is None before accessing chat_completion
        if openai_service is None:
            logger.warning("OpenAI service is None, returning default score")
            return 50.0  # Default score

        # Check if chat_completion method exists
        if not hasattr(openai_service, 'chat_completion'):
            logger.warning("OpenAI service missing chat_completion method")
            return 50.0  # Default score

        # Call OpenAI
        response = await openai_service.chat_completion(
            messages=[
                {"role": "system", "content": "You are an expert astrologer evaluating birth charts."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4-turbo",
            temperature=0.3
        )

        # Extract score from response
        try:
            content = response.get("content", "{}")
            # Attempt to find a JSON object in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            result = json.loads(content)
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
    Generate explanation for birth time rectification.

    Args:
        original_time: Original birth time
        rectified_time: Rectified birth time
        original_chart: Original chart data
        rectified_chart: Rectified chart data
        confidence: Confidence score
        use_openai: Whether to use OpenAI

    Returns:
        Explanation text
    """
    if not use_openai:
        # Use simple explanation if OpenAI is disabled
        minutes_diff = int((rectified_time - original_time).total_seconds() / 60)
        sign = "earlier" if minutes_diff < 0 else "later"
        minutes_diff = abs(minutes_diff)

        explanation = (
            f"The birth time has been rectified to {rectified_time.strftime('%H:%M:%S')}, "
            f"which is {minutes_diff} minutes {sign} than the original time of {original_time.strftime('%H:%M:%S')}. "
            f"This rectification has been determined with {confidence:.1f}% confidence based on "
            f"astrological principles and analysis of life events."
        )
        return explanation

    # Create fallback explanation
    minutes_diff = int((rectified_time - original_time).total_seconds() / 60)
    sign = "earlier" if minutes_diff < 0 else "later"
    minutes_diff = abs(minutes_diff)

    fallback_explanation = (
        f"The birth time has been rectified to {rectified_time.strftime('%H:%M:%S')}, "
        f"which is {minutes_diff} minutes {sign} than the original time of {original_time.strftime('%H:%M:%S')}. "
        f"This rectification has been determined with {confidence:.1f}% confidence based on "
        f"astrological principles and analysis of life events."
    )

    try:
        # Get OpenAI service
        openai_service = await get_openai_service()
        if openai_service is None:
            logger.warning("OpenAI service not available for explanation, using fallback")
            return fallback_explanation

        # Create prompt
        prompt = f"""
        Explain the astrological significance of rectifying a birth time from {original_time.strftime('%H:%M:%S')} to {rectified_time.strftime('%H:%M:%S')}.

        ORIGINAL CHART DETAILS:
        {json.dumps(original_chart, indent=2)}

        RECTIFIED CHART DETAILS:
        {json.dumps(rectified_chart, indent=2)}

        CONFIDENCE: {confidence:.1f}%

        Provide a 2-3 paragraph explanation that is clear, concise, and understandable to someone without astrological expertise.
        Focus on the practical implications of this rectification.
        """

        # Call OpenAI
        if not hasattr(openai_service, 'chat_completion'):
            logger.warning("OpenAI service missing chat_completion method")
            return fallback_explanation

        response = await openai_service.chat_completion(
            messages=[
                {"role": "system", "content": "You are an expert Vedic astrologer explaining birth time rectification."},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4",
            temperature=0.7
        )

        # Extract explanation from response
        if response and isinstance(response, dict) and "choices" in response:
            choice = response["choices"][0] if response.get("choices") else {}
            message = choice.get("message", {}) if isinstance(choice, dict) else {}
            explanation = message.get("content", "") if isinstance(message, dict) else str(message)

            # Check if explanation is valid
            if explanation and len(explanation) > 50:
                return explanation

        logger.warning("OpenAI explanation was too short or failed, using basic explanation")
        return fallback_explanation

    except Exception as e:
        logger.error(f"Error generating explanation: {e}")
        return fallback_explanation

async def generate_detailed_analysis(
    original_chart: Dict[str, Any],
    rectified_chart: Dict[str, Any],
    original_time: datetime,
    rectified_time: datetime
) -> Dict[str, Any]:
    """
    Generate detailed analysis comparing original and rectified charts.

    Args:
        original_chart: Original chart data
        rectified_chart: Rectified chart data
        original_time: Original birth time
        rectified_time: Rectified birth time

    Returns:
        Dictionary with detailed analysis
    """
    try:
        # Get OpenAI service
        openai_service = await get_openai_service()
        if openai_service is None:
            logger.warning("OpenAI service not available for detailed analysis")
            return {
                "summary": "Detailed analysis unavailable (OpenAI service not available)",
                "house_changes": [],
                "planet_changes": [],
                "significance": 0
            }

        # Prepare prompt for OpenAI
        prompt = f"""
        Compare the original and rectified birth charts and provide a detailed analysis focusing on the astrological significance of the changes. Explain how these changes may impact the individual's life path, personality, and key life areas.

        ORIGINAL CHART (Birth Time: {original_time.strftime('%H:%M:%S')}):
        {json.dumps(original_chart, indent=2)}

        RECTIFIED CHART (Birth Time: {rectified_time.strftime('%H:%M:%S')}):
        {json.dumps(rectified_chart, indent=2)}

        Format your response as JSON with these fields:
        - summary: A 2-3 paragraph summary of the key differences and their significance
        - house_changes: An array of objects with 'house', 'description', and 'significance' fields
        - planet_changes: An array of objects with 'planet', 'description', and 'significance' fields
        - significance: A number from 0-100 indicating the overall significance of the rectification
        """

        # Check if text_completion method exists
        if not hasattr(openai_service, 'text_completion'):
            logger.warning("OpenAI service missing text_completion method")
            return {
                "summary": "Detailed analysis unavailable (API method not available)",
                "house_changes": [],
                "planet_changes": [],
                "significance": 0
            }

        # Call OpenAI
        result = await openai_service.text_completion(
            prompt=prompt,
            model="gpt-4-turbo",
            temperature=0.4,
            max_tokens=2000
        )

        # Extract analysis from response
        response_text = ""
        if result and isinstance(result, dict):
            choices = result.get("choices", [])
            if choices and isinstance(choices, list) and len(choices) > 0:
                choice = choices[0]
                if isinstance(choice, dict):
                    response_text = choice.get("text", "")

        if not response_text:
            logger.warning("Invalid response format from OpenAI")
            return {
                "summary": "Detailed analysis unavailable (invalid response format)",
                "house_changes": [],
                "planet_changes": [],
                "significance": 0
            }

        # Try to parse JSON response
        try:
            analysis = json.loads(response_text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response")
            # Try to extract JSON from text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    logger.warning("Failed to extract JSON from response")
                    analysis = {}
            else:
                analysis = {}

        # Extract summary
        summary = analysis.get("summary", "")
        if not isinstance(summary, str):
            logger.warning("Invalid summary format for detailed analysis")
            summary = "No summary provided"

        # Extract house changes
        house_changes = analysis.get("house_changes", [])
        if not isinstance(house_changes, list):
            logger.warning("Invalid house changes format for detailed analysis")
            house_changes = []

        # Extract planet changes
        planet_changes = analysis.get("planet_changes", [])
        if not isinstance(planet_changes, list):
            logger.warning("Invalid planet changes format for detailed analysis")
            planet_changes = []

        # Extract significance
        significance = analysis.get("significance", 0)
        if not isinstance(significance, (int, float)):
            logger.warning("Invalid significance format for detailed analysis")
            significance = 0

        return {
            "summary": summary,
            "house_changes": house_changes,
            "planet_changes": planet_changes,
            "significance": significance
        }

    except Exception as e:
        logger.error(f"Error generating detailed analysis: {e}")
        return {
            "summary": f"Detailed analysis unavailable: {str(e)}",
            "house_changes": [],
            "planet_changes": [],
            "significance": 0
        }
