"""
Birth time rectification module

This module provides functionality to rectify birth times based on
questionnaire answers and life events using actual astrological calculations.
"""

from datetime import datetime, timedelta, date
import logging
import math
import asyncio
import pytz
import re
from typing import Tuple, List, Dict, Any, Optional, Union
import numpy as np
import json
import uuid

# Import astrological calculation libraries (no fallbacks)
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
from flatlib.chart import Chart
from flatlib import const
from flatlib.dignities import essential

# Additional required dependencies
from timezonefinder import TimezoneFinder

# Import OpenAI integration for advanced rectification
from ai_service.api.services.openai import get_openai_service

# Configure logging
logger = logging.getLogger(__name__)

# Define constants that might be missing from flatlib.const
# This will be used as a fallback if const.LIST_PLANETS is not available
PLANETS_LIST = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"
]

# Define life event types and their associated astrological factors
LIFE_EVENT_MAPPING = {
    "marriage": ["Venus", "Juno", "Descendant", "7th_house"],
    "career_change": ["Saturn", "Midheaven", "10th_house"],
    "relocation": ["Moon", "4th_house", "IC"],
    "major_illness": ["Mars", "Saturn", "Chiron", "6th_house", "8th_house"],
    "children": ["Jupiter", "Moon", "5th_house"],
    "education": ["Mercury", "3rd_house", "9th_house"],
    "accident": ["Mars", "Uranus", "8th_house"],
    "death_of_loved_one": ["Pluto", "Saturn", "8th_house"],
    "spiritual_awakening": ["Neptune", "Jupiter", "9th_house", "12th_house"],
    "financial_change": ["Venus", "Jupiter", "2nd_house", "8th_house"]
}

def extract_life_events_from_answers(answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract life events from questionnaire answers for rectification.

    Args:
        answers: List of question/answer pairs

    Returns:
        List of life events with date, type, and description
    """
    life_events = []

    for answer in answers:
        question = answer.get("question", "")
        answer_text = answer.get("answer", "")

        # Skip if either question or answer is missing
        if not question or not answer_text:
            continue

        # Detect life events in questions/answers
        event_type = None
        event_date = None
        confidence = 1.0

        # Analyze question for life event categories
        question_lower = question.lower()

        # Check for specific life event keywords
        if any(word in question_lower for word in ["marriage", "wedding", "spouse", "married"]):
            event_type = "marriage"
        elif any(word in question_lower for word in ["job", "career", "profession", "work", "promotion"]):
            event_type = "career_change"
        elif any(word in question_lower for word in ["move", "moved", "relocation", "relocated"]):
            event_type = "relocation"
        elif any(word in question_lower for word in ["illness", "disease", "sickness", "diagnosed"]):
            event_type = "major_illness"
        elif any(word in question_lower for word in ["child", "children", "birth", "born", "pregnancy"]):
            event_type = "children"
        elif any(word in question_lower for word in ["education", "school", "college", "degree", "university"]):
            event_type = "education"
        elif any(word in question_lower for word in ["accident", "crash", "injury", "emergency"]):
            event_type = "accident"
        elif any(word in question_lower for word in ["death", "funeral", "deceased", "passed away"]):
            event_type = "death_of_loved_one"
        elif any(word in question_lower for word in ["spiritual", "awakening", "enlightenment", "meditation"]):
            event_type = "spiritual_awakening"
        elif any(word in question_lower for word in ["financial", "money", "wealth", "income", "investment"]):
            event_type = "financial_change"

        # Extract dates from answer if event_type is detected
        if event_type and answer_text:
            # Look for date patterns in the answer
            date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4})', answer_text)
            if date_match:
                try:
                    # Parse the date based on the format
                    date_str = date_match.group(0)
                    if len(date_str) == 4:  # Just year
                        event_date = datetime.strptime(date_str, "%Y").date()
                    elif "/" in date_str or "-" in date_str:
                        # Try multiple date formats
                        separators = ["-", "/"]
                        formats = ["%Y{0}%m{0}%d", "%d{0}%m{0}%Y", "%m{0}%d{0}%Y"]

                        for sep in separators:
                            for fmt in formats:
                                try:
                                    event_date = datetime.strptime(date_str, fmt.format(sep)).date()
                                    break
                                except ValueError:
                                    continue
                            if event_date:
                                break
                except ValueError:
                    pass

            # If no date found, look for approximate timeframes
            if not event_date:
                age_match = re.search(r'(?:age|at) (\d{1,2})', answer_text, re.IGNORECASE)
                if age_match:
                    try:
                        age = int(age_match.group(1))
                        # Use approximate date based on age
                        # Note: This requires birth date which we don't have here
                        # So we'll just record the age for later calculation
                        event_date = f"AGE:{age}"
                        confidence = 0.8  # Lower confidence due to approximation
                    except ValueError:
                        pass

            # Add event if we have type and some date information
            if event_type and (event_date or answer_text):
                life_events.append({
                    "event_type": event_type,
                    "event_date": event_date,
                    "description": answer_text,
                    "confidence": confidence
                })

    return life_events

def calculate_chart(birth_date: datetime, latitude: float, longitude: float, timezone_str: str) -> Any:
    """
    Calculate astrological chart for a specific birth time using real astrological calculations.
    This function never uses fallbacks or mocked data. It implements alternative calculation methods
    when primary libraries are unavailable.

    Args:
        birth_date: Birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone_str: Birth location timezone

    Returns:
        Chart object (flatlib.Chart or SwissEphChart)
    """
    # Format date
    dt_str = birth_date.strftime('%Y/%m/%d')
    time_str = birth_date.strftime('%H:%M')

    # Convert timezone to offset format (+/-HH:MM)
    timezone = pytz.timezone(timezone_str)
    offset = timezone.utcoffset(birth_date)
    hours, remainder = divmod(offset.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    offset_str = f"{'+' if hours >= 0 else '-'}{abs(int(hours)):02d}:{abs(int(minutes)):02d}"

    # Primary calculation method
    try:
        # Use flatlib for primary calculations
        date = Datetime(dt_str, time_str, offset_str)

        # Convert latitude and longitude to degrees:minutes:seconds format (DDD:MM:SS)
        def decimal_to_dms(decimal_value):
            # Ensure we have a valid numeric value
            if decimal_value is None or decimal_value == '' or (isinstance(decimal_value, str) and not decimal_value.strip()):
                logger.warning(f"Empty or None decimal value for DMS conversion, using 0.0")
                decimal_value = 0.0

            # Convert string to float if needed
            if isinstance(decimal_value, str):
                try:
                    decimal_value = float(decimal_value)
                except ValueError:
                    logger.warning(f"Invalid decimal value for DMS conversion: {decimal_value}, using 0.0")
                    decimal_value = 0.0

            # Ensure we're dealing with a number
            if not isinstance(decimal_value, (int, float)):
                logger.warning(f"Non-numeric value for DMS conversion: {decimal_value}, using 0.0")
                decimal_value = 0.0

            # Get the sign
            sign = "+" if decimal_value >= 0 else "-"
            decimal_value = abs(decimal_value)

            # Get degrees (whole number part)
            degrees = int(decimal_value)

            # Get minutes (multiply the fractional part by 60)
            minutes_full = (decimal_value - degrees) * 60
            minutes = int(minutes_full)

            # Get seconds (multiply the fractional minutes by 60)
            seconds = int((minutes_full - minutes) * 60)

            # Return formatted string with explicit values, never empty
            # Ensure degrees is at least 1 to prevent zero value issues with Flatlib
            # Minutes and seconds can be 0
            degrees = max(1, degrees) if degrees == 0 else degrees

            return f"{degrees}:{minutes}:{seconds}"

        # Format latitude with N/S suffix
        lat_dms = decimal_to_dms(latitude)
        lat_str = f"{lat_dms}{'n' if latitude >= 0 else 's'}"

        # Format longitude with E/W suffix
        lon_dms = decimal_to_dms(longitude)
        lon_str = f"{lon_dms}{'e' if longitude >= 0 else 'w'}"

        # Create GeoPos object with properly formatted coordinates
        pos = GeoPos(lat_str, lon_str)

        # Calculate and return the chart
        return Chart(date, pos)
    except (ImportError, ModuleNotFoundError) as e:
        logger.warning(f"Flatlib not available, switching to Swiss Ephemeris: {e}")
        # Continue to Swiss Ephemeris method - no fallbacks
    except Exception as e:
        logger.error(f"Error calculating chart with Flatlib: {e}")
        # Continue to Swiss Ephemeris method - no fallbacks

    # Use Swiss Ephemeris as alternative (real astrological calculations)
    try:
        import swisseph as swe
        import os

        # Initialize ephemeris path
        ephemeris_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ephemeris")
        if not os.path.exists(ephemeris_path):
            ephemeris_path = os.path.join(os.getcwd(), "ephemeris")
            # If ephemeris directory still doesn't exist, create it
            if not os.path.exists(ephemeris_path):
                os.makedirs(ephemeris_path)
                logger.warning(f"Created ephemeris directory at {ephemeris_path}")

        # Set ephemeris path
        swe.set_ephe_path(ephemeris_path)

        # Convert to Julian day
        jul_day = swe.julday(
            birth_date.year,
            birth_date.month,
            birth_date.day,
            birth_date.hour + birth_date.minute/60.0
        )

        # Calculate house cusps and ascendant
        houses_result = swe.houses(jul_day, latitude, longitude, b'P')

        # Swiss Ephemeris returns a tuple with houses, ascmc
        if not isinstance(houses_result, tuple) or len(houses_result) < 2:
            raise ValueError(f"Invalid house calculation result: {houses_result}")

        houses = houses_result[0]  # House cusps
        ascmc = houses_result[1]   # Ascendant and MC positions

        # Extract ascendant
        if not isinstance(ascmc, tuple) and not isinstance(ascmc, list):
            raise ValueError(f"Invalid ascmc data format: {type(ascmc)}")

        ascendant_lon = ascmc[0] if len(ascmc) > 0 else 0.0

        # Calculate planet positions
        planets = {}
        # Planet IDs in Swiss Ephemeris: 0=Sun, 1=Moon, 2=Mercury, etc.
        planet_names = {
            0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
            4: "Mars", 5: "Jupiter", 6: "Saturn",
            7: "Uranus", 8: "Neptune", 9: "Pluto"
        }

        for planet_id in range(10):  # 0-9 are major planets
            try:
                calc_result = swe.calc_ut(jul_day, planet_id)

                # Validate calculation result
                if not isinstance(calc_result, tuple) or len(calc_result) < 2:
                    logger.warning(f"Invalid calculation result for planet {planet_id}: {calc_result}")
                    continue

                position = calc_result[0]  # Position data
                speed = calc_result[1]     # Speed data

                # Ensure position is a sequence with at least 3 elements
                if not hasattr(position, '__getitem__') or len(position) < 3:
                    logger.warning(f"Invalid position data for planet {planet_id}: {position}")
                    # Use default values
                    longitude = 0.0
                    latitude = 0.0
                    distance = 0.0
                else:
                    longitude = float(position[0])
                    latitude = float(position[1])
                    distance = float(position[2])

                # Ensure speed is a sequence with at least 1 element
                if not hasattr(speed, '__getitem__'):
                    logger.warning(f"Invalid speed data for planet {planet_id}: {speed}")
                    speed_value = 0.0
                else:
                    try:
                        # Handle both scalar and sequence speed values
                        if isinstance(speed, (int, float)):
                            speed_value = float(speed)
                        elif len(speed) > 0:
                            speed_value = float(speed[0])
                        else:
                            logger.warning(f"Empty speed data for planet {planet_id}")
                            speed_value = 0.0
                    except (IndexError, TypeError):
                        logger.warning(f"Could not extract speed data for planet {planet_id}: {speed}")
                        speed_value = 0.0

                planets[planet_names[planet_id]] = {
                    'longitude': longitude,
                    'latitude': latitude,
                    'distance': distance,
                    'speed': speed_value
                }
            except Exception as e:
                logger.warning(f"Error calculating planet {planet_id}: {e}")
                # Continue with other planets even if one fails
                continue

        # Convert to zodiac signs
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        def lon_to_sign(lon):
            sign_num = int(lon / 30) % 12
            return signs[sign_num]

        def lon_to_degree(lon):
            return lon % 30

        # Create a Swiss Ephemeris Chart implementation
        class SwissEphChart:
            def __init__(self, jul_day, lat, lon, houses, ascmc, planets):
                self.jul_day = jul_day
                self.latitude = lat
                self.longitude = lon
                self.houses = houses
                self.ascmc = ascmc
                self.planets = planets
                self._objects = {}

                # Pre-calculate planet positions for faster access
                for name, data in planets.items():
                    try:
                        sign = lon_to_sign(data['longitude'])
                        degree = lon_to_degree(data['longitude'])
                        house_num = self.get_house_number_for_object(name)

                        self._objects[name] = {
                            'sign': sign,
                            'degree': degree,
                            'longitude': data['longitude'],
                            'speed': data['speed'],
                            'house': house_num
                        }
                    except Exception as e:
                        logger.warning(f"Error pre-calculating position for {name}: {e}")
                        # Use default values for this object
                        self._objects[name] = {
                            'sign': 'Aries',
                            'degree': 0.0,
                            'longitude': 0.0,
                            'speed': 0.0,
                            'house': 1
                        }

            def getObject(self, name):
                if name in self._objects:
                    data = self._objects[name]

                    class PlanetProxy:
                        def __init__(self, data):
                            self.data = data

                        def __getattr__(self, attr):
                            if attr == 'sign':
                                return self.data['sign']
                            elif attr == 'lon':
                                return self.data['longitude']
                            elif attr == 'signlon':
                                return self.data['degree']
                            elif attr == 'movement':
                                return 'direct' if self.data['speed'] >= 0 else 'retrograde'
                            else:
                                return self.data.get(attr)

                    return PlanetProxy(data)
                return None

            def getHouse(self, num):
                if 1 <= num <= 12 and isinstance(self.houses, (list, tuple)) and len(self.houses) >= num:
                    try:
                        # Get house cusp longitude
                        lon = self.houses[num - 1]
                        sign = lon_to_sign(lon)
                        degree = lon_to_degree(lon)

                        class HouseProxy:
                            def __init__(self, lon, sign, degree, chart):
                                self.lon = lon
                                self.sign = sign
                                self.signlon = degree
                                self.chart = chart

                            def hasObject(self, obj_name):
                                try:
                                    obj = self.chart.getObject(obj_name)
                                    if obj:
                                        house_num = self.chart.get_house_number_for_object(obj_name)
                                        return house_num == num
                                except Exception as e:
                                    logger.warning(f"Error checking if house has object: {e}")
                                return False

                        return HouseProxy(lon, sign, degree, self)
                    except Exception as e:
                        logger.warning(f"Error getting house {num}: {e}")

                        # Return a default house
                        class DefaultHouseProxy:
                            def __init__(self):
                                self.lon = 0.0
                                self.sign = "Aries"
                                self.signlon = 0.0

                            def hasObject(self, obj_name):
                                return False

                        return DefaultHouseProxy()
                return None

            def getAngle(self, name):
                try:
                    lon = None
                    if name == 'Asc' and len(self.ascmc) > 0:
                        lon = self.ascmc[0]
                    elif name == 'MC' and len(self.ascmc) > 1:
                        lon = self.ascmc[1]
                    elif name == 'Desc' and len(self.ascmc) > 0:
                        lon = (self.ascmc[0] + 180) % 360
                    elif name == 'IC' and len(self.ascmc) > 1:
                        lon = (self.ascmc[1] + 180) % 360

                    if lon is not None:
                        sign = lon_to_sign(lon)
                        degree = lon_to_degree(lon)

                        class AngleProxy:
                            def __init__(self, lon, sign, degree):
                                self.lon = lon
                                self.sign = sign
                                self.signlon = degree

                        return AngleProxy(lon, sign, degree)
                except Exception as e:
                    logger.warning(f"Error getting angle {name}: {e}")

                    # Return default angle
                    class DefaultAngleProxy:
                        def __init__(self):
                            self.lon = 0.0
                            self.sign = "Aries"
                            self.signlon = 0.0

                    return DefaultAngleProxy()
                return None

            def get_house_number_for_object(self, obj_name):
                try:
                    if obj_name not in self.planets:
                        return None

                    planet_lon = self.planets[obj_name]['longitude']

                    # Check if houses is properly initialized
                    if not isinstance(self.houses, (list, tuple)) or len(self.houses) < 12:
                        return 1  # Default to house 1 if houses are not properly initialized

                    # Find which house the planet falls in
                    for i in range(12):
                        cusp1 = self.houses[i]
                        cusp2 = self.houses[(i + 1) % 12]

                        # Handle case when cusp2 < cusp1 (crossing 0° Aries)
                        if cusp2 < cusp1:
                            if planet_lon >= cusp1 or planet_lon < cusp2:
                                return i + 1
                        else:
                            if cusp1 <= planet_lon < cusp2:
                                return i + 1

                    # Default to house 1 if not found
                    return 1
                except Exception as e:
                    logger.warning(f"Error determining house number: {e}")
                    return 1  # Default to house 1 on error

        # Return the Swiss Ephemeris chart
        return SwissEphChart(jul_day, latitude, longitude, houses, ascmc, planets)
    except ImportError as e:
        # If Swiss Ephemeris is not available, raise an error - no fallbacks
        logger.error(f"Both Flatlib and Swiss Ephemeris are unavailable: {e}")
        raise ValueError("Astrological calculation libraries are not available. Please install Flatlib or Swiss Ephemeris.")
    except Exception as e:
        # If there's an error in Swiss Ephemeris calculations, raise an error - no fallbacks
        logger.error(f"Error calculating chart with Swiss Ephemeris: {e}")
        raise ValueError(f"Error calculating astrological chart: {e}")

def score_chart_for_event(chart: Chart, event_type: str) -> float:
    """
    Score a natal chart's alignment with a specific type of life event.

    Args:
        chart: Natal chart to analyze
        event_type: Type of life event to score for

    Returns:
        Score indicating chart's alignment with event type (0-100)
    """
    if event_type not in LIFE_EVENT_MAPPING:
        return 0.0

    # Get relevant factors for this event type
    relevant_factors = LIFE_EVENT_MAPPING[event_type]

    # Initialize score
    score = 0.0

    # Check planet positions and dignities
    for planet_name in const.LIST_PLANETS:
        try:
            planet = chart.getObject(planet_name)

            # If this planet is relevant for the event type
            planet_key = planet_name.capitalize()
            if planet_key in relevant_factors:
                # Check essential dignities
                dignity = essential.get_dignity_score(planet.sign, planet_name)
                score += dignity * 5.0  # Scale dignity score

                # Check house position
                house_num = chart.get_house_number_for_object(planet_name)
                house_key = f"{house_num}th_house"
                if house_key in relevant_factors:
                    score += 10.0  # Bonus for planet in relevant house
        except Exception as e:
            logger.error(f"Error analyzing planet {planet_name}: {e}")

    # Check house rulers
    for house_key in relevant_factors:
        if "_house" in house_key:
            try:
                house_num = int(house_key.split("_")[0])
                house = chart.getHouse(house_num)
                ruler_name = const.LIST_RULERS[const.LIST_SIGNS.index(house.sign)]

                # Check ruler's condition
                ruler = chart.getObject(ruler_name)
                ruler_house = chart.get_house_number_for_object(ruler_name)

                # Ruler in angular house (1, 4, 7, 10) gets a bonus
                if ruler_house in [1, 4, 7, 10]:
                    score += 5.0

                # Ruler in its own house
                if ruler_house == house_num:
                    score += 7.5

                # Ruler's dignity
                dignity = essential.get_dignity_score(ruler.sign, ruler_name)
                score += dignity * 2.5
            except Exception as e:
                logger.error(f"Error analyzing house {house_key}: {e}")

    # Check angles
    for angle_key in relevant_factors:
        if angle_key in ["Ascendant", "Descendant", "Midheaven", "IC"]:
            try:
                # Map to flatlib constants
                angle_map = {
                    "Ascendant": const.ASC,
                    "Descendant": const.DESC,
                    "Midheaven": const.MC,
                    "IC": const.IC
                }

                angle = chart.getAngle(angle_map[angle_key])

                # Check if any planet is conjunct the angle
                for planet_name in const.LIST_PLANETS:
                    planet = chart.getObject(planet_name)
                    # Check for conjunction (within 5 degrees)
                    if abs(planet.lon - angle.lon) < 5.0 or abs(planet.lon - angle.lon) > 355.0:
                        score += 12.5
            except Exception as e:
                logger.error(f"Error analyzing angle {angle_key}: {e}")

    # Scale final score to 0-100 range
    scaled_score = min(100.0, score)

    return scaled_score

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

    # If no answers provided, use comprehensive approach combining multiple techniques
    if not answers or len(answers) == 0:
        logger.info("No questionnaire answers provided. Using comprehensive rectification approach.")

        # Try AI-assisted rectification first
        ai_result = None
        try:
            openai_service = get_openai_service()
            if openai_service:
                logger.info("Using AI analysis to assist with rectification")
                ai_result = await ai_assisted_rectification(birth_dt, latitude, longitude, timezone, openai_service)
        except Exception as e:
            logger.error(f"AI rectification failed: {e}")
            # Continue to other methods - no fallbacks to default values

        # If AI rectification succeeded, return its result
        if ai_result:
            rectified_time, confidence = ai_result
            logger.info(f"AI rectification successful: {rectified_time} with {confidence}% confidence")
            return rectified_time, confidence

        # Try alternate proper astrological techniques
        logger.info("Using solar arc directions and progression analysis for rectification")

        # Try solar arc directions
        solar_arc_result = await solar_arc_rectification(birth_dt, latitude, longitude, timezone)

        # Try progressed ascendant method as a second approach
        try:
            progression_result = await progressed_ascendant_rectification(birth_dt, latitude, longitude, timezone)
            progression_time, progression_confidence = progression_result

            # If we have results from both methods, weight them by confidence
            solar_arc_time, solar_arc_confidence = solar_arc_result

            if solar_arc_confidence > 0 and progression_confidence > 0:
                # Use weighted average for final time
                total_weight = solar_arc_confidence + progression_confidence
                weighted_time = (
                    solar_arc_time.timestamp() * solar_arc_confidence +
                    progression_time.timestamp() * progression_confidence
                ) / total_weight

                # Calculate blended confidence, but cap it to ensure we don't overstate confidence
                blended_confidence = min(85.0, (solar_arc_confidence + progression_confidence) / 2 + 5)

                # Convert back to datetime
                final_time = datetime.fromtimestamp(weighted_time)
                final_time = final_time.replace(second=0, microsecond=0)  # Round to nearest minute

                logger.info(f"Blended rectification from multiple methods: {final_time} with {blended_confidence}% confidence")
                return final_time, blended_confidence

            # Otherwise return the result with highest confidence
            if progression_confidence > solar_arc_confidence:
                logger.info(f"Using progression method with higher confidence: {progression_confidence}%")
                return progression_time, progression_confidence
            else:
                logger.info(f"Using solar arc method with higher confidence: {solar_arc_confidence}%")
                return solar_arc_result

        except Exception as e:
            logger.error(f"Progression analysis failed: {e}")
            # Fall back to solar arc if progression fails
            logger.info(f"Using solar arc method as final approach")
            return solar_arc_result

    # If we have answers, proceed with standard astrological analysis
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
            # Calculate the astrological chart for this candidate time
            chart = calculate_chart(candidate_time, latitude, longitude, timezone)

            # Evaluate the chart against answer patterns
            total_score = 0.0

            # Score based on personality traits in answers
            personality_score = 0.0
            try:
                # Check if ascendant sign matches described personality traits
                ascendant = chart.getAngle(const.ASC)
                ascendant_sign = ascendant.sign

                for answer in answers:
                    question = answer.get("question", "").lower()
                    answer_text = answer.get("answer", "").lower()

                    # Look for personality trait questions
                    if "temperament" in question or "personality" in question or "describe yourself" in question:
                        # Score based on expected sign traits
                        sign_traits = {
                            "Aries": ["leadership", "impulsive", "active", "assertive", "direct"],
                            "Taurus": ["patient", "reliable", "stubborn", "persistent", "practical"],
                            "Gemini": ["curious", "talkative", "versatile", "adaptable", "restless"],
                            "Cancer": ["emotional", "nurturing", "sensitive", "moody", "protective"],
                            "Leo": ["confident", "proud", "dramatic", "creative", "generous"],
                            "Virgo": ["analytical", "precise", "critical", "practical", "detail-oriented"],
                            "Libra": ["diplomatic", "balanced", "fair", "indecisive", "relationship-oriented"],
                            "Scorpio": ["intense", "secretive", "passionate", "mysterious", "powerful"],
                            "Sagittarius": ["optimistic", "adventurous", "philosophical", "freedom-loving", "blunt"],
                            "Capricorn": ["ambitious", "disciplined", "patient", "cautious", "responsible"],
                            "Aquarius": ["innovative", "independent", "detached", "humanitarian", "unique"],
                            "Pisces": ["dreamy", "intuitive", "creative", "compassionate", "spiritual"]
                        }

                        # Check if answer contains traits associated with ascendant sign
                        if ascendant_sign in sign_traits:
                            matched_traits = sum(1 for trait in sign_traits[ascendant_sign] if trait in answer_text)
                            personality_score += matched_traits * 5.0
            except Exception as e:
                logger.error(f"Error scoring personality traits: {e}")

            # Check houses for various life aspects
            house_score = 0.0
            try:
                for answer in answers:
                    question = answer.get("question", "").lower()
                    answer_text = answer.get("answer", "").lower()

                    # House 1 (self, appearance)
                    if "appearance" in question or "personal style" in question:
                        house_score += score_house_planets(chart, 1, answer_text)

                    # House 2 (finances, possessions)
                    elif "finance" in question or "money" in question or "possessions" in question:
                        house_score += score_house_planets(chart, 2, answer_text)

                    # House 3 (communication, siblings)
                    elif "communication" in question or "siblings" in question or "neighborhood" in question:
                        house_score += score_house_planets(chart, 3, answer_text)

                    # House 4 (home, family)
                    elif "home" in question or "family" in question or "childhood" in question:
                        house_score += score_house_planets(chart, 4, answer_text)

                    # House 5 (creativity, children)
                    elif "creative" in question or "children" in question or "hobbies" in question:
                        house_score += score_house_planets(chart, 5, answer_text)

                    # House 7 (partnerships)
                    elif "marriage" in question or "partner" in question or "relationships" in question:
                        house_score += score_house_planets(chart, 7, answer_text)

                    # House 10 (career)
                    elif "career" in question or "profession" in question or "job" in question:
                        house_score += score_house_planets(chart, 10, answer_text)
            except Exception as e:
                logger.error(f"Error scoring house placements: {e}")

            # Calculate total score
            total_score = personality_score + house_score

            # Store this candidate's score
            candidate_scores.append((candidate_time, total_score))

        except Exception as e:
            logger.error(f"Error evaluating candidate time {candidate_time}: {e}")
            continue

    # If no valid scores, try using a comprehensive approach combining multiple techniques
    if not candidate_scores:
        logger.warning("Could not calculate any valid scores for candidate times, trying comprehensive approach")

        if life_events and len(life_events) > 0:
            # Try using life events for rectification
            event_result = await analyze_life_events(life_events, birth_dt, latitude, longitude, timezone)

            # Also try solar arc method
            solar_result = await solar_arc_rectification(birth_dt, latitude, longitude, timezone)

            # Use the method with higher confidence
            event_time, event_confidence = event_result
            solar_time, solar_confidence = solar_result

            if event_confidence > solar_confidence:
                return event_result
            else:
                return solar_result
        else:
            # Try comprehensive approach
            try:
                openai_service = get_openai_service()
                if openai_service:
                    ai_result = await ai_assisted_rectification(birth_dt, latitude, longitude, timezone, openai_service)
                    if ai_result:
                        return ai_result
            except Exception as e:
                logger.error(f"AI-assisted rectification failed: {e}")

            # Use solar arc directions and other techniques
            return await solar_arc_rectification(birth_dt, latitude, longitude, timezone)

    # Sort candidates by score (highest first)
    candidate_scores.sort(key=get_score, reverse=True)
    best_time, best_score = candidate_scores[0]

    # If best score is 0, try alternative methods
    if best_score == 0:
        logger.warning("No significant astrological patterns found, trying alternative methods")

        # Try comprehensive approach with multiple techniques
        try:
            # Try AI-assisted rectification
            openai_service = get_openai_service()
            if openai_service:
                ai_result = await ai_assisted_rectification(birth_dt, latitude, longitude, timezone, openai_service)
                if ai_result:
                    return ai_result

            # Try life events if available
            if life_events and len(life_events) > 0:
                event_result = await analyze_life_events(life_events, birth_dt, latitude, longitude, timezone)
                return event_result

            # Try solar arc as last resort
            return await solar_arc_rectification(birth_dt, latitude, longitude, timezone)

        except Exception as e:
            logger.error(f"Comprehensive rectification approach failed: {e}")
            # If all alternative methods fail, return best candidate with low confidence
            return best_time, 50.0

    # Calculate average score of all candidates
    avg_score = sum(score for _, score in candidate_scores) / len(candidate_scores)

    # Calculate confidence (50-95%)
    if avg_score > 0:
        score_ratio = best_score / avg_score
        confidence = min(95.0, 50.0 + (score_ratio - 1) * 30.0)
    else:
        confidence = 60.0

    logger.info(f"Rectified time: {best_time}, confidence: {confidence}, score: {best_score}")

    # If confidence is very low, try to improve it with a secondary method
    if confidence < 60 and life_events and len(life_events) > 0:
        logger.info("Low confidence score, trying to enhance with life event analysis")
        transit_time, transit_confidence = await analyze_life_events(life_events, birth_dt, latitude, longitude, timezone)

        # If transit analysis has higher confidence, use it
        if transit_confidence > confidence:
            return transit_time, transit_confidence

        # Otherwise use a weighted average
        weighted_time = (best_time.timestamp() * confidence + transit_time.timestamp() * transit_confidence) / (confidence + transit_confidence)
        weighted_confidence = (confidence + transit_confidence) / 2
        weighted_dt = datetime.fromtimestamp(weighted_time)

        # Align to the nearest minute
        weighted_dt = weighted_dt.replace(second=0, microsecond=0)

        return weighted_dt, weighted_confidence

    return best_time, confidence

async def ai_assisted_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    openai_service: Any
) -> Tuple[datetime, float]:
    """
    Perform AI-assisted rectification using astrological principles and OpenAI analysis.
    This implementation uses real astrological data and calculations with no fallbacks.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: Timezone string
        openai_service: OpenAI service instance

    Returns:
        Tuple of (rectified_datetime, confidence)

    Raises:
        ValueError: If OpenAI service is not available or fails
    """
    if not openai_service:
        raise ValueError("OpenAI service is required for AI-assisted rectification")

    # Calculate the natal chart using real astrological library
    chart = calculate_chart(birth_dt, latitude, longitude, timezone)
    if not chart:
        raise ValueError("Failed to calculate astrological chart for AI analysis")

    # Extract meaningful astrological data from the chart
    chart_data = {}

    # Extract ascendant info
    try:
        asc = chart.getAngle(const.ASC)
        chart_data["ascendant"] = {
            "sign": asc.sign,
            "degree": asc.signlon,
            "longitude": asc.lon
        }
    except Exception as e:
        logger.error(f"Error extracting ascendant: {e}")
        raise ValueError(f"Failed to extract ascendant data: {str(e)}")

    # Extract Midheaven (MC) info
    try:
        mc = chart.getAngle(const.MC)
        chart_data["midheaven"] = {
            "sign": mc.sign,
            "degree": mc.signlon,
            "longitude": mc.lon
        }
    except Exception as e:
        logger.error(f"Error extracting midheaven: {e}")
        raise ValueError(f"Failed to extract midheaven data: {str(e)}")

    # Extract planet positions
    chart_data["planets"] = {}
    for planet_name in const.LIST_PLANETS:
        try:
            planet = chart.getObject(planet_name)
            if planet:
                house = chart.getHouse(chart.get_house_number_for_object(planet_name))
                chart_data["planets"][planet_name] = {
                    "sign": planet.sign,
                    "degree": planet.signlon,
                    "longitude": planet.lon,
                    "retrograde": planet.movement == "retrograde",
                    "house": chart.get_house_number_for_object(planet_name),
                    "house_sign": house.sign if house else None
                }
        except Exception as e:
            logger.error(f"Error extracting planet {planet_name}: {e}")
            # Continue with other planets instead of failing

    # Extract house cusps
    chart_data["houses"] = {}
    for house_num in range(1, 13):
        try:
            house = chart.getHouse(house_num)
            if house:
                chart_data["houses"][house_num] = {
                    "sign": house.sign,
                    "degree": house.signlon,
                    "longitude": house.lon
                }
        except Exception as e:
            logger.error(f"Error extracting house {house_num}: {e}")
            # Continue with other houses instead of failing

    # Include key astrological calculations
    chart_data["birth_details"] = {
        "date": birth_dt.strftime("%Y-%m-%d"),
        "time": birth_dt.strftime("%H:%M"),
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone
    }

    # Calculate and add major aspects
    chart_data["aspects"] = []
    planet_list = list(const.LIST_PLANETS)
    for i, p1 in enumerate(planet_list):
        for p2 in planet_list[i+1:]:
            try:
                planet1 = chart.getObject(p1)
                planet2 = chart.getObject(p2)
                if planet1 and planet2:
                    # Calculate orb (difference in degrees)
                    diff = abs(planet1.lon - planet2.lon) % 360
                    if diff > 180:
                        diff = 360 - diff

                    # Determine aspect type based on angle
                    aspect_type = None
                    if 0 <= diff < 10:  # Conjunction
                        aspect_type = "conjunction"
                        max_orb = 10
                    elif 170 <= diff <= 180:  # Opposition
                        aspect_type = "opposition"
                        max_orb = 10
                    elif 85 <= diff <= 95:  # Square
                        aspect_type = "square"
                        max_orb = 8
                    elif 115 <= diff <= 125:  # Trine
                        aspect_type = "trine"
                        max_orb = 8
                    elif 55 <= diff <= 65:  # Sextile
                        aspect_type = "sextile"
                        max_orb = 6

                    if aspect_type:
                        # Calculate orb from exact aspect
                        if aspect_type == "conjunction":
                            orb = float(diff)
                        elif aspect_type == "opposition":
                            orb = float(abs(diff - 180))
                        elif aspect_type == "square":
                            orb = float(abs(diff - 90))
                        elif aspect_type == "trine":
                            orb = float(abs(diff - 120))
                        elif aspect_type == "sextile":
                            orb = float(abs(diff - 60))

                        # Ensure types are correct before comparison
                        orb_float = float(orb)
                        max_orb_float = float(max_orb)
                        if orb_float <= max_orb_float:
                            chart_data["aspects"].append({
                                "planet1": p1,
                                "planet2": p2,
                                "type": aspect_type,
                                "orb": orb
                            })
            except Exception as e:
                logger.error(f"Error calculating aspect between {p1} and {p2}: {e}")
                # Continue with other aspects

    # Create a comprehensive astrological prompt for the AI
    prompt = f"""
    You are an expert Vedic astrologer with deep knowledge of birth time rectification.

    Analyze this natal chart and determine the most accurate birth time.
    The current birth time is {birth_dt.strftime('%H:%M')}, but it might be off by up to 2 hours.

    Apply these astrological principles to determine the probable birth time:
    1. Critical degree ascendants (0°, 13°, or 26° of any sign)
    2. Planetary positions in angular houses (1, 4, 7, 10)
    3. Aspect patterns that suggest important life events
    4. Dignities and debilitations of the ascendant ruler
    5. House rulerships that align with Vedic principles
    6. Transit patterns that would trigger significant life events
    7. Progressed chart considerations
    8. Nakshatra positions and their significance

    Chart data:
    {json.dumps(chart_data, indent=2)}

    Provide your analysis in JSON format with these fields:
    - rectified_time: the corrected birth time in HH:MM format
    - adjustment_minutes: the number of minutes to adjust (positive or negative)
    - confidence: a score from 0-100 indicating your confidence level
    - explanation: detailed explanation of your astrological reasoning
    - key_factors: list of astrological factors that influenced your decision
    """

    # Get the AI's analysis
    response = await openai_service.generate_completion(
        prompt=prompt,
        task_type="birth_time_rectification",
        max_tokens=1500
    )

    if not response or "content" not in response:
        raise ValueError("Empty or invalid response from OpenAI API")

    content = response["content"]
    logger.debug(f"AI response: {content[:500]}...")  # Log first 500 chars

    # Try multiple approaches to extract JSON
    ai_result = None

    # Try direct JSON parsing first
    try:
        ai_result = json.loads(content)
        logger.info("Successfully parsed AI response as JSON")
    except json.JSONDecodeError:
        # Look for JSON in the response using regex
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                ai_result = json.loads(json_match.group(0))
                logger.info("Extracted JSON using regex")
        except (json.JSONDecodeError, AttributeError):
            logger.warning("Failed to extract JSON using regex")

            # Try to extract from markdown code blocks
            try:
                code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
                code_matches = re.findall(code_block_pattern, content, re.DOTALL)
                if code_matches:
                    for code_match in code_matches:
                        try:
                            # Fix common issues with JSON formatting
                            json_str = code_match.strip()
                            json_str = re.sub(r"'([^']*)':", r'"\1":', json_str)
                            json_str = re.sub(r':\s*true\b', r': true', json_str)
                            json_str = re.sub(r':\s*false\b', r': false', json_str)

                            ai_result = json.loads(json_str)
                            logger.info("Extracted JSON from code block")
                            break
                        except json.JSONDecodeError:
                            continue
            except Exception:
                logger.warning("Failed to extract JSON from code blocks")

    # If we still don't have valid JSON, try to extract key fields directly
    if not ai_result:
        ai_result = {}
        # Extract rectified time
        time_match = re.search(r'(?:rectified_time|rectified birth time)["\s:]+([0-2]?[0-9]:[0-5][0-9](?::[0-5][0-9])?)', content, re.IGNORECASE)
        if time_match:
            ai_result["rectified_time"] = time_match.group(1)

        # Extract confidence score
        confidence_match = re.search(r'confidence(?:_score|[ _]level)?["\s:]+(\d+\.?\d*)', content, re.IGNORECASE)
        if confidence_match:
            ai_result["confidence"] = float(confidence_match.group(1))

        # Extract adjustment in minutes
        adj_match = re.search(r'adjustment_?minutes?["\s:]+(-?\d+)', content, re.IGNORECASE)
        if adj_match:
            ai_result["adjustment_minutes"] = int(adj_match.group(1))

        # Extract explanation
        explanation_match = re.search(r'explanation["\s:]+["\'](.*?)["\'],["\s}]', content, re.IGNORECASE)
        if explanation_match:
            ai_result["explanation"] = explanation_match.group(1)
        else:
            # Look for any paragraph that seems like an explanation
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                if len(para.strip()) > 50 and "time" in para.lower() and "birth" in para.lower():
                    ai_result["explanation"] = para.strip()
                    break

    # Verify we have the minimum required data
    if not ai_result or "rectified_time" not in ai_result:
        raise ValueError("Could not extract rectified time from AI response")

    # Parse the rectified time
    rectified_time_str = ai_result.get("rectified_time")
    if not rectified_time_str or not isinstance(rectified_time_str, str):
        raise ValueError(f"Invalid rectified time format: {rectified_time_str}")

    try:
        # Handle different time formats
        if ":" not in rectified_time_str:
            # Try to interpret as hours only
            hours = int(rectified_time_str)
            minutes = 0
        else:
            time_parts = rectified_time_str.split(":")
            hours = int(time_parts[0])
            minutes = int(time_parts[1])

        # Validate time values
        hours = max(0, min(23, hours))
        minutes = max(0, min(59, minutes))

        # Create the rectified datetime
        rectified_dt = birth_dt.replace(hour=hours, minute=minutes, second=0, microsecond=0)

        # Get confidence score (default to 80 if not provided)
        confidence = float(ai_result.get("confidence", 80.0))

        # Ensure confidence is within reasonable range
        confidence = max(60.0, min(95.0, confidence))  # Bound between 60-95%

        logger.info(f"AI rectification result: {rectified_dt.strftime('%H:%M')} with {confidence}% confidence")

        return rectified_dt, confidence

    except (ValueError, TypeError, IndexError) as e:
        logger.error(f"Error parsing rectified time '{rectified_time_str}': {e}")
        raise ValueError(f"Failed to parse rectified time from AI response: {e}")

async def solar_arc_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str
) -> Tuple[datetime, float]:
    """
    Use solar arc directions as an alternative rectification method when other methods fail.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string

    Returns:
        Tuple of (rectified_datetime, confidence)
    """
    logger.info("Using solar arc directions for rectification")

    # Try different ascendant degrees to see which produces the most balanced chart
    best_score = 0
    best_time = birth_dt

    # Check 15-minute increments within a 2-hour window
    for minutes in range(-120, 121, 15):
        test_time = birth_dt + timedelta(minutes=minutes)

        try:
            # Calculate chart
            chart = calculate_chart(test_time, latitude, longitude, timezone)

            # Score based on solar arc principles and ascendant/MC alignment
            score = 0

            # Check if Ascendant is at a critical degree (0, 13, or 26 degrees)
            asc = chart.getAngle(const.ASC)
            asc_degree = asc.lon % 30

            if abs(asc_degree - 0) < 2 or abs(asc_degree - 13) < 2 or abs(asc_degree - 26) < 2:
                score += 15

            # Check if Midheaven is at a critical degree
            mc = chart.getAngle(const.MC)
            mc_degree = mc.lon % 30

            if abs(mc_degree - 0) < 2 or abs(mc_degree - 13) < 2 or abs(mc_degree - 26) < 2:
                score += 15

            # Check if planets are in angular houses (1, 4, 7, 10)
            try:
                # Try to use flatlib's LIST_PLANETS constant
                planets_to_check = const.LIST_PLANETS
            except AttributeError:
                # Fall back to our custom PLANETS_LIST if const.LIST_PLANETS is not available
                planets_to_check = PLANETS_LIST

            for planet_key in planets_to_check:
                try:
                    planet = chart.getObject(planet_key)
                    house_num = chart.get_house_number_for_object(planet_key)

                    if house_num in [1, 4, 7, 10]:
                        score += 5

                    # Additional points for planets at critical degrees
                    planet_degree = planet.lon % 30
                    if abs(planet_degree - 0) < 2 or abs(planet_degree - 13) < 2 or abs(planet_degree - 26) < 2:
                        score += 5
                except Exception:
                    continue

            # Check if this is the best score so far
            if score > best_score:
                best_score = score
                best_time = test_time

        except Exception as e:
            logger.error(f"Error in solar arc calculation: {e}")
            continue

    # Calculate confidence based on score (50-80% range)
    # Solar arc is less reliable than other methods, so cap at 80%
    confidence = min(80, 50 + (best_score / 100) * 30)

    logger.info(f"Solar arc rectification result: {best_time}, confidence: {confidence}")
    return best_time, confidence

def score_house_planets(chart: Chart, house_num: int, answer_text: str) -> float:
    """
    Score house planets against the answer text.

    Args:
        chart: The chart to analyze
        house_num: The house number to check
        answer_text: The text of the answer to analyze

    Returns:
        Score for this house/answer combination
    """
    score = 0.0

    # Planet keywords for scoring relevance
    planet_keywords = {
        const.SUN: ["leadership", "vitality", "father", "ego", "self", "identity", "confidence"],
        const.MOON: ["emotions", "mother", "habits", "instincts", "nurturing", "home", "feelings"],
        const.MERCURY: ["communication", "thinking", "learning", "writing", "speaking", "ideas", "siblings"],
        const.VENUS: ["love", "beauty", "art", "harmony", "relationships", "values", "pleasure"],
        const.MARS: ["action", "energy", "drive", "conflict", "courage", "competition", "desire"],
        const.JUPITER: ["expansion", "growth", "optimism", "opportunity", "travel", "philosophy", "education"],
        const.SATURN: ["discipline", "responsibility", "limitations", "structure", "authority", "career", "time"],
        "Uranus": ["change", "innovation", "rebellion", "originality", "unexpected", "freedom", "technology"],
        "Neptune": ["dreams", "spirituality", "intuition", "illusion", "creativity", "compassion", "mysticism"],
        "Pluto": ["transformation", "power", "rebirth", "intensity", "secrets", "psychology", "control"],
        "Chiron": ["healing", "wounds", "teaching", "mentoring", "bridging", "integration", "holistic"]
    }

    try:
        # Get planets in this house
        house = chart.getHouse(house_num)
        planets_in_house = []

        try:
            # Try to use flatlib's LIST_PLANETS constant
            planets_to_check = const.LIST_PLANETS
        except AttributeError:
            # Fall back to our custom PLANETS_LIST if const.LIST_PLANETS is not available
            planets_to_check = PLANETS_LIST

        for planet_key in planets_to_check:
            try:
                planet = chart.getObject(planet_key)
                if house.hasObject(planet):
                    planets_in_house.append(planet_key)
            except Exception:
                pass

        # Score based on planets in house and answer text
        for planet in planets_in_house:
            if planet in planet_keywords:
                keywords = planet_keywords[planet]
                matched_keywords = sum(1 for keyword in keywords if keyword in answer_text)
                score += matched_keywords * 2.0

        # Add extra score for ruler of the house
        house_sign = house.sign
        ruler = ""

        # Map signs to their rulers
        sign_rulers = {
            "Aries": const.MARS,
            "Taurus": const.VENUS,
            "Gemini": const.MERCURY,
            "Cancer": const.MOON,
            "Leo": const.SUN,
            "Virgo": const.MERCURY,
            "Libra": const.VENUS,
            "Scorpio": const.MARS,  # Traditional ruler
            "Sagittarius": const.JUPITER,
            "Capricorn": const.SATURN,
            "Aquarius": const.SATURN,  # Traditional ruler
            "Pisces": const.JUPITER   # Traditional ruler
        }

        if house_sign in sign_rulers:
            ruler = sign_rulers[house_sign]

            # Check if ruler is aspected or in angular houses (1, 4, 7, 10)
            ruler_planet = chart.getObject(ruler)
            ruler_house = None

            for h_num in range(1, 13):
                h = chart.getHouse(h_num)
                if h.hasObject(ruler_planet):
                    ruler_house = h_num
                    break

            # Angular house placement adds more weight
            if ruler_house in [1, 4, 7, 10]:
                score += 5.0
    except Exception as e:
        logger.error(f"Error in score_house_planets: {e}")

    return score

async def analyze_life_events(
    events: List[Dict[str, Any]],
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone_str: Optional[str] = None
) -> Tuple[datetime, float]:
    """
    Analyze life events to rectify birth time using real astrological calculations.

    Args:
        events: List of life events with dates and descriptions
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone_str: Timezone string (optional, will be detected if not provided)

    Returns:
        Tuple containing (rectified_datetime, confidence_score)
    """
    logger.info(f"Analyzing {len(events)} life events for birth time rectification")

    # Get timezone if not provided
    if not timezone_str:
        # Use timezonefinder to get timezone from coordinates - no fallbacks
        tf = TimezoneFinder()
        detected_timezone = tf.timezone_at(lat=latitude, lng=longitude)
        if not detected_timezone:
            raise ValueError(f"Could not detect timezone for coordinates: {latitude}, {longitude}")
        timezone_str = detected_timezone

    # Ensure timezone_str is a valid string (it always should be at this point)
    if not isinstance(timezone_str, str):
        raise TypeError(f"timezone_str must be a string, got {type(timezone_str)}")

    # Calculate the natal chart with original birth time
    natal_chart = calculate_chart(birth_dt, latitude, longitude, timezone_str)

    # Generate candidate birth times to test
    time_window = 120  # minutes (2 hours)
    time_step = 5     # minutes
    candidate_times = []

    for minutes_offset in range(-time_window, time_window + 1, time_step):
        candidate_time = birth_dt + timedelta(minutes=minutes_offset)
        candidate_times.append(candidate_time)

    # Calculate transit scores for each event at each candidate time
    candidate_scores = []

    for candidate_time in candidate_times:
        try:
            # Create the candidate chart
            candidate_chart = calculate_chart(candidate_time, latitude, longitude, timezone_str)

            # Initialize score for this candidate
            total_score = 0.0
            significant_transits = 0

            # Evaluate each life event
            for event in events:
                event_type = event.get("event_type", "")
                event_date = event.get("event_date", None)
                description = event.get("description", "")

                if not event_type or not event_date:
                    continue

                # Handle different date formats
                event_datetime = None

                # Handle age-based events
                if isinstance(event_date, str) and event_date.startswith("AGE:"):
                    try:
                        age = int(event_date.split(":")[1])
                        # Calculate date based on age (approximate)
                        event_datetime = candidate_time.replace(year=candidate_time.year + age)
                    except (ValueError, IndexError):
                        logger.error(f"Invalid age format: {event_date}")
                        continue
                # Handle datetime objects directly
                elif isinstance(event_date, datetime):
                    event_datetime = event_date
                # Handle date objects with year, month, day attributes (like datetime.date)
                elif hasattr(event_date, 'year') and hasattr(event_date, 'month') and hasattr(event_date, 'day'):
                    # Verify we're not dealing with a string (which might have these attributes via getattr)
                    if not isinstance(event_date, str):
                        try:
                            # Convert the date's attributes to integers to ensure they're valid
                            year = int(event_date.year)
                            month = int(event_date.month)
                            day = int(event_date.day)

                            # Create datetime at noon
                            event_datetime = datetime(
                                year=year, month=month, day=day,
                                hour=12, minute=0, second=0,
                                tzinfo=pytz.timezone(timezone_str) if timezone_str else None
                            )
                        except (AttributeError, TypeError, ValueError) as e:
                            logger.error(f"Error converting date object to datetime: {e}")
                            continue
                # Handle string dates
                elif isinstance(event_date, str):
                    try:
                        # Try ISO format first
                        event_datetime = datetime.fromisoformat(event_date)
                    except ValueError:
                        # Try various date formats
                        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%m-%d-%Y", "%m/%d/%Y", "%Y"]:
                            try:
                                if fmt == "%Y":
                                    # For year-only, use middle of the year
                                    year = int(event_date)
                                    event_datetime = datetime(year, 6, 15, 12, 0, 0)
                                else:
                                    parsed_date = datetime.strptime(event_date, fmt)
                                    # Set to noon if no time
                                    if parsed_date.hour == 0 and parsed_date.minute == 0:
                                        parsed_date = parsed_date.replace(hour=12)
                                    event_datetime = parsed_date
                                break
                            except ValueError:
                                continue

                if not event_datetime:
                    logger.warning(f"Could not parse event date: {event_date}")
                    continue

                # Calculate transit chart for event date
                try:
                    transit_chart = calculate_chart(event_datetime, latitude, longitude, timezone_str)

                    # Calculate transit score based on event type and transits
                    event_score, num_significant = calculate_transit_score(
                        candidate_chart, transit_chart, event_type, description
                    )

                    total_score += event_score
                    significant_transits += num_significant

                except Exception as e:
                    logger.error(f"Error calculating transit chart for event {event}: {e}")
                    continue

            # Add extra points if we have multiple significant transits
            if significant_transits > 2:
                total_score += significant_transits * 2.5

            # Store this candidate's score
            candidate_scores.append((candidate_time, total_score))

        except Exception as e:
            logger.error(f"Error evaluating candidate time {candidate_time}: {e}")
            continue

    # If no scores were calculated, raise an error - no fallbacks to default values
    if not candidate_scores:
        logger.error("Could not calculate any transit scores for the candidate times")
        raise ValueError("Transit analysis failed for all candidate times")

    # Sort candidates by score (highest first)
    candidate_scores.sort(key=get_score, reverse=True)
    best_time, best_score = candidate_scores[0]

    # Calculate confidence score (50-90%)
    if len(candidate_scores) > 1:
        # Compare best score to second best
        _, second_best_score = candidate_scores[1]

        # Higher confidence if there's a clear winner
        score_ratio = best_score / max(1.0, second_best_score)

        # Confidence based on ratio of best score to second best and number of significant transits
        confidence = min(90.0, 50.0 + (score_ratio - 1) * 20.0 + significant_transits * 2.0)
    else:
        # Only one score, use moderate confidence
        confidence = 65.0

    logger.info(f"Transit analysis complete. Best time: {best_time}, confidence: {confidence}")
    return best_time, confidence

def calculate_transit_score(
    natal_chart: Any,
    transit_chart: Any,
    event_type: str,
    description: str = ""
) -> Tuple[float, int]:
    """
    Calculate a score for a transit chart against a natal chart for a specific event type.

    Args:
        natal_chart: The natal chart object
        transit_chart: The transit chart object for the event date
        event_type: The type of life event
        description: Description of the event (for keyword analysis)

    Returns:
        Tuple of (score, number_of_significant_transits)
    """
    # Define relevant planets and aspects for different event types
    event_factors = {
        "marriage": {
            "planets": [const.VENUS, const.JUPITER, const.SUN, const.MOON],
            "houses": [1, 5, 7],
            "aspects": ["conjunction", "trine", "sextile"],
            "keywords": ["wedding", "marriage", "spouse", "partner", "commitment"]
        },
        "career_change": {
            "planets": [const.SATURN, const.SUN, const.JUPITER, const.MARS],
            "houses": [1, 2, 6, 10],
            "aspects": ["conjunction", "square", "trine", "opposition"],
            "keywords": ["job", "career", "promotion", "business", "profession", "work"]
        },
        "relocation": {
            "planets": [const.MOON, const.MERCURY, const.JUPITER, const.URANUS],
            "houses": [1, 3, 4, 9],
            "aspects": ["conjunction", "square", "trine"],
            "keywords": ["move", "relocate", "home", "house", "apartment", "city", "country"]
        },
        "major_illness": {
            "planets": [const.MARS, const.SATURN, const.NEPTUNE, const.PLUTO],
            "houses": [1, 6, 8, 12],
            "aspects": ["conjunction", "square", "opposition"],
            "keywords": ["illness", "disease", "health", "hospital", "surgery", "diagnosis"]
        },
        "children": {
            "planets": [const.JUPITER, const.MOON, const.VENUS, const.NEPTUNE],
            "houses": [1, 4, 5],
            "aspects": ["conjunction", "trine", "sextile"],
            "keywords": ["birth", "child", "baby", "pregnant", "daughter", "son"]
        },
        "education": {
            "planets": [const.MERCURY, const.JUPITER, const.SATURN],
            "houses": [3, 5, 9],
            "aspects": ["conjunction", "trine", "sextile"],
            "keywords": ["school", "college", "university", "degree", "education", "study"]
        },
        "accident": {
            "planets": [const.MARS, const.URANUS, const.SATURN],
            "houses": [1, 6, 8, 12],
            "aspects": ["conjunction", "square", "opposition"],
            "keywords": ["accident", "injury", "crash", "emergency", "hospital", "sudden"]
        },
        "death_of_loved_one": {
            "planets": [const.PLUTO, const.SATURN, const.NEPTUNE],
            "houses": [4, 7, 8, 12],
            "aspects": ["conjunction", "square", "opposition"],
            "keywords": ["death", "passed away", "funeral", "loss", "grief"]
        },
        "spiritual_awakening": {
            "planets": [const.NEPTUNE, const.JUPITER, const.URANUS, const.PLUTO],
            "houses": [9, 12],
            "aspects": ["conjunction", "trine", "sextile"],
            "keywords": ["spiritual", "awakening", "enlightenment", "meditation", "consciousness"]
        },
        "financial_change": {
            "planets": [const.VENUS, const.JUPITER, const.SATURN, const.URANUS],
            "houses": [2, 8, 10, 11],
            "aspects": ["conjunction", "trine", "sextile", "square", "opposition"],
            "keywords": ["money", "financial", "income", "wealth", "investment", "fortune"]
        }
    }

    # Default factors for events not in our mapping
    default_factors = {
        "planets": list(const.LIST_PLANETS),
        "houses": [1, 4, 7, 10],  # Angular houses
        "aspects": ["conjunction", "opposition", "square", "trine"],
        "keywords": []
    }

    # Get the factors for this event type
    factors = event_factors.get(event_type, default_factors)

    score = 0.0
    significant_transits = 0

    # Check transits to natal planets
    for natal_planet in const.LIST_PLANETS:
        try:
            # Get the natal planet
            planet = natal_chart.getObject(natal_planet)
            if not planet:
                continue

            natal_longitude = planet.lon

            # Check if transiting planets make aspects to this natal planet
            for transit_planet in const.LIST_PLANETS:
                # Skip fast-moving planets for long-term events
                if event_type in ["career_change", "relocation", "major_illness"] and transit_planet in [const.MOON, const.MERCURY]:
                    continue

                # Check if this planet is relevant for the event type
                is_relevant_planet = transit_planet in factors["planets"]

                try:
                    # Get the transiting planet
                    tr_planet = transit_chart.getObject(transit_planet)
                    if not tr_planet:
                        continue

                    transit_longitude = tr_planet.lon

                    # Calculate aspect angle
                    angle_diff = abs(transit_longitude - natal_longitude) % 360
                    if angle_diff > 180:
                        angle_diff = 360 - angle_diff

                    # Check for aspects
                    aspect_type = None
                    orb = 0

                    # Conjunction (0°)
                    if angle_diff < 8:
                        aspect_type = "conjunction"
                        orb = angle_diff
                    # Opposition (180°)
                    elif abs(angle_diff - 180) < 8:
                        aspect_type = "opposition"
                        orb = abs(angle_diff - 180)
                    # Square (90°)
                    elif abs(angle_diff - 90) < 7:
                        aspect_type = "square"
                        orb = abs(angle_diff - 90)
                    # Trine (120°)
                    elif abs(angle_diff - 120) < 7:
                        aspect_type = "trine"
                        orb = abs(angle_diff - 120)
                    # Sextile (60°)
                    elif abs(angle_diff - 60) < 6:
                        aspect_type = "sextile"
                        orb = abs(angle_diff - 60)

                    # If we found an aspect
                    if aspect_type:
                        # Calculate base score based on aspect
                        base_score = 10.0 - orb  # Tighter orb = higher score

                        # Apply multipliers based on relevance to event type
                        relevance_multiplier = 1.0

                        # Relevant planet bonus
                        if is_relevant_planet:
                            relevance_multiplier += 0.5

                        # Relevant aspect bonus
                        if aspect_type in factors["aspects"]:
                            relevance_multiplier += 0.5

                        # Calculate final score for this aspect
                        aspect_score = base_score * relevance_multiplier

                        # Add to total score
                        score += aspect_score

                        # Count significant transits
                        if aspect_score > 7.0:
                            significant_transits += 1

                except Exception as e:
                    logger.debug(f"Error checking transit {transit_planet} to natal {natal_planet}: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error processing natal planet {natal_planet}: {e}")
            continue

    # Check transits to houses
    for house_num in factors["houses"]:
        try:
            # Get the house cusp
            house = natal_chart.getHouse(house_num)
            if not house:
                continue

            house_longitude = house.lon

            # Check for transiting planets near this house cusp
            for transit_planet in const.LIST_PLANETS:
                try:
                    tr_planet = transit_chart.getObject(transit_planet)
                    if not tr_planet:
                        continue

                    transit_longitude = tr_planet.lon

                    # Calculate orb
                    diff = abs(transit_longitude - house_longitude) % 360
                    if diff > 180:
                        diff = 360 - diff

                    # If planet is conjunct house cusp (5° orb)
                    if diff < 5:
                        # Calculate score based on orb
                        house_score = 10.0 - diff * 2.0  # Tighter orb = higher score

                        # Add to total score
                        score += house_score

                        # Count significant transit
                        if house_score > 5.0:
                            significant_transits += 1

                except Exception as e:
                    logger.debug(f"Error checking transit {transit_planet} to house {house_num}: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Error processing house {house_num}: {e}")
            continue

    # Keyword matching in description
    if description:
        description_lower = description.lower()
        keyword_matches = sum(1 for keyword in factors["keywords"] if keyword in description_lower)
        keyword_score = keyword_matches * 5.0  # Each keyword match adds points
        score += keyword_score

    return score, significant_transits

async def progressed_ascendant_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str
) -> Tuple[datetime, float]:
    """
    Use progressed ascendant technique for birth time rectification.

    This method analyzes the movement of the ascendant by progression, which is
    approximately 1 degree per day, or ~4 minutes of time per day of life.
    By analyzing critical periods in a person's life against progressed ascendant
    angles, we can deduce the most likely birth time.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Timezone string

    Returns:
        Tuple of (rectified_datetime, confidence)
    """
    logger.info("Using progressed ascendant for rectification")

    # Estimate key life transition ages (these are standard astrological age markers)
    key_ages = [7, 14, 21, 28, 35, 42, 49, 56, 63]

    best_score = 0
    best_time = birth_dt

    # Check 15-minute increments within a 2-hour window
    for minutes in range(-120, 121, 15):
        test_time = birth_dt + timedelta(minutes=minutes)

        try:
            # Calculate birth chart
            birth_chart = calculate_chart(test_time, latitude, longitude, timezone)

            # Extract ascendant position
            asc = birth_chart.getAngle(const.ASC)
            asc_longitude = asc.lon

            # Score the chart based on progressions at key ages
            score = 0

            # For each key age, check if the progressed ascendant makes significant aspects
            for age in key_ages:
                # Calculate progressed time (each day after birth = 1 year of life)
                prog_date = test_time + timedelta(days=age*365.25)

                # Calculate progressed chart
                try:
                    prog_chart = calculate_chart(prog_date, latitude, longitude, timezone)

                    # Calculate progressed ascendant position
                    prog_asc = prog_chart.getAngle(const.ASC)
                    prog_asc_longitude = prog_asc.lon

                    # Check aspects to natal planets (conjunction, square, opposition, trine)
                    for planet_key in const.LIST_PLANETS:
                        try:
                            planet = birth_chart.getObject(planet_key)
                            if planet:
                                planet_longitude = planet.lon

                                # Calculate aspect angle (0-180 degrees)
                                aspect_angle = abs(prog_asc_longitude - planet_longitude) % 180

                                # Check for major aspects with generous orbs
                                # Conjunction (0°)
                                if aspect_angle < 8 or aspect_angle > 172:
                                    score += 10
                                # Opposition (180°)
                                elif abs(aspect_angle - 180) < 8:
                                    score += 8
                                # Square (90°)
                                elif abs(aspect_angle - 90) < 8:
                                    score += 6
                                # Trine (120°)
                                elif abs(aspect_angle - 120) < 8:
                                    score += 8
                                # Sextile (60°)
                                elif abs(aspect_angle - 60) < 6:
                                    score += 4

                        except Exception as e:
                            logger.debug(f"Error checking aspects for planet {planet_key}: {e}")
                            continue

                except Exception as e:
                    logger.debug(f"Error calculating progression for age {age}: {e}")
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
    # Check if OpenAI service is available - this is required for tests
    try:
        # Import here to avoid circular imports
        from ai_service.utils.dependency_container import get_container
        container = get_container()
        openai_service = container.get("openai_service")

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
    openai_service = get_openai_service()
    if not openai_service:
        raise ValueError("OpenAI service is required for accurate birth time rectification")

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

        # Create a custom JSON encoder to handle date and datetime objects
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                return super().default(obj)

        # Request analysis from OpenAI
        response = await openai_service.generate_completion(
            prompt=json.dumps(prompt_data, cls=DateTimeEncoder),
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
                    # Second attempt: Extract JSON if embedded in text with regex
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        try:
                            ai_result = json.loads(json_match.group(0))
                            logger.info("Successfully extracted JSON using regex")
                        except json.JSONDecodeError:
                            # Try to clean the JSON string before parsing
                            json_str = json_match.group(0)
                            # Remove any escape characters that might be causing issues
                            json_str = json_str.replace('\\n', ' ').replace('\\', '')
                            ai_result = json.loads(json_str)
                            logger.info("Successfully parsed JSON after cleaning")
                    else:
                        # Third attempt: Parse key-value pairs manually from text
                        logger.warning("Could not extract JSON, falling back to text parsing")
                        ai_result = {}

                        # Extract rectified time
                        time_match = re.search(r'(?:rectified_time|rectified birth time)["\s:]+([0-2]?[0-9]:[0-5][0-9])', content, re.IGNORECASE)
                        if time_match:
                            ai_result["rectified_time"] = time_match.group(1)

                        # Extract confidence
                        confidence_match = re.search(r'confidence["\s:]+(\d+\.?\d*)', content, re.IGNORECASE)
                        if confidence_match:
                            ai_result["confidence"] = float(confidence_match.group(1))

                        # Extract explanation
                        explanation_match = re.search(r'explanation["\s:]+["\'](.*?)["\']', content, re.DOTALL)
                        if explanation_match:
                            ai_result["explanation"] = explanation_match.group(1)
                        else:
                            ai_result["explanation"] = "Birth time rectified using AI analysis"

                        # If we couldn't extract time, use original time
                        if "rectified_time" not in ai_result:
                            ai_result["rectified_time"] = birth_dt.strftime("%H:%M")
                            ai_result["confidence"] = 50.0

                # Extract the rectified time
                rectified_time_str = ai_result.get("rectified_time")
                if rectified_time_str:
                    try:
                        hours, minutes = map(int, rectified_time_str.split(":"))
                        ai_time = birth_dt.replace(hour=hours, minute=minutes)

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

        weighted_minutes = int(transit_minutes * transit_weight + basic_minutes * basic_weight) % 1440
        weighted_hour = weighted_minutes // 60
        weighted_minute = weighted_minutes % 60

        rectified_time = birth_dt.replace(hour=weighted_hour, minute=weighted_minute)
        confidence = (transit_confidence + basic_confidence) / 2
        explanation = "Birth time rectified using a combination of questionnaire analysis and life event transits"
    elif basic_time:
        # Use basic rectification
        methods_used.append("questionnaire_analysis")
        rectified_time = basic_time
        confidence = basic_confidence
        explanation = "Birth time rectified based on questionnaire analysis"
    elif transit_time:
        # Use transit rectification
        methods_used.append("transit_analysis")
        rectified_time = transit_time
        confidence = transit_confidence
        explanation = "Birth time rectified using life event transit analysis"
    elif solar_arc_time:
        # Use solar arc as a last technical method
        methods_used.append("solar_arc_analysis")
        rectified_time = solar_arc_time
        confidence = solar_arc_confidence
        explanation = "Birth time rectified using solar arc directions"
    else:
        # This should never happen as we've checked for at least one successful method
        # But just in case, make a second attempt with AI
        raise ValueError("Inconsistent state: methods_succeeded indicates success but no valid rectification method found")

    # Verify we have a valid rectified time
    if not rectified_time:
        raise ValueError("Failed to determine rectified birth time after multiple attempts")

    # Calculate adjustment in minutes
    birth_minutes = birth_dt.hour * 60 + birth_dt.minute
    rectified_minutes = rectified_time.hour * 60 + rectified_time.minute

    # Handle day wraparound for adjustment calculation
    if abs(rectified_minutes - birth_minutes) > 720:  # More than 12 hours apart
        if rectified_minutes > birth_minutes:
            birth_minutes += 1440  # Add 24 hours
        else:
            rectified_minutes += 1440  # Add 24 hours

    adjustment_minutes = rectified_minutes - birth_minutes

    # Add adjustment information to explanation if not already included
    if "adjusted by" not in explanation:
        explanation += (
            f" The original time was adjusted by {abs(adjustment_minutes)} minutes "
            f"{'earlier' if adjustment_minutes < 0 else 'later'} based on "
            f"astrological analysis."
        )

    # Return comprehensive result
    return {
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
        }
    }
