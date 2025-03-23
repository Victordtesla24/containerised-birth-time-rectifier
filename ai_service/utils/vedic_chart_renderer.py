"""
Vedic Chart Renderer for North Indian Kundli Chart Format.

This module provides functionality to render astrological charts in the traditional
North Indian (Kundli) style according to Vedic astrological standards.
"""

import json
import logging
import os
import tempfile
from typing import Dict, Any, List, Optional, Tuple
import math
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logger = logging.getLogger(__name__)

# Zodiac sign symbols and names
ZODIAC_SIGNS = {
    "Aries": "♈",
    "Taurus": "♉",
    "Gemini": "♊",
    "Cancer": "♋",
    "Leo": "♌",
    "Virgo": "♍",
    "Libra": "♎",
    "Scorpio": "♏",
    "Sagittarius": "♐",
    "Capricorn": "♑",
    "Aquarius": "♒",
    "Pisces": "♓"
}

# Planet symbols
PLANET_SYMBOLS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
    "Rahu": "☊",
    "Ketu": "☋",
    "Uranus": "⛢",
    "Neptune": "♆",
    "Pluto": "♇",
    "Ascendant": "Asc"
}

# Planet colors - used for standard and relationship highlighting
PLANET_COLORS = {
    "Sun": "#e74c3c",     # Red
    "Moon": "#3498db",    # Light Blue
    "Mercury": "#2ecc71", # Green
    "Venus": "#9b59b6",   # Purple
    "Mars": "#e74c3c",    # Red
    "Jupiter": "#f1c40f", # Yellow
    "Saturn": "#34495e",  # Dark Blue
    "Rahu": "#7f8c8d",    # Gray
    "Ketu": "#7f8c8d",    # Gray
    "Uranus": "#1abc9c",  # Turquoise
    "Neptune": "#3498db", # Blue
    "Pluto": "#8e44ad",   # Dark Purple
    "Ascendant": "#e67e22" # Orange
}

# Planet relationship highlights
RELATIONSHIP_COLORS = {
    "friendly": "#2ecc71",  # Green
    "enemy": "#e74c3c",     # Red
    "neutral": "#f1c40f"    # Yellow
}

class VedicChartRenderer:
    """
    Renderer for North Indian (Kundli) style Vedic astrological charts.
    """

    def __init__(self, chart_data: Dict[str, Any], output_dir: Optional[str] = None):
        """
        Initialize the Vedic chart renderer.

        Args:
            chart_data: The chart data containing planetary positions and house information.
            output_dir: Optional directory for saving chart images.
        """
        self.chart_data = chart_data
        self.output_dir = output_dir or tempfile.mkdtemp()
        self._validate_chart_data()

    def _validate_chart_data(self):
        """Validate the chart data contains required fields."""
        required_fields = ["planets", "houses", "ascendant"]
        for field in required_fields:
            if field not in self.chart_data:
                logger.warning(f"Chart data missing required field: {field}")

    def render_north_indian_chart(self, output_path: Optional[str] = None) -> str:
        """
        Render a traditional North Indian style chart (Kundli format).

        Args:
            output_path: Optional path to save the rendered chart image.

        Returns:
            str: Path to the rendered chart image.
        """
        # Set up figure and axis
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_aspect('equal')

        # Turn off axis
        ax.axis('off')

        # Draw the main square
        main_square = patches.Rectangle((0, 0), 10, 10, linewidth=2, edgecolor='black', facecolor='none')
        ax.add_patch(main_square)

        # Draw diagonal lines to create the central house
        diag1 = patches.PathPatch(
            matplotlib.path.Path([(0, 0), (10, 10)]),
            linewidth=1.5, edgecolor='black', facecolor='none'
        )
        diag2 = patches.PathPatch(
            matplotlib.path.Path([(0, 10), (10, 0)]),
            linewidth=1.5, edgecolor='black', facecolor='none'
        )
        ax.add_patch(diag1)
        ax.add_patch(diag2)

        # Add house separators
        # Left compartment
        ax.add_patch(patches.Rectangle((0, 3.33), 3.33, 3.33, linewidth=1.5, edgecolor='black', facecolor='none'))

        # Right compartment
        ax.add_patch(patches.Rectangle((6.67, 3.33), 3.33, 3.33, linewidth=1.5, edgecolor='black', facecolor='none'))

        # Bottom compartment
        ax.add_patch(patches.Rectangle((3.33, 0), 3.33, 3.33, linewidth=1.5, edgecolor='black', facecolor='none'))

        # Top compartment
        ax.add_patch(patches.Rectangle((3.33, 6.67), 3.33, 3.33, linewidth=1.5, edgecolor='black', facecolor='none'))

        # Define house positions (house_number: (x, y))
        house_positions = {
            1: (5, 5),       # Center house
            2: (8.33, 8.33),  # Top right
            3: (8.33, 5),     # Right
            4: (8.33, 1.67),  # Bottom right
            5: (5, 1.67),     # Bottom
            6: (1.67, 1.67),  # Bottom left
            7: (1.67, 5),     # Left
            8: (1.67, 8.33),  # Top left
            9: (5, 8.33),     # Top
            10: (3.33, 6.67), # Top middle
            11: (6.67, 6.67), # Top right middle
            12: (3.33, 3.33)  # Left middle
        }

        # Add house numbers
        for house_num, pos in house_positions.items():
            ax.text(pos[0], pos[1], str(house_num),
                    horizontalalignment='center', verticalalignment='center',
                    fontsize=14, fontweight='bold')

        # Map the planets to houses
        planets_by_house = {}
        for planet in self.chart_data.get("planets", []):
            house = planet.get("house")
            if house not in planets_by_house:
                planets_by_house[house] = []
            planets_by_house[house].append(planet)

        # Get the ascendant sign for determining relationships
        ascendant = self.chart_data.get("ascendant", {}).get("sign", "Unknown")

        # Add planets to houses with relationship highlighting
        for house_num, planets in planets_by_house.items():
            if house_num not in house_positions:
                continue

            # Position for the house
            x, y = house_positions[house_num]

            # Arrange planets vertically within the house
            spacing = 0.4
            start_y = y + (len(planets) - 1) * spacing / 2

            for i, planet in enumerate(planets):
                planet_name = planet.get("name")
                planet_symbol = PLANET_SYMBOLS.get(planet_name, "?")
                planet_sign = planet.get("sign")
                planet_degree = planet.get("longitude", 0) % 30  # Degree within sign

                # Determine relationship to ascendant
                # This is a simplified version - in practice, you'd use more complex rules
                relationship = self._determine_relationship(planet_name, ascendant)

                # Choose color based on relationship
                if relationship == "friendly":
                    color = RELATIONSHIP_COLORS["friendly"]
                elif relationship == "enemy":
                    color = RELATIONSHIP_COLORS["enemy"]
                else:
                    color = PLANET_COLORS.get(planet_name, "black")

                # Place the planet in the house
                planet_y = start_y - i * spacing

                # Create text with symbol and degrees
                text = f"{planet_symbol} {planet_degree:.1f}°"

                # Draw with appropriate color based on relationship
                ax.text(x, planet_y, text,
                        color=color,
                        horizontalalignment='center',
                        verticalalignment='center',
                        fontsize=11, fontweight='bold')

        # Title
        chart_type = "Rectified " if self.chart_data.get("rectified", False) else ""
        ax.set_title(f"{chart_type}North Indian Vedic Chart (Kundli)", fontsize=16)

        # Add timestamp to bottom
        timestamp = self.chart_data.get("timestamp", "")
        if timestamp:
            plt.figtext(0.5, 0.01, f"Generated: {timestamp}",
                        ha="center", fontsize=8, color="gray")

        # Save the figure if output path is provided
        if not output_path:
            # Create a default path if not provided
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, "vedic_kundli_chart.png")

        plt.savefig(output_path, bbox_inches='tight', dpi=150)
        plt.close()

        logger.info(f"North Indian Vedic chart rendered to {output_path}")
        return output_path

    def _determine_relationship(self, planet_name: str, ascendant_sign: str) -> str:
        """
        Determine the relationship of a planet to the ascendant sign.

        Args:
            planet_name: The name of the planet.
            ascendant_sign: The zodiac sign of the ascendant.

        Returns:
            str: Relationship type ("friendly", "enemy", or "neutral").
        """
        # This is a simplified version of relationship determination
        # Real implementation would have full planetary relationship matrix

        # Simple rulership pairs (planet is strong in these signs)
        rulerships = {
            "Sun": ["Leo"],
            "Moon": ["Cancer"],
            "Mercury": ["Gemini", "Virgo"],
            "Venus": ["Taurus", "Libra"],
            "Mars": ["Aries", "Scorpio"],
            "Jupiter": ["Sagittarius", "Pisces"],
            "Saturn": ["Capricorn", "Aquarius"]
        }

        # Simple debilitation (planet is weak in these signs)
        debilitations = {
            "Sun": ["Libra"],
            "Moon": ["Scorpio"],
            "Mercury": ["Pisces"],
            "Venus": ["Virgo"],
            "Mars": ["Cancer"],
            "Jupiter": ["Capricorn"],
            "Saturn": ["Aries"]
        }

        # Check if planet is in a friendly sign for the ascendant ruler
        ascendant_ruler = self._get_ruler_of_sign(ascendant_sign)

        # If the planet rules the ascendant, it's friendly
        if planet_name == ascendant_ruler:
            return "friendly"

        # If the planet is in a sign it rules, it's friendly
        if ascendant_sign in rulerships.get(planet_name, []):
            return "friendly"

        # If the planet is in a sign where it's debilitated, it's an enemy
        if ascendant_sign in debilitations.get(planet_name, []):
            return "enemy"

        # Default - neutral relationship
        return "neutral"

    def _get_ruler_of_sign(self, sign: str) -> str:
        """Get the planetary ruler of a zodiac sign."""
        rulers = {
            "Aries": "Mars",
            "Taurus": "Venus",
            "Gemini": "Mercury",
            "Cancer": "Moon",
            "Leo": "Sun",
            "Virgo": "Mercury",
            "Libra": "Venus",
            "Scorpio": "Mars",
            "Sagittarius": "Jupiter",
            "Capricorn": "Saturn",
            "Aquarius": "Saturn",
            "Pisces": "Jupiter"
        }
        return rulers.get(sign, "Unknown")

    def render_chart_comparison(self, comparison_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Render a comparison between two Vedic charts side by side.

        Args:
            comparison_data: Dictionary containing original and rectified chart data.
            output_path: Optional path to save the rendered comparison image.

        Returns:
            str: Path to the rendered comparison image.
        """
        original_chart = comparison_data.get("original", {})
        rectified_chart = comparison_data.get("rectified", {})

        if not original_chart or not rectified_chart:
            logger.error("Comparison data must include both original and rectified charts")
            return ""

        # Create figure with two subplots side by side
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

        # Temporarily store chart_data and set to original chart
        temp_chart_data = self.chart_data
        self.chart_data = original_chart

        # Render original chart on left subplot
        self._render_chart_on_axis(ax1, "Original Birth Chart")

        # Set to rectified chart
        self.chart_data = rectified_chart

        # Render rectified chart on right subplot
        self._render_chart_on_axis(ax2, "Rectified Birth Chart")

        # Restore original chart_data
        self.chart_data = temp_chart_data

        # Add a title for the comparison
        plt.suptitle("Vedic Chart Comparison", fontsize=20)

        # Add explanation of differences
        diff_text = self._generate_differences_text(original_chart, rectified_chart)
        plt.figtext(0.5, 0.01, diff_text, ha="center", fontsize=10,
                   bbox={"facecolor":"lightgray", "alpha":0.5, "pad":5})

        # Save the figure if output path is provided
        if not output_path:
            # Create a default path if not provided
            os.makedirs(self.output_dir, exist_ok=True)
            output_path = os.path.join(self.output_dir, "vedic_chart_comparison.png")

        plt.savefig(output_path, bbox_inches='tight', dpi=150)
        plt.close()

        logger.info(f"Vedic chart comparison rendered to {output_path}")
        return output_path

    def _render_chart_on_axis(self, ax, title):
        """Helper method to render a chart on a given matplotlib axis."""
        # Turn off axis
        ax.axis('off')
        ax.set_aspect('equal')

        # Draw the main square
        main_square = patches.Rectangle((0, 0), 10, 10, linewidth=2, edgecolor='black', facecolor='none')
        ax.add_patch(main_square)

        # Draw diagonal lines to create the central house
        diag1 = patches.PathPatch(
            matplotlib.path.Path([(0, 0), (10, 10)]),
            linewidth=1.5, edgecolor='black', facecolor='none'
        )
        diag2 = patches.PathPatch(
            matplotlib.path.Path([(0, 10), (10, 0)]),
            linewidth=1.5, edgecolor='black', facecolor='none'
        )
        ax.add_patch(diag1)
        ax.add_patch(diag2)

        # Add house separators
        # Left compartment
        ax.add_patch(patches.Rectangle((0, 3.33), 3.33, 3.33, linewidth=1.5, edgecolor='black', facecolor='none'))

        # Right compartment
        ax.add_patch(patches.Rectangle((6.67, 3.33), 3.33, 3.33, linewidth=1.5, edgecolor='black', facecolor='none'))

        # Bottom compartment
        ax.add_patch(patches.Rectangle((3.33, 0), 3.33, 3.33, linewidth=1.5, edgecolor='black', facecolor='none'))

        # Top compartment
        ax.add_patch(patches.Rectangle((3.33, 6.67), 3.33, 3.33, linewidth=1.5, edgecolor='black', facecolor='none'))

        # Define house positions (house_number: (x, y))
        house_positions = {
            1: (5, 5),       # Center house
            2: (8.33, 8.33),  # Top right
            3: (8.33, 5),     # Right
            4: (8.33, 1.67),  # Bottom right
            5: (5, 1.67),     # Bottom
            6: (1.67, 1.67),  # Bottom left
            7: (1.67, 5),     # Left
            8: (1.67, 8.33),  # Top left
            9: (5, 8.33),     # Top
            10: (3.33, 6.67), # Top middle
            11: (6.67, 6.67), # Top right middle
            12: (3.33, 3.33)  # Left middle
        }

        # Add house numbers
        for house_num, pos in house_positions.items():
            ax.text(pos[0], pos[1], str(house_num),
                    horizontalalignment='center', verticalalignment='center',
                    fontsize=14, fontweight='bold')

        # Map the planets to houses
        planets_by_house = {}
        for planet in self.chart_data.get("planets", []):
            house = planet.get("house")
            if house not in planets_by_house:
                planets_by_house[house] = []
            planets_by_house[house].append(planet)

        # Get the ascendant sign for determining relationships
        ascendant = self.chart_data.get("ascendant", {}).get("sign", "Unknown")

        # Add planets to houses with relationship highlighting
        for house_num, planets in planets_by_house.items():
            if house_num not in house_positions:
                continue

            # Position for the house
            x, y = house_positions[house_num]

            # Arrange planets vertically within the house
            spacing = 0.4
            start_y = y + (len(planets) - 1) * spacing / 2

            for i, planet in enumerate(planets):
                planet_name = planet.get("name")
                planet_symbol = PLANET_SYMBOLS.get(planet_name, "?")
                planet_sign = planet.get("sign")
                planet_degree = planet.get("longitude", 0) % 30  # Degree within sign

                # Determine relationship to ascendant
                relationship = self._determine_relationship(planet_name, ascendant)

                # Choose color based on relationship
                if relationship == "friendly":
                    color = RELATIONSHIP_COLORS["friendly"]
                elif relationship == "enemy":
                    color = RELATIONSHIP_COLORS["enemy"]
                else:
                    color = PLANET_COLORS.get(planet_name, "black")

                # Place the planet in the house
                planet_y = start_y - i * spacing

                # Create text with symbol and degrees
                text = f"{planet_symbol} {planet_degree:.1f}°"

                # Draw with appropriate color based on relationship
                ax.text(x, planet_y, text,
                        color=color,
                        horizontalalignment='center',
                        verticalalignment='center',
                        fontsize=11, fontweight='bold')

        # Title
        ax.set_title(title, fontsize=16)

    def _generate_differences_text(self, original_chart, rectified_chart):
        """Generate text describing the key differences between original and rectified charts."""
        differences = []

        # Compare ascendants
        orig_asc = original_chart.get("ascendant", {})
        rect_asc = rectified_chart.get("ascendant", {})

        if orig_asc.get("sign") != rect_asc.get("sign"):
            differences.append(f"• Ascendant changed from {orig_asc.get('sign')} to {rect_asc.get('sign')}")
        elif abs(orig_asc.get("longitude", 0) - rect_asc.get("longitude", 0)) > 1:
            orig_deg = orig_asc.get("longitude", 0) % 30
            rect_deg = rect_asc.get("longitude", 0) % 30
            differences.append(f"• Ascendant degree changed from {orig_deg:.1f}° to {rect_deg:.1f}° {rect_asc.get('sign')}")

        # Compare planets' house placements
        orig_planets = {p.get("name"): p for p in original_chart.get("planets", [])}
        rect_planets = {p.get("name"): p for p in rectified_chart.get("planets", [])}

        for planet_name, rect_planet in rect_planets.items():
            if planet_name in orig_planets:
                orig_planet = orig_planets[planet_name]

                # Check if house changed
                if orig_planet.get("house") != rect_planet.get("house"):
                    differences.append(
                        f"• {planet_name} moved from house {orig_planet.get('house')} to {rect_planet.get('house')}"
                    )

                # Check if sign changed
                if orig_planet.get("sign") != rect_planet.get("sign"):
                    differences.append(
                        f"• {planet_name} moved from {orig_planet.get('sign')} to {rect_planet.get('sign')}"
                    )

        # If any house cusps changed significantly
        orig_houses = original_chart.get("houses", [])
        rect_houses = rectified_chart.get("houses", [])

        if len(orig_houses) == len(rect_houses) and len(orig_houses) > 0:
            for i in range(len(orig_houses)):
                if orig_houses[i].get("sign") != rect_houses[i].get("sign"):
                    differences.append(
                        f"• House {i+1} cusp moved from {orig_houses[i].get('sign')} to {rect_houses[i].get('sign')}"
                    )

        # Get birth time difference if available
        orig_time = original_chart.get("birth_time", "")
        rect_time = rectified_chart.get("birth_time", "")

        if orig_time and rect_time and orig_time != rect_time:
            differences.append(f"• Birth time adjusted from {orig_time} to {rect_time}")

        # Combine the differences
        if differences:
            text = "Key differences:\n" + "\n".join(differences)
        else:
            text = "No significant differences detected between charts."

        return text
