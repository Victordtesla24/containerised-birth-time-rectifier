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
import traceback
import uuid
import random

# Configure matplotlib with Agg backend before any other imports
import matplotlib  # type: ignore
matplotlib.use('Agg')  # Use non-interactive backend

# Import matplotlib modules
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.patches as patches  # type: ignore
from matplotlib.table import Table  # type: ignore
from matplotlib.patches import Circle
from matplotlib.lines import Line2D
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

# Import Axes from matplotlib.axes for proper typing
from matplotlib.axes import Axes

# Import 3D plotting tools correctly
try:
    from mpl_toolkits.mplot3d import Axes3D  # type: ignore
    HAVE_3D = True
except ImportError:
    HAVE_3D = False

# Import PDF generation libraries
import reportlab  # type: ignore
from reportlab.lib.pagesizes import letter, A4, LEGAL  # type: ignore
from reportlab.lib import colors  # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
from reportlab.lib.units import inch  # type: ignore
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle  # type: ignore
from reportlab.pdfgen import canvas  # type: ignore
import matplotlib.font_manager as fm  # type: ignore
from PIL import Image as PILImage  # type: ignore # noqa

from ai_service.core.rectification.constants import PLANETS_LIST

# Configure logger
logger = logging.getLogger(__name__)

# Local implementations of formatting functions to avoid circular imports
def format_degree(degree: float, include_sign: bool = False, include_minutes: bool = True) -> str:
    """Format a degree value into a human-readable format."""
    # Normalize degree value to 0-360 range
    degree = degree % 360

    # Get zodiac sign if requested
    sign_name = ""
    if include_sign:
        signs = [
            "Aries", "Taurus", "Gemini", "Cancer",
            "Leo", "Virgo", "Libra", "Scorpio",
            "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        sign_index = int(degree / 30)
        sign_name = signs[sign_index] + " "

    # Calculate degrees within sign
    degree_in_sign = degree % 30

    # Format degrees and minutes
    degree_part = int(degree_in_sign)

    if include_minutes:
        minutes_part = int((degree_in_sign - degree_part) * 60)
        return f"{sign_name}{degree_part}°{minutes_part}'"
    else:
        return f"{sign_name}{degree_part}°"

def format_longitude(longitude: float, format_type: str = "full") -> str:
    """Format a celestial longitude into a human-readable format."""
    # Normalize longitude value to 0-360 range
    longitude = longitude % 360

    # Define zodiac signs
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    # Get sign and position within sign
    sign_index = int(longitude / 30)
    sign_name = signs[sign_index]
    pos_in_sign = longitude % 30

    # Format based on requested format type
    if format_type == "sign_only":
        return sign_name
    elif format_type == "degree_only":
        return format_degree(pos_in_sign, include_sign=False)
    else:  # "full" format
        degree_part = int(pos_in_sign)
        minutes_part = int((pos_in_sign - degree_part) * 60)
        return f"{sign_name} {degree_part}°{minutes_part}'"

def format_time(time_value: Union[str, datetime], include_seconds: bool = True) -> str:
    """Format a time value into a consistent human-readable format."""
    # Convert string to datetime if needed
    if isinstance(time_value, str):
        # Try different formats
        formats = [
            "%H:%M:%S",
            "%H:%M",
            "%I:%M:%S %p",
            "%I:%M %p",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M"
        ]

        for fmt in formats:
            try:
                time_value = datetime.strptime(time_value, fmt)
                break
            except ValueError:
                continue
        else:
            # If no format matched, return the original string
            return time_value

    # Format datetime object
    if isinstance(time_value, datetime):
        if include_seconds:
            return time_value.strftime("%H:%M:%S")
        else:
            return time_value.strftime("%H:%M")

    # If we couldn't parse the input, return it as is
    return str(time_value)

# Local implementation of render_chart_in_subplot to avoid circular imports
def render_chart_in_subplot(ax: Any, chart_data: Dict[str, Any], title: Optional[str] = None) -> None:
    """
    Render a chart in a matplotlib subplot.

    Args:
        ax: The matplotlib axes to render on
        chart_data: The chart data to render
        title: Optional title for the chart
    """
    # Set title if provided
    if title:
        ax.set_title(title)

    # Setup the plot area
    ax.set_aspect('equal')
    ax.set_xlim(-100, 100)
    ax.set_ylim(-100, 100)
    ax.axis('off')

    # Draw a basic chart representation (wheel)
    circle = patches.Circle((0, 0), 90, fill=False, color='black')
    ax.add_patch(circle)

    # Get planets and house data
    planets = chart_data.get("planets", {})
    houses = chart_data.get("houses", [])
    ascendant = chart_data.get("ascendant", {})

    # Draw houses
    num_houses = 12
    for i in range(num_houses):
        angle = math.radians(i * (360 / num_houses))
        # Draw line from center to edge
        ax.plot([0, 90 * math.cos(angle)], [0, 90 * math.sin(angle)], 'k-')

        # Place house number labels
        label_radius = 75
        label_x = label_radius * math.cos(angle + math.radians(15))
        label_y = label_radius * math.sin(angle + math.radians(15))
        ax.text(label_x, label_y, str(i+1), ha='center', va='center')

    # Place planets
    if isinstance(planets, dict):
        for planet_name, planet_data in planets.items():
            # Get longitude or degree
            longitude = 0
            if isinstance(planet_data, dict):
                longitude = planet_data.get("longitude", 0)

            # Calculate position
            angle = math.radians(longitude)
            radius = 60  # Place inside the circle
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)

            # Add planet symbol/name
            ax.text(x, y, planet_name[:3], ha='center', va='center',
                  bbox=dict(facecolor='white', alpha=0.7, boxstyle='circle'))

    # Add ascendant marker if available
    if ascendant and isinstance(ascendant, dict) and "longitude" in ascendant:
        asc_angle = math.radians(ascendant["longitude"])
        asc_x = 90 * math.cos(asc_angle)
        asc_y = 90 * math.sin(asc_angle)
        ax.plot([0, asc_x], [0, asc_y], 'r-', linewidth=2)
        ax.text(asc_x * 1.1, asc_y * 1.1, "ASC", color='red',
              ha='center', va='center', fontweight='bold')

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
    "Ascendant": "#000000"  # Black
}


def render_vedic_square_chart(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Render a Vedic square chart (North Indian style).

    Args:
        chart_data: Chart data dictionary
        output_path: Path to save the output image

    Returns:
        Path to the generated chart image
    """
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(10, 10))

    # Set up the chart as a square
    ax.set_aspect('equal')
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)

    # Draw the outer square
    square = patches.Rectangle((-1, -1), 2, 2, fill=False, color='black')
    ax.add_patch(square)

    # Draw the inner grid (3x3 grid)
    for i in range(-1, 2, 1):
        # Vertical lines
        ax.plot([i/3, i/3], [-1, 1], color='black', linestyle='-')
        # Horizontal lines
        ax.plot([-1, 1], [i/3, i/3], color='black', linestyle='-')

    # Map houses to positions in the North Indian style
    # The positions follow the traditional layout:
    # 1 12 11
    # 2  -  10
    # 3  4  9
    # 5  6  7
    house_positions = {
        1: (-2/3, 2/3),   # Top left
        2: (-2/3, 0),     # Middle left
        3: (-2/3, -2/3),  # Bottom left
        4: (0, -2/3),     # Bottom middle
        5: (2/3, -2/3),   # Bottom right
        6: (2/3, 0),      # Middle right
        7: (2/3, 2/3),    # Top right
        8: (0, 2/3),      # Top middle
        9: (0, 0),        # Center
        10: (0, 2/3),     # Top middle
        11: (2/3, 2/3),   # Top right
        12: (-2/3, 2/3)   # Top left
    }

    # Get houses from chart data
    houses = chart_data.get("houses", [])
    for house in houses:
        house_num = house.get("house", 0)
        sign = house.get("sign", "")

        # Skip if invalid house
        if house_num not in house_positions:
            continue

        # Get position for this house
        x, y = house_positions[house_num]

        # Label the house
        ax.text(x, y, f"{house_num}\n{sign}", fontsize=8,
                ha='center', va='center', color='blue')

    # Plot planets
    planets_list = chart_data.get("planets", [])
    if isinstance(planets_list, dict):
        # Convert dict to list if needed
        planets_list = [{"name": name, **data} for name, data in planets_list.items()]

    planet_symbols = {
        "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀", "mars": "♂",
        "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆", "pluto": "♇",
        "north_node": "☊", "south_node": "☋", "chiron": "⚷"
    }

    for planet in planets_list:
        if isinstance(planet, dict):
            planet_name = planet.get("name", "").lower()
            house = planet.get("house", 0)

            # Skip if invalid house
            if house not in house_positions:
                continue

            # Get position for this house
            x, y = house_positions[house]

            # Add a small offset for multiple planets in same house
            # This is a simplified approach; a more robust method would be needed
            # for charts with many planets in the same house
            x += random.uniform(-0.15, 0.15)
            y += random.uniform(-0.15, 0.15)

            # Get the symbol for the planet
            symbol = planet_symbols.get(planet_name, planet_name[0].upper())

            # Plot the planet
            ax.text(x, y, symbol, fontsize=12, ha='center', va='center',
                   color='red', weight='bold')

    # Remove axis ticks and labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')

    # Add title with birth information if available
    title = "Vedic Chart (North Indian Style)"
    if "birth_details" in chart_data:
        birth_details = chart_data["birth_details"]
        date_str = birth_details.get("date", "")
        time_str = birth_details.get("time", "")
        if date_str and time_str:
            title += f"\n{date_str} {time_str}"

    plt.title(title)

    # Save the chart if output path is provided
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        return output_path
    else:
        # If no output path, return a temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            plt.savefig(tmp.name, dpi=300, bbox_inches='tight')
            plt.close(fig)
            return tmp.name


def render_vedic_chart(chart_data: Dict[str, Any], output_path: Optional[str] = None, style: str = "north_indian") -> str:
    """
    Render a Vedic chart with enhanced options for different styles.

    Args:
        chart_data: Chart data dictionary
        output_path: Path to save the output image
        style: Chart style ('north_indian', 'south_indian', or 'east_indian')

    Returns:
        Path to the generated chart image
    """
    if style == "north_indian":
        return render_vedic_square_chart(chart_data, output_path)
    elif style == "south_indian":
        # Implement South Indian style chart (diamond layout)
        return render_vedic_south_indian(chart_data, output_path)
    elif style == "east_indian":
        # Implement East Indian style chart (circular layout)
        return render_vedic_east_indian(chart_data, output_path)
    else:
        logger.warning(f"Unknown Vedic chart style: {style}, defaulting to North Indian")
        return render_vedic_square_chart(chart_data, output_path)


def render_vedic_south_indian(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Render a South Indian style Vedic chart (diamond layout).

    Args:
        chart_data: Chart data dictionary
        output_path: Path to save the output image

    Returns:
        Path to the generated chart image
    """
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(10, 10))

    # Set up the chart as a diamond
    ax.set_aspect('equal')
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)

    # Draw the outer diamond
    diamond = patches.Polygon(np.array([
        (0, 1.2), (1.2, 0), (0, -1.2), (-1.2, 0)
    ]), fill=False, color='black')
    ax.add_patch(diamond)

    # Draw the inner grid (3x3 grid in diamond shape)
    # Draw lines connecting midpoints of outer diamond
    ax.plot([0, 0], [-1.2, 1.2], color='black', linestyle='-')
    ax.plot([-1.2, 1.2], [0, 0], color='black', linestyle='-')

    # Draw inner diamond
    inner_diamond = patches.Polygon(np.array([
        (0, 0.4), (0.4, 0), (0, -0.4), (-0.4, 0)
    ]), fill=False, color='black')
    ax.add_patch(inner_diamond)

    # Map houses to positions in the South Indian style
    house_positions = {
        1: (0, 0.8),     # Top
        2: (0.4, 0.4),   # Top right
        3: (0.8, 0),     # Right
        4: (0.4, -0.4),  # Bottom right
        5: (0, -0.8),    # Bottom
        6: (-0.4, -0.4), # Bottom left
        7: (-0.8, 0),    # Left
        8: (-0.4, 0.4),  # Top left
        9: (0, 0),       # Center
        10: (0.8, 0),    # Right
        11: (0.4, 0.4),  # Top right
        12: (0, 0.8)     # Top
    }

    # Get houses from chart data
    houses = chart_data.get("houses", [])
    for house in houses:
        house_num = house.get("house", 0)
        sign = house.get("sign", "")

        # Skip if invalid house
        if house_num not in house_positions:
            continue

        # Get position for this house
        x, y = house_positions[house_num]

        # Label the house
        ax.text(x, y, f"{house_num}\n{sign}", fontsize=8,
                ha='center', va='center', color='blue')

    # Plot planets - similar to North Indian style but with different positions
    planets_list = chart_data.get("planets", [])
    if isinstance(planets_list, dict):
        planets_list = [{"name": name, **data} for name, data in planets_list.items()]

    planet_symbols = {
        "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀", "mars": "♂",
        "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆", "pluto": "♇",
        "north_node": "☊", "south_node": "☋", "chiron": "⚷"
    }

    for planet in planets_list:
        if isinstance(planet, dict):
            planet_name = planet.get("name", "").lower()
            house = planet.get("house", 0)

            # Skip if invalid house
            if house not in house_positions:
                continue

            # Get position for this house
            x, y = house_positions[house]

            # Add a small offset for multiple planets in same house
            x += random.uniform(-0.15, 0.15)
            y += random.uniform(-0.15, 0.15)

            # Get the symbol for the planet
            symbol = planet_symbols.get(planet_name, planet_name[0].upper())

            # Plot the planet
            ax.text(x, y, symbol, fontsize=12, ha='center', va='center',
                   color='red', weight='bold')

    # Remove axis ticks and labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')

    # Add title with birth information if available
    title = "Vedic Chart (South Indian Style)"
    if "birth_details" in chart_data:
        birth_details = chart_data["birth_details"]
        date_str = birth_details.get("date", "")
        time_str = birth_details.get("time", "")
        if date_str and time_str:
            title += f"\n{date_str} {time_str}"

    plt.title(title)

    # Save the chart if output path is provided
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        return output_path
    else:
        # If no output path, return a temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            plt.savefig(tmp.name, dpi=300, bbox_inches='tight')
            plt.close(fig)
            return tmp.name


def render_vedic_east_indian(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Render an East Indian style Vedic chart (circular layout).

    Args:
        chart_data: Chart data dictionary
        output_path: Path to save the output image

    Returns:
        Path to the generated chart image
    """
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(10, 10))

    # Set up the chart as a circle
    ax.set_aspect('equal')
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)

    # Draw the outer circle
    circle = patches.Circle((0, 0), 1, fill=False, color='black')
    ax.add_patch(circle)

    # Draw the inner circle
    inner_circle = patches.Circle((0, 0), 0.5, fill=False, color='black')
    ax.add_patch(inner_circle)

    # Draw dividing lines for the 12 houses
    for i in range(12):
        angle = i * 30 * (math.pi / 180)  # Convert to radians
        x = math.cos(angle)
        y = math.sin(angle)
        ax.plot([0, x], [0, y], color='black', linestyle='-')

    # Map houses to positions in the circular layout
    house_positions = {}
    for i in range(1, 13):
        angle = (i - 1) * 30 * (math.pi / 180)  # Convert to radians
        x = 0.75 * math.cos(angle + (15 * math.pi / 180))  # Offset by 15 degrees to center in house
        y = 0.75 * math.sin(angle + (15 * math.pi / 180))
        house_positions[i] = (x, y)

    # Get houses from chart data
    houses = chart_data.get("houses", [])
    for house in houses:
        house_num = house.get("house", 0)
        sign = house.get("sign", "")

        # Skip if invalid house
        if house_num not in house_positions:
            continue

        # Get position for this house
        x, y = house_positions[house_num]

        # Label the house
        ax.text(x, y, f"{house_num}\n{sign}", fontsize=8,
                ha='center', va='center', color='blue')

    # Plot planets - similar to other styles but with circular positioning
    planets_list = chart_data.get("planets", [])
    if isinstance(planets_list, dict):
        planets_list = [{"name": name, **data} for name, data in planets_list.items()]

    planet_symbols = {
        "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀", "mars": "♂",
        "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆", "pluto": "♇",
        "north_node": "☊", "south_node": "☋", "chiron": "⚷"
    }

    for planet in planets_list:
        if isinstance(planet, dict):
            planet_name = planet.get("name", "").lower()
            house = planet.get("house", 0)

            # Skip if invalid house
            if house not in house_positions:
                continue

            # Get position for this house
            x, y = house_positions[house]

            # Add a small offset for multiple planets in same house
            x += random.uniform(-0.1, 0.1)
            y += random.uniform(-0.1, 0.1)

            # Get the symbol for the planet
            symbol = planet_symbols.get(planet_name, planet_name[0].upper())

            # Plot the planet
            ax.text(x, y, symbol, fontsize=12, ha='center', va='center',
                   color='red', weight='bold')

    # Remove axis ticks and labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')

    # Add title with birth information if available
    title = "Vedic Chart (East Indian Style)"
    if "birth_details" in chart_data:
        birth_details = chart_data["birth_details"]
        date_str = birth_details.get("date", "")
        time_str = birth_details.get("time", "")
        if date_str and time_str:
            title += f"\n{date_str} {time_str}"

    plt.title(title)

    # Save the chart if output path is provided
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        return output_path
    else:
        # If no output path, return a temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            plt.savefig(tmp.name, dpi=300, bbox_inches='tight')
            plt.close(fig)
            return tmp.name


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


def generate_vedic_chart(chart_data, output_path=None, style="north_indian"):
    """
    Generate a Vedic chart visualization with proper export integration.

    Args:
        chart_data: Chart data to visualize
        output_path: Path to save the generated image
        style: Chart style ('north_indian' or 'south_indian')

    Returns:
        Dictionary with path and metadata about the generated chart
    """
    try:
        # Create directory if it doesn't exist
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        else:
            # Create a temporary file if no path provided
            output_dir = tempfile.gettempdir()
            chart_id = chart_data.get("chart_id", f"chart_{uuid.uuid4().hex[:8]}")
            output_path = os.path.join(output_dir, f"{chart_id}_{style}_vedic_chart.png")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Validate chart data
        required_fields = ["planets", "houses", "angles"]
        for field in required_fields:
            if field not in chart_data:
                raise ValueError(f"Missing required field '{field}' in chart data")

        # Generate the chart based on style
        if style == "north_indian":
            fig = _render_north_indian_chart(chart_data)
        elif style == "south_indian":
            fig = _render_south_indian_chart(chart_data)
        else:
            raise ValueError(f"Unsupported Vedic chart style: {style}")

        # Save the chart with proper quality settings
        fig.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        # Verify the file was created successfully
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Failed to create chart image at {output_path}")

        # Get file size and modification time for verification
        file_stats = os.stat(output_path)

        # Return metadata for export integration
        return {
            "file_path": output_path,
            "chart_style": style,
            "chart_type": "vedic",
            "file_size": file_stats.st_size,
            "created_at": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            "verified": True
        }

    except Exception as e:
        logger.error(f"Error generating Vedic chart: {e}")
        logger.error(traceback.format_exc())
        raise

def _render_north_indian_chart(chart_data):
    """
    Render a North Indian (square) style Vedic astrological chart.

    Args:
        chart_data: Dictionary containing chart data including planets, houses, and angles

    Returns:
        Matplotlib figure object with the rendered chart
    """
    # Create figure
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111)

    # Draw the basic square chart structure
    # Outer square
    outer_square = patches.Rectangle((0, 0), 10, 10, fill=False, linewidth=2)
    ax.add_patch(outer_square)

    # Draw the diagonal lines to create the 8 triangular houses
    plt.plot([0, 10], [0, 10], 'k-', linewidth=1.5)  # Diagonal from bottom-left to top-right
    plt.plot([0, 10], [10, 0], 'k-', linewidth=1.5)  # Diagonal from top-left to bottom-right

    # Draw the central square
    central_square = patches.Rectangle((3.5, 3.5), 3, 3, fill=False, linewidth=1.5)
    ax.add_patch(central_square)

    # Draw the house divisions
    # Horizontal lines
    plt.plot([0, 3.5], [5, 5], 'k-', linewidth=1.5)  # Left horizontal
    plt.plot([6.5, 10], [5, 5], 'k-', linewidth=1.5)  # Right horizontal

    # Vertical lines
    plt.plot([5, 5], [0, 3.5], 'k-', linewidth=1.5)  # Bottom vertical
    plt.plot([5, 5], [6.5, 10], 'k-', linewidth=1.5)  # Top vertical

    # Place planets in their respective houses
    planets = chart_data.get("planets", {})
    houses = chart_data.get("houses", {})

    # Define house positions for text placement
    house_positions = {
        1: (7.5, 7.5),  # Top right
        2: (5, 8.5),    # Top middle
        3: (2.5, 7.5),  # Top left
        4: (1.5, 5),    # Middle left
        5: (2.5, 2.5),  # Bottom left
        6: (5, 1.5),    # Bottom middle
        7: (7.5, 2.5),  # Bottom right
        8: (8.5, 5),    # Middle right
        9: (5, 5),      # Center
        10: (5, 6.5),   # Top center
        11: (6.5, 5),   # Right center
        12: (3.5, 5)    # Left center
    }

    # Place planets in houses
    for planet, data in planets.items():
        house = data.get("house", 1)
        pos = house_positions.get(house, (5, 5))

        # Add some random offset to prevent overlapping
        x_offset = random.uniform(-0.5, 0.5)
        y_offset = random.uniform(-0.5, 0.5)

        # Place planet symbol and degree
        plt.text(pos[0] + x_offset, pos[1] + y_offset,
                 f"{planet}\n{data.get('longitude', 0):.1f}°",
                 ha='center', va='center', fontsize=8)

    # Add house numbers
    for house_num, pos in house_positions.items():
        if house_num != 9:  # Skip center
            plt.text(pos[0], pos[1] + 0.8, f"H{house_num}",
                    ha='center', va='center', fontsize=9, color='blue')

    # Add ascendant and other angles
    angles = chart_data.get("angles", {})
    if "ascendant" in angles:
        asc_deg = angles["ascendant"]
        plt.text(8.5, 8.5, f"Asc: {asc_deg:.1f}°",
                ha='center', va='center', fontsize=10, color='red')

    # Set equal aspect ratio and remove axes
    ax.set_aspect('equal')
    ax.axis('off')

    # Set title
    if "birth_details" in chart_data:
        birth_details = chart_data["birth_details"]
        name = birth_details.get("name", "")
        date = birth_details.get("date", "")
        time = birth_details.get("time", "")
        title = f"North Indian Vedic Chart\n{name}\n{date} {time}"
        plt.title(title)
    else:
        plt.title("North Indian Vedic Chart")

    return fig

def _render_south_indian_chart(chart_data):
    """
    Render a South Indian style Vedic astrological chart.

    Args:
        chart_data: Dictionary containing chart data including planets, houses, and angles

    Returns:
        Matplotlib figure object with the rendered chart
    """
    # Create figure
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111)

    # Draw the basic square chart structure
    # Outer square
    outer_square = patches.Rectangle((0, 0), 12, 12, fill=False, linewidth=2)
    ax.add_patch(outer_square)

    # Draw the inner squares
    inner_square1 = patches.Rectangle((2, 2), 8, 8, fill=False, linewidth=1.5)
    ax.add_patch(inner_square1)

    inner_square2 = patches.Rectangle((4, 4), 4, 4, fill=False, linewidth=1.5)
    ax.add_patch(inner_square2)

    # Define the 12 houses in South Indian style
    houses = {
        1: (4, 8, 4, 4),    # Top middle
        2: (8, 8, 4, 4),    # Top right
        3: (8, 4, 4, 4),    # Middle right
        4: (8, 0, 4, 4),    # Bottom right
        5: (4, 0, 4, 4),    # Bottom middle
        6: (0, 0, 4, 4),    # Bottom left
        7: (0, 4, 4, 4),    # Middle left
        8: (0, 8, 4, 4),    # Top left
        9: (2, 8, 2, 2),    # Inner top left
        10: (4, 8, 2, 2),   # Inner top middle
        11: (6, 8, 2, 2),   # Inner top right
        12: (8, 8, 2, 2)    # Inner right top
    }

    # Place planets in their respective houses
    planets = chart_data.get("planets", {})

    # Define house centers for text placement
    house_centers = {
        1: (6, 10),    # Top middle
        2: (10, 10),   # Top right
        3: (10, 6),    # Middle right
        4: (10, 2),    # Bottom right
        5: (6, 2),     # Bottom middle
        6: (2, 2),     # Bottom left
        7: (2, 6),     # Middle left
        8: (2, 10),    # Top left
        9: (3, 9),     # Inner top left
        10: (5, 9),    # Inner top middle
        11: (7, 9),    # Inner top right
        12: (9, 9)     # Inner right top
    }

    # Place house numbers
    for house_num, center in house_centers.items():
        plt.text(center[0], center[1] + 0.8, f"H{house_num}",
                ha='center', va='center', fontsize=9, color='blue')

    # Place planets in houses
    for planet, data in planets.items():
        house = data.get("house", 1)
        center = house_centers.get(house, (6, 6))

        # Add some random offset to prevent overlapping
        x_offset = random.uniform(-0.5, 0.5)
        y_offset = random.uniform(-0.5, 0.5)

        # Place planet symbol and degree
        plt.text(center[0] + x_offset, center[1] + y_offset,
                 f"{planet}\n{data.get('longitude', 0):.1f}°",
                 ha='center', va='center', fontsize=8)

    # Add ascendant and other angles
    angles = chart_data.get("angles", {})
    if "ascendant" in angles:
        asc_deg = angles["ascendant"]
        asc_house = 1  # Ascendant is always in the 1st house in Vedic astrology
        center = house_centers.get(asc_house, (6, 10))
        plt.text(center[0], center[1] - 0.8, f"Asc: {asc_deg:.1f}°",
                ha='center', va='center', fontsize=10, color='red')

    # Set equal aspect ratio and remove axes
    ax.set_aspect('equal')
    ax.axis('off')

    # Set title
    if "birth_details" in chart_data:
        birth_details = chart_data["birth_details"]
        name = birth_details.get("name", "")
        date = birth_details.get("date", "")
        time = birth_details.get("time", "")
        title = f"South Indian Vedic Chart\n{name}\n{date} {time}"
        plt.title(title)
    else:
        plt.title("South Indian Vedic Chart")

    return fig


def generate_comparison_chart(
    original_chart: Dict[str, Any],
    rectified_chart: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Generate a comparison visualization between original and rectified charts.

    Args:
        original_chart: Original chart data
        rectified_chart: Rectified chart data (optional)
        output_path: Path to save the generated image (optional)

    Returns:
        Path to the generated comparison chart image
    """
    try:
        # Set up the figure
        fig = plt.figure(figsize=(15, 10))

        if rectified_chart is None:
            # If no rectified chart, just display the original
            ax = fig.add_subplot(111)
            _render_comparison_chart(ax, original_chart, "Original Chart")
            title = "Birth Chart Visualization"
        else:
            # Set up for comparison
            gs = GridSpec(1, 2, figure=fig)

            # Original chart on the left
            ax1 = fig.add_subplot(gs[0, 0])
            _render_comparison_chart(ax1, original_chart, "Original Chart")

            # Rectified chart on the right
            ax2 = fig.add_subplot(gs[0, 1])
            _render_comparison_chart(ax2, rectified_chart, "Rectified Chart")

            # Add differences in chart properties
            differences = _extract_key_differences(original_chart, rectified_chart)

            # Add time difference
            time_diff = 0
            if "birth_details" in original_chart and original_chart["birth_details"] and \
               "birth_details" in rectified_chart and rectified_chart["birth_details"]:
                orig_time = original_chart["birth_details"].get("time", "")
                rect_time = rectified_chart["birth_details"].get("time", "")
                if orig_time and rect_time:
                    time_diff = _calculate_time_difference(orig_time, rect_time)

            # Set title based on comparison
            title = f"Chart Comparison (Time Difference: {abs(time_diff)} minutes)"

        # Set the figure title
        fig.suptitle(title, fontsize=16, weight='bold')

        # Create output path if not provided
        if not output_path:
            # Create a temporary file with unique name
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                output_path = tmp.name

        # Save the figure
        plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust for title
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_path

    except Exception as e:
        logger.error(f"Error generating comparison chart: {e}")
        logger.error(traceback.format_exc())

        # Return a default/error image path if something goes wrong
        error_img_path = os.path.join(tempfile.gettempdir(), f"chart_error_{uuid.uuid4()}.png")

        # Create a simple error chart
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, f"Error generating chart:\n{str(e)}",
                ha='center', va='center', fontsize=12)
        ax.axis('off')
        plt.savefig(error_img_path)
        plt.close(fig)

        return error_img_path


def _render_comparison_chart(ax: Axes, chart_data: Dict[str, Any], chart_type: str = "Chart") -> None:
    """
    Render a chart on the provided axes.

    Args:
        ax: Matplotlib axes to render on
        chart_data: Chart data dictionary
        chart_type: Type of chart (for title)
    """
    # Set background color based on chart type
    if chart_type.lower() == "original":
        bg_color = '#f9f9f9'  # Light gray for original
    else:
        bg_color = '#f0f8ff'  # Light blue for rectified

    ax.set_facecolor(bg_color)

    # Draw the main square
    ax.add_patch(patches.Rectangle((0, 0), 10, 10, fill=False, linewidth=2, edgecolor='#444444'))

    # Draw the inner square (for the center)
    ax.add_patch(patches.Rectangle((3, 3), 4, 4, fill=False, linewidth=2, edgecolor='#444444'))

    # Draw the diagonal lines
    ax.plot([0, 10], [0, 10], 'k-', linewidth=1.5, color='#444444')
    ax.plot([0, 10], [10, 0], 'k-', linewidth=1.5, color='#444444')

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

    # Define rashi (sign) colors
    rashi_colors = {
        "Aries": "#FFE5E5",      # Light Red
        "Taurus": "#E5FFE5",     # Light Green
        "Gemini": "#E5E5FF",     # Light Blue
        "Cancer": "#FFFFE5",     # Light Yellow
        "Leo": "#FFE5D9",        # Light Orange
        "Virgo": "#F2E5FF",      # Light Purple
        "Libra": "#E5FFF2",      # Light Teal
        "Scorpio": "#FFE5FF",    # Light Pink
        "Sagittarius": "#E5F2FF", # Light Sky Blue
        "Capricorn": "#F2F2F2",  # Light Gray
        "Aquarius": "#E5FFFF",   # Light Cyan
        "Pisces": "#FFF2E5"      # Light Peach
    }

    # Add house signs with background colors
    for i, pos in enumerate(house_positions):
        house_num = i + 1
        x, y = pos

        # Get the sign for this house
        sign = "Unknown"
        if isinstance(houses, list) and i < len(houses):
            if isinstance(houses[i], dict):
                sign = houses[i].get("sign", "Unknown")
            elif "houses" in chart_data and isinstance(chart_data["houses"], dict):
                sign = chart_data["houses"].get(str(house_num), {}).get("sign", "Unknown")

        # Add house rectangle with sign-based color
        rect_x, rect_y = x - 1, y - 1
        rect = patches.Rectangle((rect_x, rect_y), 2, 2, fill=True, alpha=0.15, linewidth=0,
                                facecolor=rashi_colors.get(sign, '#FFFFFF'))
        ax.add_patch(rect)

        # Add house number and sign
        ax.text(x, y + 0.5, f"{house_num}", fontsize=14, ha='center', fontweight='bold', color='#333333')
        ax.text(x, y, f"{sign}", fontsize=11, ha='center', color='#555555')

        # Add zodiac symbol
        symbol = ZODIAC_SYMBOLS.get(sign, "")
        if symbol:
            ax.text(x, y - 0.3, symbol, fontsize=14, ha='center', color='#333333')

        # Find planets in this house
        planets_in_house = []
        for planet_name, planet_data in planets.items():
            planet_house = None
            if isinstance(planet_data, dict):
                planet_house = planet_data.get("house")
            elif hasattr(planet_data, "get"):
                planet_house = planet_data.get("house")

            if planet_house == house_num or planet_house == str(house_num):
                planets_in_house.append(planet_name)

        # Plot planets in this house
        if planets_in_house:
            # Calculate positions for planets
            planet_count = len(planets_in_house)
            planet_spacing = 0.25
            start_y = y - 0.7

            # If many planets, adjust spacing
            if planet_count > 4:
                planet_spacing = 0.2
                start_y = y - 0.6

            for p_idx, planet_name in enumerate(planets_in_house):
                # Stagger planets if many in same house
                planet_x = x + (p_idx % 2) * 0.3 - 0.15
                planet_y = start_y - (p_idx // 2) * planet_spacing

                # Draw planet symbol
                symbol = PLANET_SYMBOLS.get(planet_name, planet_name[:3])
                color = PLANET_COLORS.get(planet_name, "#000000")

                # For rectified chart, make planets appear more prominent
                if chart_type.lower() == "rectified":
                    # Draw a small circle behind the symbol with more emphasis
                    circle = patches.Circle((planet_x, planet_y), radius=0.14,
                                          facecolor='white', edgecolor=color,
                                          alpha=0.8, zorder=2, linewidth=1.5)
                else:
                    # Normal styling for original chart
                    circle = patches.Circle((planet_x, planet_y), radius=0.12,
                                          facecolor='white', edgecolor=color,
                                          alpha=0.7, zorder=2)
                ax.add_patch(circle)

                # Add the planet symbol
                ax.text(planet_x, planet_y, symbol, fontsize=10, ha='center', va='center',
                       color=color, weight='bold', zorder=3)

    # Set axis limits and turn off axis
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-0.5, 10.5)
    ax.axis('off')

def _extract_key_differences(original_chart: Dict[str, Any], rectified_chart: Dict[str, Any]) -> List[str]:
    """
    Extract key differences between original and rectified charts.

    Args:
        original_chart: Original chart data
        rectified_chart: Rectified chart data

    Returns:
        List of difference descriptions
    """
    differences = []

    # Check ascendant changes
    original_asc = original_chart.get("ascendant", {})
    rectified_asc = rectified_chart.get("ascendant", {})

    if isinstance(original_asc, dict) and isinstance(rectified_asc, dict):
        original_asc_sign = original_asc.get("sign", "")
        rectified_asc_sign = rectified_asc.get("sign", "")

        if original_asc_sign != rectified_asc_sign:
            differences.append(f"Ascendant changed from {original_asc_sign} to {rectified_asc_sign}")
        else:
            original_asc_degree = original_asc.get("degree", 0)
            rectified_asc_degree = rectified_asc.get("degree", 0)
            degree_diff = abs(original_asc_degree - rectified_asc_degree)
            if degree_diff > 0.5:  # Only note significant degree changes
                differences.append(f"Ascendant moved from {original_asc_degree:.2f}° to {rectified_asc_degree:.2f}° in {original_asc_sign}")

    # Check planet house changes
    original_planets = original_chart.get("planets", {})
    rectified_planets = rectified_chart.get("planets", {})

    for planet_name in set(original_planets.keys()) & set(rectified_planets.keys()):
        original_planet = original_planets.get(planet_name, {})
        rectified_planet = rectified_planets.get(planet_name, {})

        if isinstance(original_planet, dict) and isinstance(rectified_planet, dict):
            # Check house changes
            original_house = original_planet.get("house", "")
            rectified_house = rectified_planet.get("house", "")

            if original_house != rectified_house:
                differences.append(f"{planet_name} moved from house {original_house} to house {rectified_house}")

            # Check sign changes
            original_sign = original_planet.get("sign", "")
            rectified_sign = rectified_planet.get("sign", "")

            if original_sign != rectified_sign:
                differences.append(f"{planet_name} moved from {original_sign} to {rectified_sign}")

            # Check retrograde status changes
            original_retro = original_planet.get("retrograde", False)
            rectified_retro = rectified_planet.get("retrograde", False)

            if original_retro != rectified_retro:
                if rectified_retro:
                    differences.append(f"{planet_name} became retrograde")
                else:
                    differences.append(f"{planet_name} is no longer retrograde")

    # Check for major aspect changes (if available)
    original_aspects = original_chart.get("aspects", [])
    rectified_aspects = rectified_chart.get("aspects", [])

    if original_aspects and rectified_aspects:
        # Count the number of major aspects that have changed
        original_aspect_pairs = set()
        for aspect in original_aspects:
            if isinstance(aspect, dict):
                planet1 = aspect.get("planet1", "")
                planet2 = aspect.get("planet2", "")
                aspect_type = aspect.get("type", "")
                if planet1 and planet2 and aspect_type:
                    # Normalize to ensure consistent ordering
                    planets = sorted([planet1, planet2])
                    original_aspect_pairs.add((planets[0], planets[1], aspect_type))

        rectified_aspect_pairs = set()
        for aspect in rectified_aspects:
            if isinstance(aspect, dict):
                planet1 = aspect.get("planet1", "")
                planet2 = aspect.get("planet2", "")
                aspect_type = aspect.get("type", "")
                if planet1 and planet2 and aspect_type:
                    # Normalize to ensure consistent ordering
                    planets = sorted([planet1, planet2])
                    rectified_aspect_pairs.add((planets[0], planets[1], aspect_type))

        # Find aspects in rectified that weren't in original
        new_aspects = rectified_aspect_pairs - original_aspect_pairs
        lost_aspects = original_aspect_pairs - rectified_aspect_pairs

        if new_aspects:
            for planet1, planet2, aspect_type in list(new_aspects)[:3]:  # Limit to 3 to avoid overwhelming
                differences.append(f"New {aspect_type} aspect between {planet1} and {planet2}")

        if lost_aspects:
            for planet1, planet2, aspect_type in list(lost_aspects)[:3]:  # Limit to 3 to avoid overwhelming
                differences.append(f"Lost {aspect_type} aspect between {planet1} and {planet2}")

    return differences

def _calculate_time_difference(time1: str, time2: str) -> int:
    """
    Calculate the difference between two time strings in minutes.

    Args:
        time1: First time string (HH:MM or HH:MM:SS format)
        time2: Second time string (HH:MM or HH:MM:SS format)

    Returns:
        Difference in minutes (time2 - time1)
    """
    try:
        # Extract hours and minutes from strings
        if not time1 or not time2:
            return 0

        # Parse first time
        t1_parts = time1.split(":")
        hours1 = int(t1_parts[0])
        minutes1 = int(t1_parts[1])
        total_minutes1 = hours1 * 60 + minutes1

        # Parse second time
        t2_parts = time2.split(":")
        hours2 = int(t2_parts[0])
        minutes2 = int(t2_parts[1])
        total_minutes2 = hours2 * 60 + minutes2

        # Calculate difference
        return total_minutes2 - total_minutes1
    except (ValueError, IndexError) as e:
        logger.warning(f"Error calculating time difference: {e}")
        return 0

def generate_3d_chart(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate a 3D visualization of an astrological chart.

    Args:
        chart_data: Dictionary containing chart data
        output_path: Optional path to save the chart image

    Returns:
        Base64 encoded image data or path to saved image
    """
    try:
        # Set up a robust matplotlib 3D environment
        plt.close('all')  # Close any existing figures to avoid memory issues

        # Create a new figure and 3D axes
        fig = plt.figure(figsize=(12, 10), dpi=100)
        # Use projection='3d' for proper 3D plotting
        ax = fig.add_subplot(111, projection='3d')

        # Get birth data for labels
        birth_data = chart_data.get("birth_details", {})
        if not birth_data and "date" in chart_data:
            # Try to extract from top level
            birth_data = {
                "date": chart_data.get("date", ""),
                "time": chart_data.get("time", ""),
                "location": chart_data.get("location", "")
            }

        # Calculate celestial sphere parameters
        sphere_radius = 10

        # Draw transparent celestial sphere
        u, v = np.mgrid[0:2*np.pi:50j, 0:np.pi:30j]
        x = sphere_radius * np.cos(u) * np.sin(v)
        y = sphere_radius * np.sin(u) * np.sin(v)
        z = sphere_radius * np.cos(v)

        # Create semi-transparent celestial sphere (blue for aesthetic appeal)
        # Use cast to Axes3D to help type checking understand we're using 3D axes
        ax_3d = cast(Axes3D, ax)
        ax_3d.plot_surface(x, y, z, color='skyblue', alpha=0.1, linewidth=0)

        # Draw ecliptic plane - this is the plane of Earth's orbit around the Sun
        # Create a disk representing the ecliptic plane
        r = np.linspace(0, sphere_radius, 100)
        theta = np.linspace(0, 2*np.pi, 100)
        r_grid, theta_grid = np.meshgrid(r, theta)

        x_ecliptic = r_grid * np.cos(theta_grid)
        y_ecliptic = r_grid * np.sin(theta_grid)
        z_ecliptic = np.zeros_like(x_ecliptic)

        # Add the ecliptic plane semi-transparent
        ax_3d.plot_surface(x_ecliptic, y_ecliptic, z_ecliptic, color='gold', alpha=0.2)

        # Add zodiac signs markers on the ecliptic plane
        sign_colors = {
            'Aries': 'firebrick', 'Taurus': 'darkgreen', 'Gemini': 'goldenrod',
            'Cancer': 'silver', 'Leo': 'orangered', 'Virgo': 'darkkhaki',
            'Libra': 'mediumpurple', 'Scorpio': 'darkred', 'Sagittarius': 'chocolate',
            'Capricorn': 'dimgray', 'Aquarius': 'steelblue', 'Pisces': 'mediumaquamarine'
        }

        # Draw zodiac sign names on the ecliptic rim
        for i, sign in enumerate(['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
                             'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']):
            angle = i * 30 * np.pi / 180
            sign_x = (sphere_radius + 0.5) * np.cos(angle)
            sign_y = (sphere_radius + 0.5) * np.sin(angle)

            # Add a colored dot at each sign's position
            ax.scatter(sign_x, sign_y, 0, color=sign_colors.get(sign, 'black'), marker='o', alpha=0.7, s=50)

            # Add text label with proper parameter ordering
            # Third parameter should be the text content
            ax.text(sign_x * 1.05, sign_y * 1.05, sign,
                    fontsize=8, ha='center', va='center',
                    color=sign_colors.get(sign, 'black'))

        # Draw house divisions on the ecliptic plane
        houses = chart_data.get("houses", [])

        # If houses are provided, draw house boundaries
        if houses and len(houses) > 0:
            # Draw house boundaries as lines from the center to the rim
            for i, house in enumerate(houses):
                # Extract house longitude (either from dict or direct value)
                if isinstance(house, dict):
                    # If houses are dictionaries with detailed information
                    house_longitude = house.get("longitude", i * 30)
                else:
                    # If houses are just longitudes
                    house_longitude = house

                angle = house_longitude * np.pi / 180

                # Draw a line from center to the rim
                ax.plot([0, sphere_radius * np.cos(angle)],
                        [0, sphere_radius * np.sin(angle)],
                        [0, 0], color='gray', linestyle='--', alpha=0.5)

                # Add house number midway
                midpoint_x = 0.7 * sphere_radius * np.cos(angle)
                midpoint_y = 0.7 * sphere_radius * np.sin(angle)
                # Use str(i+1) as the text content (third parameter)
                ax.text(midpoint_x, midpoint_y, str(i+1),
                        fontsize=7, ha='center', va='center',
                        color='white', bbox=dict(facecolor='gray', alpha=0.5, boxstyle='round,pad=0.1'))

        # Define planet markers and colors
        planet_symbols = {
            "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
            "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇",
            "NNode": "☊", "SNode": "☋", "Chiron": "⚷", "Ceres": "⚳"
        }

        planet_colors = {
            "Sun": "gold", "Moon": "silver", "Mercury": "darkorange", "Venus": "green",
            "Mars": "red", "Jupiter": "purple", "Saturn": "dimgray", "Uranus": "darkturquoise",
            "Neptune": "blue", "Pluto": "indigo", "NNode": "darkgreen", "SNode": "darkred",
            "Chiron": "magenta", "Ceres": "darkkhaki"
        }

        # Plot each planet as a sphere at its 3D position
        planet_legend_entries = []
        planet_positions = {}

        # Get the planets data from chart_data
        planets = chart_data.get("planets", {})

        for planet_name, planet_data in planets.items():
            # Get planet data
            sign = planet_data.get("sign", "")
            sign_num = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                       "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"].index(sign) if sign else 0

            # Get planet longitude and calculate position on ecliptic
            longitude = planet_data.get("longitude", 0)

            # Convert longitude to radians
            angle = longitude * np.pi / 180

            # Basic position on the ecliptic plane
            x = sphere_radius * 0.85 * np.cos(angle)
            y = sphere_radius * 0.85 * np.sin(angle)
            z = 0

            # Store for connecting aspects later
            planet_positions[planet_name] = (x, y, z)

            # Calculate size based on planet's importance
            planet_importance = {
                "Sun": 120, "Moon": 100, "Mercury": 60, "Venus": 80,
                "Mars": 70, "Jupiter": 90, "Saturn": 85, "Uranus": 60,
                "Neptune": 60, "Pluto": 50, "NNode": 45, "SNode": 45,
                "Chiron": 40, "Ceres": 40
            }
            planet_size = planet_importance.get(planet_name, 50)

            # Get planet color
            color = planet_colors.get(planet_name, "blue")

            # Draw the planet as a 3D sphere with alpha transparency
            planet_sphere = ax.scatter(x, y, z, color=color, s=planet_size, marker='o', alpha=0.8,
                                    edgecolors='white', linewidths=1)

            # Add label with planet name
            ax.text(x, y, z + 0.5, str(planet_name), fontsize=8, ha='center', va='center',
                   color=color, fontweight='bold')

        # Connect planets with aspects
        aspects = chart_data.get("aspects", [])

        # Define aspect colors and styles
        aspect_colors = {
            "conjunction": "gold",
            "opposition": "red",
            "trine": "green",
            "square": "firebrick",
            "sextile": "blue",
            "quincunx": "purple",
            "semisextile": "darkturquoise",
            "semisquare": "orangered",
            "sesquiquadrate": "darkred"
        }

        aspect_styles = {
            "conjunction": "-",
            "opposition": "--",
            "trine": "-",
            "square": "--",
            "sextile": "-",
            "quincunx": ":",
            "semisextile": ":",
            "semisquare": ":",
            "sesquiquadrate": ":"
        }

        aspect_widths = {
            "conjunction": 2.0,
            "opposition": 1.5,
            "trine": 1.5,
            "square": 1.5,
            "sextile": 1.0,
            "quincunx": 0.8,
            "semisextile": 0.8,
            "semisquare": 0.8,
            "sesquiquadrate": 0.8
        }

        # Only draw the major aspects to avoid clutter
        major_aspects = ["conjunction", "opposition", "trine", "square", "sextile"]

        for aspect in aspects:
            aspect_type = aspect.get("aspect_type", "")
            if aspect_type not in major_aspects:
                continue

            planet1 = aspect.get("planet1", "")
            planet2 = aspect.get("planet2", "")

            # Only draw if we have both planets
            if planet1 in planet_positions and planet2 in planet_positions:
                p1_pos = planet_positions[planet1]
                p2_pos = planet_positions[planet2]

                # Get aspect properties
                color = aspect_colors.get(aspect_type, "gray")
                style = aspect_styles.get(aspect_type, "-")
                width = aspect_widths.get(aspect_type, 1.0)

                # Draw the aspect line with alpha transparency proportional to orb precision
                orb = aspect.get("orb", 5)
                alpha = max(0.3, 1 - (orb / 10))  # Higher alpha for tighter orbs

                # Draw arc connecting planets
                ax.plot([p1_pos[0], p2_pos[0]], [p1_pos[1], p2_pos[1]], [p1_pos[2], p2_pos[2]],
                       color=color, linestyle=style, linewidth=width, alpha=alpha)

                # Calculate midpoint for aspect label
                mid_x = (p1_pos[0] + p2_pos[0]) / 2
                mid_y = (p1_pos[1] + p2_pos[1]) / 2
                mid_z = (p1_pos[2] + p2_pos[2]) / 2

                # Add small aspect symbol at midpoint
                aspect_symbols = {
                    "conjunction": "☌", "opposition": "☍", "trine": "△",
                    "square": "□", "sextile": "⚹"
                }
                symbol = aspect_symbols.get(aspect_type, "")
                if symbol:
                    ax.text(mid_x, mid_y, mid_z, symbol, fontsize=10, ha='center', va='center',
                           color=color, alpha=alpha, fontweight='bold')

        # Set equal aspect ratio for the 3D plot
        ax.set_box_aspect([1, 1, 0.4])  # Slightly flatten in z axis for better viewing

        # Set tight layout and remove axis
        plt.tight_layout()
        ax.set_axis_off()

        # Set viewing angle to look at ecliptic plane at a slight angle
        # Cast to Axes3D for 3D-specific methods
        ax_3d = cast(Axes3D, ax)
        ax_3d.view_init(elev=20, azim=30)  # Elevation 20 degrees, Azimuth 30 degrees

        # Chart title
        birth_date = birth_data.get("date", chart_data.get("date", ""))
        birth_time = birth_data.get("time", birth_data.get("birth_time", ""))
        location = birth_data.get("location", chart_data.get("location", ""))

        # Get chart type from chart data
        chart_type = chart_data.get("chart_type", "Tropical")

        title = f"3D {chart_type} Chart"
        if birth_date:
            title += f" - {birth_date}"
            if birth_time:
                title += f" {birth_time}"
        if location:
            title += f" - {location}"

        plt.title(title, fontsize=14, y=0.95)

        # Add legend for planet colors at the bottom of the figure
        legend_handles = []
        legend_labels = []

        # Create legend entries for major planets
        for planet, color in planet_legend_entries:
            if planet in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
                legend_handles.append(Line2D([0], [0], marker='o', color='w', markerfacecolor=color,
                                               markersize=8, markeredgecolor='white', markeredgewidth=0.5))
                legend_labels.append(planet)

        # Add the legend outside the main plot area
        if legend_handles:
            legend = ax.legend(legend_handles, legend_labels, loc='upper center',
                          bbox_to_anchor=(0.5, -0.05), ncol=5, fancybox=True, shadow=True)

        # Add aspect legend
        aspect_legend_handles = []
        aspect_legend_labels = []

        for aspect_type in major_aspects:
            color = aspect_colors.get(aspect_type, "gray")
            style = aspect_styles.get(aspect_type, "-")
            width = aspect_widths.get(aspect_type, 1.0)

            aspect_legend_handles.append(Line2D([0], [0], color=color, linestyle=style, linewidth=width))
            aspect_legend_labels.append(aspect_type.capitalize())

        # Add second legend for aspects below the first legend
        if aspect_legend_handles:
            aspect_legend = fig.legend(aspect_legend_handles, aspect_legend_labels,
                                     loc='lower center', bbox_to_anchor=(0.5, 0.02),
                                     ncol=5, fancybox=True, shadow=True)

        # Save figure if output path is provided
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close(fig)
            return output_path
        else:
            # Convert to base64 string if no output path
            from io import BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            import base64
            data_uri = base64.b64encode(buf.read()).decode('ascii')
            return f"data:image/png;base64,{data_uri}"

    except Exception as e:
        logger.error(f"Error generating 3D chart: {e}")
        logger.error(traceback.format_exc())

        # Create a basic error image
        try:
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.text(0.5, 0.5, f"Error generating 3D chart:\n{str(e)}",
                   ha='center', va='center', fontsize=12)
            ax.axis('off')

            if output_path:
                plt.savefig(output_path, dpi=100)
                plt.close(fig)
                return output_path
            else:
                # Return a base64 encoded error image
                from io import BytesIO
                buf = BytesIO()
                plt.savefig(buf, format='png')
                plt.close(fig)
                buf.seek(0)
                import base64
                data_uri = base64.b64encode(buf.read()).decode('ascii')
                return f"data:image/png;base64,{data_uri}"
        except Exception:
            # If all else fails, return empty string
            if output_path:
                return output_path
            return ""

def _render_3d_chart_in_subplot(ax: Any, chart_data: Dict[str, Any], title: Optional[str] = None) -> None:
    """
    Render a 3D astrological chart in a matplotlib subplot.

    Args:
        ax: Matplotlib 3D axis
        chart_data: Dictionary containing chart data
        title: Optional title for the subplot
    """
    import numpy as np

    # Set title if provided
    if title:
        ax.set_title(title)

    # Create celestial sphere
    u = np.linspace(0, 2 * np.pi, 100)
    v = np.linspace(0, np.pi, 100)

    radius = 10
    x = radius * np.outer(np.cos(u), np.sin(v))
    y = radius * np.outer(np.sin(u), np.sin(v))
    z = radius * np.outer(np.ones(np.size(u)), np.cos(v))

    # Draw celestial sphere with slight transparency
    ax.plot_surface(x, y, z, color='skyblue', alpha=0.2)

    # Draw zodiac belt
    zodiac_belt_radius = radius * 1.05
    belt_width = 3  # Width of the zodiac belt in degrees

    # Generate zodiac belt
    for i in range(12):
        start_angle = i * 30  # 30 degrees per sign
        mid_angle_rad = np.radians(start_angle + 15)

        # Draw sign marker
        zodiac_signs = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]
        sign_x = zodiac_belt_radius * 1.1 * np.cos(mid_angle_rad)
        sign_y = zodiac_belt_radius * 1.1 * np.sin(mid_angle_rad)
        sign_z = 0

        ax.text(sign_x, sign_y, sign_z, zodiac_signs[i], fontsize=12, ha='center', va='center')

        # Draw degree markers at 10-degree intervals
        for degree in range(0, 30, 10):
            angle_rad = np.radians(start_angle + degree)
            marker_x = zodiac_belt_radius * np.cos(angle_rad)
            marker_y = zodiac_belt_radius * np.sin(angle_rad)
            ax.scatter(marker_x, marker_y, 0, s=15, color='gray', alpha=0.7)

    # Plot planets
    planets_data = chart_data.get("planets", {})

    # Color mapping for planets
    planet_colors = {
        "Sun": "gold",
        "Moon": "silver",
        "Mercury": "slategray",
        "Venus": "forestgreen",
        "Mars": "firebrick",
        "Jupiter": "orange",
        "Saturn": "darkslategray",
        "Uranus": "skyblue",
        "Neptune": "royalblue",
        "Pluto": "purple",
        "North Node": "darkgreen",
        "South Node": "darkred",
        "Chiron": "magenta"
    }

    planet_markers = {}

    # Plot each planet
    for planet_name, planet_data in planets_data.items():
        if isinstance(planet_data, dict):
            # Get longitude and convert to radians
            longitude = planet_data.get("longitude", 0)
            longitude_rad = np.radians(longitude)

            # Calculate 3D position - planets are at the sphere equator (z=0)
            planet_x = radius * np.cos(longitude_rad)
            planet_y = radius * np.sin(longitude_rad)
            planet_z = 0

            # Adjust z slightly for visual clarity - place planets at different depths
            # based on their traditional orbital distances
            z_offset = {
                "Moon": -0.5,
                "Mercury": -0.3,
                "Venus": -0.2,
                "Sun": 0,
                "Mars": 0.2,
                "Jupiter": 0.4,
                "Saturn": 0.6,
                "Uranus": 0.8,
                "Neptune": 1.0,
                "Pluto": 1.2,
                "North Node": -0.7,
                "South Node": -0.7,
                "Chiron": 0.3
            }.get(planet_name, 0)

            planet_z += z_offset

            # Get planet color
            color = planet_colors.get(planet_name, "blue")

            # Plot planet
            marker = ax.scatter(planet_x, planet_y, planet_z, color=color, s=100,
                            label=planet_name, alpha=0.8, edgecolors='white')
            planet_markers[planet_name] = (planet_x, planet_y, planet_z)

            # Add planet symbol or abbreviated name
            planet_symbols = {
                "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", "Mars": "♂",
                "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", "Neptune": "♆", "Pluto": "♇",
                "North Node": "☊", "South Node": "☋", "Chiron": "⚷"
            }

            symbol = planet_symbols.get(planet_name, planet_name[:2])
            ax.text(planet_x * 1.1, planet_y * 1.1, planet_z, symbol, color=color,
                   fontsize=10, ha='center', va='center', fontweight='bold')

    # Plot major aspects if available
    aspects_data = chart_data.get("aspects", [])

    # Plot only major aspects to avoid cluttering
    major_aspects = ["conjunction", "opposition", "trine", "square", "sextile"]
    aspect_colors = {
        "conjunction": "purple",
        "opposition": "red",
        "trine": "green",
        "square": "orange",
        "sextile": "blue"
    }

    for aspect in aspects_data:
        if isinstance(aspect, dict):
            aspect_type = aspect.get("type", "").lower()
            planet1 = aspect.get("planet1", "")
            planet2 = aspect.get("planet2", "")

            if (aspect_type in major_aspects and
                planet1 in planet_markers and
                planet2 in planet_markers):

                p1 = planet_markers[planet1]
                p2 = planet_markers[planet2]

                # Draw line between planets
                line_color = aspect_colors.get(aspect_type, "gray")
                ax.plot([p1[0], p2[0]], [p1[1], p2[1]], [p1[2], p2[2]],
                       color=line_color, linewidth=1, alpha=0.6, linestyle=':')

    # Set equal aspect ratio and remove axes ticks
    ax.set_box_aspect([1, 1, 1])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_zticks([])
    ax.set_xlim(-radius * 1.2, radius * 1.2)
    ax.set_ylim(-radius * 1.2, radius * 1.2)
    ax.set_zlim(-radius * 1.2, radius * 1.2)

    # Add subtle grid
    ax.grid(True, alpha=0.1)

    # Add ascendant marker
    ascendant = chart_data.get("angles", {}).get("ascendant", {})
    if ascendant:
        asc_longitude = ascendant.get("longitude", 0)
        asc_longitude_rad = np.radians(asc_longitude)

        asc_x = radius * np.cos(asc_longitude_rad)
        asc_y = radius * np.sin(asc_longitude_rad)

        # Draw a larger marker for the ascendant
        ax.scatter(asc_x, asc_y, 0, color='red', s=150, marker='*', alpha=0.8)
        ax.text(asc_x * 1.15, asc_y * 1.15, 0, "ASC", color='red', fontsize=10, fontweight='bold')

    # Add midheaven marker
    midheaven = chart_data.get("angles", {}).get("midheaven", {})
    if midheaven:
        mc_longitude = midheaven.get("longitude", 0)
        mc_longitude_rad = np.radians(mc_longitude)

        mc_x = radius * np.cos(mc_longitude_rad)
        mc_y = radius * np.sin(mc_longitude_rad)

        # Draw a larger marker for the midheaven
        ax.scatter(mc_x, mc_y, 0, color='blue', s=150, marker='*', alpha=0.8)
        ax.text(mc_x * 1.15, mc_y * 1.15, 0, "MC", color='blue', fontsize=10, fontweight='bold')

def generate_planet_table(chart_data: Dict[str, Any], output_path: str) -> str:
    """
    Generate a table image showing planetary positions.

    Args:
        chart_data: Chart data dictionary
        output_path: Path to save the table image

    Returns:
        Path to the generated image file
    """
    try:
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.axis('off')

        # Add title
        ax.text(0.5, 0.95, "Planetary Positions",
                ha='center', fontsize=14, fontweight='bold')

        # Extract planet data
        planets = chart_data.get("planets", {})

        # Create table data
        table_data = [["Planet", "Sign", "Degree", "House", "Retrograde"]]

        # Add planet rows
        for planet_name, planet_data in planets.items():
            if isinstance(planet_data, dict):
                sign = planet_data.get("sign", "")
                degree = f"{planet_data.get('degree', 0):.2f}°"
                house = str(planet_data.get("house", ""))
                retrograde = "Yes" if planet_data.get("retrograde", False) else "No"

                table_data.append([planet_name, sign, degree, house, retrograde])

        # Create the table
        table = ax.table(
            cellText=table_data,
            loc='center',
            cellLoc='center',
            colWidths=[0.2, 0.2, 0.2, 0.2, 0.2]
        )

        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.5)

        # Style header
        for i in range(len(table_data[0])):
            table[(0, i)].set_facecolor('#e6e6e6')
            table[(0, i)].set_text_props(fontweight='bold')

        # Save the image
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_path
    except Exception as e:
        logger.error(f"Error generating planet table: {e}")
        logger.error(traceback.format_exc())


        return output_path

def generate_3d_comparison(chart1: Dict[str, Any], chart2: Dict[str, Any], output_path: str) -> str:
    """
    Generate a 3D visualization comparing two charts.

    Args:
        chart1: First chart data dictionary
        chart2: Second chart data dictionary
        output_path: Path to save the comparison image

    Returns:
        Path to the generated image file
    """
    try:
        # Create figure and 3D axis
        fig = plt.figure(figsize=(12, 8))

        # Add two 3D subplots side by side
        ax1 = fig.add_subplot(121, projection='3d')
        ax2 = fig.add_subplot(122, projection='3d')

        # Get chart names or IDs
        chart1_name = chart1.get("birth_data", {}).get("name", "Chart 1")
        chart2_name = chart2.get("birth_data", {}).get("name", "Chart 2")

        # Set titles
        ax1.set_title(chart1_name)
        ax2.set_title(chart2_name)

        # Render each chart in 3D
        _render_3d_chart_in_subplot(ax1, chart1)
        _render_3d_chart_in_subplot(ax2, chart2)

        # Add main title
        plt.suptitle("Chart Comparison", fontsize=16)

        # Add a text explanation of significant differences
        # Calculate changes between charts
        differences = []

        # Compare ascendants
        asc1 = chart1.get("angles", {}).get("ascendant", {}).get("longitude", 0)
        asc2 = chart2.get("angles", {}).get("ascendant", {}).get("longitude", 0)
        asc_diff = _calculate_arc_difference(asc1, asc2)
        if asc_diff > 0.5:
            differences.append(f"Ascendant shift: {asc_diff:.2f}°")

        # Compare planets
        planet_diffs = []
        planets1 = chart1.get("planets", {})
        planets2 = chart2.get("planets", {})

        for name in set(planets1.keys()).intersection(planets2.keys()):
            if isinstance(planets1[name], dict) and isinstance(planets2[name], dict):
                p1_lon = planets1[name].get("longitude", 0)
                p2_lon = planets2[name].get("longitude", 0)
                diff = _calculate_arc_difference(p1_lon, p2_lon)

                if diff > 0.5:
                    planet_diffs.append(f"{name}: {diff:.2f}°")

        if planet_diffs:
            differences.extend(planet_diffs[:5])  # Show top 5 differences

        # Add text box with differences
        if differences:
            # Add text annotation for significant differences
            fig.text(0.5, 0.02, "\n".join(["Key Differences:"] + differences),
                    ha='center', va='bottom', fontsize=9,
                    bbox=dict(boxstyle="round,pad=0.5", fc="lightyellow", ec="orange", alpha=0.8))

        # Save the comparison
        plt.tight_layout(rect=(0, 0.05, 1, 0.95))  # Adjust for suptitle and bottom text
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)

        return output_path
    except Exception as e:
        logger.error(f"Error generating 3D comparison: {e}")
        logger.error(traceback.format_exc())

        return output_path

def save_chart_as_pdf_report(
    chart_data: Dict[str, Any],
    output_path: str,
    title: Optional[str] = None,
    include_aspects: bool = True,
    include_report: bool = True,
    width: int = 11,
    height: float = 8.0
) -> str:
    """
    Save chart as a PDF report.

    Args:
        chart_data: Chart data dictionary
        output_path: Path to save the PDF
        title: Optional title for the PDF
        include_aspects: Include aspect analysis
        include_report: Include detailed report
        width: PDF width in inches
        height: PDF height in inches

    Returns:
        Path to the generated PDF file

    Raises:
        ValueError: If chart data is invalid or empty
        RuntimeError: If PDF generation fails for any reason
    """
    if not chart_data:
        raise ValueError("No chart data provided")

    if not isinstance(chart_data, dict):
        raise ValueError(f"Chart data must be a dictionary, got {type(chart_data)}")

    # Generate a chart image for the PDF
    try:
        # Import necessary modules
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        # Create temp directory for images if needed
        import tempfile
        import os
        temp_dir = tempfile.mkdtemp()
        chart_image_path = os.path.join(temp_dir, "chart.png")

        # Generate the chart image
        from ai_service.utils.chart_visualizer import create_chart_image
        create_chart_image(chart_data, chart_image_path)

        # Create a PDF document
        doc = SimpleDocTemplate(output_path, pagesize=(width*72, height*72))

        # Container for document elements
        elements = []

        # Add title
        styles = getSampleStyleSheet()
        if not title:
            title = "Astrological Chart Analysis"

        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 12))

        # Add chart information
        chart_info = []
        if "birth_details" in chart_data:
            birth = chart_data["birth_details"]
            chart_info.append(Paragraph(f"Date: {birth.get('birth_date', 'Unknown')}", styles['Normal']))
            chart_info.append(Paragraph(f"Time: {birth.get('birth_time', 'Unknown')}", styles['Normal']))
            chart_info.append(Paragraph(f"Location: {birth.get('location', 'Unknown')}", styles['Normal']))

        elements.extend(chart_info)
        elements.append(Spacer(1, 24))

        # Build the PDF document
        doc.build(elements)

        return output_path

    except Exception as e:
        # Raise an exception rather than falling back to a simpler PDF
        raise RuntimeError(f"Failed to create PDF report: {e}")

def _calculate_arc_difference(longitude1: float, longitude2: float) -> float:
    """
    Calculate the minimum arc difference between two longitude values.

    Args:
        longitude1: First longitude value
        longitude2: Second longitude value

    Returns:
        Minimum arc difference in degrees
    """
    diff = abs(longitude1 - longitude2)
    return min(diff, 360 - diff)

def get_sign_from_longitude(longitude: float) -> str:
    """
    Get the zodiac sign for a longitude value.

    Args:
        longitude: Position in degrees (0-360)

    Returns:
        Zodiac sign name
    """
    # Normalize longitude to 0-360 range
    longitude = longitude % 360

    # Define zodiac sign boundaries (0° = start of Aries)
    signs = [
        "Aries", "Taurus", "Gemini", "Cancer",
        "Leo", "Virgo", "Libra", "Scorpio",
        "Sagittarius", "Capricorn", "Aquarius", "Pisces"
    ]

    # Each sign occupies 30 degrees
    sign_index = int(longitude / 30)
    return signs[sign_index]

def create_chart_image(chart_data: Dict[str, Any], output_path: str, dpi: int = 300) -> str:
    """
    Create a chart image from chart data.

    Args:
        chart_data: Chart data to visualize
        output_path: Path to save the image
        dpi: Resolution in dots per inch

    Returns:
        Path to the created image
    """
    try:
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 10))

        # Render chart
        render_chart_in_subplot(ax, chart_data)

        # Set title
        birth_details = chart_data.get("birth_details", {})
        birth_date = birth_details.get("birth_date", "Unknown")
        birth_time = birth_details.get("birth_time", "Unknown")
        title = f"Chart for {birth_date} {birth_time}"
        ax.set_title(title)

        # Save figure
        plt.tight_layout()
        plt.savefig(output_path, dpi=dpi)
        plt.close(fig)

        return output_path
    except Exception as e:
        logger.error(f"Failed to create chart image: {e}")
        raise RuntimeError(f"Failed to create chart image: {e}")

def generate_chart_visualization(chart_data: Dict[str, Any], output_path: str, format: str = "png") -> str:
    """
    Generate a chart visualization in the specified format.

    This function is used by the chart export functionality to generate
    visualizations in various formats.

    Args:
        chart_data: Chart data dictionary
        output_path: Path to save the visualization
        format: Output format ('png', 'pdf', 'svg')

    Returns:
        Path to the generated visualization file
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Set format-specific parameters
    dpi = 300  # Default DPI for raster formats
    if format.lower() == 'pdf':
        # Higher DPI for PDF for better quality
        dpi = 600
        # Make sure file has .pdf extension
        if not output_path.lower().endswith('.pdf'):
            output_path = f"{output_path}.pdf"
    elif format.lower() == 'png':
        # Make sure file has .png extension
        if not output_path.lower().endswith('.png'):
            output_path = f"{output_path}.png"
    elif format.lower() == 'svg':
        # Make sure file has .svg extension
        if not output_path.lower().endswith('.svg'):
            output_path = f"{output_path}.svg"

    # Choose visualization style based on chart data
    chart_type = chart_data.get("chart_type", "").lower()

    if chart_type == "vedic" or "vedic" in chart_data.get("calculation_details", {}).get("chart_type", "").lower():
        # Generate a Vedic chart
        if "style" in chart_data:
            vedic_style = chart_data["style"]
        else:
            # Default to North Indian style
            vedic_style = "north_indian"

        # Generate the Vedic chart
        chart_path = render_vedic_chart(chart_data, output_path, style=vedic_style)
    else:
        # Default to Western/Tropical wheel chart
        fig, ax = plt.subplots(figsize=(10, 10))
        render_chart_in_subplot(ax, chart_data, title="Astrological Chart")

        # Save the chart
        plt.savefig(output_path, dpi=dpi, format=format.lower(), bbox_inches='tight')
        plt.close(fig)
        chart_path = output_path

    # If chart is in a different format than requested, convert it
    if not chart_path.lower().endswith(f".{format.lower()}"):
        try:
            from PIL import Image
            # Open the image
            img = Image.open(chart_path)
            # Save in the requested format
            img.save(output_path, format=format.upper())
            # Close the image
            img.close()
            # Use the new path
            chart_path = output_path
        except Exception as e:
            logger.error(f"Failed to convert image format: {e}")
            # Continue with the original format if conversion fails

    # Add contextual information to chart if needed
    if chart_data.get("include_annotations", False):
        try:
            # Add birth details annotation
            add_chart_annotations(chart_path, chart_data)
        except Exception as e:
            logger.error(f"Failed to add annotations: {e}")

    return chart_path

def add_chart_annotations(chart_path: str, chart_data: Dict[str, Any]) -> None:
    """
    Add annotations to a chart image.

    Args:
        chart_path: Path to the chart image
        chart_data: Chart data dictionary
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        # Open the image
        img = Image.open(chart_path)
        draw = ImageDraw.Draw(img)

        # Try to get a font
        try:
            # Try to load a font that supports astrological symbols
            font = ImageFont.truetype("Arial", 12)
        except IOError:
            # Fall back to default font
            font = ImageFont.load_default()

        # Get birth details
        birth_details = chart_data.get("birth_details", {})
        date_str = birth_details.get("date", "")
        time_str = birth_details.get("time", "")
        lat_str = f"{birth_details.get('latitude', 0):.4f}"
        lon_str = f"{birth_details.get('longitude', 0):.4f}"
        location = birth_details.get("location", "")

        # Create annotation text
        annotation = f"Date: {date_str}  Time: {time_str}"
        if location:
            annotation += f"\nLocation: {location} ({lat_str}, {lon_str})"
        else:
            annotation += f"\nCoordinates: {lat_str}, {lon_str}"

        # Use fixed size for text - simplest approach that works across all PIL versions
        # Estimate based on character count and line count
        char_width = 7  # Approximate width of a character in pixels
        line_height = 15  # Approximate height of a line in pixels
        lines = annotation.split('\n')
        text_width = max(len(line) * char_width for line in lines)
        text_height = len(lines) * line_height

        # Calculate position for the bottom of the image
        position = ((img.width - text_width) // 2, img.height - text_height - 10)

        # Add white background for readability with a tuple for rectangle coordinates
        rect_coords = (
            position[0] - 5, position[1] - 5,
            position[0] + text_width + 5, position[1] + text_height + 5
        )
        draw.rectangle(rect_coords, fill="white")

        # Draw the text
        draw.text(position, annotation, fill="black", font=font)

        # Save the annotated image
        img.save(chart_path)
    except Exception as e:
        logger.error(f"Error adding annotations: {e}")
        # Continue without annotations if there's an error
