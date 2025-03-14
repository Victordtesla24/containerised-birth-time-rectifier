"""
Chart service implementation.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class ChartService:
    """Service for accessing and managing chart data."""

    def __init__(self, db_connection=None):
        """
        Initialize the chart service.

        Args:
            db_connection: Optional database connection
        """
        self.db_connection = db_connection
        logger.debug("Chart service initialized")
        self.chart_cache = {}

    async def get_chart(self, chart_id: str) -> Dict[str, Any]:
        """
        Retrieve chart data from database or return mock data for testing.

        Args:
            chart_id: Unique identifier for the chart

        Returns:
            Dictionary containing chart data
        """
        try:
            # Check if chart is in cache
            if chart_id in self.chart_cache:
                logger.debug(f"Retrieved chart {chart_id} from cache")
                return self.chart_cache[chart_id]

            # Check if we're in a test environment or have no DB connection
            is_test_env = os.environ.get("APP_ENV") == "test" or os.environ.get("TESTING") == "true"
            if is_test_env or not self.db_connection:
                logger.debug(f"Using mock data for chart {chart_id}")
                return self._generate_mock_chart(chart_id)

            # In a production environment with DB, fetch the real chart
            # This would be the actual implementation that gets data from Redis or database
            # For now, return mock data
            logger.warning("Database connection not implemented, using mock data")
            return self._generate_mock_chart(chart_id)

        except Exception as e:
            logger.error(f"Error retrieving chart {chart_id}: {str(e)}")
            # Return a basic structure even in case of error
            return {
                "chart_id": chart_id,
                "error": str(e),
                "birth_details": {
                    "birth_date": "1990-01-01",
                    "birth_time": "12:00:00"
                }
            }

    def _generate_mock_chart(self, chart_id: str) -> Dict[str, Any]:
        """Generate mock chart data for testing."""
        # Create a deterministic but realistic mock chart based on chart_id
        # Use the chart_id to seed some variations so different chart_ids get different data
        # This helps testing behave more realistically
        seed = sum(ord(c) for c in chart_id) % 12  # Simple hash of chart_id

        # Base planetary positions that we'll modify based on seed
        base_positions = [
            {"planet": "Sun", "sign": "Capricorn", "degree": 15 + (seed % 10)},
            {"planet": "Moon", "sign": "Taurus", "degree": 8 + (seed % 15)},
            {"planet": "Mercury", "sign": "Sagittarius", "degree": 20 + (seed % 8)},
            {"planet": "Venus", "sign": "Pisces", "degree": 5 + (seed % 12)},
            {"planet": "Mars", "sign": "Aries", "degree": 12 + (seed % 9)},
            {"planet": "Jupiter", "sign": "Libra", "degree": 18 + (seed % 7)},
            {"planet": "Saturn", "sign": "Capricorn", "degree": 25 + (seed % 4)},
            {"planet": "Ascendant", "sign": "Virgo", "degree": 15 + (seed % 20)},
            {"planet": "Midheaven", "sign": "Gemini", "degree": 10 + (seed % 15)}
        ]

        # Zodiac signs in order
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        # Generate house cusps based on seed
        houses = []
        for i in range(1, 13):
            # Assign each house to a sign
            sign_index = (seed + i - 1) % 12
            # Degree varies by house number and seed
            degree = (i * 7 + seed) % 30
            houses.append({
                "house": i,
                "sign": signs[sign_index],
                "degree": degree
            })

        # Generate aspects
        aspects = []
        for i in range(len(base_positions)):
            for j in range(i+1, len(base_positions)):
                # Only include some aspects based on seed to keep the list reasonable
                if (i + j + seed) % 4 == 0:
                    aspects.append({
                        "aspect_type": "Conjunction" if (i+j) % 5 == 0 else
                                     "Trine" if (i+j) % 5 == 1 else
                                     "Square" if (i+j) % 5 == 2 else
                                     "Opposition" if (i+j) % 5 == 3 else
                                     "Sextile",
                        "planet1": base_positions[i]["planet"],
                        "planet2": base_positions[j]["planet"],
                        "orb": ((i+j) * seed) % 5 + 1
                    })

        # Generate the chart data
        chart_data = {
            "chart_id": chart_id,
            "birth_details": {
                "birth_date": f"1990-{((seed % 12) + 1):02d}-{((seed % 28) + 1):02d}",
                "birth_time": f"{((seed + 8) % 24):02d}:{((seed * 5) % 60):02d}:00",
                "latitude": 40.7128 + (seed / 10),
                "longitude": -74.0060 - (seed / 10),
                "timezone": "America/New_York",
                "location": "New York, NY"
            },
            "planets": base_positions,
            "houses": houses,
            "aspects": aspects,
            "settings": {
                "house_system": "W",
                "ayanamsa": "lahiri",
                "chart_type": "north_indian"
            },
            "generated_at": datetime.now().isoformat(),
            "verification": {
                "verified": True,
                "confidence": 85.0 + (seed % 10),
                "corrections_applied": seed % 2 == 0
            }
        }

        # Store in cache for future requests
        self.chart_cache[chart_id] = chart_data

        return chart_data

    async def save_chart(self, chart_data: Dict[str, Any]) -> str:
        """
        Save chart data to database or mock storage.

        Args:
            chart_data: Chart data to save

        Returns:
            Chart ID
        """
        try:
            # Generate a chart ID if not provided
            chart_id = chart_data.get("chart_id", f"chrt_{datetime.now().strftime('%Y%m%d%H%M%S')}")

            # Store in cache
            self.chart_cache[chart_id] = chart_data

            # In a real implementation, this would save to DB
            logger.info(f"Saved chart {chart_id} (mock implementation)")

            return chart_id
        except Exception as e:
            logger.error(f"Error saving chart: {str(e)}")
            return f"error_{datetime.now().strftime('%Y%m%d%H%M%S')}"

# Singleton instance
_instance = None

def get_chart_service(db_connection=None) -> ChartService:
    """Get or create the chart service singleton."""
    global _instance
    if _instance is None:
        _instance = ChartService(db_connection)
    return _instance
