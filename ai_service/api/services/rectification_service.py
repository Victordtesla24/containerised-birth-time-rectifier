"""
Birth Time Rectification Service

This module provides services for birth time rectification using astrological
algorithms and AI-based approaches with real calculations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
try:
    import pytz
except ImportError:
    logging.warning("pytz module not found. Some timezone functions may not work correctly.")
    # Define a minimal pytz fallback
    class FakePytz:
        class TimezoneClass:
            @staticmethod
            def utcoffset(dt):
                return datetime.utcnow() - dt

        @staticmethod
        def timezone(tz_str):
            return FakePytz.TimezoneClass()

    pytz = FakePytz()
import math
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib.chart import Chart
from flatlib import const
from flatlib.dignities import essential
import numpy as np
from timezonefinder import TimezoneFinder

# Use the new modularized structure
from ai_service.core.rectification.chart_calculator import calculate_chart
from ai_service.core.rectification.constants import PLANETS_LIST

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

def calculate_chart_for_time(birth_date: datetime, latitude: float, longitude: float, timezone_str: str) -> Chart:
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

def get_house_planet_connections(chart: Chart, house_num: int) -> List[Dict[str, Any]]:
    """
    Get all planets in or aspecting a specific house.

    Args:
        chart: Flatlib Chart object
        house_num: House number (1-12)

    Returns:
        List of planet objects connected to this house
    """
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

def get_planet_aspects(chart: Chart, planet1_name: str, planet2_name: str) -> List[Dict[str, Any]]:
    """
    Get all aspects between two planets.

    Args:
        chart: Flatlib Chart object
        planet1_name: First planet name
        planet2_name: Second planet name

    Returns:
        List of aspect details
    """
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

def score_chart_for_event(chart: Chart, event_type: str) -> float:
    """
    Score a chart for a specific life event.

    Args:
        chart: Flatlib Chart object
        event_type: Type of life event (marriage, divorce, etc.)

    Returns:
        Score indicating how well the chart aligns with the event
    """
    total_score = 0.0
    event_factors = LIFE_EVENT_MAPPING.get(event_type, [])

    # Check all event factors
    for factor in event_factors:
        if 'house' in factor:
            # Check house connections
            house_connections = get_house_planet_connections(chart, factor['house'])
            for connection in house_connections:
                total_score += connection['strength']
        else:
            # Check planet aspects
            aspects = get_planet_aspects(chart, factor['planet1'], factor['planet2'])
            for aspect in aspects:
                if aspect['aspect_type'] == factor['aspect']:
                    total_score += aspect['strength']

    return total_score

async def rectify_birth_time(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    answers: List[Dict[str, Any]]
) -> Tuple[datetime, float]:
    """
    Birth time rectification algorithm using astrological factors.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth location latitude
        longitude: Birth location longitude
        timezone: Birth location timezone
        answers: List of questionnaire answers with life events

    Returns:
        Tuple of (rectified_time, confidence)
    """
    logger.info(f"Rectifying birth time for {birth_dt} at {latitude}, {longitude}")

    # Generate candidate birth times to test (30-minute window in 5-minute increments)
    time_window = 30  # minutes
    time_step = 5  # minutes
    candidate_times = []

    for minutes_offset in range(-time_window, time_window + 1, time_step):
        candidate_time = birth_dt + timedelta(minutes=minutes_offset)
        candidate_times.append(candidate_time)

    # Calculate scores for each candidate time
    candidate_scores = []

    for candidate_time in candidate_times:
        try:
            chart = calculate_chart_for_time(candidate_time, latitude, longitude, timezone)

            # Initialize score for this candidate
            total_score = 0.0

            # Process each answer/life event
            for answer in answers:
                event_type = answer.get('event_type')
                event_date = answer.get('event_date')
                confidence = answer.get('confidence', 1.0)

                if event_type and event_type in LIFE_EVENT_MAPPING:
                    # Score based on natal chart's alignment with this event type
                    event_score = score_chart_for_event(chart, event_type) * confidence
                    total_score += event_score

            candidate_scores.append((candidate_time, total_score))
        except Exception as e:
            logger.error(f"Error calculating chart for {candidate_time}: {str(e)}")
            continue

    # Find the best candidate time
    if not candidate_scores:
        logger.warning("No valid candidate times found")
        return birth_dt, 50.0

    # Sort by score (highest first)
    candidate_scores.sort(key=lambda x: x[1], reverse=True)

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

class EnhancedRectificationService:
    """
    Enhanced birth time rectification service using AI analysis
    and astrological calculations.
    """

    def __init__(self):
        """Initialize the enhanced rectification service."""
        logger.info("Initializing EnhancedRectificationService")
        self.tf = TimezoneFinder()

    def get_timezone_from_coordinates(self, latitude: float, longitude: float) -> str:
        """
        Get timezone string from coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            Timezone string
        """
        timezone_str = self.tf.timezone_at(lat=latitude, lng=longitude)
        return timezone_str or "UTC"

    def calculate_transits_for_event(self, birth_chart: Chart, event_date: datetime,
                                  latitude: float, longitude: float, timezone: str) -> Dict[str, Any]:
        """
        Calculate transit chart for a specific event date and analyze aspects to natal chart.

        Args:
            birth_chart: Natal chart
            event_date: Date of the event
            latitude: Event location latitude
            longitude: Event location longitude
            timezone: Event location timezone

        Returns:
            Transit analysis results
        """
        # Calculate transit chart
        transit_chart = calculate_chart_for_time(event_date, latitude, longitude, timezone)

        # Check aspects between transit planets and natal planets
        transit_aspects = []

        for transit_planet in const.LIST_PLANETS:
            tr_planet_obj = transit_chart.getObject(transit_planet)

            for natal_planet in const.LIST_PLANETS:
                natal_planet_obj = birth_chart.getObject(natal_planet)

                for aspect_type in ASPECT_ORBS.keys():
                    if is_aspect_active(tr_planet_obj.lon, natal_planet_obj.lon, aspect_type):
                        # Calculate orb
                        target_angle = get_aspect_angle(aspect_type)
                        diff = abs(tr_planet_obj.lon - natal_planet_obj.lon) % 360
                        if diff > 180:
                            diff = 360 - diff
                        actual_orb = abs(diff - target_angle)

                        transit_aspects.append({
                            'transit_planet': transit_planet,
                            'natal_planet': natal_planet,
                            'aspect_type': aspect_type,
                            'orb': actual_orb
                        })

        # Check transit planets in natal houses
        transit_house_placements = []

        for transit_planet in const.LIST_PLANETS:
            tr_planet_obj = transit_chart.getObject(transit_planet)

            for house_num in range(1, 13):
                house = birth_chart.getHouse(house_num)
                if house.hasObject(tr_planet_obj):
                    transit_house_placements.append({
                        'transit_planet': transit_planet,
                        'natal_house': house_num
                    })

        return {
            'transit_aspects': transit_aspects,
            'transit_house_placements': transit_house_placements
        }

    def analyze_major_events(self, birth_dt: datetime, latitude: float, longitude: float,
                           timezone: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze major life events against the birth chart.

        Args:
            birth_dt: Birth datetime
            latitude: Birth location latitude
            longitude: Birth location longitude
            timezone: Birth location timezone
            events: List of major life events with dates

        Returns:
            Analysis results
        """
        birth_chart = calculate_chart_for_time(birth_dt, latitude, longitude, timezone)

        event_analyses = []

        for event in events:
            event_type = event.get('event_type')
            event_date = event.get('event_date')
            event_location = event.get('location', {})

            if not event_date:
                continue

            # Use birth location if event location not provided
            event_lat = event_location.get('latitude', latitude)
            event_lon = event_location.get('longitude', longitude)
            event_timezone = event_location.get('timezone', timezone)

            # Calculate transits for this event
            transit_analysis = self.calculate_transits_for_event(
                birth_chart, event_date, event_lat, event_lon, event_timezone)

            # Score this event against expected astrological patterns
            if event_type and isinstance(event_type, str):
                event_score = score_chart_for_event(birth_chart, event_type)
            else:
                event_score = 0.0

            # Add results to list
            event_analyses.append({
                'event_type': event_type,
                'event_date': event_date,
                'transit_analysis': transit_analysis,
                'event_score': event_score
            })

        return {
            'birth_chart_data': {
                'ascendant': birth_chart.getAngle(const.ASC).sign,
                'mc': birth_chart.getAngle(const.MC).sign,
                'sun_sign': birth_chart.getObject(const.SUN).sign,
                'moon_sign': birth_chart.getObject(const.MOON).sign
            },
            'event_analyses': event_analyses
        }

    def evaluate_birth_time_candidates(self, start_time: datetime, end_time: datetime,
                                    step_minutes: int, latitude: float, longitude: float,
                                    timezone: str, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate multiple birth time candidates against life events.

        Args:
            start_time: Start of birth time range
            end_time: End of birth time range
            step_minutes: Time step in minutes
            latitude: Birth location latitude
            longitude: Birth location longitude
            timezone: Birth location timezone
            events: List of life events with dates

        Returns:
            List of scored birth time candidates
        """
        candidates = []

        current_time = start_time
        while current_time <= end_time:
            try:
                # Calculate birth chart
                birth_chart = calculate_chart_for_time(current_time, latitude, longitude, timezone)

                # Calculate total score for all events
                total_score = 0.0

                for event in events:
                    event_type = event.get('event_type')
                    confidence = event.get('confidence', 1.0)

                    if event_type and isinstance(event_type, str) and event_type in LIFE_EVENT_MAPPING:
                        event_score = score_chart_for_event(birth_chart, event_type) * confidence
                        total_score += event_score

                # Add this candidate to the list
                candidates.append({
                    'birth_time': current_time,
                    'score': total_score,
                    'ascendant': birth_chart.getAngle(const.ASC).sign,
                    'mc': birth_chart.getAngle(const.MC).sign,
                    'sun_sign': birth_chart.getObject(const.SUN).sign,
                    'moon_sign': birth_chart.getObject(const.MOON).sign
                })
            except Exception as e:
                logger.error(f"Error evaluating birth time {current_time}: {str(e)}")

            # Move to next time step
            current_time += timedelta(minutes=step_minutes)

        # Sort by score (highest first)
        candidates.sort(key=lambda x: x['score'], reverse=True)

        return candidates

    async def rectify(self, **kwargs):
        """
        Enhanced birth time rectification algorithm.

        Args:
            birth_dt: Original birth datetime
            latitude: Birth location latitude
            longitude: Birth location longitude
            timezone: Birth location timezone
            answers: List of questionnaire answers
            constraints: Optional birth time range constraints

        Returns:
            Dict containing rectified_time, confidence, and explanation
        """
        return await self.process_rectification(**kwargs)

    async def process_rectification(
        self,
        birth_dt: datetime,
        latitude: float,
        longitude: float,
        timezone: str,
        answers: List[Dict[str, Any]],
        constraints: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced birth time rectification algorithm using astrological calculations.

        Args:
            birth_dt: Original birth datetime
            latitude: Birth location latitude
            longitude: Birth location longitude
            timezone: Birth location timezone
            answers: List of questionnaire answers
            constraints: Optional birth time range constraints

        Returns:
            Dict containing rectified_time, confidence, and explanation
        """
        logger.info(f"Enhanced rectification for {birth_dt} at {latitude}, {longitude}")

        # Apply constraints if provided
        min_hour = constraints.get("min_hours", 0) if constraints else 0
        min_minute = constraints.get("min_minutes", 0) if constraints else 0
        max_hour = constraints.get("max_hours", 23) if constraints else 23
        max_minute = constraints.get("max_minutes", 59) if constraints else 59

        # Create start and end times based on constraints
        start_time = birth_dt.replace(hour=min_hour, minute=min_minute)
        end_time = birth_dt.replace(hour=max_hour, minute=max_minute)

        # If date changes, ensure we're still in the same day
        if end_time < start_time:
            end_time = end_time.replace(day=start_time.day)

        # Evaluate birth time candidates
        step_minutes = 10  # 10-minute steps for comprehensive analysis

        # Extract life events from answers
        events = []
        for answer in answers:
            if 'event_type' in answer and 'event_date' in answer:
                events.append(answer)

        candidates = self.evaluate_birth_time_candidates(
            start_time, end_time, step_minutes, latitude, longitude, timezone, events)

        # No valid candidates
        if not candidates:
            logger.warning("No valid birth time candidates found")
            return {
                "rectified_time": birth_dt,
                "confidence": 50.0,
                "explanation": "Unable to determine a rectified birth time based on the provided information."
            }

        # Get the best candidate
        best_candidate = candidates[0]

        # Calculate confidence based on score distribution
        if len(candidates) > 1:
            best_score = best_candidate['score']
            avg_score = sum(c['score'] for c in candidates) / len(candidates)

            if avg_score > 0:
                score_ratio = best_score / avg_score
                confidence = min(95.0, 60.0 + (score_ratio - 1) * 25.0)
            else:
                confidence = 60.0
        else:
            confidence = 60.0

        # Create explanation
        rectified_time = best_candidate['birth_time']
        time_diff = rectified_time - birth_dt
        hours_diff = time_diff.total_seconds() / 3600

        if abs(hours_diff) < 0.01:  # Less than 1 minute difference
            explanation = "Analysis confirms the original birth time is accurate."
        else:
            # Format time difference
            if abs(hours_diff) >= 1:
                hours = int(abs(hours_diff))
                minutes = int((abs(hours_diff) - hours) * 60)
                time_diff_str = f"{hours} hour{'s' if hours > 1 else ''} and {minutes} minute{'s' if minutes > 1 else ''}"
            else:
                minutes = int(abs(hours_diff) * 60)
                time_diff_str = f"{minutes} minute{'s' if minutes > 1 else ''}"

            direction = "earlier" if hours_diff < 0 else "later"

            explanation = (
                f"Birth time adjusted {time_diff_str} {direction} "
                f"based on {len(answers)} questionnaire answers. The rectified time aligns "
                f"better with reported life events and planetary positions. "
                f"Ascendant: {best_candidate['ascendant']}, "
                f"Midheaven: {best_candidate['mc']}."
            )

        logger.info(f"Enhanced rectified time: {rectified_time}, confidence: {confidence}")

        return {
            "rectified_time": rectified_time,
            "confidence": confidence,
            "explanation": explanation
        }
