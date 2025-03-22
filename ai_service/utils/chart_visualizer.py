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
import sys
import numpy as np
from datetime import datetime
import io
import base64
import tempfile

# Configure matplotlib with Agg backend before any other imports
import matplotlib  # type: ignore
matplotlib.use('Agg')  # Use non-interactive backend

# Import matplotlib modules
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.patches as patches  # type: ignore
from matplotlib.table import Table  # type: ignore

# Handle 3D plotting imports with fallbacks for compatibility
try:
    from mpl_toolkits.mplot3d import Axes3D  # type: ignore
    from typing import Any

    # Just define Axes3DType as Any to make type checking happy
    # This is the simplest most reliable solution
    Axes3DType = Any  # type: ignore

except ImportError:
    from typing import Any

    # Create a stub type for when 3D plotting is unavailable
    Axes3DType = Any  # type: ignore

# Import PDF generation libraries
import reportlab  # type: ignore
from reportlab.lib.pagesizes import letter, A4  # type: ignore
from reportlab.lib import colors  # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
from reportlab.platypus import SimpleDocTemplate, Table as RLTable, TableStyle, Paragraph, Spacer, Image  # type: ignore
from reportlab.pdfgen import canvas  # type: ignore
import matplotlib.font_manager as fm  # type: ignore
from PIL import Image as PILImage  # type: ignore

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
    "Sun": "#FFB900",
    "Moon": "#C0C0C0",
    "Mercury": "#9999FF",
    "Venus": "#00C000",
    "Mars": "#FF0000",
    "Jupiter": "#FFA500",
    "Saturn": "#0000A0",
    "Uranus": "#00FFFF",
    "Neptune": "#800080",
    "Pluto": "#A52A2A",
    "Rahu": "#708090",
    "Ketu": "#808000",
    "Ascendant": "#000000" # Black
}

# Remove duplicate type definition
# Axes3DType = plt.Axes  # type: ignore

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

def generate_comparison_chart(original_chart: Dict[str, Any], rectified_chart: Dict[str, Any], output_path: str) -> str:
    """
    Generate a comparison visualization between two charts (original and rectified).

    Args:
        original_chart: Original chart data
        rectified_chart: Rectified chart data
        output_path: Path to save the generated image

    Returns:
        Path to the saved image file
    """
    # Set up the figure with two side-by-side charts
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9))

    # Extract birth details
    original_details = original_chart.get("birth_details", {})
    rectified_details = rectified_chart.get("birth_details", {})

    original_time = original_details.get("birth_time", "")
    rectified_time = rectified_details.get("birth_time", "")

    # Set titles for both charts
    ax1.set_title(f"Original Chart\nBirth Time: {original_time}", fontsize=14)
    ax2.set_title(f"Rectified Chart\nBirth Time: {rectified_time}", fontsize=14)

    # Draw chart circles
    original_circle = patches.Circle((0, 0), 0.9, fill=False, color='black', linewidth=2)
    rectified_circle = patches.Circle((0, 0), 0.9, fill=False, color='black', linewidth=2)
    ax1.add_patch(original_circle)
    ax2.add_patch(rectified_circle)

    # Draw ascendant lines
    ax1.plot([0, -0.9], [0, 0], 'r-', linewidth=2)
    ax2.plot([0, -0.9], [0, 0], 'r-', linewidth=2)

    # Draw house cusps for original chart
    draw_houses(ax1, original_chart.get("houses", []))

    # Draw house cusps for rectified chart
    draw_houses(ax2, rectified_chart.get("houses", []))

    # Draw planets for original chart
    draw_planets(ax1, original_chart.get("planets", []), color='blue')

    # Draw planets for rectified chart
    draw_planets(ax2, rectified_chart.get("planets", []), color='red')

    # Set equal aspect ratios and remove axis ticks
    ax1.set_aspect('equal')
    ax1.set_xlim(-1.1, 1.1)
    ax1.set_ylim(-1.1, 1.1)
    ax1.axis('off')

    ax2.set_aspect('equal')
    ax2.set_xlim(-1.1, 1.1)
    ax2.set_ylim(-1.1, 1.1)
    ax2.axis('off')

    # Add a main title to the figure with comparison info
    time_diff_mins = calculate_time_difference(original_time, rectified_time)
    plt.suptitle(f"Chart Comparison\nTime Difference: {abs(time_diff_mins)} minutes {'later' if time_diff_mins > 0 else 'earlier'}",
                fontsize=16)

    # Save the comparison chart
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path

def draw_houses(ax, houses):
    """Helper function to draw house cusps on a chart axis."""
    for house in houses:
        # Convert house positions to angles
        house_num = house.get("number", 0)
        sign = house.get("sign", "")
        degree = house.get("degree", 0)

        # Calculate sign index
        sign_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3,
                     "Leo": 4, "Virgo": 5, "Libra": 6, "Scorpio": 7,
                     "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(sign, 0)

        # Calculate angle
        angle = (sign_index * 30 + degree) * math.pi / 180

        # Convert to cartesian coordinates
        x = 0.9 * math.cos(angle - math.pi/2)
        y = 0.9 * math.sin(angle - math.pi/2)

        # Draw house cusp line
        ax.plot([0, x], [0, y], 'k-', linewidth=1)

        # Add house number
        text_x = 1.0 * math.cos(angle - math.pi/2)
        text_y = 1.0 * math.sin(angle - math.pi/2)
        ax.text(text_x, text_y, str(house_num), fontsize=10)

def draw_planets(ax, planets, color='blue'):
    """Helper function to draw planets on a chart axis."""
    # Handle both list and dict formats of planets
    if isinstance(planets, dict):
        planets_list = []
        for name, data in planets.items():
            if isinstance(data, dict):
                planet_data = data.copy()
                planet_data["name"] = name
                planets_list.append(planet_data)
        planets = planets_list

    for planet in planets:
        name = planet.get("name", "")
        sign = planet.get("sign", "")
        degree = planet.get("degree", 0)

        # Calculate sign index
        sign_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3,
                     "Leo": 4, "Virgo": 5, "Libra": 6, "Scorpio": 7,
                     "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(sign, 0)

        # Calculate angle
        angle = (sign_index * 30 + degree) * math.pi / 180

        # Plot at 75% of radius for planets
        x = 0.75 * math.cos(angle - math.pi/2)
        y = 0.75 * math.sin(angle - math.pi/2)

        # Plot planet
        ax.plot(x, y, 'o', color=color, markersize=8)

        # Add planet symbol or abbreviation
        symbols = {
            "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
            "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇"
        }

        symbol = symbols.get(name, name[:2])
        ax.text(x + 0.05, y + 0.05, symbol, fontsize=10, color=color)

def calculate_time_difference(time1, time2):
    """Calculate difference between two time strings in minutes."""
    if not time1 or not time2:
        return 0

    try:
        # Parse time strings (format: HH:MM or HH:MM:SS)
        t1_parts = time1.split(":")
        t2_parts = time2.split(":")

        # Extract hours and minutes
        hours1 = int(t1_parts[0])
        minutes1 = int(t1_parts[1])

        hours2 = int(t2_parts[0])
        minutes2 = int(t2_parts[1])

        # Calculate total minutes
        total_minutes1 = hours1 * 60 + minutes1
        total_minutes2 = hours2 * 60 + minutes2

        # Return difference
        return total_minutes2 - total_minutes1
    except (ValueError, IndexError):
        return 0

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
        ax3d = cast(Any, ax)

        # Create zodiac wheel (circle in 3D space)
        theta = np.linspace(0, 2 * np.pi, 100)
        x = 5 * np.cos(theta)
        y = 5 * np.sin(theta)
        z = np.zeros_like(theta)
        ax3d.plot(x, y, z, 'k-', linewidth=1)  # type: ignore

        # Add zodiac divisions (spokes)
        for i in range(12):
            angle = i * 30 * np.pi / 180
            ax3d.plot([0, 5 * np.cos(angle)], [0, 5 * np.sin(angle)], [0, 0], 'k-', linewidth=0.5)  # type: ignore

        # Add zodiac sign markers
        for i, sign in enumerate(ZODIAC_SIGNS):
            angle = i * 30 * np.pi / 180
            x_pos = 5.5 * np.cos(angle)
            y_pos = 5.5 * np.sin(angle)
            symbol = ZODIAC_SYMBOLS.get(sign, sign[:3])
            ax3d.text(x_pos, y_pos, 0, symbol, fontsize=12, ha='center', va='center')  # type: ignore

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
            ax3d.scatter(xs=x_pos, ys=y_pos, zs=int(z_pos), c=color, s=100)  # type: ignore
            ax3d.text(x_pos, y_pos, z_pos + 0.3, symbol, fontsize=10, ha='center', color=color)  # type: ignore

        # Add ascendant
        ascendant = chart_data.get("ascendant", {})
        asc_longitude = ascendant.get("longitude", 0)
        asc_angle = (90 - asc_longitude) * np.pi / 180

        # Draw ascendant line
        ax3d.plot([0, 6 * np.cos(asc_angle)], [0, 6 * np.sin(asc_angle)], [0, 0], 'r-', linewidth=2)  # type: ignore

        # Set labels and title
        ax3d.set_xlabel('X')  # type: ignore
        ax3d.set_ylabel('Y')  # type: ignore
        ax3d.set_zlabel('Z')  # type: ignore
        ax3d.set_title("3D Chart Visualization", fontsize=14)  # type: ignore

        # Set equal aspect ratio
        # Use a float value for set_box_aspect if available (newer matplotlib versions)
        if hasattr(ax3d, 'set_box_aspect'):
            ax3d.set_box_aspect((1, 1, 0.5))  # This works in newer matplotlib  # type: ignore

        # Remove grid and background
        ax3d.grid(False)  # type: ignore

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

def generate_planet_table(chart_data: Dict[str, Any], output_path: str) -> str:
    """
    Generate a table visualization of planetary positions.

    Args:
        chart_data: Dictionary containing chart data
        output_path: Path to save the generated image

    Returns:
        Path to the saved image file
    """
    # Get planets data
    planets = chart_data.get("planets", [])

    # Handle both list and dict formats of planets
    if isinstance(planets, dict):
        planets_list = []
        for name, data in planets.items():
            if isinstance(data, dict):
                planet_data = data.copy()
                planet_data["name"] = name
                planets_list.append(planet_data)
        planets = planets_list

    # Sort planets in traditional order
    planet_order = {"Sun": 1, "Moon": 2, "Mercury": 3, "Venus": 4, "Mars": 5,
                   "Jupiter": 6, "Saturn": 7, "Uranus": 8, "Neptune": 9, "Pluto": 10}

    sorted_planets = sorted(planets, key=lambda p: planet_order.get(p.get("name", ""), 99))

    # Create figure and axis for the table
    fig, ax = plt.subplots(figsize=(10, 6))

    # Hide axes
    ax.axis('off')
    ax.axis('tight')

    # Create table data
    table_data = []

    # Header row
    table_data.append(["Planet", "Sign", "Degree", "House", "Retrograde"])

    # Add planet data
    for planet in sorted_planets:
        name = planet.get("name", "")
        sign = planet.get("sign", "")
        degree = planet.get("degree", 0)
        house = planet.get("house", "")
        retrograde = "R" if planet.get("retrograde", False) else ""

        # Format the degree with minutes
        degree_int = int(degree)
        minutes = int((degree - degree_int) * 60)
        degree_str = f"{degree_int}° {minutes}'"

        # Add row to table
        table_data.append([name, sign, degree_str, str(house), retrograde])

    # Create the table
    table = ax.table(
        cellText=table_data,
        cellLoc='center',
        loc='center',
        colWidths=[0.2, 0.25, 0.25, 0.15, 0.15]
    )

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(12)

    # Style header row
    for (i, j), cell in table.get_celld().items():
        if i == 0:  # Header row
            cell.set_text_props(fontproperties=fm.FontProperties(weight='bold'))
            cell.set_facecolor('#E0E0E0')  # Light gray background

        # Add borders
        cell.set_edgecolor('black')

        # Adjust cell height
        cell.set_height(0.06)

    # Add chart title
    birth_details = chart_data.get("birth_details", {})
    birth_date = birth_details.get("birth_date", "")
    birth_time = birth_details.get("birth_time", "")
    title = f"Planetary Positions\n{birth_date} {birth_time}"
    plt.title(title, fontsize=16, pad=20)

    # Adjust layout and save
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path

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

def generate_chart_image(chart_data: Dict[str, Any], output_path: str) -> str:
    """
    Generate visualization of an astrological chart.

    Args:
        chart_data: Dictionary containing chart data
        output_path: Path to save the generated image

    Returns:
        Path to the saved image file
    """
    # Set up the figure
    fig, ax = plt.subplots(figsize=(10, 10))

    # Draw the chart circle
    chart_circle = patches.Circle((0, 0), 0.9, fill=False, color='black', linewidth=2)
    ax.add_patch(chart_circle)

    # Draw the ascendant line (usually at 9 o'clock position)
    ax.plot([0, -0.9], [0, 0], 'r-', linewidth=2)

    # Calculate house cusps
    houses = chart_data.get("houses", [])
    house_angles = []

    # Check if houses is an array of floats or an array of objects
    if houses and isinstance(houses[0], (int, float)):
        # Convert array of float longitudes to house objects
        house_objects = []
        for i, longitude in enumerate(houses):
            # Calculate sign and degree from longitude
            sign_index = int(longitude / 30) % 12
            degree = longitude % 30

            # Map sign index to sign name
            sign_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                         "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
            sign = sign_names[sign_index]

            # Create house object
            house_objects.append({
                "number": i + 1,
                "sign": sign,
                "degree": degree
            })
        houses = house_objects

    for house in houses:
        # Convert house positions to angles (0 = Aries, 30 = Taurus, etc.)
        house_num = house.get("number", 0)
        sign = house.get("sign", "")
        degree = house.get("degree", 0)

        # Calculate sign index (0 = Aries, 1 = Taurus, etc.)
        sign_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3,
                     "Leo": 4, "Virgo": 5, "Libra": 6, "Scorpio": 7,
                     "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(sign, 0)

        # Calculate total angle (0 = Aries at 0°, 360 = Pisces at 30°)
        angle = (sign_index * 30 + degree) * math.pi / 180

        # Convert to cartesian coordinates (rotate 90° counter-clockwise for traditional chart layout)
        x = 0.9 * math.cos(angle - math.pi/2)
        y = 0.9 * math.sin(angle - math.pi/2)

        # Store house cusp information
        house_angles.append((house_num, angle, x, y))

        # Draw house cusps
        ax.plot([0, x], [0, y], 'k-', linewidth=1)

        # Add house numbers
        text_x = 1.0 * math.cos(angle - math.pi/2)
        text_y = 1.0 * math.sin(angle - math.pi/2)
        ax.text(text_x, text_y, str(house_num), fontsize=12)

    # Plot planets
    planets = chart_data.get("planets", [])

    # Handle both list and dict formats of planets
    if isinstance(planets, dict):
        planets_list = []
        for name, data in planets.items():
            if isinstance(data, dict):
                planet_data = data.copy()
                planet_data["name"] = name
                planets_list.append(planet_data)
        planets = planets_list

    for planet in planets:
        name = planet.get("name", "")
        sign = planet.get("sign", "")
        degree = planet.get("degree", 0)

        # Calculate sign index (0 = Aries, 1 = Taurus, etc.)
        sign_index = {"Aries": 0, "Taurus": 1, "Gemini": 2, "Cancer": 3,
                     "Leo": 4, "Virgo": 5, "Libra": 6, "Scorpio": 7,
                     "Sagittarius": 8, "Capricorn": 9, "Aquarius": 10, "Pisces": 11}.get(sign, 0)

        # Calculate total angle
        angle = (sign_index * 30 + degree) * math.pi / 180

        # Plot at 75% of radius for planets
        x = 0.75 * math.cos(angle - math.pi/2)
        y = 0.75 * math.sin(angle - math.pi/2)

        # Plot planet
        ax.plot(x, y, 'bo', markersize=8)

        # Add planet symbol or abbreviation
        symbols = {
            "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
            "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇"
        }

        symbol = symbols.get(name, name[:2])
        ax.text(x + 0.05, y + 0.05, symbol, fontsize=12)

    # Add chart title
    birth_details = chart_data.get("birth_details", {})
    birth_date = birth_details.get("birth_date", "")
    birth_time = birth_details.get("birth_time", "")
    location = birth_details.get("location", "")

    plt.title(f"Birth Chart\n{birth_date} {birth_time}\n{location}")

    # Set equal aspect ratio and remove axis ticks
    ax.set_aspect('equal')
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    plt.axis('off')

    # Save the chart
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return output_path

def save_chart_as_pdf(chart_data: Dict[str, Any], output_path: str) -> str:
    """
    Generate a professional PDF report of an astrological chart.

    Args:
        chart_data: Dictionary containing chart data
        output_path: Path to save the PDF file

    Returns:
        Path to the saved PDF file
    """
    # Create temporary directory for images
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate chart image first
        chart_img_path = os.path.join(temp_dir, "chart_image.png")
        chart_img_path = generate_chart_image(chart_data, chart_img_path)

        # Generate a table of planetary positions
        planet_table_path = os.path.join(temp_dir, "planet_table.png")
        generate_planet_table(chart_data, planet_table_path)

        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Get styles
        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        heading_style = styles["Heading2"]
        normal_style = styles["Normal"]

        # Add custom style for astrological interpretations
        astro_style = ParagraphStyle(
            'AstroStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            leftIndent=10,
            rightIndent=10,
            firstLineIndent=0,
            spaceBefore=5,
            spaceAfter=5
        )

        # Create content elements
        elements = []

        # Add title
        birth_details = chart_data.get("birth_details", {})
        name = birth_details.get("name", "")
        title_text = f"Astrological Chart Analysis" + (f" for {name}" if name else "")
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 12))

        # Add birth details
        birth_date = birth_details.get("birth_date", "")
        birth_time = birth_details.get("birth_time", "")
        location = birth_details.get("location", "")

        details_text = f"<b>Date:</b> {birth_date}<br/><b>Time:</b> {birth_time}<br/><b>Location:</b> {location}"
        elements.append(Paragraph("Birth Details", heading_style))
        elements.append(Paragraph(details_text, normal_style))
        elements.append(Spacer(1, 12))

        # Add chart image
        if os.path.exists(chart_img_path):
            elements.append(Paragraph("Birth Chart", heading_style))
            img_width = 400
            img = Image(chart_img_path, width=img_width, height=img_width)
            elements.append(img)
            elements.append(Spacer(1, 12))

        # Add planetary positions table
        elements.append(Paragraph("Planetary Positions", heading_style))

        # Create table directly in ReportLab instead of using an image
        table_data = [["Planet", "Sign", "Degree", "House", "Retrograde"]]

        # Get planets data
        planets = chart_data.get("planets", [])

        # Handle both list and dict formats of planets
        if isinstance(planets, dict):
            planets_list = []
            for name, data in planets.items():
                if isinstance(data, dict):
                    planet_data = data.copy()
                    planet_data["name"] = name
                    planets_list.append(planet_data)
            planets = planets_list

        # Sort planets in traditional order
        planet_order = {"Sun": 1, "Moon": 2, "Mercury": 3, "Venus": 4, "Mars": 5,
                       "Jupiter": 6, "Saturn": 7, "Uranus": 8, "Neptune": 9, "Pluto": 10}

        sorted_planets = sorted(planets, key=lambda p: planet_order.get(p.get("name", ""), 99))

        for planet in sorted_planets:
            name = planet.get("name", "")
            sign = planet.get("sign", "")
            degree = planet.get("degree", 0)
            house = planet.get("house", "")
            retrograde = "R" if planet.get("retrograde", False) else ""

            # Format the degree with minutes
            degree_int = int(degree)
            minutes = int((degree - degree_int) * 60)
            degree_str = f"{degree_int}° {minutes}'"

            # Add row to table
            table_data.append([name, sign, degree_str, str(house), retrograde])

        # Create the table
        planet_table = RLTable(table_data, colWidths=[80, 80, 80, 60, 60])

        # Add table style
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])

        planet_table.setStyle(table_style)
        elements.append(planet_table)
        elements.append(Spacer(1, 20))

        # Add house information
        elements.append(Paragraph("House Cusps", heading_style))

        # Create house cusps table
        house_table_data = [["House", "Sign", "Degree"]]

        houses = chart_data.get("houses", [])

        # Check if houses is an array of floats or an array of objects
        if houses and isinstance(houses[0], (int, float)):
            # Convert array of float longitudes to house objects
            house_objects = []
            for i, longitude in enumerate(houses):
                # Calculate sign and degree from longitude
                sign_index = int(longitude / 30) % 12
                degree = longitude % 30

                # Map sign index to sign name
                sign_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                             "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                sign = sign_names[sign_index]

                # Create house object
                house_objects.append({
                    "number": i + 1,
                    "sign": sign,
                    "degree": degree
                })
            houses = house_objects

        for house in houses:
            house_num = house.get("number", "")
            sign = house.get("sign", "")
            degree = house.get("degree", 0)

            # Format the degree with minutes
            degree_int = int(degree)
            minutes = int((degree - degree_int) * 60)
            degree_str = f"{degree_int}° {minutes}'"

            # Add row to table
            house_table_data.append([str(house_num), sign, degree_str])

        # Create the table
        house_table = RLTable(house_table_data, colWidths=[60, 100, 100])

        # Add table style (same as planet table)
        house_table.setStyle(table_style)
        elements.append(house_table)
        elements.append(Spacer(1, 20))

        # Add aspects section
        elements.append(Paragraph("Planetary Aspects", heading_style))

        aspects = chart_data.get("aspects", [])
        if aspects:
            aspects_text = ""
            for aspect in aspects[:15]:  # Limit to first 15 aspects to avoid overwhelming
                planet1 = aspect.get("planet1", "")
                planet2 = aspect.get("planet2", "")
                aspect_type = aspect.get("type", "")
                orb = aspect.get("orb", 0)

                aspects_text += f"<b>{planet1} {aspect_type} {planet2}</b> (Orb: {orb:.1f}°)<br/>"

            elements.append(Paragraph(aspects_text, astro_style))
        else:
            elements.append(Paragraph("No significant aspects found in the chart data.", normal_style))

        elements.append(Spacer(1, 12))

        # Add interpretation if available
        if "interpretation" in chart_data:
            elements.append(Paragraph("Chart Interpretation", heading_style))

            interpretation = chart_data.get("interpretation", {})
            if isinstance(interpretation, dict):
                # Handle structured interpretation

                # Overall summary
                if "overall_summary" in interpretation:
                    elements.append(Paragraph("<b>Overall Summary</b>", astro_style))
                    elements.append(Paragraph(interpretation["overall_summary"], normal_style))
                    elements.append(Spacer(1, 8))

                # Ascendant interpretation
                if "ascendant" in interpretation:
                    elements.append(Paragraph("<b>Ascendant</b>", astro_style))
                    elements.append(Paragraph(interpretation["ascendant"], normal_style))
                    elements.append(Spacer(1, 8))

                # Planet interpretations
                if "planets" in interpretation and isinstance(interpretation["planets"], dict):
                    elements.append(Paragraph("<b>Planetary Positions</b>", astro_style))

                    for planet, text in interpretation["planets"].items():
                        elements.append(Paragraph(f"<b>{planet}</b>: {text}", normal_style))
                        elements.append(Spacer(1, 4))

                # Aspect interpretations
                if "aspects" in interpretation:
                    elements.append(Paragraph("<b>Aspects</b>", astro_style))
                    elements.append(Paragraph(interpretation["aspects"], normal_style))
            else:
                # Handle plain text interpretation
                elements.append(Paragraph(str(interpretation), normal_style))

        # Add validation information if available
        if "verification" in chart_data:
            verification = chart_data.get("verification", {})
            verification_message = verification.get("message", "")

            if verification_message:
                elements.append(Spacer(1, 20))
                elements.append(Paragraph("Verification", heading_style))
                elements.append(Paragraph(verification_message, normal_style))

        # Add footer
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M')}"
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(footer_text, normal_style))

        # Build the PDF
        doc.build(elements)

        return output_path
