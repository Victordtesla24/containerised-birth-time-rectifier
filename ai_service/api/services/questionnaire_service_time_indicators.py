"""
Birth time indicator extraction module for the questionnaire service.

This module contains functions for extracting birth time indicators from questionnaire responses.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

# logger initialization
logger = logging.getLogger(__name__)

async def _extract_birth_time_indicators(self, question: str, answer: Any) -> Optional[Dict[str, Any]]:
    """
    Extract birth time indicators from the answer to a question using advanced pattern recognition.

    Args:
        question: The question text
        answer: The answer to the question

    Returns:
        Dictionary containing birth time indicators, or None if no indicators found
    """
    # Convert answer to string for text processing
    if not isinstance(answer, str):
        answer = str(answer)

    indicators = {}
    answer_lower = answer.lower()

    # PATTERN GROUP 1: DIRECT TIME REFERENCES
    # Check if question is about birth time
    if any(phrase in question.lower() for phrase in ["birth time", "born", "time of birth", "what time", "when were you born"]):
        # 1a. Extract exact time references
        exact_time_patterns = [
            r'(?:born|birth|delivered)(?:\s+at)?\s+(?:around|about|approximately)?\s*(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?|am|pm|hours|hrs))',
            r'(?:at|around|about|approximately)\s+(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?|am|pm|hours|hrs))',
            r'(\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?|am|pm|hours)(?:\s+(?:in|at|on)\s+(?:the|my)\s+(?:morning|afternoon|evening|night))?)'
        ]

        for pattern in exact_time_patterns:
            match = re.search(pattern, answer_lower)
            if match:
                time_text = match.group(1)
                indicators["exact_time_reference"] = time_text
                # Normalize the time
                hour, minute, period = self._normalize_time_reference(time_text)
                if hour is not None:
                    indicators["normalized_time"] = f"{hour:02d}:{minute:02d}"
                    indicators["time_precision"] = "exact"
                    break

        # 1b. Check for time of day references with enhanced pattern matching
        if "exact_time_reference" not in indicators:
            time_of_day_patterns = [
                r'(?:born|birth|delivered)(?:\s+(?:in|during|at))?\s+(?:the)?\s+(early|late)?\s*(morning|afternoon|evening|night|dawn|dusk|daytime|noon|midnight)',
                r'(?:it\s+was|around|during)\s+(?:the)?\s+(early|late)?\s*(morning|afternoon|evening|night|dawn|dusk|daytime|noon|midnight)',
                r'(early|late)?\s*(morning|afternoon|evening|night|dawn|dusk|daytime|noon|midnight)\s+(?:birth|delivery|born)'
            ]

            for pattern in time_of_day_patterns:
                match = re.search(pattern, answer_lower)
                if match:
                    modifier = match.group(1) or ""
                    time_of_day = match.group(2)
                    time_of_day_full = f"{modifier} {time_of_day}".strip()
                    indicators["time_of_day"] = time_of_day_full
                    indicators["time_range"] = self._time_of_day_to_range(time_of_day_full)
                    indicators["time_precision"] = "approximate"
                    break

    # PATTERN GROUP 2: INDIRECT BIRTH CIRCUMSTANCES
    # Look for birth circumstances that might indicate time
    birth_circumstance_patterns = {
        "hospital_shift": r'(?:doctor|nurse|hospital staff)\s+(?:change|shift|switch|rotation|handover)',
        "night_birth": r'(?:everyone|doctors|nurses)\s+(?:was|were)\s+(?:tired|sleeping|exhausted)',
        "meal_time": r'(?:during|after|before)\s+(?:breakfast|lunch|dinner|supper|meal)',
        "family_routine": r'(?:father|mother|dad|mom)\s+(?:was at|coming from|going to)\s+(?:work|home)',
        "tv_program": r'(?:while|during)\s+(?:watching|program|show|news)',
        "traffic_conditions": r'(?:traffic|rush hour|commute)',
        "visiting_hours": r'(?:visiting|visitor|visit)\s+(?:hours|time|period)'
    }

    for circumstance, pattern in birth_circumstance_patterns.items():
        if re.search(pattern, answer_lower):
            indicators["birth_circumstances"] = indicators.get("birth_circumstances", []) + [circumstance]

            # Associate circumstances with time ranges
            if circumstance == "hospital_shift" and "time_range" not in indicators:
                indicators["time_range"] = "06:30-07:30 or 18:30-19:30"  # Common shift change times
            elif circumstance == "meal_time" and "time_range" not in indicators:
                if "breakfast" in answer_lower:
                    indicators["time_range"] = "07:00-09:00"
                elif "lunch" in answer_lower:
                    indicators["time_range"] = "12:00-14:00"
                elif "dinner" in answer_lower:
                    indicators["time_range"] = "18:00-20:00"

    # PATTERN GROUP 3: PHYSICAL CHARACTERISTICS FOR ASCENDANT
    if any(phrase in question.lower() for phrase in ["appearance", "physical", "look", "feature", "body", "face"]):
        # Enhanced physical trait keywords with more detailed mapping and confidence levels
        trait_keywords = {
            # Format: "trait": (["signs"], confidence)
            "tall": (["Aries", "Sagittarius", "Aquarius"], 0.7),
            "short": (["Cancer", "Scorpio", "Capricorn"], 0.7),
            "athletic": (["Leo", "Capricorn", "Aries"], 0.8),
            "muscular": (["Aries", "Leo", "Scorpio"], 0.8),
            "thin": (["Gemini", "Virgo", "Aquarius"], 0.7),
            "slender": (["Virgo", "Gemini", "Libra"], 0.7),
            "well-proportioned": (["Libra", "Taurus", "Leo"], 0.6),
            "heavy": (["Taurus", "Cancer", "Pisces"], 0.6),
            "stocky": (["Taurus", "Capricorn", "Scorpio"], 0.7),
            "broad shoulders": (["Capricorn", "Sagittarius", "Aries"], 0.8),
            "prominent eyes": (["Pisces", "Sagittarius", "Aquarius"], 0.6),
            "strong jaw": (["Taurus", "Capricorn", "Aries"], 0.7),
            "high forehead": (["Aries", "Aquarius", "Gemini"], 0.6),
            "round face": (["Cancer", "Pisces", "Taurus"], 0.7),
            "oval face": (["Libra", "Leo", "Gemini"], 0.6),
            "square face": (["Capricorn", "Taurus", "Scorpio"], 0.7),
            "graceful": (["Libra", "Pisces", "Taurus"], 0.6),
            "pale skin": (["Pisces", "Cancer", "Scorpio"], 0.5),
            "dark complexion": (["Scorpio", "Capricorn", "Aquarius"], 0.5),
            "athletic build": (["Aries", "Leo", "Sagittarius"], 0.7),
            "curly hair": (["Leo", "Aries", "Sagittarius"], 0.5),
            "early balding": (["Cancer", "Virgo", "Capricorn"], 0.5),
            "thick hair": (["Leo", "Taurus", "Scorpio"], 0.5),
            "large eyes": (["Pisces", "Sagittarius", "Aquarius"], 0.6),
            "intense gaze": (["Scorpio", "Capricorn", "Aries"], 0.7),
            "expressive eyes": (["Pisces", "Gemini", "Sagittarius"], 0.6),
            "full lips": (["Taurus", "Libra", "Pisces"], 0.5),
            "thin lips": (["Virgo", "Capricorn", "Aquarius"], 0.5),
            "strong nose": (["Aries", "Capricorn", "Scorpio"], 0.6),
            "delicate features": (["Libra", "Pisces", "Gemini"], 0.6)
        }

        # Detect physical traits using regex to catch variations
        physical_indicators = {}
        for trait, (signs, confidence) in trait_keywords.items():
            # Create regex pattern that looks for the trait or its variations
            trait_pattern = r'\b' + re.escape(trait) + r'(?:\s+body|\s+physique|\s+appearance|\s+build|\s+physical)?\b'
            trait_pattern_alt = r'\b(?:body|build|physique|appearance)\s+(?:is|was)?\s+' + re.escape(trait) + r'\b'

            if re.search(trait_pattern, answer_lower) or re.search(trait_pattern_alt, answer_lower):
                for sign in signs:
                    if sign not in physical_indicators:
                        physical_indicators[sign] = 0
                    physical_indicators[sign] += confidence

        # Add highest confidence indicators
        if physical_indicators:
            sorted_signs = sorted(physical_indicators.items(), key=lambda x: x[1], reverse=True)
            indicators["physical_traits_detected"] = [trait for trait, _ in sorted_signs[:3]]
            indicators["potential_ascendants"] = [sign for sign, _ in sorted_signs[:3]]
            indicators["potential_ascendant_confidence"] = sorted_signs[0][1] if sorted_signs else 0

    # PATTERN GROUP 4: PERSONALITY TRAITS FOR ASCENDANT AND MOON
    if any(phrase in question.lower() for phrase in ["personality", "character", "temperament", "behavior", "nature", "disposition"]):
        # Enhanced personality keywords with confidence levels
        personality_keywords = {
            # Format: "trait": (["primary signs"], ["secondary influences"], confidence)
            "leader": (["Aries", "Leo"], ["Sun dominant", "Mars dominant"], 0.8),
            "determined": (["Capricorn", "Scorpio"], ["Saturn dominant", "Pluto dominant"], 0.7),
            "analytical": (["Virgo", "Gemini"], ["Mercury dominant"], 0.8),
            "intellectual": (["Aquarius", "Gemini"], ["Uranus dominant", "Mercury dominant"], 0.7),
            "emotional": (["Cancer", "Pisces"], ["Moon dominant", "Neptune dominant"], 0.8),
            "sensitive": (["Pisces", "Cancer"], ["Neptune dominant", "Moon dominant"], 0.7),
            "practical": (["Capricorn", "Taurus"], ["Saturn dominant", "Venus dominant"], 0.7),
            "reliable": (["Taurus", "Capricorn"], ["Venus dominant", "Saturn dominant"], 0.7),
            "social": (["Libra", "Gemini"], ["Venus dominant", "Mercury dominant"], 0.7),
            "diplomatic": (["Libra", "Pisces"], ["Venus dominant", "Neptune dominant"], 0.7),
            "intense": (["Scorpio", "Aries"], ["Pluto dominant", "Mars dominant"], 0.8),
            "secretive": (["Scorpio", "Pisces"], ["Pluto dominant", "Neptune dominant"], 0.7),
            "philosophical": (["Sagittarius", "Aquarius"], ["Jupiter dominant", "Uranus dominant"], 0.7),
            "optimistic": (["Sagittarius", "Leo"], ["Jupiter dominant", "Sun dominant"], 0.7),
            "innovative": (["Aquarius", "Gemini"], ["Uranus dominant", "Mercury dominant"], 0.7),
            "rebellious": (["Aquarius", "Aries"], ["Uranus dominant", "Mars dominant"], 0.7),
            "artistic": (["Pisces", "Libra"], ["Neptune dominant", "Venus dominant"], 0.7),
            "compassionate": (["Pisces", "Cancer"], ["Neptune dominant", "Moon dominant"], 0.7),
            "confident": (["Leo", "Aries"], ["Sun dominant", "Mars dominant"], 0.7),
            "generous": (["Leo", "Sagittarius"], ["Sun dominant", "Jupiter dominant"], 0.7),
            "detail-oriented": (["Virgo", "Capricorn"], ["Mercury dominant", "Saturn dominant"], 0.8),
            "reserved": (["Capricorn", "Virgo"], ["Saturn dominant", "Mercury dominant"], 0.7),
            "passionate": (["Scorpio", "Aries"], ["Pluto dominant", "Mars dominant"], 0.7),
            "adaptable": (["Gemini", "Pisces"], ["Mercury dominant", "Neptune dominant"], 0.6),
            "stubborn": (["Taurus", "Leo"], ["Venus dominant", "Sun dominant"], 0.7),
            "independent": (["Aries", "Aquarius"], ["Mars dominant", "Uranus dominant"], 0.7)
        }

        # Detect personality traits
        personality_indicators = {"ascendant": {}, "moon": {}}
        for trait, (primary_signs, secondary_influences, confidence) in personality_keywords.items():
            # Create regex pattern that looks for personality trait mentions
            trait_pattern = r'\b' + re.escape(trait) + r'(?:\s+person|\s+personality|\s+type|\s+character)?\b'
            trait_pattern_alt = r'\b(?:I am|I\'m|I was|very|quite|extremely)\s+' + re.escape(trait) + r'\b'

            if re.search(trait_pattern, answer_lower) or re.search(trait_pattern_alt, answer_lower):
                # Primary traits likely influence ascendant
                for sign in primary_signs:
                    if sign not in personality_indicators["ascendant"]:
                        personality_indicators["ascendant"][sign] = 0
                    personality_indicators["ascendant"][sign] += confidence

                # Secondary influences might point more to moon or other placements
                for influence in secondary_influences:
                    if influence.endswith("dominant"):
                        planet = influence.split()[0]
                        if planet not in personality_indicators["moon"]:
                            personality_indicators["moon"][planet] = 0
                        personality_indicators["moon"][planet] += confidence * 0.7  # Lower confidence for secondary

        # Add highest confidence indicators
        if personality_indicators["ascendant"]:
            sorted_asc = sorted(personality_indicators["ascendant"].items(), key=lambda x: x[1], reverse=True)
            indicators["personality_ascendant_indicators"] = [sign for sign, _ in sorted_asc[:3]]
            indicators["personality_ascendant_confidence"] = sorted_asc[0][1] if sorted_asc else 0

        if personality_indicators["moon"]:
            sorted_moon = sorted(personality_indicators["moon"].items(), key=lambda x: x[1], reverse=True)
            indicators["personality_planet_influences"] = [planet for planet, _ in sorted_moon[:3]]
            indicators["personality_planet_confidence"] = sorted_moon[0][1] if sorted_moon else 0

    # PATTERN GROUP 5: LIFE EVENT TIMING FOR TRANSIT ANALYSIS
    if any(phrase in question.lower() for phrase in ["event", "experience", "change", "happen", "occurred", "life"]):
        # Expanded patterns for age and date references
        event_patterns = {
            "age": [
                r'(?:at|around|when I was)\s+(?:the\s+)?age(?:\s+of)?\s+(\d+)',
                r'(?:when|while)\s+(?:I\s+)?was\s+(\d+)(?:\s+years?\s+old)?',
                r'(\d+)\s+years?\s+old',
                r'(?:in\s+my|during\s+my)\s+(?:early|mid|late)?\s*(\d+)s',  # e.g., "in my early 20s"
            ],
            "year": [
                r'(?:in|during|around|about)\s+(?:the\s+)?(?:year\s+)?(\d{4})',
                r'(?:back\s+in|happened\s+in)\s+(\d{4})'
            ],
            "month_year": [
                r'(?:in|during)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:of\s+)?(\d{4})',
                r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(?:of\s+)?(\d{4})'
            ],
            "relative_time": [
                r'(\d+)\s+(?:years|months|weeks|days)\s+(?:ago|before|after)',
                r'(?:about|around|approximately)\s+(\d+)\s+(?:years|months|weeks|days)\s+(?:ago|before|after)'
            ]
        }

        # Extract event timing references
        for event_type, patterns in event_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, answer_lower)

                if matches:
                    # Process matches based on event type
                    if event_type == "age":
                        ages = []
                        for match in matches:
                            try:
                                if isinstance(match, tuple):  # Handle complex regex groups
                                    for group in match:
                                        if group.isdigit() and int(group) < 100:
                                            ages.append(int(group))
                                elif match.isdigit() and int(match) < 100:
                                    ages.append(int(match))
                            except (ValueError, TypeError):
                                continue

                        if ages:
                            indicators["event_ages"] = ages

                    elif event_type == "year":
                        years = []
                        for match in matches:
                            try:
                                if isinstance(match, tuple):  # Handle complex regex groups
                                    for group in match:
                                        if group.isdigit() and 1900 < int(group) < 2100:
                                            years.append(int(group))
                                elif match.isdigit() and 1900 < int(match) < 2100:
                                    years.append(int(match))
                            except (ValueError, TypeError):
                                continue

                        if years:
                            indicators["event_years"] = years

                    elif event_type == "month_year":
                        month_years = []
                        for match in matches:
                            if isinstance(match, tuple) and len(match) >= 2:
                                month, year = match[0], match[1]
                                if year.isdigit() and 1900 < int(year) < 2100:
                                    month_years.append(f"{month} {year}")

                        if month_years:
                            indicators["event_month_years"] = month_years

                    elif event_type == "relative_time":
                        relative_times = []
                        for match in matches:
                            if isinstance(match, tuple):
                                if match[0].isdigit():
                                    relative_times.append(match[0] + " " + match[1])
                            elif isinstance(match, str) and match.isdigit():
                                relative_times.append(match)

                        if relative_times:
                            indicators["event_relative_times"] = relative_times

        # Extract life event types for astrological significance
        life_event_keywords = {
            "marriage": ["marriage", "wedding", "got married", "marry", "spouse", "husband", "wife"],
            "relationship": ["relationship", "partner", "dating", "boyfriend", "girlfriend", "significant other"],
            "divorce": ["divorce", "separated", "split up", "broke up", "end of marriage"],
            "career": ["job", "career", "profession", "work", "employment", "promotion", "business"],
            "education": ["school", "college", "university", "degree", "graduation", "education", "study"],
            "relocation": ["move", "relocation", "moved house", "moved city", "new home", "new place"],
            "health": ["health", "illness", "disease", "diagnosis", "surgery", "hospital", "medical"],
            "accident": ["accident", "injury", "fall", "crash", "emergency"],
            "children": ["child", "baby", "birth", "childbirth", "pregnant", "pregnancy", "daughter", "son"],
            "death": ["death", "died", "passed away", "funeral", "loss of", "deceased"],
            "spiritual": ["spiritual", "awakening", "meditation", "enlightenment", "religious"],
            "financial": ["money", "financial", "investment", "property", "purchase", "debt"]
        }

        event_types_detected = []
        for event_type, keywords in life_event_keywords.items():
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', answer_lower):
                    event_types_detected.append(event_type)
                    break

        if event_types_detected:
            indicators["life_event_types"] = event_types_detected

    # If we have any indicators, return them
    if indicators:
        return indicators

    return None

def _normalize_time_reference(self, time_text: str) -> Tuple[Optional[int], int, Optional[str]]:
    """
    Normalize time references to 24-hour format.

    Args:
        time_text: Time reference text (e.g., "3:30pm", "10 am", "14:00 hrs")

    Returns:
        Tuple of (hour, minute, period) with hour in 24-hour format
    """
    # Clean up the text
    time_text = time_text.lower().strip()
    time_text = re.sub(r'\s+', ' ', time_text)

    # Extract components
    hour = None
    minute = 0
    period = None

    # Check for 24-hour format first
    match_24h = re.search(r'(\d{1,2})[:.]?(\d{2})?\s*(?:hours|hrs)', time_text)
    if match_24h:
        hour = int(match_24h.group(1))
        minute = int(match_24h.group(2) or "0")
        if hour > 23:
            hour = hour % 24
        return hour, minute, None

    # Check for AM/PM format
    match_am_pm = re.search(r'(\d{1,2})[:.]?(\d{2})?\s*([ap]\.?m\.?)', time_text)
    if match_am_pm:
        hour = int(match_am_pm.group(1))
        minute = int(match_am_pm.group(2) or "0")
        period = match_am_pm.group(3)[0].lower()  # 'a' or 'p'

        # Convert to 24-hour format
        if period == 'p' and hour < 12:
            hour += 12
        elif period == 'a' and hour == 12:
            hour = 0

        return hour, minute, period

    # Just a number with am/pm
    match_simple = re.search(r'(\d{1,2})\s*([ap]\.?m\.?)', time_text)
    if match_simple:
        hour = int(match_simple.group(1))
        minute = 0
        period = match_simple.group(2)[0].lower()  # 'a' or 'p'

        # Convert to 24-hour format
        if period == 'p' and hour < 12:
            hour += 12
        elif period == 'a' and hour == 12:
            hour = 0

        return hour, minute, period

    # Just a number without am/pm - can't normalize reliably
    match_number = re.search(r'(\d{1,2})', time_text)
    if match_number:
        hour = int(match_number.group(1))
        # Can't reliably convert without am/pm
        return hour, 0, None

    # Couldn't parse
    return None, 0, None

def _time_of_day_to_range(self, time_of_day: str) -> str:
    """
    Convert a time of day reference to a time range.

    Args:
        time_of_day: String describing time of day

    Returns:
        Time range in HH:MM-HH:MM format
    """
    time_ranges = {
        "morning": "06:00-12:00",
        "early morning": "04:00-08:00",
        "late morning": "10:00-12:00",
        "afternoon": "12:00-17:00",
        "early afternoon": "12:00-14:00",
        "late afternoon": "15:00-17:00",
        "evening": "17:00-21:00",
        "early evening": "17:00-19:00",
        "late evening": "19:00-21:00",
        "night": "21:00-04:00",
        "early night": "21:00-00:00",
        "late night": "00:00-04:00",
        "midnight": "23:30-00:30",
        "noon": "11:30-12:30",
        "dawn": "04:00-07:00",
        "dusk": "17:00-20:00"
    }

    # Find the best match
    for key, value in time_ranges.items():
        if key in time_of_day or time_of_day in key:
            return value

    # Default range if no match (full day)
    return "00:00-23:59"

def _extract_pattern_from_text(self, text: str, pattern: str) -> Optional[str]:
    """
    Extract a pattern from text using regex.

    Args:
        text: Source text to search in
        pattern: Regex pattern to search for

    Returns:
        Matched string or None if no match
    """
    match = re.search(pattern, text)
    return match.group(0) if match else None
