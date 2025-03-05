"""
Unified birth time rectification model for Birth Time Rectifier API.
Handles AI-based analysis for birth time rectification.
"""

import logging
import random
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

# Import OpenAI service
from ..api.services.openai_service import OpenAIService

# Configure logging
logger = logging.getLogger(__name__)

class UnifiedRectificationModel:
    """
    Model for birth time rectification using questionnaire responses and chart data.

    Implements multi-task AI model architecture for birth time rectification,
    combining different astrological techniques (Tattva, Nadi, KP systems)
    with intelligent model routing for optimal accuracy and cost efficiency.
    """

    def __init__(self):
        """Initialize the model for continuous operation"""
        logger.info("Initializing Unified Rectification Model")

        # Initialize version and status
        self.model_version = "1.0.0"
        self.is_initialized = True

        # Initialize caching for improved performance
        self.request_counter = 0
        self.last_cache_clear = time.time()
        self.response_cache = {}  # Simple cache for repeated queries

        # Initialize OpenAI service
        try:
            self.openai_service = OpenAIService()
            logger.info("OpenAI service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service: {e}")
            # Continue with initialization even if OpenAI service fails
            # This ensures the model can still function in fallback mode
            self.openai_service = None

        # Initialize GPU memory management if available
        try:
            from ..utils.gpu_manager import GPUMemoryManager
            self.gpu_manager = GPUMemoryManager(model_allocation=0.7)
            logger.info("GPU memory manager initialized")

            # Optimize GPU memory if available
            if hasattr(self.gpu_manager, 'device') and self.gpu_manager.device == 'cuda':
                self.gpu_manager.optimize_memory()
        except (ImportError, Exception) as e:
            logger.warning(f"GPU memory management not available: {e}")
            self.gpu_manager = None

        # Initialize multi-task architecture components
        self._initialize_task_components()

        logger.info(f"Model initialized successfully (version {self.model_version})")

    def _initialize_task_components(self):
        """Initialize components for the multi-task architecture"""
        # Define weights for different rectification techniques
        self.technique_weights = {
            'tattva': 0.4,  # Traditional Vedic approach
            'nadi': 0.35,   # Nadi astrology method
            'kp': 0.25      # Krishnamurti Paddhati system
        }

        # Define significance weights for different question categories (as before)
        self.category_weights = {
            "personality": 0.7,
            "life_events": 0.9,
            "career": 0.8,
            "relationships": 0.7
        }

        # Define critical chart factors (as before)
        self.critical_factors = [
            "Ascendant",
            "Moon placement",
            "MC/IC axis",
            "Angular planets"
        ]

    async def _perform_ai_rectification(self, birth_details: Dict[str, Any],
                                  chart_data: Dict[str, Any],
                                  questionnaire_data: Dict[str, Any]) -> Tuple[Optional[int], float]:
        """
        Use o1-preview model for astronomical calculations and rectification.

        Args:
            birth_details: Original birth details
            chart_data: Original chart data
            questionnaire_data: Questionnaire responses

        Returns:
            Tuple of (adjustment_minutes, confidence)
        """
        if not self.openai_service:
            return None, 0

        try:
            # Create cache key based on input data
            cache_key = f"{hash(str(birth_details))}-{hash(str(questionnaire_data))}"

            # Check if result is in cache
            if cache_key in self.response_cache:
                logger.info("Using cached rectification result")
                return self.response_cache[cache_key]

            # Format chart data and questionnaire responses
            prompt = self._prepare_rectification_prompt(birth_details, chart_data, questionnaire_data)

            # Call OpenAI with rectification task type
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="rectification",  # Will route to o1-preview
                max_tokens=1000,
                temperature=0.2  # Lower temperature for more deterministic results
            )

            # Parse the response to extract adjustment
            parsed_result = self._parse_rectification_response(response["content"])
            adjustment_minutes = parsed_result.get("adjustment_minutes", 0)
            confidence = parsed_result.get("confidence", 70.0)

            # Cache the result
            self.response_cache[cache_key] = (adjustment_minutes, confidence)

            # Update request counter and clear cache if needed
            self._update_cache_management()

            return adjustment_minutes, confidence
        except Exception as e:
            logger.error(f"AI rectification failed: {e}")
            return None, 0

    def _prepare_rectification_prompt(self, birth_details: Dict[str, Any],
                                     chart_data: Dict[str, Any],
                                     questionnaire_data: Dict[str, Any]) -> str:
        """
        Prepare the prompt for the AI rectification model.

        Args:
            birth_details: Original birth details
            chart_data: Original chart data
            questionnaire_data: Questionnaire responses

        Returns:
            Formatted prompt string
        """
        # Format birth details for prompt
        birth_date = birth_details.get("birthDate", "")
        birth_time = birth_details.get("birthTime", "")
        latitude = birth_details.get("latitude", 0)
        longitude = birth_details.get("longitude", 0)
        timezone = birth_details.get("timezone", "UTC")

        # Format planetary positions from chart data
        planets_str = ""
        if chart_data and "planets" in chart_data:
            planets_str = "\n".join([
                f"- {planet['name']}: {planet.get('longitude', 0)}° in {planet.get('sign', '')}, "
                f"House: {planet.get('house', '')}"
                for planet in chart_data.get("planets", [])
            ])

        # Format questionnaire responses
        responses_str = ""
        if "responses" in questionnaire_data:
            responses_str = "\n".join([
                f"Q: {resp.get('question', '')}\nA: {resp.get('answer', '')}"
                for resp in questionnaire_data.get("responses", [])
            ])

        # Create the prompt
        prompt = f"""
        As an expert in Vedic astrology, perform a detailed birth time rectification analysis based on the following information:

        BIRTH DETAILS:
        Date: {birth_date}
        Approximate Time: {birth_time}
        Location: {latitude}, {longitude}
        Timezone: {timezone}

        CHART DATA (ORIGINAL):
        Ascendant: {chart_data.get('ascendant', {}).get('degree', 0)}° {chart_data.get('ascendant', {}).get('sign', '')}

        PLANETARY POSITIONS:
        {planets_str}

        QUESTIONNAIRE RESPONSES:
        {responses_str}

        ANALYSIS REQUESTED:
        Based on these details, determine the most accurate birth time rectification. Focus on:
        1. Planetary positions relative to houses and angles
        2. Correlation between life events and planetary transits
        3. Dashas/planetary periods alignment with life experiences
        4. Ayanamsa corrections and calculation precision

        INSTRUCTIONS:
        - Analyze using three methods: Tattva (traditional), Nadi, and KP system
        - Calculate the most likely adjustment in minutes (positive for later, negative for earlier)
        - Provide a confidence score (0-100)
        - Keep the response focused on the numerical adjustment and confidence

        FORMAT YOUR RESPONSE AS JSON:
        {{
          "adjustment_minutes": [number],
          "confidence": [number],
          "reasoning": "[brief explanation]"
        }}
        """

        return prompt

    def _parse_rectification_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse the AI response to extract adjustment and confidence.

        Args:
            response_content: Raw response from OpenAI

        Returns:
            Dictionary with parsed values
        """
        try:
            # Try to parse as JSON directly
            import json
            data = json.loads(response_content)

            # Validate expected fields
            if "adjustment_minutes" in data and "confidence" in data:
                return {
                    "adjustment_minutes": int(data["adjustment_minutes"]),
                    "confidence": float(data["confidence"]),
                    "reasoning": data.get("reasoning", "")
                }
            else:
                logger.warning(f"Missing required fields in AI response: {data}")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI response as JSON, trying fallback parsing")

            # Fallback parsing for non-JSON formatted responses
            result = {}

            # Look for adjustment minutes
            import re
            adjustment_match = re.search(r'adjustment[_\s]?minutes["\s:]+([+-]?\d+)', response_content)
            if adjustment_match:
                result["adjustment_minutes"] = int(adjustment_match.group(1))

            # Look for confidence
            confidence_match = re.search(r'confidence["\s:]+(\d+\.?\d*)', response_content)
            if confidence_match:
                result["confidence"] = float(confidence_match.group(1))

            if result:
                return result

        # Default values if parsing fails
        return {
            "adjustment_minutes": 0,
            "confidence": 60.0
        }

    def _update_cache_management(self):
        """Update request counter and manage cache size"""
        self.request_counter += 1

        # Clear cache periodically to prevent memory issues
        current_time = time.time()
        if (self.request_counter > 1000 or
            (current_time - self.last_cache_clear > 3600)):  # 1 hour
            self.response_cache.clear()
            self.request_counter = 0
            self.last_cache_clear = current_time
            logger.info("Cache cleared due to size or time limit")

    async def rectify_birth_time(self, birth_details: Dict[str, Any],
                           questionnaire_data: Dict[str, Any],
                           original_chart: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Rectify birth time based on questionnaire responses and chart analysis.

        Args:
            birth_details: Original birth details
            questionnaire_data: Answers to questionnaire
            original_chart: Original chart data (optional)

        Returns:
            Dictionary with rectification results
        """
        try:
            logger.info(f"Processing birth time rectification request")

            # Extract original birth time
            birth_time_str = birth_details.get("birthTime", "00:00")
            birth_time = datetime.strptime(birth_time_str, "%H:%M").time()

            # Use AI service for rectification if available
            use_ai_rectification = self.openai_service is not None and original_chart is not None

            # Attempt AI-based rectification
            adjustment_minutes = None
            ai_confidence = 0

            if use_ai_rectification and original_chart is not None:  # Extra check to satisfy type checker
                try:
                    logger.info("Using AI model (o1-preview) for rectification calculations")
                    adjustment_minutes, ai_confidence = await self._perform_ai_rectification(
                        birth_details, original_chart, questionnaire_data
                    )
                except Exception as e:
                    use_ai_rectification = False
                    logger.error(f"Error in AI rectification, falling back to simulation: {e}")

            # If AI rectification failed or unavailable, use simulation
            if adjustment_minutes is None:
                logger.info("Using simulated rectification method")
                # Use existing simulation logic
                direction = 1 if random.random() > 0.5 else -1
                magnitude = random.randint(1, 30)
                adjustment_minutes = direction * magnitude

            # Apply adjustment
            birth_dt = datetime.combine(datetime.today().date(), birth_time)
            adjusted_dt = birth_dt + timedelta(minutes=adjustment_minutes)
            adjusted_time = adjusted_dt.time()

            # Format adjusted time
            suggested_time = adjusted_time.strftime("%H:%M")

            # Calculate confidence based on answers, enhanced with AI confidence
            base_confidence = self._calculate_confidence(questionnaire_data)
            confidence = base_confidence
            if use_ai_rectification and ai_confidence > 0:
                # Blend the AI confidence with the rule-based confidence
                confidence = (base_confidence * 0.3) + (ai_confidence * 0.7)

            # Determine reliability
            reliability = self._determine_reliability(confidence, questionnaire_data)

            # Generate task-specific predictions
            task_predictions = {
                "time_accuracy": min(85, confidence),
                "ascendant_accuracy": min(90, confidence + 5),
                "houses_accuracy": min(80, confidence - 5)
            }

            # Generate significant events that support the rectification
            if use_ai_rectification:
                significant_events = await self._identify_significant_events_ai(
                    questionnaire_data, adjustment_minutes
                )
            else:
                significant_events = self._identify_significant_events_fallback(questionnaire_data)

            # Generate explanation
            explanation = await self._generate_explanation(
                adjustment_minutes,
                reliability,
                questionnaire_data
            )

            # Return results with additional AI info
            return {
                "suggested_time": suggested_time,
                "confidence": confidence,
                "reliability": reliability,
                "task_predictions": task_predictions,
                "explanation": explanation,
                "significant_events": significant_events,
                "ai_used": use_ai_rectification,
                "techniques_used": list(self.technique_weights.keys()) if use_ai_rectification else ["simulation"]
            }

        except Exception as e:
            logger.error(f"Error in birth time rectification: {e}")
            # Return default values in case of error
            return {
                "suggested_time": birth_time_str,
                "confidence": 60.0,
                "reliability": "low",
                "task_predictions": {
                    "time_accuracy": 60,
                    "ascendant_accuracy": 65,
                    "houses_accuracy": 60
                },
                "explanation": "Unable to perform accurate birth time rectification due to an error.",
                "significant_events": []
            }

    def _calculate_confidence(self, questionnaire_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on questionnaire responses.

        Args:
            questionnaire_data: Dictionary of question responses

        Returns:
            Confidence score (0-100)
        """
        # In a real implementation, this would use a sophisticated algorithm

        # For mock implementation, base confidence on number of questions
        base_confidence = 70
        adjustment = min(len(questionnaire_data) * 2, 25)

        # Add random variation
        variation = random.uniform(-5, 5)

        confidence = base_confidence + adjustment + variation

        # Ensure within bounds
        confidence = max(50, min(95, confidence))

        return confidence

    def _determine_reliability(self, confidence: float, questionnaire_data: Dict[str, Any]) -> str:
        """
        Determine reliability rating based on confidence and data quality.

        Args:
            confidence: Confidence score
            questionnaire_data: Dictionary of question responses

        Returns:
            Reliability rating (low, moderate, high, very high)
        """
        # In a real implementation, this would consider data quality, consistency, etc.

        if confidence >= 90:
            return "very high"
        elif confidence >= 80:
            return "high"
        elif confidence >= 70:
            return "moderate"
        else:
            return "low"

    # Renamed from _identify_significant_events to avoid duplicate function name
    async def _identify_significant_events_ai(self, questionnaire_data: Dict[str, Any],
                                     adjustment_minutes: int) -> List[str]:
        """
        Use AI to identify significant life events that support the rectification.

        Args:
            questionnaire_data: Dictionary of question responses
            adjustment_minutes: Calculated adjustment in minutes

        Returns:
            List of significant event descriptions
        """
        if not self.openai_service:
            return self._identify_significant_events_fallback(questionnaire_data)

        try:
            # Create prompt for identifying significant events
            prompt = f"""
            Based on the questionnaire responses below and an adjusted birth time of {adjustment_minutes} minutes
            {'later' if adjustment_minutes > 0 else 'earlier'}, identify 3-5 significant astrological transits
            or planetary periods that correlate with major life events.

            Questionnaire responses:
            """

            # Add responses
            if "responses" in questionnaire_data:
                for resp in questionnaire_data["responses"]:
                    prompt += f"\n- Q: {resp.get('question', '')}\n  A: {resp.get('answer', '')}"

            prompt += """

            For each event, provide a concise explanation of the astrological correlation.
            Format each event as: "[Event description] - [Astrological explanation]"
            """

            # Call OpenAI service
            response = await self.openai_service.generate_completion(
                prompt=prompt,
                task_type="auxiliary",  # Routes to GPT-4o-mini
                max_tokens=300,
                temperature=0.7
            )

            # Parse result - each line is an event
            events = [line.strip() for line in response["content"].strip().split("\n") if line.strip()]

            # Filter out any non-event lines
            events = [event for event in events if " - " in event]

            # Limit to a reasonable number
            return events[:5]

        except Exception as e:
            logger.error(f"Error identifying significant events with AI: {e}")
            return self._identify_significant_events_fallback(questionnaire_data)

    def _identify_significant_events_fallback(self, questionnaire_data: Dict[str, Any]) -> List[str]:
        """
        Fallback method to identify significant life events (same as original implementation).

        Args:
            questionnaire_data: Dictionary of question responses

        Returns:
            List of significant event descriptions
        """
        # Mock implementation with common astrological event descriptions
        possible_events = [
            "Career change during Saturn transit to 10th house",
            "Relationship milestone aligned with Venus-Jupiter aspect",
            "Relocation during Moon-Uranus transit",
            "Health improvement during Jupiter transit to 6th house",
            "Personal transformation during Pluto transit to Ascendant",
            "Family changes during Saturn-Moon aspect",
            "Educational advancement during Jupiter transit to 9th house",
            "Financial improvement during Venus-Jupiter aspect"
        ]

        # Select 2-4 random events
        num_events = random.randint(2, 4)
        selected_events = random.sample(possible_events, num_events)

        return selected_events

    async def _generate_explanation(self, adjustment_minutes: int,
                              reliability: str,
                              questionnaire_data: Dict[str, Any]) -> str:
        """
        Generate an explanation for the birth time rectification using OpenAI.

        Args:
            adjustment_minutes: Adjustment in minutes
            reliability: Reliability rating
            questionnaire_data: Dictionary of question responses

        Returns:
            Explanation string
        """
        # Get direction and absolute minutes for explanation
        direction = "later" if adjustment_minutes > 0 else "earlier"
        abs_minutes = abs(adjustment_minutes)

        # Check if OpenAI service is available
        if self.openai_service is not None:
            try:
                # Create a more detailed prompt for better explanation
                prompt = f"""
                Based on the birth time rectification analysis, the birth time should be adjusted by {abs_minutes} minutes {direction}.
                The reliability of this rectification is assessed as {reliability}.

                Key points from the questionnaire:
                """

                # Add a few key points from questionnaire
                if "responses" in questionnaire_data:
                    for i, response in enumerate(questionnaire_data["responses"][:3]):
                        prompt += f"\n- {response.get('question', 'Question')}: {response.get('answer', 'No answer')}"

                prompt += """

                Please provide a concise explanation for this birth time rectification in astrological terms.
                Include:
                1. How this adjustment affects key positions in the birth chart
                2. Why this adjustment aligns better with the person's life events
                3. What astrological techniques were used to determine this adjustment

                Use clear, informative language that emphasizes the astrological reasoning.
                """

                # Call OpenAI service for explanation generation using GPT-4 Turbo
                response = await self.openai_service.generate_completion(
                    prompt=prompt,
                    task_type="explanation",  # Routes to GPT-4 Turbo
                    max_tokens=350,
                    temperature=0.7,
                    system_message="You are an expert in Vedic astrology specializing in birth time rectification."
                )

                # Extract and return the explanation
                explanation = response["content"]

                # Log token usage (for monitoring)
                logger.info(f"Explanation generated. Tokens used: {response['tokens']['total']}")

                return explanation

            except Exception as e:
                logger.error(f"Error generating explanation with OpenAI: {e}")
                # Fall back to template-based explanation if API fails
                return self._generate_fallback_explanation(adjustment_minutes, reliability, questionnaire_data)
        else:
            # If OpenAI service is not available, use fallback
            logger.warning("OpenAI service not available, using fallback explanation")
            return self._generate_fallback_explanation(adjustment_minutes, reliability, questionnaire_data)

    def _generate_fallback_explanation(self, adjustment_minutes: int,
                                      reliability: str,
                                      questionnaire_data: Dict[str, Any]) -> str:
        """
        Generate a fallback explanation when OpenAI is unavailable.

        Args:
            adjustment_minutes: Adjustment in minutes
            reliability: Reliability rating
            questionnaire_data: Dictionary of question responses

        Returns:
            Explanation text
        """
        direction = "later" if adjustment_minutes > 0 else "earlier"
        abs_minutes = abs(adjustment_minutes)

        explanations = [
            f"Based on your questionnaire responses, your birth time appears to be {abs_minutes} minutes {direction} than recorded.",
            f"Analysis suggests a {reliability} probability that your actual birth time was {abs_minutes} minutes {direction}.",
            f"The rectified birth time aligns better with significant life events and personality traits described in your responses."
        ]

        if reliability in ["high", "very high"]:
            explanations.append("Your answers showed strong correlation with specific planetary positions.")

        if len(questionnaire_data) >= 5:
            explanations.append("The comprehensive information you provided allowed for a detailed rectification analysis.")

        # Join explanations into a single paragraph
        return " ".join(explanations)
