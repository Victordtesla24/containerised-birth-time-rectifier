"""
Chart visualization functions for the chart service.

This module provides functions for rendering and visualizing astrological charts.
"""

import os
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Tuple

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches

from ai_service.utils.vedic_chart_renderer import VedicChartRenderer

logger = logging.getLogger(__name__)

def generate_vedic_kundli_chart(chart_data: Dict[str, Any], output_dir: Optional[str] = None, chart_output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a traditional North Indian style Kundli chart based on chart data.

    Args:
        chart_data: Dictionary containing chart data including planets, houses, and ascendant.
        output_dir: Optional directory for saving the chart image.
        chart_output_dir: Fallback directory for saving the chart image.

    Returns:
        Dict containing the path to the rendered chart and metadata.
    """
    try:
        # Validate required fields in chart data
        required_fields = ["planets", "houses", "ascendant"]
        for field in required_fields:
            if field not in chart_data:
                raise ValueError(f"Missing required field '{field}' in chart data")

        # Use specified output directory or default
        chart_dir = output_dir or chart_output_dir
        if chart_dir is None:
            raise ValueError("No output directory specified and no default directory available")
        os.makedirs(chart_dir, exist_ok=True)

        # Generate a unique filename
        chart_id = chart_data.get("chart_id", f"vedic_chart_{uuid.uuid4().hex[:8]}")
        filename = f"{chart_id}_north_indian.png"
        output_path = os.path.join(chart_dir, filename)

        # Create the Vedic chart renderer
        renderer = VedicChartRenderer(
            planets=chart_data["planets"],
            houses=chart_data["houses"],
            ascendant=chart_data["ascendant"]
        )

        # Render the chart
        renderer.render(output_path)

        # Return metadata about the generated chart
        return {
            "chart_id": chart_id,
            "chart_type": "vedic_north_indian",
            "chart_path": output_path,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating Vedic Kundli chart: {e}")
        raise

def generate_western_chart(chart_data: Dict[str, Any], output_dir: Optional[str] = None, chart_output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a Western/Tropical chart based on chart data.

    Args:
        chart_data: Dictionary containing chart data including planets, houses, and ascendant.
        output_dir: Optional directory for saving the chart image.
        chart_output_dir: Fallback directory for saving the chart image.

    Returns:
        Dict containing the path to the rendered chart and metadata.
    """
    try:
        # Validate required fields in chart data
        required_fields = ["planets", "houses", "ascendant"]
        for field in required_fields:
            if field not in chart_data:
                raise ValueError(f"Missing required field '{field}' in chart data")

        # Use specified output directory or default
        chart_dir = output_dir or chart_output_dir
        if chart_dir is None:
            raise ValueError("No output directory specified and no default directory available")
        os.makedirs(chart_dir, exist_ok=True)

        # Generate a unique filename
        chart_id = chart_data.get("chart_id", f"western_chart_{uuid.uuid4().hex[:8]}")
        filename = f"{chart_id}_western.png"
        output_path = os.path.join(chart_dir, filename)

        # Render Western chart with matplotlib
        render_western_chart(chart_data, output_path)

        # Return metadata about the generated chart
        return {
            "chart_id": chart_id,
            "chart_type": "western",
            "chart_path": output_path,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating Western chart: {e}")
        raise

def render_western_chart(chart_data: Dict[str, Any], output_path: str) -> None:
    """
    Render a Western astrological chart using matplotlib.

    Args:
        chart_data: The chart data to render
        output_path: Path where to save the output image
    """
    # Set matplotlib to use a non-interactive backend
    matplotlib.use('Agg')

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 10))

    # Set up the chart as a circle
    ax.set_aspect('equal')
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)

    # Draw the outer circle
    circle = patches.Circle((0, 0), 1, fill=False, color='black')
    ax.add_artist(circle)

    # Draw the inner circle
    inner_circle = patches.Circle((0, 0), 0.7, fill=False, color='black')
    ax.add_artist(inner_circle)

    # Draw the house lines
    houses = chart_data.get("houses", [])
    for house in houses:
        house_num = house.get("house", 0)
        longitude = house.get("longitude", 0)
        # Convert astrological degrees to mathematical radians
        # 0° in astrology is at the 3 o'clock position, and it increases counterclockwise
        angle_rad = (90 - longitude) * (np.pi / 180)
        x = np.cos(angle_rad)
        y = np.sin(angle_rad)
        ax.plot([0, x], [0, y], color='black', linestyle='-', alpha=0.5)

        # Label the houses
        text_x = 0.85 * np.cos(angle_rad)
        text_y = 0.85 * np.sin(angle_rad)
        ax.text(text_x, text_y, str(house_num), fontsize=8,
                ha='center', va='center', color='blue')

    # Plot planets
    planets_list = chart_data.get("planets", [])
    planet_symbols = {
        "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀", "mars": "♂",
        "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆", "pluto": "♇"
    }

    for planet in planets_list:
        if isinstance(planet, dict):
            planet_name = planet.get("name", "").lower()
            longitude = planet.get("longitude", 0)
            # Convert to radians for plotting
            angle_rad = (90 - longitude) * (np.pi / 180)
            radius = 0.85  # Slightly inside the outer circle
            x = radius * np.cos(angle_rad)
            y = radius * np.sin(angle_rad)

            # Get the symbol for the planet
            symbol = planet_symbols.get(planet_name, planet_name[0])

            # Plot the planet
            ax.text(x, y, symbol, fontsize=12, ha='center', va='center',
                    color='red', weight='bold')

    # Remove axis ticks and labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')

    # Add title
    chart_time = chart_data.get("date", "") + " " + chart_data.get("time", "")
    plt.title(f"Western Astrological Chart\n{chart_time}")

    # Save the chart
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)  # Close the figure to free memory

    logger.info(f"Western chart saved to {output_path}")

def render_chart_in_subplot(ax: plt.Axes, chart_data: Dict[str, Any]) -> None:
    """
    Render a chart in a matplotlib subplot.

    Args:
        ax: Matplotlib axis to draw on
        chart_data: Chart data to render
    """
    # Set up the chart as a circle
    ax.set_aspect('equal')
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)

    # Draw the outer circle
    circle = patches.Circle((0, 0), 1, fill=False, color='black')
    ax.add_artist(circle)

    # Draw the inner circle
    inner_circle = patches.Circle((0, 0), 0.7, fill=False, color='black')
    ax.add_artist(inner_circle)

    # Draw the house lines
    houses = chart_data.get("houses", [])
    for house in houses:
        house_num = house.get("house", 0)
        longitude = house.get("longitude", 0)
        # Convert astrological degrees to mathematical radians
        angle_rad = (90 - longitude) * (np.pi / 180)
        x = np.cos(angle_rad)
        y = np.sin(angle_rad)
        ax.plot([0, x], [0, y], color='black', linestyle='-', alpha=0.5)

        # Label the houses
        text_x = 0.85 * np.cos(angle_rad)
        text_y = 0.85 * np.sin(angle_rad)
        ax.text(text_x, text_y, str(house_num), fontsize=8,
               ha='center', va='center', color='blue')

    # Plot planets
    planets_list = chart_data.get("planets", [])
    planet_symbols = {
        "sun": "☉", "moon": "☽", "mercury": "☿", "venus": "♀", "mars": "♂",
        "jupiter": "♃", "saturn": "♄", "uranus": "♅", "neptune": "♆", "pluto": "♇"
    }

    for planet in planets_list:
        if isinstance(planet, dict):
            planet_name = planet.get("name", "").lower()
            longitude = planet.get("longitude", 0)
            # Convert to radians for plotting
            angle_rad = (90 - longitude) * (np.pi / 180)
            radius = 0.85  # Slightly inside the outer circle
            x = radius * np.cos(angle_rad)
            y = radius * np.sin(angle_rad)

            # Get the symbol for the planet
            symbol = planet_symbols.get(planet_name, planet_name[0])

            # Plot the planet
            ax.text(x, y, symbol, fontsize=12, ha='center', va='center',
                   color='red', weight='bold')

    # Remove axis ticks and labels
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis('off')
