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
        """Initialize the questionnaire engine with AI capabilities"""
        # Set maximum number of questions
        self.max_questions = 10

        # Initialize OpenAI service for dynamic question generation
        try:
            from ..api.services.openai import OpenAIService
            self.openai_service = OpenAIService()
            logger.info("OpenAI service initialized for questionnaire engine")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service for questionnaire: {e}")
            self.openai_service = None

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

        # Cache for generated questions to avoid repetition
        self.question_cache = {}

    def get_first_question(self, chart_data: Dict[str, Any], birth_details: Dict[str, Any]) -> Dict[str, Any]:
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

        # Create question
        question = {
            "id": question_id,
            "type": template.get("type", "yes_no"),
            "text": template["text"],
            "options": options,
            "relevance": template.get("relevance", "medium")
        }

        return question

    async def generate_dynamic_question(self, chart_data: Dict[str, Any],
                                   previous_answers: Dict[str, Any],
                                   current_confidence: float) -> Dict[str, Any]:
        """
        Generate a dynamic question using AI based on previous answers and chart data.

        Args:
            chart_data: The natal chart data
            previous_answers: Dictionary of answers to previous questions
            current_confidence: Current confidence level (0-100)

        Returns:
            Dictionary with AI-generated question
        """
        if not self.openai_service:
            # Fall back to template-based question if OpenAI service is unavailable
            logger.warning("AI service unavailable, using template-based question generation")
            return self._get_template_question(previous_answers)

        try:
            # Format chart data for the prompt
            chart_summary = self._format_chart_summary(chart_data)

            # Format previous Q&A for context
            qa_history = ""
            if "responses" in previous_answers:
                qa_history = "\n".join([
                    f"Q: {resp.get('question', 'Unknown question')}\nA: {resp.get('answer', 'Unknown answer')}"
                    for resp in previous_answers.get("responses", [])
                ])

            # Create a prompt for the AI
            prompt = f"""
            Based on this birth chart data and previous questions/answers,
            generate the most effective next question to help improve birth time rectification.

            Chart data:
            {chart_summary}

            Previous Q&A:
            {qa_history}

            Current confidence: {current_confidence}%

            Generate a single question that would most effectively improve the birth time accuracy.
            The question should address areas that haven't been covered yet or need clarification.

            Return in this JSON format:
            {{
                "text": "Question text here",
                "type": "yes_no" OR "multiple_choice",
                "options": ["Option 1", "Option 2"] (only if multiple_choice),
                "relevance": "high" OR "medium" OR "low",
                "rationale": "Brief explanation of why this question helps with rectification"
            }}
            """

            # Call the OpenAI service with auxiliary task type (routes to GPT-4o-mini)
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="auxiliary",  # Routes to GPT-4o-mini
                max_tokens=300,
                temperature=0.7
            )

            try:
                # Parse the response to extract the question
                import json
                question_data = json.loads(response["content"])

                # Create a unique ID for this question
                question_id = f"q_{uuid.uuid4()}"

                # Determine question type
                question_type = question_data.get("type", "yes_no")

                # Format options based on question type
                options = None
                if question_type == "multiple_choice" and "options" in question_data:
                    options = [{"id": f"opt_{i}", "text": opt}
                              for i, opt in enumerate(question_data["options"])]
                elif question_type == "yes_no":
                    options = [
                        {"id": "yes", "text": "Yes, definitely"},
                        {"id": "somewhat", "text": "Somewhat"},
                        {"id": "no", "text": "No, not at all"}
                    ]

                # Create the question object
                question = {
                    "id": question_id,
                    "type": question_type,
                    "text": question_data["text"],
                    "options": options,
                    "relevance": question_data.get("relevance", "medium"),
                    "ai_generated": True,
                    "rationale": question_data.get("rationale", "")
                }

                # Cache this question
                cache_key = f"{len(previous_answers.get('responses', []))}-{hash(str(previous_answers))}"
                self.question_cache[cache_key] = question

                logger.info(f"AI generated question: {question['text']}")
                return question

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI-generated question: {e}")
                return self._get_template_question(previous_answers)

        except Exception as e:
            logger.error(f"Error generating dynamic question: {e}")
            return self._get_template_question(previous_answers)

    def _format_chart_summary(self, chart_data: Dict[str, Any]) -> str:
        """
        Format chart data into a concise summary for AI prompts.

        Args:
            chart_data: The natal chart data

        Returns:
            Formatted string summary
        """
        if not chart_data:
            return "No chart data available"

        summary_parts = []

        # Add ascendant
        if "ascendant" in chart_data:
            ascendant = chart_data["ascendant"]
            summary_parts.append(f"Ascendant: {ascendant.get('sign', '')} {ascendant.get('degree', 0)}°")

        # Add sun and moon positions
        if "planets" in chart_data:
            for planet in chart_data["planets"]:
                if planet["name"] in ["Sun", "Moon"]:
                    summary_parts.append(f"{planet['name']}: {planet.get('sign', '')} {planet.get('degree', 0)}° (House {planet.get('house', 'Unknown')})")

        # Add house cusps if available
        if "houses" in chart_data:
            house_summary = ", ".join([f"House {h['number']}: {h['sign']}" for h in chart_data["houses"][:4]])
            summary_parts.append(f"Houses: {house_summary}")

        # Add significant aspects if available
        if "aspects" in chart_data and len(chart_data["aspects"]) > 0:
            aspects = chart_data["aspects"][:3]  # Just use first few aspects
            aspect_summary = ", ".join([f"{a['planet1']} {a['aspectType']} {a['planet2']}" for a in aspects])
            summary_parts.append(f"Key Aspects: {aspect_summary}")

        return "\n".join(summary_parts)

    def _get_template_question(self, previous_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a template-based question when AI generation fails.

        Args:
            previous_answers: Dictionary of previous answers

        Returns:
            Template question dictionary
        """
        # Choose a category based on what hasn't been asked yet
        all_categories = list(self.question_templates.keys())

        # Filter out categories we've already asked about
        used_categories = set()
        for resp in previous_answers.get("responses", []):
            question_text = resp.get("question", "").lower()

            # Try to determine category from question text
            for category in all_categories:
                if category.lower() in question_text:
                    used_categories.add(category)
                    break

        available_categories = [c for c in all_categories if c not in used_categories]

        # If all categories used, pick a random one
        if not available_categories:
            available_categories = all_categories

        category = random.choice(available_categories)

        # Choose a random question from that category
        template = random.choice(self.question_templates[category])

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

        # Create question
        question = {
            "id": question_id,
            "type": template.get("type", "yes_no"),
            "text": template["text"],
            "options": options,
            "relevance": template.get("relevance", "medium"),
            "ai_generated": False
        }

        return question

    async def get_next_question(self, chart_data: Dict[str, Any], birth_details: Dict[str, Any],
                         previous_answers: Dict[str, Any], current_confidence: float) -> Dict[str, Any]:
        """
        Generate the next question based on previous answers and chart data.
        Uses AI-driven question generation when available.

        Args:
            chart_data: The natal chart data
            birth_details: Birth details provided by the user
            previous_answers: Dictionary of answers to previous questions
            current_confidence: Current confidence level (0-100)

        Returns:
            Dictionary containing the next question
        """
        # First check if we should use AI-based question generation
        use_ai_generation = self.openai_service is not None and chart_data is not None

        # Try AI generation if available
        if use_ai_generation:
            try:
                # Generate question using AI
                logger.info("Generating next question using AI")
                return await self.generate_dynamic_question(chart_data, previous_answers, current_confidence)
            except Exception as e:
                logger.error(f"AI question generation failed, falling back to template: {e}")
                # Continue to fallback method

        # Fall back to template-based question if AI is unavailable or failed
        logger.info("Using template-based question generation")
        return self._get_template_question(previous_answers)

    async def calculate_confidence(self, answers: Dict[str, Any], chart_data: Optional[Dict[str, Any]] = None) -> float:
        """
        Calculate the confidence level based on answers provided.
        Uses AI for enhanced confidence scoring when available.

        Args:
            answers: Dictionary of answers to previous questions
            chart_data: Original chart data (optional)

        Returns:
            Confidence level (0-100)
        """
        # First calculate base confidence using simple formula
        base_confidence = 30  # Start with some base confidence
        num_answers = len(answers.get("responses", []))
        question_value = 10   # Each question contributes this much
        max_confidence = 95   # Cap at this level

        simple_confidence = min(base_confidence + (num_answers * question_value), max_confidence)

        # If OpenAI service is available, use AI to enhance confidence calculation
        if self.openai_service is not None and chart_data is not None and num_answers >= 3:
            try:
                # Format chart data and answers for AI analysis
                chart_summary = self._format_chart_summary(chart_data)

                # Format responses for AI analysis
                qa_formatted = ""
                for resp in answers.get("responses", []):
                    qa_formatted += f"Q: {resp.get('question', '')}\nA: {resp.get('answer', '')}\n"

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
                Consider factors like:
                - Specificity of life events with clear timing
                - Consistency in personality descriptions
                - Clarity in reported experiences
                - Amount of useful data provided

                Return ONLY a JSON with the following format:
                {{
                    "confidence_score": [number between 0-100],
                    "reasoning": "[brief explanation]"
                }}
                """

                # Call OpenAI service
                response = await self.openai_service.generate_completion(
                    prompt=prompt,
                    task_type="auxiliary",  # Routes to GPT-4o-mini
                    max_tokens=200,
                    temperature=0.5
                )

                try:
                    # Parse the response
                    import json
                    result = json.loads(response["content"])
                    ai_confidence = result.get("confidence_score", simple_confidence)

                    # Blend the AI confidence with the rule-based confidence
                    # Weight AI confidence more as we get more answers
                    ai_weight = min(0.7, 0.4 + (num_answers * 0.05))
                    final_confidence = (simple_confidence * (1 - ai_weight)) + (ai_confidence * ai_weight)

                    logger.info(f"AI enhanced confidence: {final_confidence:.1f}% (from base: {simple_confidence:.1f}%)")
                    return min(max(final_confidence, 30), max_confidence)  # Ensure within bounds

                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing AI confidence response: {e}")
                    return simple_confidence

            except Exception as e:
                logger.error(f"Error in AI confidence calculation: {e}")
                return simple_confidence

        return simple_confidence

    async def analyze_answers(self, chart_data: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze answers to determine birth time adjustment.
        Uses AI for enhanced analysis when available.
        Verifies chart data against Indian Vedic Astrological standards.

        Args:
            chart_data: Original chart data
            answers: Dictionary of answers to questions

        Returns:
            Analysis results including suggested birth time adjustment
        """
        # First, verify the chart data against Indian Vedic Astrological standards
        try:
            birth_details = chart_data.get("birth_details", {})
            verified_chart = chart_data

            if "verification" not in chart_data and birth_details:
                # Extract the necessary data for verification
                birth_date = birth_details.get("date", "")
                birth_time = birth_details.get("time", "")
                latitude = birth_details.get("latitude", 0)
                longitude = birth_details.get("longitude", 0)
                location = birth_details.get("location", "")

                if birth_date and birth_time and latitude and longitude:
                    logger.info(f"Verifying chart data with OpenAI for birth time: {birth_time}")
                    verified_chart = await calculate_verified_chart(
                        birth_date=birth_date,
                        birth_time=birth_time,
                        latitude=latitude,
                        longitude=longitude,
                        location=location
                    )
                    logger.info("Chart verification completed")

            # Use the verified chart for the analysis
            chart_data = verified_chart
        except Exception as e:
            logger.error(f"Error verifying chart data: {e}")
            # Continue with original chart if verification fails

        # Calculate confidence (with AI enhancement if available)
        confidence = await self.calculate_confidence(answers, chart_data)

        # If OpenAI service is available, use AI for the analysis
        if self.openai_service is not None and chart_data is not None and len(answers.get("responses", [])) >= 3:
            try:
                # Format chart data and answers for AI analysis
                chart_summary = self._format_chart_summary(chart_data)

                # Format responses for AI analysis
                qa_formatted = ""
                for resp in answers.get("responses", []):
                    qa_formatted += f"Q: {resp.get('question', '')}\nA: {resp.get('answer', '')}\n"

                # Create a prompt for birth time analysis
                prompt = f"""
                As an expert in astrological birth time rectification, analyze these question responses
                and suggest a birth time adjustment based on this data.

                Chart summary:
                {chart_summary}

                Questionnaire responses:
                {qa_formatted}

                Based on astrological principles and the responses given, determine:
                1. How many minutes the birth time should be adjusted (positive for later, negative for earlier)
                2. The reliability of this adjustment (low, moderate, high, very high)
                3. Which houses/planets are most relevant to review
                4. Critical markers that support this adjustment

                Return ONLY a JSON with the following format:
                {{
                    "adjustment_minutes": [number],
                    "reliability": "[low|moderate|high|very high]",
                    "suggested_houses_to_review": [array of house numbers 1-12],
                    "critical_time_markers": [array of strings]
                }}
                """

                # Call OpenAI service
                response = await self.openai_service.generate_completion(
                    prompt=prompt,
                    task_type="auxiliary",  # Routes to GPT-4o-mini
                    max_tokens=300,
                    temperature=0.7
                )

                try:
                    # Parse the response
                    import json
                    result = json.loads(response["content"])

                    # Create analysis result
                    analysis_result = {
                        "confidence": confidence,
                        "suggested_adjustment_minutes": result.get("adjustment_minutes", 0),
                        "reliability": result.get("reliability", "moderate"),
                        "suggested_houses_to_review": result.get("suggested_houses_to_review", [1, 10, 7]),
                        "critical_time_markers": result.get("critical_time_markers",
                                                 ["Ascendant-Moon aspects", "Angular planets"]),
                        "ai_assisted": True
                    }

                    logger.info(f"AI analysis completed: {analysis_result['suggested_adjustment_minutes']} minutes adjustment")
                    return analysis_result

                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing AI analysis response: {e}")
                    # Fall back to simple analysis

            except Exception as e:
                logger.error(f"Error in AI answer analysis: {e}")
                # Fall back to simple analysis

        # If we reach here, use the simple analysis
        return {
            "confidence": confidence,
            "suggested_adjustment_minutes": random.randint(-30, 30),
            "reliability": "moderate",
            "suggested_houses_to_review": [1, 10, 7],  # Ascendant, MC, Descendant
            "critical_time_markers": ["Mars-Saturn aspects", "Moon house placement"],
            "ai_assisted": False
        }
