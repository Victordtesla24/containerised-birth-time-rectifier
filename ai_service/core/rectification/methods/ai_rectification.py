"""
AI-assisted birth time rectification module.
"""
from datetime import datetime
import logging
import json
import re
import uuid
from typing import Any, Tuple, Dict, Optional, List

logger = logging.getLogger(__name__)

async def ai_assisted_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    openai_service: Any,
    answers: Optional[List[Dict[str, Any]]] = None,
    events: Optional[List[Dict[str, Any]]] = None
) -> Tuple[datetime, float]:
    """
    Perform AI-assisted rectification using astrological principles and OpenAI analysis.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: Timezone string
        openai_service: OpenAI service instance
        answers: Optional list of questionnaire answers
        events: Optional list of life events

    Returns:
        Tuple of (rectified_datetime, confidence)

    Raises:
        ValueError: If OpenAI service is not available or fails
    """
    if not openai_service:
        raise ValueError("OpenAI service is required for AI-assisted rectification")

    # Import chart calculator here to avoid circular imports
    from ..chart_calculator import calculate_chart
    from ..constants import PLANETS_LIST
    from flatlib import const  # We need this for angle constants

    # Calculate the natal chart using real astrological library
    chart = calculate_chart(birth_dt, latitude, longitude, timezone)
    if not chart:
        raise ValueError("Failed to calculate astrological chart for AI analysis")

    # Extract meaningful astrological data from the chart
    chart_data = {}

    # Extract ascendant info
    try:
        if "angles" in chart and "asc" in chart["angles"]:
            asc_data = chart["angles"]["asc"]
            chart_data["ascendant"] = {
                "sign": asc_data.get("sign", ""),
                "degree": asc_data.get("longitude", 0.0) % 30,  # Get degree within sign
                "longitude": asc_data.get("longitude", 0.0)
            }
        else:
            raise ValueError("Ascendant data not found in chart")
    except Exception as e:
        logger.error(f"Error extracting ascendant: {e}")
        raise ValueError(f"Failed to extract ascendant data: {str(e)}")

    # Extract Midheaven (MC) info
    try:
        if "angles" in chart and "mc" in chart["angles"]:
            mc_data = chart["angles"]["mc"]
            chart_data["midheaven"] = {
                "sign": mc_data.get("sign", ""),
                "degree": mc_data.get("longitude", 0.0) % 30,  # Get degree within sign
                "longitude": mc_data.get("longitude", 0.0)
            }
        else:
            raise ValueError("Midheaven data not found in chart")
    except Exception as e:
        logger.error(f"Error extracting midheaven: {e}")
        raise ValueError(f"Failed to extract midheaven data: {str(e)}")

    # Extract planet positions
    chart_data["planets"] = {}
    planets_list = PLANETS_LIST  # Using our constant list to avoid flatlib const issues

    for planet_name in planets_list:
        try:
            planet_key = planet_name.lower()
            if "planets" in chart and planet_key in chart["planets"]:
                planet_data = chart["planets"][planet_key]

                # Determine house for this planet
                house_num = planet_data.get("house", 1)

                # Get the house data if available
                house_sign = None
                if "houses" in chart and isinstance(chart["houses"], list) and len(chart["houses"]) >= house_num:
                    house_longitude = chart["houses"][house_num - 1]
                    # Calculate sign from longitude
                    house_sign_index = int(house_longitude / 30) % 12
                    # Convert to sign name if needed
                    house_sign = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                                 "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"][house_sign_index]

                chart_data["planets"][planet_name] = {
                    "sign": planet_data.get("sign", ""),
                    "degree": planet_data.get("longitude", 0.0) % 30,  # Get degree within sign
                    "longitude": planet_data.get("longitude", 0.0),
                    "retrograde": planet_data.get("retrograde", False),
                    "house": house_num,
                    "house_sign": house_sign
                }
        except Exception as e:
            logger.error(f"Error extracting planet {planet_name}: {e}")
            # Continue with other planets instead of failing

    # Extract house cusps
    chart_data["houses"] = {}
    if "houses" in chart and isinstance(chart["houses"], list):
        for house_num in range(1, min(13, len(chart["houses"]) + 1)):
            try:
                house_idx = house_num - 1
                if house_idx < len(chart["houses"]):
                    house_longitude = chart["houses"][house_idx]

                    # Calculate sign from longitude
                    sign_index = int(house_longitude / 30) % 12
                    # Convert to sign name
                    sign_name = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"][sign_index]

                    chart_data["houses"][house_num] = {
                        "sign": sign_name,
                        "degree": house_longitude % 30,  # Get degree within sign
                        "longitude": house_longitude
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
    planet_list = PLANETS_LIST
    for i, p1 in enumerate(planet_list):
        for p2 in planet_list[i+1:]:
            try:
                p1_key = p1.lower()
                p2_key = p2.lower()

                if "planets" in chart and p1_key in chart["planets"] and p2_key in chart["planets"]:
                    planet1_data = chart["planets"][p1_key]
                    planet2_data = chart["planets"][p2_key]

                    # Calculate orb (difference in degrees)
                    if "longitude" in planet1_data and "longitude" in planet2_data:
                        diff = abs(planet1_data["longitude"] - planet2_data["longitude"]) % 360
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
            # Validate string is not empty before converting to int
            if rectified_time_str.strip():
                hours = int(rectified_time_str)
            else:
                raise ValueError("Empty time string")
            minutes = 0
        else:
            time_parts = rectified_time_str.split(":")
            # Validate parts are not empty before converting to int
            if time_parts[0].strip():
                hours = int(time_parts[0])
            else:
                raise ValueError("Empty hours part")

            if len(time_parts) > 1 and time_parts[1].strip():
                minutes = int(time_parts[1])
            else:
                minutes = 0

        # Validate time values
        hours = max(0, min(23, hours))
        minutes = max(0, min(59, minutes))

        # Create the rectified datetime
        rectified_dt = birth_dt.replace(hour=hours, minute=minutes)

        # Get confidence score (default to 80 if not provided)
        confidence = float(ai_result.get("confidence", 80.0))

        # Ensure confidence is within reasonable range
        confidence = max(60.0, min(95.0, confidence))  # Bound between 60-95%

        logger.info(f"AI rectification result: {rectified_dt.strftime('%H:%M')} with {confidence}% confidence")

        return rectified_dt, confidence

    except (ValueError, TypeError, IndexError) as e:
        logger.error(f"Error parsing rectified time '{rectified_time_str}': {e}")
        raise ValueError(f"Failed to parse rectified time from AI response: {e}")
