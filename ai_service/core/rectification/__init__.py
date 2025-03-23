"""
Birth Time Rectification Module

This module provides utilities for rectifying birth times using various
astrological methods.

Usage:
    from ai_service.core.rectification import rectify_birth_time, comprehensive_rectification
    rectified_time, confidence = await rectify_birth_time(birth_dt, lat, lon, tz, answers)
"""

import logging
import warnings
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import asyncio

# Import main functionality
from .main import (
    rectify_birth_time as _rectify_birth_time,
    comprehensive_rectification as _comprehensive_rectification,
    questionnaire_based_rectification,
    chart_based_rectification,
    generate_rectification_explanation,
    generate_detailed_analysis
)

# Import chart calculation utilities
from .chart_calculator import (
    calculate_chart as _calculate_chart,
    get_planets_list as _get_planets_list
)

# Import event analysis functionality
from .event_analysis import extract_life_events_from_answers as _extract_life_events_from_answers

# Import constants
from .constants import PLANETS_LIST, LIFE_EVENT_MAPPING

# Import methods for specific rectification approaches
from .methods.transit_analysis import analyze_life_events
from .methods.ai_rectification import ai_assisted_rectification
from .methods.solar_arc import solar_arc_rectification
from .methods.progressed import progressed_ascendant_rectification

# Import utilities
from .utils.storage import store_rectified_chart as _store_rectified_chart
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

# Forward compatibility functions
async def rectify_birth_time(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    answers: Optional[List[Dict[str, Any]]] = None
) -> Tuple[datetime, float]:
    """
    Forwards to the new modular implementation.
    """
    warnings.warn(
        "Using compatibility layer: Import from ai_service.core.rectification.main instead",
        DeprecationWarning, stacklevel=2
    )
    return await _rectify_birth_time(birth_dt, latitude, longitude, timezone, answers)

async def comprehensive_rectification(
    birth_dt: datetime,
    latitude: float,
    longitude: float,
    timezone: str,
    answers: List[Dict[str, Any]],
    events: Optional[List[Dict[str, Any]]] = None,
    chart_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Forwards to the new modular implementation.
    """
    warnings.warn(
        "Using compatibility layer: Import from ai_service.core.rectification.main instead",
        DeprecationWarning, stacklevel=2
    )
    return await _comprehensive_rectification(birth_dt, latitude, longitude, timezone, answers, events, chart_id)

def extract_life_events_from_answers(answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Forwards to the new modular implementation.
    """
    warnings.warn(
        "Using compatibility layer: Import from ai_service.core.rectification.event_analysis instead",
        DeprecationWarning, stacklevel=2
    )
    return _extract_life_events_from_answers(answers)

def calculate_chart(birth_dt: datetime, latitude: float, longitude: float, timezone_str: str) -> Any:
    """
    Forwards to the new modular implementation.
    """
    warnings.warn(
        "Using compatibility layer: Import from ai_service.core.rectification.chart_calculator instead",
        DeprecationWarning, stacklevel=2
    )
    return _calculate_chart(birth_dt, latitude, longitude, timezone_str)

def get_planets_list() -> List[str]:
    """
    Forwards to the new modular implementation.
    """
    warnings.warn(
        "Using compatibility layer: Import from ai_service.core.rectification.chart_calculator instead",
        DeprecationWarning, stacklevel=2
    )
    return _get_planets_list()

def store_rectified_chart(chart_data: Dict[str, Any], rectification_id: str, birth_dt: datetime, rectified_time_dt: datetime) -> Optional[str]:
    """
    Forwards to the new modular implementation.
    """
    warnings.warn(
        "Using compatibility layer: Import from ai_service.core.rectification.utils.storage instead",
        DeprecationWarning, stacklevel=2
    )
    # This is a sync function wrapping an async function, so we need to run it in an event loop
    try:
        # Create a new event loop if needed
        loop = asyncio.get_event_loop()
        # If the loop is closed or not running, create a new one
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        # Run the async function in the loop and return the result
        return loop.run_until_complete(_store_rectified_chart(chart_data, rectification_id, birth_dt, rectified_time_dt))
    except Exception as e:
        logger.error(f"Error in store_rectified_chart: {e}")
        return None

# Log deprecation warning when module is imported
logger.warning(
    "ai_service.core.rectification is deprecated. Please update your imports to use the new modular structure."
)
