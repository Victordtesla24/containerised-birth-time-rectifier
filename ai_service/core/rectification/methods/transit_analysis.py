"""
Transit Analysis for Birth Time Rectification.

This module calculates potential birth times based on transits to sensitive points
in the natal chart during significant life events.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional, Union
from datetime import datetime, timedelta
import math
import swisseph as swe
import json

# Add proper imports for dateutil and pytz
try:
    from dateutil import parser as dateutil_parser
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

# Change relative import to absolute import
from ai_service.core.rectification.methods.astrological_constants import DSC, IC, MC

from ai_service.core.rectification.utils.ephemeris import (
    get_planet_position as original_get_planet_position,
    get_house_cusps,
    calculate_ascendant,
    calculate_midheaven,
)

logger = logging.getLogger(__name__)

# Aspects to consider in transit analysis
MAJOR_ASPECTS = {
    "conjunction": 0,
    "opposition": 180,
    "trine": 120,
    "square": 90,
    "sextile": 60
}

# Orbs for different aspects
ASPECT_ORBS = {
    "conjunction": 8,  # Wider orb for conjunction
    "opposition": 8,   # Wider orb for opposition
    "trine": 7,        # Medium orb for trine
    "square": 7,       # Medium orb for square
    "sextile": 6,      # Smaller orb for sextile
    "quincunx": 3,     # Small orb for quincunx
    "semisextile": 2   # Small orb for semisextile
}

# Planets to consider in transit analysis
TRANSIT_PLANETS = [
    swe.JUPITER,  # Jupiter for career/education
    swe.SATURN,   # Saturn for challenges/responsibilities
    swe.URANUS,   # Uranus for sudden changes
    swe.PLUTO,    # Pluto for transformations
    swe.NEPTUNE,  # Neptune for spiritual changes
    swe.MARS,     # Mars for action/energy
    swe.SUN,      # Sun for vitality/recognition
    swe.MOON,     # Moon for emotional events
    swe.VENUS,    # Venus for relationships
    swe.MERCURY   # Mercury for communication/education
]

# Transiting points to analyze
TRANSIT_POINTS = {
    "career_change": [swe.JUPITER, swe.SATURN, swe.SUN, MC],
    "relationship": [swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN, DSC],
    "residence_change": [swe.MOON, swe.JUPITER, swe.SATURN, swe.URANUS, IC],
    "education": [swe.MERCURY, swe.JUPITER, swe.SUN, MC],
    "health_crisis": [swe.MARS, swe.SATURN, swe.PLUTO, swe.URANUS, swe.SUN, swe.ASC],
    "spiritual": [swe.NEPTUNE, swe.JUPITER, swe.URANUS, swe.PLUTO],
    "family": [swe.MOON, swe.VENUS, swe.SATURN, swe.JUPITER, IC],
    "financial": [swe.VENUS, swe.JUPITER, swe.SATURN, swe.PLUTO, MC],
    "travel": [swe.JUPITER, swe.MERCURY, swe.MOON, swe.URANUS],
    "children": [swe.MOON, swe.VENUS, swe.JUPITER, swe.SATURN]
}

# Natal points to consider for different event types
NATAL_POINTS = {
    "career_change": [swe.SUN, swe.SATURN, swe.JUPITER, swe.MARS, MC],
    "relationship": [swe.VENUS, swe.MOON, DSC, swe.MARS, swe.SUN],
    "residence_change": [swe.MOON, IC, swe.SATURN, swe.URANUS, swe.JUPITER],
    "education": [swe.MERCURY, swe.JUPITER, swe.SUN, swe.MOON],
    "health_crisis": [swe.MARS, swe.SATURN, swe.PLUTO, swe.SUN, swe.ASC],
    "spiritual": [swe.NEPTUNE, swe.JUPITER, swe.MOON, swe.URANUS],
    "family": [swe.MOON, swe.VENUS, IC, swe.SATURN, swe.JUPITER],
    "financial": [swe.VENUS, swe.JUPITER, swe.SATURN, MC, swe.PLUTO],
    "travel": [swe.MERCURY, swe.JUPITER, swe.MOON, swe.URANUS, swe.NEPTUNE],
    "children": [swe.MOON, swe.VENUS, swe.JUPITER, swe.SATURN, swe.SUN]
}

# House meanings for different life events
EVENT_HOUSES = {
    "career_change": [10, 6, 2],     # Career houses
    "relationship": [7, 5, 1, 8],    # Relationship houses
    "residence_change": [4, 3, 9],   # Home/relocation houses
    "education": [9, 3, 11],         # Education houses
    "health_crisis": [1, 6, 8, 12],  # Health houses
    "spiritual": [9, 12, 8, 4],      # Spiritual houses
    "family": [4, 5, 3, 10, 11],     # Family houses
    "financial": [2, 8, 10, 6],      # Financial houses
    "travel": [9, 3, 12, 1],         # Travel houses
    "children": [5, 1, 4, 11]        # Children houses
}

# Override the get_planet_position function to support speed calculation
def get_planet_position(dt: datetime, planet_id: int, include_speed: bool = False) -> Union[Tuple[float, float, float], Tuple[float, float, float, float]]:
    """
    Get the longitude, latitude, and distance of a planet at a specific datetime.

    Args:
        dt: Datetime
        planet_id: Swiss Ephemeris planet ID
        include_speed: Whether to include speed information

    Returns:
        Tuple of (longitude, latitude, distance) or (longitude, latitude, distance, speed)
    """
    # Call the original function to get position
    lon, lat, dist = original_get_planet_position(dt, planet_id)

    if include_speed:
        # Calculate speed using a simple approximation (change in position over time)
        dt_later = dt + timedelta(hours=1)
        lon_later, _, _ = original_get_planet_position(dt_later, planet_id)

        # Calculate hourly speed in degrees
        speed = (lon_later - lon) % 360
        if speed > 180:
            speed = speed - 360

        return lon, lat, dist, speed
    else:
        return lon, lat, dist

# Replace the score_candidate_time function entirely with a simplified version
async def score_candidate_time(
    birth_time: datetime,
    events: List[Dict[str, Any]],
    latitude: float,
    longitude: float
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Score a candidate birth time based on transit analysis.

    Args:
        birth_time: Candidate birth datetime
        events: List of life events with dates
        latitude: Birth latitude
        longitude: Birth longitude

    Returns:
        Tuple of (score, significant_aspects)
    """
    # Initialize score and aspects list
    total_score = 0.0
    significant_aspects = []

    # Calculate basic natal chart data
    natal_positions = {}
    natal_houses = []

    try:
        # Calculate house cusps
        natal_houses = get_house_cusps(birth_time, latitude, longitude)

        # Calculate main planet positions
        for planet in TRANSIT_PLANETS:
            lon, lat, dist = original_get_planet_position(birth_time, planet)
            natal_positions[planet] = {
                "longitude": lon,
                "name": _get_planet_name(planet)
            }

        # Calculate angles
        asc_lon = calculate_ascendant(birth_time, latitude, longitude)
        mc_lon = calculate_midheaven(birth_time, latitude, longitude)

        natal_positions["ASC"] = {"longitude": asc_lon, "name": "Ascendant"}
        natal_positions["MC"] = {"longitude": mc_lon, "name": "Midheaven"}
        natal_positions["DSC"] = {"longitude": (asc_lon + 180) % 360, "name": "Descendant"}
        natal_positions["IC"] = {"longitude": (mc_lon + 180) % 360, "name": "IC"}

        # Process each event
        for event in events:
            event_score = 0

            # Get event date
            if not isinstance(event.get("date"), datetime):
                try:
                    # Parse string date
                    if DATEUTIL_AVAILABLE:
                        event_date = dateutil_parser.parse(event["date"])
                    else:
                        # Simple parsing attempt
                        event_date = datetime.strptime(event["date"], "%Y-%m-%d")
                except Exception:
                    # Skip events with unparseable dates
                    continue
            else:
                event_date = event["date"]

            # Calculate transit positions
            transit_positions = {}
            for planet in TRANSIT_PLANETS:
                lon, lat, dist = original_get_planet_position(event_date, planet)
                transit_positions[planet] = {
                    "longitude": lon,
                    "name": _get_planet_name(planet)
                }

            # Calculate transit angles
            transit_positions["ASC"] = {
                "longitude": calculate_ascendant(event_date, latitude, longitude),
                "name": "Ascendant"
            }
            transit_positions["MC"] = {
                "longitude": calculate_midheaven(event_date, latitude, longitude),
                "name": "Midheaven"
            }

            # Find aspects between transit and natal planets
            for transit_id, transit_data in transit_positions.items():
                transit_lon = transit_data["longitude"]
                transit_name = transit_data["name"]

                for natal_id, natal_data in natal_positions.items():
                    natal_lon = natal_data["longitude"]
                    natal_name = natal_data["name"]

                    # Calculate the angular difference
                    diff = abs((transit_lon - natal_lon) % 360)
                    if diff > 180:
                        diff = 360 - diff

                    # Check for major aspects
                    for aspect_name, aspect_angle in MAJOR_ASPECTS.items():
                        orb = ASPECT_ORBS.get(aspect_name, 5)

                        aspect_diff = abs(diff - aspect_angle)
                        if aspect_diff <= orb:
                            # Calculate aspect strength
                            aspect_strength = 1 - (aspect_diff / orb)

                            # Base aspect score
                            aspect_score = 1.0

                            # Apply modifiers based on aspect
                            if aspect_name == "conjunction":
                                aspect_score *= 1.5
                            elif aspect_name == "opposition":
                                aspect_score *= 1.3
                            elif aspect_name == "square":
                                aspect_score *= 1.2

                            # Prioritize angles
                            if natal_id in ["ASC", "MC", "DSC", "IC"]:
                                aspect_score *= 1.3

                            # Prioritize slower planets
                            if transit_id in [swe.SATURN, swe.URANUS, swe.NEPTUNE, swe.PLUTO]:
                                aspect_score *= 1.2

                            # Calculate significance
                            significance = aspect_strength * 100

                            # Record aspect
                            aspect_info = {
                                "transit_planet": transit_name,
                                "natal_planet": natal_name,
                                "aspect": aspect_name,
                                "orb": aspect_diff,
                                "score": aspect_score,
                                "event_date": event_date.isoformat(),
                                "strength": aspect_strength,
                                "significance": significance
                            }

                            significant_aspects.append(aspect_info)
                            event_score += aspect_score

            # Add event score to total
            total_score += event_score

        # Sort aspects by score
        significant_aspects.sort(key=lambda x: x["score"], reverse=True)

        # Limit results
        significant_aspects = significant_aspects[:10]

    except Exception as e:
        logger.error(f"Error in score_candidate_time: {e}")
        # In case of error, return minimal results

    return total_score, significant_aspects

# Helper function to determine which house a planet is in based on its longitude
def _determine_house_for_planet(house_cusps: List[float], longitude: float) -> int:
    """
    Determine which house a planet is in based on its longitude.

    Args:
        house_cusps: List of house cusp longitudes
        longitude: Planet's longitude

    Returns:
        House number (1-12)
    """
    # Make sure we have valid house cusps
    if not house_cusps or len(house_cusps) < 12:
        return 0

    # Check each house
    for i in range(12):
        cusp = house_cusps[i]
        next_cusp = house_cusps[(i + 1) % 12]

        # Handle houses that cross the 0° point
        if next_cusp < cusp:  # House crosses 0°
            if longitude >= cusp or longitude < next_cusp:
                return i + 1
        else:  # Normal case
            if cusp <= longitude < next_cusp:
                return i + 1

    # Default to first house if no match found
    return 1

# Fix the calculate_correlation_score function to ensure it returns a float in all code paths
def calculate_correlation_score(natal_factors: list, transit_factors: list) -> float:
    """
    Calculate a correlation score based on natal and transit factors.

    Args:
        natal_factors: List of natal chart factors
        transit_factors: List of transit factors

    Returns:
        Correlation score from 0.0 to 100.0
    """
    # Initialize score
    score = 50.0  # Start with a baseline score

    # Add points for natal factors
    for factor in natal_factors:
        significance = factor.get("significance", "")
        if significance == "high":
            score += 5.0
        elif significance == "medium-high":
            score += 3.0
        elif significance == "medium":
            score += 2.0

    # Add points for transit factors
    for factor in transit_factors:
        significance = factor.get("significance", "")
        factor_type = factor.get("type", "")

        # Base points by significance
        if significance == "high":
            points = 5.0
        elif significance == "medium-high":
            points = 3.0
        elif significance == "medium":
            points = 2.0
        else:
            points = 1.0

        # Adjust by factor type
        if factor_type == "transit_aspect":
            aspect = factor.get("aspect", "")
            # Stronger aspects get more weight
            if aspect in ["conjunction", "opposition"]:
                points *= 1.2
            elif aspect == "square":
                points *= 1.1

            # Adjust by orb - closer aspects are stronger
            orb = factor.get("orb", 0)
            if orb < 1.0:
                points *= 1.5
            elif orb < 3.0:
                points *= 1.2

        # Add to score
        score += points

    # Cap the score
    score = min(score, 100.0)

    # Ensure we return a float
    return float(score)

async def analyze_life_events(
    events: List[Dict[str, Any]],
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str
) -> Tuple[datetime, float]:
    """
    Analyzes life events to determine the most likely birth time.

    This function evaluates how well different candidate birth times
    correlate with the timing of significant life events through
    transits and progressions.

    Args:
        events: List of life events with dates and descriptions
        birth_dt: Original birth datetime
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string

    Returns:
        Tuple of (rectified_datetime, confidence_score)
    """
    # Check if we have enough events for accurate analysis
    if not events or len(events) < 1:
        logger.warning("Not enough life events for transit analysis")
        return birth_dt, 50.0

    logger.info(f"Analyzing {len(events)} life events for birth time rectification")

    # Generate candidate birth times (within 2 hours before and after the given time)
    candidates = []
    for minutes in range(-120, 121, 15):  # 15-minute increments
        candidate_time = birth_dt + timedelta(minutes=minutes)
        candidates.append(candidate_time)

    # Score each candidate time
    candidate_scores = []
    for candidate_time in candidates:
        try:
            score, analyzed_events = await score_candidate_time(
                candidate_time, events, latitude, longitude
            )

            # Add candidate with its score
            time_diff = int((candidate_time - birth_dt).total_seconds() / 60)
            candidate_scores.append({
                'birth_time': candidate_time,
                'score': score,
                'time_diff_minutes': time_diff,
                'analyzed_events': analyzed_events
            })
            logger.debug(f"Candidate {candidate_time.strftime('%H:%M')} scored {score:.2f}")
        except Exception as e:
            logger.error(f"Error scoring candidate time {candidate_time}: {e}")
            continue

    # Sort candidates by score (highest first)
    candidate_scores.sort(key=lambda x: x['score'], reverse=True)

    # Get the best candidate
    if not candidate_scores:
        logger.warning("No valid candidates found")
        return birth_dt, 50.0

    best_candidate = candidate_scores[0]
    best_time = best_candidate['birth_time']

    # Calculate confidence based on score (50-95% range)
    # Higher scores translate to higher confidence
    best_score = best_candidate['score']
    confidence = min(95, 50 + (best_score / 150) * 45)  # Scale score to 50-95 range

    logger.info(f"Best birth time: {best_time.strftime('%H:%M')} (shifted by {best_candidate['time_diff_minutes']} minutes)")
    logger.info(f"Score: {best_score:.2f}, Confidence: {confidence:.2f}%")

    return best_time, confidence

def _get_planet_name(planet_id):
    """Convert planet ID to name."""
    # Convert pyswisseph constants to human-readable names
    planet_names = {
        swe.SUN: "Sun",
        swe.MOON: "Moon",
        swe.MERCURY: "Mercury",
        swe.VENUS: "Venus",
        swe.MARS: "Mars",
        swe.JUPITER: "Jupiter",
        swe.SATURN: "Saturn",
        swe.URANUS: "Uranus",
        swe.NEPTUNE: "Neptune",
        swe.PLUTO: "Pluto",
        swe.MEAN_NODE: "North Node",
        "ASC": "Ascendant",
        "MC": "Midheaven",
        "DSC": "Descendant",
        "IC": "IC"
    }
    return planet_names.get(planet_id, str(planet_id))

async def get_detailed_transit_analysis(
    events: list,
    rectified_time: datetime,
    latitude: float,
    longitude: float,
    timezone: str
) -> dict:
    """
    Provide detailed transit analysis for the rectified chart.

    Args:
        events: List of life events
        rectified_time: Rectified birth time
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string

    Returns:
        Dictionary with transit analysis for each event
    """
    from ai_service.core.rectification.chart_calculator import calculate_chart

    analysis = {
        "events": [],
        "summary": {}
    }

    # Calculate rectified natal chart
    natal_chart = calculate_chart(rectified_time, latitude, longitude, timezone)
    if not natal_chart:
        return analysis

    # Analyze each event
    significant_aspects = []

    for event in events:
        if "date" not in event or not event["date"]:
            continue

        # Parse event date
        event_date = None
        try:
            if isinstance(event["date"], str):
                # Try ISO format first
                try:
                    event_date = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
                except ValueError:
                    # Try other common formats
                    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y'):
                        try:
                            event_date = datetime.strptime(event["date"], fmt)
                            break
                        except ValueError:
                            continue
            else:
                event_date = event["date"]  # Already a datetime
        except Exception as e:
            logger.warning(f"Could not parse event date: {e}")
            continue

        if not event_date:
            continue

        # Get event type
        event_type = event.get("event_type", "general_event")

        # Get event description
        description = event.get("description", "")

        # Calculate transit chart for event date
        transit_chart = calculate_chart(event_date, latitude, longitude, timezone)
        if not transit_chart:
            continue

        # Get event rulers
        event_rulers = get_event_rulers(event_type)

        # Find significant transits
        aspects = []

        # Check transits from planets to natal planets
        for transit_planet, transit_data in transit_chart.get("planets", {}).items():
            transit_longitude = transit_data.get("longitude")
            if transit_longitude is None:
                continue

            # Get transit speed for applying/separating calculation
            transit_speed = transit_data.get("speed", 0)

            # Get transit house
            transit_house = transit_data.get("house", 0)

            # Check aspects to natal planets
            for natal_planet, natal_data in natal_chart.get("planets", {}).items():
                natal_longitude = natal_data.get("longitude")
                if natal_longitude is None:
                    continue

                # Get natal speed (will be 0 for applying/separating calculation)
                natal_speed = 0

                # Get natal house
                natal_house = natal_data.get("house", 0)

                # Calculate aspect angle
                diff = abs(transit_longitude - natal_longitude) % 360
                if diff > 180:
                    diff = 360 - diff

                # Check for major aspects
                aspect_name = None
                exact_orb = 0

                # Check each aspect type
                if 0 <= diff < 10:  # Conjunction
                    aspect_name = "conjunction"
                    exact_orb = diff
                elif 170 <= diff <= 180:  # Opposition
                    aspect_name = "opposition"
                    exact_orb = abs(diff - 180)
                elif 85 <= diff <= 95:  # Square
                    aspect_name = "square"
                    exact_orb = abs(diff - 90)
                elif 115 <= diff <= 125:  # Trine
                    aspect_name = "trine"
                    exact_orb = abs(diff - 120)
                elif 55 <= diff <= 65:  # Sextile
                    aspect_name = "sextile"
                    exact_orb = abs(diff - 60)

                if aspect_name:
                    # Calculate raw aspect strength
                    max_orb = 10 if aspect_name in ["conjunction", "opposition"] else 6
                    strength = (1 - (exact_orb / max_orb)) * 100 if max_orb > 0 else 100

                    # Enhanced astrological evaluation
                    final_significance = _evaluate_astrological_significance(
                        transit_planet=transit_planet.capitalize(),
                        natal_planet=natal_planet.capitalize(),
                        aspect=aspect_name,
                        strength=strength,
                        event_type=event_type,
                        orb=exact_orb,
                        is_applying=transit_speed > natal_speed,  # Transit planet is moving faster than natal
                        transit_house=transit_house,
                        natal_house=natal_house
                    )

                    # Only include significant aspects
                    if final_significance >= 20:
                        aspects.append({
                            "type": "planet-planet",
                            "transit_planet": transit_planet.capitalize(),
                            "natal_planet": natal_planet.capitalize(),
                            "aspect": aspect_name,
                            "orb": round(exact_orb, 2),
                            "significance": round(final_significance, 1),
                            "astrological_meaning": get_aspect_meaning(transit_planet, natal_planet, aspect_name, event_type),
                            "is_applying": transit_speed > natal_speed
                        })

                        # Add to list of significant aspects
                        significant_aspects.append({
                            "event_type": event_type,
                            "transit": transit_planet.capitalize(),
                            "natal": natal_planet.capitalize(),
                            "aspect": aspect_name,
                            "significance": round(final_significance, 1)
                        })

            # Check aspects to angles
            for angle_name, angle_data in natal_chart.get("angles", {}).items():
                angle_longitude = angle_data.get("longitude")
                if angle_longitude is None:
                    continue

                # Calculate aspect angle
                diff = abs(transit_longitude - angle_longitude) % 360
                if diff > 180:
                    diff = 360 - diff

                # Check for major aspects (tighter orbs for angles)
                aspect_name = None
                exact_orb = 0

                # Check each aspect type with tighter orbs for angles
                if 0 <= diff < 8:  # Conjunction
                    aspect_name = "conjunction"
                    exact_orb = diff
                elif 172 <= diff <= 180:  # Opposition
                    aspect_name = "opposition"
                    exact_orb = abs(diff - 180)
                elif 87 <= diff <= 93:  # Square
                    aspect_name = "square"
                    exact_orb = abs(diff - 90)

                if aspect_name:
                    # Calculate raw aspect strength
                    max_orb = 8 if aspect_name == "conjunction" else 6
                    strength = (1 - (exact_orb / max_orb)) * 100 if max_orb > 0 else 100

                    # Enhanced astrological evaluation for angles
                    final_significance = _evaluate_astrological_significance(
                        transit_planet=transit_planet.capitalize(),
                        natal_planet=angle_name.upper(),
                        aspect=aspect_name,
                        strength=strength,
                        event_type=event_type,
                        orb=exact_orb,
                        is_applying=transit_speed > 0,  # For angles, just check if transit is direct
                        transit_house=transit_house,
                        natal_house=0  # Angles don't have houses
                    )

                    # Only include significant aspects
                    if final_significance >= 20:
                        aspects.append({
                            "type": "planet-angle",
                            "transit_planet": transit_planet.capitalize(),
                            "natal_angle": angle_name.upper(),
                            "aspect": aspect_name,
                            "orb": round(exact_orb, 2),
                            "significance": round(final_significance, 1),
                            "astrological_meaning": get_aspect_meaning(transit_planet, angle_name, aspect_name, event_type),
                            "is_applying": transit_speed > 0
                        })

                        # Add to list of significant aspects
                        significant_aspects.append({
                            "event_type": event_type,
                            "transit": transit_planet.capitalize(),
                            "natal": angle_name.upper(),
                            "aspect": aspect_name,
                            "significance": round(final_significance, 1)
                        })

        # Sort aspects by significance
        aspects.sort(key=lambda x: x["significance"], reverse=True)

        # Add event analysis
        event_analysis = {
            "event_type": event_type,
            "event_date": event_date.isoformat(),
            "description": description,
            "aspects": aspects[:10],  # Only include top 10 aspects
            "aspect_count": len(aspects)
        }

        analysis["events"].append(event_analysis)

    # Create summary information
    if significant_aspects:
        # Group by planet combinations
        planet_counts = {}

        for aspect in significant_aspects:
            combo = f"{aspect['transit']}-{aspect['natal']}"
            if combo not in planet_counts:
                planet_counts[combo] = {
                    "count": 0,
                    "significance": 0,
                    "aspects": []
                }

            planet_counts[combo]["count"] += 1
            planet_counts[combo]["significance"] += aspect["significance"]
            planet_counts[combo]["aspects"].append(aspect["aspect"])

        # Calculate average significance and sort
        for combo, data in planet_counts.items():
            data["avg_significance"] = round(data["significance"] / data["count"], 1)

        # Sort by significance
        sorted_combos = sorted(planet_counts.items(),
                               key=lambda x: (x[1]["count"], x[1]["avg_significance"]),
                               reverse=True)

        # Create summary
        analysis["summary"] = {
            "top_combinations": [{
                "combination": combo,
                "count": data["count"],
                "avg_significance": data["avg_significance"],
                "aspects": list(set(data["aspects"]))
            } for combo, data in sorted_combos[:5]]  # Top 5 combinations
        }

    return analysis

def get_aspect_meaning(
    transit_planet: str,
    natal_planet: str,
    aspect: str,
    event_type: str = ""
) -> str:
    """
    Get the astrological meaning of a transit aspect.

    Args:
        transit_planet: Transiting planet
        natal_planet: Natal planet or angle
        aspect: Aspect type
        event_type: Optional event type for context

    Returns:
        Description of the aspect meaning
    """
    # Basic meanings for different aspects
    aspect_meanings = {
        "conjunction": "intensifies and activates",
        "opposition": "creates tension and awareness with",
        "trine": "creates flow and ease with",
        "square": "creates challenges and growth with",
        "sextile": "creates opportunities and harmony with"
    }

    # Default meaning if no specific meaning is found
    base_meaning = f"Transit {transit_planet} {aspect_meanings.get(aspect, 'aspects')} natal {natal_planet}"

    # Specific meanings for important combinations
    specific_meanings = {
        # Saturn transits
        ("Saturn", "Sun", "conjunction"): f"A time of increased responsibility, possible limitations, and reality checks in the areas of identity and life direction.",
        ("Saturn", "Moon", "conjunction"): f"Emotional challenges, possible feelings of isolation, and a time to build emotional maturity.",
        ("Saturn", "Ascendant", "conjunction"): f"A period of personal restructuring, taking on new responsibilities, and possibly restrictions in personal freedom.",

        # Jupiter transits
        ("Jupiter", "Sun", "conjunction"): f"A period of expanded opportunities, increased optimism, and possible growth in status or recognition.",
        ("Jupiter", "Moon", "conjunction"): f"Emotional expansiveness, increased well-being, and possible domestic improvements.",
        ("Jupiter", "Ascendant", "conjunction"): f"Personal growth, new opportunities, and an expanded sense of self.",

        # Uranus transits
        ("Uranus", "Sun", "conjunction"): f"Sudden changes in life direction, increased need for freedom, and possibly unexpected events affecting identity.",
        ("Uranus", "Moon", "conjunction"): f"Emotional volatility, desire for change in home or family, and possibly unexpected emotional revelations.",
        ("Uranus", "Ascendant", "conjunction"): f"Radical personal changes, unexpected new beginnings, and possibly a reinvention of self.",

        # Neptune transits
        ("Neptune", "Sun", "conjunction"): f"Heightened imagination, possible confusion about identity, and spiritual awakening.",
        ("Neptune", "Moon", "conjunction"): f"Increased sensitivity, possible emotional confusion, and spiritual or creative inspiration.",

        # Pluto transits
        ("Pluto", "Sun", "conjunction"): f"Profound transformation of identity, power struggles, and deep personal evolution.",
        ("Pluto", "Moon", "conjunction"): f"Deep emotional transformation, confrontation with emotional patterns, and powerful changes in home or family."
    }

    # Check for specific meaning
    key = (transit_planet, natal_planet, aspect)
    if key in specific_meanings:
        return specific_meanings[key]

    # General meaning based on event type and transit
    if event_type == "marriage" and transit_planet in ["Venus", "Jupiter"]:
        return f"Transit {transit_planet} {aspect_meanings.get(aspect, 'aspects')} natal {natal_planet}, bringing relationship opportunities or developments."
    elif event_type == "career" and transit_planet in ["Saturn", "Jupiter", "Pluto"]:
        return f"Transit {transit_planet} {aspect_meanings.get(aspect, 'aspects')} natal {natal_planet}, triggering career changes or opportunities."
    elif event_type == "relocation" and transit_planet in ["Moon", "Uranus", "Jupiter"]:
        return f"Transit {transit_planet} {aspect_meanings.get(aspect, 'aspects')} natal {natal_planet}, stimulating changes in residence or location."

    return base_meaning

def get_event_rulers(event_type: str) -> dict:
    """
    Returns planet and house rulers for different types of life events.

    Args:
        event_type: Type of life event

    Returns:
        Dictionary of relevant planets, houses, and aspects
    """
    # Default rulers
    rulers = {
        "planets": ["Sun", "Moon", "Jupiter", "Saturn"],
        "houses": [1, 10],
        "angles": ["ASC", "MC"],
        "event_type": event_type
    }

    # Event-specific rulers
    if event_type == "marriage" or event_type == "relationship":
        rulers = {
            "planets": ["Venus", "Mars", "Moon", "Jupiter"],
            "houses": [5, 7],
            "angles": ["ASC", "DSC"],
            "Venus": 1.5,
            "Mars": 1.3,
            "Moon": 1.2,
            "Jupiter": 1.2,
            "event_type": event_type
        }
    elif event_type == "career" or event_type == "job":
        rulers = {
            "planets": ["Sun", "Saturn", "Mars", "Jupiter"],
            "houses": [6, 10],
            "angles": ["MC"],
            "Saturn": 1.5,
            "Mars": 1.3,
            "Sun": 1.4,
            "Jupiter": 1.2,
            "event_type": event_type
        }
    elif event_type == "relocation" or event_type == "move":
        rulers = {
            "planets": ["Moon", "Mercury", "Uranus"],
            "houses": [3, 4, 9],
            "angles": ["IC"],
            "Moon": 1.5,
            "Mercury": 1.3,
            "Uranus": 1.3,
            "event_type": event_type
        }
    elif event_type == "health" or event_type == "illness":
        rulers = {
            "planets": ["Mars", "Saturn", "Neptune", "Pluto"],
            "houses": [1, 6, 8, 12],
            "angles": ["ASC"],
            "Mars": 1.5,
            "Saturn": 1.4,
            "Neptune": 1.3,
            "Pluto": 1.3,
            "event_type": event_type
        }
    elif event_type == "children" or event_type == "pregnancy":
        rulers = {
            "planets": ["Jupiter", "Venus", "Moon"],
            "houses": [5],
            "angles": [],
            "Jupiter": 1.5,
            "Venus": 1.4,
            "Moon": 1.5,
            "event_type": event_type
        }
    elif event_type == "education" or event_type == "learning":
        rulers = {
            "planets": ["Mercury", "Jupiter", "Uranus"],
            "houses": [3, 9],
            "angles": [],
            "Mercury": 1.5,
            "Jupiter": 1.4,
            "Uranus": 1.2,
            "event_type": event_type
        }
    elif event_type == "accident":
        rulers = {
            "planets": ["Mars", "Uranus", "Saturn"],
            "houses": [1, 6, 8],
            "angles": ["ASC"],
            "Mars": 1.6,
            "Uranus": 1.5,
            "Saturn": 1.3,
            "event_type": event_type
        }
    elif event_type == "death":
        rulers = {
            "planets": ["Pluto", "Saturn", "Neptune", "Mars"],
            "houses": [8],
            "angles": [],
            "Pluto": 1.7,
            "Saturn": 1.5,
            "Neptune": 1.3,
            "Mars": 1.3,
            "event_type": event_type
        }
    elif event_type == "financial":
        rulers = {
            "planets": ["Venus", "Jupiter", "Saturn", "Uranus"],
            "houses": [2, 8],
            "angles": [],
            "Venus": 1.5,
            "Jupiter": 1.4,
            "Saturn": 1.3,
            "Uranus": 1.3,
            "event_type": event_type
        }

    return rulers

def _evaluate_astrological_significance(
    transit_planet: str,
    natal_planet: str,
    aspect: str,
    strength: float,
    event_type: str,
    orb: float,
    is_applying: bool,
    transit_house: int,
    natal_house: int
) -> float:
    """
    Evaluate the astrological significance of a transit-natal aspect.

    This function implements astrological wisdom about which aspects
    between which planets are most significant for different types of events.

    Args:
        transit_planet: Transiting planet name
        natal_planet: Natal planet name
        aspect: Aspect type
        strength: Raw aspect strength
        event_type: Type of life event
        orb: Exactness of aspect (smaller is more exact)
        is_applying: Whether the aspect is applying
        transit_house: House of the transiting planet
        natal_house: House of the natal planet

    Returns:
        Astrological significance score (0-100)
    """
    base_score = strength

    # Basic aspect significance
    aspect_weights = {
        "conjunction": 10.0,
        "opposition": 9.0,
        "square": 8.0,
        "trine": 7.0,
        "sextile": 6.0
    }

    aspect_weight = aspect_weights.get(aspect, 5.0)

    # Adjust significance based on planets involved
    planet_significance = {
        # Outer planets have higher significance for major life events
        "Pluto": 1.5,
        "Neptune": 1.4,
        "Uranus": 1.3,
        "Saturn": 1.2,
        "Jupiter": 1.1,
        # Inner planets have moderate significance
        "Mars": 1.0,
        "Sun": 1.0,
        "Venus": 0.9,
        "Mercury": 0.9,
        "Moon": 1.1,  # Moon slightly higher due to emotional significance
    }

    transit_significance = planet_significance.get(transit_planet, 1.0)
    natal_significance = planet_significance.get(natal_planet, 1.0)

    # Adjust for applying vs separating (applying aspects are stronger)
    applying_factor = 1.2 if is_applying else 0.9

    # Houses significance
    # Angular houses (1, 4, 7, 10) are more significant
    angular_houses = [1, 4, 7, 10]
    if transit_house in angular_houses:
        house_factor = 1.3
    elif transit_house in [2, 5, 8, 11]:  # Succedent houses
        house_factor = 1.1
    else:  # Cadent houses
        house_factor = 0.9

    # Natal house significance also matters
    if natal_house in angular_houses:
        house_factor *= 1.2

    # Event-specific planet significances
    event_rulers = {}

    # Define relevant planets and houses for different event types
    if event_type == "marriage" or event_type == "relationship":
        event_rulers = {
            "Venus": 1.5, "Mars": 1.3, "Moon": 1.2, "Jupiter": 1.2,
            "houses": [5, 7]
        }
    elif event_type == "career" or event_type == "job":
        event_rulers = {
            "Saturn": 1.5, "Mars": 1.3, "Sun": 1.4, "Jupiter": 1.2,
            "houses": [6, 10]
        }
    elif event_type == "relocation" or event_type == "move":
        event_rulers = {
            "Moon": 1.5, "Mercury": 1.3, "Uranus": 1.3,
            "houses": [3, 4, 9]
        }
    elif event_type == "health" or event_type == "illness":
        event_rulers = {
            "Mars": 1.5, "Saturn": 1.4, "Neptune": 1.3, "Pluto": 1.3,
            "houses": [1, 6, 8, 12]
        }
    elif event_type == "children" or event_type == "pregnancy":
        event_rulers = {
            "Jupiter": 1.5, "Venus": 1.4, "Moon": 1.5,
            "houses": [5]
        }
    elif event_type == "education" or event_type == "learning":
        event_rulers = {
            "Mercury": 1.5, "Jupiter": 1.4, "Uranus": 1.2,
            "houses": [3, 9]
        }
    elif event_type == "accident":
        event_rulers = {
            "Mars": 1.6, "Uranus": 1.5, "Saturn": 1.3,
            "houses": [1, 6, 8]
        }
    elif event_type == "death":
        event_rulers = {
            "Pluto": 1.7, "Saturn": 1.5, "Neptune": 1.3, "Mars": 1.3,
            "houses": [8]
        }
    elif event_type == "financial":
        event_rulers = {
            "Venus": 1.5, "Jupiter": 1.4, "Saturn": 1.3, "Uranus": 1.3,
            "houses": [2, 8]
        }

    # Calculate event-specific planet significance
    event_planet_factor = 1.0
    if event_type and event_rulers:
        transit_event_factor = event_rulers.get(transit_planet, 1.0)
        natal_event_factor = event_rulers.get(natal_planet, 1.0)
        event_planet_factor = (transit_event_factor + natal_event_factor) / 2

        # Check if houses involved are relevant for this event
        relevant_houses = event_rulers.get("houses", [])
        if transit_house in relevant_houses or natal_house in relevant_houses:
            event_planet_factor *= 1.3

    # Specific planet combinations with special significance
    special_combinations = {
        ("Saturn", "Sun"): 1.5,      # Saturn transiting Sun is significant for career/authority
        ("Jupiter", "Sun"): 1.4,     # Jupiter transiting Sun brings opportunities
        ("Uranus", "Sun"): 1.3,      # Uranus transiting Sun brings sudden changes
        ("Saturn", "Moon"): 1.4,     # Saturn transiting Moon brings emotional challenges
        ("Pluto", "Sun"): 1.6,       # Pluto transiting Sun brings profound changes
        ("Neptune", "Sun"): 1.3,     # Neptune transiting Sun can bring confusion or spirituality
        ("Jupiter", "Venus"): 1.4,   # Jupiter transiting Venus is good for relationships
        ("Saturn", "Venus"): 1.3,    # Saturn transiting Venus tests relationships
        ("Uranus", "Venus"): 1.5,    # Uranus transiting Venus brings sudden relationship changes
        ("Jupiter", "Jupiter"): 1.4, # Jupiter return is significant
        ("Saturn", "Saturn"): 1.7    # Saturn return is very significant
    }

    # Check both directions (transit to natal and natal to transit)
    combination_factor = special_combinations.get((transit_planet, natal_planet), 1.0)
    reverse_combination_factor = special_combinations.get((natal_planet, transit_planet), 1.0)
    combination_factor = max(combination_factor, reverse_combination_factor)

    # Exactness of aspect (orb factor)
    orb_factor = 1.0
    if orb < 1.0:  # Very exact
        orb_factor = 1.5
    elif orb < 2.0:  # Quite exact
        orb_factor = 1.3
    elif orb < 3.0:  # Moderate
        orb_factor = 1.1

    # Calculate final significance score
    final_score = (base_score * aspect_weight * transit_significance * natal_significance *
                 applying_factor * house_factor * event_planet_factor *
                 combination_factor * orb_factor) / 10.0

    # Ensure score is within 0-100 range
    final_score = min(100.0, max(0.0, final_score))

    return final_score

async def correlate_events_with_chart(
    events: list,
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str
) -> list:
    """
    Correlate life events with natal chart positions to validate rectification.

    Args:
        events: List of life events with dates and descriptions
        birth_dt: Birth datetime (rectified)
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string

    Returns:
        List of event correlations with astrological factors
    """

    logger.info(f"Correlating {len(events)} events with natal chart")

    # Get detailed transit analysis which includes event correlations
    analysis = await get_detailed_transit_analysis(
        events, birth_dt, latitude, longitude, timezone
    )

    # Format the results in a structure that matches the expected output
    correlations = []

    for event_analysis in analysis.get("events", []):
        event_date = event_analysis.get("event_date", "")
        event_type = event_analysis.get("event_type", "")
        description = event_analysis.get("description", "")
        aspects = event_analysis.get("aspects", [])

        # Calculate correlation score from aspects
        if aspects:
            correlation_score = sum(aspect.get("significance", 0) for aspect in aspects[:5]) / min(5, len(aspects))
            # Normalize to 0-100 scale
            correlation_score = min(100, correlation_score)
        else:
            correlation_score = 50  # Default moderate score

        # Parse the date to calculate age at event
        age_at_event = None
        try:
            if isinstance(event_date, str):
                event_dt = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
                birth_year = birth_dt.year
                event_year = event_dt.year
                age_at_event = event_year - birth_year
                # Adjust if birthday hasn't occurred yet in event year
                if (event_dt.month, event_dt.day) < (birth_dt.month, birth_dt.day):
                    age_at_event -= 1
        except (ValueError, TypeError):
            # If date parsing fails, skip age calculation
            logger.error(f"Failed to parse event date: {event_date}")

        # Format aspects for the correlation output
        natal_factors = []
        transit_factors = []

        for aspect in aspects:
            # Add transit factors
            if aspect.get("type") == "planet-planet":
                transit_factors.append({
                    "planet": aspect.get("transit_planet"),
                    "aspect": aspect.get("aspect"),
                    "natal_planet": aspect.get("natal_planet"),
                    "significance": aspect.get("significance")
                })

                # Also add as natal factors
                natal_factors.append({
                    "planet": aspect.get("natal_planet"),
                    "aspect_from": aspect.get("transit_planet"),
                    "aspect_type": aspect.get("aspect"),
                    "significance": aspect.get("significance")
                })
            elif aspect.get("type") == "planet-angle":
                transit_factors.append({
                    "planet": aspect.get("transit_planet"),
                    "aspect": aspect.get("aspect"),
                    "natal_angle": aspect.get("natal_angle"),
                    "significance": aspect.get("significance")
                })

                # Also add as natal factors
                natal_factors.append({
                    "angle": aspect.get("natal_angle"),
                    "aspect_from": aspect.get("transit_planet"),
                    "aspect_type": aspect.get("aspect"),
                    "significance": aspect.get("significance")
                })

        # Create correlation entry
        correlation = {
            "event_date": event_date,
            "event_type": event_type,
            "description": description,
            "age_at_event": age_at_event,
            "natal_factors": natal_factors[:5],  # Limit to top 5
            "transit_factors": transit_factors[:5],  # Limit to top 5
            "correlation_score": round(correlation_score, 1)
        }

        correlations.append(correlation)

    # Sort by correlation score (highest first)
    correlations.sort(key=lambda x: x.get("correlation_score", 0), reverse=True)

    return correlations
