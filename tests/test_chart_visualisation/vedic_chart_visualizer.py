#!/usr/bin/env python3
"""
Vedic Chart Visualizer

This script visualizes Vedic birth charts in the traditional North Indian Kundali style
from JSON data produced by the birth time rectification tests.
"""

import os
import json
import argparse
import math
from typing import Dict, Any, List, Tuple, Optional
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, PathPatch, Circle, Wedge
from matplotlib.path import Path
import matplotlib.colors as mcolors
import numpy as np
import base64
from io import BytesIO
import sys

# Add project root to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Planet symbols and abbreviations
PLANET_SYMBOLS = {
    "sun": "Su",
    "moon": "Mo",
    "mars": "Ma",
    "mercury": "Me",
    "jupiter": "Ju",
    "venus": "Ve",
    "saturn": "Sa",
    "rahu": "Ra",
    "ketu": "Ke",
    "ascendant": "As",
    "midheaven": "MC"
}

# Zodiac sign symbols and abbreviations
ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

ZODIAC_ABBR = {
    "Aries": "Ar",
    "Taurus": "Ta",
    "Gemini": "Ge",
    "Cancer": "Ca",
    "Leo": "Le",
    "Virgo": "Vi",
    "Libra": "Li",
    "Scorpio": "Sc",
    "Sagittarius": "Sg",
    "Capricorn": "Cp",
    "Aquarius": "Aq",
    "Pisces": "Pi"
}

# House positions for North Indian style chart - each tuple is (house_number, x_position, y_position)
# House positions counterclockwise starting from Ascendant (house 1)
NORTH_INDIAN_HOUSE_POSITIONS = [
    (1, 0.5, 0.9),   # House 1 (Lagna / Ascendant)
    (2, 0.25, 0.75), # House 2
    (3, 0.1, 0.5),   # House 3
    (4, 0.25, 0.25), # House 4
    (5, 0.5, 0.1),   # House 5
    (6, 0.75, 0.25), # House 6
    (7, 0.9, 0.5),   # House 7
    (8, 0.75, 0.75), # House 8
    (9, 0.5, 0.75),  # House 9
    (10, 0.5, 0.5),  # House 10
    (11, 0.75, 0.5), # House 11
    (12, 0.5, 0.25)  # House 12
]

# Colors for planets
PLANET_COLORS = {
    "sun": "#FFD700",      # Gold
    "moon": "#FFFAFA",     # Snow white
    "mercury": "#9ACD32",  # Yellow-green
    "venus": "#FF69B4",    # Pink
    "mars": "#FF4500",     # Red
    "jupiter": "#FFB6C1",  # Light pink
    "saturn": "#4682B4",   # Steel blue
    "rahu": "#800080",     # Purple
    "ketu": "#FFA500",     # Orange
    "ascendant": "#000000" # Black
}

def load_chart_data(json_file: str) -> Dict[str, Any]:
    """Load chart data from JSON file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading JSON data: {e}")
        sys.exit(1)

def normalize_chart_data(chart_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize chart data for consistent processing regardless of JSON structure.
    Returns a standardized dictionary with planets, houses, and angles.
    """
    normalized = {
        "planets": {},
        "houses": {},
        "angles": {},
    }

    # Check if we're dealing with original or rectified chart
    if "chart_data" in chart_data:
        # This is likely the rectified chart format
        planets_data = chart_data.get("chart_data", {}).get("planets", {})
        houses_data = chart_data.get("chart_data", {}).get("houses", {})
        angles_data = {
            "ascendant": chart_data.get("chart_data", {}).get("ascendant", {}),
            "midheaven": chart_data.get("chart_data", {}).get("midheaven", {})
        }
    else:
        # This is likely the original chart format
        planets_data = chart_data.get("planets", {})
        houses_data = chart_data.get("houses", [])
        angles_data = chart_data.get("angles", {})

    # Process planets
    for planet_name, planet_data in planets_data.items():
        if isinstance(planet_data, dict):
            normalized["planets"][planet_name] = {
                "sign": planet_data.get("sign", "Unknown"),
                "degree": float(planet_data.get("degree", 0)),
                "house": planet_data.get("house", 0)
            }

    # Process houses
    if isinstance(houses_data, dict):
        for house_num, house_data in houses_data.items():
            if house_num.isdigit() and int(house_num) <= 12:
                normalized["houses"][int(house_num)] = {
                    "sign": house_data.get("sign", "Unknown"),
                    "degree": float(house_data.get("degree", 0))
                }
    elif isinstance(houses_data, list) and len(houses_data) >= 12:
        # Handle house positions as a list format
        for i in range(12):
            normalized["houses"][i+1] = {
                "longitude": houses_data[i],
                "sign": ZODIAC_SIGNS[int(houses_data[i] / 30) % 12],
                "degree": houses_data[i] % 30
            }

    # Process angles
    for angle_name, angle_data in angles_data.items():
        if isinstance(angle_data, dict):
            normalized["angles"][angle_name] = {
                "sign": angle_data.get("sign", "Unknown"),
                "degree": float(angle_data.get("degree", 0))
            }

    return normalized

def get_house_occupants(chart_data: Dict[str, Any]) -> Dict[int, List[str]]:
    """
    Determine which planets are in which houses.
    Returns a dictionary mapping house numbers to lists of planet symbols.
    """
    house_occupants = {i: [] for i in range(1, 13)}

    normalized = normalize_chart_data(chart_data)

    # Assign planets to houses
    for planet_name, planet_data in normalized["planets"].items():
        house = planet_data.get("house")

        # If house is provided, use it
        if house and 1 <= house <= 12:
            house_num = house
        else:
            # Otherwise derive it from the sign - this is a simplification
            # as proper house determination requires the ascendant
            sign = planet_data.get("sign")
            if sign in ZODIAC_SIGNS:
                sign_index = ZODIAC_SIGNS.index(sign)

                # Get ascendant sign if available
                asc_sign = normalized["angles"].get("ascendant", {}).get("sign")
                if asc_sign in ZODIAC_SIGNS:
                    asc_index = ZODIAC_SIGNS.index(asc_sign)
                    house_num = ((sign_index - asc_index) % 12) + 1
                else:
                    # Fallback if no ascendant
                    house_num = sign_index + 1
            else:
                # Skip if no valid sign
                continue

        symbol = PLANET_SYMBOLS.get(planet_name.lower(), planet_name[:2])
        house_occupants[house_num].append(symbol)

    return house_occupants

def render_vedic_chart_ascii(chart_data: Dict[str, Any], title: str = "Vedic Birth Chart") -> str:
    """
    Render a Vedic chart in ASCII format.
    """
    house_occupants = get_house_occupants(chart_data)

    # Create the chart grid
    chart = []

    # Top row header
    chart.append(f"\n*** {title} ***\n")
    chart.append("┌─────────┬─────────┬─────────┐")

    # House 12, 1, 2
    occupants_12 = " ".join(house_occupants.get(12, []))
    occupants_1 = " ".join(house_occupants.get(1, []))
    occupants_2 = " ".join(house_occupants.get(2, []))
    chart.append(f"│    {occupants_12:<5} │    {occupants_1:<5} │    {occupants_2:<5} │")
    chart.append(f"│   12    │    1    │    2    │")

    # Middle rows top
    chart.append("├─────────┼─────────┼─────────┤")

    # House 11 and 3 content
    occupants_11 = " ".join(house_occupants.get(11, []))
    occupants_3 = " ".join(house_occupants.get(3, []))
    chart.append(f"│    {occupants_11:<5} │         │    {occupants_3:<5} │")
    chart.append(f"│   11    │         │    3    │")

    # Middle rows middle
    chart.append("├─────────┤         ├─────────┤")

    # House 10 content
    occupants_10 = " ".join(house_occupants.get(10, []))
    occupants_4 = " ".join(house_occupants.get(4, []))
    chart.append(f"│    {occupants_10:<5} │         │    {occupants_4:<5} │")
    chart.append(f"│   10    │         │    4    │")

    # Middle rows bottom
    chart.append("├─────────┤         ├─────────┤")

    # House 9 content
    occupants_9 = " ".join(house_occupants.get(9, []))
    occupants_5 = " ".join(house_occupants.get(5, []))
    chart.append(f"│    {occupants_9:<5} │         │    {occupants_5:<5} │")
    chart.append(f"│    9    │         │    5    │")

    # Bottom rows
    chart.append("├─────────┼─────────┼─────────┤")

    # House 8, 7, 6 content
    occupants_8 = " ".join(house_occupants.get(8, []))
    occupants_7 = " ".join(house_occupants.get(7, []))
    occupants_6 = " ".join(house_occupants.get(6, []))
    chart.append(f"│    {occupants_8:<5} │    {occupants_7:<5} │    {occupants_6:<5} │")
    chart.append(f"│    8    │    7    │    6    │")

    # Final line
    chart.append("└─────────┴─────────┴─────────┘")

    return "\n".join(chart)

def render_vedic_chart_matplotlib(chart_data: Dict[str, Any],
                                 title: str = "Vedic Birth Chart",
                                 show_planets: bool = True) -> Figure:
    """
    Render a Vedic chart using Matplotlib.
    Returns a matplotlib Figure object.
    """
    fig, ax = plt.subplots(figsize=(10, 10))

    # Get house occupants
    house_occupants = get_house_occupants(chart_data)

    # Configure plot
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # Draw the outer square
    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, linewidth=2, color='black'))

    # Draw the central square (center of the chart)
    ax.add_patch(Rectangle((0.3, 0.3), 0.4, 0.4, fill=False, linewidth=2, color='black'))

    # Draw diagonal lines
    ax.plot([0, 1], [0, 1], 'k-', linewidth=2)
    ax.plot([0, 1], [1, 0], 'k-', linewidth=2)

    # Add house numbers and content - Using North Indian style positions
    for house_num, x, y in NORTH_INDIAN_HOUSE_POSITIONS:
        # Add house number
        ax.text(x, y, str(house_num), fontsize=14, ha='center', va='center',
                 bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))

        # Add planets in house if any
        if show_planets and house_num in house_occupants and house_occupants[house_num]:
            planet_text = " ".join(house_occupants[house_num])
            # Position planet text slightly offset from house number
            if house_num in [1, 5, 7, 9]:  # Top and bottom houses
                ax.text(x, y - 0.08, planet_text, fontsize=12, ha='center', va='center',
                       bbox=dict(facecolor='lightyellow', alpha=0.8, edgecolor='none'))
            elif house_num in [3, 11]:  # Left and right houses
                ax.text(x, y + 0.08, planet_text, fontsize=12, ha='center', va='center',
                       bbox=dict(facecolor='lightyellow', alpha=0.8, edgecolor='none'))
            else:  # Corner houses
                ax.text(x + 0.05, y - 0.05, planet_text, fontsize=12, ha='center', va='center',
                       bbox=dict(facecolor='lightyellow', alpha=0.8, edgecolor='none'))

    # Add title
    plt.suptitle(title, fontsize=16, y=0.95)

    # Add a note about ascendant position
    normalized = normalize_chart_data(chart_data)
    asc_info = normalized["angles"].get("ascendant", {})
    if asc_info and "sign" in asc_info:
        asc_text = f"Ascendant: {asc_info['sign']} {asc_info.get('degree', 0):.1f}°"
        plt.figtext(0.5, 0.02, asc_text, ha="center", fontsize=12,
                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='lightgray'))

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    return fig

def render_vedic_chart_html(chart_data: Dict[str, Any],
                           title: str = "Vedic Birth Chart",
                           output_dir: str = "output",
                           show_planets: bool = True) -> str:
    """
    Render a Vedic chart as HTML.
    Returns the path to the HTML file.
    """
    # Create the matplotlib chart
    fig = render_vedic_chart_matplotlib(chart_data, title, show_planets)

    # Save the figure to a BytesIO object
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=100)
    plt.close(fig)
    buf.seek(0)

    # Encode the image as base64
    img_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    # Create HTML content
    normalized = normalize_chart_data(chart_data)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; }}
        .chart-container {{ text-align: center; margin: 20px 0; }}
        .planet-info {{ margin-top: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>

        <div class="chart-container">
            <img src="data:image/png;base64,{img_base64}" alt="Vedic Birth Chart" style="max-width:100%;">
        </div>

        <div class="planet-info">
            <h2>Planetary Positions</h2>
            <table>
                <tr>
                    <th>Planet</th>
                    <th>Sign</th>
                    <th>Degree</th>
                    <th>House</th>
                </tr>
    """

    # Add planetary positions table
    for planet_name, planet_data in normalized["planets"].items():
        html_content += f"""
                <tr>
                    <td>{planet_name.capitalize()}</td>
                    <td>{planet_data.get('sign', 'Unknown')}</td>
                    <td>{planet_data.get('degree', 0):.2f}°</td>
                    <td>{planet_data.get('house', '-')}</td>
                </tr>"""

    # Add ascendant and midheaven info if available
    for angle_name, angle_data in normalized["angles"].items():
        html_content += f"""
                <tr>
                    <td>{angle_name.capitalize()}</td>
                    <td>{angle_data.get('sign', 'Unknown')}</td>
                    <td>{angle_data.get('degree', 0):.2f}°</td>
                    <td>-</td>
                </tr>"""

    html_content += """
            </table>
        </div>
    </div>
</body>
</html>
    """

    # Save HTML to file
    output_file = os.path.join(output_dir, f"{title.replace(' ', '_').lower()}.html")
    with open(output_file, 'w') as f:
        f.write(html_content)

    return output_file

def process_charts(input_json: str, output_dir: str, format_choice: str, show_planets: bool) -> None:
    """
    Process and visualize charts from the JSON data.
    """
    # Load the chart data
    data = load_chart_data(input_json)

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Process original chart
    original_chart = data.get("original_chart", {})
    if original_chart:
        print("Generating visualization for original chart...")

        if format_choice in ["ascii", "all"]:
            ascii_chart = render_vedic_chart_ascii(original_chart, "Original Vedic Birth Chart")
            ascii_file = os.path.join(output_dir, "original_chart_ascii.txt")
            with open(ascii_file, 'w') as f:
                f.write(ascii_chart)
            print(f"ASCII chart saved to {ascii_file}")

            # Also print to console
            print("\nOriginal Chart (ASCII):")
            print(ascii_chart)

        if format_choice in ["png", "all"]:
            fig = render_vedic_chart_matplotlib(original_chart, "Original Vedic Birth Chart", show_planets)
            png_file = os.path.join(output_dir, "original_chart.png")
            fig.savefig(png_file, dpi=150)
            plt.close(fig)
            print(f"PNG chart saved to {png_file}")

        if format_choice in ["html", "all"]:
            html_file = render_vedic_chart_html(original_chart, "Original Vedic Birth Chart", output_dir, show_planets)
            print(f"HTML chart saved to {html_file}")

    # Process rectified chart
    rectified_chart = data.get("rectified_chart", {})
    if rectified_chart:
        print("\nGenerating visualization for rectified chart...")

        if format_choice in ["ascii", "all"]:
            ascii_chart = render_vedic_chart_ascii(rectified_chart, "Rectified Vedic Birth Chart")
            ascii_file = os.path.join(output_dir, "rectified_chart_ascii.txt")
            with open(ascii_file, 'w') as f:
                f.write(ascii_chart)
            print(f"ASCII chart saved to {ascii_file}")

            # Also print to console
            print("\nRectified Chart (ASCII):")
            print(ascii_chart)

        if format_choice in ["png", "all"]:
            fig = render_vedic_chart_matplotlib(rectified_chart, "Rectified Vedic Birth Chart", show_planets)
            png_file = os.path.join(output_dir, "rectified_chart.png")
            fig.savefig(png_file, dpi=150)
            plt.close(fig)
            print(f"PNG chart saved to {png_file}")

        if format_choice in ["html", "all"]:
            html_file = render_vedic_chart_html(rectified_chart, "Rectified Vedic Birth Chart", output_dir, show_planets)
            print(f"HTML chart saved to {html_file}")

    # Generate side-by-side comparison if both charts exist
    if original_chart and rectified_chart and format_choice in ["png", "html", "all"]:
        print("\nGenerating side-by-side comparison...")

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

        # Configure plot 1 (original)
        ax1.set_xlim(0, 1)
        ax1.set_ylim(0, 1)
        ax1.axis('off')
        ax1.set_title("Original Chart", fontsize=16)

        # Configure plot 2 (rectified)
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.axis('off')
        ax2.set_title("Rectified Chart", fontsize=16)

        # Draw original chart in first subplot
        house_occupants1 = get_house_occupants(original_chart)

        # Draw the outer square
        ax1.add_patch(Rectangle((0, 0), 1, 1, fill=False, linewidth=2, color='black'))
        ax1.add_patch(Rectangle((0.3, 0.3), 0.4, 0.4, fill=False, linewidth=2, color='black'))
        ax1.plot([0, 1], [0, 1], 'k-', linewidth=2)
        ax1.plot([0, 1], [1, 0], 'k-', linewidth=2)

        # Draw rectified chart in second subplot
        house_occupants2 = get_house_occupants(rectified_chart)

        # Draw the outer square
        ax2.add_patch(Rectangle((0, 0), 1, 1, fill=False, linewidth=2, color='black'))
        ax2.add_patch(Rectangle((0.3, 0.3), 0.4, 0.4, fill=False, linewidth=2, color='black'))
        ax2.plot([0, 1], [0, 1], 'k-', linewidth=2)
        ax2.plot([0, 1], [1, 0], 'k-', linewidth=2)

        # Add house numbers and content for both charts
        for house_num, x, y in NORTH_INDIAN_HOUSE_POSITIONS:
            # Add to original chart
            ax1.text(x, y, str(house_num), fontsize=14, ha='center', va='center',
                   bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))

            # Add to rectified chart
            ax2.text(x, y, str(house_num), fontsize=14, ha='center', va='center',
                   bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))

            # Add planets if showing
            if show_planets:
                # Original chart planets
                if house_num in house_occupants1 and house_occupants1[house_num]:
                    planet_text = " ".join(house_occupants1[house_num])
                    ax1.text(x, y - 0.08, planet_text, fontsize=12, ha='center', va='center',
                           bbox=dict(facecolor='lightyellow', alpha=0.8, edgecolor='none'))

                # Rectified chart planets
                if house_num in house_occupants2 and house_occupants2[house_num]:
                    planet_text = " ".join(house_occupants2[house_num])
                    ax2.text(x, y - 0.08, planet_text, fontsize=12, ha='center', va='center',
                           bbox=dict(facecolor='lightyellow', alpha=0.8, edgecolor='none'))

        # Add birth time info
        orig_time = data.get("original_birth_details", {}).get("birth_time", "Unknown")
        rect_time = data.get("rectified_birth_details", {}).get("birth_time", "Unknown")

        # Add a subtitle with time information
        if isinstance(rect_time, str) and "T" in rect_time:
            # Handle ISO format
            rect_time = rect_time.split("T")[1]

        plt.figtext(0.5, 0.02,
                   f"Original Birth Time: {orig_time}   →   Rectified Birth Time: {rect_time}",
                   ha="center", fontsize=14,
                   bbox=dict(facecolor='white', alpha=0.8, edgecolor='lightgray'))

        plt.suptitle("Vedic Birth Chart Comparison", fontsize=18, y=0.98)
        plt.tight_layout(rect=[0, 0.05, 1, 0.95])

        # Save the comparison chart
        comparison_file = os.path.join(output_dir, "chart_comparison.png")
        plt.savefig(comparison_file, dpi=150)
        plt.close(fig)
        print(f"Comparison chart saved to {comparison_file}")

        # Create HTML comparison view
        if format_choice in ["html", "all"]:
            # Get base64 of comparison image
            with open(comparison_file, 'rb') as f:
                comparison_img_base64 = base64.b64encode(f.read()).decode('utf-8')

            # Create HTML content for comparison
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Vedic Birth Chart Comparison</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1, h2 {{ color: #333; text-align: center; }}
        .chart-container {{ text-align: center; margin: 20px 0; }}
        .comparison-info {{ margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }}
        .time-diff {{ font-weight: bold; color: #d9534f; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .changed {{ background-color: #fff4e5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Vedic Birth Chart Comparison</h1>

        <div class="comparison-info">
            <p><strong>Original Birth Time:</strong> {orig_time}</p>
            <p><strong>Rectified Birth Time:</strong> {rect_time}</p>
            <p class="time-diff">Time Difference: {data.get("rectification_details", {}).get("time_adjustment", "Unknown")}</p>
            <p><strong>Explanation:</strong> {data.get("rectification_details", {}).get("explanation", "No explanation provided.")}</p>
        </div>

        <div class="chart-container">
            <img src="data:image/png;base64,{comparison_img_base64}" alt="Chart Comparison" style="max-width:100%;">
        </div>

        <h2>Planetary Positions Comparison</h2>
        <table>
            <tr>
                <th>Planet</th>
                <th>Original Sign</th>
                <th>Original Degree</th>
                <th>Rectified Sign</th>
                <th>Rectified Degree</th>
                <th>Changed?</th>
            </tr>
            """

            # Normalize both charts
            orig_normalized = normalize_chart_data(original_chart)
            rect_normalized = normalize_chart_data(rectified_chart)

            # Add planetary positions comparison
            for planet_name in sorted(set(list(orig_normalized["planets"].keys()) + list(rect_normalized["planets"].keys()))):
                orig_planet = orig_normalized["planets"].get(planet_name, {})
                rect_planet = rect_normalized["planets"].get(planet_name, {})

                orig_sign = orig_planet.get("sign", "Unknown")
                orig_degree = orig_planet.get("degree", 0)
                rect_sign = rect_planet.get("sign", "Unknown")
                rect_degree = rect_planet.get("degree", 0)

                changed = orig_sign != rect_sign or abs(orig_degree - rect_degree) > 0.5
                row_class = "changed" if changed else ""

                html_content += f"""
                <tr class="{row_class}">
                    <td>{planet_name.capitalize()}</td>
                    <td>{orig_sign}</td>
                    <td>{orig_degree:.2f}°</td>
                    <td>{rect_sign}</td>
                    <td>{rect_degree:.2f}°</td>
                    <td>{"Yes" if changed else "No"}</td>
                </tr>"""

            # Add ascendant comparison
            orig_asc = orig_normalized["angles"].get("ascendant", {})
            rect_asc = rect_normalized["angles"].get("ascendant", {})

            orig_asc_sign = orig_asc.get("sign", "Unknown")
            orig_asc_degree = orig_asc.get("degree", 0)
            rect_asc_sign = rect_asc.get("sign", "Unknown")
            rect_asc_degree = rect_asc.get("degree", 0)

            asc_changed = orig_asc_sign != rect_asc_sign or abs(orig_asc_degree - rect_asc_degree) > 0.5
            asc_row_class = "changed" if asc_changed else ""

            html_content += f"""
                <tr class="{asc_row_class}">
                    <td>Ascendant</td>
                    <td>{orig_asc_sign}</td>
                    <td>{orig_asc_degree:.2f}°</td>
                    <td>{rect_asc_sign}</td>
                    <td>{rect_asc_degree:.2f}°</td>
                    <td>{"Yes" if asc_changed else "No"}</td>
                </tr>"""

            html_content += """
            </table>
        </div>
    </div>
</body>
</html>
            """

            # Save HTML comparison to file
            comparison_html_file = os.path.join(output_dir, "chart_comparison.html")
            with open(comparison_html_file, 'w') as f:
                f.write(html_content)
            print(f"HTML comparison saved to {comparison_html_file}")

def main():
    """Main function to process arguments and run the visualization."""
    parser = argparse.ArgumentParser(description='Visualize Vedic charts from JSON data')
    parser.add_argument('--input-json', required=True, help='Path to input JSON file')
    parser.add_argument('--output-dir', required=True, help='Directory to save output files')
    parser.add_argument('--format', choices=['ascii', 'png', 'html', 'all'], default='all',
                      help='Output format (default: all)')
    parser.add_argument('--show-planets', type=str, choices=['true', 'false'], default='true',
                      help='Show planet symbols in chart (default: true)')

    args = parser.parse_args()

    show_planets = args.show_planets.lower() == 'true'

    process_charts(args.input_json, args.output_dir, args.format, show_planets)

if __name__ == "__main__":
    main()
