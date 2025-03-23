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
from matplotlib import path as mpath

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
    "sun": "☉",
    "moon": "☽",
    "mercury": "☿",
    "venus": "♀",
    "mars": "♂",
    "jupiter": "♃",
    "saturn": "♄",
    "uranus": "♅",
    "neptune": "♆",
    "pluto": "♇",
    "rahu": "☊",
    "ketu": "☋"
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
    """Renderer for Vedic astrological charts in North Indian format (Kundli)."""

    def __init__(
        self,
        planets: Dict[str, Any],
        houses: List[Dict[str, Any]],
        ascendant: Dict[str, Any],
        width: int = 1000,
        height: int = 1000,
        background_color: str = "white",
        line_color: str = "black",
        text_color: str = "black",
        planet_color: str = "red"
    ):
        """
        Initialize the Vedic chart renderer.

        Args:
            planets: Dictionary of planets with their positions
            houses: List of houses with their positions
            ascendant: Ascendant (Lagna) information
            width: Chart width in pixels
            height: Chart height in pixels
            background_color: Background color
            line_color: Line color for chart grid
            text_color: Text color
            planet_color: Color for planet symbols
        """
        self.planets = planets
        self.houses = houses
        self.ascendant = ascendant
        self.width = width
        self.height = height
        self.background_color = background_color
        self.line_color = line_color
        self.text_color = text_color
        self.planet_color = planet_color

        # Computed properties
        self.ascendant_sign = self.ascendant.get("sign", "Aries")
        self.ascendant_house = 1  # In Vedic astrology, ascendant is always in the 1st house

        # Find the zodiac sign that corresponds to the 1st house (ascendant/lagna)
        for house in self.houses:
            if house.get("house") == 1:
                self.first_house_sign = house.get("sign", self.ascendant_sign)
                break
        else:
            self.first_house_sign = self.ascendant_sign

    def render(self, output_path: str) -> str:
        """
        Render the Vedic chart and save it to the specified path.

        Args:
            output_path: Path where to save the output image

        Returns:
            The path to the saved image
        """
        try:
            # Create figure with the specified size
            fig, ax = plt.subplots(figsize=(10, 10))

            # Set up the plot
            ax.set_xlim(0, self.width)
            ax.set_ylim(0, self.height)
            ax.set_aspect('equal')
            ax.axis('off')  # Hide axes

            # Draw the North Indian chart structure (Kundli)
            self._draw_kundli_structure(ax)

            # Draw zodiac signs in each house based on ascendant position
            self._draw_zodiac_signs(ax)

            # Draw planets in their respective houses
            self._draw_planets(ax)

            # Save the chart
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close(fig)

            logger.info(f"Vedic chart saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error rendering Vedic chart: {e}")
            raise

    def _draw_kundli_structure(self, ax):
        """
        Draw the North Indian chart structure (Kundli square).

        Args:
            ax: Matplotlib axis
        """
        # Main square
        main_square = patches.Rectangle(
            (100, 100), self.width-200, self.height-200,
            linewidth=2, edgecolor=self.line_color, facecolor='none'
        )
        ax.add_patch(main_square)

        # Center square
        center_x = self.width/2
        center_y = self.height/2
        center_width = (self.width-200)/3
        center_height = (self.height-200)/3

        center_square = patches.Rectangle(
            (center_x - center_width/2, center_y - center_height/2),
            center_width, center_height,
            linewidth=2, edgecolor=self.line_color, facecolor='none'
        )
        ax.add_patch(center_square)

        # Draw diagonals
        ax.plot([100, self.width-100], [100, self.height-100],
                color=self.line_color, linestyle='-', linewidth=1)
        ax.plot([100, self.width-100], [self.height-100, 100],
                color=self.line_color, linestyle='-', linewidth=1)

        # Draw horizontal and vertical dividers
        h_third = (self.height-200)/3
        w_third = (self.width-200)/3

        # Horizontal lines
        ax.plot([100, self.width-100], [100 + h_third, 100 + h_third],
                color=self.line_color, linestyle='-', linewidth=1)
        ax.plot([100, self.width-100], [100 + 2*h_third, 100 + 2*h_third],
                color=self.line_color, linestyle='-', linewidth=1)

        # Vertical lines
        ax.plot([100 + w_third, 100 + w_third], [100, self.height-100],
                color=self.line_color, linestyle='-', linewidth=1)
        ax.plot([100 + 2*w_third, 100 + 2*w_third], [100, self.height-100],
                color=self.line_color, linestyle='-', linewidth=1)

        # Label the houses
        self._label_houses(ax)

    def _label_houses(self, ax):
        """
        Label the houses with their numbers.

        Args:
            ax: Matplotlib axis
        """
        # Define house positions in the North Indian chart
        # Houses are numbered 1-12, with 1 being the Ascendant/Lagna house

        # In North Indian chart, houses are fixed positions:
        # 1  12  11
        # 2   9  10
        # 3   4   5
        house_positions = {
            1: (self.width/6, self.height/6),     # Top-left
            2: (self.width/6, self.height/2),     # Middle-left
            3: (self.width/6, 5*self.height/6),   # Bottom-left
            4: (self.width/2, 5*self.height/6),   # Bottom-center
            5: (5*self.width/6, 5*self.height/6), # Bottom-right
            6: (5*self.width/6, self.height/2),   # Middle-right
            7: (5*self.width/6, self.height/6),   # Top-right
            8: (self.width/2, self.height/6),     # Top-center
            9: (self.width/2, self.height/2),     # Center
            10: (5*self.width/6, self.height/3),  # Upper-right
            11: (2*self.width/3, self.height/6),  # Upper-center-right
            12: (self.width/3, self.height/6),    # Upper-center-left
        }

        # Adjust house numbers based on the Ascendant house
        # In Vedic astrology with North Indian style, the 1st house is always the Ascendant house
        # and is always placed at the top-left position

        # Draw house numbers
        for house_num, (x, y) in house_positions.items():
            ax.text(x, y, str(house_num), fontsize=14,
                   ha='center', va='center', color=self.text_color,
                   bbox=dict(facecolor=self.background_color, alpha=0.7, boxstyle='round'))

    def _draw_zodiac_signs(self, ax):
        """
        Draw zodiac signs in the chart.

        Args:
            ax: Matplotlib axis
        """
        # Map of house positions for the signs
        # In North Indian chart, signs are placed according to the Ascendant position

        # House positions (same as in _label_houses)
        house_positions = {
            1: (self.width/6, self.height/6 + 30),     # Top-left
            2: (self.width/6, self.height/2 + 30),     # Middle-left
            3: (self.width/6, 5*self.height/6 + 30),   # Bottom-left
            4: (self.width/2, 5*self.height/6 + 30),   # Bottom-center
            5: (5*self.width/6, 5*self.height/6 + 30), # Bottom-right
            6: (5*self.width/6, self.height/2 + 30),   # Middle-right
            7: (5*self.width/6, self.height/6 + 30),   # Top-right
            8: (self.width/2, self.height/6 + 30),     # Top-center
            9: (self.width/2, self.height/2 + 30),     # Center
            10: (5*self.width/6, self.height/3 + 30),  # Upper-right
            11: (2*self.width/6, self.height/6 + 30),  # Upper-center-right
            12: (self.width/3, self.height/6 + 30),    # Upper-center-left
        }

        # Zodiac sign order
        zodiac_order = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]

        # Find the index of the ascendant sign
        try:
            asc_index = zodiac_order.index(self.ascendant_sign)
        except ValueError:
            logger.warning(f"Ascendant sign {self.ascendant_sign} not found in zodiac signs")
            asc_index = 0

        # Draw zodiac signs for each house
        for house_num in range(1, 13):
            # Calculate which sign goes in this house
            sign_index = (asc_index + house_num - 1) % 12
            sign = zodiac_order[sign_index]
            symbol = ZODIAC_SIGNS.get(sign, sign)

            # Get position for this house
            x, y = house_positions.get(house_num, (0, 0))

            # Draw the sign
            ax.text(x, y, symbol, fontsize=16,
                   ha='center', va='center', color=self.text_color,
                   bbox=dict(facecolor=self.background_color, alpha=0.8))

    def _draw_planets(self, ax):
        """
        Draw planets in their respective houses.

        Args:
            ax: Matplotlib axis
        """
        # Determine where each planet should be placed
        planet_house_map = {}

        zodiac_order = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]

        # Find the index of the ascendant sign
        try:
            asc_index = zodiac_order.index(self.ascendant_sign)
        except ValueError:
            logger.warning(f"Ascendant sign {self.ascendant_sign} not found in zodiac signs")
            asc_index = 0

        # Determine which house each planet is in
        for planet_name, planet_data in self.planets.items():
            if isinstance(planet_data, dict):
                # Get the sign the planet is in
                planet_sign = planet_data.get("sign", "")

                if not planet_sign or planet_sign not in zodiac_order:
                    logger.warning(f"Invalid sign for planet {planet_name}: {planet_sign}")
                    continue

                # Calculate which house this sign corresponds to
                sign_index = zodiac_order.index(planet_sign)
                house_offset = (sign_index - asc_index) % 12 + 1

                # Add to map
                if house_offset not in planet_house_map:
                    planet_house_map[house_offset] = []
                planet_house_map[house_offset].append(planet_name)

        # House positions for planets (adjusted from center of each house)
        house_positions = {
            1: (self.width/6, self.height/6 - 30),     # Top-left
            2: (self.width/6, self.height/2 - 30),     # Middle-left
            3: (self.width/6, 5*self.height/6 - 30),   # Bottom-left
            4: (self.width/2, 5*self.height/6 - 30),   # Bottom-center
            5: (5*self.width/6, 5*self.height/6 - 30), # Bottom-right
            6: (5*self.width/6, self.height/2 - 30),   # Middle-right
            7: (5*self.width/6, self.height/6 - 30),   # Top-right
            8: (self.width/2, self.height/6 - 30),     # Top-center
            9: (self.width/2, self.height/2 - 30),     # Center
            10: (5*self.width/6, self.height/3 - 30),  # Upper-right
            11: (2*self.width/6, self.height/6 - 30),  # Upper-center-right
            12: (self.width/3, self.height/6 - 30),    # Upper-center-left
        }

        # Draw planets in their houses
        for house_num, planet_list in planet_house_map.items():
            if house_num < 1 or house_num > 12:
                continue

            x, y = house_positions.get(house_num, (0, 0))

            # If multiple planets in a house, arrange them
            planet_text = ""
            for i, planet_name in enumerate(planet_list):
                symbol = PLANET_SYMBOLS.get(planet_name.lower(), planet_name[0])
                planet_text += symbol + " "

            # Draw all planets for this house
            if planet_text:
                ax.text(x, y, planet_text, fontsize=14,
                       ha='center', va='center', color=self.planet_color,
                       bbox=dict(facecolor=self.background_color, alpha=0.8, boxstyle='round'))
