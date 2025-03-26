"""
Questionnaire completion module for the questionnaire service.

This module contains functions for completing and analyzing the full questionnaire.
"""

import logging
import traceback
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# logger initialization
logger = logging.getLogger(__name__)

try:
    from timezonefinder import TimezoneFinder
    TIMEZONE_FINDER_AVAILABLE = True
except ImportError:
    TIMEZONE_FINDER_AVAILABLE = False

from ai_service.api.services.openai import get_openai_service, OpenAIService
from ai_service.api.services.session_service import get_session_store
from ai_service.services import get_chart_service
from ai_service.api.services.chart_calculator_service import chart_calculator

async def complete_questionnaire(self, session_id: str, chart_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Complete the questionnaire and generate birth time rectification with enhanced astrological insights.

    This method analyzes all questionnaire responses, extracts birth time indicators,
    correlates them with astrological principles, and provides comprehensive rectification
    results with deep astrological insights.

    Args:
        session_id: Session ID for the questionnaire
        chart_id: Optional chart ID to update with rectification

    Returns:
        Dictionary with questionnaire completion results including deep astrological insights
    """
    try:
        # Get session store
        session_store = self.session_store
        if not session_store:
            from ai_service.api.services.session_service import get_session_store
            session_store = get_session_store()

        if not session_store:
            return {
                "status": "error",
                "message": "Session store not available"
            }

        # Get session data
        session = await session_store.get_session(session_id)
        if not session:
            return {
                "status": "error",
                "message": "Session not found"
            }

        # Get questionnaire data
        questionnaire_data = session.get("questionnaire", {})
        responses = questionnaire_data.get("answers", [])

        if not responses:
            return {
                "status": "error",
                "message": "No answers found in questionnaire"
            }

        # Get birth details from session
        birth_details = session.get("birth_details", {})
        if not birth_details:
            return {
                "status": "error",
                "message": "No birth details found in session"
            }

        # Extract birth time indicators from responses using enhanced pattern recognition
        birth_time_indicators = []
        for response in responses:
            # Get question and answer
            question = response.get("question", {})
            if isinstance(question, dict):
                question_text = question.get("text", "")
            else:
                question_text = str(question)

            answer = response.get("answer")
            if answer is None:
                continue

            # Extract time indicators with enhanced pattern recognition
            time_indicator = await self._extract_birth_time_indicators(question_text, answer)
            if time_indicator:
                birth_time_indicators.append({
                    "question": question_text,
                    "answer": answer,
                    "indicators": time_indicator
                })

        # Group and categorize responses by astrological relevance
        categorized_responses = self._categorize_responses(responses)

        # Log the categorization for tracking effectiveness
        logger.info(f"Categorized {len(responses)} responses into {len(categorized_responses)} categories")
        for category, items in categorized_responses.items():
            logger.info(f"Category '{category}': {len(items)} responses")

        # Perform comprehensive analysis with enhanced astrological insights
        analysis = await self._perform_comprehensive_analysis(
            responses,
            birth_details,
            birth_time_indicators
        )

        # Extract confidence score
        confidence = analysis.get("confidence", 0)

        # Get time adjustment
        time_adjustment = analysis.get("time_adjustment", {})

        # Get birth time range
        birth_time_range = analysis.get("birth_time_range", {})

        # Extract deep astrological insights
        astrological_insights = analysis.get("astrological_insights", {})

        # Generate astrological report with enhanced insights
        report = self._generate_astrological_report(
            analysis,
            birth_details,
            confidence
        )

        # Prepare comprehensive response with enhanced astrological data
        response = {
            "status": "complete",
            "session_id": session_id,
            "confidence": confidence,
            "birth_time_range": birth_time_range,
            "time_adjustment": time_adjustment,
            "report": report,
            "analysis": analysis,
            "astrological_insights": astrological_insights,
            "ascendant": analysis.get("ascendant", {}),
            "moon_sign": analysis.get("moon_sign", {}),
            "dominant_planets": analysis.get("dominant_planets", []),
            "house_analysis": analysis.get("house_analysis", {})
        }

        # If chart_id is provided, try to update it with rectified time
        if chart_id:
            try:
                from ai_service.services import get_chart_service
                chart_service = get_chart_service()

                if chart_service:
                    # Extract the original and rectified birth times
                    original_birth_time = birth_details.get("birth_time", birth_details.get("birthTime", ""))
                    rectified_birth_time = birth_time_range.get("most_likely_time", "")

                    # If there's no explicit most likely time, calculate based on mid-range
                    if not rectified_birth_time and birth_time_range.get("start") and birth_time_range.get("end"):
                        start_time = birth_time_range.get("start")
                        end_time = birth_time_range.get("end")

                        # Calculate mid-point time
                        try:
                            def parse_time(time_str):
                                if not time_str or ":" not in time_str:
                                    return 0
                                parts = time_str.split(":")
                                hours = int(parts[0])
                                minutes = int(parts[1]) if len(parts) > 1 else 0
                                return hours * 60 + minutes  # Convert to minutes

                            # Ensure we have valid time strings before processing
                            if start_time and end_time and ":" in start_time and ":" in end_time:
                                start_minutes = parse_time(start_time)
                                end_minutes = parse_time(end_time)

                                # Handle day boundary crossing
                                if end_minutes < start_minutes:
                                    end_minutes += 24 * 60  # Add a day

                                mid_minutes = (start_minutes + end_minutes) // 2
                                mid_hours = (mid_minutes // 60) % 24
                                mid_minutes = mid_minutes % 60

                                rectified_birth_time = f"{mid_hours:02d}:{mid_minutes:02d}"
                                birth_time_range["most_likely_time"] = rectified_birth_time
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Error calculating mid-point time: {e}")


                    # Only update chart if we have a valid rectified time
                    if rectified_birth_time:
                        logger.info(f"Updating chart {chart_id} with rectified time {rectified_birth_time}")

                        try:
                            # Calculate a chart with the rectified birth time
                            result = chart_service.calculate_chart(
                                birth_date=birth_details.get("birth_date", ""),
                                birth_time=rectified_birth_time,
                                latitude=birth_details.get("latitude", 0),
                                longitude=birth_details.get("longitude", 0),
                                timezone=birth_details.get("timezone", "UTC"),
                                chart_type="vedic",
                                house_system="placidus"
                            )

                            if result:
                                # Try to update the existing chart with rectification data if that method exists
                                try:
                                    if hasattr(chart_service, 'update_chart_with_rectification'):
                                        # If the service has the update_chart_with_rectification method, use it
                                        update_result = await chart_service.update_chart_with_rectification(
                                            chart_id=chart_id,
                                            rectification_data={
                                                "original_birth_time": original_birth_time,
                                                "rectified_birth_time": rectified_birth_time,
                                                "confidence": confidence,
                                                "birth_time_range": birth_time_range,
                                                "ascendant": analysis.get("ascendant", {})
                                            }
                                        )
                                        if update_result:
                                            response["rectified_chart_id"] = update_result.get("chart_id", chart_id)
                                            response["chart_updated"] = True
                                except Exception as update_error:
                                    logger.warning(f"Could not update chart with rectification: {update_error}")

                                # Regardless of whether update succeeded, include chart data in response
                                response["chart_data"] = {
                                    "planets": result.get("planets", {}),
                                    "houses": result.get("houses", {}),
                                    "angles": result.get("angles", {})
                                }
                        except Exception as calc_error:
                            logger.error(f"Error calculating rectified chart: {calc_error}")
                            response["chart_updated"] = False
                            response["chart_error"] = str(calc_error)
            except Exception as chart_error:
                logger.error(f"Error updating chart with rectified time: {chart_error}")
                response["chart_updated"] = False
                response["chart_error"] = str(chart_error)

        # Update session with completion data
        session["questionnaire_completion"] = {
            "completed_at": datetime.now().isoformat(),
            "confidence": confidence,
            "birth_time_range": birth_time_range,
            "time_adjustment": time_adjustment
        }
        await session_store.update_session(session_id, session)

        return response

    except Exception as e:
        logger.error(f"Error completing questionnaire: {e}")
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Error completing questionnaire: {str(e)}"
        }

async def _perform_comprehensive_analysis(
    self,
    responses: List[Dict[str, Any]],
    birth_details: Dict[str, Any],
    birth_time_indicators: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of questionnaire responses to determine birth time.

    Args:
        responses: List of questionnaire responses
        birth_details: Dictionary of birth details
        birth_time_indicators: Optional list of pre-extracted time indicators

    Returns:
        Comprehensive analysis dictionary

    Raises:
        ValueError: When OpenAI service is not available or analysis fails
    """
    try:
        # Initialize OpenAI service
        openai_service = await get_openai_service()
        if not openai_service:
            raise ValueError("OpenAI service is not available")

        # Format data for analysis
        birth_date = birth_details.get("birth_date", "")
        birth_time = birth_details.get("birth_time", "")
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        location = birth_details.get("birth_place", "")

        # Format responses
        formatted_responses = ""
        for idx, response in enumerate(responses):
            question = response.get("question", "")
            answer = response.get("answer", "")
            formatted_responses += f"Q{idx+1}: {question}\nA{idx+1}: {answer}\n\n"

        # Create analysis prompt
        system_prompt = """
        You are an expert Vedic astrologer specializing in birth time rectification.

        Your task is to analyze questionnaire responses and birth details to determine
        the most accurate birth time. Consider all responses carefully, prioritizing
        those that relate to major life events, personality traits, and physical characteristics
        that are strongly influenced by birth time.

        Provide a comprehensive analysis including:

        1. A refined birth time estimate (specific time or narrow range)
        2. Confidence level (percentage)
        3. The likely ascendant (rising sign) and degree
        4. Key factors that influenced your determination
        5. House analysis based on the rectified time

        Format your response as a detailed JSON object that can be parsed by our system.
        """

        user_prompt = f"""
        BIRTH DETAILS:
        Date: {birth_date}
        Approximate Time: {birth_time}
        Location: {location} (Lat: {latitude}, Lon: {longitude})

        QUESTIONNAIRE RESPONSES:
        {formatted_responses}

        Based on this information, please provide a comprehensive birth time rectification analysis.
        Format your response as a JSON object with these sections:
        - birth_time_range (start, end, most_likely_time)
        - time_adjustment (minutes, direction, explanation)
        - confidence (percentage)
        - ascendant (sign, degree)
        - key_factors (array of factors with explanations)
        - house_analysis (analysis of key houses)
        """

        # Call OpenAI API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await openai_service.chat_completion(
            messages=messages,
            model="gpt-4",
            temperature=0.2
        )

        # Extract and parse the response
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # Parse the response
        import json
        import re

        try:
            # First try direct parsing
            analysis = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON using regex
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    # Try another pattern
                    json_str = re.search(r'({[\s\S]*})', content)
                    if json_str:
                        try:
                            analysis = json.loads(json_str.group(1))
                        except Exception:
                            # Return basic analysis if parsing fails
                            logger.error("Could not parse JSON from response")
                            analysis = {
                                "birth_time_range": {
                                    "start": birth_time,
                                    "end": birth_time,
                                    "most_likely_time": birth_time
                                },
                                "confidence": 50.0,
                                "key_factors": ["Failed to parse structured analysis"],
                                "error": "Failed to parse JSON response"
                            }
                    else:
                        # Return basic analysis if no JSON found
                        logger.error("No JSON found in response")
                        analysis = {
                            "birth_time_range": {
                                "start": birth_time,
                                "end": birth_time,
                                "most_likely_time": birth_time
                            },
                            "confidence": 50.0,
                            "key_factors": ["Failed to parse structured analysis"],
                            "error": "No JSON found in response"
                        }
            else:
                # Return basic analysis if no JSON block found
                logger.error("No JSON block found in response")
                analysis = {
                    "birth_time_range": {
                        "start": birth_time,
                        "end": birth_time,
                        "most_likely_time": birth_time
                    },
                    "confidence": 50.0,
                    "key_factors": ["Failed to parse structured analysis"],
                    "error": "No JSON block found in response"
                }

        # Ensure required fields are present
        if not isinstance(analysis, dict):
            analysis = {}

        if "birth_time_range" not in analysis:
            analysis["birth_time_range"] = {
                "start": birth_time,
                "end": birth_time,
                "most_likely_time": birth_time
            }

        if "confidence" not in analysis:
            analysis["confidence"] = 50.0

        if "key_factors" not in analysis:
            analysis["key_factors"] = []

        return analysis

    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {str(e)}")
        # Return minimal analysis on error
        return {
            "birth_time_range": {
                "start": birth_details.get("birth_time", "Unknown"),
                "end": birth_details.get("birth_time", "Unknown"),
                "most_likely_time": birth_details.get("birth_time", "Unknown")
            },
            "confidence": 50.0,
            "error": str(e)
        }

def _generate_astrological_report(
    self,
    comprehensive_analysis: Dict[str, Any],
    birth_details: Dict[str, Any],
    confidence: float
) -> Dict[str, Any]:
    """
    Generate a human-readable astrological report based on comprehensive analysis.

    Args:
        comprehensive_analysis: Dictionary with comprehensive analysis
        birth_details: Dictionary with birth details
        confidence: Confidence score

    Returns:
        Dictionary with astrological report
    """
    report = {}

    # Add summary
    report["summary"] = {
        "title": "Birth Time Rectification Summary",
        "confidence_level": self._describe_confidence_level(confidence),
        "confidence_score": round(confidence, 1)
    }

    # Add birth time information
    birth_time_range = comprehensive_analysis.get("birth_time_range", {})
    time_adjustment = comprehensive_analysis.get("time_adjustment", {})

    original_time = birth_details.get("birth_time", "Unknown")

    report["birth_time"] = {
        "original_time": original_time,
        "rectified_time": birth_time_range.get("most_likely_time", original_time),
        "possible_range": f"{birth_time_range.get('start', '')} - {birth_time_range.get('end', '')}",
        "adjustment": f"{time_adjustment.get('minutes', 0)} minutes {time_adjustment.get('direction', '')}",
        "explanation": time_adjustment.get("explanation", "")
    }

    # Add ascendant information
    ascendant = comprehensive_analysis.get("ascendant", {})

    report["ascendant"] = {
        "sign": ascendant.get("sign", "Unknown"),
        "degree": ascendant.get("degree", 0),
        "explanation": "The Ascendant represents your physical appearance, personality, and approach to life."
    }

    # Add key factors
    key_factors = comprehensive_analysis.get("key_factors", [])

    report["key_factors"] = [
        {
            "factor": factor.get("factor", ""),
            "explanation": factor.get("explanation", "")
        }
        for factor in key_factors
    ]

    # Add house analysis
    house_analysis = comprehensive_analysis.get("house_analysis", {})
    houses = house_analysis.get("houses", [])

    report["house_analysis"] = [
        {
            "house": house.get("house", 0),
            "planets": house.get("planets", []),
            "significance": house.get("significance", "")
        }
        for house in houses
    ]

    # Add methodologies used
    report["methodologies"] = [
        {
            "name": "Questionnaire Analysis",
            "description": "Analysis of your responses to determine personality traits, life events, and physical characteristics."
        },
        {
            "name": "Ascendant Sign Analysis",
            "description": "Determining the most likely Ascendant sign based on physical appearance and personality."
        },
        {
            "name": "Life Event Timing",
            "description": "Analyzing the timing of significant life events to correlate with planetary transits."
        }
    ]

    # Add recommendations
    report["recommendations"] = [
        {
            "title": "Use Rectified Time for Future Readings",
            "description": f"Use the rectified birth time ({birth_time_range.get('most_likely_time', original_time)}) for future astrological readings."
        },
        {
            "title": "Verify with Major Life Events",
            "description": "Continue to verify the accuracy of this rectified time by checking if it correctly predicts major life events."
        }
    ]

    return report

def _describe_confidence_level(self, confidence: float) -> str:
    """
    Describe the confidence level in human-readable terms.

    Args:
        confidence: Confidence score (0-100)

    Returns:
        Human-readable confidence description
    """
    if confidence >= 90:
        return "Very High"
    elif confidence >= 75:
        return "High"
    elif confidence >= 60:
        return "Moderate"
    elif confidence >= 45:
        return "Fair"
    else:
        return "Low"

def _calculate_time_adjustment(
    self,
    time_indicators: Dict[str, Any],
    comprehensive_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate time adjustment based on time indicators and comprehensive analysis.

    Args:
        time_indicators: Dictionary with time indicators
        comprehensive_analysis: Dictionary with comprehensive analysis

    Returns:
        Dictionary with time adjustment details
    """
    # Start with any adjustment from comprehensive analysis
    adjustment = comprehensive_analysis.get("time_adjustment", {})

    # If no adjustment in analysis, calculate from time indicators
    if not adjustment:
        adjustment = {
            "minutes": 0,
            "direction": "none",
            "explanation": "No significant time adjustment required."
        }

        # Extract time of day from indicators
        time_of_day = time_indicators.get("time_of_day", "")
        time_range = time_indicators.get("time_range", "")

        if time_of_day and time_range:
            original_time = comprehensive_analysis.get("original_time", "")
            if original_time:
                try:
                    # Parse original time
                    hours, minutes = map(int, original_time.split(":"))
                    original_minutes = hours * 60 + minutes

                    # Parse time range
                    start_time, end_time = time_range.split("-")
                    start_hours, start_minutes = map(int, start_time.split(":"))
                    end_hours, end_minutes = map(int, end_time.split(":"))

                    start_total_minutes = start_hours * 60 + start_minutes
                    end_total_minutes = end_hours * 60 + end_minutes

                    # Handle day boundary crossing
                    if end_total_minutes < start_total_minutes:
                        end_total_minutes += 24 * 60

                    # Calculate midpoint of time range
                    mid_total_minutes = (start_total_minutes + end_total_minutes) // 2

                    # Calculate adjustment
                    diff_minutes = mid_total_minutes - original_minutes

                    # Handle day boundary crossing for diff
                    if diff_minutes > 12 * 60:
                        diff_minutes -= 24 * 60
                    elif diff_minutes < -12 * 60:
                        diff_minutes += 24 * 60

                    # Set direction based on diff
                    direction = "later" if diff_minutes > 0 else "earlier"

                    # Update adjustment
                    adjustment = {
                        "minutes": abs(diff_minutes),
                        "direction": direction,
                        "explanation": f"Adjusted based on time of day indicator: {time_of_day}"
                    }
                except Exception as e:
                    logger.warning(f"Error calculating time adjustment: {e}")

    return adjustment

def _determine_birth_time_range(
    self,
    time_indicators: Dict[str, Any],
    comprehensive_analysis: Dict[str, Any],
    birth_details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Determine birth time range based on time indicators and comprehensive analysis.

    Args:
        time_indicators: Dictionary with time indicators
        comprehensive_analysis: Dictionary with comprehensive analysis
        birth_details: Dictionary with birth details

    Returns:
        Dictionary with birth time range details
    """
    # Start with any range from comprehensive analysis
    birth_time_range = comprehensive_analysis.get("birth_time_range", {})

    # If no range in analysis, calculate from time indicators and original time
    if not birth_time_range or not birth_time_range.get("start") or not birth_time_range.get("end"):
        original_time = birth_details.get("birth_time", "")

        # Default to full day if no information available
        birth_time_range = {
            "start": "00:00",
            "end": "23:59",
            "most_likely_time": original_time if original_time else "12:00"
        }

        # Narrow down based on time of day indicator
        time_of_day = time_indicators.get("time_of_day", "")
        time_range = time_indicators.get("time_range", "")

        if time_range and ":" in time_range:
            try:
                birth_time_range["start"], birth_time_range["end"] = time_range.split("-")

                # If we have an original time, use it as most likely if within range
                if original_time:
                    # Parse all times to minutes since midnight
                    def to_minutes(time_str):
                        hours, minutes = map(int, time_str.split(":"))
                        return hours * 60 + minutes

                    start_minutes = to_minutes(birth_time_range["start"])
                    end_minutes = to_minutes(birth_time_range["end"])
                    original_minutes = to_minutes(original_time)

                    # Handle day boundary crossing
                    if end_minutes < start_minutes:
                        end_minutes += 24 * 60
                        if original_minutes < start_minutes:
                            original_minutes += 24 * 60

                    # Check if original time is within range
                    if start_minutes <= original_minutes <= end_minutes:
                        birth_time_range["most_likely_time"] = original_time
                    else:
                        # If outside range, use midpoint of range
                        mid_minutes = (start_minutes + end_minutes) // 2
                        mid_hours = (mid_minutes // 60) % 24
                        mid_mins = mid_minutes % 60
                        birth_time_range["most_likely_time"] = f"{mid_hours:02d}:{mid_mins:02d}"
            except Exception as e:
                logger.warning(f"Error calculating birth time range: {e}")

    return birth_time_range

def _extract_key_astrological_factors(
    self,
    responses: List[Dict[str, Any]],
    birth_details: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Extract key astrological factors from questionnaire responses.

    Args:
        responses: List of question-answer pairs
        birth_details: Dictionary with birth details

    Returns:
        List of key astrological factors
    """
    factors = []

    # Categorize responses
    categorized = self._categorize_responses(responses)

    # Extract physical traits for Ascendant
    physical_traits = categorized.get("physical_appearance", [])
    if physical_traits:
        trait_signs = {}
        for resp in physical_traits:
            answer = resp.get("answer", "").lower()

            # Check for common physical trait keywords
            trait_map = {
                "tall": ["Aries", "Sagittarius"],
                "lean": ["Gemini", "Virgo"],
                "muscular": ["Leo", "Aries"],
                "balanced": ["Libra"],
                "stocky": ["Taurus", "Capricorn"],
                "round": ["Cancer", "Pisces"],
                "athletic": ["Leo", "Sagittarius"],
                "slender": ["Virgo", "Gemini"],
                "well-proportioned": ["Libra", "Taurus"],
                "heavy-set": ["Taurus", "Cancer"],
                "broad": ["Capricorn", "Scorpio"]
            }

            for trait, signs in trait_map.items():
                if trait in answer:
                    for sign in signs:
                        trait_signs[sign] = trait_signs.get(sign, 0) + 1

        # Find most common Ascendant sign from physical traits
        if trait_signs:
            most_common = max(trait_signs.items(), key=lambda x: x[1])
            factors.append({
                "factor": "Physical Appearance",
                "sign": most_common[0],
                "explanation": f"Physical traits suggest {most_common[0]} Ascendant"
            })

    # Extract personality traits for Ascendant/Moon
    personality_traits = categorized.get("personality", [])
    if personality_traits:
        trait_signs = {}
        for resp in personality_traits:
            answer = resp.get("answer", "").lower()

            # Check for common personality trait keywords
            trait_map = {
                "leader": ["Aries", "Leo"],
                "patient": ["Taurus", "Capricorn"],
                "communicative": ["Gemini", "Libra"],
                "emotional": ["Cancer", "Pisces"],
                "dramatic": ["Leo"],
                "analytical": ["Virgo"],
                "balanced": ["Libra"],
                "intense": ["Scorpio"],
                "adventurous": ["Sagittarius"],
                "disciplined": ["Capricorn"],
                "innovative": ["Aquarius"],
                "creative": ["Pisces"],
                "impulsive": ["Aries"],
                "stubborn": ["Taurus"],
                "curious": ["Gemini"],
                "nurturing": ["Cancer"],
                "confident": ["Leo"],
                "practical": ["Virgo"],
                "diplomatic": ["Libra"],
                "mysterious": ["Scorpio"],
                "philosophical": ["Sagittarius"],
                "ambitious": ["Capricorn"],
                "independent": ["Aquarius"],
                "compassionate": ["Pisces"]
            }

            for trait, signs in trait_map.items():
                if trait in answer:
                    for sign in signs:
                        trait_signs[sign] = trait_signs.get(sign, 0) + 1

        # Find most common sign from personality traits
        if trait_signs:
            most_common = max(trait_signs.items(), key=lambda x: x[1])
            factors.append({
                "factor": "Personality",
                "sign": most_common[0],
                "explanation": f"Personality traits suggest {most_common[0]} influence"
            })

    # Extract life events for timing analysis
    life_events = categorized.get("life_events", [])
    if life_events:
        # Group events by age ranges
        age_ranges = {
            "early_childhood": [],
            "childhood": [],
            "adolescence": [],
            "early_adulthood": [],
            "adulthood": [],
            "middle_age": [],
            "senior": []
        }

        for resp in life_events:
            answer = resp.get("answer", "").lower()

            # Try to extract age
            age_match = re.search(r'age (\d+)', answer)
            if age_match:
                age = int(age_match.group(1))

                # Categorize by age range
                if age <= 5:
                    age_ranges["early_childhood"].append({"age": age, "description": answer})
                elif age <= 12:
                    age_ranges["childhood"].append({"age": age, "description": answer})
                elif age <= 19:
                    age_ranges["adolescence"].append({"age": age, "description": answer})
                elif age <= 29:
                    age_ranges["early_adulthood"].append({"age": age, "description": answer})
                elif age <= 45:
                    age_ranges["adulthood"].append({"age": age, "description": answer})
                elif age <= 65:
                    age_ranges["middle_age"].append({"age": age, "description": answer})
                else:
                    age_ranges["senior"].append({"age": age, "description": answer})

        # Add significant life stages to factors
        for stage, events in age_ranges.items():
            if events:
                factors.append({
                    "factor": f"Life Events ({stage.replace('_', ' ')})",
                    "event_count": len(events),
                    "explanation": f"Significant events during {stage.replace('_', ' ')}"
                })

    return factors

def _calculate_rectification_confidence(
    self,
    answers: List[Dict[str, Any]],
    time_indicators: Dict[str, Any]
) -> float:
    """
    Calculate confidence level for birth time rectification.

    Args:
        answers: List of question-answer pairs
        time_indicators: Dictionary with time indicators

    Returns:
        Confidence score (0-100)
    """
    # Base confidence starts at 50%
    confidence = 50.0

    # Number of answers contributes to confidence
    answer_count = len(answers)
    if answer_count >= 10:
        confidence += 15
    elif answer_count >= 7:
        confidence += 10
    elif answer_count >= 5:
        confidence += 5

    # Time of day indicator provides significant confidence boost
    if "time_of_day" in time_indicators:
        confidence += 15

    # Physical traits that match Ascendant signs
    if "potential_ascendants" in time_indicators:
        confidence += 10

    # Event ages and years provide good confirmation
    if "event_ages" in time_indicators or "event_years" in time_indicators:
        confidence += 10

    # Consistency across multiple indicators
    indicator_count = len(time_indicators)
    if indicator_count >= 3:
        confidence += 15
    elif indicator_count >= 2:
        confidence += 10
    elif indicator_count >= 1:
        confidence += 5

    # Cap confidence at 95% (never 100% certain)
    return min(confidence, 95.0)

def _categorize_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Categorize questionnaire responses by their astrological relevance.

    Args:
        responses: List of question-answer pairs

    Returns:
        Dictionary with responses categorized by astrological theme
    """
    categorized = {
        "physical_appearance": [],
        "personality": [],
        "life_events": [],
        "career": [],
        "relationships": [],
        "early_life": [],
        "health": [],
        "education": [],
        "other": []
    }

    for response in responses:
        # Skip empty responses
        if not response:
            continue

        # Get question text
        question = response.get("question", {})
        if isinstance(question, dict):
            question_text = question.get("text", "").lower()
            category = question.get("category", "").lower()
        else:
            question_text = str(question).lower()
            category = ""

        # Get answer
        answer = response.get("answer", "")
        if not answer:
            continue

        # Categorize based on question content and any provided category
        if any(kw in question_text for kw in ["appearance", "look", "physical", "body", "face", "height", "weight"]):
            categorized["physical_appearance"].append(response)

        elif any(kw in question_text for kw in ["personality", "character", "temperament", "nature", "emotional", "feel", "react"]):
            categorized["personality"].append(response)

        elif any(kw in question_text for kw in ["event", "experience", "happen", "occurred", "significant", "important", "memorable"]):
            categorized["life_events"].append(response)

        elif any(kw in question_text for kw in ["career", "job", "profession", "work", "employment", "occupation", "business"]):
            categorized["career"].append(response)

        elif any(kw in question_text for kw in ["relationship", "marriage", "partner", "spouse", "romantic", "love", "dating"]):
            categorized["relationships"].append(response)

        elif any(kw in question_text for kw in ["childhood", "childhood", "early years", "mother", "father", "parents", "family", "home"]):
            categorized["early_life"].append(response)

        elif any(kw in question_text for kw in ["health", "illness", "medical", "disease", "condition", "doctor", "hospital"]):
            categorized["health"].append(response)

        elif any(kw in question_text for kw in ["education", "school", "college", "university", "learning", "study", "academic"]):
            categorized["education"].append(response)

        # Try to categorize based on provided category if not already categorized
        elif category:
            if category in ["appearance", "physical", "body"]:
                categorized["physical_appearance"].append(response)
            elif category in ["personality", "character", "emotional"]:
                categorized["personality"].append(response)
            elif category in ["events", "life_events", "experiences"]:
                categorized["life_events"].append(response)
            elif category in ["career", "profession", "work"]:
                categorized["career"].append(response)
            elif category in ["relationships", "marriage", "love"]:
                categorized["relationships"].append(response)
            elif category in ["childhood", "early_life", "family"]:
                categorized["early_life"].append(response)
            elif category in ["health", "medical"]:
                categorized["health"].append(response)
            elif category in ["education", "learning", "academic"]:
                categorized["education"].append(response)
            else:
                categorized["other"].append(response)
        else:
            # Check answer content for additional clues
            answer_lower = str(answer).lower()

            if any(kw in answer_lower for kw in ["look like", "appearance", "tall", "short", "body", "face", "hair", "eyes"]):
                categorized["physical_appearance"].append(response)
            elif any(kw in answer_lower for kw in ["i am", "personality", "feel", "emotional", "think", "temperament"]):
                categorized["personality"].append(response)
            elif any(kw in answer_lower for kw in ["happened", "event", "experience", "when i", "at age", "in year"]):
                categorized["life_events"].append(response)
            elif any(kw in answer_lower for kw in ["job", "career", "work", "profession", "business"]):
                categorized["career"].append(response)
            elif any(kw in answer_lower for kw in ["relationship", "partner", "married", "love", "spouse"]):
                categorized["relationships"].append(response)
            elif any(kw in answer_lower for kw in ["childhood", "growing up", "parents", "mother", "father", "home"]):
                categorized["early_life"].append(response)
            elif any(kw in answer_lower for kw in ["health", "sick", "illness", "hospital", "doctor"]):
                categorized["health"].append(response)
            elif any(kw in answer_lower for kw in ["school", "college", "education", "university", "learn"]):
                categorized["education"].append(response)
            else:
                categorized["other"].append(response)

    # Remove empty categories
    return {k: v for k, v in categorized.items() if v}
