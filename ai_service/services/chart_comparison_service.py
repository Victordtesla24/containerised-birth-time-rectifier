"""
Chart comparison service for the Birth Time Rectifier API.
Provides functionality to compare original and rectified birth charts.
"""

import logging
import uuid
import math
from typing import List, Dict, Any, Optional, Tuple

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

    def compare_charts(
        self,
        chart1_id: str,
        chart2_id: str,
        comparison_type: str = "differences",
        include_significance: bool = True
    ) -> ChartComparisonResponse:
        """
        Compare two charts and identify the differences between them

        Args:
            chart1_id: ID of the first chart (usually the original chart)
            chart2_id: ID of the second chart (usually the rectified chart)
            comparison_type: Type of comparison to perform
                             ("differences", "full", or "summary")
            include_significance: Whether to include significance scores
                                 for each difference

        Returns:
            ChartComparisonResponse with the comparison results

        Raises:
            ValueError: If chart_service is not provided or charts are not found
        """
        # Generate a unique ID for this comparison
        comparison_id = f"comp_{uuid.uuid4().hex[:12]}"

        try:
            # Retrieve both charts using the utils.retrieve_chart function
            try:
                chart1 = retrieve_chart(chart1_id)
                if not chart1:
                    logger.error(f"Chart not found: {chart1_id}")
                    raise ValueError(f"Chart not found: {chart1_id}")
            except Exception as e:
                logger.error(f"Error retrieving chart1 (ID: {chart1_id}): {str(e)}")
                raise ValueError(f"Chart not found: {chart1_id}")

            try:
                chart2 = retrieve_chart(chart2_id)
                if not chart2:
                    logger.error(f"Chart not found: {chart2_id}")
                    raise ValueError(f"Chart not found: {chart2_id}")
            except Exception as e:
                logger.error(f"Error retrieving chart2 (ID: {chart2_id}): {str(e)}")
                raise ValueError(f"Chart not found: {chart2_id}")

            # Initialize differences list
            differences = []

            # Compare Ascendant
            ascendant_diff = self._compare_ascendant(chart1, chart2)
            if ascendant_diff:
                differences.append(ascendant_diff)

            # Compare Midheaven
            midheaven_diff = self._compare_midheaven(chart1, chart2)
            if midheaven_diff:
                differences.append(midheaven_diff)

            # Compare planets by sign and house
            planet_diffs = self._compare_planets(chart1, chart2)
            differences.extend(planet_diffs)

            # Compare aspects
            aspect_diffs = self._compare_aspects(chart1, chart2)
            differences.extend(aspect_diffs)

            # Compare house cusps
            house_diffs = self._compare_houses(chart1, chart2)
            differences.extend(house_diffs)

            # Calculate overall impact if requested
            overall_impact = None
            if include_significance and differences:
                impact_sum = sum(diff.significance for diff in differences)
                overall_impact = min(1.0, impact_sum / (len(differences) * 0.8))

            # Generate summary if requested
            summary = None
            if comparison_type in ["full", "summary"]:
                summary = self._generate_summary(chart1, chart2, differences, overall_impact)

            # Create and return comparison response
            return ChartComparisonResponse(
                comparison_id=comparison_id,
                chart1_id=chart1_id,
                chart2_id=chart2_id,
                comparison_type=comparison_type,
                differences=differences,
                summary=summary,
                overall_impact=overall_impact
            )
        except Exception as e:
            # Log detailed error
            logger.error(f"Error comparing charts: {str(e)}", exc_info=True)

            # Return a minimal valid response with error details to avoid 500 errors
            return ChartComparisonResponse(
                comparison_id=comparison_id,
                chart1_id=chart1_id,
                chart2_id=chart2_id,
                comparison_type=comparison_type,
                differences=[],
                summary=f"Error during chart comparison: {str(e)}",
                overall_impact=0.0
            )

    def _compare_ascendant(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> Optional[ChartDifference]:
        """Compare Ascendant positions between two charts"""
        asc1 = chart1.get("ascendant", {})
        asc2 = chart2.get("ascendant", {})

        # If either chart is missing ascendant data, skip comparison
        if not asc1 or not asc2:
            return None

        sign1 = asc1.get("sign")
        sign2 = asc2.get("sign")
        degree1 = asc1.get("degree", 0)
        degree2 = asc2.get("degree", 0)

        # Check if signs differ
        if sign1 != sign2:
            return ChartDifference(
                type=DifferenceType.ASCENDANT_SHIFT,
                description=f"Ascendant has changed from {sign1} to {sign2}",
                significance=1.0,  # Major change
                chart1_position=PlanetaryPosition(sign=sign1, degree=degree1),
                chart2_position=PlanetaryPosition(sign=sign2, degree=degree2)
            )

        # Check if degrees differ significantly within same sign
        degree_diff = abs(degree1 - degree2)
        if degree_diff > 1.0:
            # Calculate significance based on degree difference
            # Anything over 5 degrees is considered very significant
            significance = min(1.0, degree_diff / 5.0)

            return ChartDifference(
                type=DifferenceType.ASCENDANT_SHIFT,
                description=f"Ascendant has shifted {degree_diff:.2f}° within {sign1}",
                significance=significance,
                chart1_position=PlanetaryPosition(sign=sign1, degree=degree1),
                chart2_position=PlanetaryPosition(sign=sign2, degree=degree2)
            )

        return None

    def _compare_midheaven(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> Optional[ChartDifference]:
        """Compare Midheaven positions between two charts"""
        mc1 = chart1.get("midheaven", {})
        mc2 = chart2.get("midheaven", {})

        # If either chart is missing midheaven data, skip comparison
        if not mc1 or not mc2:
            return None

        sign1 = mc1.get("sign")
        sign2 = mc2.get("sign")
        degree1 = mc1.get("degree", 0)
        degree2 = mc2.get("degree", 0)

        # Check if signs differ
        if sign1 != sign2:
            return ChartDifference(
                type=DifferenceType.MIDHEAVEN_SHIFT,
                description=f"Midheaven has changed from {sign1} to {sign2}",
                significance=0.9,  # Major change
                chart1_position=PlanetaryPosition(sign=sign1, degree=degree1),
                chart2_position=PlanetaryPosition(sign=sign2, degree=degree2)
            )

        # Check if degrees differ significantly within same sign
        degree_diff = abs(degree1 - degree2)
        if degree_diff > 1.0:
            # Calculate significance based on degree difference
            # Anything over 5 degrees is considered very significant
            significance = min(0.9, degree_diff / 5.0)

            return ChartDifference(
                type=DifferenceType.MIDHEAVEN_SHIFT,
                description=f"Midheaven has shifted {degree_diff:.2f}° within {sign1}",
                significance=significance,
                chart1_position=PlanetaryPosition(sign=sign1, degree=degree1),
                chart2_position=PlanetaryPosition(sign=sign2, degree=degree2)
            )

        return None

    def _compare_planets(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> List[ChartDifference]:
        """Compare planetary positions between two charts"""
        differences = []

        # Log chart structure for debugging
        logger.info(f"Chart1 structure: {chart1.keys()}")
        logger.info(f"Chart2 structure: {chart2.keys()}")

        # Check if planets exist in both charts
        if "planets" not in chart1 or "planets" not in chart2:
            logger.warning("One or both charts missing planets data")
            return differences

        # Handle different planet data structures
        planets1 = {}
        planets2 = {}

        # Check if planets is a list or dictionary
        if isinstance(chart1["planets"], list):
            # List format: [{"name": "Sun", ...}, {"name": "Moon", ...}]
            planets1 = {p["name"]: p for p in chart1.get("planets", [])}
        elif isinstance(chart1["planets"], dict):
            # Dict format: {"Sun": {...}, "Moon": {...}}
            planets1 = chart1["planets"]
        else:
            logger.warning(f"Unexpected planets format in chart1: {type(chart1['planets'])}")

        if isinstance(chart2["planets"], list):
            planets2 = {p["name"]: p for p in chart2.get("planets", [])}
        elif isinstance(chart2["planets"], dict):
            planets2 = chart2["planets"]
        else:
            logger.warning(f"Unexpected planets format in chart2: {type(chart2['planets'])}")

        # Get the set of all planet names
        all_planet_names = set(planets1.keys()) | set(planets2.keys())

        for planet_name in all_planet_names:
            # Skip if planet is missing from either chart
            if planet_name not in planets1 or planet_name not in planets2:
                continue

            planet1 = planets1[planet_name]
            planet2 = planets2[planet_name]

            # Check for sign change
            sign1 = planet1.get("sign")
            sign2 = planet2.get("sign")
            if sign1 and sign2 and sign1 != sign2:
                differences.append(ChartDifference(
                    type=DifferenceType.PLANET_SIGN_CHANGE,
                    description=f"{planet_name} has changed from {sign1} to {sign2}",
                    significance=self._get_planet_significance(planet_name),
                    planet=planet_name,
                    chart1_position=PlanetaryPosition(sign=sign1, degree=planet1.get("degree", 0)),
                    chart2_position=PlanetaryPosition(sign=sign2, degree=planet2.get("degree", 0))
                ))

            # Check for house change
            house1 = planet1.get("house")
            house2 = planet2.get("house")
            if house1 and house2 and house1 != house2:
                differences.append(ChartDifference(
                    type=DifferenceType.PLANET_HOUSE_CHANGE,
                    description=f"{planet_name} has moved from house {house1} to house {house2}",
                    significance=self._get_planet_significance(planet_name) * 0.8,
                    planet=planet_name,
                    chart1_position=PlanetaryPosition(sign=sign1, degree=planet1.get("degree", 0), house=house1),
                    chart2_position=PlanetaryPosition(sign=sign2, degree=planet2.get("degree", 0), house=house2)
                ))

            # Check for significant degree change within same sign
            if sign1 and sign2 and sign1 == sign2:
                degree1 = float(planet1.get("degree", 0))
                degree2 = float(planet2.get("degree", 0))
                degree_diff = abs(degree1 - degree2)

                if degree_diff > 3.0:  # More than 3 degrees is significant
                    significance = min(0.7, degree_diff / 10.0)  # Scale significance by degree difference
                    differences.append(ChartDifference(
                        type=DifferenceType.PLANET_DEGREE_CHANGE,
                        description=f"{planet_name} has shifted {degree_diff:.1f}° within {sign1}",
                        significance=significance * self._get_planet_significance(planet_name),
                        planet=planet_name,
                        chart1_position=PlanetaryPosition(sign=sign1, degree=degree1, house=house1),
                        chart2_position=PlanetaryPosition(sign=sign2, degree=degree2, house=house2)
                    ))

        return differences

    def _compare_aspects(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> List[ChartDifference]:
        """Compare aspects between two charts"""
        differences = []

        # Create dictionaries for easy lookup
        aspects1 = {
            f"{a.get('planet1')}_{a.get('planet2')}_{a.get('type')}": a
            for a in chart1.get("aspects", [])
        }
        aspects2 = {
            f"{a.get('planet1')}_{a.get('planet2')}_{a.get('type')}": a
            for a in chart2.get("aspects", [])
        }

        # Find aspects in chart1 that don't exist or changed in chart2
        for aspect_key, aspect1 in aspects1.items():
            if aspect_key not in aspects2:
                # Aspect dissolution
                planet1 = aspect1.get("planet1", "Unknown")
                planet2 = aspect1.get("planet2", "Unknown")
                aspect_type = aspect1.get("type", "Unknown")

                differences.append(ChartDifference(
                    type=DifferenceType.ASPECT_DISSOLUTION,
                    description=f"{aspect_type} aspect between {planet1} and {planet2} has dissolved",
                    significance=self._get_aspect_significance(aspect_type, planet1, planet2),
                    planet1=planet1,
                    planet2=planet2,
                    chart1_aspect=AspectData(
                        type=aspect_type,
                        orb=aspect1.get("orb", 0.0),
                        applying=aspect1.get("applying", False)
                    )
                ))
            else:
                # Aspect changed (orb or applying/separating status)
                aspect2 = aspects2[aspect_key]
                orb1 = aspect1.get("orb", 0.0)
                orb2 = aspect2.get("orb", 0.0)
                orb_diff = abs(orb1 - orb2)

                # Only note significant orb changes
                if orb_diff > 1.0:
                    planet1 = aspect1.get("planet1", "Unknown")
                    planet2 = aspect1.get("planet2", "Unknown")
                    aspect_type = aspect1.get("type", "Unknown")

                    # Determine if aspect is getting stronger or weaker
                    stronger = orb2 < orb1
                    direction = "stronger" if stronger else "weaker"

                    differences.append(ChartDifference(
                        type=DifferenceType.ASPECT_CHANGE,
                        description=f"{aspect_type} aspect between {planet1} and {planet2} has become {direction}",
                        significance=self._get_aspect_significance(aspect_type, planet1, planet2) * (orb_diff / 5.0),
                        planet1=planet1,
                        planet2=planet2,
                        chart1_aspect=AspectData(
                            type=aspect_type,
                            orb=orb1,
                            applying=aspect1.get("applying", False)
                        ),
                        chart2_aspect=AspectData(
                            type=aspect_type,
                            orb=orb2,
                            applying=aspect2.get("applying", False)
                        )
                    ))

        # Find aspects in chart2 that don't exist in chart1 (new aspects)
        for aspect_key, aspect2 in aspects2.items():
            if aspect_key not in aspects1:
                # New aspect formation
                planet1 = aspect2.get("planet1", "Unknown")
                planet2 = aspect2.get("planet2", "Unknown")
                aspect_type = aspect2.get("type", "Unknown")

                differences.append(ChartDifference(
                    type=DifferenceType.ASPECT_FORMATION,
                    description=f"New {aspect_type} aspect has formed between {planet1} and {planet2}",
                    significance=self._get_aspect_significance(aspect_type, planet1, planet2),
                    planet1=planet1,
                    planet2=planet2,
                    chart2_aspect=AspectData(
                        type=aspect_type,
                        orb=aspect2.get("orb", 0.0),
                        applying=aspect2.get("applying", False)
                    )
                ))

        return differences

    def _compare_houses(self, chart1: Dict[str, Any], chart2: Dict[str, Any]) -> List[ChartDifference]:
        """Compare house cusps between two charts"""
        differences = []

        houses1 = {h["number"]: h for h in chart1.get("houses", [])}
        houses2 = {h["number"]: h for h in chart2.get("houses", [])}

        # Check all houses from 1 to 12
        for house_num in range(1, 13):
            if house_num not in houses1 or house_num not in houses2:
                continue

            house1 = houses1[house_num]
            house2 = houses2[house_num]

            # Check for sign change
            if house1.get("sign") != house2.get("sign"):
                differences.append(ChartDifference(
                    type=DifferenceType.HOUSE_CUSP_SHIFT,
                    description=f"House {house_num} cusp has changed from {house1.get('sign')} to {house2.get('sign')}",
                    significance=self._get_house_significance(house_num),
                    house=house_num,
                    chart1_position=PlanetaryPosition(
                        sign=house1.get("sign", "Unknown"),
                        degree=house1.get("degree", 0)
                    ),
                    chart2_position=PlanetaryPosition(
                        sign=house2.get("sign", "Unknown"),
                        degree=house2.get("degree", 0)
                    )
                ))

            # Check for significant degree shift within same sign
            elif abs(house1.get("degree", 0) - house2.get("degree", 0)) > 3.0:
                degree_diff = abs(house1.get("degree", 0) - house2.get("degree", 0))

                differences.append(ChartDifference(
                    type=DifferenceType.HOUSE_CUSP_SHIFT,
                    description=f"House {house_num} cusp has shifted {degree_diff:.2f}° within {house1.get('sign')}",
                    significance=self._get_house_significance(house_num) * (degree_diff / 15.0),
                    house=house_num,
                    chart1_position=PlanetaryPosition(
                        sign=house1.get("sign", "Unknown"),
                        degree=house1.get("degree", 0)
                    ),
                    chart2_position=PlanetaryPosition(
                        sign=house2.get("sign", "Unknown"),
                        degree=house2.get("degree", 0)
                    )
                ))

        return differences

    def _generate_summary(
        self,
        chart1: Dict[str, Any],
        chart2: Dict[str, Any],
        differences: List[ChartDifference],
        overall_impact: Optional[float]
    ) -> str:
        """Generate a textual summary of the differences between charts"""
        if not differences:
            return "No significant differences found between the charts."

        # Sort differences by significance
        sorted_diffs = sorted(differences, key=lambda d: d.significance, reverse=True)

        # Get the top most significant differences
        top_diffs = sorted_diffs[:3]

        # Create summary text
        summary = "Key differences between the original and rectified charts:\n\n"

        for i, diff in enumerate(top_diffs):
            summary += f"{i+1}. {diff.description}"
            if hasattr(diff, "significance") and diff.significance is not None:
                summary += f" (Significance: {diff.significance:.2f})"
            summary += "\n"

        # Add overall impact if available
        if overall_impact is not None:
            impact_desc = "minimal"
            if overall_impact > 0.3 and overall_impact <= 0.6:
                impact_desc = "moderate"
            elif overall_impact > 0.6 and overall_impact <= 0.8:
                impact_desc = "significant"
            elif overall_impact > 0.8:
                impact_desc = "major"

            summary += f"\nThe rectification has a {impact_desc} overall impact on the chart "
            summary += f"(Impact score: {overall_impact:.2f})."

        return summary

    def _get_planet_significance(self, planet_name: str) -> float:
        """
        Get the significance weight for a planet

        Higher values (closer to 1.0) indicate more significant planets
        """
        significance_map = {
            "Sun": 0.9,
            "Moon": 0.9,
            "Ascendant": 1.0,
            "Mercury": 0.7,
            "Venus": 0.7,
            "Mars": 0.7,
            "Jupiter": 0.6,
            "Saturn": 0.8,
            "Uranus": 0.5,
            "Neptune": 0.5,
            "Pluto": 0.5,
            "North Node": 0.6,
            "South Node": 0.6,
            "Chiron": 0.4,
            "Ketu": 0.6
        }

        return significance_map.get(planet_name, 0.5)

    def _get_aspect_significance(self, aspect_type: str, planet1: str, planet2: str) -> float:
        """
        Get the significance weight for an aspect between two planets

        Higher values (closer to 1.0) indicate more significant aspects
        """
        # Base significance by aspect type
        aspect_significance = {
            "conjunction": 0.8,
            "opposition": 0.8,
            "trine": 0.6,
            "square": 0.7,
            "sextile": 0.5,
            "quincunx": 0.4,
            "semisextile": 0.3,
            "semisquare": 0.4,
            "sesquiquadrate": 0.4
        }

        base_significance = aspect_significance.get(aspect_type.lower(), 0.5)

        # Adjust by planet significance
        planet1_sig = self._get_planet_significance(planet1)
        planet2_sig = self._get_planet_significance(planet2)

        # Average the planet significances, but weight toward the more significant planet
        planet_avg = (planet1_sig * 0.6) + (planet2_sig * 0.4)

        # Combine aspect type and planet significances
        return min(1.0, base_significance * 0.7 + planet_avg * 0.3)

    def _get_house_significance(self, house_number: int) -> float:
        """
        Get the significance weight for a house

        Higher values (closer to 1.0) indicate more significant houses
        """
        significance_map = {
            1: 0.9,  # Ascendant/1st house (identity, self)
            4: 0.8,  # IC/4th house (home, family, roots)
            7: 0.8,  # Descendant/7th house (partnerships, marriage)
            10: 0.9, # MC/10th house (career, public standing)
            2: 0.6,  # 2nd house (resources, values)
            3: 0.5,  # 3rd house (communication, siblings)
            5: 0.7,  # 5th house (creativity, children)
            6: 0.5,  # 6th house (work, health)
            8: 0.7,  # 8th house (transformation, shared resources)
            9: 0.6,  # 9th house (higher learning, philosophy)
            11: 0.6, # 11th house (groups, friends, hopes)
            12: 0.7  # 12th house (unconscious, spirituality)
        }

        return significance_map.get(house_number, 0.5)
