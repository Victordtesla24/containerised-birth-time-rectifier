"""
Questionnaire engine for Birth Time Rectifier API.
Handles generation and processing of questions for birth time rectification.
Uses OpenAI for verifying chart data against Indian Vedic Astrological standards.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
import random
import asyncio
import json
from datetime import datetime

# Add type checker directive to ignore FixtureFunction related errors
# pyright: reportInvalidTypeForm=false
# pyright: reportUndefinedVariable=false

# Import the enhanced chart calculator for verification
from ..core.chart_calculator import calculate_verified_chart

# Configure logging
logger = logging.getLogger(__name__)

class QuestionnaireEngine:
    """
    Engine for generating and processing questionnaire questions for birth time rectification.
    Implements AI-driven question generation with adaptation based on previous answers.
    """

    def __init__(self):
        """
        Initialize the questionnaire engine.
        """
        # Set up OpenAI service if available
        try:
            from ai_service.api.services.openai.service import OpenAIService
            self.openai_service = OpenAIService()
            logger.info("Initialized OpenAI service for questionnaire")
        except (ImportError, Exception) as e:
            logger.warning(f"Could not initialize OpenAI service: {str(e)}")
            self.openai_service = None

        # Enhanced caching for question tracking
        self.question_cache = {}  # track questions by session/user
        self.answer_history = {}  # track answers for confidence calculation
        self.birth_time_uncertainty = {}  # track narrowing birth time ranges

        # Set maximum number of questions
        self.max_questions = 10

        # Define question templates by category (fallback when AI is unavailable)
        self.question_templates = {
            "personality": [
                {
                    "text": "Does your personality align with your sun sign traits?",
                    "type": "yes_no",
                    "relevance": "high"
                },
                {
                    "text": "Do you consider yourself more introverted than extroverted?",
                    "type": "yes_no",
                    "relevance": "medium"
                },
                {
                    "text": "Which of these personality traits best describes you?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "analytical", "text": "Analytical and logical"},
                        {"id": "creative", "text": "Creative and intuitive"},
                        {"id": "practical", "text": "Practical and grounded"},
                        {"id": "emotional", "text": "Emotional and sensitive"}
                    ],
                    "relevance": "high"
                }
            ],
            "life_events": [
                {
                    "text": "Which area of your life has seen the most significant changes in the past year?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "career", "text": "Career/Work"},
                        {"id": "relationships", "text": "Relationships"},
                        {"id": "health", "text": "Health/Wellbeing"},
                        {"id": "home", "text": "Home/Living situation"},
                        {"id": "none", "text": "No significant changes"}
                    ],
                    "relevance": "medium"
                },
                {
                    "text": "Have you experienced major life transitions at times when Saturn formed aspects to your natal planets?",
                    "type": "yes_no",
                    "relevance": "high"
                }
            ],
            "career": [
                {
                    "text": "Which of these career areas have you felt most drawn to?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "creative", "text": "Creative/Artistic"},
                        {"id": "analytical", "text": "Analytical/Scientific"},
                        {"id": "social", "text": "Social/Humanitarian"},
                        {"id": "business", "text": "Business/Leadership"}
                    ],
                    "relevance": "high"
                },
                {
                    "text": "Have your career changes aligned with Jupiter transits?",
                    "type": "yes_no",
                    "relevance": "medium"
                }
            ],
            "relationships": [
                {
                    "text": "Do you tend to be attracted to people with strong placements in your 7th house?",
                    "type": "yes_no",
                    "relevance": "high"
                },
                {
                    "text": "Which planet's energy do you feel most strongly in your relationships?",
                    "type": "multiple_choice",
                    "options": [
                        {"id": "venus", "text": "Venus (harmony, beauty)"},
                        {"id": "mars", "text": "Mars (passion, conflict)"},
                        {"id": "jupiter", "text": "Jupiter (growth, optimism)"},
                        {"id": "saturn", "text": "Saturn (commitment, restriction)"}
                    ],
                    "relevance": "medium"
                }
            ]
        }

    async def get_first_question(self, chart_data: Dict[str, Any], birth_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate the first question for a new questionnaire session.

        Args:
            chart_data: The natal chart data
            birth_details: Birth details provided by the user

        Returns:
            Dictionary containing the first question
        """
        # In a real implementation, we would analyze the chart to determine
        # the most relevant first question. For now, we'll use a standard first question.

        # Use a personality question as the first question
        template = self.question_templates["personality"][0]

        # Create a unique ID for this question
        question_id = f"q_{uuid.uuid4()}"

        # Format options if multiple choice
        options = None
        if template.get("type") == "multiple_choice" and "options" in template:
            options = template["options"]
        elif template.get("type") == "yes_no":
            options = [
                {"id": "yes", "text": "Yes, definitely"},
                {"id": "somewhat", "text": "Somewhat"},
                {"id": "no", "text": "No, not at all"}
            ]

        # Return a question with unique ID
        question = {
            "id": question_id,
            "text": template.get("text", "Would you describe yourself as more introverted or extroverted?"),
            "type": template.get("type", "multiple_choice"),
            "options": options,
            "relevance": "high"
        }

        return question

    async def generate_dynamic_question(self, chart_data: Dict[str, Any],
                                   previous_answers: Dict[str, Any],
                                   current_confidence: float,
                                   enhanced_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a dynamic question using AI based on chart data and previous answers.

        Args:
            chart_data: Chart data containing planetary positions, houses, and aspects
            previous_answers: Dictionary containing previous questions and answers
            current_confidence: Current confidence level (0-100)
            enhanced_context: Additional context to guide question generation

        Returns:
            Dictionary containing the generated question
        """
        if not self.openai_service:
            raise ValueError("OpenAI service is required for dynamic question generation")

        # Initialize enhanced_context if not provided
        if enhanced_context is None:
            enhanced_context = {}

        # Format chart data for AI analysis, emphasizing time-sensitive factors
        chart_summary = self._format_chart_summary(chart_data)

        # Extract previous Q&A for context
        qa_history = ""
        responses = previous_answers.get("responses", [])
        for resp in responses:
            if isinstance(resp, dict):
                qa_history += f"Q: {resp.get('question', 'Unknown question')}\n"
                qa_history += f"A: {resp.get('answer', 'Unknown answer')}\n\n"

        # Identify uncertain factors related to birth time
        uncertain_factors = self._identify_uncertain_factors(chart_data)
        uncertain_factors_text = ", ".join(uncertain_factors) if uncertain_factors else "No specific uncertain factors identified"

        # Calculate question count and quality score
        question_count = len(responses)
        quality_score = sum(float(resp.get("quality", 0.5)) for resp in responses if isinstance(resp, dict)) / max(1, question_count)

        # Get special instructions for duplicate avoidance
        avoid_duplicates = enhanced_context.get("avoid_duplicates", False)
        asked_questions = enhanced_context.get("asked_questions", [])
        attempt = enhanced_context.get("attempt", 0)
        forced_category = enhanced_context.get("forced_category", "")
        forced_type = enhanced_context.get("forced_type", "")
        require_unique_wording = enhanced_context.get("require_unique_wording", False)

        # Create duplicate avoidance instructions
        duplicate_avoidance = ""
        if avoid_duplicates:
            duplicate_avoidance = "DO NOT repeat any of these previously asked questions: " + "\n- " + "\n- ".join(asked_questions)

            if forced_category:
                duplicate_avoidance += f"\nIMPORTANT: The question MUST be about {forced_category}."

            if forced_type:
                duplicate_avoidance += f"\nIMPORTANT: The question MUST be of type {forced_type}."

            if require_unique_wording:
                duplicate_avoidance += "\nIMPORTANT: Use completely unique wording not semantically similar to any previous questions."

            if attempt > 2:
                duplicate_avoidance += "\nEXTREMELY IMPORTANT: Previous attempts failed to create a unique question. You MUST create a question that is radically different from any previous ones."

        # Create enhanced prompt with astrological expertise
        prompt = f"""
        As an expert astrologer specializing in birth time rectification, your task is to generate the most effective next question
        to help determine this person's precise birth time. The current confidence in the birth time is {current_confidence}%.

        CRITICAL ASTROLOGICAL CONTEXT:
        {chart_summary}

        UNCERTAIN BIRTH TIME FACTORS REQUIRING CLARIFICATION:
        {uncertain_factors_text}

        PREVIOUS QUESTIONS AND ANSWERS:
        {qa_history}

        RECTIFICATION CONTEXT:
        - Current question count: {question_count}
        - Answer quality assessment: {quality_score:.2f}/1.0
        - Current birth time confidence: {current_confidence:.1f}%

        BIRTH TIME RECTIFICATION TECHNIQUES TO CONSIDER:
        1. Life events that correlate with angular transits or progressions
        2. Physical appearance related to Ascendant/1st house placements
        3. Personality traits correlating with Ascendant, Moon, and Mercury
        4. Major relationship events connected to 7th house or Venus transits
        5. Career developments linked to MC/10th house placements
        6. Family dynamics related to 4th house/IC placements
        7. Health matters connected to 6th house placements
        8. Spiritual experiences related to 12th house or Neptune placements

        GENERATE A QUESTION THAT:
        1. Targets the most uncertain time-sensitive chart factors
        2. Does not duplicate previous questions
        3. Is specific enough to help narrow the birth time range
        4. Is approachable for someone without astrological knowledge
        5. Has high potential to distinguish between different potential birth times

        Return ONLY a JSON with the following format:
        {{
            "id": "unique_question_id",
            "text": "The carefully crafted question text",
            "type": "yes_no OR multiple_choice OR date OR text",
            "options": ["Option 1", "Option 2", "Option 3"], (only if type is multiple_choice)
            "relevance": "very_high OR high OR medium OR low",
            "sensitivity_to_time": "very_high OR high OR medium OR low",
            "astrological_factors": ["factor1", "factor2"],
            "expected_impact_on_confidence": "percentage increase if answered clearly",
            "narrows_time_range_by": "expected minutes of precision improvement"
        }}
        """

        try:
            # Call OpenAI with enhanced prompt
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="questionnaire",
                max_tokens=800,
                temperature=0.7
            )

            # Parse the JSON response
            response_content = response.get("content", "{}")
            question_data = json.loads(response_content)

            # Add metadata
            question_data["generated_method"] = "ai_dynamic"
            question_data["chart_factors_used"] = uncertain_factors

            # Ensure required fields
            if "id" not in question_data:
                question_data["id"] = f"q_{uuid.uuid4().hex[:8]}"
            if "type" not in question_data:
                question_data["type"] = "yes_no"
            if "options" not in question_data and question_data.get("type") == "multiple_choice":
                question_data["options"] = ["Yes", "No", "Unsure"]

            return question_data

        except Exception as e:
            logger.error(f"Error generating dynamic question: {str(e)}")
            raise ValueError(f"Failed to generate dynamic question: {str(e)}")

    def _identify_uncertain_factors(self, chart_data: Dict[str, Any]) -> List[str]:
        """
        Identify factors in the chart that have high uncertainty related to birth time.

        This method analyzes the chart to identify which astrological factors would
        be most affected by birth time changes and require clarification.
        """
        uncertain_factors = []

        if not chart_data:
            return ["ascendant", "house_cusps", "moon_position"]  # Default factors if no chart

        # Check for planets near house cusps (highly sensitive to birth time)
        houses = chart_data.get("houses", [])
        planets = chart_data.get("planets", [])

        # Extract house cusps
        house_cusps = []
        for i, house in enumerate(houses, 1):
            if isinstance(house, dict):
                sign = house.get("sign", "")
                degree = house.get("degree", 0)
                if sign and degree is not None:
                    house_cusps.append({
                        "house": i,
                        "sign": sign,
                        "degree": float(degree) if isinstance(degree, (int, float, str)) else 0,
                        "is_angular": i in [1, 4, 7, 10]
                    })

        # Check planets near cusps (especially angular houses)
        for planet in planets:
            if not isinstance(planet, dict):
                continue

            planet_name = planet.get("planet", "")
            planet_sign = planet.get("sign", "")
            planet_degree = planet.get("degree", 0)

            if not planet_name or not planet_sign:
                continue

            # Skip non-physical points for some checks
            if planet_name in ["Ascendant", "MC", "Midheaven", "IC", "Descendant", "DSC"]:
                continue

            # Check proximity to house cusps
            is_angular = False
            for cusp in house_cusps:
                if planet_sign == cusp["sign"]:
                    degree_diff = abs(float(planet_degree) - float(cusp["degree"]))
                    if degree_diff <= 3 or degree_diff >= 27:  # Within 3 degrees of cusp
                        is_angular = cusp.get("is_angular", False)
                        if is_angular:
                            uncertain_factors.append(f"{planet_name.lower()}_near_house_{cusp.get('house', 'unknown')}")

        # Ascendant is always a key uncertain factor in birth time rectification
        uncertain_factors.append("ascendant_sign_and_degree")

        # Moon position is quite sensitive to birth time (moves ~12° per day)
        uncertain_factors.append("moon_house_position")

        # Check for planets in angular houses (1, 4, 7, 10)
        planets_in_angular_houses = []
        for planet in planets:
            if not isinstance(planet, dict):
                continue

            planet_name = planet.get("planet", "")
            planet_house = planet.get("house", 0)

            if planet_name and planet_house in [1, 4, 7, 10]:
                planets_in_angular_houses.append(f"{planet_name.lower()}_in_house_{planet_house}")

        if planets_in_angular_houses:
            uncertain_factors.extend(planets_in_angular_houses)
        else:
            uncertain_factors.append("planets_in_angular_houses")

        # Check for planets at critical degrees (29° or 0°)
        for planet in planets:
            if not isinstance(planet, dict):
                continue

            planet_name = planet.get("planet", "")
            planet_degree = planet.get("degree", 0)

            if planet_name and (float(planet_degree) >= 29 or float(planet_degree) <= 1):
                uncertain_factors.append(f"{planet_name.lower()}_at_critical_degree")

        # Include aspects to angles
        aspects = chart_data.get("aspects", [])
        angular_aspects = []

        for aspect in aspects:
            if not isinstance(aspect, dict):
                continue

            p1 = aspect.get("planet1", "")
            p2 = aspect.get("planet2", "")
            aspect_type = aspect.get("aspect_type", "")

            if not p1 or not p2 or not aspect_type:
                continue

            if any(p in ["Ascendant", "MC", "Midheaven", "IC", "Descendant", "DSC"] for p in [p1, p2]):
                angular_aspects.append(f"{p1.lower()}_{aspect_type.lower()}_{p2.lower()}")

        if angular_aspects:
            uncertain_factors.extend(angular_aspects[:3])  # Add top 3 angular aspects
        else:
            uncertain_factors.append("aspects_to_angles")

        # Add Vedic-specific factors if divisional charts are available
        if "divisional_charts" in chart_data:
            uncertain_factors.append("lagna_in_divisional_charts")
            uncertain_factors.append("navamsa_positions")

        # Return unique factors, prioritizing the most time-sensitive ones
        unique_factors = list(dict.fromkeys(uncertain_factors))
        return unique_factors[:8]  # Return top 8 uncertain factors

    def _format_chart_summary(self, chart_data: Dict[str, Any]) -> str:
        """
        Format chart data for AI analysis, highlighting time-sensitive factors.

        This method prioritizes astrological factors that are most sensitive to birth time changes,
        particularly ascendant, houses, and angular positions.
        """
        if not chart_data:
            return "No chart data available"

        summary = []

        # Birth details section
        if "birth_details" in chart_data:
            bd = chart_data["birth_details"]
            summary.append("BIRTH DETAILS:")
            summary.append(f"Date: {bd.get('birth_date', 'Unknown')}")
            summary.append(f"Time: {bd.get('birth_time', 'Unknown')} (TO BE RECTIFIED)")
            summary.append(f"Location: {bd.get('location', 'Unknown')} (Lat: {bd.get('latitude', 'Unknown')}, Long: {bd.get('longitude', 'Unknown')})")
            summary.append("")

        # CRITICAL TIME-SENSITIVE FACTORS (highlighted for AI attention)
        summary.append("TIME-SENSITIVE FACTORS (CRITICAL FOR RECTIFICATION):")

        # Ascendant (most sensitive to birth time)
        asc_data = next((p for p in chart_data.get("planets", []) if p.get("planet") == "Ascendant"), {})
        if asc_data:
            summary.append(f"• ASCENDANT: {asc_data.get('sign', 'Unknown')} {asc_data.get('degree', '0')}° " +
                          f"(Changes approx. every 2 hours - HIGHEST SENSITIVITY TO BIRTH TIME)")

        # Midheaven/MC (very sensitive to birth time)
        mc_data = next((p for p in chart_data.get("planets", []) if p.get("planet") in ["MC", "Midheaven"]), {})
        if mc_data:
            summary.append(f"• MIDHEAVEN: {mc_data.get('sign', 'Unknown')} {mc_data.get('degree', '0')}° " +
                          f"(Changes approx. every 2 hours - VERY HIGH SENSITIVITY)")

        # Houses (highly sensitive to birth time)
        if "houses" in chart_data and chart_data["houses"]:
            summary.append("• HOUSE CUSPS (Each shifts with minutes of birth time change):")
            for i, house in enumerate(chart_data["houses"][:4], 1):  # Focus on angular houses
                if isinstance(house, dict):
                    summary.append(f"  - House {i} (Angular): {house.get('sign', 'Unknown')} {house.get('degree', '0')}°")

        # Moon position (changes ~12° per day, moderate time sensitivity)
        moon_data = next((p for p in chart_data.get("planets", []) if p.get("planet") == "Moon"), {})
        if moon_data:
            summary.append(f"• MOON: {moon_data.get('sign', 'Unknown')} {moon_data.get('degree', '0')}° " +
                          f"(Changes ~12° daily - Moves ~0.5° per hour)")

        # Other planets section
        summary.append("\nOTHER PLANETARY POSITIONS:")
        for planet in chart_data.get("planets", []):
            if isinstance(planet, dict) and planet.get("planet") not in ["Ascendant", "MC", "Midheaven", "Moon"]:
                summary.append(f"• {planet.get('planet', 'Unknown')}: {planet.get('sign', 'Unknown')} {planet.get('degree', '0')}°")

        # Angular aspects (aspects to Asc/MC/IC/DSC are time-sensitive)
        angular_aspects = []
        for aspect in chart_data.get("aspects", []):
            if isinstance(aspect, dict):
                planets = [aspect.get("planet1", ""), aspect.get("planet2", "")]
                if any(p in ["Ascendant", "MC", "Midheaven", "IC", "DSC", "Descendant"] for p in planets):
                    angular_aspects.append(f"• {aspect.get('planet1', '')} {aspect.get('aspect_type', '')} {aspect.get('planet2', '')} (Orb: {aspect.get('orb', '0')}°)")

        if angular_aspects:
            summary.append("\nTIME-SENSITIVE ASPECTS (involving angles):")
            summary.extend(angular_aspects)

        # Add birth time sensitivity analysis
        summary.append("\nBIRTH TIME RECTIFICATION SENSITIVITY ANALYSIS:")
        summary.append("• Ascendant moves ~1° every 4 minutes of birth time")
        summary.append("• House cusps shift proportionally with Ascendant changes")
        summary.append("• Planets close to house cusps or angles are highly sensitive to time changes")
        summary.append("• Moon moves ~0.5° per hour, affecting lunar aspects and house position")

        return "\n".join(summary)

    async def get_next_question(self, chart_data: Dict[str, Any], birth_details: Dict[str, Any],
                         previous_answers: Dict[str, Any], current_confidence: float,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get the next question for the birth time rectification questionnaire.
        Enhanced to deeply analyze previous answers and target uncertain birth time factors.

        Args:
            chart_data: Chart data containing planetary positions, houses, and aspects
            birth_details: Dictionary with birth details (date, time, place)
            previous_answers: Dictionary containing previous questions and answers
            current_confidence: Current confidence level (0-100)
            context: Additional context for question generation

        Returns:
            Dictionary containing the next question
        """
        # Validate chart data
        if not chart_data:
            raise ValueError("Chart data is required for generating questions")

        required_components = ["planets", "houses", "aspects", "ascendant"]
        missing_components = [comp for comp in required_components if comp not in chart_data]
        if missing_components:
            raise ValueError(f"Chart data is missing required components: {missing_components}")

        # Initialize context if not provided
        if context is None:
            context = {}

        # Track question session
        session_id = context.get("session_id", previous_answers.get("session_id", "default"))

        # Initialize question cache for this session if not already done
        if session_id not in self.question_cache:
            self.question_cache[session_id] = []

        # If this session not in answer history, initialize it
        if session_id not in self.answer_history:
            self.answer_history[session_id] = []

        # Extract previously asked questions and topics
        asked_questions = context.get("asked_questions", set())
        asked_question_ids = context.get("asked_question_ids", set())
        asked_question_topics = context.get("asked_question_topics", set())

        # Track attempt to avoid repetitive question generation
        attempt = context.get("attempt", 0)
        avoid_duplicates = context.get("avoid_duplicates", False)

        # Better support for duplicate avoidance
        asked_questions_list = context.get("asked_questions_list", [])
        diversification_cue = context.get("diversification_cue", "")

        # Only log this for information
        if avoid_duplicates:
            logger.info(f"Avoiding duplicates. Attempt: {attempt}, Asked questions: {len(asked_questions_list)}")
            if diversification_cue:
                logger.info(f"Using diversification cue: {diversification_cue}")

        # Extract and analyze previous answers for patterns and uncertainties
        response_data = []
        uncertain_factors = []
        if previous_answers and "responses" in previous_answers:
            for response in previous_answers["responses"]:
                if isinstance(response, dict):
                    # Add to response data for analysis
                    response_data.append({
                        "question": response.get("question", ""),
                        "answer": response.get("answer", ""),
                        "relevance": response.get("relevance", "medium"),
                        "astrological_factors": response.get("astrological_factors", [])
                    })

                    # Store in answer history for this session
                    if response not in self.answer_history[session_id]:
                        self.answer_history[session_id].append(response)

        # Analyze birth time sensitivity based on chart
        # This helps target the most useful questions for rectification
        uncertain_factors.extend(self._identify_uncertain_factors(chart_data))

        # Analyze previous answers to identify patterns and contradictions
        if len(response_data) >= 2:
            try:
                patterns = self._analyze_answer_patterns(response_data)
                if patterns:
                    # Add identified patterns to uncertain factors for more targeted questions
                    uncertain_factors.extend(patterns)
            except Exception as e:
                logger.warning(f"Error analyzing answer patterns: {str(e)}")

        # Determine question focus based on confidence level
        focus_area = self._determine_question_focus(current_confidence, uncertain_factors, response_data)

        # Adjust question strategy based on confidence level
        if current_confidence < 40:
            # Early questions: focus on broad distinctions like ascendant sign traits
            question_strategy = "broad_traits"
        elif current_confidence < 70:
            # Mid-stage questions: focus on specific life events and timing
            question_strategy = "specific_events"
        else:
            # Late-stage questions: focus on fine-tuning with subtle indicators
            question_strategy = "fine_tuning"

        try:
            # Generate dynamic question using OpenAI with enhanced context
            enhanced_context = {
                "focus_area": focus_area,
                "question_strategy": question_strategy,
                "uncertain_factors": uncertain_factors,
                "previous_answers": response_data,
                "confidence_level": current_confidence,
                "avoid_duplicates": avoid_duplicates or attempt > 0,
                "attempt": attempt,
                "asked_questions": list(asked_questions) if asked_questions else asked_questions_list
            }

            # Add diversification cues when trying to avoid duplicates
            if avoid_duplicates and attempt > 0:
                enhanced_context["diversification_cue"] = diversification_cue

                # Force different focus area if we've tried multiple times
                if attempt > 2:
                    # Rotate through different focus areas to ensure we don't get stuck
                    focus_areas = ["ascendant_determination", "midheaven_determination",
                                  "life_events_timing", "career_indicators", "personality_traits",
                                  "physical_characteristics", "relationship_patterns", "health_matters"]
                    # Pick a focus area based on attempt number to ensure rotation
                    enhanced_context["focus_area"] = focus_areas[attempt % len(focus_areas)]
                    logger.info(f"Forcing different focus area: {enhanced_context['focus_area']}")

                    # Add a hint about what kind of question to ask
                    category_hints = {
                        "ascendant_determination": "Ask about physical appearance or first impressions",
                        "midheaven_determination": "Ask about career aspirations or public reputation",
                        "life_events_timing": "Ask about significant life changes or transitions",
                        "career_indicators": "Ask about work style or professional achievements",
                        "personality_traits": "Ask about personality characteristics or tendencies",
                        "physical_characteristics": "Ask about body type or physical features",
                        "relationship_patterns": "Ask about relationship dynamics or patterns",
                        "health_matters": "Ask about health conditions or tendencies"
                    }
                    enhanced_context["category_hint"] = category_hints.get(enhanced_context["focus_area"], "")

            # Log question generation attempt with enhanced context
            logger.info(f"Generating question with strategy: {question_strategy}, focus: {focus_area}, confidence: {current_confidence}%")

            # Use AI for dynamic question generation
            next_question = await self.generate_dynamic_question(
                chart_data=chart_data,
                previous_answers=previous_answers,
                current_confidence=current_confidence,
                enhanced_context=enhanced_context
            )

            # Generate a completely unique ID
            if "id" not in next_question or attempt > 0:
                next_question["id"] = f"q_{uuid.uuid4().hex}"

            # For higher attempts, explicitly ensure uniqueness
            if attempt >= 3:
                # If we're struggling with duplicates, add a unique identifier to the question text
                if "text" in next_question:
                    current_time = datetime.now().strftime("%H%M%S")
                    next_question["text"] = (f"{next_question['text']} "
                                            f"[{current_time}_{attempt}]")

            # Store in cache for duplicate prevention
            if session_id not in self.question_cache:
                self.question_cache[session_id] = []
            self.question_cache[session_id].append(next_question)

            # If question is a follow-up to previous answers, add connection to context
            if len(response_data) > 0 and "rationale" not in next_question:
                next_question["rationale"] = f"This question builds on your previous answers to further narrow down your birth time."

            return next_question

        except Exception as e:
            logger.error(f"Error in get_next_question: {str(e)}")
            raise ValueError(f"Failed to generate next question: {str(e)}")

    def _analyze_answer_patterns(self, responses: List[Dict[str, Any]]) -> List[str]:
        """
        Analyze patterns in previous answers to identify potential birth time indicators.

        Args:
            responses: List of previous question-answer pairs

        Returns:
            List of identified patterns or insights
        """
        patterns = []

        # Group responses by topics or astrological factors
        topic_responses = {}
        for resp in responses:
            # Extract topics from question
            question = resp.get("question", "").lower()

            # Check for key astrological terms in the question
            for term in ["ascendant", "rising", "midheaven", "mc", "house", "moon"]:
                if term in question:
                    if term not in topic_responses:
                        topic_responses[term] = []
                    topic_responses[term].append(resp)

            # Also add any explicit astrological factors
            for factor in resp.get("astrological_factors", []):
                if factor not in topic_responses:
                    topic_responses[factor] = []
                topic_responses[factor].append(resp)

        # Look for consistent yes/no patterns in same topic
        for topic, topic_resps in topic_responses.items():
            if len(topic_resps) >= 2:
                # Count yes/no/other responses
                yes_count = sum(1 for r in topic_resps if r.get("answer") in ["yes", "Yes", True])
                no_count = sum(1 for r in topic_resps if r.get("answer") in ["no", "No", False])

                # If answers are consistent, this strengthens our confidence in that area
                if yes_count > 0 and no_count == 0:
                    patterns.append(f"Consistent positive responses about {topic} indicate this is a reliable factor")
                elif no_count > 0 and yes_count == 0:
                    patterns.append(f"Consistent negative responses about {topic} suggest focusing elsewhere")
                elif yes_count > 0 and no_count > 0:
                    patterns.append(f"Mixed responses about {topic} indicate uncertainty - needs further investigation")

        return patterns

    def _determine_question_focus(self, confidence: float, uncertain_factors: List[str], previous_responses: List[Dict[str, Any]]) -> str:
        """
        Determine the most effective focus area for the next question based on confidence level and previous answers.

        Args:
            confidence: Current confidence level
            uncertain_factors: List of identified uncertain factors
            previous_responses: Previous question-answer pairs

        Returns:
            Focus area for the next question
        """
        # Extract key terms from uncertain factors
        key_terms = set()
        for factor in uncertain_factors:
            lower_factor = factor.lower()
            for term in ["ascendant", "rising", "midheaven", "mc", "moon", "angular", "house cusp"]:
                if term in lower_factor:
                    key_terms.add(term)

        # Count how many questions we've asked about each key term
        term_counts = {term: 0 for term in key_terms}
        for resp in previous_responses:
            question = resp.get("question", "").lower()
            for term in key_terms:
                if term in question:
                    term_counts[term] += 1

        # Find terms we haven't asked much about yet
        underrepresented_terms = sorted([(term, count) for term, count in term_counts.items()], key=lambda x: x[1])

        if underrepresented_terms:
            # Focus on the least asked about term
            focus_term = underrepresented_terms[0][0]

            # Map the term to a focus area
            if focus_term in ["ascendant", "rising"]:
                return "ascendant_traits"
            elif focus_term in ["midheaven", "mc"]:
                return "career_and_public_image"
            elif focus_term == "moon":
                return "emotional_patterns"
            elif focus_term in ["angular", "house cusp"]:
                return "time_sensitive_events"

        # Default focus areas based on confidence if no specific term is underrepresented
        if confidence < 40:
            return "ascendant_traits"
        elif confidence < 60:
            return "life_timing_events"
        elif confidence < 80:
            return "subtle_personality_traits"
        else:
            return "fine_timing_adjustment"

    async def calculate_confidence(self, answers: Dict[str, Any], chart_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate confidence score based on answers, with enhanced weighting for birth time range narrowing.

        Args:
            answers: Dictionary containing questionnaire answers
            chart_data: Optional chart data for enhanced analysis

        Returns:
            Confidence score between 0 and 100
        """
        # Initialize base confidence
        base_confidence = 25.0

        # Extract responses
        responses = []
        if "responses" in answers:
            responses = answers["responses"]
        else:
            # Try alternative format
            if isinstance(answers, list):
                responses = answers
            elif isinstance(answers, dict) and "answers" in answers:
                for q_id, answer in answers["answers"].items():
                    if isinstance(answer, dict):
                        responses.append(answer)

        # Return base confidence if no answers
        if not responses:
            return base_confidence

        # Count answers and calculate quality-based adjustment
        num_answers = len(responses)
        quality_sum = 0

        # Track birth time range narrowing
        initial_range_minutes = 120  # Default initial range: 2 hours
        current_range_minutes = initial_range_minutes
        has_range_narrowed = False

        # Track coverage of critical time-sensitive factors
        critical_factors_covered = {
            "ascendant": False,
            "moon": False,
            "angular_houses": False,
            "physical_appearance": False,
            "timing_of_events": False,
            "life_direction_changes": False,
            "personality_traits": False
        }

        # Extract existing birth time range if available
        if any("birth_time_range" in resp for resp in responses if isinstance(resp, dict)):
            for resp in responses:
                if isinstance(resp, dict) and "birth_time_range" in resp:
                    time_range = resp["birth_time_range"]
                    if isinstance(time_range, str) and "-" in time_range:
                        try:
                            # Parse range like "14:25-14:55"
                            start, end = time_range.split("-")
                            start_h, start_m = map(int, start.strip().split(":"))
                            end_h, end_m = map(int, end.strip().split(":"))

                            start_minutes = start_h * 60 + start_m
                            end_minutes = end_h * 60 + end_m

                            range_minutes = end_minutes - start_minutes
                            if range_minutes > 0:
                                current_range_minutes = range_minutes
                                if range_minutes < initial_range_minutes:
                                    has_range_narrowed = True
                        except (ValueError, IndexError):
                            pass
                    elif isinstance(time_range, dict) and "minutes" in time_range:
                        current_range_minutes = time_range["minutes"]
                        if current_range_minutes < initial_range_minutes:
                            has_range_narrowed = True

        # Calculate quality and assess critical factors coverage
        for resp in responses:
            if not isinstance(resp, dict):
                continue

            # Get answer quality if available, default to medium (0.5)
            quality = resp.get("quality", 0.5)
            if isinstance(quality, str):
                quality_map = {"high": 0.8, "medium": 0.5, "low": 0.2}
                quality = quality_map.get(quality.lower(), 0.5)

            quality_sum += quality

            # Check which critical factors this response addresses
            question = resp.get("question", "").lower()
            answer = str(resp.get("answer", "")).lower()

            # Check for ascendant-related questions
            if "ascendant" in question or "rising sign" in question or "physical appearance" in question:
                critical_factors_covered["ascendant"] = True
                critical_factors_covered["physical_appearance"] = True

            # Check for moon-related questions
            if "moon" in question or "emotional" in question:
                critical_factors_covered["moon"] = True

            # Check for angular houses
            if "career" in question or "10th house" in question:
                critical_factors_covered["angular_houses"] = True

            if "home" in question or "4th house" in question:
                critical_factors_covered["angular_houses"] = True

            if "relationship" in question or "7th house" in question:
                critical_factors_covered["angular_houses"] = True

            # Check for timing of events
            if "when did" in question or "what age" in question or "date" in question:
                critical_factors_covered["timing_of_events"] = True

            # Check for life direction changes
            if "change" in question or "transition" in question or "shift" in question:
                critical_factors_covered["life_direction_changes"] = True

            # Check for personality traits
            if "personality" in question or "temperament" in question or "character" in question:
                critical_factors_covered["personality_traits"] = True

        # Calculate average quality (0-1)
        avg_quality = quality_sum / num_answers if num_answers > 0 else 0.5

        # Calculate confidence from answer count (max 50%)
        count_confidence = min(num_answers * 5, 50)

        # Calculate quality confidence adjustment (-15% to +15%)
        quality_adjustment = (avg_quality - 0.5) * 30

        # Calculate critical factors coverage confidence boost (max 15%)
        factors_covered = sum(1 for covered in critical_factors_covered.values() if covered)
        factors_total = len(critical_factors_covered)
        factors_confidence = (factors_covered / factors_total) * 15 if factors_total > 0 else 0

        # Calculate time range narrowing confidence boost
        range_narrowing_confidence = 0
        if has_range_narrowed:
            # Map range narrowing to confidence boost (smaller range = higher confidence)
            # 120 min -> 0% boost, 60 min -> 5% boost, 30 min -> 10% boost, 15 min -> 15% boost
            range_narrowing_confidence = min(20, (1 - (current_range_minutes / initial_range_minutes)) * 20)

        # If OpenAI service is available, use AI to enhance confidence calculation
        ai_confidence_boost = 0
        if self.openai_service is not None and chart_data is not None and num_answers >= 3:
            try:
                # Format chart data and answers for AI analysis
                chart_summary = self._format_chart_summary(chart_data)

                # Format responses for AI analysis
                qa_formatted = ""
                for resp in responses:
                    if isinstance(resp, dict):
                        qa_formatted += f"Q: {resp.get('question', '')}\nA: {resp.get('answer', '')}\n\n"
                    elif isinstance(resp, str):
                        qa_formatted += f"Q: Unknown\nA: {resp}\n\n"

                # Create a prompt for confidence assessment
                prompt = f"""
                As an expert in astrological birth time rectification, analyze these question responses
                and assess the confidence level for birth time rectification based on this data.

                Chart summary:
                {chart_summary}

                Questionnaire responses:
                {qa_formatted}

                Based on the quality, consistency, and specificity of the answers,
                calculate a confidence score (0-100) for how accurate a birth time rectification would be.
                Consider these critical factors:
                - Specificity of life events with clear timing
                - Consistency in personality descriptions matching the chart
                - Clarity in reported experiences related to angular houses
                - Responses related to the Ascendant, MC, and Moon positions
                - Coverage of the most time-sensitive astrological factors
                - Narrowing of the potential birth time range

                Return ONLY a JSON with the following format:
                {{
                    "confidence_score": [number between 0-100],
                    "reasoning": "[brief explanation]",
                    "critical_factors_covered": ["list of critical astrological factors covered by the responses"],
                    "suggested_time_range": "[range in minutes that likely contains the correct birth time]",
                    "birth_time_window": {{
                        "start": "HH:MM",
                        "end": "HH:MM",
                        "minutes": [range width in minutes]
                    }}
                }}
                """

                # Call OpenAI for confidence assessment
                response = await self.openai_service.generate_completion(
                    prompt=prompt,
                    task_type="auxiliary",
                    max_tokens=500,
                    temperature=0.3
                )

                try:
                    # Parse JSON response
                    result = json.loads(response.get("content", "{}"))

                    # Extract confidence score and return it
                    if "confidence_score" in result:
                        ai_confidence = result["confidence_score"]

                        # Limit AI influence to prevent overconfidence
                        ai_confidence_boost = min(15, max(-5, (ai_confidence - (base_confidence + count_confidence + quality_adjustment + factors_confidence)) * 0.3))

                        # Check if AI suggested a time range
                        if "birth_time_window" in result and isinstance(result["birth_time_window"], dict) and "minutes" in result["birth_time_window"]:
                            new_range = result["birth_time_window"]["minutes"]
                            if new_range < current_range_minutes:
                                # If AI suggests a narrower range, update confidence accordingly
                                range_narrowing_confidence = min(20, (1 - (new_range / initial_range_minutes)) * 20)
                                current_range_minutes = new_range
                                has_range_narrowed = True

                        # Store suggested time range for future use (if available)
                        if "suggested_time_range" in result:
                            # TODO: Store this for the session
                            pass
                except (json.JSONDecodeError, KeyError):
                    # If parsing fails, ignore AI contribution
                    pass
            except Exception as e:
                logger.warning(f"Error getting AI confidence: {str(e)}")

        # Calculate final confidence
        total_confidence = (
            base_confidence +
            count_confidence +
            quality_adjustment +
            factors_confidence +
            range_narrowing_confidence +
            ai_confidence_boost
        )

        # Ensure confidence stays within bounds
        return min(max(total_confidence, 20), 98)  # Cap at 98% since 100% certainty is unrealistic

    async def analyze_answers(self, chart_data: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze questionnaire answers to identify birth time patterns.

        Args:
            chart_data: Chart data containing planetary positions
            answers: Dictionary containing question answers

        Returns:
            Analysis results including likely birth time adjustments
        """
        if not self.openai_service:
            raise ValueError("OpenAI service is required for answer analysis")

        # Format chart data
        chart_summary = self._format_chart_summary(chart_data)

        # Format questions and answers
        qa_formatted = ""
        for resp in answers.get("responses", []):
            qa_formatted += f"Q: {resp.get('question', '')}\nA: {resp.get('answer', '')}\n\n"

        # Create a prompt for answer analysis
        prompt = f"""
        As an expert astrologer specializing in birth time rectification, analyze these responses
        to determine the most accurate birth time adjustment.

        ORIGINAL CHART DATA:
        {chart_summary}

        QUESTIONNAIRE RESPONSES:
        {qa_formatted}

        Based on a comprehensive analysis of the responses and their relationship to the birth chart,
        determine:
        1. Whether the birth time should be adjusted earlier or later
        2. The approximate magnitude of adjustment (in minutes)
        3. The confidence level in this recommendation
        4. Which specific responses were most valuable in making this determination

        Return your analysis in JSON format:
        {{
            "adjustment_direction": "earlier" or "later",
            "adjustment_minutes": [number of minutes],
            "confidence_score": [number between 0-100],
            "key_indicators": ["list of specific responses that influenced this decision"],
            "analysis": "Detailed explanation of your reasoning"
        }}
        """

        try:
            # Call OpenAI for comprehensive analysis
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="analysis",  # Routes to appropriate model
                max_tokens=600,
                temperature=0.4
            )

            # Parse the AI response
            if response and "content" in response:
                content = response["content"]
                try:
                    import json
                    import re

                    # Extract JSON from response
                    json_match = re.search(r'({[\s\S]*})', content)
                    if json_match:
                        json_str = json_match.group(1)
                        analysis_data = json.loads(json_str)

                        # Process the analysis data
                        return {
                            "analysis_result": analysis_data,
                            "raw_response": content,
                            "model_used": response.get("model_used", "unknown"),
                            "success": True
                        }
                    else:
                        raise ValueError("No JSON data found in response")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.error(f"Failed to parse analysis response: {str(e)}")
                    return {
                        "success": False,
                        "error": f"Failed to parse analysis: {str(e)}",
                        "raw_response": content
                    }
            else:
                return {
                    "success": False,
                    "error": "No content in response"
                }
        except Exception as e:
            logger.error(f"Error in answer analysis: {str(e)}")
            return {
                "success": False,
                "error": f"Analysis failed: {str(e)}"
            }

    def _extract_question_topics(self, question_text: str) -> List[str]:
        """
        Extract astrological topics from a question using NLP techniques.

        Args:
            question_text: The question text to analyze

        Returns:
            List of extracted topics and their relevance to birth time
        """
        # More sophisticated topic extraction using key astrological concepts
        topic_keywords = {
            # High relevance to birth time factors
            "ascendant": ["ascendant", "rising sign", "lagna", "physical appearance", "first house", "how you appear", "personality", "first impression"],
            "midheaven": ["midheaven", "mc", "career", "public life", "reputation", "tenth house", "profession", "achievement"],
            "house_cusps": ["house cusp", "house boundary", "angular house", "cardinal house"],
            "angular_houses": ["first house", "fourth house", "seventh house", "tenth house", "1st house", "4th house", "7th house", "10th house", "ic", "descendant"],

            # Medium relevance to birth time
            "moon": ["moon", "emotions", "mother", "nurturing", "feelings", "home life", "emotional response"],
            "navamsa": ["navamsa", "d9", "marriage", "spouse", "partnership", "divisional chart"],
            "dasha": ["dasha", "planetary period", "major period", "life timing", "bhukti", "antardasha"],

            # Lower relevance to birth time
            "planets": ["sun", "mercury", "venus", "mars", "jupiter", "saturn", "rahu", "ketu", "planets", "planetary"],
            "aspects": ["aspect", "conjunction", "opposition", "square", "trine", "sextile", "yuti", "drishti"],
            "nakshatras": ["nakshatra", "lunar mansion", "asterism", "pada"]
        }

        # Initialize for NLP analysis
        extracted_topics = []
        question_lower = question_text.lower()

        # Extract major topics based on keyword matching
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in question_lower:
                    if topic not in extracted_topics:
                        extracted_topics.append(topic)
                    break

        # Categorize life events (which provide time markers for rectification)
        life_event_markers = {
            "career": ["job", "career", "profession", "work", "business", "promotion", "fired", "quit", "employment"],
            "relationships": ["marriage", "divorce", "relationship", "partner", "spouse", "romantic", "engagement"],
            "family": ["child", "birth", "pregnancy", "parent", "death", "family", "sibling", "daughter", "son"],
            "education": ["school", "college", "university", "education", "degree", "graduate", "study", "learn"],
            "health": ["health", "illness", "accident", "injury", "hospital", "surgery", "medical", "healing"],
            "travel": ["travel", "journey", "move", "abroad", "foreign", "country", "relocation"],
            "spiritual": ["spiritual", "awakening", "meditation", "insight", "vision", "mystical"]
        }

        # Look for life event markers
        for event, markers in life_event_markers.items():
            for marker in markers:
                if marker in question_lower:
                    event_topic = f"life_event_{event}"
                    if event_topic not in extracted_topics:
                        extracted_topics.append(event_topic)
                    break

        # Look for time-related terms that indicate birth time sensitivity
        time_markers = ["when", "time", "date", "year", "month", "day", "age", "period", "moment", "exact", "specific"]
        for marker in time_markers:
            if marker in question_lower:
                if "time_specific" not in extracted_topics:
                    extracted_topics.append("time_specific")
                break

        # If no topics are found, classify as "general"
        if not extracted_topics:
            extracted_topics.append("general")

        return extracted_topics
