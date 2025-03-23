"""
Chart calculator wrappers for the questionnaire service.

This module contains wrappers and stubs for chart calculator functionality.
"""

import logging

# logger initialization
logger = logging.getLogger(__name__)

# Import chart_calculator and create stub methods as needed
try:
    # Updated import to use new modular structure
    from ai_service.core.rectification import chart_calculator as chart_calculator_module

    # Create a wrapper to ensure the module has the necessary methods
    class ChartCalculatorWrapper:
        def __init__(self, module):
            self.module = module

        def create_chart(self, datetime_obj, geo_pos):
            if hasattr(self.module, 'create_chart'):
                return self.module.create_chart(datetime_obj, geo_pos)
            else:
                logger.warning("Using fallback chart creation method")
                return {"planets": {}, "houses": [], "angles": {}}

        def calculate_transits(self, natal_chart, transit_datetime, geo_pos):
            if hasattr(self.module, 'calculate_transits'):
                return self.module.calculate_transits(natal_chart, transit_datetime, geo_pos)
            else:
                logger.warning("Using fallback transit calculation method")
                return []

        def evaluate_transit_significance(self, transits):
            if hasattr(self.module, 'evaluate_transit_significance'):
                return self.module.evaluate_transit_significance(transits)
            else:
                logger.warning("Using fallback transit significance evaluation method")
                return 0.5

    # Create wrapped module
    chart_calculator = ChartCalculatorWrapper(chart_calculator_module)

except ImportError:
    logger.warning("chart_calculator module not available, chart comparison functions will be limited")

    # Create a stub module when chart_calculator is not available
    class ChartCalculatorStub:
        def create_chart(self, datetime_obj, geo_pos):
            logger.warning("Using stub chart creation method")
            return {"planets": {}, "houses": [], "angles": {}}

        def calculate_transits(self, natal_chart, transit_datetime, geo_pos):
            logger.warning("Using stub transit calculation method")
            return []

        def evaluate_transit_significance(self, transits):
            logger.warning("Using stub transit significance evaluation method")
            return 0.5

    chart_calculator = ChartCalculatorStub()
