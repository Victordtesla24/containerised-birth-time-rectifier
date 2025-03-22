"""DEPRECATED: This file has been removed as part of code deduplication.

This functionality has been moved to ai_service.core.rectification.chart_calculator
Please update your imports to use ai_service.core.rectification.chart_calculator directly.

For command-line chart calculation, use:
python -m ai_service.core.rectification.chart_calculator

Example:
from ai_service.core.rectification.chart_calculator import calculate_chart
"""

# Import constants that might be used by other modules
from ai_service.core.rectification.chart_calculator import calculate_chart

# Raise deprecation error to enforce migration
raise ImportError(
    "This module has been deprecated and removed. "
    "Please update your imports to use ai_service.core.rectification.chart_calculator directly."
)
