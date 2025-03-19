"""
Utilities for Birth Time Rectifier tests.
Provides shared functionality for visualization, logging, and input handling.
"""

import logging
import json
import random
import sys
import os
import argparse
import datetime
import requests
from typing import Dict, Any, List, Tuple, Optional, Union
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
import shutil
import pytest

# Base URL for API tests with standardized v1 prefix
BASE_URL = "http://localhost:8000/api/v1"

# Configure logging
log_dir = os.path.join(os.getcwd(), 'tests', 'results', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'consolidated_tests.log')

# Clear previous log file
if os.path.exists(log_file):
    os.remove(log_file)

# Set up file and console logging
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Get the root logger and add handlers
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
# Remove any existing handlers
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Create a logger for this module
logger = logging.getLogger("test_utils")

# Terminal colors for enhanced output
class TermColors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def colorize(text, color):
        return f"{color}{text}{TermColors.ENDC}"

    @staticmethod
    def get_confidence_color(confidence: float) -> str:
        """Return appropriate color based on confidence level"""
        if confidence >= 80:
            return TermColors.GREEN
        elif confidence >= 50:
            return TermColors.YELLOW
        else:
            return TermColors.RED


# Input handling functions
def generate_random_birth_data() -> Dict[str, Any]:
    """Generate random birth data for testing"""
    # List of major cities with their coordinates and timezones
    cities = [
        {"name": "New York", "country": "USA", "latitude": 40.7128, "longitude": -74.0060, "timezone": "America/New_York"},
        {"name": "London", "country": "UK", "latitude": 51.5074, "longitude": -0.1278, "timezone": "Europe/London"},
        {"name": "Tokyo", "country": "Japan", "latitude": 35.6762, "longitude": 139.6503, "timezone": "Asia/Tokyo"},
        {"name": "Sydney", "country": "Australia", "latitude": -33.8688, "longitude": 151.2093, "timezone": "Australia/Sydney"},
        {"name": "Mumbai", "country": "India", "latitude": 19.0760, "longitude": 72.8777, "timezone": "Asia/Kolkata"},
        {"name": "Cairo", "country": "Egypt", "latitude": 30.0444, "longitude": 31.2357, "timezone": "Africa/Cairo"},
        {"name": "Rio de Janeiro", "country": "Brazil", "latitude": -22.9068, "longitude": -43.1729, "timezone": "America/Sao_Paulo"},
        {"name": "Moscow", "country": "Russia", "latitude": 55.7558, "longitude": 37.6173, "timezone": "Europe/Moscow"},
        {"name": "Los Angeles", "country": "USA", "latitude": 34.0522, "longitude": -118.2437, "timezone": "America/Los_Angeles"},
        {"name": "Paris", "country": "France", "latitude": 48.8566, "longitude": 2.3522, "timezone": "Europe/Paris"}
    ]

    # Generate random date (1950-2010)
    year = random.randint(1950, 2010)
    month = random.randint(1, 12)
    # Handle month lengths, including February in leap years
    if month == 2:
        max_day = 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
    elif month in [4, 6, 9, 11]:
        max_day = 30
    else:
        max_day = 31
    day = random.randint(1, max_day)

    # Generate random time
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)

    # Format date and time
    birth_date = f"{year}-{month:02d}-{day:02d}"
    birth_time = f"{hour:02d}:{minute:02d}:00"

    # Select random city
    location = random.choice(cities)

    # Construct birth data
    birth_data = {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "location": f"{location['name']}, {location['country']}",
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timezone": location["timezone"]
    }

    logger.info(f"Generated random birth data: {json.dumps(birth_data, indent=2)}")
    return birth_data

def prompt_for_birth_data() -> Dict[str, Any]:
    """Prompt user for birth data input"""
    print(TermColors.colorize("\nBIRTH TIME RECTIFIER TEST", TermColors.HEADER + TermColors.BOLD))
    print(TermColors.colorize("Please enter birth details for testing:\n", TermColors.CYAN))

    # Get birth date
    while True:
        try:
            birth_date = input("Birth date (YYYY-MM-DD): ")
            # Validate date format
            datetime.datetime.strptime(birth_date, "%Y-%m-%d")
            break
        except ValueError:
            print(TermColors.colorize("Invalid date format. Please use YYYY-MM-DD.", TermColors.RED))

    # Get birth time
    while True:
        try:
            birth_time = input("Birth time (HH:MM, 24-hour format): ")
            # Add seconds if not provided
            if len(birth_time.split(":")) == 2:
                birth_time = f"{birth_time}:00"
            # Validate time format
            datetime.datetime.strptime(birth_time, "%H:%M:%S")
            break
        except ValueError:
            print(TermColors.colorize("Invalid time format. Please use HH:MM (24-hour format).", TermColors.RED))

    # Get birth location
    location = input("Birth location (City, Country): ")

    # Geocode the location
    print(TermColors.colorize("Geocoding location...", TermColors.YELLOW))
    geocoded_location = geocode_location(location)

    # Construct birth data
    birth_data = {
        "birth_date": birth_date,
        "birth_time": birth_time,
        "location": location,
        "latitude": geocoded_location["latitude"],
        "longitude": geocoded_location["longitude"],
        "timezone": geocoded_location["timezone"]
    }

    logger.info(f"User provided birth data: {json.dumps(birth_data, indent=2)}")
    return birth_data

def geocode_location(location_name: str) -> Dict[str, Any]:
    """Geocode location using API or fallback to static list"""
    # Try geocoding with API first
    try:
        response = requests.post(
            f"{BASE_URL}/geocode",
            json={"query": location_name},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                print(TermColors.colorize(f"Found location: {result.get('name', location_name)} "
                                        f"(Lat: {result['latitude']}, Lon: {result['longitude']})",
                                        TermColors.GREEN))
                return {
                    "latitude": result["latitude"],
                    "longitude": result["longitude"],
                    "timezone": result["timezone"]
                }
    except Exception as e:
        logger.warning(f"API geocoding failed: {str(e)}")

    # If API fails, try static list
    cities = [
        {"name": "New York", "country": "USA", "latitude": 40.7128, "longitude": -74.0060, "timezone": "America/New_York"},
        {"name": "London", "country": "UK", "latitude": 51.5074, "longitude": -0.1278, "timezone": "Europe/London"},
        {"name": "Tokyo", "country": "Japan", "latitude": 35.6762, "longitude": 139.6503, "timezone": "Asia/Tokyo"},
        {"name": "Sydney", "country": "Australia", "latitude": -33.8688, "longitude": 151.2093, "timezone": "Australia/Sydney"},
        {"name": "Mumbai", "country": "India", "latitude": 19.0760, "longitude": 72.8777, "timezone": "Asia/Kolkata"},
        {"name": "Cairo", "country": "Egypt", "latitude": 30.0444, "longitude": 31.2357, "timezone": "Africa/Cairo"},
        {"name": "Rio de Janeiro", "country": "Brazil", "latitude": -22.9068, "longitude": -43.1729, "timezone": "America/Sao_Paulo"},
        {"name": "Moscow", "country": "Russia", "latitude": 55.7558, "longitude": 37.6173, "timezone": "Europe/Moscow"},
        {"name": "Los Angeles", "country": "USA", "latitude": 34.0522, "longitude": -118.2437, "timezone": "America/Los_Angeles"},
        {"name": "Paris", "country": "France", "latitude": 48.8566, "longitude": 2.3522, "timezone": "Europe/Paris"}
    ]

    # Try to match location with cities list
    location_lower = location_name.lower()
    for city in cities:
        if city["name"].lower() in location_lower or location_lower in city["name"].lower():
            print(TermColors.colorize(f"Found location: {city['name']} "
                                     f"(Lat: {city['latitude']}, Lon: {city['longitude']})",
                                     TermColors.GREEN))
            return {
                "latitude": city["latitude"],
                "longitude": city["longitude"],
                "timezone": city["timezone"]
            }

    # If all else fails, prompt for manual coordinates
    print(TermColors.colorize(f"Could not geocode {location_name}. Please enter coordinates manually:", TermColors.YELLOW))

    while True:
        try:
            latitude = float(input("Latitude: "))
            if latitude < -90 or latitude > 90:
                raise ValueError("Latitude must be between -90 and 90")
            break
        except ValueError as e:
            print(TermColors.colorize(f"Invalid latitude: {str(e)}", TermColors.RED))

    while True:
        try:
            longitude = float(input("Longitude: "))
            if longitude < -180 or longitude > 180:
                raise ValueError("Longitude must be between -180 and 180")
            break
        except ValueError as e:
            print(TermColors.colorize(f"Invalid longitude: {str(e)}", TermColors.RED))

    # List of common timezones for selection
    common_timezones = [
        "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
        "Europe/London", "Europe/Paris", "Europe/Berlin", "Europe/Moscow",
        "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata", "Asia/Dubai",
        "Australia/Sydney", "Pacific/Auckland", "Africa/Cairo"
    ]

    print("Select a timezone:")
    for i, tz in enumerate(common_timezones, 1):
        print(f"{i}. {tz}")

    while True:
        try:
            selection = int(input("Enter timezone number: "))
            if 1 <= selection <= len(common_timezones):
                timezone = common_timezones[selection - 1]
                break
            else:
                raise ValueError(f"Select a number between 1 and {len(common_timezones)}")
        except ValueError as e:
            print(TermColors.colorize(f"Invalid selection: {str(e)}", TermColors.RED))

    return {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone
    }

def parse_birth_data_args() -> Dict[str, Any]:
    """Parse command line arguments for birth data"""
    parser = argparse.ArgumentParser(description='Birth Time Rectifier Tests')
    parser.add_argument('--mode', choices=['random', 'manual'], default='random',
                        help='Data input mode: random or manual')
    parser.add_argument('--date', help='Birth date in YYYY-MM-DD format')
    parser.add_argument('--time', help='Birth time in HH:MM or HH:MM:SS format')
    parser.add_argument('--location', help='Birth location (City, Country)')
    parser.add_argument('--confidence-threshold', type=int, default=80,
                        help='Confidence threshold for questionnaire (1-100, default 80)')

    args = parser.parse_args()

    # If any birth detail is provided, switch to manual mode
    if args.date or args.time or args.location:
        args.mode = 'manual'

    # If manual mode but missing details, will prompt for them later
    if args.mode == 'manual':
        if not all([args.date, args.time, args.location]):
            logger.info("Some birth details missing from command line, will prompt for input")

    return {
        "mode": args.mode,
        "date": args.date,
        "time": args.time,
        "location": args.location,
        "confidence_threshold": args.confidence_threshold
    }

def get_birth_data() -> Dict[str, Any]:
    """Get birth data from command line args or user input"""
    args = parse_birth_data_args()

    if args["mode"] == "random":
        return generate_random_birth_data()
    else:
        # If manual mode with complete args, construct birth data
        if all([args["date"], args["time"], args["location"]]):
            # Add seconds if not provided in time
            time = args["time"]
            if len(time.split(":")) == 2:
                time = f"{time}:00"

            # Need to geocode the location
            geocoded = geocode_location(args["location"])

            return {
                "birth_date": args["date"],
                "birth_time": time,
                "location": args["location"],
                "latitude": geocoded["latitude"],
                "longitude": geocoded["longitude"],
                "timezone": geocoded["timezone"]
            }
        else:
            # Prompt for missing details
            return prompt_for_birth_data()

# Visualization functions
def visualize_confidence_progress(confidence_history: List[Dict[str, Any]], threshold: int = 80) -> str:
    """Generate visualization of confidence progression and save to file"""
    # Create figure directory if it doesn't exist
    fig_dir = os.path.join(os.getcwd(), 'tests', 'results', 'figures')
    os.makedirs(fig_dir, exist_ok=True)

    # Create figure filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(fig_dir, f'confidence_progress_{timestamp}.png')

    # Extract data
    questions = [item["question_num"] for item in confidence_history]
    confidence_values = [item["confidence"] for item in confidence_history]

    # Set up figure
    plt.figure(figsize=(10, 6))

    # Create confidence line plot
    plt.plot(questions, confidence_values, 'b-', linewidth=2, marker='o', markersize=8)

    # Add threshold line
    plt.axhline(y=threshold, color='r', linestyle='--', alpha=0.7, label=f'Threshold ({threshold}%)')

    # Add labels and title
    plt.xlabel('Question Number')
    plt.ylabel('Confidence Score (%)')
    plt.title('Birth Time Rectification Confidence Progression')

    # Set axes limits
    plt.ylim(0, 105)  # Slightly above 100 to see the full range
    plt.xlim(0.5, max(questions) + 0.5)  # Start at 0.5 to see question 1 clearly

    # Add grid
    plt.grid(True, alpha=0.3)

    # Add annotations for significant changes
    for i in range(1, len(confidence_history)):
        change = confidence_history[i]["confidence"] - confidence_history[i-1]["confidence"]
        if abs(change) > 5:  # Only annotate significant changes
            color = 'green' if change > 0 else 'red'
            plt.annotate(f'{change:+.1f}%',
                         xy=(questions[i], confidence_values[i]),
                         xytext=(10, 10 if change > 0 else -15),
                         textcoords='offset points',
                         color=color,
                         arrowprops=dict(arrowstyle='->', color=color))

    # Add threshold crossing point
    crossed_threshold = False
    for i in range(1, len(confidence_history)):
        if confidence_values[i-1] < threshold <= confidence_values[i]:
            crossed_threshold = True
            plt.scatter(questions[i], confidence_values[i], color='red', s=100, zorder=5)

            # Annotation without problematic parameters
            annotation_props = {
                'xy': (questions[i], confidence_values[i]),
                'xytext': (0, 20),
                'textcoords': 'offset points',
                'color': 'darkred',
                'fontweight': 'bold',
                'arrowprops': {'arrowstyle': '->', 'color': 'darkred'}
            }
            # Add bbox separately to avoid type checking issues
            bbox_props = {'boxstyle': 'round,pad=0.5', 'fc': 'yellow', 'alpha': 0.7}
            annotation = plt.annotate(
                f'Threshold reached at Q{questions[i]}!',
                **annotation_props
            )
            annotation.set_bbox(bbox_props)

    # Add legend
    plt.legend(loc='best')

    # Save figure
    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()

    logger.info(f"Confidence progression visualization saved to {filename}")
    return filename

def display_confidence_progress_bar(current: float, threshold: int = 80, bar_width: int = 50) -> None:
    """Display a progress bar showing current confidence vs threshold"""
    # Calculate number of filled blocks
    filled_width = int(current / 100 * bar_width)
    # Calculate threshold position
    threshold_pos = int(threshold / 100 * bar_width)

    # Create the bar with appropriate colors
    bar = []
    for i in range(bar_width):
        if i < filled_width:
            # Filled part
            if i < threshold_pos:
                bar.append(TermColors.colorize('█', TermColors.YELLOW))
            else:
                bar.append(TermColors.colorize('█', TermColors.GREEN))
        else:
            # Unfilled part
            if i == threshold_pos:
                bar.append(TermColors.colorize('|', TermColors.RED))
            else:
                bar.append(' ')

    # Format confidence with appropriate color
    if current >= threshold:
        conf_color = TermColors.GREEN
    elif current >= 50:
        conf_color = TermColors.YELLOW
    else:
        conf_color = TermColors.RED

    conf_text = TermColors.colorize(f"{current:.1f}%", conf_color)

    # Calculate remaining to threshold
    if current < threshold:
        remaining = threshold - current
        remaining_text = f" ({remaining:.1f}% to threshold)"
    else:
        remaining_text = f" (Exceeded threshold by {current - threshold:.1f}%)"

    # Print the bar
    print(f"Confidence: [{(''.join(bar))}] {conf_text}{remaining_text}")

def visualize_planets(planets_data,
                      title: str = "Planetary Positions",
                      save_path: Optional[str] = None) -> str:
    """Create a visualization of planetary positions in the chart"""
    # Create figure directory if it doesn't exist
    fig_dir = os.path.join(os.getcwd(), 'tests', 'results', 'figures')
    os.makedirs(fig_dir, exist_ok=True)

    # Create figure filename if not provided
    if not save_path:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(fig_dir, f'planets_{timestamp}.png')

    # Process the planets data into a standard list format
    planets_list = []

    # Handle different input formats
    if isinstance(planets_data, dict):
        # It might be a chart object with a planets key
        if "planets" in planets_data:
            planets_source = planets_data["planets"]
            if isinstance(planets_source, dict):
                # Convert dict of planets to list
                for planet_key, planet_data in planets_source.items():
                    if isinstance(planet_data, dict):
                        # Add name if not present but we have the key
                        if "name" not in planet_data and planet_key:
                            planet_copy = planet_data.copy()
                            planet_copy["name"] = planet_key.capitalize()
                            planets_list.append(planet_copy)
                        else:
                            planets_list.append(planet_data)
            elif isinstance(planets_source, list):
                planets_list = planets_source
        else:
            # If it's a dict but doesn't have planets key, might be a single planet
            if "name" in planets_data:
                planets_list = [planets_data]
    elif isinstance(planets_data, list):
        # Already a list of planets
        planets_list = planets_data
    elif isinstance(planets_data, str):
        # If it's a string, log an error and return a default filename
        logger.error(f"Invalid planets_data (string): {planets_data}")
        return save_path

    # Convert planet data to degrees for plotting
    planet_names = []
    planet_degrees = []
    planet_categories = []

    for planet in planets_list:
        # Skip if planet is not a dict
        if not isinstance(planet, dict):
            continue

        # Get the planet name
        name = planet.get("name", "")
        if not name:
            continue

        # Get position in degrees (0-360)
        sign_num = planet.get("sign_num", 0)
        degree = planet.get("degree", 0)
        position_deg = (sign_num - 1) * 30 + degree

        planet_names.append(name)
        planet_degrees.append(position_deg)

        # Categorize planets
        if name in ["Sun", "Moon"]:
            category = "Luminaries"
        elif name in ["Mercury", "Venus", "Mars"]:
            category = "Personal Planets"
        elif name in ["Jupiter", "Saturn"]:
            category = "Social Planets"
        else:
            category = "Outer Planets"

        planet_categories.append(category)

    # Set up figure - polar plot
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='polar')

    # Convert degrees to radians for polar plot (and reverse direction)
    radians = [(360 - deg) * np.pi / 180 for deg in planet_degrees]

    # Set up category colors
    category_colors = {
        "Luminaries": "gold",
        "Personal Planets": "crimson",
        "Social Planets": "royalblue",
        "Outer Planets": "darkviolet"
    }

    colors = [category_colors[cat] for cat in planet_categories]

    # Plot planets
    ax.scatter(radians, [1] * len(radians), s=200, c=colors, alpha=0.8, zorder=3)

    # Add planet labels
    for i, (rad, name) in enumerate(zip(radians, planet_names)):
        ax.annotate(name,
                   xy=(rad, 1),
                   xytext=(rad, 1.1),
                   horizontalalignment='center',
                   verticalalignment='center',
                   fontsize=9)

    # Add zodiac signs (in the traditional order)
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

    for i, sign in enumerate(signs):
        # Calculate angle for this sign (center of the 30° slice)
        angle_rad = (360 - (i * 30 + 15)) * np.pi / 180
        ax.annotate(sign,
                   xy=(angle_rad, 1.5),
                   xytext=(angle_rad, 1.5),
                   horizontalalignment='center',
                   verticalalignment='center',
                   fontweight='bold',
                   fontsize=10)

    # Draw zodiac sign boundaries
    for i in range(12):
        angle_rad = (360 - i * 30) * np.pi / 180
        ax.plot([angle_rad, angle_rad], [0, 1.7], 'k--', alpha=0.3, zorder=1)

    # Set up chart for polar plot
    # Use standard methods that work with all axes types
    ax.set_ylim(0, 2)  # Set radius limit
    # Hide radial ticks
    ax.tick_params(axis='y', labelleft=False)
    ax.set_xticks(np.pi/180. * (360 - np.array([0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330])))
    ax.set_xticklabels([])  # Hide angular ticks

    # Add title
    plt.title(title, fontsize=14, pad=20)

    # Add legend for categories
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=color, edgecolor='k', label=cat)
                      for cat, color in category_colors.items()]
    ax.legend(handles=legend_elements, loc='upper right')

    # Save figure
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"Planetary visualization saved to {save_path}")
    return save_path

def visualize_chart_comparison(original_chart: Dict[str, Any],
                               rectified_chart: Dict[str, Any],
                               differences: List[Dict[str, Any]]) -> str:
    """Create visualization comparing original and rectified charts"""
    # Create figure directory if it doesn't exist
    fig_dir = os.path.join(os.getcwd(), 'tests', 'results', 'figures')
    os.makedirs(fig_dir, exist_ok=True)

    # Create figure filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(fig_dir, f'chart_comparison_{timestamp}.png')

    # Create a figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 9), subplot_kw={'projection': 'polar'})

    # Helper function to plot a single chart
    def plot_chart(ax, chart_data, title):
        # Convert planet data to degrees for plotting
        planet_names = []
        planet_degrees = []

        for planet in chart_data.get("planets", []):
            name = planet.get("name")
            if not name:
                continue

            # Get position in degrees (0-360)
            sign_num = planet.get("sign_num", 0)
            degree = planet.get("degree", 0)
            position_deg = (sign_num - 1) * 30 + degree

            planet_names.append(name)
            planet_degrees.append(position_deg)

        # Convert degrees to radians for polar plot (and reverse direction)
        radians = [(360 - deg) * np.pi / 180 for deg in planet_degrees]

        # Plot planets
        ax.scatter(radians, [1] * len(radians), s=200, c='blue', alpha=0.7, zorder=3)

        # Add planet labels
        for i, (rad, name) in enumerate(zip(radians, planet_names)):
            ax.annotate(name,
                       xy=(rad, 1),
                       xytext=(rad, 1.1),
                       horizontalalignment='center',
                       verticalalignment='center',
                       fontsize=9)

        # Add zodiac signs (in the traditional order)
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        for i, sign in enumerate(signs):
            # Calculate angle for this sign (center of the 30° slice)
            angle_rad = (360 - (i * 30 + 15)) * np.pi / 180
            ax.annotate(sign,
                       xy=(angle_rad, 1.5),
                       xytext=(angle_rad, 1.5),
                       horizontalalignment='center',
                       verticalalignment='center',
                       fontweight='bold',
                       fontsize=9)

        # Draw zodiac sign boundaries
        for i in range(12):
            angle_rad = (360 - i * 30) * np.pi / 180
            ax.plot([angle_rad, angle_rad], [0, 1.7], 'k--', alpha=0.3, zorder=1)

        # Set up chart
        ax.set_rmax(2)
        ax.set_rticks([])  # Hide radial ticks
        ax.set_xticks(np.pi/180. * (360 - np.array([0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330])))
        ax.set_xticklabels([])  # Hide angular ticks

        # Add title
        ax.set_title(title, fontsize=12, pad=20)

    # Plot each chart
    original_time = original_chart.get("birth_details", {}).get("birth_time", "Unknown")
    rectified_time = rectified_chart.get("birth_details", {}).get("birth_time", "Unknown")

    plot_chart(ax1, original_chart, f"Original Chart ({original_time})")
    plot_chart(ax2, rectified_chart, f"Rectified Chart ({rectified_time})")

    # Add a note about the differences
    if differences:
        most_significant = max(differences, key=lambda d: d.get("significance", 0))
        fig.suptitle(f"Chart Comparison\nMost significant change: {most_significant.get('description', 'Unknown')}",
                    fontsize=14)
    else:
        fig.suptitle("Chart Comparison\nNo significant differences detected", fontsize=14)

    # Save the chart and return filename
    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"Chart comparison visualization saved to {filename}")
    return filename

def test_utils_simple():
    """Simple test to verify utils test discovery."""
    assert True
