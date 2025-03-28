"""
Unified Chart Calculator Service.

This module provides a unified interface to chart calculation functionality,
consolidating multiple calculator implementations into a single service.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import uuid

from ai_service.utils.dependency_container import get_container

# Import chart calculation modules
from ai_service.core.rectification.chart_calculator import calculate_chart
from ai_service.utils.swisseph import initialize_swiss_ephemeris

# Configure logging
logger = logging.getLogger(__name__)

class ChartCalculatorService:
    """
    Unified service for astrological chart calculations.

    This service provides a standardized interface for calculating astrological charts,
    transits, progressions, and other derived chart data.
    """

    def __init__(self):
        """Initialize the chart calculator service."""
        # Initialize SwissEphemeris if not already initialized
        try:
            initialize_swiss_ephemeris()
            logger.info("Swiss Ephemeris initialized for chart calculations")
        except Exception as e:
            logger.error(f"Failed to initialize Swiss Ephemeris: {e}")

    def create_chart(self, datetime_obj: datetime, latitude: float, longitude: float, timezone_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Create an astrological chart for a given date/time and location.

        Args:
            datetime_obj: The date and time for the chart
            latitude: Geographic latitude
            longitude: Geographic longitude
            timezone_str: Optional timezone string (if not provided, determined from coordinates)

        Returns:
            Complete chart data
        """
        try:
            return calculate_chart(
                birth_dt=datetime_obj,
                latitude=latitude,
                longitude=longitude,
                timezone_str=timezone_str or ""  # Will be determined from coordinates if empty
            )
        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            raise ValueError(f"Failed to create chart: {e}")

    def calculate_transits(self, natal_chart: Dict[str, Any], transit_datetime: datetime,
                         latitude: float, longitude: float, timezone_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Calculate transits for a given natal chart and transit time.

        Args:
            natal_chart: The natal chart to calculate transits against
            transit_datetime: The datetime for transit calculation
            latitude: Geographic latitude
            longitude: Geographic longitude
            timezone_str: Optional timezone string (if not provided, determined from coordinates)

        Returns:
            List of transit aspects
        """
        try:
            # Calculate transit chart
            transit_chart = self.create_chart(
                datetime_obj=transit_datetime,
                latitude=latitude,
                longitude=longitude,
                timezone_str=timezone_str
            )

            # Calculate aspects between transit and natal planets
            from ai_service.services.chart_service_aspects import calculate_aspects

            # Merge charts for aspect calculation
            merged_data = {
                "natal_planets": natal_chart.get("planets", {}),
                "transit_planets": transit_chart.get("planets", {}),
                "houses": natal_chart.get("houses", [])
            }

            # Call calculate_aspects
            return calculate_aspects(merged_data)

        except Exception as e:
            logger.error(f"Error calculating transits: {e}")
            raise ValueError(f"Failed to calculate transits: {e}")

    def evaluate_transit_significance(self, transits: List[Dict[str, Any]]) -> float:
        """
        Evaluate the significance of transits.

        Args:
            transits: List of transit aspects

        Returns:
            Significance score (0.0-1.0)
        """
        try:
            # Implement direct calculation without attempting to import
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

            # Calculate significance
            total_weight = 0.0
            significant_count = 0

            for transit in transits:
                aspect_type = transit.get("aspect", "")
                weight = weights.get(aspect_type.lower(), 0.3)

                planet1 = transit.get("planet1", "")
                planet2 = transit.get("planet2", "")

                # Major planets have higher significance
                major_planets = ["sun", "moon", "ascendant", "mc"]
                if planet1.lower() in major_planets or planet2.lower() in major_planets:
                    weight *= 1.5

                # Apply orb factor - closer aspects are more significant
                orb = transit.get("orb", 5.0)
                orb_factor = max(0.2, 1.0 - (orb / 10.0))

                weight *= orb_factor
                total_weight += weight
                significant_count += 1

            # Normalize to 0-1 scale with reasonable upper bound
            if significant_count > 0:
                return min(1.0, total_weight / (significant_count * 0.8))
            return 0.0

        except Exception as e:
            logger.error(f"Error evaluating transit significance: {e}")
            return 0.0

    def calculate_progressions(self, natal_chart: Dict[str, Any], progression_date: datetime,
                            progression_type: str = "secondary") -> Dict[str, Any]:
        """
        Calculate progressions for a natal chart.

        Args:
            natal_chart: The natal chart to progress
            progression_date: The date to progress to
            progression_type: Type of progression (secondary, tertiary, solar arc)

        Returns:
            Progressed chart data
        """
        try:
            # Implement direct calculations without attempting to import
            birth_data = natal_chart.get("birth_details", {})
            birth_dt = datetime.fromisoformat(birth_data.get("birth_datetime", ""))

            # Calculate days between birth and target date
            days_diff = (progression_date - birth_dt).days

            if progression_type == "secondary":
                # Secondary progressions: 1 day = 1 year
                prog_dt = birth_dt + timedelta(days=days_diff)

                # Calculate chart for progressed date
                return self.create_chart(
                    datetime_obj=prog_dt,
                    latitude=birth_data.get("latitude", 0),
                    longitude=birth_data.get("longitude", 0),
                    timezone_str=birth_data.get("timezone", "")
                )
            elif progression_type == "tertiary":
                # Tertiary progressions: 1 lunar cycle ≈ 1 year (27.32 days)
                lunar_days = days_diff * (27.32 / 365.25)
                prog_dt = birth_dt + timedelta(days=lunar_days)

                return self.create_chart(
                    datetime_obj=prog_dt,
                    latitude=birth_data.get("latitude", 0),
                    longitude=birth_data.get("longitude", 0),
                    timezone_str=birth_data.get("timezone", "")
                )
            elif progression_type == "solar_arc":
                # Solar Arc: Move all planets by the same arc the Sun has moved
                # Calculate the natal Sun position
                natal_chart_data = calculate_chart(
                    birth_dt=birth_dt,
                    latitude=birth_data.get("latitude", 0),
                    longitude=birth_data.get("longitude", 0),
                    timezone_str=birth_data.get("timezone", "")
                )

                # Calculate the progressed Sun position
                years_diff = days_diff / 365.25
                solar_arc_degrees = years_diff  # Sun moves approximately 1 degree per year

                # Apply solar arc to all planets and points in natal chart
                result_chart = natal_chart_data.copy()

                # Adjust planet positions
                for planet_name, planet_data in result_chart.get("planets", {}).items():
                    if "longitude" in planet_data:
                        new_longitude = (planet_data["longitude"] + solar_arc_degrees) % 360
                        planet_data["longitude"] = new_longitude

                        # Update sign and degree
                        sign_num = int(new_longitude / 30)
                        sign = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                               "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"][sign_num]
                        degree = new_longitude % 30

                        planet_data["sign"] = sign
                        planet_data["sign_num"] = sign_num
                        planet_data["degree"] = degree

                # Update ascendant and other angles
                if "ascendant" in result_chart:
                    asc_data = result_chart["ascendant"]
                    if "longitude" in asc_data:
                        new_longitude = (asc_data["longitude"] + solar_arc_degrees) % 360
                        asc_data["longitude"] = new_longitude

                        # Update sign and degree
                        sign_num = int(new_longitude / 30)
                        sign = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                               "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"][sign_num]
                        degree = new_longitude % 30

                        asc_data["sign"] = sign
                        asc_data["degree"] = degree

                return result_chart
            else:
                raise ValueError(f"Unsupported progression type: {progression_type}")
        except Exception as e:
            logger.error(f"Error calculating progressions: {e}")
            raise ValueError(f"Failed to calculate progressions: {e}")

    def calculate_sensitive_periods(self, birth_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate astrologically sensitive periods based on birth details.

        Args:
            birth_data: Birth details including date, time, and location

        Returns:
            List of sensitive periods with descriptions
        """
        try:
            # Use direct calculation without attempting to import questionnaire_service module
            birth_date = birth_data.get("birth_date", "")
            birth_year = int(birth_date.split("-")[0]) if birth_date else 0

            if birth_year == 0:
                return []

            return [
                {
                    "age": 7,
                    "year": birth_year + 7,
                    "description": "First Saturn square - early childhood transition",
                    "significance": 0.6
                },
                {
                    "age": 14,
                    "year": birth_year + 14,
                    "description": "Second Saturn square - adolescence transition",
                    "significance": 0.7
                },
                {
                    "age": 21,
                    "year": birth_year + 21,
                    "description": "First Saturn opposition - early adulthood",
                    "significance": 0.8
                },
                {
                    "age": 29,
                    "year": birth_year + 29,
                    "description": "Saturn return - major life transition",
                    "significance": 1.0
                },
                {
                    "age": 38,
                    "year": birth_year + 38,
                    "description": "Uranus opposition - midlife transition",
                    "significance": 0.9
                }
            ]
        except Exception as e:
            logger.error(f"Error calculating sensitive periods: {e}")
            return []

    def analyze_life_events(self, birth_chart: Dict[str, Any], events: List[Dict[str, datetime]]) -> Dict[str, Any]:
        """
        Analyze how life events correlate with astrological transits.

        Args:
            birth_chart: Natal chart data
            events: List of life events with dates

        Returns:
            Analysis of astrological correlations with events
        """
        try:
            results = {
                "events_analyzed": len(events),
                "significant_correlations": [],
                "average_significance": 0.0
            }

            total_significance = 0.0
            birth_details = birth_chart.get("birth_details", {})

            for event in events:
                event_date = event.get("date")
                event_name = event.get("description", "Unnamed event")

                if not event_date:
                    continue

                # Calculate transits for this event
                transits = self.calculate_transits(
                    natal_chart=birth_chart,
                    transit_datetime=event_date,
                    latitude=birth_details.get("latitude", 0),
                    longitude=birth_details.get("longitude", 0)
                )

                # Evaluate significance
                significance = self.evaluate_transit_significance(transits)
                total_significance += significance

                # Add significant correlations
                if significance > 0.6:
                    results["significant_correlations"].append({
                        "event": event_name,
                        "date": event_date.isoformat(),
                        "significance": significance,
                        "key_transits": [
                            f"{t.get('planet1', '')} {t.get('aspect', '')} {t.get('planet2', '')}"
                            for t in sorted(transits, key=lambda x: x.get("orb", 10))[:3]
                        ]
                    })

            # Calculate average significance
            if events:
                results["average_significance"] = total_significance / len(events)

            return results

        except Exception as e:
            logger.error(f"Error analyzing life events: {e}")
            return {"error": str(e), "events_analyzed": 0}

    def generate_chart_id(self) -> str:
        """
        Generate a unique chart ID.

        Returns:
            A unique chart ID string
        """
        return f"chart_{uuid.uuid4().hex[:12]}"

# Singleton instance
_chart_calculator_service = None

def get_chart_calculator_service() -> ChartCalculatorService:
    """
    Get or create the chart calculator service singleton.

    Returns:
        ChartCalculatorService: The chart calculator service instance
    """
    global _chart_calculator_service

    # Return existing instance if available
    if _chart_calculator_service is not None:
        return _chart_calculator_service

    # Check if available in container
    container = get_container()
    if container.has_service("chart_calculator_service"):
        service = container.get("chart_calculator_service")
        if service:
            _chart_calculator_service = service
            return service

    # Create new instance
    service = ChartCalculatorService()

    # Register in container
    if container:
        container.register_service("chart_calculator_service", service)

    _chart_calculator_service = service
    return service

# For backward compatibility, create a simple wrapper with the old interface
class ChartCalculatorWrapper:
    """Compatibility wrapper for existing code that uses the old interface."""

    def __init__(self):
        """Initialize the wrapper."""
        self._service = get_chart_calculator_service()

    def create_chart(self, datetime_obj, geo_pos):
        """Compatibility method for create_chart."""
        return self._service.create_chart(
            datetime_obj=datetime_obj,
            latitude=geo_pos.lat,
            longitude=geo_pos.lon
        )

    def calculate_transits(self, natal_chart, transit_datetime, geo_pos):
        """Compatibility method for calculate_transits."""
        return self._service.calculate_transits(
            natal_chart=natal_chart,
            transit_datetime=transit_datetime,
            latitude=geo_pos.lat,
            longitude=geo_pos.lon
        )

    def evaluate_transit_significance(self, transits):
        """Compatibility method for evaluate_transit_significance."""
        return self._service.evaluate_transit_significance(transits)

# Create instance for backward compatibility
chart_calculator = ChartCalculatorWrapper()
