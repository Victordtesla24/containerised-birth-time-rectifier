"""
Questionnaire service for Birth Time Rectifier API.

This service handles the generation and processing of questions for birth time rectification.
"""

import logging
import asyncio
import json
import uuid
import random
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple, Union, TypedDict
import re
import os
import traceback

# logger initialization must come before any code that uses it
logger = logging.getLogger(__name__)

try:
    from timezonefinder import TimezoneFinder
    TIMEZONE_FINDER_AVAILABLE = True
except ImportError:
    TIMEZONE_FINDER_AVAILABLE = False

from ai_service.api.services.openai import get_openai_service
from ai_service.api.services.openai.service import OpenAIService
from ai_service.api.services.session_service import get_session_store
from ai_service.core.config import settings
from ai_service.services import get_chart_service

# Import the shared DateTimeEncoder
from ai_service.utils.json_encoder import DateTimeEncoder

# Import DynamicQuestionnaireService here to make it available through this module
from ai_service.api.services.dynamic_questionnaire_service import DynamicQuestionnaireService

# Import modularized components
from ai_service.api.services.questionnaire_service_types import (
    QUESTION_TYPES,
    Question,
    QuestionOption
)

from ai_service.api.services.questionnaire_service_chart_calculator import (
    chart_calculator
)

from ai_service.api.services.questionnaire_service_chart_calculations import (
    _calculate_significant_periods,
    _calculate_birth_chart,
    _get_house_data,
    _get_angle_data,
    _calculate_chart_data,
    _calculate_ascendant_changes,
    _format_chart_data_for_prompt
)

from ai_service.api.services.questionnaire_service_time_indicators import (
    _extract_birth_time_indicators,
    _time_of_day_to_range,
    _extract_pattern_from_text
)

from ai_service.api.services.questionnaire_service_utilities import (
    _parse_text_response,
    _extract_json_from_content,
    _enhance_astrological_analysis,
    _assess_time_precision
)

from ai_service.api.services.questionnaire_service_analysis import (
    submit_answer,
    _check_for_contradictions,
    _detect_contradiction,
    _calculate_similarity,
    _extract_key_insights,
    _perform_astrological_analysis
)

from ai_service.api.services.questionnaire_service_generation import (
    get_initial_questions,
    _generate_template_questions,
    generate_next_question,
    _generate_astrologically_relevant_question,
    _generate_fallback_question,
    QUESTION_TEMPLATES
)

from ai_service.api.services.questionnaire_service_completion import (
    complete_questionnaire,
    _perform_comprehensive_analysis,
    _generate_astrological_report,
    _describe_confidence_level,
    _calculate_time_adjustment,
    _determine_birth_time_range,
    _extract_key_astrological_factors,
    _calculate_rectification_confidence,
    _categorize_responses
)

class QuestionnaireService:
    """
    Service for managing birth time rectification questionnaires.

    This service handles the generation, processing, and analysis of questions
    used for birth time rectification.
    """

    def __init__(self, openai_service: Optional[OpenAIService] = None):
        """
        Initialize the questionnaire service.

        Args:
            openai_service: Optional OpenAI service for AI-powered question generation
        """
        self.openai_service = openai_service
        self.session_store = get_session_store()

        logger.info("QuestionnaireService initialized")

    # Import methods from modularized components
    get_initial_questions = get_initial_questions
    generate_next_question = generate_next_question
    submit_answer = submit_answer
    complete_questionnaire = complete_questionnaire

    # Import private methods
    _generate_template_questions = _generate_template_questions
    _generate_astrologically_relevant_question = _generate_astrologically_relevant_question
    _generate_fallback_question = _generate_fallback_question
    _check_for_contradictions = _check_for_contradictions
    _detect_contradiction = _detect_contradiction
    _calculate_similarity = _calculate_similarity
    _extract_key_insights = _extract_key_insights
    _perform_astrological_analysis = _perform_astrological_analysis
    _parse_text_response = _parse_text_response
    _extract_birth_time_indicators = _extract_birth_time_indicators
    _time_of_day_to_range = _time_of_day_to_range
    _extract_pattern_from_text = _extract_pattern_from_text
    _perform_comprehensive_analysis = _perform_comprehensive_analysis
    _generate_astrological_report = _generate_astrological_report
    _describe_confidence_level = _describe_confidence_level
    _calculate_time_adjustment = _calculate_time_adjustment
    _determine_birth_time_range = _determine_birth_time_range
    _extract_key_astrological_factors = _extract_key_astrological_factors
    _calculate_rectification_confidence = _calculate_rectification_confidence
    _categorize_responses = _categorize_responses
    _extract_json_from_content = _extract_json_from_content
    _enhance_astrological_analysis = _enhance_astrological_analysis
    _assess_time_precision = _assess_time_precision
    _calculate_significant_periods = _calculate_significant_periods
    _calculate_birth_chart = _calculate_birth_chart
    _get_house_data = _get_house_data
    _get_angle_data = _get_angle_data
    _calculate_chart_data = _calculate_chart_data
    _calculate_ascendant_changes = _calculate_ascendant_changes
    _format_chart_data_for_prompt = _format_chart_data_for_prompt

    # Add a fallback method for _fallback_comprehensive_analysis that wasn't specifically modularized
    def _fallback_comprehensive_analysis(
        self,
        responses: List[Dict[str, Any]],
        birth_details: Dict[str, Any],
        birth_time_indicators: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Fallback method for comprehensive analysis when OpenAI is not available.

        Args:
            responses: List of question-answer pairs
            birth_details: Dictionary with birth details
            birth_time_indicators: Optional list of extracted birth time indicators

        Returns:
            Dictionary with comprehensive analysis
        """
        # Create a simple analysis based on available data
        analysis = {
            "birth_time_range": {
                "start": "00:00",
                "end": "23:59",
                "most_likely_time": birth_details.get("birth_time", "12:00")
            },
            "time_adjustment": {
                "minutes": 0,
                "direction": "none",
                "explanation": "No significant time adjustment required."
            },
            "confidence": 30,
            "ascendant": {
                "sign": "Unknown",
                "degree": 0
            },
            "key_factors": [],
            "house_analysis": {
                "houses": []
            }
        }

        # If we have time indicators, use them to improve the analysis
        time_indicators_dict = {}
        if birth_time_indicators:
            for indicator in birth_time_indicators:
                ind = indicator.get("indicators", {})
                for k, v in ind.items():
                    time_indicators_dict[k] = v

            # Update birth time range if we have a time range indicator
            if "time_range" in time_indicators_dict:
                time_range = time_indicators_dict["time_range"]
                if time_range and ":" in time_range:
                    try:
                        start, end = time_range.split("-")
                        analysis["birth_time_range"]["start"] = start
                        analysis["birth_time_range"]["end"] = end
                    except Exception as e:
                        logger.warning(f"Error parsing time range: {e}")

            # Update confidence based on indicators
            confidence = self._calculate_rectification_confidence(
                responses,
                time_indicators_dict
            )
            analysis["confidence"] = confidence

        return analysis

# Singleton pattern
_questionnaire_service = None

def get_questionnaire_service() -> QuestionnaireService:
    """
    Get the singleton instance of the QuestionnaireService.

    Returns:
        QuestionnaireService instance
    """
    global _questionnaire_service

    # Try to get from dependency container first
    try:
        from ai_service.utils.dependency_container import get_container
        container = get_container()

        # Check if already registered
        try:
            return container.get("questionnaire_service")
        except ValueError:
            # Not registered yet, register it
            def create_questionnaire_service():
                return QuestionnaireService()

            container.register("questionnaire_service", create_questionnaire_service)
            return container.get("questionnaire_service")
    except Exception as e:
        # Fallback to module-level singleton if dependency container is not available
        logger.info(f"Using module-level singleton for QuestionnaireService: {e}")

        if _questionnaire_service is None:
            _questionnaire_service = QuestionnaireService()

        return _questionnaire_service
