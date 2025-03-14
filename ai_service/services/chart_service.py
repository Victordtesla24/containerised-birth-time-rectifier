"""
Chart Service

This module provides services for chart generation, retrieval, and validation.
It handles the business logic for astrological chart operations.
"""

import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from ai_service.utils.constants import ZODIAC_SIGNS
from ai_service.core.chart_calculator import (
    calculate_houses, calculate_ketu_position, calculate_chart as calculate_basic_chart,
    calculate_verified_chart, get_enhanced_chart_calculator
)

# Setup logging
logger = logging.getLogger(__name__)

# In-memory chart store - in production, should be replaced with a database
chart_store = {}

class ChartService:
    """Service for chart operations including generation, validation, and retrieval"""

    def __init__(self):
        """Initialize the chart service with access to chart storage"""
        # For backward compatibility with code that uses chart_storage attribute
        self.chart_storage = chart_store

    @staticmethod
    async def generate_chart(
        birth_date: str,
        birth_time: str,
        latitude: float,
        longitude: float,
        timezone: str,
        house_system: str = "P",
        zodiac_type: str = "sidereal",
        ayanamsa: float = 23.6647,
        verify_with_openai: bool = True,
        node_type: str = "true"
    ) -> Dict[str, Any]:
        """
        Generate a chart based on birth details with optional OpenAI verification

        Args:
            birth_date: Birth date in format YYYY-MM-DD
            birth_time: Birth time in format HH:MM:SS
            latitude: Birth location latitude
            longitude: Birth location longitude
            timezone: Timezone string (e.g., "America/New_York")
            house_system: House system to use (default "P" for Placidus)
            zodiac_type: Zodiac type (default "sidereal" for Indian astrology)
            ayanamsa: Ayanamsa value (default 23.6647 for Lahiri)
            verify_with_openai: Whether to verify chart with OpenAI
            node_type: Type of nodes to calculate (default "true")

        Returns:
            Dictionary containing chart data
        """
        # Create birth datetime
        birth_dt_str = f"{birth_date}T{birth_time}"
        birth_dt = datetime.fromisoformat(birth_dt_str)

        try:
            # Generate chart with OpenAI verification if requested
            if verify_with_openai:
                logger.info(f"Generating verified chart for {birth_date} {birth_time}")
                chart_data = await calculate_verified_chart(
                    birth_date=birth_date,
                    birth_time=birth_time,
                    latitude=latitude,
                    longitude=longitude,
                    location="",  # Optional location name
                    house_system=house_system,
                    ayanamsa=int(ayanamsa),
                    node_type=node_type
                )
                logger.info("Using OpenAI-verified chart")
            else:
                # Use basic calculation without verification
                chart_data = calculate_basic_chart(
                    birth_date=birth_dt.strftime("%Y-%m-%d"),
                    birth_time=birth_dt.strftime("%H:%M:%S"),
                    latitude=latitude,
                    longitude=float(longitude),
                    location="",  # Add location parameter
                    house_system=house_system,
                    ayanamsa=float(ayanamsa),
                    node_type=node_type  # Add node_type parameter with default
                )
        except Exception as e:
            # If verification fails, fall back to basic calculation
            logger.warning(f"Chart calculation failed, using fallback: {e}")
            chart_data = calculate_basic_chart(
                birth_date=birth_dt.strftime("%Y-%m-%d"),
                birth_time=birth_dt.strftime("%H:%M:%S"),
                latitude=latitude,
                longitude=float(longitude),
                location="",  # Add location parameter
                house_system=house_system,
                ayanamsa=float(ayanamsa),
                node_type=node_type  # Add node_type parameter with default
            )

        # Process and normalize chart data
        chart_data = ChartService._process_chart_data(chart_data)

        # Generate a chart ID and store the chart
        chart_id = str(uuid.uuid4())[:8]
        chart_store[chart_id] = chart_data

        return {
            "chart_id": chart_id,
            **chart_data
        }

    @staticmethod
    def get_chart(chart_id: str) -> Dict[str, Any]:
        """
        Retrieve a chart by ID

        Args:
            chart_id: The ID of the chart to retrieve

        Returns:
            Dictionary containing chart data

        Raises:
            ValueError: If chart with ID not found
        """
        if chart_id not in chart_store:
            raise ValueError(f"Chart not found: {chart_id}")

        chart_data = chart_store[chart_id]
        return {
            "chart_id": chart_id,
            **chart_data
        }

    def compare_charts(self, chart1_id: str, chart2_id: str, comparison_type: str = "differences", include_significance: bool = True) -> Dict:
        """
        Compare two charts and analyze their differences.

        Args:
            chart1_id: ID of the first chart
            chart2_id: ID of the second chart
            comparison_type: Type of comparison (differences, full, summary)
            include_significance: Whether to include significance ratings

        Returns:
            Dictionary containing comparison results
        """
        # Verify both charts exist
        if chart1_id not in chart_store:
            raise ValueError(f"Chart not found: {chart1_id}")
        if chart2_id not in chart_store:
            raise ValueError(f"Chart not found: {chart2_id}")

        # Get the charts from storage
        chart1 = chart_store[chart1_id]
        chart2 = chart_store[chart2_id]

        # Compare ascendant changes
        ascendant_change = {
            "type": "ascendant_shift",
            "chart1_position": {
                "sign": chart1["ascendant"]["sign"],
                "degree": chart1["ascendant"]["degree"]
            },
            "chart2_position": {
                "sign": chart2["ascendant"]["sign"],
                "degree": chart2["ascendant"]["degree"]
            },
            "significance": 85.0 if include_significance else None
        }

        # Compare planets
        planet_differences = []
        for planet_name, planet1 in chart1["planets"].items():
            # Find the same planet in chart2
            if planet_name in chart2["planets"]:
                planet2 = chart2["planets"][planet_name]

                # Check if there are meaningful differences
                sign_change = planet1["sign"] != planet2["sign"]
                house_change = planet1.get("house", 0) != planet2.get("house", 0)
                degree_diff = abs(planet1["degree"] - planet2["degree"]) > 1.0

                if sign_change or house_change or degree_diff:
                    diff_entry = {
                        "type": "planet_shift",
                        "planet": planet1["name"],
                        "chart1_position": {
                            "sign": planet1["sign"],
                            "degree": planet1["degree"],
                            "house": planet1.get("house", 0)
                        },
                        "chart2_position": {
                            "sign": planet2["sign"],
                            "degree": planet2["degree"],
                            "house": planet2.get("house", 0)
                        },
                    }

                    if include_significance:
                        diff_entry["significance"] = 75.0 if sign_change else (65.0 if house_change else 40.0)

                    planet_differences.append(diff_entry)

        # Generate a unique comparison ID
        comparison_id = f"comp_{uuid.uuid4().hex[:12]}"

        # Create full response
        differences = [ascendant_change] + planet_differences

        response = {
            "comparison_id": comparison_id,
            "chart1_id": chart1_id,
            "chart2_id": chart2_id,
            "comparison_type": comparison_type,
            "differences": differences,
        }

        # Add summary for "full" or "summary" comparison types
        if comparison_type.lower() == "full" or comparison_type.lower() == "summary":
            # Count meaningful changes
            signs_changed = sum(1 for d in differences if d["type"] == "planet_shift" and
                               d["chart1_position"]["sign"] != d["chart2_position"]["sign"])

            houses_changed = sum(1 for d in differences if d["type"] == "planet_shift" and
                                 d["chart1_position"]["house"] != d["chart2_position"]["house"])

            summary = f"The chart comparison reveals: "

            # Extract birth time info
            birth_time1 = chart1["birth_details"]["birth_time"]
            birth_time2 = chart2["birth_details"]["birth_time"]

            summary += f"Birth time adjustment from {birth_time1} to {birth_time2}; "

            # Ascendant info
            asc1_sign = chart1["ascendant"]["sign"]
            asc2_sign = chart2["ascendant"]["sign"]
            if asc1_sign != asc2_sign:
                summary += f"Ascendant changes from {asc1_sign} to {asc2_sign}; "

            # Planet and house info
            if houses_changed:
                summary += f"{houses_changed} planet(s) change houses; "
            if signs_changed:
                summary += f"{signs_changed} planet(s) change signs; "

            # House sign changes
            house_sign_changes = 0
            if "houses" in chart1 and "houses" in chart2:
                for i in range(min(len(chart1["houses"]), len(chart2["houses"]))):
                    if chart1["houses"][i]["sign"] != chart2["houses"][i]["sign"]:
                        house_sign_changes += 1

            if house_sign_changes:
                summary += f"{house_sign_changes} house(s) change signs."

            response["summary"] = summary.strip()

        return response

    @staticmethod
    def _process_chart_data(chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the generated chart data to ensure it's in the expected format.

        Args:
            chart_data: Raw chart data from calculation

        Returns:
            Processed chart data with standardized structure
        """
        processed_data = {**chart_data}  # Create a copy of the original data

        # Ensure d1Chart field is present for compatibility with tests
        if "d1Chart" not in processed_data:
            # Extract the main chart as d1Chart
            d1_chart = {
                "ascendant": chart_data.get("ascendant", {}),
                "planets": [],
                "houses": chart_data.get("houses", []),
                "aspects": chart_data.get("aspects", [])
            }

            # Extract planets from the main data if they exist
            planets = chart_data.get("planets", [])
            if planets:
                d1_chart["planets"] = planets

            # Add d1Chart to the processed data
            processed_data["d1Chart"] = d1_chart

        return processed_data
