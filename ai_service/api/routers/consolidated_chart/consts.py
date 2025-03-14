"""
Chart Router Constants

This module defines constants used by the chart-related routers.
"""

# Error codes for standardized error responses
ERROR_CODES = {
    "CHART_NOT_FOUND": "ERR_CHART_NOT_FOUND",
    "CALCULATION_ERROR": "ERR_CALCULATION_FAILED",
    "VALIDATION_ERROR": "ERR_VALIDATION_FAILED",
    "RECTIFICATION_FAILED": "ERR_RECTIFICATION_FAILED",
    "COMPARISON_FAILED": "ERR_COMPARISON_FAILED",
    "EXPORT_FAILED": "ERR_EXPORT_FAILED",
    "INTERNAL_SERVER_ERROR": "ERR_INTERNAL_SERVER",
    "INVALID_REQUEST": "ERR_INVALID_REQUEST"
}

# Default chart options
DEFAULT_CHART_OPTIONS = {
    "house_system": "P",
    "zodiac_type": "sidereal",
    "ayanamsa": "lahiri",
    "node_type": "true",
    "verify_with_openai": True
}

# Chart types
CHART_TYPES = [
    "natal",
    "transit",
    "progressed",
    "synastry",
    "composite",
    "rectified"
]

# Export formats
EXPORT_FORMATS = [
    "json",
    "pdf",
    "png",
    "svg",
    "text"
]
