"""
Utility functions for the questionnaire service.

This module contains helper functions for parsing and processing data in the questionnaire service.
"""

import logging
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

# logger initialization
logger = logging.getLogger(__name__)

def _parse_text_response(self, content: str) -> Dict[str, Any]:
    """
    Parse a text response (potentially containing JSON) into a structured format.

    Args:
        content: Text content, possibly containing JSON

    Returns:
        Structured dictionary from the parsed content
    """
    try:
        # Try to parse as JSON directly
        return json.loads(content)
    except json.JSONDecodeError:
        # If direct parsing fails, try to extract JSON from the text
        return self._extract_json_from_content(content)

def _extract_json_from_content(self, content: str) -> Dict[str, Any]:
    """
    Extract JSON from a text content that might contain other text.

    Args:
        content: Text content that might contain JSON

    Returns:
        Extracted JSON as a dictionary
    """
    try:
        # Find JSON-like patterns with regex
        json_pattern = r'(\{[\s\S]*\})'
        json_match = re.search(json_pattern, content)

        if json_match:
            # Try to parse the extracted JSON
            json_str = json_match.group(1)
            return json.loads(json_str)

        # If no JSON found, return empty dict
        return {}
    except Exception as e:
        logger.error(f"Error extracting JSON from content: {e}")
        return {}

def _enhance_astrological_analysis(
    self,
    analysis: Dict[str, Any],
    question: str,
    answer: str,
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    chart_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Enhance astrological analysis with additional details.

    Args:
        analysis: Base analysis to enhance
        question: Original question
        answer: User's answer
        birth_date: Birth date string
        birth_time: Birth time string
        latitude: Birth latitude
        longitude: Birth longitude
        chart_data: Chart data dictionary

    Returns:
        Enhanced analysis dictionary
    """
    # Start with the original analysis
    enhanced = analysis.copy()

    # If analysis is empty, create basic structure
    if not enhanced:
        enhanced = {
            "houses": {},
            "planets": {},
            "ascendant": {},
            "time_indicators": {}
        }

    # Make sure all expected sections exist
    if "houses" not in enhanced:
        enhanced["houses"] = {}

    if "planets" not in enhanced:
        enhanced["planets"] = {}

    if "ascendant" not in enhanced:
        enhanced["ascendant"] = {}

    if "time_indicators" not in enhanced:
        enhanced["time_indicators"] = {}

    # Add chart data if available
    if chart_data:
        # Add ascendant info
        if not enhanced["ascendant"] and "ascendant" in chart_data:
            enhanced["ascendant"] = chart_data["ascendant"]

        # Add planet info
        if "planets" in chart_data:
            for planet, data in chart_data["planets"].items():
                if planet not in enhanced["planets"]:
                    enhanced["planets"][planet] = data

        # Add house info
        if "houses" in chart_data:
            for i, house in enumerate(chart_data["houses"]):
                house_num = str(i + 1)
                if house_num not in enhanced["houses"]:
                    enhanced["houses"][house_num] = house

    # Add question and answer context
    enhanced["context"] = {
        "question": question,
        "answer": answer,
        "birth_details": {
            "date": birth_date,
            "time": birth_time,
            "latitude": latitude,
            "longitude": longitude
        }
    }

    # Add metadata
    enhanced["metadata"] = {
        "analysis_type": "astrological",
        "version": "1.0",
        "generated_at": datetime.now().isoformat()
    }

    return enhanced

def _assess_time_precision(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess the precision of time indicators in an analysis.

    Args:
        analysis: Astrological analysis dictionary

    Returns:
        Dictionary with precision assessment
    """
    precision = {
        "level": "low",
        "range_hours": 6,
        "confidence": 0.3,
        "factors": []
    }

    # Check for time indicators
    time_indicators = analysis.get("time_indicators", {})
    if not time_indicators:
        return precision

    # Check for narrowed range
    narrowed_range = time_indicators.get("narrowed_range", "")
    if narrowed_range:
        try:
            # Parse range like "10:00-12:00"
            start, end = narrowed_range.split("-")

            # Extract hours
            start_hour = int(start.split(":")[0])
            end_hour = int(end.split(":")[0])

            # Calculate range in hours (handling day boundary crossing)
            if end_hour < start_hour:
                end_hour += 24

            range_hours = end_hour - start_hour

            # Set precision based on range
            if range_hours <= 1:
                precision["level"] = "very high"
                precision["range_hours"] = range_hours
                precision["confidence"] = 0.9
                precision["factors"].append(f"Narrow time range of {range_hours} hours")
            elif range_hours <= 2:
                precision["level"] = "high"
                precision["range_hours"] = range_hours
                precision["confidence"] = 0.8
                precision["factors"].append(f"Time range of {range_hours} hours")
            elif range_hours <= 4:
                precision["level"] = "medium"
                precision["range_hours"] = range_hours
                precision["confidence"] = 0.6
                precision["factors"].append(f"Time range of {range_hours} hours")
            else:
                precision["level"] = "low"
                precision["range_hours"] = range_hours
                precision["confidence"] = 0.4
                precision["factors"].append(f"Wide time range of {range_hours} hours")
        except Exception as e:
            logger.warning(f"Error parsing time range: {e}")

    # Check for confidence level
    confidence = time_indicators.get("confidence", "")
    if confidence:
        confidence_map = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3
        }

        if isinstance(confidence, str) and confidence.lower() in confidence_map:
            # Adjust confidence based on stated level
            confidence_value = confidence_map[confidence.lower()]

            # Average with existing confidence
            precision["confidence"] = (precision["confidence"] + confidence_value) / 2
            precision["factors"].append(f"{confidence.capitalize()} confidence stated in analysis")

    # Update level based on final confidence
    if precision["confidence"] >= 0.8:
        precision["level"] = "very high"
    elif precision["confidence"] >= 0.7:
        precision["level"] = "high"
    elif precision["confidence"] >= 0.5:
        precision["level"] = "medium"
    else:
        precision["level"] = "low"

    return precision
