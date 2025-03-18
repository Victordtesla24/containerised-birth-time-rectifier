"""
Dynamic Questionnaire Service

This service generates personalized questions for birth time rectification
based on previous answers and birth details.
"""

import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
import random

from ai_service.api.services.openai import OpenAIService

# Set up logging
logger = logging.getLogger(__name__)

class DynamicQuestionnaireService:
    """
    Service for generating dynamic, personalized questionnaires
    for birth time rectification.
    """

    def __init__(self, openai_service: Optional[Any] = None):
        """
        Initialize the questionnaire service with OpenAI service.
        """
        self.openai_service = openai_service
        self.max_questions = 15
        self.question_templates = self._load_question_templates()
        # Track questions across sessions for better duplicate detection
        self.global_question_cache = {}  # session_id -> list of questions
        self.question_similarity_threshold = 0.60  # Reduced threshold for semantic similarity (was 0.65)

        # Stop words to filter out before similarity comparison
        self.stop_words = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
                          "about", "have", "has", "had", "you", "your", "is", "are", "were", "was",
                          "be", "been", "being", "do", "does", "did", "can", "could", "would", "should",
                          "will", "shall", "may", "might", "must", "of", "by", "any", "some"}

        # Base question categories
        self.question_categories = [
            "life_events",
            "physical_traits",
            "personality_traits",
            "career",
            "relationships",
            "health",
            "education",
            "travel",
            "spiritual_experiences"
        ]

        # Threshold for confidence score
        self.confidence_threshold = 0.8

    async def generate_next_question(self, birth_details: Dict[str, Any], previous_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the next question based on birth details and previous answers.
        """
        logger.info("Generating next question")

        try:
            # Extract birth details
            birth_date = birth_details.get("birthDate", "")
            birth_time = birth_details.get("birthTime", "")
            birth_place = birth_details.get("birthPlace", "")
            latitude = birth_details.get("latitude")
            longitude = birth_details.get("longitude")

            # Validate essential input
            if not birth_date or not birth_time:
                return {
                    "error": "Missing birth details",
                    "message": "Birth date and time are required to generate questions",
                    "status_code": 400
                }

            # Initialize variables
            chart_data = None
            asked_questions = set()
            asked_question_ids = set()
            asked_question_topics = set()
            answer_count = 0
            answer_quality = 0
            current_confidence = 20.0  # Default starting confidence

            # Process previous answers if available
            if previous_answers and isinstance(previous_answers, dict):
                # Extract previously asked questions
                if "responses" in previous_answers:
                    for resp in previous_answers.get("responses", []):
                        if isinstance(resp, dict):
                            if "question" in resp:
                                asked_questions.add(resp["question"])
                            if "question_id" in resp:
                                asked_question_ids.add(resp["question_id"])
                            if "topic" in resp:
                                asked_question_topics.add(resp["topic"])

                            # Count answers and assess quality
                            if "answer" in resp and resp["answer"]:
                                answer_count += 1
                                if isinstance(resp.get("quality"), (int, float)):
                                    answer_quality += resp.get("quality", 0.5)

            # Get coordinates if needed
            if not latitude or not longitude:
                logger.info("Coordinates not provided, attempting to resolve from location")
                location = birth_place

                # Try different geocoding methods
                coords_found = False

                # Try to use geocoding service if available
                try:
                    from ai_service.utils.geocoding import get_coordinates
                    if location:
                        logger.info(f"Attempting to get coordinates for {location} using geocoding service")
                        coords = await get_coordinates(location)
                        if coords:
                            latitude = coords.get("latitude", 0)
                            longitude = coords.get("longitude", 0)
                            coords_found = True
                            logger.info(f"Found coordinates: lat={latitude}, lng={longitude}")
                except ImportError:
                    logger.warning("Geocoding service not available")

                # If coordinates not found, try chart service
                if not coords_found:
                    try:
                        from ai_service.api.services.chart import get_chart_service
                        chart_service = get_chart_service()

                        # Use the geocoding utility directly instead of chart service
                        from ai_service.utils.geocoding import get_coordinates
                        if location:
                            logger.info(f"Attempting to get coordinates for {location} using geocoding service")
                            coords = await get_coordinates(location)
                            if coords:
                                latitude = coords.get("latitude", 0)
                                longitude = coords.get("longitude", 0)
                                coords_found = True
                                logger.info(f"Found coordinates: lat={latitude}, lng={longitude}")
                    except ImportError:
                        logger.warning("Geocoding service not available")

                # Validate that we have coordinates
                if not coords_found or latitude is None or longitude is None:
                    return {
                        "error": "Could not resolve coordinates",
                        "message": "Please provide latitude and longitude for accurate chart calculation",
                        "status_code": 400
                    }

            # Generate chart data using AstroCalculator
            try:
                from ai_service.utils.astro_calculator import get_astro_calculator
                calculator = get_astro_calculator()

                logger.info(f"Calculating chart for {birth_date} {birth_time} at lat={latitude}, lng={longitude}")

                # Check if specific aspects or houses are requested
                include_aspects = True
                include_houses = True
                include_divisional_charts = False

                # Calculate the chart based on birth details
                chart_data = await calculator.calculate_chart(
                    birth_date=birth_date,
                    birth_time=birth_time,
                    latitude=latitude,
                    longitude=longitude,
                    include_aspects=include_aspects
                )

                # Verify we have the expected chart structure
                if chart_data and "planets" in chart_data:
                    # Calculate aspects
                    if include_aspects:
                        logger.info("Calculating aspects and houses")
                        chart_data["aspects"] = calculator._calculate_aspects(chart_data["planets"])

                    # Calculate house positions
                    if include_houses:
                        houses = calculator._calculate_houses(
                            calculator._get_julian_day(birth_date, birth_time),
                            latitude,
                            longitude,
                            "P"  # Placidus
                        )
                        chart_data["houses"] = houses

                # Verify chart data has all required components
                required_components = ["planets", "houses", "aspects", "ascendant"]
                missing_components = [comp for comp in required_components if comp not in chart_data]

                if missing_components:
                    logger.warning(f"Chart data is missing components: {missing_components}")
                    # Try to complete the missing components
                    for component in missing_components:
                        if component == "aspects" and "planets" in chart_data:
                            logger.info("Calculating missing aspects")
                            chart_data["aspects"] = await calculator.calculate_aspects(chart_data["planets"])
                        elif component == "houses" and "ascendant" in chart_data:
                            logger.info("Calculating missing houses")
                            chart_data["houses"] = await calculator.calculate_houses(
                                birth_date, birth_time, latitude, longitude
                            )

                    # Re-check for required components
                    missing_components = [comp for comp in required_components if comp not in chart_data]
                    if missing_components:
                        return {
                            "error": "Incomplete chart data",
                            "message": f"Cannot generate questions without complete chart data. Missing: {', '.join(missing_components)}",
                            "status_code": 500
                        }

                logger.info(f"Generated chart data with {len(chart_data.get('planets', []))} planets, "
                          f"{len(chart_data.get('houses', []))} houses, and "
                          f"{len(chart_data.get('aspects', []))} aspects")
            except ImportError:
                logger.warning("AstroCalculator not available, generating minimal chart data")
                chart_data = self._generate_minimal_chart_data(birth_details)
            except Exception as e:
                logger.error(f"Error generating chart data: {str(e)}")
                chart_data = self._generate_minimal_chart_data(birth_details)

            # Calculate confidence based on answer count and quality
            if answer_count > 0:
                # Base confidence from answer count (max 60%)
                count_confidence = min(answer_count * 10, 60)

                # Quality adjustment (if we have quality data)
                quality_adjustment = 0
                if answer_quality > 0:
                    # Adjust by up to ±15% based on answer quality
                    avg_quality = answer_quality / answer_count
                    quality_adjustment = (avg_quality - 0.5) * 30  # -15% to +15%

                current_confidence += count_confidence + quality_adjustment

                # Ensure confidence stays within reasonable bounds
                current_confidence = min(max(current_confidence, 30), 95)

            # Prepare additional context for the questionnaire engine
            context = {
                "chart_data": chart_data,
                "birth_details": birth_details,
                "previous_answers": previous_answers,
                "current_confidence": current_confidence,
                "asked_questions": asked_questions,
                "asked_question_ids": asked_question_ids,
                "asked_question_topics": asked_question_topics
            }

            # Get the next question using the enhanced questionnaire engine with full context
            try:
                from ai_service.utils.questionnaire_engine import QuestionnaireEngine
                questionnaire_engine = QuestionnaireEngine()

                next_question = await questionnaire_engine.get_next_question(
                    chart_data=chart_data,
                    birth_details=birth_details,
                    previous_answers=previous_answers,
                    current_confidence=current_confidence,
                    context=context  # Pass the full context for better question generation
                )
            except ImportError:
                logger.error("Could not import QuestionnaireEngine module")
                return {
                    "error": "Missing questionnaire engine module",
                    "message": "Required module for question generation is not available",
                    "status_code": 500
                }
            except Exception as e:
                logger.error(f"Error from questionnaire engine: {str(e)}")
                return {
                    "error": "Question generation failed",
                    "message": str(e),
                    "status_code": 500
                }

            # Enhanced duplicate detection with semantic similarity
            max_attempts = 7  # Increased for better chance of finding unique question
            attempt = 0

            while self._is_duplicate_question(next_question, asked_questions, asked_question_ids, asked_question_topics) and attempt < max_attempts:
                logger.error(f"Generated question is a duplicate, retrying. Attempt {attempt+1}/{max_attempts}")
                # Try again with explicit instruction to avoid previous questions
                try:
                    # In later attempts, add more explicit diversification cues
                    diversification_cues = [
                        "Generate a completely different question about a new topic.",
                        "Change the subject of the question entirely.",
                        "Focus on a different area of life or personality trait.",
                        "Ask about a different time period in the person's life.",
                        "Change the format of the question (e.g., yes/no to multiple choice)."
                    ]

                    # After a few attempts, use stronger diversification
                    diversification_cue = ""
                    if attempt >= 2:
                        diversification_cue = diversification_cues[min(attempt-2, len(diversification_cues)-1)]

                    next_question = await questionnaire_engine.get_next_question(
                        chart_data=chart_data,
                        birth_details=birth_details,
                        previous_answers=previous_answers,
                        current_confidence=current_confidence,
                        context={
                            **context,
                            "avoid_duplicates": True,
                            "attempt": attempt + 1,
                            "asked_questions_list": list(asked_questions),
                            "diversification_cue": diversification_cue
                        }
                    )

                    # After several attempts, try a completely different approach
                    if attempt >= 4:
                        # Force a change to question category or type
                        next_question["type"] = self._get_alternative_question_type(next_question.get("type", "yes_no"))

                        # If available, add a unique marker to ensure the question is different
                        if "text" in next_question:
                            next_question["text"] = f"{next_question['text']} [variant {attempt+1}]"

                    attempt += 1
                except Exception as e:
                    logger.error(f"Error generating non-duplicate question: {str(e)}")
                    return {
                        "error": "Failed to generate a unique question",
                        "message": str(e),
                        "status_code": 500
                    }

            if attempt >= max_attempts:
                logger.error("Failed to generate a unique question after multiple attempts")
                # Try one last approach - generate from templates instead of AI
                try:
                    logger.info("Attempting to generate a fallback question from templates")
                    template_questions = self._generate_template_questions(birth_details, previous_answers)
                    if template_questions and len(template_questions) > 0:
                        next_question = template_questions[0]
                        # Add a marker to make it unique
                        next_question["text"] = f"{next_question['text']} [fallback]"
                        # Check one more time if it's unique
                        if not self._is_duplicate_question(next_question, asked_questions, asked_question_ids, asked_question_topics):
                            logger.info("Successfully generated a unique fallback question")
                            return {
                                "next_question_url": f"/api/v1/questionnaire/{next_question.get('id', '')}/answer",
                                "next_question": next_question,
                                "confidence": current_confidence
                            }
                except Exception as fallback_err:
                    logger.error(f"Error generating fallback question: {str(fallback_err)}")

                # If all attempts fail, return error
                return {
                    "error": "Could not generate a unique question",
                    "message": "Please try again or continue with previous answers",
                    "current_confidence": current_confidence,
                    "status_code": 422
                }

            # Add metadata to the question
            question_url = f"/api/v1/questionnaire/{next_question.get('id', '')}/answer"

            # Return the complete next question data
            return {
                "next_question_url": question_url,
                "next_question": next_question,
                "confidence": current_confidence
            }

        except Exception as e:
            logger.error(f"Error generating next question: {str(e)}")
            return {
                "error": "Failed to generate next question",
                "message": str(e),
                "status_code": 500
            }

    async def generate_questions(self, birth_details: Dict[str, Any], previous_answers: Dict[str, Any], current_confidence: float) -> Dict[str, Any]:
        """
        Generate dynamic questions based on birth details and previous answers.

        Args:
            birth_details: Birth details including date, time, place, coordinates
            previous_answers: Previous answers to questions
            current_confidence: Current confidence score (0-100)

        Returns:
            Dictionary with questions, confidence score, and completion status
        """
        try:
            # Normalize confidence score to 0-1 range
            current_confidence = current_confidence / 100 if current_confidence > 1 else current_confidence

            # Check if we've reached the confidence threshold
            if current_confidence >= self.confidence_threshold:
                return {
                    "questions": [],
                    "confidence_score": current_confidence,
                    "is_complete": True,
                    "has_reached_threshold": True
                }

            # Check if we've reached the maximum number of questions
            if len(previous_answers) >= self.max_questions:
                return {
                    "questions": [],
                    "confidence_score": current_confidence,
                    "is_complete": True,
                    "has_reached_threshold": current_confidence >= self.confidence_threshold
                }

            # Check for contradictory answers
            contradictions = self._check_for_contradictions(previous_answers)

            # If contradictions found, generate clarifying questions
            if contradictions and len(contradictions) > 0:
                clarifying_questions = self._generate_clarifying_questions(contradictions)

                # Return clarifying questions with unchanged confidence
                return {
                    "questions": clarifying_questions,
                    "confidence_score": current_confidence,
                    "is_complete": False,
                    "has_reached_threshold": False,
                    "contradictions_found": True
                }

            # Try to use AI to generate personalized questions
            try:
                if self.openai_service:
                    # Generate questions using OpenAI
                    ai_questions = await self._generate_ai_questions(birth_details, previous_answers)

                    if ai_questions and len(ai_questions) > 0:
                        # Calculate new confidence score
                        new_confidence = self._calculate_confidence_score(current_confidence, previous_answers)

                        return {
                            "questions": ai_questions,
                            "confidence_score": new_confidence,
                            "is_complete": new_confidence >= self.confidence_threshold,
                            "has_reached_threshold": new_confidence >= self.confidence_threshold
                        }
            except Exception as e:
                logging.warning(f"Failed to generate AI questions: {str(e)}")

            # Fall back to template-based questions if AI fails
            template_questions = self._generate_template_questions(birth_details, previous_answers)

            # Calculate new confidence score
            new_confidence = self._calculate_confidence_score(current_confidence, previous_answers)

            return {
                "questions": template_questions,
                "confidence_score": new_confidence,
                "is_complete": new_confidence >= self.confidence_threshold,
                "has_reached_threshold": new_confidence >= self.confidence_threshold
            }

        except Exception as e:
            logging.error(f"Error generating questions: {str(e)}")
            # Return fallback questions in case of error
            return {
                "questions": self._get_fallback_questions(),
                "confidence_score": current_confidence,
                "is_complete": False,
                "has_reached_threshold": False,
                "error": str(e)
            }

    def _check_for_contradictions(self, previous_answers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check for contradictory answers in previous responses.

        Args:
            previous_answers: Dictionary of previous answers

        Returns:
            List of contradiction details
        """
        contradictions = []

        # Define contradiction rules
        contradiction_rules = [
            # Example: Introvert/Extrovert contradiction
            {
                "questions": ["personality_introvert", "personality_extrovert"],
                "contradictory_values": [
                    {"q1_value": "yes", "q2_value": "yes"},
                    {"q1_value": "strongly_agree", "q2_value": "strongly_agree"}
                ]
            },
            # Example: Career change timing contradiction
            {
                "questions": ["career_change_recent", "career_stable"],
                "contradictory_values": [
                    {"q1_value": "yes", "q2_value": "yes"}
                ]
            }
        ]

        # Check each contradiction rule
        for rule in contradiction_rules:
            q1, q2 = rule["questions"]

            # Skip if either question hasn't been answered
            if q1 not in previous_answers or q2 not in previous_answers:
                continue

            # Check for contradictory values
            for contradiction in rule["contradictory_values"]:
                q1_value = contradiction.get("q1_value", "")
                q2_value = contradiction.get("q2_value", "")
                if (previous_answers[q1] == q1_value and
                    previous_answers[q2] == q2_value):
                    contradictions.append({
                        "questions": [q1, q2],
                        "values": [previous_answers[q1], previous_answers[q2]]
                    })

        return contradictions

    def _generate_clarifying_questions(self, contradictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate clarifying questions for contradictory answers.

        Args:
            contradictions: List of contradiction details

        Returns:
            List of clarifying questions
        """
        clarifying_questions = []

        for i, contradiction in enumerate(contradictions):
            q1, q2 = contradiction["questions"]
            v1, v2 = contradiction["values"]

            # Generate a clarifying question
            question = {
                "id": f"clarify_{i}_{uuid.uuid4().hex[:8]}",
                "text": f"Earlier you indicated both '{q1}' and '{q2}', which seem contradictory. Which feels more accurate most of the time?",
                "type": "options",
                "options": [
                    f"Mostly {q1.replace('_', ' ')}",
                    f"Mostly {q2.replace('_', ' ')}",
                    "It varies significantly",
                    "Neither is accurate"
                ],
                "is_clarification": True,
                "related_questions": [q1, q2]
            }

            clarifying_questions.append(question)

        return clarifying_questions

    async def _generate_ai_questions(self, birth_details: Dict[str, Any], previous_answers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate questions using AI based on birth details and previous answers.

        Args:
            birth_details: Birth details
            previous_answers: Previous answers

        Returns:
            List of AI-generated questions
        """
        if not self.openai_service:
            logger.error("OpenAI service not available for question generation")
            return []

        try:
            # Get chart data for AI analysis
            chart_data = None
            if birth_details:
                try:
                    # Ensure we have complete chart data by using the astro calculator directly
                    try:
                        from ai_service.utils.astro_calculator import get_astro_calculator
                        calculator = get_astro_calculator()

                        chart_data = await calculator.calculate_chart(
                            birth_date=birth_details.get("birthDate", ""),
                            birth_time=birth_details.get("birthTime", ""),
                            latitude=birth_details.get("latitude", 0),
                            longitude=birth_details.get("longitude", 0),
                            include_aspects=True,
                            include_houses=True,
                            include_divisional_charts=True,
                            format_for_ai=True
                        )
                    except ImportError:
                        logger.error("Could not import astro_calculator module")
                        return []
                except Exception as e:
                    logger.error(f"Error getting chart data for AI question generation: {str(e)}")
                    # Don't proceed without chart data
                    return []

            if not chart_data:
                logger.error("No chart data available for AI question generation")
                return []

            # Prepare context for AI
            context = {
                "birth_details": birth_details,
                "previous_answers": previous_answers,
                "question_count": len(previous_answers.get("responses", [])),
                "remaining_questions": self.max_questions - len(previous_answers.get("responses", [])),
                "chart_data": chart_data  # Pass the complete chart data
            }

            # Call OpenAI service to generate questions
            response = await self.openai_service.generate_questions(context)

            # Process and format AI-generated questions
            questions = []

            for i, q in enumerate(response.get("questions", [])):
                question_id = q.get("id", f"ai_q_{i}_{uuid.uuid4().hex[:8]}")

                question = {
                    "id": question_id,
                    "text": q.get("text", ""),
                    "type": q.get("type", "boolean"),
                    "options": q.get("options", ["Yes", "No"]),
                    "relevance": q.get("relevance", "medium"),
                    "rationale": q.get("rationale", ""),  # Include rationale if provided
                    "astrological_factors": q.get("astrological_factors", [])  # Include relevant astrological factors
                }

                # Extract and store topics for better duplicate detection
                topics = set()
                self._extract_question_topics(question["text"], topics)
                if topics:
                    question["topics"] = list(topics)

                questions.append(question)

            return questions

        except Exception as e:
            logger.error(f"Error generating AI questions: {str(e)}")
            return []

    def _generate_template_questions(self, birth_details: Dict[str, Any], previous_answers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate questions from templates based on birth details and previous answers.

        Args:
            birth_details: Birth details
            previous_answers: Previous answers

        Returns:
            List of template-based questions
        """
        # Determine which categories to focus on
        used_categories = set()
        for answer_key in previous_answers.keys():
            for category in self.question_categories:
                if category in answer_key:
                    used_categories.add(category)

        # Prioritize unused categories
        available_categories = [c for c in self.question_categories if c not in used_categories]

        # If all categories used, pick random ones
        if not available_categories:
            available_categories = self.question_categories

        # Select categories to use for this batch
        selected_categories = random.sample(
            available_categories,
            min(3, len(available_categories))
        )

        # Generate questions from selected categories
        questions = []

        for category in selected_categories:
            # Get templates for this category
            templates = self.question_templates.get(category, [])

            if templates:
                # Select a random template
                template = random.choice(templates)

                # Generate a unique ID
                question_id = f"{category}_{uuid.uuid4().hex[:8]}"

                # Create question from template
                question = {
                    "id": question_id,
                    "text": template.get("text", ""),
                    "type": template.get("type", "boolean"),
                    "options": template.get("options", ["Yes", "No"]),
                    "relevance": template.get("relevance", "medium")
                }

                questions.append(question)

        return questions

    def _extract_question_topics(self, question_text: str, topic_set: set) -> None:
        """
        Extract topic keywords from a question using NLP-style analysis.

        This improved method uses more sophisticated pattern matching and
        contextual analysis to identify astrological topics in questions.

        Args:
            question_text: The question text to analyze
            topic_set: Set to add extracted topics to
        """
        if not question_text:
            return

        # Convert question to lowercase for case-insensitive matching
        question_lower = question_text.lower()

        # Define advanced pattern matching for topics with contextual awareness
        topic_patterns = {
            # Career patterns with context
            "career": [
                r"\b(career|job|profession|work|business|employment)\b",
                r"\b(promot(ed|ion)|hired|fired|resign(ed|ation)|interview)\b",
                r"\b(boss|colleague|coworker|workplace|office|company)\b"
            ],

            # Relationship patterns with context
            "relationships": [
                r"\b(relationship|marriage|partner|spouse|dating|romantic)\b",
                r"\b(love|affair|break(up|ing up)|divorce|wedding|engagement)\b",
                r"\b(met.*partner|significant other|husband|wife|boyfriend|girlfriend)\b"
            ],

            # Health patterns
            "health": [
                r"\b(health|illness|medical|disease|condition|physical)\b",
                r"\b(hospital|surgery|accident|injury|recovery|diagnosis)\b",
                r"\b(chronic|acute|symptoms|treatment|medication|therapy)\b"
            ],

            # Personality patterns
            "personality": [
                r"\b(personality|character|trait|temperament|nature)\b",
                r"\b(introvert|extrovert|sensitive|analytical|emotional|logical)\b",
                r"\b(how would.*describe (yourself|your personality)|tend to be)\b"
            ],

            # Education patterns
            "education": [
                r"\b(education|school|college|university|degree|study|academic)\b",
                r"\b(graduated|diploma|course|major|student|professor|teacher)\b",
                r"\b(learn|training|certification|class|lecture|exam|thesis)\b"
            ],

            # Travel patterns
            "travel": [
                r"\b(travel|journey|trip|abroad|foreign|country|move|relocate)\b",
                r"\b(vacation|holiday|destination|flight|overseas|international)\b",
                r"\b(visit|tourism|explorer|adventure|expedition|migration)\b"
            ],

            # Family patterns
            "family": [
                r"\b(family|parent|child|sibling|relative|mother|father)\b",
                r"\b(son|daughter|brother|sister|grandparent|aunt|uncle|cousin)\b",
                r"\b(born|birth|adoption|heritage|lineage|ancestry|descendant)\b"
            ],

            # Spirituality patterns
            "spirituality": [
                r"\b(spiritual|religion|belief|faith|meditation|practice)\b",
                r"\b(god|divine|sacred|holy|prayer|worship|ritual|ceremony)\b",
                r"\b(enlightenment|awakening|consciousness|soul|spirit|energy)\b"
            ],

            # Appearance patterns
            "appearance": [
                r"\b(appearance|look|physical|body|height|weight|feature)\b",
                r"\b(face|hair|eyes|skin|build|tall|short|thin|heavy)\b",
                r"\b(attractive|beauty|handsome|pretty|ugly|average)\b"
            ],

            # Finances patterns
            "finances": [
                r"\b(finance|money|wealth|investment|financial|income)\b",
                r"\b(savings|debt|loan|mortgage|budget|expense|spending)\b",
                r"\b(salary|wage|earn|bonus|inheritance|lottery|poverty)\b"
            ],

            # Birth time specific patterns
            "birth_time": [
                r"\b(birth.*time|time.*birth|born.*time|time.*born)\b",
                r"\b(morning|afternoon|evening|night|dawn|dusk|midnight|noon)\b",
                r"\b(hour|minute|clock|watch|early|late|exactly|approximately)\b"
            ],

            # Life events patterns
            "life_events": [
                r"\b(event|experience|milestone|turning point|significant|major)\b",
                r"\b(happen|occur|change|transform|shift|transition|phase)\b",
                r"\b(life.*changing|defining moment|critical|pivotal|landmark)\b"
            ],

            # Astrological house patterns
            "houses": [
                r"\b(house|cusp|angle|ascendant|midheaven|IC|descendant)\b",
                r"\b(1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th|11th|12th)\b",
                r"\b(angular|succedent|cadent|rising|setting|culminating)\b"
            ],

            # Planet patterns
            "planets": [
                r"\b(sun|moon|mercury|venus|mars|jupiter|saturn|uranus|neptune|pluto)\b",
                r"\b(luminary|benefic|malefic|retrograde|direct|station|transit)\b",
                r"\b(conjunction|opposition|square|trine|sextile|aspect)\b"
            ]
        }

        # Check each topic pattern set
        for topic, pattern_list in topic_patterns.items():
            for pattern in pattern_list:
                import re
                if re.search(pattern, question_lower):
                    topic_set.add(topic)
                    break  # Once found, move to next topic

        # Check for contextual combinations indicating specific time-sensitive topics
        if ("birth_time" in topic_set and any(t in topic_set for t in ["life_events", "personality"])) or \
           ("houses" in topic_set and any(t in topic_set for t in ["career", "relationships", "health"])):
            topic_set.add("birth_time_rectification")

        # Add weighting for birth time relevant topics
        if "ascendant" in question_lower or "rising sign" in question_lower:
            topic_set.add("ascendant_focused")
            topic_set.add("birth_time_critical")

        if "midheaven" in question_lower or "mc" in question_lower or "career direction" in question_lower:
            topic_set.add("midheaven_focused")
            topic_set.add("birth_time_critical")

    def _get_relevance_score(self, relevance: str) -> float:
        """
        Convert relevance string to a numerical score.

        Args:
            relevance: Relevance string ('high', 'medium', 'low')

        Returns:
            Relevance score between 0 and 1
        """
        relevance_mapping = {
            "very_high": 1.0,   # Critical astrological factors (ascendant, Moon position)
            "high": 0.85,       # Important factors (Sun position, angular houses)
            "medium": 0.65,     # Moderately important factors (non-angular houses, minor aspects)
            "low": 0.45,        # Less important factors (distant aspects, minor planets)
            "very_low": 0.25    # Minimal significance
        }

        return relevance_mapping.get(relevance.lower(), 0.65)  # Default to medium

    def _is_duplicate_question(self,
                              question: Dict[str, Any],
                              asked_questions: set,
                              asked_question_ids: set,
                              asked_question_topics: set) -> bool:
        """
        Enhanced duplicate question detection using semantic similarity.

        Args:
            question: The question to check
            asked_questions: Set of previously asked question texts
            asked_question_ids: Set of previously asked question IDs
            asked_question_topics: Set of previously asked question topics

        Returns:
            True if the question is a duplicate, False otherwise
        """
        # Log for debugging
        logger.info(f"Checking question for duplication: {question.get('text', '')[:50]}...")

        # Check ID duplication
        if question.get("id") in asked_question_ids:
            logger.error(f"Duplicate question ID detected: {question.get('id')}")
            return True

        # Check exact text duplication
        question_text = question.get("text", "").strip().lower()
        if not question_text:
            logger.error("Empty question text detected")
            return True  # Empty questions are considered duplicates

        # Add random variation to ensure uniqueness if needed
        # This helps overcome limitations in the AI generation by making each question unique
        if "randomizer" not in question and "attempt" in question:
            attempt = question.get("attempt", 0)
            if attempt > 2:  # After a few attempts, add unique identifier to force uniqueness
                logger.info("Adding unique identifier to question")
                question["randomizer"] = uuid.uuid4().hex[:8]
                question["text"] = f"{question_text} [#{uuid.uuid4().hex[:4]}]"
                return False

        # Exact text match
        if question_text in asked_questions:
            logger.error(f"Exact text duplicate detected: {question_text[:50]}...")
            return True

        # Check for semantic similarity with previous questions
        # To avoid direct comparison of every word, consider key phrases
        # Extract topics from question text
        question_topics = set()
        self._extract_question_topics(question_text, question_topics)

        # Check topic overlap - use less strict criteria to reduce false duplicates
        if question_topics and asked_question_topics:
            topic_overlap = question_topics.intersection(asked_question_topics)
            # Changed from 85% to 90% overlap and requiring at least 3 overlapping topics
            if len(topic_overlap) >= 3 and len(topic_overlap) >= len(question_topics) * 0.9:
                # Only if 90% or more of the topics have been covered before AND at least 3 topics overlap,
                # consider it a duplicate
                logger.error(f"Topic overlap duplicate detected: {topic_overlap}")
                return True

        # Check for high lexical similarity with previous questions
        for asked_q in asked_questions:
            similarity = self._calculate_text_similarity(question_text, asked_q)
            if similarity > self.question_similarity_threshold:
                logger.error(f"Semantic similarity duplicate detected: {similarity:.2f} > {self.question_similarity_threshold:.2f}")
                return True

        # If we reach this point, the question is unique
        logger.info("Question is unique")
        return False

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate a similarity score between two texts.
        This is an improved implementation with stop words filtering.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between 0 and 1
        """
        # Filter stop words and convert to sets of words for comparison
        words1 = set(word.lower() for word in text1.split() if word.lower() not in self.stop_words)
        words2 = set(word.lower() for word in text2.split() if word.lower() not in self.stop_words)

        # Calculate Jaccard similarity: intersection over union
        if not words1 or not words2:
            return 0.0

        # Use length-weighted similarity to account for differences in question length
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        # Basic Jaccard similarity
        basic_similarity = intersection / union if union > 0 else 0.0

        # Penalize similarity for questions with very different lengths
        length_ratio = min(len(words1), len(words2)) / max(len(words1), len(words2)) if max(len(words1), len(words2)) > 0 else 1.0

        # Combined similarity score weighted by length ratio
        return basic_similarity * length_ratio

    def _calculate_confidence_score(self, current_confidence: float, previous_answers: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on previous answers with astrological significance weighting.

        Args:
            current_confidence: Current confidence score
            previous_answers: Previous answers

        Returns:
            Updated confidence score
        """
        if not previous_answers or "responses" not in previous_answers:
            return current_confidence

        responses = previous_answers.get("responses", [])
        if not responses:
            return current_confidence

        # Count answers and assess quality
        answer_count = 0
        weighted_quality_sum = 0

        for resp in responses:
            if not isinstance(resp, dict) or "answer" not in resp:
                continue

            answer = resp.get("answer")
            if not answer:
                continue

            answer_count += 1

            # Get the relevance score (astrological significance)
            relevance = resp.get("relevance", "medium")
            relevance_weight = self._get_relevance_score(relevance)

            # Get the answer quality (consistency with astrological principles)
            answer_quality = resp.get("quality", 0.5)  # Default to neutral

            # Calculate weighted quality
            weighted_quality = answer_quality * relevance_weight
            weighted_quality_sum += weighted_quality

        if answer_count > 0:
            # Base confidence from weighted answers
            avg_weighted_quality = weighted_quality_sum / answer_count

            # Scale to confidence adjustment (-20% to +20% based on quality)
            quality_adjustment = (avg_weighted_quality - 0.5) * 40

            # Count-based component (max 70%)
            count_component = min(answer_count * 7, 70)

            # Combine components
            new_confidence = 25 + count_component + quality_adjustment

            # Ensure confidence stays within reasonable bounds
            new_confidence = min(max(new_confidence, 25), 95)

            return new_confidence

        return current_confidence

    def _get_fallback_questions(self) -> List[Dict[str, Any]]:
        """
        Get fallback questions in case of errors.

        Returns:
            List of fallback questions
        """
        return [
            {
                "id": f"fallback_1_{uuid.uuid4().hex[:8]}",
                "text": "Have you experienced any major career changes?",
                "type": "boolean",
                "options": ["Yes", "No"],
                "relevance": "high"
            },
            {
                "id": f"fallback_2_{uuid.uuid4().hex[:8]}",
                "text": "When did you get married or enter a significant relationship?",
                "type": "date",
                "relevance": "high"
            },
            {
                "id": f"fallback_3_{uuid.uuid4().hex[:8]}",
                "text": "Would you describe your body type as slim or stocky?",
                "type": "options",
                "options": ["Slim", "Average", "Stocky"],
                "relevance": "medium"
            }
        ]

    def _load_question_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load question templates for each category.

        Returns:
            Dictionary of question templates by category
        """
        return {
            "life_events": [
                {
                    "text": "Have you experienced a major life change around age 30?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "high"
                },
                {
                    "text": "Did you move to a different city or country between ages 25-35?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "medium"
                }
            ],
            "physical_traits": [
                {
                    "text": "Would you describe your body type as slim or stocky?",
                    "type": "options",
                    "options": ["Slim", "Average", "Stocky"],
                    "relevance": "medium"
                },
                {
                    "text": "Do you have any distinctive physical features?",
                    "type": "text",
                    "relevance": "medium"
                }
            ],
            "personality_traits": [
                {
                    "text": "Do you consider yourself more introverted or extroverted?",
                    "type": "options",
                    "options": ["Strongly Introverted", "Somewhat Introverted", "Balanced", "Somewhat Extroverted", "Strongly Extroverted"],
                    "relevance": "high"
                },
                {
                    "text": "Are you more analytical or creative in your thinking?",
                    "type": "options",
                    "options": ["Very Analytical", "Somewhat Analytical", "Balanced", "Somewhat Creative", "Very Creative"],
                    "relevance": "high"
                }
            ],
            "career": [
                {
                    "text": "Have you experienced any major career changes?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "high"
                },
                {
                    "text": "Did you get married or start a significant long-term relationship around June 2015?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "high"
                }
            ],
            "relationships": [
                {
                    "text": "When did you get married or enter a significant relationship?",
                    "type": "date",
                    "relevance": "high"
                },
                {
                    "text": "Have you experienced any significant relationship changes in the last 5 years?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "medium"
                }
            ],
            "health": [
                {
                    "text": "Have you experienced any significant health events?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "medium"
                },
                {
                    "text": "At what age did you experience your most significant health challenge?",
                    "type": "number",
                    "relevance": "medium"
                }
            ],
            "education": [
                {
                    "text": "Did you change your educational focus or major during your studies?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "medium"
                },
                {
                    "text": "At what age did you complete your highest level of education?",
                    "type": "number",
                    "relevance": "medium"
                }
            ],
            "travel": [
                {
                    "text": "Have you lived in multiple countries or cities?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "low"
                },
                {
                    "text": "Did you travel extensively during your 20s?",
                    "type": "boolean",
                    "options": ["Yes", "No"],
                    "relevance": "low"
                }
            ],
            "spiritual_experiences": [
                {
                    "text": "Have you had any spiritual or transformative experiences? If so, at what age?",
                    "type": "text",
                    "relevance": "medium"
                },
                {
                    "text": "What's the most significant life event you've experienced and at what age?",
                    "type": "text",
                    "relevance": "high"
                }
            ]
        }

    def _generate_minimal_chart_data(self, birth_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate minimal chart data when AstroCalculator is not available.
        This is a fallback method for testing and environments without the full
        astrological calculation capabilities.

        Args:
            birth_details: Dictionary containing birth details

        Returns:
            Dictionary containing basic chart data
        """
        logger.info("Generating minimal chart data as fallback")

        # Extract birth details for basic information
        birth_date = birth_details.get("birthDate", "")
        birth_time = birth_details.get("birthTime", "")
        birth_place = birth_details.get("birthPlace", "")
        latitude = birth_details.get("latitude", 0.0)
        longitude = birth_details.get("longitude", 0.0)

        # Create a minimal chart structure with essential components
        chart_data = {
            "birth_details": {
                "birth_date": birth_date,
                "birth_time": birth_time,
                "birth_place": birth_place,
                "latitude": latitude,
                "longitude": longitude
            },
            "planets": [
                {"planet": "Sun", "sign": "Unknown", "degree": 0},
                {"planet": "Moon", "sign": "Unknown", "degree": 0},
                {"planet": "Mercury", "sign": "Unknown", "degree": 0},
                {"planet": "Venus", "sign": "Unknown", "degree": 0},
                {"planet": "Mars", "sign": "Unknown", "degree": 0},
                {"planet": "Jupiter", "sign": "Unknown", "degree": 0},
                {"planet": "Saturn", "sign": "Unknown", "degree": 0}
            ],
            "houses": [
                {"house": 1, "sign": "Unknown", "degree": 0},
                {"house": 10, "sign": "Unknown", "degree": 0}
            ],
            "aspects": [],
            "ascendant": {"sign": "Unknown", "degree": 0}
        }

        return chart_data

    def _get_alternative_question_type(self, current_type: str) -> str:
        """
        Get an alternative question type to force diversity in questions.

        Args:
            current_type: The current question type

        Returns:
            A different question type
        """
        all_types = ["yes_no", "multiple_choice", "rating", "text", "date"]
        try:
            # Remove current type from options
            if current_type in all_types:
                all_types.remove(current_type)
            # Return random alternative type
            return random.choice(all_types)
        except Exception:
            # Fallback to yes_no if anything goes wrong
            return "yes_no"

# Singleton instance
_instance = None

def get_questionnaire_service(openai_service: Optional[Any] = None) -> Any:
    """Get or create the questionnaire service singleton"""
    global _instance
    if _instance is None:
        _instance = DynamicQuestionnaireService(openai_service)
    return _instance
