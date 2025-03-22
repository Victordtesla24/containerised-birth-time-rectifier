"""
Transit analysis module for birth time rectification using life events.
"""
import logging
from datetime import datetime, timedelta
import re
from typing import List, Dict, Any, Tuple, Optional, Union

logger = logging.getLogger(__name__)

def calculate_transit_score(
    natal_chart: Any,
    transit_chart: Any,
    event_type: str,
    description: str = ""
) -> Tuple[float, int]:
    """
    Calculate transit score for an event.

    Args:
        natal_chart: The natal chart object
        transit_chart: The transit chart object
        event_type: Type of life event
        description: Event description

    Returns:
        Tuple of (score, aspect_count)
    """
    from ..constants import LIFE_EVENT_MAPPING

    # Get relevant planets and points for this event type
    relevant_points = LIFE_EVENT_MAPPING.get(event_type, [])

    # If no specific mappings for this event type, use common points
    if not relevant_points:
        relevant_points = ['Sun', 'Moon', 'Ascendant', 'MC']

    # Track score and aspect count
    score = 0.0
    aspect_count = 0

    # Check transits to each relevant point
    for point in relevant_points:
        try:
            # Handle special case for houses
            if point.endswith('_house'):
                try:
                    # Extract house number, handling ordinal suffixes like '3rd', '9th', etc.
                    house_part = point.split('_')[0]
                    # Remove any non-numeric characters to get just the number
                    house_num = int(''.join(filter(str.isdigit, house_part)))

                    # Check if house data exists
                    if "houses" in natal_chart and isinstance(natal_chart["houses"], list) and house_num <= len(natal_chart["houses"]):
                        house_lon = natal_chart["houses"][house_num - 1]

                        # Check transits to this house
                        for planet in ['sun', 'moon', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']:
                            if "planets" in transit_chart and planet in transit_chart["planets"]:
                                transit_planet_data = transit_chart["planets"][planet]
                                transit_planet_lon = transit_planet_data.get("longitude", 0)

                                # Simple check if planet is in or near the house (within 10 degrees)
                                house_start = house_lon
                                house_end = natal_chart["houses"][house_num % 12] if house_num < 12 else (house_lon + 30) % 360

                                if house_end < house_start:  # Handle case where house crosses 0 degrees
                                    in_house = (transit_planet_lon >= house_start or transit_planet_lon < house_end)
                                else:
                                    in_house = (transit_planet_lon >= house_start and transit_planet_lon < house_end)

                                if in_house:
                                    score += 10.0
                                    aspect_count += 1
                except Exception as e:
                    logger.warning(f"Error evaluating transit to {point}: {e}")
                    continue

            # Handle regular points (planets, angles)
            else:
                # Get natal position
                natal_point_lon = None
                natal_point_data = None

                if point in ['Ascendant', 'Asc', 'MC', 'Descendant', 'IC']:
                    # Map to correct key
                    angle_key = point.lower()
                    if point == 'Ascendant':
                        angle_key = 'asc'
                    elif point == 'Descendant':
                        angle_key = 'desc'

                    # Get angle data
                    if "angles" in natal_chart and angle_key in natal_chart["angles"]:
                        natal_point_data = natal_chart["angles"][angle_key]
                        natal_point_lon = natal_point_data.get("longitude")
                else:
                    # It's a planet
                    planet_key = point.lower()
                    if "planets" in natal_chart and planet_key in natal_chart["planets"]:
                        natal_point_data = natal_chart["planets"][planet_key]
                        natal_point_lon = natal_point_data.get("longitude")

                # Skip if point is not valid
                if natal_point_lon is None:
                    continue

                # Check transits from major planets
                transit_planets = ['sun', 'moon', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']

                for transit_planet_name in transit_planets:
                    if "planets" in transit_chart and transit_planet_name in transit_chart["planets"]:
                        transit_planet_data = transit_chart["planets"][transit_planet_name]
                        transit_planet_lon = transit_planet_data.get("longitude")

                        if transit_planet_lon is None:
                            continue

                        # Calculate aspect angle
                        angle_diff = abs(natal_point_lon - transit_planet_lon) % 360
                        if angle_diff > 180:
                            angle_diff = 360 - angle_diff

                        # Score based on aspect type
                        if abs(angle_diff - 0) < 5:  # Conjunction
                            score += 10.0
                            aspect_count += 1
                        elif abs(angle_diff - 180) < 5:  # Opposition
                            score += 10.0
                            aspect_count += 1
                        elif abs(angle_diff - 90) < 5:  # Square
                            score += 8.0
                            aspect_count += 1
                        elif abs(angle_diff - 120) < 5:  # Trine
                            score += 6.0
                            aspect_count += 1
                        elif abs(angle_diff - 60) < 5:  # Sextile
                            score += 5.0
                            aspect_count += 1

        except Exception as e:
            logger.warning(f"Error evaluating transit to {point}: {e}")
            continue

    return score, aspect_count

async def analyze_life_events(
    events: List[Dict[str, Any]],
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone_str: Optional[str] = None
) -> Tuple[datetime, float]:
    """
    Analyze life events and rectify birth time based on transits.

    Args:
        events: List of life events
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone_str: Timezone string

    Returns:
        Tuple of (rectified_datetime, confidence_score)
    """
    from ..chart_calculator import calculate_chart
    import pytz

    # Ensure we have events to analyze
    if not events or len(events) == 0:
        logger.warning("No life events provided for transit analysis")
        return birth_dt, 50.0

    # Default timezone to UTC if not provided
    if timezone_str is None:
        logger.warning("No timezone provided, using UTC for transit analysis")
        timezone_str = "UTC"

    # Define potential birth times to test (every 15 minutes within a 4-hour window)
    test_times = []
    for minutes in range(-120, 121, 15):
        test_time = birth_dt + timedelta(minutes=minutes)
        test_times.append(test_time)

    # Track results for each test time
    results = []

    # Process each test time
    for test_time in test_times:
        try:
            # Calculate natal chart for this test time
            natal_chart = calculate_chart(test_time, latitude, longitude, timezone_str)
            if not natal_chart:
                continue

            # Track total score for this birth time
            total_score = 0.0
            total_aspects = 0
            valid_events = 0

            # Process each life event
            for event in events:
                # Skip events without a date
                event_date_str = event.get('date')
                if not event_date_str or event_date_str == 'unknown':
                    continue

                # Handle case where only a year is provided
                if re.match(r'^\d{4}$', event_date_str):
                    event_date_str = f"{event_date_str}-06-15"  # Default to middle of the year

                # Parse event date
                try:
                    event_date = datetime.fromisoformat(event_date_str)
                except ValueError:
                    try:
                        # Try with fallback format
                        event_date = datetime.strptime(event_date_str, "%Y-%m-%d")
                    except ValueError:
                        # Skip if date can't be parsed
                        continue

                # Use noon time for transit chart if not specified
                if event_date.hour == 0 and event_date.minute == 0:
                    event_date = event_date.replace(hour=12)

                # Calculate transit chart
                transit_chart = calculate_chart(event_date, latitude, longitude, timezone_str)
                if not transit_chart:
                    continue

                # Get event type and description
                event_type = event.get('type', 'life_event')
                description = event.get('description', '')

                # Calculate transit score
                event_score, aspect_count = calculate_transit_score(
                    natal_chart, transit_chart, event_type, description
                )

                # Skip if no aspects found
                if aspect_count == 0:
                    continue

                # Add to totals
                total_score += event_score
                total_aspects += aspect_count
                valid_events += 1

            # Skip if no valid events were analyzed
            if valid_events == 0:
                continue

            # Calculate average score per event
            avg_score = total_score / valid_events

            # Add to results
            results.append((test_time, avg_score, total_aspects, valid_events))

        except Exception as e:
            logger.warning(f"Error analyzing test time {test_time}: {e}")
            continue

    # If no valid results, return original time with low confidence
    if not results:
        logger.warning("No valid results found in transit analysis")
        return birth_dt, 50.0

    # Sort results by average score (descending)
    results.sort(key=lambda x: x[1], reverse=True)

    # Get best result
    best_time, best_score, total_aspects, valid_events = results[0]

    # Calculate confidence (50-90% range)
    confidence = min(90, 50 + (best_score / 20) * 40)

    # Log results
    logger.info(f"Transit analysis result: {best_time}, score: {best_score:.2f}, confidence: {confidence:.1f}")
    logger.info(f"Based on {valid_events} events with {total_aspects} significant aspects")

    return best_time, confidence
