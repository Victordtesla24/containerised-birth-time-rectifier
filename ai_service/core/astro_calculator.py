"""DEPRECATED: This file is provided for backward compatibility.

This functionality has been moved to ai_service.core.rectification.chart_calculator
Please update your imports to use ai_service.core.rectification.chart_calculator directly.

Example:
from ai_service.core.rectification.chart_calculator import calculate_chart
"""

import warnings
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Issue deprecation warning
warnings.warn(
    "ai_service.core.astro_calculator is deprecated. "
    "Please update your imports to use ai_service.core.rectification.chart_calculator directly.",
    DeprecationWarning,
    stacklevel=2
)

# Import from the new location for forwarding
from ai_service.core.rectification.chart_calculator import (
    calculate_chart as _calculate_chart,
    get_planets_list as _get_planets_list,
    normalize_longitude,
    EnhancedChartCalculator as _EnhancedChartCalculator
)

# Provide compatibility class that forwards to the new implementation
class AstroCalculator:
    """
    Compatibility wrapper for the new chart calculator.

    This class forwards calls to ai_service.core.rectification.chart_calculator.
    """

    def __init__(self, ephe_path: Optional[str] = None, ayanamsa_type: int = 1):
        """
        Initialize the calculator with ephemeris path and ayanamsa.

        Args:
            ephe_path: Path to ephemeris files (falls back to environment variable)
            ayanamsa_type: Ayanamsa type (1=Lahiri, 0=None/Tropical)
        """
        self.ephe_path = ephe_path or os.environ.get("SWISSEPH_PATH", "/app/ephemeris")
        self.ayanamsa_type = ayanamsa_type

    async def calculate_chart(self, birth_dt: datetime, latitude: float, longitude: float,
                             timezone_str: str, house_system: str = 'P') -> Dict[str, Any]:
        """Forward to the new implementation."""
        return _calculate_chart(birth_dt, latitude, longitude, timezone_str, house_system)

    def _datetime_to_jd(self, dt: datetime) -> float:
        """Compatibility method for tests."""
        # Simple implementation without relying on non-existent import
        import swisseph as swe

        # Convert datetime to Julian Day
        utc_dt = dt.astimezone(timezone.utc)
        year, month, day = utc_dt.year, utc_dt.month, utc_dt.day
        hour = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0

        # Use swiss ephemeris function directly
        jd = swe.julday(year, month, day, hour)
        return jd

    def _calculate_aspects(self, positions: Dict[str, float]) -> Dict[str, Any]:
        """Compatibility method for tests."""
        # Simple implementation for test compatibility
        aspects = {}
        planets = list(positions.keys())

        for i in range(len(planets)):
            planet1 = planets[i]
            for j in range(i + 1, len(planets)):
                planet2 = planets[j]

                lon1 = positions[planet1]
                lon2 = positions[planet2]

                # Calculate angular distance
                diff = abs(lon1 - lon2)
                if diff > 180:
                    diff = 360 - diff

                # Define aspects and their orbs
                aspect_types = {
                    0: ('conjunction', 10),
                    60: ('sextile', 6),
                    90: ('square', 8),
                    120: ('trine', 8),
                    180: ('opposition', 10)
                }

                # Find matching aspect
                for angle, (name, orb) in aspect_types.items():
                    if abs(diff - angle) <= orb:
                        aspect_key = f"{planet1}_{planet2}"
                        aspects[aspect_key] = {
                            'planets': [planet1, planet2],
                            'type': name,
                            'angle': angle,
                            'orb': abs(diff - angle)
                        }
                        break

        return aspects

# Singleton accessor for backward compatibility
_calculator_instance = None

def get_astro_calculator() -> AstroCalculator:
    """
    Get singleton instance of AstroCalculator for backward compatibility.
    """
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = AstroCalculator()
    return _calculator_instance
