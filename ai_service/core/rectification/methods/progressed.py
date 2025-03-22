"""
Progressed chart rectification method for birth time adjustment.
"""
import logging
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, List, Optional

logger = logging.getLogger(__name__)

async def progressed_ascendant_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str
) -> Tuple[datetime, float]:
    """
    Perform rectification using progressed ascendant.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: Timezone string

    Returns:
        Tuple of (rectified_datetime, confidence_score)
    """
    from ..chart_calculator import calculate_chart

    # Define test times to check (within 2 hours before and after the given time)
    test_times = []

    # Check every 15 minutes within a 4-hour window
    for minutes in range(-120, 121, 15):
        test_time = birth_dt + timedelta(minutes=minutes)
        test_times.append(test_time)

    # Track the best score and corresponding time
    best_score = 0
    best_time = birth_dt

    # Calculate current age
    current_date = datetime.now()
    age = current_date.year - birth_dt.year
    if (current_date.month, current_date.day) < (birth_dt.month, birth_dt.day):
        age -= 1

    # Evaluate each test time
    for test_time in test_times:
        try:
            # Calculate chart for this test time
            chart = calculate_chart(test_time, latitude, longitude, timezone)

            # Skip if chart calculation failed
            if not chart:
                continue

            # Calculate score based on progressions
            score = 0

            # For each age from 0 to current age, calculate progressions
            for age_year in range(age + 1):
                try:
                    # One day for each year of life in secondary progressions
                    progression_date = test_time + timedelta(days=age_year)

                    # Calculate progressed chart
                    progressed_chart = calculate_chart(progression_date, latitude, longitude, timezone)
                    if not progressed_chart:
                        continue

                    # Get progressed angles
                    prog_asc_data = progressed_chart.get("angles", {}).get("asc")
                    prog_mc_data = progressed_chart.get("angles", {}).get("mc")

                    # Get natal planets
                    natal_planets = {}
                    for planet_key in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']:
                        planet_key_lower = planet_key.lower()
                        if "planets" in chart and planet_key_lower in chart["planets"]:
                            natal_planets[planet_key] = chart["planets"][planet_key_lower]

                    # Calculate aspects between progressed angles and natal planets
                    for planet_key, planet_data in natal_planets.items():
                        try:
                            planet_longitude = planet_data.get("longitude")

                            # Check aspects to Ascendant
                            if prog_asc_data and "longitude" in prog_asc_data:
                                asc_longitude = prog_asc_data["longitude"]
                                aspect_angle = abs(planet_longitude - asc_longitude) % 360
                                if aspect_angle > 180:
                                    aspect_angle = 360 - aspect_angle

                                # Score major aspects
                                if abs(aspect_angle - 0) < 3:  # Conjunction
                                    score += 12
                                elif abs(aspect_angle - 90) < 3:  # Square
                                    score += 8
                                elif abs(aspect_angle - 180) < 3:  # Opposition
                                    score += 10
                                elif abs(aspect_angle - 120) < 3:  # Trine
                                    score += 6
                                elif abs(aspect_angle - 60) < 3:  # Sextile
                                    score += 4

                            # Check aspects to Midheaven
                            if prog_mc_data and "longitude" in prog_mc_data:
                                mc_longitude = prog_mc_data["longitude"]
                                aspect_angle = abs(planet_longitude - mc_longitude) % 360
                                if aspect_angle > 180:
                                    aspect_angle = 360 - aspect_angle

                                # Score major aspects
                                if abs(aspect_angle - 0) < 3:  # Conjunction
                                    score += 12
                                elif abs(aspect_angle - 90) < 3:  # Square
                                    score += 8
                                elif abs(aspect_angle - 180) < 3:  # Opposition
                                    score += 10
                                elif abs(aspect_angle - 120) < 3:  # Trine
                                    score += 6
                                elif abs(aspect_angle - 60) < 3:  # Sextile
                                    score += 4

                        except Exception as e:
                            logger.debug(f"Error checking aspects for planet {planet_key}: {e}")
                            continue

                except Exception as e:
                    logger.debug(f"Error calculating progression for age {age_year}: {e}")
                    continue

            # Check if this is the best score so far
            if score > best_score:
                best_score = score
                best_time = test_time

        except Exception as e:
            logger.error(f"Error in progression calculation: {e}")
            continue

    # Calculate confidence based on score (50-85% range)
    confidence = min(85, 50 + (best_score / 120) * 35)

    logger.info(f"Progressed ascendant rectification result: {best_time}, confidence: {confidence}")
    return best_time, confidence
