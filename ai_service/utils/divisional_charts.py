"""
Divisional Charts (Varga) Utility Module

This module provides functions for calculating and rendering divisional charts
commonly used in Vedic astrology, such as D-9 (Navamsa), D-3 (Drekkana),
and others.
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple, Union
import tempfile
import io
import base64

# Import visualization libraries
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.table import Table

from ai_service.utils.chart_visualizer import (
    ZODIAC_SIGNS,
    ZODIAC_SYMBOLS,
    PLANET_SYMBOLS,
    PLANET_COLORS,
    render_vedic_square_chart
)

logger = logging.getLogger(__name__)

def calculate_navamsa_longitude(zodiacal_longitude: float) -> float:
    """
    Calculate navamsa (D-9) longitude from the zodiacal longitude.

    Args:
        zodiacal_longitude: Longitude in degrees (0-360)

    Returns:
        The navamsa longitude in degrees (0-360)
    """
    # Each sign is 30 degrees, each navamsa is 3.33 degrees (30/9)
    sign = int(zodiacal_longitude / 30)
    remainder = zodiacal_longitude % 30
    navamsa = int(remainder / (30/9))

    # Calculate the new longitude based on the navamsa position
    # For odd signs (Aries, Gemini, etc.), the sequence starts from Aries
    # For even signs (Taurus, Cancer, etc.), the sequence starts from Capricorn
    if sign % 2 == 0:  # Odd signs (0-based index means 0 is Aries, which is odd)
        new_sign = (navamsa) % 12
    else:  # Even signs
        new_sign = (navamsa + 9) % 12  # Start from Capricorn (9)

    # Position within the new sign (middle of the navamsa)
    new_longitude = new_sign * 30 + 3.33 / 2

    return new_longitude

def generate_navamsa_chart(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate a D-9 (Navamsa) chart from the birth chart data.

    Args:
        chart_data: Dictionary containing the birth chart data
        output_path: Optional path to save the chart image

    Returns:
        Base64 encoded image data or path to saved image
    """
    try:
        # Create a deep copy of the chart data to modify
        import copy
        d9_chart_data = copy.deepcopy(chart_data)

        # Update the chart title to indicate it's a Navamsa chart
        d9_chart_data["chart_type"] = "Navamsa (D-9)"
        d9_chart_data["divisional"] = "D9"

        # Calculate navamsa positions for all planets
        if "planets" in d9_chart_data:
            planets = d9_chart_data["planets"]

            # Process each planet
            for planet_name, planet_data in planets.items():
                # Get the planet's longitude
                longitude = planet_data.get("longitude", 0)

                # Calculate the navamsa longitude
                navamsa_longitude = calculate_navamsa_longitude(longitude)

                # Update the planet data with navamsa position
                planet_data["longitude"] = navamsa_longitude

                # Recalculate sign based on the new longitude
                sign_num = int(navamsa_longitude / 30)
                sign = ZODIAC_SIGNS[sign_num]
                planet_data["sign"] = sign

                # Calculate position in sign
                pos_in_sign = navamsa_longitude % 30
                planet_data["position_in_sign"] = pos_in_sign

                # Calculate degrees, minutes, seconds
                degrees = int(pos_in_sign)
                minutes_float = (pos_in_sign - degrees) * 60
                minutes = int(minutes_float)
                seconds = int((minutes_float - minutes) * 60)

                planet_data["degrees"] = degrees
                planet_data["minutes"] = minutes
                planet_data["seconds"] = seconds

        # Calculate navamsa position for ascendant
        if "ascendant" in d9_chart_data:
            ascendant = d9_chart_data["ascendant"]
            asc_longitude = ascendant.get("longitude", 0)

            # Calculate the navamsa longitude for ascendant
            navamsa_asc_longitude = calculate_navamsa_longitude(asc_longitude)

            # Update the ascendant data
            ascendant["longitude"] = navamsa_asc_longitude

            # Recalculate sign
            sign_num = int(navamsa_asc_longitude / 30)
            sign = ZODIAC_SIGNS[sign_num]
            ascendant["sign"] = sign

            # Calculate position in sign
            pos_in_sign = navamsa_asc_longitude % 30
            ascendant["position_in_sign"] = pos_in_sign

            # Calculate degrees, minutes, seconds
            degrees = int(pos_in_sign)
            minutes_float = (pos_in_sign - degrees) * 60
            minutes = int(minutes_float)
            seconds = int((minutes_float - minutes) * 60)

            ascendant["degrees"] = degrees
            ascendant["minutes"] = minutes
            ascendant["seconds"] = seconds

        # Recalculate houses based on the new ascendant position
        if "houses" in d9_chart_data and "ascendant" in d9_chart_data:
            houses = []
            asc_longitude = d9_chart_data["ascendant"]["longitude"]

            # Generate 12 houses starting from the ascendant
            for i in range(12):
                house_longitude = (asc_longitude + i * 30) % 360
                sign_num = int(house_longitude / 30)
                sign = ZODIAC_SIGNS[sign_num]

                houses.append({
                    "house_number": i + 1,
                    "sign": sign,
                    "longitude": house_longitude
                })

            d9_chart_data["houses"] = houses

        # Render the Navamsa chart using the standard Vedic chart renderer
        return render_vedic_square_chart(d9_chart_data, output_path)

    except Exception as e:
        logger.error(f"Error generating Navamsa chart: {e}")

        # Create a simple error chart if rendering fails
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, "Error generating Navamsa (D-9) chart",
                ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        if output_path:
            plt.savefig(output_path, bbox_inches='tight')
            plt.close(fig)
            return output_path
        else:
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            return img_str

def generate_drekkana_chart(chart_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate a D-3 (Drekkana) chart from the birth chart data.

    Args:
        chart_data: Dictionary containing the birth chart data
        output_path: Optional path to save the chart image

    Returns:
        Base64 encoded image data or path to saved image
    """
    # Placeholder for D-3 implementation
    # This would use similar logic to the navamsa chart but with different division rules
    logger.warning("D-3 (Drekkana) chart generation not fully implemented")

    # Return a placeholder image
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.text(0.5, 0.5, "D-3 (Drekkana) Chart\nImplementation in progress",
            ha='center', va='center', fontsize=14)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    if output_path:
        plt.savefig(output_path, bbox_inches='tight')
        plt.close(fig)
        return output_path
    else:
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        return img_str

def generate_divisional_chart(chart_data: Dict[str, Any], division: int, output_path: Optional[str] = None) -> str:
    """
    Generate a divisional chart (D-n) from the birth chart data.

    Args:
        chart_data: Dictionary containing the birth chart data
        division: Division number (e.g., 9 for D-9)
        output_path: Optional path to save the chart image

    Returns:
        Base64 encoded image data or path to saved image
    """
    # Implement specific divisional charts based on division number
    if division == 9:
        return generate_navamsa_chart(chart_data, output_path)
    elif division == 3:
        return generate_drekkana_chart(chart_data, output_path)
    else:
        logger.warning(f"D-{division} chart generation not implemented")

        # Return a placeholder image
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.text(0.5, 0.5, f"D-{division} Chart\nImplementation in progress",
                ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        if output_path:
            plt.savefig(output_path, bbox_inches='tight')
            plt.close(fig)
            return output_path
        else:
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            img_str = base64.b64encode(buf.read()).decode('utf-8')
            return img_str
