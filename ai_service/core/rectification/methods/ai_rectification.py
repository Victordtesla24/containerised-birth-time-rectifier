"""
AI-assisted birth time rectification module.
"""
from datetime import datetime, time as datetime_time
import logging
import json
import re
from typing import Any, Dict, Optional, List
import asyncio
import traceback

# Use absolute import
from ai_service.core.rectification.chart_calculator import calculate_chart

logger = logging.getLogger(__name__)

async def ai_assisted_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    openai_service: Any,
    *,  # Force keyword arguments after this point
    time_indicators: Optional[List[Dict[str, Any]]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> Dict[str, Any]:
    """
    Perform birth time rectification using AI analysis of answers and events.

    Args:
        birth_dt: Original birth datetime
        latitude: Birth latitude in decimal degrees
        longitude: Birth longitude in decimal degrees
        timezone: Timezone string (e.g., 'America/New_York')
        openai_service: OpenAI service instance for AI analysis
        time_indicators: Optional list of birth time indicators from questionnaire
        events: Optional list of life events
        max_retries: Maximum number of OpenAI API retries
        retry_delay: Delay between retries in seconds

    Returns:
        Dictionary with rectification results including rectified time and confidence

    Raises:
        ValueError: If required parameters are missing
        RuntimeError: If rectification process fails
    """
    # Validate required inputs
    if not openai_service:
        raise ValueError("OpenAI service is required for AI-assisted rectification")

    original_time = birth_dt.strftime("%H:%M:%S")
    logger.info("Starting AI-assisted rectification for birth time %s", original_time)

    # Calculate initial chart for the original birth time
    try:
        chart_data = calculate_chart(
            birth_dt=birth_dt,
            latitude=latitude,
            longitude=longitude,
            timezone_str=timezone
        )
    except Exception as e:
        logger.error("Error calculating initial chart: %s", e)
        logger.error(traceback.format_exc())
        raise ValueError(f"Failed to calculate initial chart: {str(e)}") from e

    # Extract key data from chart
    try:
        ascendant = chart_data.get("ascendant", {})
        planets = chart_data.get("planets", {})
        houses = chart_data.get("houses", [])

        ascendant_sign = ascendant.get("sign", "Unknown")
        ascendant_degree = ascendant.get("longitude", 0) % 30

        # Format chart elements for the prompt
        chart_elements = {
            "ascendant": {
                "sign": ascendant_sign,
                "degree": round(ascendant_degree, 2)
            },
            "houses": [],
            "planets": []
        }

        # Add houses
        for house in houses:
            if isinstance(house, dict):
                chart_elements["houses"].append({
                    "number": house.get("number", 0),
                    "sign": house.get("sign", ""),
                    "degree": house.get("longitude", 0) % 30
                })

        # Add planets
        for planet_name, planet_data in planets.items():
            chart_elements["planets"].append({
                "name": planet_name,
                "sign": planet_data.get("sign", ""),
                "degree": planet_data.get("longitude", 0) % 30,
                "house": planet_data.get("house", 0)
            })
    except Exception as e:
        logger.error("Error extracting chart elements: %s", e)
        chart_elements = {"error": "Failed to extract chart elements"}

    # Format answers for the prompt
    formatted_answers = []
    if time_indicators:
        for indicator in time_indicators:
            question = indicator.get("question", "")
            response = indicator.get("response", "")

            if not question and "text" in indicator:
                question = indicator.get("text", "")

            if not response and "response" in indicator:
                response = indicator.get("response", "")

            if question and response:
                formatted_answers.append({
                    "question": question,
                    "response": response
                })

    # Format life events for the prompt
    formatted_events = []
    if events:
        for event in events:
            event_type = event.get("event_type", "general")
            date = event.get("date", "unknown")
            description = event.get("description", "")

            if date and description:
                formatted_events.append({
                    "type": event_type,
                    "date": date,
                    "description": description
                })

    # Create a structured prompt for OpenAI
    prompt_data = {
        "task": "birth_time_rectification",
        "birth_details": {
            "date": birth_dt.strftime("%Y-%m-%d"),
            "time": birth_dt.strftime("%H:%M:%S"),
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone
        },
        "chart_elements": chart_elements,
        "answers": formatted_answers,
        "life_events": formatted_events,
        "instructions": [
            "Analyze the birth chart, questionnaire answers, and life events",
            "Determine if the birth time needs adjustment based on astrological principles",
            "Provide a rectified birth time with confidence score and explanation",
            "Consider rising sign precision, house cusps, and planetary placements",
            "Analyze life events in relation to transits and progressions",
            "Return results in a structured JSON format"
        ]
    }

    # Convert prompt to JSON string
    prompt_str = json.dumps(prompt_data)

    # Call OpenAI with retry logic
    retry_count = 0
    result = None

    while retry_count < max_retries:
        try:
            # Call OpenAI service
            ai_response = await openai_service.generate_completion(
                prompt=prompt_str,
                task_type="birth_time_rectification",
                max_tokens=1500
            )

            # Parse the result
            result = await parse_ai_response(ai_response)

            # Successful response, break the loop
            break

        except Exception as e:
            retry_count += 1
            logger.warning("OpenAI API error (attempt %s/%s): %s", retry_count, max_retries, e)

            if retry_count < max_retries:
                await asyncio.sleep(retry_delay * retry_count)  # Exponential backoff
            else:
                logger.error("OpenAI API failed after %s attempts: %s", max_retries, e)
                logger.error(traceback.format_exc())
                raise ValueError(f"Failed to get AI analysis after {max_retries} attempts: {str(e)}") from e

    # Process the AI response
    if not result:
        raise ValueError("Failed to get valid response from AI analysis")

    # Extract rectified time
    try:
        rectified_time_str = result.get("rectified_time", original_time)
        confidence_score = float(result.get("confidence", 60.0))

        # Parse the rectified time
        rectified_time = await parse_rectified_time(rectified_time_str, birth_dt)

        # Log the result
        time_diff = rectified_time - birth_dt
        minutes_diff = time_diff.total_seconds() / 60
        logger.info("AI rectification suggests time adjustment of %.1f minutes", minutes_diff)
        logger.info("Rectified time: %s, confidence: %.1f", rectified_time.strftime('%H:%M:%S'), confidence_score)

        return {
            "rectified_time": rectified_time.strftime("%H:%M:%S"),
            "confidence": confidence_score,
            "explanation": result.get("explanation", "No explanation provided")
        }

    except Exception as e:
        logger.error("Error processing AI rectification result: %s", e)
        logger.error(traceback.format_exc())
        raise ValueError(f"Failed to process AI rectification result: {str(e)}") from e

async def parse_ai_response(content: str) -> Dict[str, Any]:
    """
    Parse the response from OpenAI into a structured format.

    Args:
        content: Response content from OpenAI

    Returns:
        Dictionary with parsed rectification data
    """
    # If content is already a dictionary, return it
    if isinstance(content, dict):
        return content

    # If content is a string, try to parse it as JSON
    try:
        # Extract JSON if embedded in text
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)

        if json_match:
            json_str = json_match.group(1)
            return json.loads(json_str)

        # Try direct JSON parsing
        return json.loads(content)
    except json.JSONDecodeError:
        # If not valid JSON, extract key information using regex
        result = {}

        # Extract rectified time
        time_match = re.search(r'rectified\s+time\s*(?:is|:)\s*(\d{1,2}:\d{2}(?::\d{2})?)', content, re.IGNORECASE)
        if time_match:
            result["rectified_time"] = time_match.group(1)

        # Extract confidence score
        confidence_match = re.search(r'confidence\s*(?:score|level|:)\s*(\d+\.?\d*)', content, re.IGNORECASE)
        if confidence_match:
            result["confidence"] = float(confidence_match.group(1))
        else:
            # Default confidence
            result["confidence"] = 60.0

        # Extract explanation
        explanation_match = re.search(r'explanation\s*(?::|is)\s*(.*?)(?:\n\n|\Z)', content, re.DOTALL | re.IGNORECASE)
        if explanation_match:
            result["explanation"] = explanation_match.group(1).strip()

        return result

async def parse_rectified_time(time_str: str, birth_dt: datetime) -> datetime:
    """
    Parse a rectified time string and return a datetime object.

    Args:
        time_str: Time string in various formats (e.g., "14:30", "2:30 PM")
        birth_dt: Original birth datetime for reference

    Returns:
        Datetime object with the rectified time
    """
    # Clean the time string
    time_str = time_str.strip()

    # Try parsing different time formats
    formats = [
        "%H:%M:%S",  # 14:30:00
        "%H:%M",     # 14:30
        "%I:%M %p",  # 2:30 PM
        "%I:%M%p",   # 2:30PM
        "%I:%M:%S %p",  # 2:30:00 PM
        "%I:%M:%S%p"    # 2:30:00PM
    ]

    parsed_time = None

    for fmt in formats:
        try:
            # Add seconds if not present in format
            if "%S" not in fmt and len(time_str.split(":")) == 2:
                time_str += ":00"

            # Try parsing
            parsed_time = datetime.strptime(time_str, fmt).time()
            break
        except ValueError:
            continue

    if not parsed_time:
        # Try extracting time components with regex
        hour_minute_match = re.search(r'(\d{1,2})(?::(\d{1,2}))?(?::(\d{1,2}))?\s*(am|pm)?', time_str, re.IGNORECASE)

        if hour_minute_match:
            hour = int(hour_minute_match.group(1))
            minute = int(hour_minute_match.group(2) or "0")
            second = int(hour_minute_match.group(3) or "0")
            am_pm = hour_minute_match.group(4)

            # Adjust hour for PM
            if am_pm and am_pm.lower() == "pm" and hour < 12:
                hour += 12
            elif am_pm and am_pm.lower() == "am" and hour == 12:
                hour = 0

            parsed_time = datetime_time(hour, minute, second)

    if not parsed_time:
        raise ValueError(f"Could not parse time: {time_str}")

    # Combine the parsed time with the original date
    return birth_dt.replace(
        hour=parsed_time.hour,
        minute=parsed_time.minute,
        second=parsed_time.second,
        microsecond=0
    )
