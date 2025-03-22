"""DEPRECATED: This file has been removed as part of code deduplication.

This functionality has been moved to ai_service.core.rectification.chart_calculator
Please update your imports to use ai_service.core.rectification.chart_calculator directly.

Example:
from ai_service.core.rectification.chart_calculator import calculate_chart

For more advanced chart functionality:
from ai_service.core.rectification.chart_calculator import calculate_chart
"""

# Import from the new module to allow legacy imports to still work
from ai_service.core.rectification.chart_calculator import (
    calculate_chart, get_planets_list
)

# Also import any classes or functions that might be used by other modules
try:
    from ai_service.core.rectification.chart_calculator import (
        normalize_longitude,
        calculate_verified_chart
    )
except ImportError:
    # If those specific functions don't exist in the new module,
    # provide alternatives or raise a more helpful error
    import logging
    import asyncio
    from typing import Dict, Any, Coroutine

    logger = logging.getLogger(__name__)
    logger.warning(
        "Some functions are not available in the new module. "
        "Please update your imports and code to use the new structure."
    )

    # Define sync versions of async functions
    async def calculate_verified_chart(*args, **kwargs) -> Dict[str, Any]:
        """Redirect to the standard calculate_chart function."""
        logger.warning("calculate_verified_chart is deprecated. Use calculate_chart instead.")
        try:
            # Since calculate_chart is not async, we don't need to await it
            return calculate_chart(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in calculate_verified_chart: {str(e)}")
            raise

    def normalize_longitude(longitude):
        """Simple longitude normalization to 0-360 range."""
        return longitude % 360

    # Create a sync-compatible wrapper class
    class EnhancedChartCalculator:
        """Fallback implementation of EnhancedChartCalculator."""
        def __init__(self, *args, **kwargs):
            logger.warning("Using fallback EnhancedChartCalculator. Please update your imports.")

        async def calculate_chart(self, *args, **kwargs) -> Dict[str, Any]:
            """Forward to the global calculate_chart function."""
            logger.warning("Using asynchronous fallback for calculate_chart")
            try:
                # Since calculate_chart is not async, we don't need to await it
                return calculate_chart(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in EnhancedChartCalculator.calculate_chart: {str(e)}")
                raise

    def get_enhanced_chart_calculator(*args, **kwargs):
        """Stub function to prevent import errors."""
        raise ImportError(
            "get_enhanced_chart_calculator has been moved. "
            "Please update your imports to the new module."
        )
