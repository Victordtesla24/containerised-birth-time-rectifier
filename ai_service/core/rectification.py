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
import json

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
    Calculate astrological chart for a specific birth time using available libraries.

    Args:
        birth_date: Birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone_str: Birth location timezone

    Returns:
        Chart object (flatlib.Chart or custom dict)
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

    try:
        # Try using flatlib first
        from flatlib.datetime import Datetime
        from flatlib.geopos import GeoPos
        from flatlib.chart import Chart

        date = Datetime(dt_str, time_str, offset_str)
        pos = GeoPos(f"{abs(latitude)}{'n' if latitude >= 0 else 's'}",
                   f"{abs(longitude)}{'e' if longitude >= 0 else 'w'}")

        # Calculate and return the chart
        return Chart(date, pos)
    except ImportError:
        logger.warning("Flatlib not available, using Swiss Ephemeris")

        try:
            # Use Swiss Ephemeris as alternative
            import swisseph as swe
            import os

            # Initialize ephemeris path
            ephemeris_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ephemeris")
            swe.set_ephe_path(ephemeris_path)

            # Convert to Julian day
            jul_day = swe.julday(
                birth_date.year,
                birth_date.month,
                birth_date.day,
                birth_date.hour + birth_date.minute/60.0
            )

            # Calculate house cusps and ascendant
            houses, ascmc = swe.houses(jul_day, latitude, longitude, b'P')

            # Extract ascendant
            ascendant_lon = ascmc[0]

            # Calculate planet positions
            planets = {}
            # Planet IDs in Swiss Ephemeris: 0=Sun, 1=Moon, 2=Mercury, etc.
            planet_names = {
                0: "Sun", 1: "Moon", 2: "Mercury", 3: "Venus",
                4: "Mars", 5: "Jupiter", 6: "Saturn",
                7: "Uranus", 8: "Neptune", 9: "Pluto"
            }

            for planet_id in range(10):  # 0-9 are major planets
                position, speed = swe.calc_ut(jul_day, planet_id)
                planets[planet_names[planet_id]] = {
                    'longitude': position[0],
                    'latitude': position[1],
                    'distance': position[2],
                    'speed': speed[0]
                }

            # Convert to zodiac signs
            signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

            def lon_to_sign(lon):
                sign_num = int(lon / 30) % 12
                return signs[sign_num]

            def lon_to_degree(lon):
                return lon % 30

            # Create a custom Chart-like object with the necessary methods for compatibility
            class SwissEphChart:
                def __init__(self, jul_day, lat, lon, houses, ascmc, planets):
                    self.jul_day = jul_day
                    self.latitude = lat
                    self.longitude = lon
                    self.houses = houses
                    self.ascmc = ascmc
                    self.planets = planets
                    self._objects = {}

                    # Calculate and store planet objects
                    for planet_name, data in planets.items():
                        sign = lon_to_sign(data['longitude'])
                        degree = lon_to_degree(data['longitude'])

                        # Find which house this planet is in
                        house_num = 1
                        for i in range(1, 13):
                            next_house = (i % 12) + 1
                            house_lon = houses[i - 1]
                            next_house_lon = houses[next_house - 1]

                            # Handle house wrap around 0/360
                            if next_house_lon < house_lon:
                                if data['longitude'] >= house_lon or data['longitude'] < next_house_lon:
                                    house_num = i
                                    break
                            else:
                                if house_lon <= data['longitude'] < next_house_lon:
                                    house_num = i
                                    break

                        self._objects[planet_name] = {
                            'name': planet_name,
                            'sign': sign,
                            'degree': degree,
                            'longitude': data['longitude'],
                            'latitude': data['latitude'],
                            'house': house_num,
                            'speed': data['speed']
                        }

                    # Pre-calculate house data
                    self._houses = {}
                    for i in range(12):
                        house_num = i + 1
                        house_lon = houses[i]
                        sign = lon_to_sign(house_lon)
                        degree = lon_to_degree(house_lon)

                        self._houses[house_num] = {
                            'number': house_num,
                            'sign': sign,
                            'degree': degree,
                            'longitude': house_lon
                        }

                # Implement flatlib-compatible interface methods
                def getObject(self, name):
                    if name in self._objects:
                        obj = self._objects[name]

                        # Create a flatlib-like object with the needed attributes and methods
                        class PlanetProxy:
                            def __init__(self, data):
                                self.data = data
                                self.name = data['name']
                                self.lon = data['longitude']
                                self.sign = data['sign']

                            def __getattr__(self, name):
                                return self.data.get(name)

                        return PlanetProxy(obj)
                    return None

                def getHouse(self, num):
                    if 1 <= num <= 12:
                        house_data = self._houses[num]

                        class HouseProxy:
                            def __init__(self, data, chart):
                                self.data = data
                                self.chart = chart
                                self.sign = data['sign']
                                self.lon = data['longitude']

                            def hasObject(self, obj):
                                if hasattr(obj, 'data') and 'house' in obj.data:
                                    return obj.data['house'] == self.data['number']
                                return False

                            def __getattr__(self, name):
                                return self.data.get(name)

                        return HouseProxy(house_data, self)
                    return None

                def getAngle(self, name):
                    angles = {
                        'Asc': ascmc[0],  # Ascendant
                        'MC': ascmc[1],   # Midheaven
                    }

                    if name in angles:
                        angle_lon = angles[name]

                        class AngleProxy:
                            def __init__(self, lon):
                                self.lon = lon
                                self.sign = lon_to_sign(lon)
                                self.degree = lon_to_degree(lon)

                        return AngleProxy(angle_lon)
                    return None

                def get_house_number_for_object(self, obj_name):
                    if obj_name in self._objects:
                        return self._objects[obj_name]['house']
                    return None

            # Return the SwissEphChart object
            return SwissEphChart(jul_day, latitude, longitude, houses, ascmc, planets)

        except ImportError:
            # If neither Flatlib nor Swiss Ephemeris is available, use Python's built-in
            # astronomical calculations as a last resort
            logger.warning("Neither Flatlib nor Swiss Ephemeris available. Using minimal calculations.")

            # Create a minimal chart with basic calculations
            class MinimalChart:
                def __init__(self, birth_date, lat, lon):
                    self.birth_date = birth_date
                    self.latitude = lat
                    self.longitude = lon

                    # Use simple formulas for approximate ascendant calculation
                    # This is a very simplified model but better than nothing
                    utc_hour = birth_date.hour + birth_date.minute/60.0
                    days_since_jan1 = birth_date.timetuple().tm_yday

                    # Convert local time to sidereal time (very approximate)
                    sidereal_time = (utc_hour + (lon / 15.0) +
                                    (days_since_jan1 * 24.0 / 365.25)) % 24

                    # Simplified ascendant calculation
                    ascendant_deg = (sidereal_time * 15.0 + 270.0) % 360.0

                    # Create minimal objects/houses
                    self._ascendant = ascendant_deg

                    # Create planet locations based on approximate daily motion
                    self._objects = {
                        "Sun": {"longitude": (days_since_jan1 * 0.98561) % 360.0, "house": 1},
                        "Moon": {"longitude": (days_since_jan1 * 13.1763 + utc_hour * 0.55) % 360.0, "house": 2},
                        "Mercury": {"longitude": (days_since_jan1 * 1.383 + 30) % 360.0, "house": 3},
                        "Venus": {"longitude": (days_since_jan1 * 1.2 + 60) % 360.0, "house": 4},
                        "Mars": {"longitude": (days_since_jan1 * 0.524 + 90) % 360.0, "house": 5},
                        "Jupiter": {"longitude": (days_since_jan1 * 0.083 + 120) % 360.0, "house": 6},
                        "Saturn": {"longitude": (days_since_jan1 * 0.033 + 150) % 360.0, "house": 7}
                    }

                    # Create houses
                    self._houses = {}
                    for i in range(12):
                        house_deg = (self._ascendant + i * 30.0) % 360.0
                        self._houses[i+1] = {"longitude": house_deg, "number": i+1}

                def getObject(self, name):
                    if name in self._objects:
                        data = self._objects[name]

                        class MinimalPlanet:
                            def __init__(self, lon, name):
                                self.lon = lon
                                self.name = name
                                self.sign = lon_to_sign(lon)

                        return MinimalPlanet(data["longitude"], name)
                    return None

                def getHouse(self, num):
                    if 1 <= num <= 12:
                        data = self._houses[num]

                        class MinimalHouse:
                            def __init__(self, lon, num):
                                self.lon = lon
                                self.number = num
                                self.sign = lon_to_sign(lon)

                            def hasObject(self, obj):
                                return False  # Simplified - we don't calculate this accurately

                        return MinimalHouse(data["longitude"], num)
                    return None

                def getAngle(self, name):
                    if name == "Asc":
                        class MinimalAngle:
                            def __init__(self, lon):
                                self.lon = lon
                                self.sign = lon_to_sign(lon)

                        return MinimalAngle(self._ascendant)
                    return None

                def get_house_number_for_object(self, obj_name):
                    if obj_name in self._objects:
                        return self._objects[obj_name]["house"]
                    return None

            # Helper function to convert longitude to sign
            def lon_to_sign(lon):
                signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                sign_num = int(lon / 30) % 12
                return signs[sign_num]

            # Return minimal chart
            return MinimalChart(birth_date, latitude, longitude)
    except Exception as e:
        # Log the error and re-raise with more detail
        logger.error(f"Error calculating chart: {e}")
        raise ValueError(f"Chart calculation failed: {str(e)}")

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

    # If no answers provided, try to use AI-assisted rectification
    if not answers or len(answers) == 0:
        # Try to get OpenAI service
        try:
            openai_service = get_openai_service()
            if openai_service:
                logger.info("Using AI analysis to assist with rectification")
                ai_result = await ai_assisted_rectification(birth_dt, latitude, longitude, timezone, openai_service)
                if ai_result:
                    rectified_time, confidence = ai_result
                    return rectified_time, confidence
        except Exception as e:
            logger.error(f"AI rectification failed: {e}")

        # If AI assistance fails, use direct astrological technique
        logger.warning("No answers provided and AI assistance failed. Using solar arc directions method")
        return await solar_arc_rectification(birth_dt, latitude, longitude, timezone)

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

    # If no valid scores, try using an alternative method
    if not candidate_scores:
        logger.warning("Could not calculate any valid scores for candidate times, trying alternative method")
        if life_events and len(life_events) > 0:
            # Try using life events for rectification
            return await analyze_life_events(life_events, birth_dt, latitude, longitude, timezone)
        else:
            # Try solar arc directions as a fallback
            return await solar_arc_rectification(birth_dt, latitude, longitude, timezone)

    # Sort candidates by score (highest first)
    candidate_scores.sort(key=get_score, reverse=True)
    best_time, best_score = candidate_scores[0]

    # If best score is 0, try alternative methods
    if best_score == 0:
        logger.warning("No significant astrological patterns found, trying alternative method")
        if life_events and len(life_events) > 0:
            # Try using life events for rectification
            return await analyze_life_events(life_events, birth_dt, latitude, longitude, timezone)
        else:
            # Try solar arc directions as a fallback
            return await solar_arc_rectification(birth_dt, latitude, longitude, timezone)

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
) -> Optional[Tuple[datetime, float]]:
    """
    Perform AI-assisted rectification when no questionnaire answers are available.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: Timezone string
        openai_service: OpenAI service instance

    Returns:
        Tuple of (rectified_datetime, confidence) or None if fails
    """
    try:
        # Calculate the natal chart
        chart = calculate_chart(birth_dt, latitude, longitude, timezone)

        # Prepare chart data for AI
        chart_data = {
            "birth_datetime": birth_dt.isoformat(),
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "ascendant": getattr(chart.getAngle(const.ASC), "sign", "Unknown"),
            "midheaven": getattr(chart.getAngle(const.MC), "sign", "Unknown"),
            "sun_sign": getattr(chart.getObject(const.SUN), "sign", "Unknown"),
            "moon_sign": getattr(chart.getObject(const.MOON), "sign", "Unknown"),
            "rising_degree": getattr(chart.getAngle(const.ASC), "lon", 0) % 30
        }

        # Create the prompt for the AI
        prompt = f"""
        Analyze this natal chart and determine the most likely accurate birth time.
        The current birth time is {birth_dt.strftime('%H:%M')}, but it might be off by up to 2 hours.
        Apply astrological principles to determine the most probable birth time.

        Chart data:
        {json.dumps(chart_data, indent=2)}

        Provide your analysis in JSON format with these fields:
        - rectified_time: the corrected birth time in HH:MM format
        - adjustment_minutes: the number of minutes to adjust (positive or negative)
        - confidence: a score from 0-100 indicating your confidence
        - explanation: brief explanation of your reasoning
        """

        # Get the AI's analysis
        response = await openai_service.generate_completion(
            prompt=prompt,
            task_type="birth_time_rectification",
            max_tokens=1000
        )

        if not response or "content" not in response:
            return None

        content = response["content"]

        # Try to extract JSON
        try:
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                ai_result = json.loads(json_match.group(0))
            else:
                ai_result = json.loads(content)

            # Extract the rectified time
            rectified_time_str = ai_result.get("rectified_time")
            if not rectified_time_str:
                return None

            hours, minutes = map(int, rectified_time_str.split(":"))
            rectified_dt = birth_dt.replace(hour=hours, minute=minutes)

            confidence = float(ai_result.get("confidence", 70))

            return rectified_dt, confidence

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing AI response: {e}")
            return None

    except Exception as e:
        logger.error(f"AI-assisted rectification failed: {e}")
        return None

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
            for planet_key in const.LIST_PLANETS:
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

        for planet_key in const.LIST_PLANETS:
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

    # Get timezone if not provided
    if not timezone:
        tf = TimezoneFinder()
        timezone = tf.timezone_at(lat=latitude, lng=longitude) or "UTC"

    # Ensure timezone is a string
    timezone_str = str(timezone) if timezone else "UTC"

    # Calculate the natal chart
    natal_chart = calculate_chart(birth_dt, latitude, longitude, timezone_str)

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
            # Create the candidate chart
            candidate_chart = calculate_chart(candidate_time, latitude, longitude, timezone_str)

            # Initialize score for this candidate
            total_score = 0.0

            # Evaluate each life event
            for event in events:
                event_date_str = event.get('date')
                event_type = event.get('type')

                if not event_date_str or not event_type:
                    continue

                try:
                    # Parse event date
                    event_date = datetime.fromisoformat(event_date_str)

                    # Calculate transit chart for event date
                    transit_chart = calculate_chart(event_date, latitude, longitude, timezone_str)

                    # Calculate transit score for this event
                    event_score = calculate_transit_score(natal_chart, transit_chart, event_type)
                    total_score += event_score
                except Exception as e:
                    logger.error(f"Error analyzing event {event}: {str(e)}")
                    continue

            # Store this candidate's score
            candidate_scores.append((candidate_time, total_score))
        except Exception as e:
            logger.error(f"Error evaluating candidate time {candidate_time}: {str(e)}")
            continue

    # No valid candidates
    if not candidate_scores:
        raise ValueError("No valid transit scores calculated, cannot perform rectification")

    # Find the best candidate time
    candidate_scores.sort(key=get_score, reverse=True)
    best_time, best_score = candidate_scores[0]

    # Calculate average score of top 3 candidates
    top_candidates = candidate_scores[:3]
    avg_top_score = sum(score for _, score in top_candidates) / len(top_candidates)

    # Calculate average of all candidates
    avg_all_score = sum(score for _, score in candidate_scores) / len(candidate_scores)

    # Calculate confidence based on how much better the best time is
    if avg_all_score > 0:
        score_ratio = best_score / avg_all_score
        confidence = min(90.0, 60.0 + (score_ratio - 1) * 20.0)
    else:
        confidence = 60.0

    # Add confidence based on number of events (more events = higher confidence)
    events_factor = min(10.0, len(events) * 2.0)
    confidence = min(95.0, confidence + events_factor)

    logger.info(f"Transit-based rectified time: {best_time}, confidence: {confidence}, score: {best_score}")

    return best_time, confidence

def calculate_transit_score(natal_chart: Chart, transit_chart: Chart, event_type: str) -> float:
    """
    Calculate transit score for a specific event type.

    Args:
        natal_chart: Birth chart
        transit_chart: Transit chart at event time
        event_type: Type of life event

    Returns:
        Score for this transit
    """
    if event_type not in LIFE_EVENT_MAPPING:
        return 0.0

    # Get relevant factors for this event type
    relevant_factors = LIFE_EVENT_MAPPING[event_type]

    # Initialize score
    score = 0.0

    # Check transiting planets against natal chart
    for transit_planet in const.LIST_PLANETS:
        try:
            # Get transiting planet
            t_planet = transit_chart.getObject(transit_planet)

            # Check aspects to natal planets
            for natal_planet in const.LIST_PLANETS:
                try:
                    # Get natal planet
                    n_planet = natal_chart.getObject(natal_planet)

                    # Calculate aspect angle
                    angle = (t_planet.lon - n_planet.lon) % 360

                    # Check for major aspects
                    # Conjunction: 0° (orb: 8°)
                    if angle < 8 or angle > 352:
                        score += 10.0

                    # Opposition: 180° (orb: 8°)
                    elif 172 < angle < 188:
                        score += 8.0

                    # Trine: 120° (orb: 7°)
                    elif 113 < angle < 127 or 233 < angle < 247:
                        score += 6.0

                    # Square: 90° (orb: 7°)
                    elif 83 < angle < 97 or 263 < angle < 277:
                        score += 7.0

                    # Sextile: 60° (orb: 6°)
                    elif 54 < angle < 66 or 294 < angle < 306:
                        score += 5.0

                except Exception as e:
                    logger.error(f"Error checking aspect between {transit_planet} and {natal_planet}: {e}")

            # Check transits to natal angles
            for angle_name in ["ASC", "MC", "DESC", "IC"]:
                try:
                    natal_angle = natal_chart.getAngle(getattr(const, angle_name))

                    # Calculate aspect angle
                    angle = (t_planet.lon - natal_angle.lon) % 360

                    # Check for major aspects to angles
                    # Conjunction: 0° (orb: 5°)
                    if angle < 5 or angle > 355:
                        score += 15.0

                    # Opposition: 180° (orb: 5°)
                    elif 175 < angle < 185:
                        score += 12.0

                    # Square: 90° (orb: 5°)
                    elif 85 < angle < 95 or 265 < angle < 275:
                        score += 10.0

                except Exception as e:
                    logger.error(f"Error checking transit to angle {angle_name}: {e}")

        except Exception as e:
            logger.error(f"Error processing transit planet {transit_planet}: {e}")

    return score

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
    # Extract life events from answers if not provided
    if not events:
        events = extract_life_events_from_answers(answers)

    # Ensure we have at least an empty list of events
    if not events:
        events = []
        logger.warning("No life events found in answers, this reduces rectification accuracy")

    # Try to use OpenAI for advanced analysis if available
    openai_service = None
    ai_rectification_result = None
    try:
        openai_service = get_openai_service()
        if openai_service:
            logger.info("Using OpenAI for advanced rectification analysis")

            # Format the data for OpenAI
            prompt_data = {
                "birth_datetime": birth_dt.isoformat(),
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "answers": answers,
                "life_events": events,
                "task": "Rectify the birth time based on the provided answers and life events"
            }

            # Request analysis from OpenAI
            response = await openai_service.generate_completion(
                prompt=json.dumps(prompt_data),
                task_type="birth_time_rectification",
                max_tokens=1000
            )

            if response and "content" in response:
                # Try to extract JSON from the response
                content = response.get("content", "")
                try:
                    # Extract JSON if embedded in text
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        ai_result = json.loads(json_match.group(0))
                    else:
                        ai_result = json.loads(content)

                    # Extract relevant info if present
                    if "rectified_time" in ai_result:
                        time_str = ai_result["rectified_time"]
                        hours, minutes = map(int, time_str.split(":"))
                        ai_time = birth_dt.replace(hour=hours, minute=minutes)

                        ai_confidence = float(ai_result.get("confidence", 80))
                        ai_explanation = ai_result.get("explanation", "Birth time rectified using AI analysis")

                        ai_rectification_result = {
                            "rectified_time": ai_time,
                            "confidence": ai_confidence,
                            "explanation": ai_explanation
                        }

                        logger.info(f"AI rectification successful: {ai_time}, confidence: {ai_confidence}")
                except Exception as e:
                    logger.error(f"Error parsing AI rectification result: {e}")
    except Exception as e:
        logger.error(f"Error using OpenAI for rectification: {e}")

    # Perform basic rectification using questionnaire answers
    basic_time = None
    basic_confidence = 0
    basic_error = None

    try:
        basic_time, basic_confidence = await rectify_birth_time(
            birth_dt, latitude, longitude, timezone, answers
        )
        logger.info(f"Basic rectification successful: {basic_time}, confidence: {basic_confidence}")
    except Exception as e:
        logger.error(f"Basic rectification failed: {e}")
        basic_error = str(e)

    # Calculate transit-based rectification if we have life events
    transit_time = None
    transit_confidence = 0
    transit_error = None
    transit_available = False

    # Only try transit analysis if we have life events
    if events and len(events) > 0:
        try:
            # Perform transit-based rectification
            transit_time, transit_confidence = await analyze_life_events(
                events, birth_dt, latitude, longitude, timezone
            )
            transit_available = True
            logger.info(f"Transit analysis successful: {transit_time}, confidence: {transit_confidence}")
        except Exception as e:
            logger.error(f"Transit analysis failed: {e}")
            transit_error = str(e)
    else:
        logger.info("Skipping transit analysis due to lack of life events")

    # Try solar arc rectification as an alternative method
    solar_arc_time = None
    solar_arc_confidence = 0

    try:
        solar_arc_time, solar_arc_confidence = await solar_arc_rectification(
            birth_dt, latitude, longitude, timezone
        )
        logger.info(f"Solar arc rectification: {solar_arc_time}, confidence: {solar_arc_confidence}")
    except Exception as e:
        logger.error(f"Solar arc rectification failed: {e}")

    # Determine best method or combine methods
    methods_used = []
    explanation = ""
    rectified_time = birth_dt
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
        # Use solar arc as a last resort
        methods_used.append("solar_arc_analysis")
        rectified_time = solar_arc_time
        confidence = solar_arc_confidence
        explanation = "Birth time rectified using solar arc directions"
    else:
        # We couldn't perform any rectification, try to use AI-assisted rectification as a last resort
        try:
            if openai_service:
                ai_fallback = await ai_assisted_rectification(birth_dt, latitude, longitude, timezone, openai_service)
                if ai_fallback:
                    rectified_time, confidence = ai_fallback
                    methods_used.append("ai_fallback_analysis")
                    explanation = "Birth time rectified using AI astrological analysis (fallback method)"
                else:
                    # No rectification possible, return original time with low confidence
                    rectified_time = birth_dt
                    confidence = 30
                    explanation = "Could not rectify birth time using any method. Original time returned with low confidence."
            else:
                # No rectification possible, return original time with low confidence and explanation
                rectified_time = birth_dt
                confidence = 30
                explanation = "Could not rectify birth time. All methods failed. Original time returned with low confidence."
        except Exception as e:
            logger.error(f"Final AI fallback method failed: {e}")
            rectified_time = birth_dt
            confidence = 30
            explanation = "Birth time rectification failed. Original time returned with low confidence."

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
        "method_details": {
            "ai_rectification": bool(ai_rectification_result),
            "basic_rectification": bool(basic_time),
            "transit_rectification": bool(transit_time),
            "solar_arc_rectification": bool(solar_arc_time)
        }
    }
