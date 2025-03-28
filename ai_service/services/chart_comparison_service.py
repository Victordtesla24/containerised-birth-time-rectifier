"""
Chart comparison service for the Birth Time Rectifier API.
Provides functionality to compare original and rectified birth charts.
"""

import logging
import uuid
import math
import os
import tempfile
import base64
import traceback
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ai_service.models.chart_comparison import (
    ChartDifference, DifferenceType, PlanetaryPosition,
    AspectData, ChartComparisonResponse
)
from ai_service.services.chart_utils import retrieve_chart
from ai_service.utils.chart_visualizer import generate_comparison_chart

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
        include_significance: bool = True,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare two charts and generate a comprehensive analysis with visualization.

        Args:
            chart1_id: ID of the first chart
            chart2_id: ID of the second chart
            comparison_type: Type of comparison to perform
            include_significance: Whether to include significance metrics
            output_path: Optional path to save visualization

        Returns:
            Dictionary containing comparison results and visualization
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
        comparison_id = f"comp_{uuid.uuid4().hex[:8]}"
        comparison_response = ChartComparisonResponse(
            comparison_id=comparison_id,
            chart1_id=chart1_id,
            chart2_id=chart2_id,
            differences=[],
            summary="",
            comparison_type=comparison_type
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

        # Generate visual comparison
        visualization_data = self._generate_visualization(chart1, chart2, differences, output_path)

        # Return formatted response
        return {
            "comparison_id": comparison_id,
            "comparison_timestamp": datetime.now().isoformat(),
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
            "differences": [diff.model_dump() if hasattr(diff, 'model_dump') else diff.dict() for diff in differences],
            "overall_impact": overall_impact,
            "summary": summary,
            "visualization": visualization_data,
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

            # Ensure signs are not None for PlanetaryPosition
            safe_asc1_sign = asc1_sign or "Unknown"
            safe_asc2_sign = asc2_sign or "Unknown"

            difference = ChartDifference(
                type=DifferenceType.POSITION_CHANGE,
                description=f"Ascendant moved by {degree_diff:.2f}° " +
                            (f"from {safe_asc1_sign} to {safe_asc2_sign}" if sign_changed else f"within {safe_asc1_sign}"),
                significance=min(100, max(0, degree_diff * 10)) if degree_diff > 0 else 0,
                chart1_position=PlanetaryPosition(
                    sign=safe_asc1_sign,
                    degree=asc1_data.get('longitude', 0) % 30,
                    house=1
                ),
                chart2_position=PlanetaryPosition(
                    sign=safe_asc2_sign,
                    degree=asc2_data.get('longitude', 0) % 30,
                    house=1
                )
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
                type=DifferenceType.POSITION_CHANGE,
                description=f"Midheaven moved by {degree_diff:.2f}° " +
                            (f"from {mc1_sign} to {mc2_sign}" if sign_changed else f"within {mc1_sign}"),
                significance=min(100, max(0, degree_diff * 8)) if degree_diff > 0 else 0,
                chart1_position=PlanetaryPosition(
                    sign=mc1_sign,
                    degree=mc1_data.get('longitude', 0) % 30,
                    house=10  # Midheaven is typically associated with house 10
                ),
                chart2_position=PlanetaryPosition(
                    sign=mc2_sign,
                    degree=mc2_data.get('longitude', 0) % 30,
                    house=10
                )
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
                    type=DifferenceType.POSITION_CHANGE,
                    description=f"{name} moved by {degree_diff:.2f}° " +
                                (f"from {p1_sign} to {p2_sign}" if sign_changed else f"within {p1_sign}"),
                    significance=significance,
                    chart1_position=PlanetaryPosition(
                        sign=p1_sign,
                        degree=p1_lon % 30,
                        house=p1.get("house", 0)
                    ),
                    chart2_position=PlanetaryPosition(
                        sign=p2_sign,
                        degree=p2_lon % 30,
                        house=p2.get("house", 0)
                    )
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
                        type=DifferenceType.ASPECT_REMOVED,
                        description=f"{aspect_type.title()} aspect between {planet1.title()} and {planet2.title()} no longer present",
                        significance=self._get_aspect_significance(aspect_type, planet1, planet2),
                        chart1_position=PlanetaryPosition(
                            sign=aspect.get("sign1", "Unknown"),
                            degree=aspect.get("degree1", 0),
                            house=aspect.get("house1", 0)
                        ),
                        chart2_position=PlanetaryPosition(
                            sign="Unknown",
                            degree=0,
                            house=0
                        )
                    )
                    differences.append(difference)

            # Find aspects in chart2 that don't exist in chart1 (new aspects)
            for key, aspect in aspects2.items():
                if key not in aspects1:
                    planet1 = aspect.get("planet1", "Unknown")
                    planet2 = aspect.get("planet2", "Unknown")
                    aspect_type = aspect.get("type", "Unknown")

                    difference = ChartDifference(
                        type=DifferenceType.ASPECT_ADDED,
                        description=f"New {aspect_type.title()} aspect between {planet1.title()} and {planet2.title()}",
                        significance=self._get_aspect_significance(aspect_type, planet1, planet2),
                        chart1_position=PlanetaryPosition(
                            sign="Unknown",
                            degree=0,
                            house=0
                        ),
                        chart2_position=PlanetaryPosition(
                            sign=aspect.get("sign1", "Unknown"),
                            degree=aspect.get("degree1", 0),
                            house=aspect.get("house1", 0)
                        )
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
                        type=DifferenceType.ASPECT_CHANGED,
                        description=f"{aspect_type.title()} aspect between {planet1.title()} and {planet2.title()} " +
                                   (f"strengthened by {orb_diff:.2f}°" if strengthening else f"weakened by {orb_diff:.2f}°"),
                        significance=min(100, max(0, self._get_aspect_significance(aspect_type, planet1, planet2) * orb_diff / 3)),
                        chart1_position=PlanetaryPosition(
                            sign=aspect1.get("sign1", "Unknown"),
                            degree=aspect1.get("degree1", 0),
                            house=aspect1.get("house1", 0)
                        ),
                        chart2_position=PlanetaryPosition(
                            sign=aspect2.get("sign1", "Unknown"),
                            degree=aspect2.get("degree1", 0),
                            house=aspect2.get("house1", 0)
                        )
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
                    type=DifferenceType.POSITION_CHANGE,
                    description=f"House {i} cusp moved by {degree_diff:.2f}° " +
                                (f"from {h1_sign} to {h2_sign}" if sign_changed else f"within {h1_sign}"),
                    significance=significance,
                    chart1_position=PlanetaryPosition(
                        sign=h1_sign,
                        degree=h1_lon % 30,
                        house=i
                    ),
                    chart2_position=PlanetaryPosition(
                        sign=h2_sign,
                        degree=h2_lon % 30,
                        house=i
                    )
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
        Generate a comprehensive summary of the chart comparison with deep astrological insight.

        Args:
            chart1: First chart data
            chart2: Second chart data
            differences: List of differences
            overall_impact: Overall impact score

        Returns:
            Detailed astrological summary text
        """
        if not differences:
            return "The charts show no significant differences in planetary positions or aspects."

        # Get birth time difference if available
        time_diff_minutes = 0
        birth_time1 = chart1.get("birth_time", "") or chart1.get("birth_details", {}).get("time", "")
        birth_time2 = chart2.get("birth_time", "") or chart2.get("birth_details", {}).get("time", "")

        if birth_time1 and birth_time2:
            try:
                # Extract hours and minutes from time strings
                from datetime import datetime
                time1 = datetime.strptime(birth_time1.split(".")[0], "%H:%M:%S")
                time2 = datetime.strptime(birth_time2.split(".")[0], "%H:%M:%S")
                diff = time2 - time1
                time_diff_minutes = abs(diff.total_seconds() / 60)
            except (ValueError, IndexError):
                # Handle various time format issues
                pass

        time_diff_text = f" resulting from a {time_diff_minutes:.0f} minute birth time adjustment" if time_diff_minutes > 0 else ""

        # Categorize and count differences by type with proper null checks
        angle_diffs = [d for d in differences if d.chart1_position is not None and d.chart1_position.house in [1, 10]]
        planet_diffs = [d for d in differences if d.type == DifferenceType.POSITION_CHANGE and
                        d.chart1_position is not None and not (d.chart1_position.house in [1, 10])]
        aspect_diffs = [d for d in differences if d.type in [DifferenceType.ASPECT_ADDED,
                                                           DifferenceType.ASPECT_REMOVED,
                                                           DifferenceType.ASPECT_CHANGED]]
        house_diffs = [d for d in differences if d.type == DifferenceType.POSITION_CHANGE and
                       d.chart1_position is not None and d.chart1_position.house is not None and
                       d.chart1_position.house > 0]

        # Sort differences by significance for better analysis
        significant_diffs = sorted(differences, key=lambda x: x.significance or 0, reverse=True)
        top_diffs = significant_diffs[:min(5, len(significant_diffs))]

        # Format overall impact with greater astrological context
        impact_level = ""
        impact_description = ""
        if overall_impact is not None:
            if overall_impact < 15:
                impact_level = "minimal"
                impact_description = "suggesting minor refinements to timing"
            elif overall_impact < 35:
                impact_level = "moderate"
                impact_description = "indicating notable shifts in planetary dynamics"
            elif overall_impact < 60:
                impact_level = "significant"
                impact_description = "revealing substantial changes in chart interpretation"
            else:
                impact_level = "transformative"
                impact_description = "fundamentally altering key chart dynamics and interpretations"

        # Create a more insightful and astrologically meaningful summary
        summary_parts = []

        # Opening statement
        summary_parts.append(f"Chart comparison reveals {len(differences)} astrological differences{time_diff_text}, "
                            f"with {impact_level} overall impact ({overall_impact:.1f}%) {impact_description}.")

        # Analyze angular changes (ascendant and midheaven)
        if angle_diffs:
            asc_diff = next((d for d in angle_diffs if d.description and "Ascendant" in d.description), None)
            mc_diff = next((d for d in angle_diffs if d.description and "Midheaven" in d.description), None)

            angle_texts = []
            if asc_diff:
                # Check if ascendant changed signs
                sign_change = "crossing into a new sign" if (asc_diff.chart1_position is not None and
                                                            asc_diff.chart2_position is not None and
                                                            asc_diff.chart1_position.sign != asc_diff.chart2_position.sign) else "within same sign"
                angle_texts.append(f"Ascendant shifted {sign_change} ({asc_diff.significance:.1f}% significance)")

            if mc_diff:
                # Check if midheaven changed signs
                sign_change = "crossing into a new sign" if (mc_diff.chart1_position is not None and
                                                           mc_diff.chart2_position is not None and
                                                           mc_diff.chart1_position.sign != mc_diff.chart2_position.sign) else "within same sign"
                angle_texts.append(f"Midheaven shifted {sign_change} ({mc_diff.significance:.1f}% significance)")

            if angle_texts:
                angle_impact = "dramatically altering chart interpretation" if any(d.significance and d.significance > 50 for d in angle_diffs) else \
                              "significantly shifting house positions" if any(d.significance and d.significance > 30 for d in angle_diffs) else \
                              "modifying overall chart dynamics"
                summary_parts.append(f"Angular changes: {', '.join(angle_texts)}, {angle_impact}.")

        # Analyze planetary position changes with astrological context
        if planet_diffs:
            # Focus on most significant planet changes
            sig_planets = sorted([d for d in planet_diffs if d.significance and d.significance > 20],
                                key=lambda x: x.significance or 0, reverse=True)

            # Check for planets changing houses
            house_changing_planets = [d for d in planet_diffs if d.chart1_position and d.chart2_position and
                                     d.chart1_position.house != d.chart2_position.house]

            # Check for planets changing signs
            sign_changing_planets = [d for d in planet_diffs if d.chart1_position and d.chart2_position and
                                    d.chart1_position.sign != d.chart2_position.sign]

            planet_texts = []
            if sig_planets:
                top_planets = sig_planets[:min(3, len(sig_planets))]
                planet_names = [d.description.split(" moved")[0] for d in top_planets]
                planet_texts.append(f"Notable shifts in {', '.join(planet_names)}")

            if house_changing_planets:
                num_changing = len(house_changing_planets)
                planet_texts.append(f"{num_changing} planet{'s' if num_changing != 1 else ''} changed houses")

            if sign_changing_planets:
                num_changing = len(sign_changing_planets)
                planet_texts.append(f"{num_changing} planet{'s' if num_changing != 1 else ''} changed zodiac signs")

            if planet_texts:
                planetary_impact = "substantially altering life area emphasis" if len(house_changing_planets) > 2 else \
                                  "shifting planetary energies across different domains" if house_changing_planets else \
                                  "refining planetary expressions"
                summary_parts.append(f"Planetary positions: {'; '.join(planet_texts)}, {planetary_impact}.")

        # Analyze aspect changes with deeper astrological meaning
        if aspect_diffs:
            added = [d for d in aspect_diffs if d.type == DifferenceType.ASPECT_ADDED]
            removed = [d for d in aspect_diffs if d.type == DifferenceType.ASPECT_REMOVED]
            changed = [d for d in aspect_diffs if d.type == DifferenceType.ASPECT_CHANGED]

            # Check for significant aspect changes
            sig_aspects = [d for d in aspect_diffs if d.significance and d.significance > 40]

            aspect_texts = []
            if added:
                num_added = len(added)
                # Identify most significant new aspect
                most_sig_new = max(added, key=lambda x: x.significance or 0) if added else None
                if most_sig_new and most_sig_new.description:
                    aspect_name = most_sig_new.description.split("New ")[1].split(" aspect")[0]
                    planets = most_sig_new.description.split("between ")[1].split(" and ")
                    planet1, planet2 = planets[0], planets[1].split(",")[0] if "," in planets[1] else planets[1]
                    aspect_texts.append(f"{num_added} new aspect{'s' if num_added != 1 else ''} formed "
                                       f"(notably {aspect_name} between {planet1} and {planet2})")
                else:
                    aspect_texts.append(f"{num_added} new aspect{'s' if num_added != 1 else ''} formed")

            if removed:
                num_removed = len(removed)
                aspect_texts.append(f"{num_removed} aspect{'s' if num_removed != 1 else ''} dissolved")

            if changed:
                num_changed = len(changed)
                # Count strengthened vs weakened aspects
                strengthened = len([d for d in changed if "strengthened" in d.description])
                weakened = len([d for d in changed if "weakened" in d.description])

                if strengthened > weakened:
                    aspect_texts.append(f"{num_changed} aspect{'s' if num_changed != 1 else ''} changed "
                                      f"(mostly strengthened)")
                elif weakened > strengthened:
                    aspect_texts.append(f"{num_changed} aspect{'s' if num_changed != 1 else ''} changed "
                                      f"(mostly weakened)")
                else:
                    aspect_texts.append(f"{num_changed} aspect{'s' if num_changed != 1 else ''} changed in orb")

            if aspect_texts:
                aspect_impact = "dramatically reshaping planetary relationships" if len(sig_aspects) > 2 else \
                               "altering the dynamic interplay of energies" if sig_aspects else \
                               "subtly adjusting planetary connections"
                summary_parts.append(f"Aspect changes: {'; '.join(aspect_texts)}, {aspect_impact}.")

        # Analyze house cusp changes and their astrological meaning
        if house_diffs:
            # Count significant house changes
            sig_houses = [d for d in house_diffs if d.significance and d.significance > 30]
            # Check for houses changing signs
            sign_changing_houses = [d for d in house_diffs if d.chart1_position and d.chart2_position and
                                   d.chart1_position.sign != d.chart2_position.sign]

            house_texts = []
            if sig_houses:
                # Focus on angular and succedent houses (1,4,7,10,2,5,8,11)
                angular_houses = [d for d in sig_houses if d.chart1_position and d.chart1_position.house in [1,4,7,10]]
                succedent_houses = [d for d in sig_houses if d.chart1_position and d.chart1_position.house in [2,5,8,11]]

                if angular_houses:
                    houses_text = ", ".join([f"House {d.chart1_position.house}" for d in angular_houses
                                           if d.chart1_position is not None])
                    house_texts.append(f"Angular houses shifted ({houses_text})")

                if succedent_houses:
                    houses_text = ", ".join([f"House {d.chart1_position.house}" for d in succedent_houses
                                           if d.chart1_position is not None])
                    house_texts.append(f"Succedent houses shifted ({houses_text})")

            if sign_changing_houses:
                num_changing = len(sign_changing_houses)
                house_texts.append(f"{num_changing} house cusp{'s' if num_changing != 1 else ''} changed signs")

            if house_texts:
                house_impact = "redefining life area interpretations" if len(sign_changing_houses) > 3 else \
                              "shifting focus of key life domains" if sign_changing_houses else \
                              "refining life area expressions"
                summary_parts.append(f"House changes: {'; '.join(house_texts)}, {house_impact}.")

        # Add astrological interpretation summary based on overall pattern of changes
        if overall_impact is not None:
            if "Ascendant" in "".join([d.description for d in angle_diffs if d.description]):
                summary_parts.append(f"This birth time adjustment primarily impacts self-expression, physical appearance, "
                                   f"and how one approaches life's challenges.")
            elif "Midheaven" in "".join([d.description for d in angle_diffs if d.description]):
                summary_parts.append(f"This rectification particularly affects career trajectory, public reputation, "
                                   f"and relationship with authority figures.")
            elif len(sign_changing_planets) > 2:
                summary_parts.append(f"Multiple planets changing signs indicates a significant reframing of core "
                                   f"personality traits and life experiences.")
            elif len(house_changing_planets) > 2:
                summary_parts.append(f"Several planets changing houses suggests a redistribution of energy and focus "
                                   f"across different areas of life.")
            elif len(added) > len(removed) and len(added) > 2:
                summary_parts.append(f"The formation of new aspects enriches the chart with additional planetary "
                                   f"connections, potentially activating previously dormant energies.")
            elif len(removed) > len(added) and len(removed) > 2:
                summary_parts.append(f"The dissolution of multiple aspects suggests a simplification of the chart's "
                                   f"dynamics, potentially reducing internal tensions or conflicts.")

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

    def _generate_visualization(self, chart1: Dict[str, Any], chart2: Dict[str, Any],
                              differences: List[ChartDifference], output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate visualization for chart comparison.

        Args:
            chart1: First chart data
            chart2: Second chart data
            differences: List of differences
            output_path: Optional path to save visualization

        Returns:
            Dictionary containing visualization data
        """
        try:
            # Create a temporary file if no output path is provided
            if not output_path:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    temp_path = tmp.name
            else:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                temp_path = output_path

            # Generate the comparison chart image
            comparison_result = generate_comparison_chart(chart1, chart2, temp_path)

            # Process the result based on its type
            if isinstance(comparison_result, str):
                # Result is a file path
                image_path = comparison_result

                # Read image and encode as base64 for API response
                with open(image_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')

                # Return visualization data
                result = {
                    "image_data": f"data:image/png;base64,{img_data}",
                    "file_path": image_path if output_path else None,
                    "format": "png",
                    "encoding": "base64"
                }

                # Delete temporary file if no output path was provided
                if not output_path and os.path.exists(temp_path):
                    os.unlink(temp_path)

                return result

            elif isinstance(comparison_result, dict):
                # Result is already a dictionary with data
                if "image_data" in comparison_result:
                    # The function already returned base64 data
                    return comparison_result
                else:
                    # The function returned a dict with file path
                    image_path = comparison_result.get("file_path", "")

                    if image_path and os.path.exists(image_path):
                        # Read image and encode as base64 for API response
                        with open(image_path, 'rb') as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')

                        # Add base64 data to result
                        comparison_result["image_data"] = f"data:image/png;base64,{img_data}"
                        comparison_result["encoding"] = "base64"

                    return comparison_result

            # Raise an exception for unexpected result type
            error_msg = "Failed to generate comparison visualization due to unexpected result type"
            logger.error(error_msg)
            raise ValueError(error_msg)

        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            logger.error(traceback.format_exc())

            # Re-raise the exception instead of returning an error object
            raise RuntimeError(f"Chart comparison visualization failed: {str(e)}") from e

    def compare_chart_data(self, chart1: Dict[str, Any], chart2: Dict[str, Any], output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Compare two chart data objects directly and generate a comprehensive analysis with visualization.

        Args:
            chart1: First chart data
            chart2: Second chart data
            output_path: Optional path to save visualization

        Returns:
            Dictionary containing comparison results and visualization
        """
        try:
            # Normalize chart data formats
            chart1_normalized = self._normalize_chart_data(chart1)
            chart2_normalized = self._normalize_chart_data(chart2)

            # Add chart titles for better visualization
            chart1_normalized["title"] = chart1.get("title", "Original Chart")
            chart2_normalized["title"] = chart2.get("title", "Rectified Chart")

            # Generate comparison ID
            comparison_id = f"comp_{uuid.uuid4().hex[:8]}"

            # Calculate differences
            differences = []

            # Ascendant comparison
            ascendant_diff = self._compare_ascendant(chart1_normalized, chart2_normalized)
            if ascendant_diff:
                differences.append(ascendant_diff)

            # Midheaven comparison
            midheaven_diff = self._compare_midheaven(chart1_normalized, chart2_normalized)
            if midheaven_diff:
                differences.append(midheaven_diff)

            # Planet positions comparison
            planet_diffs = self._compare_planets(chart1_normalized, chart2_normalized)
            differences.extend(planet_diffs)

            # Aspects comparison
            aspect_diffs = self._compare_aspects(chart1_normalized, chart2_normalized)
            differences.extend(aspect_diffs)

            # House cusps comparison
            house_diffs = self._compare_houses(chart1_normalized, chart2_normalized)
            differences.extend(house_diffs)

            # Calculate overall impact score
            overall_impact = None
            if differences:
                impact_sum = sum(d.significance if d.significance else 0 for d in differences)
                overall_impact = min(100, max(0, impact_sum / len(differences) * 100))

            # Generate summary text
            summary = self._generate_summary(chart1_normalized, chart2_normalized, differences, overall_impact)

            # Generate visual comparison
            visualization_data = self._generate_visualization(chart1_normalized, chart2_normalized, differences, output_path)

            # Return combined results
            result = {
                "comparison_id": comparison_id,
                "comparison_timestamp": datetime.now().isoformat(),
                "differences": [diff.model_dump() if hasattr(diff, 'model_dump') else diff.dict() for diff in differences],
                "overall_impact": overall_impact,
                "summary": summary,
                "visualization": visualization_data,
                "chart1_id": chart1.get("chart_id", "chart1"),
                "chart2_id": chart2.get("chart_id", "chart2"),
                "chart1_data": {
                    "date": chart1.get("birth_date", chart1.get("birth_details", {}).get("date", "")),
                    "time": chart1.get("birth_time", chart1.get("birth_details", {}).get("time", "")),
                    "location": chart1.get("birth_location", chart1.get("birth_details", {}).get("location", ""))
                },
                "chart2_data": {
                    "date": chart2.get("birth_date", chart2.get("birth_details", {}).get("date", "")),
                    "time": chart2.get("birth_time", chart2.get("birth_details", {}).get("time", "")),
                    "location": chart2.get("birth_location", chart2.get("birth_details", {}).get("location", ""))
                }
            }

            return result
        except Exception as e:
            logger.error(f"Error comparing charts: {e}")
            logger.error(traceback.format_exc())
            raise

    def _normalize_chart_data(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize chart data to ensure consistent format for comparison.

        Args:
            chart_data: Chart data to normalize

        Returns:
            Normalized chart data
        """
        normalized_data = chart_data.copy()

        # Ensure planets are in a dictionary format
        planets = normalized_data.get("planets", {})
        if isinstance(planets, list):
            # Convert list of planets to dictionary
            planets_dict = {}
            for planet in planets:
                if isinstance(planet, dict) and "name" in planet:
                    planets_dict[planet["name"]] = planet
            normalized_data["planets"] = planets_dict

        # Ensure houses are in a consistent format
        houses = normalized_data.get("houses", [])
        if isinstance(houses, dict):
            # Convert dictionary of houses to list
            houses_list = []
            for i in range(1, 13):
                house_key = str(i)
                if house_key in houses:
                    house_data = houses[house_key]
                    if isinstance(house_data, dict):
                        house_data["house"] = i
                        houses_list.append(house_data)
            normalized_data["houses"] = houses_list

        # Add empty aspects list if not present
        if "aspects" not in normalized_data:
            normalized_data["aspects"] = []

        return normalized_data
