"""
Answer analysis module for the questionnaire service.

This module contains functions for analyzing and processing answers to questionnaire questions.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# logger initialization
logger = logging.getLogger(__name__)

from ai_service.api.services.openai.service import OpenAIService

async def submit_answer(
    self,
    session_id: str,
    question_id: str,
    answer: Any
) -> Dict[str, Any]:
    """
    Submit an answer to a question and get a response.

    Args:
        session_id: Session ID for the questionnaire
        question_id: ID of the question being answered
        answer: The answer provided

    Returns:
        Dictionary with the result of the submission
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

        # Get questionnaire data from session
        questionnaire_data = session.get("questionnaire", {})

        # Get previous answers
        previous_answers = questionnaire_data.get("answers", [])

        # Get current question
        current_question = questionnaire_data.get("current_question", {})
        questions = questionnaire_data.get("questions", [])

        # Find the question by ID
        question = None
        for q in questions:
            if q.get("id") == question_id:
                question = q
                break

        # If question not found, use current question
        if not question and current_question.get("id") == question_id:
            question = current_question

        # If still no question found, return error
        if not question:
            return {
                "status": "error",
                "message": f"Question with ID {question_id} not found"
            }

        # Format the answer record
        answer_record = {
            "question_id": question_id,
            "question": question,
            "answer": answer,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Check for contradictions with previous answers
        contradictions = await self._check_for_contradictions(session_id, question.get("text", ""), answer)

        if contradictions:
            # Add contradiction flag to answer record
            answer_record["contradicts"] = contradictions

            # Return the contradiction info
            return {
                "status": "contradiction",
                "message": "Your answer contradicts previous answers",
                "contradictions": contradictions,
                "previous_answers": previous_answers
            }

        # If birth details are available, perform astrological analysis
        birth_details = session.get("birth_details", {})
        if birth_details and all(key in birth_details for key in ["birth_date", "latitude", "longitude"]):
            try:
                analysis = await self._perform_astrological_analysis(
                    question.get("text", ""),
                    answer,
                    birth_details.get("birth_date", ""),
                    birth_details.get("birth_time", "12:00"),  # Use noon as default if no time
                    birth_details.get("latitude", 0),
                    birth_details.get("longitude", 0),
                    birth_details.get("timezone", "UTC")
                )

                if analysis:
                    # Add analysis to answer record
                    answer_record["analysis"] = analysis

                    # Extract birth time indicators if available
                    time_indicators = await self._extract_birth_time_indicators(question.get("text", ""), answer)
                    if time_indicators:
                        answer_record["time_indicators"] = time_indicators
            except Exception as e:
                logger.error(f"Error performing astrological analysis: {e}")

        # Add the answer to the list
        previous_answers.append(answer_record)

        # Update session data
        questionnaire_data["answers"] = previous_answers
        session["questionnaire"] = questionnaire_data

        # Save session
        await session_store.update_session(session_id, session)

        # Generate the next question
        next_question_data = await self.generate_next_question(birth_details, previous_answers)

        # Update session with next question
        questionnaire_data["current_question"] = next_question_data.get("question")
        questionnaire_data["questions"] = questions + [next_question_data.get("question")] if next_question_data.get("question") else questions
        session["questionnaire"] = questionnaire_data

        # Save session again with the next question
        await session_store.update_session(session_id, session)

        # Prepare the response
        response = {
            "status": "success",
            "message": "Answer submitted successfully",
            "next": next_question_data
        }

        # If we have time indicators, include them
        if "time_indicators" in answer_record:
            response["time_indicators"] = answer_record["time_indicators"]

        return response

    except Exception as e:
        logger.error(f"Error in submit_answer: {e}")
        return {
            "status": "error",
            "message": f"Failed to submit answer: {str(e)}"
        }

async def _check_for_contradictions(
    self,
    session_id: str,
    question: str,
    answer: Any
) -> List[Dict[str, Any]]:
    """
    Check for contradictions between the current answer and previous answers.

    Args:
        session_id: Session ID
        question: Current question text
        answer: Current answer

    Returns:
        List of contradiction details, or empty list if no contradictions
    """
    try:
        # Get session store
        session_store = self.session_store
        if not session_store:
            from ai_service.api.services.session_service import get_session_store
            session_store = get_session_store()

        if not session_store:
            return []

        # Get session data
        session = await session_store.get_session(session_id)
        if not session:
            return []

        # Get previous answers
        questionnaire_data = session.get("questionnaire", {})
        previous_answers = questionnaire_data.get("answers", [])

        if not previous_answers:
            return []

        # List to store contradictions
        contradictions = []

        # Convert current answer to string for comparison
        current_answer_str = str(answer)

        # Check each previous answer for potential contradictions
        for prev in previous_answers:
            prev_question = prev.get("question", {})
            prev_question_text = prev_question.get("text", "")
            prev_answer = prev.get("answer")

            # Skip if previous answer is None
            if prev_answer is None:
                continue

            # Convert previous answer to string
            prev_answer_str = str(prev_answer)

            # Check for contradiction between questions
            contradiction = self._detect_contradiction(
                prev_question_text,
                prev_answer_str,
                question,
                current_answer_str
            )

            if contradiction:
                contradictions.append({
                    "previous_question": prev_question_text,
                    "previous_answer": prev_answer_str,
                    "current_question": question,
                    "current_answer": current_answer_str,
                    "contradiction_details": contradiction
                })

        return contradictions

    except Exception as e:
        logger.error(f"Error checking for contradictions: {e}")
        return []

def _detect_contradiction(
    self,
    question1: str,
    answer1: str,
    question2: str,
    answer2: str
) -> Optional[Dict[str, Any]]:
    """
    Detect contradiction between two question-answer pairs.

    Args:
        question1: First question text
        answer1: First answer text
        question2: Second question text
        answer2: Second answer text

    Returns:
        Dictionary with contradiction details if found, None otherwise
    """
    # Skip if questions are identical (same question being answered twice)
    if question1 == question2:
        return None

    # Calculate similarity between questions
    question_similarity = self._calculate_similarity(question1, question2)

    # If questions are not similar, skip extensive checking
    if question_similarity < 0.3:
        return None
        

    # Extract key patterns from questions and answers

    # Time of day patterns
    time_of_day_pattern = r'(morning|afternoon|evening|night|dawn|dusk)'
    time1 = re.search(time_of_day_pattern, answer1.lower())
    time2 = re.search(time_of_day_pattern, answer2.lower())

    if time1 and time2 and time1.group(0) != time2.group(0):
        # Check if these are contradictory times
        contradictory_times = {
            "morning": ["night", "evening"],
            "afternoon": ["night", "dawn"],
            "evening": ["morning", "dawn"],
            "night": ["morning", "afternoon"],
            "dawn": ["evening", "night"],
            "dusk": ["morning", "dawn"]
        }

        time1_text = time1.group(0)
        time2_text = time2.group(0)

        if time2_text in contradictory_times.get(time1_text, []):
            return {
                "type": "time_of_day",
                "details": f"Previously mentioned {time1_text}, now saying {time2_text}"
            }

    # Yes/No contradictions
    yes_pattern = r'\b(yes|yeah|correct|right|true|agree|positive)\b'
    no_pattern = r'\b(no|nope|not|never|disagree|negative|false)\b'

    yes1 = re.search(yes_pattern, answer1.lower()) is not None
    no1 = re.search(no_pattern, answer1.lower()) is not None
    yes2 = re.search(yes_pattern, answer2.lower()) is not None
    no2 = re.search(no_pattern, answer2.lower()) is not None

    if (yes1 and no2) or (no1 and yes2):
        # If both questions are similar and answers are yes/no contradictions
        if question_similarity > 0.7:
            return {
                "type": "yes_no",
                "details": "Opposite answers to similar questions"
            }

    # Age or date contradictions
    age_pattern = r'\b(\d+)\s*(?:years|year|yrs|yr)\b'
    age1 = re.search(age_pattern, answer1.lower())
    age2 = re.search(age_pattern, answer2.lower())

    if age1 and age2 and abs(int(age1.group(1)) - int(age2.group(1))) > 2:
        # If significant age difference mentioned
        return {
            "type": "age",
            "details": f"Previously mentioned age {age1.group(1)}, now saying {age2.group(1)}"
        }

    # Simple negation contradictions (only for highly similar questions)
    if question_similarity > 0.8:
        # If one answer contains the negation of the other
        if "not " in answer1.lower() and answer1.lower().replace("not ", "") in answer2.lower():
            return {
                "type": "negation",
                "details": "Direct contradiction in answers"
            }

        if "not " in answer2.lower() and answer2.lower().replace("not ", "") in answer1.lower():
            return {
                "type": "negation",
                "details": "Direct contradiction in answers"
            }

    # No contradiction detected
    return None

def _calculate_similarity(self, text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts using a simple approach.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score between 0 and 1
    """
    # Convert to lowercase
    text1 = text1.lower()
    text2 = text2.lower()

    # Tokenize (simple split by spaces)
    tokens1 = set(text1.split())
    tokens2 = set(text2.split())

    # Calculate Jaccard similarity
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)

    if not union:
        return 0.0

    return len(intersection) / len(union)

def _extract_key_insights(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key insights from astrological analysis.

    Args:
        analysis: Dictionary with astrological analysis

    Returns:
        Dictionary with key insights
    """
    insights = {}

    # Extract house insights
    houses = analysis.get("houses", {})
    for house_num, house_data in houses.items():
        if house_data.get("significant", False):
            insights[f"house_{house_num}"] = {
                "planets": house_data.get("planets", []),
                "significance": house_data.get("significance", "medium"),
                "keywords": house_data.get("keywords", [])
            }

    # Extract planet insights
    planets = analysis.get("planets", {})
    for planet, planet_data in planets.items():
        if planet_data.get("significant", False):
            insights[f"planet_{planet}"] = {
                "house": planet_data.get("house"),
                "sign": planet_data.get("sign"),
                "significance": planet_data.get("significance", "medium"),
                "keywords": planet_data.get("keywords", [])
            }

    # Extract ascendant insights
    ascendant = analysis.get("ascendant", {})
    if ascendant:
        insights["ascendant"] = {
            "sign": ascendant.get("sign"),
            "degree": ascendant.get("degree"),
            "significance": ascendant.get("significance", "high"),
            "keywords": ascendant.get("keywords", [])
        }

    # Extract time indicators
    time_indicators = analysis.get("time_indicators", {})
    if time_indicators:
        insights["time_indicators"] = time_indicators

    return insights

async def _perform_astrological_analysis(
    self,
    question: str,
    answer: Any,
    birth_date: str,
    birth_time: str,
    latitude: float,
    longitude: float,
    timezone: str = "UTC"
) -> Dict[str, Any]:
    """
    Perform astrological analysis on an answer.

    Args:
        question: Question text
        answer: The answer
        birth_date: Birth date string
        birth_time: Birth time string
        latitude: Birth latitude
        longitude: Birth longitude
        timezone: Birth timezone

    Returns:
        Dictionary with astrological analysis
    """
    try:
        # Try to get OpenAI service
        openai_service = self.openai_service
        if not openai_service:
            from ai_service.api.services.openai import get_openai_service
            openai_service = get_openai_service()

        if not openai_service:
            logger.warning("OpenAI service not available for astrological analysis")
            return {}

        # Convert answer to string
        if not isinstance(answer, str):
            answer_text = str(answer)
        else:
            answer_text = answer

        # Calculate chart data
        chart_data = self._calculate_chart_data(
            birth_date,
            birth_time,
            latitude,
            longitude,
            timezone
        )

        # Create system message
        system_message = """
        You are an expert Vedic astrologer specialized in interpreting birth chart data.
        Your task is to analyze a person's answer in the context of their birth chart and
        determine what astrological factors might explain the described experiences or traits.

        Specifically focus on:
        1. Which houses in the chart relate to the answer
        2. Which planets might be influencing these life areas
        3. What the answer suggests about possible birth time and Ascendant
        4. Any indicators that would help refine birth time accuracy

        Provide a thorough astrological interpretation by connecting the person's experience
        to specific placements in their chart. If the answer contains information that could
        help rectify birth time, emphasize those indicators.
        """

        # Format chart data for prompt
        chart_text = self._format_chart_data_for_prompt(chart_data)

        # Create user message
        user_message = f"""
        BIRTH CHART DATA:
        {chart_text}

        QUESTION: {question}

        ANSWER: {answer_text}

        Based on this person's answer and birth chart data, provide an astrological analysis
        that explains how the chart correlates with their experience. Focus especially on
        any timing indicators that could help rectify birth time.

        Return your analysis as a JSON object with the following structure:
        {{
          "houses": {{
            "1": {{"significant": true/false, "planets": [], "significance": "high/medium/low", "keywords": []}},
            // other houses...
          }},
          "planets": {{
            "sun": {{"house": 1, "sign": "Aries", "significant": true/false, "significance": "high/medium/low", "keywords": []}},
            // other planets...
          }},
          "ascendant": {{"sign": "Gemini", "degree": 15, "significance": "high/medium/low", "keywords": []}},
          "time_indicators": {{
            "narrowed_range": "10:00-12:00",
            "possible_ascendants": ["Gemini", "Cancer"],
            "confidence": "high/medium/low",
            "reasoning": "explanation"
          }}
        }}
        """

        # Call OpenAI API
        response = await openai_service.generate_completion(
            prompt={
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ]
            },
            task_type="astrological_analysis",
            max_tokens=1500,
            temperature=0.7
        )

        # Parse response
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        result = self._parse_text_response(content)

        # Enhance analysis with chart data
        enhanced_analysis = self._enhance_astrological_analysis(
            result,
            question,
            answer_text,
            birth_date,
            birth_time,
            latitude,
            longitude,
            chart_data
        )

        # Assess time precision
        precision_assessment = self._assess_time_precision(enhanced_analysis)
        if precision_assessment:
            enhanced_analysis["time_precision"] = precision_assessment

        return enhanced_analysis

    except Exception as e:
        logger.error(f"Error performing astrological analysis: {e}")
        return {}
