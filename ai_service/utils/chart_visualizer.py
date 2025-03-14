"""
Chart Visualization Module

This module provides functions for visualizing astrological charts
in various formats including North Indian Vedic style.
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple, cast, Union
import os
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
# Import 3D plotting tools
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.axes3d import Axes3D as Axes3DType
import numpy as np
from datetime import datetime
import io
import base64

from ai_service.core.chart_calculator import normalize_longitude

# Configure logging
logger = logging.getLogger(__name__)

# Constants for chart visualization
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

ZODIAC_SYMBOLS = {
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

PLANET_SYMBOLS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mercury": "☿",
    "Venus": "♀",
    "Mars": "♂",
    "Jupiter": "♃",
    "Saturn": "♄",
    "Uranus": "♅",
    "Neptune": "♆",
    "Pluto": "♇",
    "Rahu": "☊",
    "Ketu": "☋",
    "Ascendant": "Asc"
}

PLANET_COLORS = {
    "Sun": "#FFD700",      # Gold
    "Moon": "#C0C0C0",     # Silver
    "Mercury": "#32CD32",  # Lime Green
    "Venus": "#FF69B4",    # Hot Pink
    "Mars": "#FF0000",     # Red
    "Jupiter": "#FFA500",  # Orange
    "Saturn": "#4682B4",   # Steel Blue
    "Uranus": "#9370DB",   # Medium Purple
    "Neptune": "#00BFFF",  # Deep Sky Blue
    "Pluto": "#8B4513",    # Saddle Brown
    "Rahu": "#800080",     # Purple
    "Ketu": "#8B0000",     # Dark Red
    "Ascendant": "#000000" # Black
}

def render_vedic_square_chart(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Render a North Indian (square) Vedic chart.

    Args:
        chart_data: Dictionary containing chart data
        output_path: Optional path to save the chart image

    Returns:
        Base64 encoded image data or path to saved image
    """
    try:
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 10))

        # Draw the main square
        ax.add_patch(patches.Rectangle((0, 0), 10, 10, fill=False, linewidth=2))

        # Draw the inner square (for the center)
        ax.add_patch(patches.Rectangle((3, 3), 4, 4, fill=False, linewidth=2))

        # Draw the diagonal lines
        ax.plot([0, 10], [0, 10], 'k-', linewidth=2)
        ax.plot([0, 10], [10, 0], 'k-', linewidth=2)

        # Get house data
        houses = chart_data.get("houses", [])
        planets = chart_data.get("planets", {})
        ascendant = chart_data.get("ascendant", {})

        # House positions in the chart (North Indian style)
        house_positions = [
            (3, 7),    # House 1 (top center)
            (1, 7),    # House 2 (top left)
            (1, 5),    # House 3 (middle left)
            (1, 3),    # House 4 (bottom left)
            (3, 1),    # House 5 (bottom center)
            (5, 1),    # House 6 (bottom right)
            (7, 3),    # House 7 (middle right)
            (7, 5),    # House 8 (middle right)
            (7, 7),    # House 9 (top right)
            (5, 7),    # House 10 (top center)
            (5, 5),    # House 11 (center right)
            (3, 5)     # House 12 (center left)
        ]

        # Add house signs
        for i, pos in enumerate(house_positions):
            house_num = i + 1

            # Get the sign for this house
            sign = "Unknown"
            if i < len(houses):
                sign = houses[i].get("sign", "Unknown")

            # Add house number and sign
            ax.text(pos[0], pos[1] + 0.5, f"{house_num}", fontsize=12, ha='center')
            ax.text(pos[0], pos[1], f"{sign}", fontsize=10, ha='center')

            # Add planets in this house
            planets_in_house = []
            for planet_name, planet_data in planets.items():
                if planet_data.get("house") == house_num:
                    planets_in_house.append(planet_name)

            # Display planets
            for j, planet in enumerate(planets_in_house):
                symbol = PLANET_SYMBOLS.get(planet, planet[:2])
                color = PLANET_COLORS.get(planet, "#000000")
                ax.text(pos[0], pos[1] - 0.3 - (j * 0.3), symbol, fontsize=10, ha='center', color=color)

        # Add ascendant marker
        asc_sign = ascendant.get("sign", "Unknown")
        asc_degree = ascendant.get("degree", 0)
        ax.text(5, 5, f"Asc: {asc_sign} {asc_degree:.1f}°", fontsize=12, ha='center', weight='bold')

        # Add chart info
        if "birth_details" in chart_data:
            birth = chart_data["birth_details"]
            info_text = f"Name: {birth.get('name', 'Unknown')}\n"
            info_text += f"Date: {birth.get('date', 'Unknown')}\n"
            info_text += f"Time: {birth.get('time', 'Unknown')}\n"
            info_text += f"Place: {birth.get('location', 'Unknown')}"

            ax.text(5, 10.5, info_text, fontsize=10, ha='center')

        # Set axis limits and remove ticks
        ax.set_xlim(-1, 11)
        ax.set_ylim(-1, 11)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title("North Indian Vedic Chart", fontsize=14)

        # Save or return the chart
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            return output_path
        else:
            # Return as base64 encoded image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            return img_str

    except Exception as e:
        logger.error(f"Error rendering Vedic chart: {e}")
        raise

def render_vedic_chart(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Render a simplified Vedic chart.

    Args:
        chart_data: Dictionary containing chart data
        output_path: Optional path to save the chart image

    Returns:
        Base64 encoded image data or path to saved image
    """
    # For now, this is an alias to the square chart
    return render_vedic_square_chart(chart_data, output_path)

def generate_multiple_charts(chart_data: Dict[str, Any], output_dir: str) -> Dict[str, str]:
    """
    Generate multiple chart visualizations from the same data.

    Args:
        chart_data: Dictionary containing chart data
        output_dir: Directory to save the chart images

    Returns:
        Dictionary mapping chart types to their file paths
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate charts
    results = {}

    # North Indian Vedic chart
    vedic_path = os.path.join(output_dir, "vedic_chart.png")
    results["vedic"] = render_vedic_square_chart(chart_data, vedic_path)

    # Add more chart types here as needed

    return results

def generate_comparison_chart(original_chart: Dict[str, Any], rectified_chart: Dict[str, Any],
                             output_path: Optional[str] = None) -> str:
    """
    Generate a comparison chart showing differences between original and rectified charts.

    Args:
        original_chart: Dictionary containing original chart data
        rectified_chart: Dictionary containing rectified chart data
        output_path: Optional path to save the chart image

    Returns:
        Base64 encoded image data or path to saved image
    """
    try:
        # Create figure with two subplots side by side
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

        # Draw original chart on left
        _draw_chart_on_axis(ax1, original_chart)
        ax1.set_title("Original Chart", fontsize=14)

        # Draw rectified chart on right
        _draw_chart_on_axis(ax2, rectified_chart)
        ax2.set_title("Rectified Chart", fontsize=14)

        # Add comparison info
        original_time = original_chart.get("birth_details", {}).get("time", "Unknown")
        rectified_time = rectified_chart.get("birth_details", {}).get("time", "Unknown")

        plt.figtext(0.5, 0.01, f"Original Time: {original_time} → Rectified Time: {rectified_time}",
                   ha="center", fontsize=12, bbox={"facecolor":"orange", "alpha":0.2, "pad":5})

        # Save or return the chart
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            return output_path
        else:
            # Return as base64 encoded image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            return img_str

    except Exception as e:
        logger.error(f"Error rendering comparison chart: {e}")
        raise

def _draw_chart_on_axis(ax, chart_data: Dict[str, Any]):
    """Helper function to draw a chart on a specific matplotlib axis"""
    # Draw the main square
    ax.add_patch(patches.Rectangle((0, 0), 10, 10, fill=False, linewidth=2))

    # Draw the inner square (for the center)
    ax.add_patch(patches.Rectangle((3, 3), 4, 4, fill=False, linewidth=2))

    # Draw the diagonal lines
    ax.plot([0, 10], [0, 10], 'k-', linewidth=2)
    ax.plot([0, 10], [10, 0], 'k-', linewidth=2)

    # Get house data
    houses = chart_data.get("houses", [])
    planets = chart_data.get("planets", {})
    ascendant = chart_data.get("ascendant", {})

    # House positions in the chart (North Indian style)
    house_positions = [
        (3, 7),    # House 1 (top center)
        (1, 7),    # House 2 (top left)
        (1, 5),    # House 3 (middle left)
        (1, 3),    # House 4 (bottom left)
        (3, 1),    # House 5 (bottom center)
        (5, 1),    # House 6 (bottom right)
        (7, 3),    # House 7 (middle right)
        (7, 5),    # House 8 (middle right)
        (7, 7),    # House 9 (top right)
        (5, 7),    # House 10 (top center)
        (5, 5),    # House 11 (center right)
        (3, 5)     # House 12 (center left)
    ]

    # Add house signs
    for i, pos in enumerate(house_positions):
        house_num = i + 1

        # Get the sign for this house
        sign = "Unknown"
        if i < len(houses):
            sign = houses[i].get("sign", "Unknown")

        # Add house number and sign
        ax.text(pos[0], pos[1] + 0.5, f"{house_num}", fontsize=12, ha='center')
        ax.text(pos[0], pos[1], f"{sign}", fontsize=10, ha='center')

        # Add planets in this house
        planets_in_house = []
        for planet_name, planet_data in planets.items():
            if planet_data.get("house") == house_num:
                planets_in_house.append(planet_name)

        # Display planets
        for j, planet in enumerate(planets_in_house):
            symbol = PLANET_SYMBOLS.get(planet, planet[:2])
            color = PLANET_COLORS.get(planet, "#000000")
            ax.text(pos[0], pos[1] - 0.3 - (j * 0.3), symbol, fontsize=10, ha='center', color=color)

    # Add ascendant marker
    asc_sign = ascendant.get("sign", "Unknown")
    asc_degree = ascendant.get("degree", 0)
    ax.text(5, 5, f"Asc: {asc_sign} {asc_degree:.1f}°", fontsize=12, ha='center', weight='bold')

    # Add chart info
    if "birth_details" in chart_data:
        birth = chart_data["birth_details"]
        info_text = f"Name: {birth.get('name', 'Unknown')}\n"
        info_text += f"Date: {birth.get('date', 'Unknown')}\n"
        info_text += f"Time: {birth.get('time', 'Unknown')}\n"
        info_text += f"Place: {birth.get('location', 'Unknown')}"

        ax.text(5, 10.5, info_text, fontsize=10, ha='center')

    # Set axis limits and remove ticks
    ax.set_xlim(-1, 11)
    ax.set_ylim(-1, 11)
    ax.set_xticks([])
    ax.set_yticks([])

def generate_3d_chart(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate a 3D visualization of the astrological chart.

    Args:
        chart_data: The chart data containing planets and houses.
        output_path: Optional path to save the chart image.

    Returns:
        Path to the saved image or base64 encoded image data.
    """
    try:
        # Extract planet data from chart
        planets = chart_data.get("planets", {})

        # Create figure and 3D axis
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        # Cast to proper 3D axes type for type checking
        ax3d = cast(Axes3DType, ax)

        # Create zodiac wheel (circle in 3D space)
        theta = np.linspace(0, 2 * np.pi, 100)
        x = 5 * np.cos(theta)
        y = 5 * np.sin(theta)
        z = np.zeros_like(theta)
        ax3d.plot(x, y, z, 'k-', linewidth=1)

        # Add zodiac divisions (spokes)
        for i in range(12):
            angle = i * 30 * np.pi / 180
            ax3d.plot([0, 5 * np.cos(angle)], [0, 5 * np.sin(angle)], [0, 0], 'k-', linewidth=0.5)

        # Add zodiac sign markers
        for i, sign in enumerate(ZODIAC_SIGNS):
            angle = i * 30 * np.pi / 180
            x_pos = 5.5 * np.cos(angle)
            y_pos = 5.5 * np.sin(angle)
            symbol = ZODIAC_SYMBOLS.get(sign, sign[:3])
            ax3d.text(x_pos, y_pos, 0, symbol, fontsize=12, ha='center', va='center')

        # Plot planets
        for planet_name, planet_data in planets.items():
            # Get planet longitude and convert to radians
            longitude = planet_data.get("longitude", 0)
            angle = (90 - longitude) * np.pi / 180  # Adjust to start from top

            # Calculate position
            x_pos = 4 * np.cos(angle)
            y_pos = 4 * np.sin(angle)
            z_pos = 0.5  # Slightly above the zodiac wheel

            # Plot planet
            symbol = PLANET_SYMBOLS.get(planet_name, planet_name[:2])
            color = PLANET_COLORS.get(planet_name, "#000000")

            # Fix the scatter method call with proper zs parameter type
            ax3d.scatter(xs=x_pos, ys=y_pos, zs=int(z_pos), c=color, s=100)
            ax3d.text(x_pos, y_pos, z_pos + 0.3, symbol, fontsize=10, ha='center', color=color)

        # Add ascendant
        ascendant = chart_data.get("ascendant", {})
        asc_longitude = ascendant.get("longitude", 0)
        asc_angle = (90 - asc_longitude) * np.pi / 180

        # Draw ascendant line
        ax3d.plot([0, 6 * np.cos(asc_angle)], [0, 6 * np.sin(asc_angle)], [0, 0], 'r-', linewidth=2)

        # Set labels and title
        ax3d.set_xlabel('X')
        ax3d.set_ylabel('Y')
        ax3d.set_zlabel('Z')
        ax3d.set_title("3D Chart Visualization", fontsize=14)

        # Set equal aspect ratio
        # Use a float value for set_box_aspect if available (newer matplotlib versions)
        if hasattr(ax3d, 'set_box_aspect'):
            ax3d.set_box_aspect((1, 1, 0.5))  # This works in newer matplotlib

        # Remove grid and background
        ax3d.grid(False)

        # Handle pane properties if available (depends on matplotlib version)
        # Wrap each property access in its own try/except to handle different matplotlib versions
        for axis_name in ['xaxis', 'yaxis', 'zaxis']:
            if hasattr(ax3d, axis_name):
                axis = getattr(ax3d, axis_name)
                try:
                    if hasattr(axis, 'pane'):
                        axis.pane.fill = False
                except (AttributeError, TypeError):
                    # Just ignore if these properties aren't available
                    pass

        # Save or return the chart
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            return output_path
        else:
            # Return as base64 encoded image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            return img_str

    except Exception as e:
        logger.error(f"Error rendering 3D chart: {e}")
        raise

def generate_planet_table(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate a table of planetary positions.

    Args:
        chart_data: Dictionary containing chart data
        output_path: Optional path to save the table image

    Returns:
        Base64 encoded image data or path to saved image
    """
    try:
        # Get planet data
        planets = chart_data.get("planets", {})

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, len(planets) * 0.5 + 2))

        # Hide axis
        ax.axis('tight')
        ax.axis('off')

        # Prepare table data
        table_data = []
        for planet_name, planet_data in planets.items():
            sign = planet_data.get("sign", "Unknown")
            degree = planet_data.get("degree", 0)
            house = planet_data.get("house", 0)
            retrograde = "R" if planet_data.get("retrograde", False) else ""

            table_data.append([
                planet_name,
                f"{sign}",
                f"{degree:.2f}°{retrograde}",
                f"House {house}"
            ])

        # Sort by traditional planet order
        planet_order = [
            "Sun", "Moon", "Mercury", "Venus", "Mars",
            "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
            "Rahu", "Ketu"
        ]

        # Sort table data
        def get_planet_order(row):
            try:
                return planet_order.index(row[0])
            except ValueError:
                return len(planet_order)

        table_data.sort(key=get_planet_order)

        # Create table
        table = ax.table(
            cellText=table_data,
            colLabels=["Planet", "Sign", "Degree", "House"],
            loc='center',
            cellLoc='center'
        )

        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.5)

        # Color the header row
        for i, key in enumerate(["Planet", "Sign", "Degree", "House"]):
            table[(0, i)].set_facecolor('#4472C4')
            table[(0, i)].set_text_props(color='white')

        # Add title
        plt.title("Planetary Positions", fontsize=14, pad=20)

        # Save or return the table
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            return output_path
        else:
            # Return as base64 encoded image
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            return img_str

    except Exception as e:
        logger.error(f"Error generating planet table: {e}")
        raise

def get_house_occupants(planets_data: Union[Dict[str, Any], List[Dict[str, Any]]], houses_data: List[Dict[str, Any]]) -> Dict[int, List[str]]:
    """
    Determine which planets occupy which houses.

    Args:
        planets_data: Planet data (either list of dictionaries or dictionary of planet data)
        houses_data: List of house data dictionaries

    Returns:
        Dictionary mapping house numbers to lists of planet abbreviations
    """
    house_occupants = {i: [] for i in range(1, 13)}

    # Convert planets dictionary to list if needed
    planets = []
    if planets_data and isinstance(planets_data, dict):
        # Handle dictionary format (where keys are planet names)
        for planet_key, planet_data in planets_data.items():
            # Create a planet entry with name from the key
            if isinstance(planet_data, dict):
                planet_entry = dict(planet_data)
                if "name" not in planet_entry:
                    planet_entry["name"] = planet_key.capitalize()
                planets.append(planet_entry)
    else:
        # Handle list format (or empty data)
        planets = planets_data if planets_data else []

    # Handle case where planets is a list of strings
    if planets and all(isinstance(p, str) for p in planets):
        # In this case, we can't determine house occupants
        # Just return empty dictionary
        return house_occupants

    # Create mapping of house cusps
    house_cusps = {}
    for house in houses_data:
        house_num = house.get("house_number")
        if house_num:
            house_cusps[house_num] = normalize_longitude(house.get("longitude", 0))

    # For each planet, find which house it's in
    for planet in planets:
        # Skip if planet is not a dictionary
        if not isinstance(planet, dict):
            continue

        planet_name = planet.get("name")
        if not planet_name:
            continue

        abbr = PLANET_SYMBOLS.get(planet_name, planet_name[:2])
        longitude = normalize_longitude(planet.get("longitude", 0))

        # Find which house contains this longitude
        for house_num in range(1, 13):
            next_house = house_num + 1 if house_num < 12 else 1
            start_long = house_cusps.get(house_num, 0)
            end_long = house_cusps.get(next_house, 0)

            # Handle case where house spans 0°
            if end_long < start_long:
                if longitude >= start_long or longitude < end_long:
                    house_occupants[house_num].append(abbr)
                    break
            else:
                if start_long <= longitude < end_long:
                    house_occupants[house_num].append(abbr)
                    break
        else:
            # If we can't determine the house, put it in house 1
            house_occupants[1].append(abbr)

    return house_occupants

def modify_chart_for_harmonic(chart_data: Dict[str, Any], harmonic_number: int) -> Dict[str, Any]:
    """
    Modify chart data for harmonic analysis (e.g., Navamsa or D4).

    Args:
        chart_data: Chart data from the API
        harmonic_number: Harmonic number to apply (e.g., 9 for Navamsa)

    Returns:
        Modified chart data
    """
    # Create a deep copy of the chart data
    modified_data = json.loads(json.dumps(chart_data))

    # Handle different planet data formats
    planets_data = modified_data.get("planets", [])

    if isinstance(planets_data, dict):
        # Dictionary format (keys are planet names)
        for planet_name, planet_data in planets_data.items():
            if isinstance(planet_data, dict) and "longitude" in planet_data:
                longitude = planet_data.get("longitude", 0)
                # Harmonic calculation: multiply by harmonic and take modulo 360
                harmonic_longitude = (longitude * harmonic_number) % 360
                planets_data[planet_name]["longitude"] = harmonic_longitude

                # Update sign and degree if present
                if "sign" in planet_data or "degree" in planet_data:
                    sign_num = int(harmonic_longitude / 30)
                    degree = harmonic_longitude % 30
                    if "sign" in planet_data and sign_num < len(ZODIAC_SIGNS):
                        planets_data[planet_name]["sign"] = ZODIAC_SIGNS[sign_num]
                    if "degree" in planet_data:
                        planets_data[planet_name]["degree"] = degree
    else:
        # List format (each item is a planet object)
        for i, planet in enumerate(planets_data):
            if isinstance(planet, dict):
                longitude = planet.get("longitude", 0)
                # Harmonic calculation: multiply by harmonic and take modulo 360
                harmonic_longitude = (longitude * harmonic_number) % 360
                planets_data[i]["longitude"] = harmonic_longitude

                # Update sign and degree if present
                if "sign" in planet or "degree" in planet:
                    sign_num = int(harmonic_longitude / 30)
                    degree = harmonic_longitude % 30
                    if "sign" in planet and sign_num < len(ZODIAC_SIGNS):
                        planets_data[i]["sign"] = ZODIAC_SIGNS[sign_num]
                    if "degree" in planet:
                        planets_data[i]["degree"] = degree

    # Update planets in modified data
    modified_data["planets"] = planets_data

    return modified_data
