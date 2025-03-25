"""
Birth Time Rectification Module

This module provides utilities for rectifying birth times using various
astrological methods.

Usage:
    from ai_service.core.rectification.main import rectify_birth_time, comprehensive_rectification
    from ai_service.core.rectification.chart_calculator import calculate_chart
    from ai_service.core.rectification.event_analysis import extract_life_events_from_answers
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

# Import main functionality
from .main import (
    rectify_birth_time,
    comprehensive_rectification,
    questionnaire_based_rectification,
    chart_based_rectification,
    generate_rectification_explanation,
    generate_detailed_analysis
)

# Import chart calculation utilities
from .chart_calculator import (
    calculate_chart,
    get_planets_list
)

# Import event analysis functionality
from .event_analysis import extract_life_events_from_answers

# Import constants
from .constants import PLANETS_LIST, LIFE_EVENT_MAPPING

# Import methods for specific rectification approaches
from .methods.transit_analysis import analyze_life_events
from .methods.ai_rectification import ai_assisted_rectification
from .methods.solar_arc import solar_arc_rectification
from .methods.progressed import progressed_ascendant_rectification

# Import utilities
from .utils.storage import store_rectified_chart
from .utils.ephemeris import verify_ephemeris_files

# Import AI verification utilities
from .ai_verification import verify_with_openai, create_standardized_openai_prompt

# Set up logger
logger = logging.getLogger(__name__)

# Export all necessary functions and constants
__all__ = [
    # Main functions
    'rectify_birth_time',
    'comprehensive_rectification',
    'questionnaire_based_rectification',
    'chart_based_rectification',
    'generate_rectification_explanation',
    'generate_detailed_analysis',

    # Chart utilities
    'calculate_chart',
    'get_planets_list',

    # Event analysis
    'extract_life_events_from_answers',

    # Constants
    'PLANETS_LIST',
    'LIFE_EVENT_MAPPING',

    # Method-specific functions
    'analyze_life_events',
    'ai_assisted_rectification',
    'solar_arc_rectification',
    'progressed_ascendant_rectification',

    # Utilities
    'store_rectified_chart',
    'verify_ephemeris_files',

    # AI verification
    'verify_with_openai',
    'create_standardized_openai_prompt'
]

# Log initialization
logger.debug("Birth time rectification module initialized")
