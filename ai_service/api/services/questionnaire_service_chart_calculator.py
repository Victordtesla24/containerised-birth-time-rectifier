"""
Chart calculator wrappers for the questionnaire service.

This module contains wrappers and stubs for chart calculator functionality.
"""

import logging

# logger initialization
logger = logging.getLogger(__name__)

# Import directly from the chart_calculator module
try:
    # Direct import from the chart_calculator module
    from ai_service.core.rectification.chart_calculator import calculate_chart

    # Create a wrapper to ensure the module has the necessary methods
    class ChartCalculatorWrapper:
        def create_chart(self, datetime_obj, geo_pos):
            try:
                return calculate_chart(
                    birth_dt=datetime_obj,
                    latitude=geo_pos.lat,
                    longitude=geo_pos.lon,
                    timezone_str=""
                )
            except Exception as e:
                logger.error(f"Error creating chart: {e}")
                return {"planets": {}, "houses": [], "angles": {}}

        def calculate_transits(self, natal_chart, transit_datetime, geo_pos):
            """Calculate transits for a given natal chart and transit time."""
            try:
                # This is a simplified transit calculation implementation
                transit_chart = calculate_chart(
                    birth_dt=transit_datetime,
                    latitude=geo_pos.lat,
                    longitude=geo_pos.lon,
                    timezone_str=""
                )

                # Calculate aspects between transit and natal planets
                transits = []
                for transit_planet, transit_data in transit_chart.get("planets", {}).items():
                    for natal_planet, natal_data in natal_chart.get("planets", {}).items():
                        # Calculate orb (difference in degrees)
                        orb = abs(transit_data.get("longitude", 0) - natal_data.get("longitude", 0))
                        if orb > 180:
                            orb = 360 - orb

                        # Check for common aspects (conjunction, opposition, trine, square, sextile)
                        aspect_type = None
                        if orb < 10:  # Conjunction
                            aspect_type = "conjunction"
                        elif 170 < orb < 190:  # Opposition
                            aspect_type = "opposition"
                        elif 110 < orb < 130:  # Trine
                            aspect_type = "trine"
                        elif 80 < orb < 100:  # Square
                            aspect_type = "square"
                        elif 50 < orb < 70:  # Sextile
                            aspect_type = "sextile"

                        if aspect_type:
                            transits.append({
                                "transit_planet": transit_planet,
                                "natal_planet": natal_planet,
                                "aspect": aspect_type,
                                "orb": orb
                            })

                return transits
            except Exception as e:
                logger.error(f"Error calculating transits: {e}")
                return []

        def evaluate_transit_significance(self, transits):
            """Evaluate the significance of transits."""
            try:
                # This is a simplified transit significance implementation
                if not transits:
                    return 0.0

                # Assign weights to different aspect types
                weights = {
                    "conjunction": 1.0,
                    "opposition": 0.8,
                    "trine": 0.6,
                    "square": 0.7,
                    "sextile": 0.5
                }

                # Calculate the total significance
                total_weight = 0
                for transit in transits:
                    aspect_type = transit.get("aspect")
                    weight = weights.get(aspect_type, 0.3)
                    total_weight += weight

                # Normalize to a 0-1 scale
                significance = min(1.0, total_weight / len(transits))
                return significance
            except Exception as e:
                logger.error(f"Error evaluating transit significance: {e}")
                return 0.5

    # Create wrapped module
    chart_calculator = ChartCalculatorWrapper()

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

    # Use stub
    chart_calculator = ChartCalculatorStub()
