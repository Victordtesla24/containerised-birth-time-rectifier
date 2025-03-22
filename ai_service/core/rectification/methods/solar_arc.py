"""
Solar arc rectification method for birth time adjustment.
"""
import logging
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, List, Optional

logger = logging.getLogger(__name__)

async def solar_arc_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str
) -> Tuple[datetime, float]:
    """
    Perform solar arc-based birth time rectification.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: Timezone string

    Returns:
        Tuple of (rectified_datetime, confidence_score)
    """
    from ..chart_calculator import calculate_chart

    logger.info("Using solar arc directions for rectification")

    # Define test times to check (within 2 hours before and after the given time)
    test_times = []

    # Check every 15 minutes within a 4-hour window
    for minutes in range(-120, 121, 15):
        test_time = birth_dt + timedelta(minutes=minutes)
        test_times.append(test_time)

    # Track the best score and corresponding time
    best_score = 0
    best_time = birth_dt

    # Evaluate each test time
    for test_time in test_times:
        try:
            # Calculate chart for this test time
            chart_data = calculate_chart(test_time, latitude, longitude, timezone)

            # Skip if chart calculation failed
            if not chart_data:
                continue

            # Calculate score based on solar arc aspects
            score = 0

            # Check for important solar arc directional aspects
            try:
                # Get the ascendant and midheaven longitudes
                ascendant_lon = None
                midheaven_lon = None

                if "angles" in chart_data:
                    if "asc" in chart_data["angles"]:
                        ascendant_lon = chart_data["angles"]["asc"].get("longitude")
                    if "mc" in chart_data["angles"]:
                        midheaven_lon = chart_data["angles"]["mc"].get("longitude")

                if not ascendant_lon or not midheaven_lon:
                    continue  # Skip if we can't find the angles

                # Check aspects to Ascendant and Midheaven
                for planet_name in ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn']:
                    if planet_name not in chart_data.get("planets", {}):
                        continue

                    planet_lon = chart_data["planets"][planet_name].get("longitude")
                    if not planet_lon:
                        continue

                    # Calculate aspect angle to Ascendant
                    aspect_angle = abs(planet_lon - ascendant_lon) % 360
                    if aspect_angle > 180:
                        aspect_angle = 360 - aspect_angle

                    # Score based on harmonious or challenging aspects
                    if abs(aspect_angle - 0) < 3:  # Conjunction
                        score += 10
                    elif abs(aspect_angle - 60) < 3:  # Sextile
                        score += 6
                    elif abs(aspect_angle - 90) < 3:  # Square
                        score += 8
                    elif abs(aspect_angle - 120) < 3:  # Trine
                        score += 8
                    elif abs(aspect_angle - 180) < 3:  # Opposition
                        score += 10

                    # Calculate aspect angle to Midheaven
                    aspect_angle = abs(planet_lon - midheaven_lon) % 360
                    if aspect_angle > 180:
                        aspect_angle = 360 - aspect_angle

                    # Score based on harmonious or challenging aspects
                    if abs(aspect_angle - 0) < 3:  # Conjunction
                        score += 10
                    elif abs(aspect_angle - 60) < 3:  # Sextile
                        score += 6
                    elif abs(aspect_angle - 90) < 3:  # Square
                        score += 8
                    elif abs(aspect_angle - 120) < 3:  # Trine
                        score += 8
                    elif abs(aspect_angle - 180) < 3:  # Opposition
                        score += 10

            except Exception as e:
                logger.debug(f"Error calculating aspects: {e}")
                continue

            # Check if this is the best score so far
            if score > best_score:
                best_score = score
                best_time = test_time

        except Exception as e:
            logger.debug(f"Error in solar arc calculation: {e}")
            continue

    # If no good candidates were found, return the original time with low confidence
    if best_score == 0:
        logger.info("No significant solar arc patterns found, returning original birth time")
        return birth_dt, 50.0

    # Calculate confidence based on score (50-85% range)
    confidence = min(85, 50 + (best_score / 60) * 35)

    logger.info(f"Solar arc rectification result: {best_time}, confidence: {confidence}")
    return best_time, confidence
