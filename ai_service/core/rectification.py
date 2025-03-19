"""
Birth time rectification module

This module provides functionality to rectify birth times based on
questionnaire answers and life events using actual astrological calculations.
"""

from datetime import datetime, timedelta
import logging
import math
import asyncio
import pytz
import re
from typing import Tuple, List, Dict, Any, Optional, Union
import numpy as np

# Import astrological calculation libraries
try:
    from flatlib.datetime import Datetime  # type: ignore
    from flatlib.geopos import GeoPos  # type: ignore
    from flatlib.chart import Chart  # type: ignore
    from flatlib import const  # type: ignore
    from flatlib.dignities import essential  # type: ignore
    FLATLIB_AVAILABLE = True
except ImportError:
    FLATLIB_AVAILABLE = False
    # Create dummy values for type checking
    class DummyConst:
        ASC = "ASC"
        MC = "MC"
        LIST_PLANETS = ["SUN", "MOON", "MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"]
        SUN = "SUN"
        MOON = "MOON"
        MERCURY = "MERCURY"
        VENUS = "VENUS"
        MARS = "MARS"
        JUPITER = "JUPITER"
        SATURN = "SATURN"
        URANUS = "URANUS"
        NEPTUNE = "NEPTUNE"
        PLUTO = "PLUTO"
    const = DummyConst()

# Additional required dependencies
import numpy as np
try:
    from timezonefinder import TimezoneFinder
    TIMEZONEFINDER_AVAILABLE = True
except ImportError:
    TIMEZONEFINDER_AVAILABLE = False
    # Create dummy implementation for timezonefinder
    class DummyTimezoneFinder:
        def timezone_at(self, lat=None, lng=None):
            return "UTC"
    TimezoneFinder = DummyTimezoneFinder

# Import OpenAI integration for advanced rectification
try:
    from ai_service.api.services.openai import get_openai_service
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    # Use Any type for get_openai_service to avoid type mismatch
    def get_openai_service() -> Any:
        return None

# Configure logging
logger = logging.getLogger(__name__)

# Astrological life event mapping - specific planetary transits/aspects associated with life events
LIFE_EVENT_MAPPING = {
    'marriage': [
        {'planet1': const.VENUS, 'planet2': const.JUPITER, 'aspect': 'conjunction'},
        {'planet1': const.VENUS, 'planet2': const.MOON, 'aspect': 'trine'},
        {'planet1': const.SUN, 'planet2': const.VENUS, 'aspect': 'conjunction'},
        {'house': 7} # 7th house connections
    ],
    'divorce': [
        {'planet1': const.VENUS, 'planet2': const.SATURN, 'aspect': 'square'},
        {'planet1': const.VENUS, 'planet2': const.MARS, 'aspect': 'opposition'},
        {'planet1': const.SUN, 'planet2': const.SATURN, 'aspect': 'opposition'},
        {'house': 7} # 7th house connections
    ],
    'child_birth': [
        {'planet1': const.JUPITER, 'planet2': const.MOON, 'aspect': 'conjunction'},
        {'planet1': const.VENUS, 'planet2': const.JUPITER, 'aspect': 'trine'},
        {'house': 5} # 5th house connections
    ],
    'career_change': [
        {'planet1': const.SATURN, 'planet2': const.SUN, 'aspect': 'conjunction'},
        {'planet1': const.JUPITER, 'planet2': const.MC, 'aspect': 'conjunction'},
        {'house': 10} # 10th house connections
    ],
    'relocation': [
        {'planet1': const.MOON, 'planet2': const.URANUS, 'aspect': 'conjunction'},
        {'planet1': const.MERCURY, 'planet2': const.JUPITER, 'aspect': 'trine'},
        {'house': 4} # 4th house connections
    ],
    'health_crisis': [
        {'planet1': const.MARS, 'planet2': const.SATURN, 'aspect': 'conjunction'},
        {'planet1': const.SUN, 'planet2': const.NEPTUNE, 'aspect': 'square'},
        {'house': 6} # 6th house connections
    ]
}

# Aspect orbs - maximum allowed degrees deviation from exact aspect
ASPECT_ORBS = {
    'conjunction': 8.0,  # 0 degrees
    'opposition': 8.0,   # 180 degrees
    'trine': 7.0,        # 120 degrees
    'square': 7.0,       # 90 degrees
    'sextile': 6.0,      # 60 degrees
    'semi-sextile': 3.0, # 30 degrees
    'quincunx': 3.0,     # 150 degrees
    'semi-square': 3.0,  # 45 degrees
}

def get_aspect_angle(aspect_type: str) -> float:
    """Get the angle for a specific aspect type."""
    aspect_angles = {
        'conjunction': 0.0,
        'opposition': 180.0,
        'trine': 120.0,
        'square': 90.0,
        'sextile': 60.0,
        'semi-sextile': 30.0,
        'quincunx': 150.0,
        'semi-square': 45.0,
    }
    return aspect_angles.get(aspect_type, 0.0)

def is_aspect_active(angle1: float, angle2: float, aspect_type: str) -> bool:
    """
    Check if an aspect between two angles is active.

    Args:
        angle1: First angle in degrees
        angle2: Second angle in degrees
        aspect_type: Type of aspect to check

    Returns:
        True if aspect is active, False otherwise
    """
    # Get the target angle for this aspect
    target_angle = get_aspect_angle(aspect_type)

    # Calculate the absolute difference between angles
    diff = abs(angle1 - angle2) % 360
    if diff > 180:
        diff = 360 - diff

    # Check if the difference is within the allowed orb
    return abs(diff - target_angle) <= ASPECT_ORBS.get(aspect_type, 0)

def calculate_chart(birth_date: datetime, latitude: float, longitude: float, timezone_str: str) -> Any:
    """
    Calculate astrological chart for a specific birth time.

    Args:
        birth_date: Birth datetime
        latitude: Birth location latitude
        longitude: Birth location longitude
        timezone_str: Birth location timezone

    Returns:
        Flatlib Chart object
    """
    if not FLATLIB_AVAILABLE:
        logger.error("Flatlib is not available. Cannot calculate chart.")
        return None

    # Format date for flatlib
    dt_str = birth_date.strftime('%Y/%m/%d')
    time_str = birth_date.strftime('%H:%M')

    # Convert timezone to offset format (+/-HH:MM)
    timezone = pytz.timezone(timezone_str)
    offset = timezone.utcoffset(birth_date)
    hours, remainder = divmod(offset.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    offset_str = f"{'+' if hours >= 0 else '-'}{abs(int(hours)):02d}:{abs(int(minutes)):02d}"

    # Create flatlib datetime and position objects
    date = Datetime(dt_str, time_str, offset_str)
    pos = GeoPos(f"{abs(latitude)}{'n' if latitude >= 0 else 's'}",
                f"{abs(longitude)}{'e' if longitude >= 0 else 'w'}")

    # Calculate and return the chart
    return Chart(date, pos)

def get_house_planet_connections(chart: Any, house_num: int) -> List[Dict[str, Any]]:
    """
    Get all planets in or aspecting a specific house.

    Args:
        chart: Flatlib Chart object
        house_num: House number (1-12)

    Returns:
        List of planet objects connected to this house
    """
    if not FLATLIB_AVAILABLE or chart is None:
        return []

    house = chart.getHouse(house_num)
    house_objects = []

    # Check planets in the house
    for planet_name in const.LIST_PLANETS:
        planet = chart.getObject(planet_name)
        if house.hasObject(planet):
            house_objects.append({
                'planet': planet_name,
                'connection_type': 'in_house',
                'strength': 10.0  # Direct placement is strongest
            })

    # Check planets aspecting house cusp
    house_cusp_longitude = house.lon
    for planet_name in const.LIST_PLANETS:
        planet = chart.getObject(planet_name)
        planet_longitude = planet.lon

        for aspect_type in ASPECT_ORBS.keys():
            if is_aspect_active(house_cusp_longitude, planet_longitude, aspect_type):
                # Calculate strength based on aspect type and orb
                orb = ASPECT_ORBS[aspect_type]
                target_angle = get_aspect_angle(aspect_type)
                diff = abs(house_cusp_longitude - planet_longitude) % 360
                if diff > 180:
                    diff = 360 - diff
                actual_orb = abs(diff - target_angle)

                # Closer to exact aspect = stronger
                strength = (1 - actual_orb/orb) * 5.0

                # Certain aspects are more significant
                if aspect_type in ['conjunction', 'opposition']:
                    strength *= 1.5
                elif aspect_type in ['trine', 'square']:
                    strength *= 1.2

                house_objects.append({
                    'planet': planet_name,
                    'connection_type': f'aspect_{aspect_type}',
                    'strength': strength
                })

    return house_objects

def get_planet_aspects(chart: Any, planet1_name: str, planet2_name: str) -> List[Dict[str, Any]]:
    """
    Get all aspects between two planets.

    Args:
        chart: Flatlib Chart object
        planet1_name: First planet name
        planet2_name: Second planet name

    Returns:
        List of aspect details
    """
    if not FLATLIB_AVAILABLE or chart is None:
        return []

    planet1 = chart.getObject(planet1_name)
    planet2 = chart.getObject(planet2_name)

    aspects = []
    for aspect_type in ASPECT_ORBS.keys():
        if is_aspect_active(planet1.lon, planet2.lon, aspect_type):
            # Calculate strength based on aspect type and orb
            orb = ASPECT_ORBS[aspect_type]
            target_angle = get_aspect_angle(aspect_type)
            diff = abs(planet1.lon - planet2.lon) % 360
            if diff > 180:
                diff = 360 - diff
            actual_orb = abs(diff - target_angle)

            # Closer to exact aspect = stronger
            strength = (1 - actual_orb/orb) * 10.0

            # Consider essential dignity
            p1_dignity = essential.get_dignity(planet1)
            p2_dignity = essential.get_dignity(planet2)
            dignity_factor = 1.0
            if p1_dignity == 'ruler' or p2_dignity == 'ruler':
                dignity_factor = 1.5
            elif p1_dignity == 'exalted' or p2_dignity == 'exalted':
                dignity_factor = 1.3
            elif p1_dignity == 'fall' or p2_dignity == 'fall':
                dignity_factor = 0.7
            elif p1_dignity == 'detriment' or p2_dignity == 'detriment':
                dignity_factor = 0.8

            strength *= dignity_factor

            aspects.append({
                'aspect_type': aspect_type,
                'strength': strength,
                'orb': actual_orb
            })

    return aspects

def score_chart_for_event(chart: Any, event_type: str) -> float:
    """
    Score a chart for a specific life event.

    Args:
        chart: Flatlib Chart object
        event_type: Type of life event (marriage, divorce, etc.)

    Returns:
        Score indicating how well the chart aligns with the event
    """
    if not FLATLIB_AVAILABLE or chart is None:
        return 0.0

    total_score = 0.0
    event_factors = LIFE_EVENT_MAPPING.get(event_type, [])

    # Check all event factors
    for factor in event_factors:
        if 'house' in factor:
            # Check house connections
            house_connections = get_house_planet_connections(chart, factor.get('house', 1))
            for connection in house_connections:
                total_score += connection['strength']
        else:
            # Check planet aspects
            planet1 = factor.get('planet1')
            planet2 = factor.get('planet2')
            aspect_type = factor.get('aspect')

            if planet1 and planet2:
                aspects = get_planet_aspects(chart, planet1, planet2)
                for aspect in aspects:
                    if aspect.get('aspect_type') == aspect_type:
                        total_score += aspect['strength']

    return total_score

def extract_life_events_from_answers(answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract life events from questionnaire answers.

    Args:
        answers: List of questionnaire answers

    Returns:
        List of structured life events with event_type and event_date
    """
    life_events = []

    # Keywords for detecting event types
    event_keywords = {
        'marriage': ['marriage', 'married', 'wedding', 'spouse'],
        'divorce': ['divorce', 'separated', 'split'],
        'child_birth': ['child', 'baby', 'birth', 'born', 'kid'],
        'career_change': ['career', 'job', 'profession', 'work', 'promotion'],
        'relocation': ['move', 'moved', 'relocation', 'changed city', 'changed country'],
        'health_crisis': ['health', 'illness', 'disease', 'diagnosis', 'hospitalized']
    }

    # Extract dates using regex patterns
    date_patterns = [
        r'(?:in|on|around)\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}',
        r'(?:in|on|around)\s+\d{4}',
        r'\d{4}'
    ]

    for answer in answers:
        answer_text = answer.get('answer', '').lower()
        if not answer_text or answer_text in ['no', 'none', 'n/a']:
            continue

        # Identify event type
        identified_event = None
        confidence = 0.5  # Default confidence

        for event_type, keywords in event_keywords.items():
            if any(keyword in answer_text for keyword in keywords):
                identified_event = event_type
                # More keywords = higher confidence
                matches = sum(1 for keyword in keywords if keyword in answer_text)
                confidence = min(1.0, 0.5 + 0.1 * matches)
                break

        if not identified_event:
            continue

        # Extract date
        event_date = None
        for pattern in date_patterns:
            date_matches = re.findall(pattern, answer_text)
            if date_matches:
                date_str = date_matches[0]

                # Remove prefixes like "in" or "on"
                date_str = re.sub(r'^(?:in|on|around)\s+', '', date_str)

                try:
                    # Handle different date formats
                    if re.match(r'\d{4}$', date_str):
                        # Just a year
                        event_date = datetime(int(date_str), 6, 15)  # Mid-year as default
                    else:
                        # Month and year
                        month_map = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }

                        month_str = re.search(r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)', date_str, re.IGNORECASE)
                        year_str = re.search(r'(\d{4})', date_str)

                        if month_str and year_str:
                            month = month_map.get(month_str.group(1)[:3].lower(), 1)
                            year = int(year_str.group(1))
                            event_date = datetime(year, month, 15)  # Middle of month as default
                except Exception as e:
                    logger.warning(f"Failed to parse date '{date_str}': {e}")
                    continue

                break

        if event_date:
            life_events.append({
                'event_type': identified_event,
                'event_date': event_date,
                'confidence': confidence
            })

    return life_events

def get_score(candidate_score_tuple: Tuple[datetime, float]) -> float:
    """Extract the score from a (datetime, score) tuple for sorting."""
    return float(candidate_score_tuple[1])

async def rectify_birth_time(
    birth_dt: datetime,
    latitude: Union[float, int],
    longitude: Union[float, int],
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

    if not FLATLIB_AVAILABLE:
        logger.warning("Flatlib is not available. Cannot perform accurate rectification.")
        return birth_dt, 30.0  # Return original time with very low confidence

    # If no answers provided, we cannot do any accurate rectification
    if not answers or len(answers) == 0:
        logger.info("No answers provided. Cannot perform accurate rectification.")
        return birth_dt, 50.0  # Return original time with low confidence

    # Extract life events from answers
    life_events = extract_life_events_from_answers(answers)

    # Generate candidate birth times to test (60-minute window in 5-minute increments)
    time_window = 60  # minutes
    time_step = 5  # minutes
    candidate_times = []

    for minutes_offset in range(-time_window, time_window + 1, time_step):
        candidate_time = birth_dt + timedelta(minutes=minutes_offset)
        candidate_times.append(candidate_time)

    # Calculate scores for each candidate time
    candidate_scores = []

    for candidate_time in candidate_times:
        try:
            chart = calculate_chart(candidate_time, latitude, longitude, timezone)
            if chart is None:
                continue

            # Initialize score for this candidate
            total_score = 0.0

            # Process each life event
            for event in life_events:
                event_type = event.get('event_type')
                event_confidence = event.get('confidence', 1.0)

                if event_type and event_type in LIFE_EVENT_MAPPING:
                    # Score based on natal chart's alignment with this event type
                    event_score = score_chart_for_event(chart, event_type) * event_confidence
                    total_score += event_score

            # Additional scoring based on chart sensitivity to time
            # Check ascendant and midheaven positions
            asc = chart.getAngle(const.ASC)
            mc = chart.getAngle(const.MC)

            # Charts with ascendant near sign boundaries or critical degrees are more time-sensitive
            asc_sensitivity = 0.0
            if asc.lon % 30 < 3 or asc.lon % 30 > 27:  # Near sign boundary
                asc_sensitivity = 10.0
            elif asc.lon % 10 < 1 or asc.lon % 10 > 9:  # Near critical degree
                asc_sensitivity = 5.0

            total_score += asc_sensitivity

            candidate_scores.append((candidate_time, total_score))
        except Exception as e:
            logger.error(f"Error calculating chart for {candidate_time}: {str(e)}")
            continue

    # Find the best candidate time
    if not candidate_scores:
        logger.warning("No valid candidate times found")
        return birth_dt, 50.0

    # Sort by score (highest first)
    candidate_scores.sort(key=get_score, reverse=True)

    # Calculate confidence based on how much better the best time is compared to others
    best_time, best_score = candidate_scores[0]

    # No valid scores found
    if best_score == 0:
        logger.warning("No significant astrological patterns found in any candidate time")
        return birth_dt, 50.0

    # Calculate average score of all candidates
    avg_score = sum(score for _, score in candidate_scores) / len(candidate_scores)

    # Calculate confidence (50-95%)
    if avg_score > 0:
        score_ratio = best_score / avg_score
        confidence = min(95.0, 50.0 + (score_ratio - 1) * 30.0)
    else:
        confidence = 50.0

    logger.info(f"Rectified time: {best_time}, confidence: {confidence}, score: {best_score}")

    return best_time, confidence

async def analyze_life_events(
    events: List[Dict[str, Any]],
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: Optional[str] = None
) -> Tuple[datetime, float]:
    """
    Analyze life events to rectify birth time using real astrological calculations.

    Args:
        events: List of life events with dates and descriptions
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: Timezone string (optional, will be detected if not provided)

    Returns:
        Tuple containing (rectified_datetime, confidence_score)
    """
    logger.info(f"Analyzing {len(events)} life events for birth time rectification")

    if not FLATLIB_AVAILABLE:
        logger.warning("Flatlib is not available. Cannot perform transit analysis.")
        return birth_dt, 30.0  # Return original time with very low confidence

    # Get timezone if not provided
    if not timezone:
        if TIMEZONEFINDER_AVAILABLE:
            tf = TimezoneFinder()
            timezone = tf.timezone_at(lat=latitude, lng=longitude) or "UTC"
        else:
            logger.warning("TimezoneFinder not available. Using UTC as fallback.")
            timezone = "UTC"

    # Ensure timezone is a string
    timezone_str = str(timezone) if timezone else "UTC"

    # Calculate the natal chart
    natal_chart = calculate_chart(birth_dt, latitude, longitude, timezone_str)
    if natal_chart is None:
        return birth_dt, 30.0

    # Generate candidate birth times to test
    time_window = 90  # minutes
    time_step = 5     # minutes
    candidate_times = []

    for minutes_offset in range(-time_window, time_window + 1, time_step):
        candidate_time = birth_dt + timedelta(minutes=minutes_offset)
        candidate_times.append(candidate_time)

    # Calculate transit scores for each event at each candidate time
    candidate_scores = []

    for candidate_time in candidate_times:
        try:
            # Calculate candidate natal chart
            candidate_chart = calculate_chart(candidate_time, latitude, longitude, timezone_str)
            if candidate_chart is None:
                continue

            # Total score for this candidate across all events
            total_score = 0.0

            # Process each life event
            for event in events:
                event_type = event.get('event_type')
                event_date = event.get('event_date')

                if not event_date:
                    continue

                # Calculate transit chart for this event
                transit_chart = calculate_chart(event_date, latitude, longitude, timezone_str)
                if transit_chart is None:
                    continue

                # Check transit-to-natal aspects
                transit_score = 0.0

                # Check each transiting planet against natal planets
                for transit_planet in const.LIST_PLANETS:
                    tr_planet_obj = transit_chart.getObject(transit_planet)

                    for natal_planet in const.LIST_PLANETS:
                        natal_planet_obj = candidate_chart.getObject(natal_planet)

                        for aspect_type in ['conjunction', 'opposition', 'trine', 'square']:
                            if is_aspect_active(tr_planet_obj.lon, natal_planet_obj.lon, aspect_type):
                                # Assign score based on aspect significance for this event type
                                aspect_score = 2.0  # Default score

                                # Check if this aspect is significant for this event type
                                if event_type and event_type in LIFE_EVENT_MAPPING:
                                    for factor in LIFE_EVENT_MAPPING.get(event_type, []):
                                        if ('planet1' in factor and 'planet2' in factor and 'aspect' in factor and
                                            ((factor.get('planet1') == transit_planet and factor.get('planet2') == natal_planet) or
                                             (factor.get('planet1') == natal_planet and factor.get('planet2') == transit_planet)) and
                                            factor.get('aspect') == aspect_type):
                                                aspect_score = 10.0  # Significant match
                                                break

                                transit_score += aspect_score

                # Check transits to houses
                if event_type and event_type in LIFE_EVENT_MAPPING:
                    for factor in LIFE_EVENT_MAPPING.get(event_type, []):
                        if 'house' in factor:
                            house_num = factor.get('house', 1)
                            house = candidate_chart.getHouse(house_num)

                            # Check each transiting planet in this house
                            for transit_planet in const.LIST_PLANETS:
                                tr_planet_obj = transit_chart.getObject(transit_planet)
                                if house.hasObject(tr_planet_obj):
                                    transit_score += 8.0  # Significant house transit

                # Add this event's score to the total
                event_confidence = event.get('confidence', 1.0)
                total_score += transit_score * event_confidence

            candidate_scores.append((candidate_time, total_score))

        except Exception as e:
            logger.error(f"Error analyzing transits for {candidate_time}: {str(e)}")
            continue

    # Find the best candidate time
    if not candidate_scores:
        logger.warning("No valid candidate times found in transit analysis")
        return birth_dt, 50.0

    # Sort by score (highest first)
    candidate_scores.sort(key=get_score, reverse=True)

    # Get the best time and score
    best_time, best_score = candidate_scores[0]

    # No valid scores found
    if best_score == 0:
        logger.warning("No significant transit patterns found in any candidate time")
        return birth_dt, 50.0

    # Calculate average score of all candidates
    avg_score = sum(score for _, score in candidate_scores) / len(candidate_scores)

    # Calculate confidence (50-95%)
    if avg_score > 0:
        score_ratio = best_score / avg_score
        confidence = min(95.0, 60.0 + (score_ratio - 1) * 25.0)
    else:
        confidence = 60.0

    # Add confidence based on number of events (more events = higher confidence)
    events_factor = min(10.0, len(events) * 2.0)
    confidence = min(95.0, confidence + events_factor)

    logger.info(f"Transit-based rectified time: {best_time}, confidence: {confidence}, score: {best_score}")

    return best_time, confidence

async def comprehensive_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    answers: List[Dict[str, Any]],
    events: Optional[List[Dict[str, Any]]] = None
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

    Returns:
        Dictionary with rectification results
    """
    if not FLATLIB_AVAILABLE:
        logger.warning("Flatlib is not available. Cannot perform accurate rectification.")
        return {
            "rectified_time": birth_dt,
            "confidence": 30.0,
            "explanation": "Rectification libraries are not available. Using original birth time.",
            "adjustment_minutes": 0,
            "methods_used": [],
            "life_events_analyzed": 0
        }

    # Extract life events from answers if not provided
    if not events:
        events = extract_life_events_from_answers(answers)

    # Perform basic rectification using questionnaire answers
    basic_time, basic_confidence = await rectify_birth_time(
        birth_dt, latitude, longitude, timezone, answers
    )

    # Perform detailed analysis using life events if available
    if events and len(events) > 0:
        transit_time, transit_confidence = await analyze_life_events(
            events, birth_dt, latitude, longitude, timezone
        )

        # Weight the results based on confidence
        if transit_confidence > basic_confidence:
            # Transit analysis is more confident
            weight_transit = 0.7
            weight_basic = 0.3
        else:
            # Basic analysis is more confident
            weight_transit = 0.3
            weight_basic = 0.7

        # Calculate time difference in minutes
        basic_minutes = basic_time.hour * 60 + basic_time.minute
        transit_minutes = transit_time.hour * 60 + transit_time.minute

        # Weighted average of minutes
        combined_minutes = int(round(
            (basic_minutes * weight_basic + transit_minutes * weight_transit) /
            (weight_basic + weight_transit)
        ))

        # Convert back to hours and minutes
        combined_hours = combined_minutes // 60
        combined_minutes = combined_minutes % 60

        # Create combined rectified time
        combined_time = birth_dt.replace(hour=combined_hours, minute=combined_minutes)

        # Combined confidence (weighted average)
        combined_confidence = (
            basic_confidence * weight_basic + transit_confidence * weight_transit
        ) / (weight_basic + weight_transit)
    else:
        # No events available, use basic rectification only
        combined_time = basic_time
        combined_confidence = basic_confidence

    # Generate explanation
    time_diff = combined_time - birth_dt
    minutes_diff = int(time_diff.total_seconds() / 60)

    explanation = (
        f"Birth time rectified using astrological calculations with "
        f"{len(answers)} questionnaire responses"
    )

    if events:
        explanation += f" and {len(events)} life events"

    explanation += (
        f". The original time was adjusted by {abs(minutes_diff)} minutes "
        f"{'earlier' if minutes_diff < 0 else 'later'} based on "
        f"planetary positions, aspects, and house placements."
    )

    return {
        "rectified_time": combined_time,
        "confidence": combined_confidence,
        "explanation": explanation,
        "adjustment_minutes": minutes_diff,
        "methods_used": ["questionnaire_analysis", "transit_analysis" if events else None],
        "life_events_analyzed": len(events) if events else 0
    }
