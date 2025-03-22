"""
Chart comparison service for the Birth Time Rectifier API.
Provides functionality to compare original and rectified birth charts.
"""

import logging
import uuid
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ai_service.models.chart_comparison import (
    ChartDifference, DifferenceType, PlanetaryPosition,
    AspectData, ChartComparisonResponse
)
from ai_service.api.routers.consolidated_chart.utils import retrieve_chart

# Setup logging
logger = logging.getLogger("birth-time-rectifier.chart-comparison")

class ChartComparisonService:
    """Service for comparing astrological charts"""

    def __init__(self, chart_service=None):
        """
        Initialize the chart comparison service

        Args:
            chart_service: ChartService instance for retrieving chart data
        """
        self.chart_service = chart_service

    async def compare_charts(
        self,
        chart1_id: str,
        chart2_id: str,
        comparison_type: str = "differences",
        include_significance: bool = True
    ) -> Dict[str, Any]:
        """
        Compare two charts and identify key differences.

        Args:
            chart1_id: ID of the first chart
            chart2_id: ID of the second chart
            comparison_type: Type of comparison to perform
            include_significance: Whether to include significance metrics

        Returns:
            Dictionary with comparison results
        """
        logger.info(f"Comparing charts {chart1_id} and {chart2_id}")

        # Retrieve chart data
        try:
            chart1 = await retrieve_chart(chart1_id)
            if not chart1:
                raise ValueError(f"Chart with ID {chart1_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving chart 1: {str(e)}")
            raise

        try:
            chart2 = await retrieve_chart(chart2_id)
            if not chart2:
                raise ValueError(f"Chart with ID {chart2_id} not found")
        except Exception as e:
            logger.error(f"Error retrieving chart 2: {str(e)}")
            raise

        # Validate chart data
        self._validate_chart_data(chart1)
        self._validate_chart_data(chart2)

        # Prepare comparison response
        response = ChartComparisonResponse(
            chart1_id=chart1_id,
            chart2_id=chart2_id,
            differences=[],
            summary="",
            comparison_type=comparison_type,
            comparison_date=datetime.utcnow().isoformat()
        )

        # Identify differences
        differences = []

        # Ascendant comparison
        ascendant_diff = self._compare_ascendant(chart1, chart2)
        if ascendant_diff:
            differences.append(ascendant_diff)

        # Midheaven comparison
        midheaven_diff = self._compare_midheaven(chart1, chart2)
        if midheaven_diff:
            differences.append(midheaven_diff)

        # Planet positions comparison
        planet_diffs = self._compare_planets(chart1, chart2)
        differences.extend(planet_diffs)

        # Aspects comparison
        aspect_diffs = self._compare_aspects(chart1, chart2)
        differences.extend(aspect_diffs)

        # House cusps comparison
        house_diffs = self._compare_houses(chart1, chart2)
        differences.extend(house_diffs)

        # Calculate overall impact score
        overall_impact = None
        if include_significance and differences:
            impact_sum = sum(d.significance if d.significance else 0 for d in differences)
            overall_impact = min(100, max(0, impact_sum / len(differences) * 100))

        # Generate summary
        summary = self._generate_summary(chart1, chart2, differences, overall_impact)

        # Return formatted response
        return {
            "chart1_id": chart1_id,
            "chart2_id": chart2_id,
            "chart1_data": {
                "date": chart1.get("birth_date", ""),
                "time": chart1.get("birth_time", ""),
                "location": chart1.get("birth_location", "")
            },
            "chart2_data": {
                "date": chart2.get("birth_date", ""),
                "time": chart2.get("birth_time", ""),
                "location": chart2.get("birth_location", "")
            },
            "differences": [d.dict() for d in differences],
            "overall_impact": overall_impact,
            "summary": summary,
            "comparison_type": comparison_type
        }

    def _validate_chart_data(self, chart: Dict[str, Any]) -> None:
        """
        Validate that the chart data contains all required fields.

        Args:
            chart: Chart data to validate

        Raises:
            ValueError: If chart data is missing required fields
        """
        if not chart:
            raise ValueError("Chart data is empty")

        # Check for required sections
        required_sections = ["planets", "houses", "angles"]
        for section in required_sections:
            if section not in chart:
                raise ValueError(f"Chart is missing required section: {section}")

        # Ensure planets contain required data
        if not chart.get("planets"):
            raise ValueError("Chart is missing planetary data")

        # Ensure houses contain required data
        if not chart.get("houses"):
            raise ValueError("Chart is missing house data")

        # Ensure angles contain required data
        if not chart.get("angles"):
            raise ValueError("Chart is missing angle data")

    def _compare_ascendant(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> Optional[ChartDifference]:
        """
        Compare ascendant between two charts.

        Args:
            chart1: First chart data
            chart2: Second chart data

        Returns:
            ChartDifference if there's a significant difference, None otherwise
        """
        try:
            asc1_data, asc1_sign = self._get_ascendant_data(chart1)
            asc2_data, asc2_sign = self._get_ascendant_data(chart2)

            if not (asc1_data and asc2_data):
                logger.warning("Couldn't extract ascendant data from charts")
                return None

            # Calculate degree difference
            degree_diff = abs(asc1_data.get("longitude", 0) - asc2_data.get("longitude", 0))
            degree_diff = self._normalize_degree_difference(degree_diff)

            # Only create a difference if it's significant enough (more than 0.5 degrees)
            if degree_diff <= 0.5:
                return None

            # Check if sign has changed
            sign_changed = asc1_sign != asc2_sign

            difference = ChartDifference(
                element_type="angle",
                element_name="Ascendant",
                difference_type=DifferenceType.POSITION_CHANGE,
                description=f"Ascendant moved by {degree_diff:.2f}° " +
                            (f"from {asc1_sign} to {asc2_sign}" if sign_changed else f"within {asc1_sign}"),
                original_value=f"{asc1_data.get('longitude', 0):.2f}°",
                new_value=f"{asc2_data.get('longitude', 0):.2f}°",
                degree_difference=degree_diff,
                significance=min(100, max(0, degree_diff * 10)) if degree_diff > 0 else 0,
                sign_changed=sign_changed
            )

            return difference
        except Exception as e:
            logger.warning(f"Error comparing ascendants: {str(e)}")
            return None

    def _get_ascendant_data(self, chart: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract ascendant data from chart.

        Args:
            chart: Chart data

        Returns:
            Tuple of (ascendant data, ascendant sign)
        """
        try:
            if not chart.get("angles"):
                return None, None

            for angle in chart["angles"]:
                if angle.get("name", "").lower() == "ascendant":
                    sign = angle.get("sign", "Unknown")
                    return angle, sign

            return None, None
        except Exception as e:
            logger.warning(f"Error extracting ascendant data: {str(e)}")
            return None, None

    def _normalize_degree_difference(self, diff: float) -> float:
        """Normalize degree difference to be between 0 and 180."""
        while diff > 180:
            diff = 360 - diff
        return diff

    def _compare_midheaven(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> Optional[ChartDifference]:
        """
        Compare midheaven between two charts.

        Args:
            chart1: First chart data
            chart2: Second chart data

        Returns:
            ChartDifference if there's a significant difference, None otherwise
        """
        try:
            # Extract midheaven data
            mc1_data = None
            mc1_sign = "Unknown"
            mc2_data = None
            mc2_sign = "Unknown"

            if chart1.get("angles"):
                for angle in chart1["angles"]:
                    if angle.get("name", "").lower() in ["midheaven", "mc"]:
                        mc1_data = angle
                        mc1_sign = angle.get("sign", "Unknown")
                        break

            if chart2.get("angles"):
                for angle in chart2["angles"]:
                    if angle.get("name", "").lower() in ["midheaven", "mc"]:
                        mc2_data = angle
                        mc2_sign = angle.get("sign", "Unknown")
                        break

            if not (mc1_data and mc2_data):
                logger.warning("Couldn't extract midheaven data from charts")
                return None

            # Calculate degree difference
            degree_diff = abs(mc1_data.get("longitude", 0) - mc2_data.get("longitude", 0))
            degree_diff = self._normalize_degree_difference(degree_diff)

            # Only create a difference if it's significant enough (more than 0.5 degrees)
            if degree_diff <= 0.5:
                return None

            # Check if sign has changed
            sign_changed = mc1_sign != mc2_sign

            difference = ChartDifference(
                element_type="angle",
                element_name="Midheaven",
                difference_type=DifferenceType.POSITION_CHANGE,
                description=f"Midheaven moved by {degree_diff:.2f}° " +
                            (f"from {mc1_sign} to {mc2_sign}" if sign_changed else f"within {mc1_sign}"),
                original_value=f"{mc1_data.get('longitude', 0):.2f}°",
                new_value=f"{mc2_data.get('longitude', 0):.2f}°",
                degree_difference=degree_diff,
                significance=min(100, max(0, degree_diff * 8)) if degree_diff > 0 else 0,
                sign_changed=sign_changed
            )

            return difference
        except Exception as e:
            logger.warning(f"Error comparing midheaven: {str(e)}")
            return None

    def _compare_planets(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> List[ChartDifference]:
        """
        Compare planetary positions between two charts.

        Args:
            chart1: First chart data
            chart2: Second chart data

        Returns:
            List of ChartDifference objects
        """
        differences = []

        try:
            if not (chart1.get("planets") and chart2.get("planets")):
                logger.warning("Charts are missing planetary data")
                return differences

            # Create lookup dictionaries
            planets1 = {p.get("name", "").lower(): p for p in chart1["planets"]}
            planets2 = {p.get("name", "").lower(): p for p in chart2["planets"]}

            # Standard planet names to ensure we don't miss any
            standard_planets = [
                "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
                "uranus", "neptune", "pluto", "north node", "south node", "chiron"
            ]

            for planet_name in standard_planets:
                if planet_name not in planets1 or planet_name not in planets2:
                    continue

                p1 = planets1[planet_name]
                p2 = planets2[planet_name]

                # Extract data
                name = p1.get("name", planet_name).title()
                p1_lon = p1.get("longitude", 0)
                p2_lon = p2.get("longitude", 0)
                p1_sign = p1.get("sign", "Unknown")
                p2_sign = p2.get("sign", "Unknown")

                # Calculate degree difference
                degree_diff = abs(p1_lon - p2_lon)
                degree_diff = self._normalize_degree_difference(degree_diff)

                # Only create a difference if it's significant enough
                # Different thresholds for different bodies
                min_threshold = 0.1
                if planet_name in ["sun", "moon"]:
                    min_threshold = 0.2
                elif planet_name in ["mercury", "venus", "mars"]:
                    min_threshold = 0.3

                if degree_diff <= min_threshold:
                    continue

                # Check if sign has changed
                sign_changed = p1_sign != p2_sign

                # Calculate significance based on planet and degree difference
                significance = self._get_planet_significance(planet_name) * degree_diff / 5
                significance = min(100, max(0, significance))

                difference = ChartDifference(
                    element_type="planet",
                    element_name=name,
                    difference_type=DifferenceType.POSITION_CHANGE,
                    description=f"{name} moved by {degree_diff:.2f}° " +
                                (f"from {p1_sign} to {p2_sign}" if sign_changed else f"within {p1_sign}"),
                    original_value=f"{p1_lon:.2f}°",
                    new_value=f"{p2_lon:.2f}°",
                    degree_difference=degree_diff,
                    significance=significance,
                    sign_changed=sign_changed
                )

                differences.append(difference)

            return differences
        except Exception as e:
            logger.warning(f"Error comparing planets: {str(e)}")
            return differences

    def _compare_aspects(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> List[ChartDifference]:
        """
        Compare aspects between two charts.

        Args:
            chart1: First chart data
            chart2: Second chart data

        Returns:
            List of ChartDifference objects
        """
        differences = []

        try:
            if not (chart1.get("aspects") and chart2.get("aspects")):
                # If either chart is missing aspects, return empty
                return differences

            # Create lookup dictionaries
            aspects1 = {f"{a.get('planet1', '')}-{a.get('planet2', '')}-{a.get('type', '')}": a
                       for a in chart1.get("aspects", [])}
            aspects2 = {f"{a.get('planet1', '')}-{a.get('planet2', '')}-{a.get('type', '')}": a
                       for a in chart2.get("aspects", [])}

            # Find aspects in chart1 that don't exist in chart2 (disappeared aspects)
            for key, aspect in aspects1.items():
                if key not in aspects2:
                    planet1 = aspect.get("planet1", "Unknown")
                    planet2 = aspect.get("planet2", "Unknown")
                    aspect_type = aspect.get("type", "Unknown")

                    difference = ChartDifference(
                        element_type="aspect",
                        element_name=f"{planet1}-{planet2}",
                        difference_type=DifferenceType.ASPECT_REMOVED,
                        description=f"{aspect_type.title()} aspect between {planet1.title()} and {planet2.title()} no longer present",
                        original_value=f"{aspect_type.title()} ({aspect.get('orb', 0):.2f}° orb)",
                        new_value="None",
                        significance=self._get_aspect_significance(aspect_type, planet1, planet2)
                    )
                    differences.append(difference)

            # Find aspects in chart2 that don't exist in chart1 (new aspects)
            for key, aspect in aspects2.items():
                if key not in aspects1:
                    planet1 = aspect.get("planet1", "Unknown")
                    planet2 = aspect.get("planet2", "Unknown")
                    aspect_type = aspect.get("type", "Unknown")

                    difference = ChartDifference(
                        element_type="aspect",
                        element_name=f"{planet1}-{planet2}",
                        difference_type=DifferenceType.ASPECT_ADDED,
                        description=f"New {aspect_type.title()} aspect between {planet1.title()} and {planet2.title()}",
                        original_value="None",
                        new_value=f"{aspect_type.title()} ({aspect.get('orb', 0):.2f}° orb)",
                        significance=self._get_aspect_significance(aspect_type, planet1, planet2)
                    )
                    differences.append(difference)

            # Find aspects that exist in both but have significant orb changes
            for key in set(aspects1.keys()).intersection(aspects2.keys()):
                aspect1 = aspects1[key]
                aspect2 = aspects2[key]

                orb1 = aspect1.get("orb", 0)
                orb2 = aspect2.get("orb", 0)
                orb_diff = abs(orb1 - orb2)

                # Only report if orb changed significantly (more than 0.5 degrees)
                if orb_diff > 0.5:
                    planet1 = aspect1.get("planet1", "Unknown")
                    planet2 = aspect1.get("planet2", "Unknown")
                    aspect_type = aspect1.get("type", "Unknown")

                    # Determine if aspect is strengthening or weakening
                    strengthening = orb2 < orb1  # Lower orb is stronger

                    difference = ChartDifference(
                        element_type="aspect",
                        element_name=f"{planet1}-{planet2}",
                        difference_type=DifferenceType.ASPECT_CHANGED,
                        description=f"{aspect_type.title()} aspect between {planet1.title()} and {planet2.title()} " +
                                   (f"strengthened by {orb_diff:.2f}°" if strengthening else f"weakened by {orb_diff:.2f}°"),
                        original_value=f"{orb1:.2f}° orb",
                        new_value=f"{orb2:.2f}° orb",
                        significance=min(100, max(0, self._get_aspect_significance(aspect_type, planet1, planet2) * orb_diff / 3))
                    )
                    differences.append(difference)

            return differences
        except Exception as e:
            logger.warning(f"Error comparing aspects: {str(e)}")
            return differences

    def _compare_houses(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> List[ChartDifference]:
        """
        Compare house cusps between two charts.

        Args:
            chart1: First chart data
            chart2: Second chart data

        Returns:
            List of ChartDifference objects
        """
        differences = []

        try:
            if not (chart1.get("houses") and chart2.get("houses")):
                logger.warning("Charts are missing house data")
                return differences

            # Create lookup dictionaries
            houses1 = {h.get("house", 0): h for h in chart1["houses"]}
            houses2 = {h.get("house", 0): h for h in chart2["houses"]}

            # Compare each house
            for i in range(1, 13):  # 12 houses
                if i not in houses1 or i not in houses2:
                    continue

                h1 = houses1[i]
                h2 = houses2[i]

                # Extract data
                h1_lon = h1.get("longitude", 0)
                h2_lon = h2.get("longitude", 0)
                h1_sign = h1.get("sign", "Unknown")
                h2_sign = h2.get("sign", "Unknown")

                # Calculate degree difference
                degree_diff = abs(h1_lon - h2_lon)
                degree_diff = self._normalize_degree_difference(degree_diff)

                # Only create a difference if it's significant enough
                if degree_diff <= 0.5:
                    continue

                # Check if sign has changed
                sign_changed = h1_sign != h2_sign

                # Calculate significance based on house
                significance = self._get_house_significance(i) * degree_diff / 5
                significance = min(100, max(0, significance))

                difference = ChartDifference(
                    element_type="house",
                    element_name=f"House {i}",
                    difference_type=DifferenceType.POSITION_CHANGE,
                    description=f"House {i} cusp moved by {degree_diff:.2f}° " +
                                (f"from {h1_sign} to {h2_sign}" if sign_changed else f"within {h1_sign}"),
                    original_value=f"{h1_lon:.2f}°",
                    new_value=f"{h2_lon:.2f}°",
                    degree_difference=degree_diff,
                    significance=significance,
                    sign_changed=sign_changed
                )

                differences.append(difference)

            return differences
        except Exception as e:
            logger.warning(f"Error comparing houses: {str(e)}")
            return differences

    def _generate_summary(
        self,
        chart1: Dict[str, Any],
        chart2: Dict[str, Any],
        differences: List[ChartDifference],
        overall_impact: Optional[float]
    ) -> str:
        """
        Generate a summary of the chart comparison.

        Args:
            chart1: First chart data
            chart2: Second chart data
            differences: List of differences
            overall_impact: Overall impact score

        Returns:
            Summary text
        """
        if not differences:
            return "The charts show no significant differences."

        # Count differences by type
        angle_diffs = [d for d in differences if d.element_type == "angle"]
        planet_diffs = [d for d in differences if d.element_type == "planet"]
        aspect_diffs = [d for d in differences if d.element_type == "aspect"]
        house_diffs = [d for d in differences if d.element_type == "house"]

        # Format overall impact
        impact_text = ""
        if overall_impact is not None:
            if overall_impact < 20:
                impact_text = " with minimal impact"
            elif overall_impact < 50:
                impact_text = " with moderate impact"
            else:
                impact_text = " with significant impact"

        # Create summary
        summary_parts = []
        summary_parts.append(f"Comparison reveals {len(differences)} differences{impact_text}.")

        # Add angle summary
        if angle_diffs:
            angle_text = ", ".join([d.element_name for d in angle_diffs])
            summary_parts.append(f"Angular changes to {angle_text}.")

        # Add planet summary (focus on the significant ones)
        significant_planets = sorted(
            [d for d in planet_diffs if d.significance and d.significance > 30],
            key=lambda x: x.significance or 0,
            reverse=True
        )
        if significant_planets:
            top_planets = significant_planets[:3]  # Top 3 most significant
            planets_text = ", ".join([d.element_name for d in top_planets])
            summary_parts.append(f"Notable planetary shifts in {planets_text}.")

        # Add aspect summary
        if aspect_diffs:
            added = len([d for d in aspect_diffs if d.difference_type == DifferenceType.ASPECT_ADDED])
            removed = len([d for d in aspect_diffs if d.difference_type == DifferenceType.ASPECT_REMOVED])
            changed = len([d for d in aspect_diffs if d.difference_type == DifferenceType.ASPECT_CHANGED])

            if added > 0:
                summary_parts.append(f"{added} new aspect{'s' if added != 1 else ''} formed.")
            if removed > 0:
                summary_parts.append(f"{removed} aspect{'s' if removed != 1 else ''} dissolved.")
            if changed > 0:
                summary_parts.append(f"{changed} aspect{'s' if changed != 1 else ''} changed in strength.")

        return " ".join(summary_parts)

    def _get_planet_significance(self, planet_name: str) -> float:
        """
        Get significance weight for a planet.

        Args:
            planet_name: Name of the planet

        Returns:
            Significance weight (0-10)
        """
        # Define significance weights for planets
        significance_map = {
            "sun": 10.0,
            "moon": 10.0,
            "ascendant": 9.5,
            "midheaven": 9.0,
            "mercury": 8.0,
            "venus": 7.5,
            "mars": 7.0,
            "jupiter": 6.5,
            "saturn": 6.0,
            "uranus": 5.0,
            "neptune": 4.5,
            "pluto": 4.0,
            "north node": 3.5,
            "south node": 3.0,
            "chiron": 2.5,
        }

        return significance_map.get(planet_name.lower(), 3.0)

    def _get_aspect_significance(self, aspect_type: str, planet1: str, planet2: str) -> float:
        """
        Get significance weight for an aspect.

        Args:
            aspect_type: Type of aspect
            planet1: First planet
            planet2: Second planet

        Returns:
            Significance weight (0-10)
        """
        # Define significance weights for aspects
        aspect_weights = {
            "conjunction": 8.0,
            "opposition": 7.5,
            "trine": 7.0,
            "square": 6.5,
            "sextile": 6.0,
            "quincunx": 4.0,
            "semisextile": 3.5,
            "semisquare": 3.0,
            "sesquiquadrate": 3.0,
            "quintile": 2.5,
            "biquintile": 2.0,
        }

        # Get base significance from aspect type
        base_significance = aspect_weights.get(aspect_type.lower(), 2.0)

        # Adjust based on planets involved
        planet1_significance = self._get_planet_significance(planet1)
        planet2_significance = self._get_planet_significance(planet2)

        # Average the planet significances and multiply by aspect weight
        planet_avg = (planet1_significance + planet2_significance) / 2

        return (base_significance * planet_avg) / 10

    def _get_house_significance(self, house_number: int) -> float:
        """
        Get significance weight for a house.

        Args:
            house_number: House number (1-12)

        Returns:
            Significance weight (0-10)
        """
        # Define significance weights for houses
        # Angular houses (1, 4, 7, 10) are most significant
        significance_map = {
            1: 10.0,  # Ascendant
            10: 9.5,  # Midheaven
            7: 9.0,   # Descendant
            4: 8.5,   # IC
            2: 6.0,
            3: 5.5,
            5: 7.0,
            6: 5.0,
            8: 7.5,
            9: 6.5,
            11: 6.0,
            12: 7.0,
        }

        return significance_map.get(house_number, 5.0)
