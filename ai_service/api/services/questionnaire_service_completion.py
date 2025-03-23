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

from ai_service.api.services.openai import get_openai_service
from ai_service.api.services.session_service import get_session_store
from ai_service.services import get_chart_service
from ai_service.api.services.questionnaire_service_chart_calculator import chart_calculator

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
                            # Use original time as fallback
                            rectified_birth_time = original_birth_time

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
    Perform comprehensive analysis of questionnaire responses with enhanced astrological insights.

    Args:
        responses: List of question-answer pairs
        birth_details: Dictionary with birth details
        birth_time_indicators: Optional list of extracted birth time indicators

    Returns:
        Dictionary with comprehensive analysis including deep astrological insights
    """
    try:
        # Get OpenAI service
        openai_service = self.openai_service
        if not openai_service:
            from ai_service.api.services.openai import get_openai_service
            openai_service = get_openai_service()

        if not openai_service:
            logger.warning("OpenAI service not available for comprehensive analysis")
            # Fallback to simpler analysis
            return self._fallback_comprehensive_analysis(responses, birth_details, birth_time_indicators)

        # Format responses for analysis with categorization
        categorized_responses = self._categorize_responses(responses)

        # Format response data with better structure
        response_sections = []

        # Physical appearance indicators (for Ascendant)
        if categorized_responses.get("physical_appearance"):
            response_sections.append("PHYSICAL APPEARANCE INDICATORS (relevant for Ascendant):")
            for idx, resp in enumerate(categorized_responses["physical_appearance"]):
                question = resp.get("question", "")
                answer = resp.get("answer", "")
                response_sections.append(f"Q{idx+1}: {question}\nA{idx+1}: {answer}")
            response_sections.append("")

        # Personality traits (for Ascendant and Moon)
        if categorized_responses.get("personality"):
            response_sections.append("PERSONALITY TRAITS (relevant for Ascendant and Moon):")
            for idx, resp in enumerate(categorized_responses["personality"]):
                question = resp.get("question", "")
                answer = resp.get("answer", "")
                response_sections.append(f"Q{idx+1}: {question}\nA{idx+1}: {answer}")
            response_sections.append("")

        # Life events (for transits and progressions)
        if categorized_responses.get("life_events"):
            response_sections.append("LIFE EVENTS (relevant for transits and progressions):")
            for idx, resp in enumerate(categorized_responses["life_events"]):
                question = resp.get("question", "")
                answer = resp.get("answer", "")
                response_sections.append(f"Q{idx+1}: {question}\nA{idx+1}: {answer}")
            response_sections.append("")

        # Career and work (for MC/10th house)
        if categorized_responses.get("career"):
            response_sections.append("CAREER AND WORK (relevant for MC/10th house):")
            for idx, resp in enumerate(categorized_responses["career"]):
                question = resp.get("question", "")
                answer = resp.get("answer", "")
                response_sections.append(f"Q{idx+1}: {question}\nA{idx+1}: {answer}")
            response_sections.append("")

        # Relationships (for Venus, 7th house)
        if categorized_responses.get("relationships"):
            response_sections.append("RELATIONSHIPS (relevant for Venus, 7th house):")
            for idx, resp in enumerate(categorized_responses["relationships"]):
                question = resp.get("question", "")
                answer = resp.get("answer", "")
                response_sections.append(f"Q{idx+1}: {question}\nA{idx+1}: {answer}")
            response_sections.append("")

        # Early life (for Moon, 4th house)
        if categorized_responses.get("early_life"):
            response_sections.append("EARLY LIFE (relevant for Moon, 4th house):")
            for idx, resp in enumerate(categorized_responses["early_life"]):
                question = resp.get("question", "")
                answer = resp.get("answer", "")
                response_sections.append(f"Q{idx+1}: {question}\nA{idx+1}: {answer}")
            response_sections.append("")

        # Other responses
        if categorized_responses.get("other"):
            response_sections.append("OTHER RESPONSES:")
            for idx, resp in enumerate(categorized_responses["other"]):
                question = resp.get("question", "")
                answer = resp.get("answer", "")
                response_sections.append(f"Q{idx+1}: {question}\nA{idx+1}: {answer}")
            response_sections.append("")

        # Combine all sections
        response_text = "\n".join(response_sections)

        # Compile extracted birth time indicators with confidence scores
        indicators_text = ""
        ascendant_candidates = {}
        moon_sign_candidates = {}
        time_range_candidates = []

        if birth_time_indicators:
            indicators_text += "BIRTH TIME INDICATORS ANALYSIS:\n"

            for idx, indicator in enumerate(birth_time_indicators):
                indicator_data = indicator.get("indicators", {})
                question = indicator.get("question", "")
                answer = indicator.get("answer", "")

                # Track potential ascendants with confidence
                if "potential_ascendants" in indicator_data and "potential_ascendant_confidence" in indicator_data:
                    for sign in indicator_data["potential_ascendants"]:
                        if sign not in ascendant_candidates:
                            ascendant_candidates[sign] = 0
                        ascendant_candidates[sign] += indicator_data["potential_ascendant_confidence"]

                # Track Moon influences
                if "personality_planet_influences" in indicator_data and "Moon" in indicator_data["personality_planet_influences"]:
                    moon_idx = indicator_data["personality_planet_influences"].index("Moon")
                    if "personality_ascendant_indicators" in indicator_data and len(indicator_data["personality_ascendant_indicators"]) > moon_idx:
                        moon_sign = indicator_data["personality_ascendant_indicators"][moon_idx]
                        if moon_sign not in moon_sign_candidates:
                            moon_sign_candidates[moon_sign] = 0
                        moon_sign_candidates[moon_sign] += indicator_data["personality_planet_confidence"]

                # Track time ranges
                if "time_range" in indicator_data:
                    time_range_candidates.append(indicator_data["time_range"])
                elif "normalized_time" in indicator_data:
                    hour = int(indicator_data["normalized_time"].split(":")[0])
                    # Create a 1-hour window
                    time_range_candidates.append(f"{hour:02d}:00-{(hour+1)%24:02d}:00")

                # Format all indicator data for the prompt
                indicators_text += f"Indicator {idx+1} (from question about {question.strip()[:30]}...):\n"
                for key, value in indicator_data.items():
                    indicators_text += f"  {key}: {value}\n"
                indicators_text += f"  Source answer: {answer}\n\n"

            # Summarize ascendant candidates
            if ascendant_candidates:
                sorted_ascendants = sorted(ascendant_candidates.items(), key=lambda x: x[1], reverse=True)
                indicators_text += "ASCENDANT CANDIDATES SUMMARY:\n"
                for sign, score in sorted_ascendants[:3]:
                    indicators_text += f"  {sign}: confidence score {score:.1f}\n"
                indicators_text += "\n"

            # Summarize Moon sign candidates
            if moon_sign_candidates:
                sorted_moon = sorted(moon_sign_candidates.items(), key=lambda x: x[1], reverse=True)
                indicators_text += "MOON SIGN CANDIDATES SUMMARY:\n"
                for sign, score in sorted_moon[:3]:
                    indicators_text += f"  {sign}: confidence score {score:.1f}\n"
                indicators_text += "\n"

            # Summarize time ranges
            if time_range_candidates:
                indicators_text += "TIME RANGE CANDIDATES:\n"
                for time_range in time_range_candidates:
                    indicators_text += f"  {time_range}\n"
                indicators_text += "\n"

        # Format birth details
        birth_date = birth_details.get("birth_date", "")
        birth_time = birth_details.get("birth_time", "Unknown")
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        timezone = birth_details.get("timezone", "UTC")

        # Create system message with comprehensive astrological knowledge base
        system_message = """
        You are an expert Vedic astrologer specialized in birth time rectification with deep knowledge of:

        1. Ascendant determination through physical appearance and personality traits:
           - Aries rising: Athletic build, prominent forehead, direct manner, pioneering attitude
           - Taurus rising: Solid build, strong neck, patient demeanor, artistic sensibilities
           - Gemini rising: Slender build, expressive hands, adaptable personality, communicative
           - Cancer rising: Rounded face, nurturing presence, emotional sensitivity, family-oriented
           - Leo rising: Strong posture, abundant hair, confident presence, creative expression
           - Virgo rising: Neat appearance, analytical expression, detail-oriented, service-minded
           - Libra rising: Balanced features, diplomatic manner, artistic sensibility, relationship-focused
           - Scorpio rising: Penetrating gaze, intense presence, passionate nature, transformative
           - Sagittarius rising: Athletic physique, optimistic expression, philosophical outlook, freedom-loving
           - Capricorn rising: Dignified bearing, mature demeanor, ambitious nature, disciplined
           - Aquarius rising: Distinctive appearance, innovative thinking, humanitarian values, independent
           - Pisces rising: Dreamy eyes, gentle demeanor, intuitive nature, compassionate

        2. House systems and their significance:
           - 1st house: Self-image, physical body, appearance, approach to life
           - 4th house: Home, family, mother, emotional foundations
           - 7th house: Partnerships, marriage, significant relationships, contracts
           - 10th house: Career, public reputation, authority, father figure, life direction

        3. Planetary dignities and their impact on chart interpretation
        4. Transit timing and astrological event correlation
        5. Dasha systems and timing of life events
        6. Ashtakavarga and strength determination of houses and planets

        Using all this knowledge, analyze the responses to determine the most likely birth time.
        Integrate both traditional astrological wisdom and modern timing techniques in your analysis.
        """

        # Create user message with enhanced astrological request
        user_message = f"""
        BIRTH DETAILS:
        Date: {birth_date}
        Current registered time: {birth_time}
        Coordinates: {latitude}, {longitude}
        Timezone: {timezone}

        QUESTIONNAIRE RESPONSES (CATEGORIZED BY ASTROLOGICAL RELEVANCE):
        {response_text}

        {indicators_text}

        Based on this information, perform a comprehensive astrological analysis to determine the most accurate birth time.
        Focus on these key astrological factors:

        1. ASCENDANT DETERMINATION:
           - Analyze physical descriptions for likely Ascendant sign
           - Evaluate personality traits that correlate with Ascendant/1st house placements
           - Consider critical degrees that may amplify Ascendant influence

        2. ANGULAR HOUSE ANALYSIS:
           - Determine likely placements in the 1st, 4th, 7th, and 10th houses
           - Evaluate influence of house rulers on personality and life events
           - Identify potential Midheaven sign from career information

        3. PLANETARY INFLUENCE ASSESSMENT:
           - Identify dominant planets from personality traits and life experiences
           - Evaluate aspects between personal planets that explain relationship patterns
           - Determine Moon sign influence on emotional patterns

        4. TRANSIT CORRELATION:
           - Match significant life events with likely transit patterns
           - Identify recurring planetary cycles that correspond to life changes
           - Evaluate Saturn, Jupiter and outer planet transits to angular houses

        5. DASHA/PROGRESSION ANALYSIS:
           - Relate major life transitions to potential dasha periods
           - Correlate life themes with major planetary periods

        Return your analysis as a comprehensive JSON object with the following structure:
        {
          "birth_time_range": {
            "start": "HH:MM",
            "end": "HH:MM",
            "most_likely_time": "HH:MM"
          },
          "time_adjustment": {
            "minutes": integer (positive or negative),
            "direction": "earlier" or "later",
            "explanation": "detailed astrological reasoning"
          },
          "confidence": integer (0-100),
          "ascendant": {
            "sign": "sign name",
            "degree": integer,
            "confidence": integer (0-100),
            "supporting_traits": ["trait1", "trait2", ...]
          },
          "moon_sign": {
            "sign": "sign name",
            "house": integer,
            "confidence": integer (0-100)
          },
          "dominant_planets": [
            {"planet": "name", "sign": "sign", "house": integer, "significance": "explanation"}
          ],
          "key_factors": [
            {"factor": "factor name", "explanation": "explanation", "confidence": integer}
          ],
          "house_analysis": {
            "angular_houses": [
              {"house": integer, "planets": ["names"], "significance": "explanation"}
            ],
            "significant_placements": [
              {"planet": "name", "house": integer, "significance": "explanation"}
            ]
          },
          "astrological_insights": {
            "personality": ["detailed insights connecting traits to planetary positions"],
            "life_path": ["insights about major life themes and directions"],
            "relationships": ["insights about relationship patterns and planetary influences"],
            "career": ["insights about career path and MC influences"]
          }
        }
        """

        # Call OpenAI API with enhanced parameters
        response = await openai_service.generate_completion(
            prompt={
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ]
            },
            task_type="birth_time_rectification",
            max_tokens=3000,
            temperature=0.2  # Lower temperature for more consistent, analytical responses
        )

        # Extract and parse response
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")

        try:
            # Parse the JSON response
            analysis = json.loads(content)

            # Enhance analysis with additional birth chart data if available
            if "birth_date" in birth_details and "latitude" in birth_details and "longitude" in birth_details:
                try:
                    # Get most likely birth time for chart calculation
                    most_likely_time = analysis.get("birth_time_range", {}).get("most_likely_time")
                    if most_likely_time:
                        # Parse birth date and time
                        birth_date_str = birth_details["birth_date"]

                        if isinstance(birth_date_str, str):
                            # Attempt to handle various date formats
                            try:
                                if "T" in birth_date_str:  # ISO format with time
                                    birth_date_obj = datetime.fromisoformat(birth_date_str.split("T")[0])
                                else:
                                    birth_date_obj = datetime.strptime(birth_date_str, "%Y-%m-%d")
                            except ValueError:
                                # Try alternate format
                                try:
                                    birth_date_obj = datetime.strptime(birth_date_str, "%Y/%m/%d")
                                except ValueError:
                                    # Fall back to date object if it's already one
                                    birth_date_obj = birth_date_str
                        else:
                            # Assume it's already a datetime or date object
                            birth_date_obj = birth_date_str

                        # Parse time
                        time_parts = most_likely_time.split(":")
                        hour = int(time_parts[0])
                        minute = int(time_parts[1]) if len(time_parts) > 1 else 0

                        # Create full datetime for chart calculation
                        if isinstance(birth_date_obj, datetime):
                            rectified_dt = birth_date_obj.replace(hour=hour, minute=minute)
                        else:
                            # If it's a date object, convert to datetime
                            try:
                                from datetime import date
                                if isinstance(birth_date_obj, date):
                                    rectified_dt = datetime.combine(birth_date_obj, datetime.min.time()).replace(hour=hour, minute=minute)
                                else:
                                    # Fall back to string parsing
                                    rectified_dt = datetime.strptime(f"{birth_date_str} {most_likely_time}", "%Y-%m-%d %H:%M")
                            except (ValueError, TypeError):
                                logger.warning(f"Could not create datetime from {birth_date_str} and {most_likely_time}")
                                rectified_dt = None

                        if rectified_dt:
                            # Calculate chart using MinimalChart
                            try:
                                from ai_service.core.rectification.utils.ephemeris import MinimalChart
                                chart = MinimalChart(
                                    rectified_dt,
                                    birth_details["latitude"],
                                    birth_details["longitude"]
                                )

                                # Extract chart data
                                chart_data = chart.to_dict()

                                # Add chart data to analysis for enhanced insights
                                if "astrological_charts" not in analysis:
                                    analysis["astrological_charts"] = {}

                                analysis["astrological_charts"]["calculated_chart"] = {
                                    "ascendant": chart_data.get("angles", {}).get("asc", {}),
                                    "midheaven": chart_data.get("angles", {}).get("mc", {}),
                                    "planets": {
                                        planet: {
                                            "sign": data.get("sign"),
                                            "house": data.get("house"),
                                            "retrograde": data.get("retrograde", False)
                                        } for planet, data in chart_data.get("planets", {}).items()
                                    },
                                    "aspects": {
                                        aspect_type: len(aspects) for aspect_type, aspects
                                        in chart_data.get("aspects", {}).items()
                                    }
                                }
                            except Exception as chart_err:
                                logger.warning(f"Error calculating chart: {chart_err}")

                except Exception as chart_analysis_error:
                    logger.warning(f"Error enhancing analysis with chart data: {chart_analysis_error}")

            # Extract astrological factors for further processing
            key_astrological_factors = self._extract_key_astrological_factors(
                responses,
                birth_details
            )

            # Add these to the analysis
            if key_astrological_factors and "key_factors" not in analysis:
                analysis["key_factors"] = key_astrological_factors

            # Ensure birth time range is present
            if "birth_time_range" not in analysis:
                analysis["birth_time_range"] = self._determine_birth_time_range(
                    {},  # No specific indicators from AI
                    analysis,
                    birth_details
                )

            # Ensure time adjustment is present
            if "time_adjustment" not in analysis:
                analysis["time_adjustment"] = self._calculate_time_adjustment(
                    {},  # No specific indicators from AI
                    analysis
                )

            # Ensure confidence is present
            if "confidence" not in analysis:
                analysis["confidence"] = self._calculate_rectification_confidence(
                    responses,
                    {}  # No specific indicators from AI
                )

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Error parsing OpenAI response: {e}")
            logger.error(f"Response content: {content[:500]}...")  # Log first 500 chars

            # Try to extract usable information from the text
            try:
                # Extract birth time range
                birth_time_range = {}
                time_range_match = re.search(r'birth\s+time\s+range.*?(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})', content, re.IGNORECASE | re.DOTALL)
                if time_range_match:
                    birth_time_range["start"] = time_range_match.group(1)
                    birth_time_range["end"] = time_range_match.group(2)

                # Extract most likely time
                likely_time_match = re.search(r'most\s+likely\s+time.*?(\d{1,2}:\d{2})', content, re.IGNORECASE | re.DOTALL)
                if likely_time_match:
                    birth_time_range["most_likely_time"] = likely_time_match.group(1)

                # Extract confidence
                confidence = 65  # Default moderate confidence
                confidence_match = re.search(r'confidence.*?(\d{1,3})', content, re.IGNORECASE | re.DOTALL)
                if confidence_match:
                    confidence = int(confidence_match.group(1))

                # Extract ascendant
                ascendant = {}
                ascendant_match = re.search(r'ascendant.*?(Aries|Taurus|Gemini|Cancer|Leo|Virgo|Libra|Scorpio|Sagittarius|Capricorn|Aquarius|Pisces)',
                                           content, re.IGNORECASE | re.DOTALL)
                if ascendant_match:
                    ascendant["sign"] = ascendant_match.group(1)

                # Create partial analysis
                partial_analysis = {
                    "birth_time_range": birth_time_range,
                    "confidence": confidence,
                    "ascendant": ascendant,
                    "parsing_error": "Complete JSON parsing failed, extracted partial information",
                    "time_adjustment": self._calculate_time_adjustment({}, {"birth_time_range": birth_time_range})
                }

                # Add fallback data for missing sections
                if not birth_time_range:
                    partial_analysis["birth_time_range"] = self._determine_birth_time_range(
                        {},
                        partial_analysis,
                        birth_details
                    )

                logger.info("Created partial analysis from text response")
                return partial_analysis

            except Exception as extract_error:
                logger.error(f"Error extracting partial data: {extract_error}")
                # Fall back to basic analysis
                return self._fallback_comprehensive_analysis(responses, birth_details, birth_time_indicators)

        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return self._fallback_comprehensive_analysis(responses, birth_details, birth_time_indicators)

    except Exception as e:
        logger.error(f"Error in _perform_comprehensive_analysis: {e}")
        return self._fallback_comprehensive_analysis(responses, birth_details, birth_time_indicators)

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
