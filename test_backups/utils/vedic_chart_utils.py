"""
Utilities for rendering and manipulating Vedic astrological charts.
Provides visualization and comparison functions for birth charts.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple
import datetime

logger = logging.getLogger(__name__)

# ASCII art symbols for planets and signs
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
    "Uranus": "♅",
    "Neptune": "♆",
    "Pluto": "♇",
    "Ascendant": "AC",
    "Midheaven": "MC"
}

SIGN_SYMBOLS = {
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

# Terminal color codes
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

def render_vedic_square_chart(chart_data: Dict[str, Any], title: str = "Vedic Birth Chart") -> str:
    """
    Render a Vedic square chart as ASCII art based on chart data.
    Returns a string representation of the chart.
    """
    # Extract planets data - handle both dictionary and list formats
    planets_data = chart_data.get("planets", {})

    # Convert planets dictionary to list if needed
    planets = []
    if isinstance(planets_data, dict):
        # New format: dictionary with lowercase keys
        for planet_key, planet_data in planets_data.items():
            # Add name if not present
            if "name" not in planet_data and planet_key:
                planet_data = planet_data.copy()  # Create a copy to avoid modifying the original
                planet_data["name"] = planet_key.capitalize()
            planets.append(planet_data)
    else:
        # Old format: already a list
        planets = planets_data

    houses = chart_data.get("houses", [])

    # Get ascendant sign number
    ascendant_sign_num = 1  # Default to Aries

    # Try to get from ascendant in chart data
    if "ascendant" in chart_data:
        ascendant_data = chart_data["ascendant"]
        if "sign_num" in ascendant_data:
            ascendant_sign_num = ascendant_data["sign_num"]
        elif "sign" in ascendant_data:
            # Convert sign name to number
            sign_names = list(SIGN_SYMBOLS.keys())
            try:
                ascendant_sign_num = sign_names.index(ascendant_data["sign"]) + 1
            except ValueError:
                pass  # Keep default if sign name not found

    # Fall back to looking in planets list
    if ascendant_sign_num == 1:
        for planet in planets:
            if planet.get("name") == "Ascendant":
                ascendant_sign_num = planet.get("sign_num", 1)
                break

    # Map planets to houses
    house_contents = {i: [] for i in range(1, 13)}

    for planet in planets:
        name = planet.get("name")
        sign_num = planet.get("sign_num", 0)
        degree = planet.get("degree", 0)

        # Calculate house number based on ascendant
        house_num = ((sign_num - ascendant_sign_num) % 12) + 1

        # Add planet to house
        symbol = PLANET_SYMBOLS.get(name, name[:2])
        house_contents[house_num].append({
            "name": name,
            "symbol": symbol,
            "degree": degree,
            "sign_num": sign_num
        })

    # Determine sign for each house
    house_signs = {}
    for i in range(1, 13):
        sign_num = ((ascendant_sign_num + i - 1) % 12)
        if sign_num == 0:
            sign_num = 12

        # Convert sign number to sign name
        sign_names = list(SIGN_SYMBOLS.keys())
        sign_name = sign_names[sign_num - 1]
        house_signs[i] = {
            "name": sign_name,
            "symbol": SIGN_SYMBOLS[sign_name]
        }

    # Create ASCII chart (South Indian style - square)
    chart = []

    # Add title
    chart.append(f"\n{TermColors.BOLD}{TermColors.CYAN}*** {title} ***{TermColors.ENDC}\n")

    # Top row - houses 10, 11, 12, 1
    row1 = "┌─────────────┬─────────────┬─────────────┬─────────────┐"
    chart.append(row1)

    house_row1 = f"│ {format_house_label(10, house_signs)} │ {format_house_label(11, house_signs)} │ {format_house_label(12, house_signs)} │ {format_house_label(1, house_signs)} │"
    chart.append(house_row1)

    content_row1a = f"│ {format_house_content(house_contents[10], 0, 2)} │ {format_house_content(house_contents[11], 0, 2)} │ {format_house_content(house_contents[12], 0, 2)} │ {format_house_content(house_contents[1], 0, 2)} │"
    chart.append(content_row1a)

    content_row1b = f"│ {format_house_content(house_contents[10], 2, 4)} │ {format_house_content(house_contents[11], 2, 4)} │ {format_house_content(house_contents[12], 2, 4)} │ {format_house_content(house_contents[1], 2, 4)} │"
    chart.append(content_row1b)

    # Divider row
    divider1 = "├─────────────┼─────────────┼─────────────┼─────────────┤"
    chart.append(divider1)

    # Middle - top row - houses 9 and 2
    house_row2 = f"│ {format_house_label(9, house_signs)} │             │             │ {format_house_label(2, house_signs)} │"
    chart.append(house_row2)

    content_row2a = f"│ {format_house_content(house_contents[9], 0, 2)} │             │             │ {format_house_content(house_contents[2], 0, 2)} │"
    chart.append(content_row2a)

    content_row2b = f"│ {format_house_content(house_contents[9], 2, 4)} │   JUPITER   │   SYMBOL    │ {format_house_content(house_contents[2], 2, 4)} │"
    chart.append(content_row2b)

    # Divider row
    divider2 = "├─────────────┤   VEDIC     │   CHART     ├─────────────┤"
    chart.append(divider2)

    # Middle - bottom row - houses 8 and 3
    house_row3 = f"│ {format_house_label(8, house_signs)} │             │             │ {format_house_label(3, house_signs)} │"
    chart.append(house_row3)

    content_row3a = f"│ {format_house_content(house_contents[8], 0, 2)} │             │             │ {format_house_content(house_contents[3], 0, 2)} │"
    chart.append(content_row3a)

    content_row3b = f"│ {format_house_content(house_contents[8], 2, 4)} │             │             │ {format_house_content(house_contents[3], 2, 4)} │"
    chart.append(content_row3b)

    # Divider row
    divider3 = "├─────────────┼─────────────┼─────────────┼─────────────┤"
    chart.append(divider3)

    # Bottom row - houses 7, 6, 5, 4
    house_row4 = f"│ {format_house_label(7, house_signs)} │ {format_house_label(6, house_signs)} │ {format_house_label(5, house_signs)} │ {format_house_label(4, house_signs)} │"
    chart.append(house_row4)

    content_row4a = f"│ {format_house_content(house_contents[7], 0, 2)} │ {format_house_content(house_contents[6], 0, 2)} │ {format_house_content(house_contents[5], 0, 2)} │ {format_house_content(house_contents[4], 0, 2)} │"
    chart.append(content_row4a)

    content_row4b = f"│ {format_house_content(house_contents[7], 2, 4)} │ {format_house_content(house_contents[6], 2, 4)} │ {format_house_content(house_contents[5], 2, 4)} │ {format_house_content(house_contents[4], 2, 4)} │"
    chart.append(content_row4b)

    # Bottom
    bottom = "└─────────────┴─────────────┴─────────────┴─────────────┘"
    chart.append(bottom)

    # Join all rows
    return "\n".join(chart)

def format_house_label(house_num: int, house_signs: Dict[int, Dict[str, str]]) -> str:
    """Format house number and sign for display in chart"""
    sign = house_signs.get(house_num, {})
    sign_symbol = sign.get("symbol", "?")

    house_label = f"{house_num}"
    if house_num == 1:
        house_label = f"{TermColors.BOLD}{TermColors.RED}{house_num}{TermColors.ENDC}"

    return f"{house_label} {sign_symbol}".ljust(11)

def format_house_content(planets: List[Dict[str, Any]], start_idx: int, end_idx: int) -> str:
    """Format planet content for a house segment"""
    content = ""

    # Get slice of planets for this segment
    visible_planets = planets[start_idx:end_idx] if start_idx < len(planets) else []

    # Format each planet
    for i, planet in enumerate(visible_planets):
        symbol = planet["symbol"]
        name = planet["name"]

        # Special formatting for Ascendant
        if name == "Ascendant":
            symbol = f"{TermColors.RED}{TermColors.BOLD}{symbol}{TermColors.ENDC}"

        # Add separation between planets
        if i > 0:
            content += " "

        content += symbol

    # Pad to fill space
    return content.ljust(11)

def format_planetary_position_table(chart_data: Dict[str, Any], title: str = "Planetary Positions") -> str:
    """Create a table of planetary positions from chart data"""
    planets_data = chart_data.get("planets", {})

    # Convert planets dictionary to list if needed
    planets = []
    if isinstance(planets_data, dict):
        # New format: dictionary with lowercase keys
        for planet_key, planet_data in planets_data.items():
            # Add name if not present
            if "name" not in planet_data and planet_key:
                planet_data = planet_data.copy()  # Create a copy to avoid modifying the original
                planet_data["name"] = planet_key.capitalize()
            planets.append(planet_data)
    else:
        # Old format: already a list
        planets = planets_data

    # Sort planets in traditional order
    planet_order = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
                   "Rahu", "Ketu", "Uranus", "Neptune", "Pluto", "Ascendant", "Midheaven"]

    def get_sort_key(planet):
        name = planet.get("name", "").capitalize()
        try:
            return planet_order.index(name)
        except ValueError:
            return 999

    planets_sorted = sorted(planets, key=get_sort_key)

    # Create table
    table = []
    table.append(f"\n{TermColors.BOLD}{TermColors.CYAN}*** {title} ***{TermColors.ENDC}\n")

    # Header
    table.append(f"{TermColors.BOLD}{'Planet':<12} {'Sign':<12} {'Degree':<8} {'House':<6} {'Retrograde':<10}{TermColors.ENDC}")
    table.append("─" * 50)

    # Rows
    for planet in planets_sorted:
        name = planet.get("name", "Unknown")
        symbol = PLANET_SYMBOLS.get(name, name[:2])
        sign_num = planet.get("sign_num", 0)
        degree = planet.get("degree", 0)
        house = planet.get("house", 0)
        is_retrograde = planet.get("is_retrograde", False)

        # Get sign name from sign number
        sign_names = list(SIGN_SYMBOLS.keys())
        if 1 <= sign_num <= 12:
            sign_name = sign_names[sign_num - 1]
            sign_symbol = SIGN_SYMBOLS[sign_name]
        else:
            sign_name = "Unknown"
            sign_symbol = "?"

        # Format degree with minutes
        degree_int = int(degree)
        minutes = int((degree - degree_int) * 60)
        degree_str = f"{degree_int}° {minutes}'"

        # Format retrograde
        retrograde = "R" if is_retrograde else ""

        # Special formatting for Ascendant
        planet_name = f"{symbol} {name}"
        if name == "Ascendant":
            planet_name = f"{TermColors.RED}{TermColors.BOLD}{symbol} {name}{TermColors.ENDC}"

        # Add row
        table.append(f"{planet_name:<12} {sign_symbol} {sign_name:<10} {degree_str:<8} {house:<6} {retrograde:<10}")

    # Join all rows
    return "\n".join(table)

def display_charts_side_by_side(chart1: str, chart2: str) -> str:
    """Combine two charts side by side for comparison"""
    # Split charts into lines
    lines1 = chart1.split("\n")
    lines2 = chart2.split("\n")

    # Ensure both charts have the same number of lines
    max_lines = max(len(lines1), len(lines2))
    lines1 += [""] * (max_lines - len(lines1))
    lines2 += [""] * (max_lines - len(lines2))

    # Combine lines side by side
    combined = []
    for l1, l2 in zip(lines1, lines2):
        combined.append(f"{l1}    {l2}")

    return "\n".join(combined)

def display_verification_summary(chart_data: Dict[str, Any]) -> str:
    """Display a summary of the chart verification results"""
    verification = chart_data.get("verification", {})

    if not verification:
        return f"\n{TermColors.YELLOW}No verification data available for this chart.{TermColors.ENDC}\n"

    status = verification.get("status", "Unknown")
    confidence = verification.get("confidence", 0)
    corrections_applied = verification.get("corrections_applied", False)
    message = verification.get("message", "No verification details available.")

    # Determine color based on status
    if status.lower() == "verified":
        status_color = TermColors.GREEN
    elif status.lower() == "partially_verified":
        status_color = TermColors.YELLOW
    else:
        status_color = TermColors.RED

    # Format the summary
    summary = []
    summary.append(f"\n{TermColors.BOLD}{TermColors.CYAN}*** Chart Verification Summary ***{TermColors.ENDC}\n")

    # Status with color
    summary.append(f"Status: {status_color}{status}{TermColors.ENDC}")

    # Confidence score with color
    conf_color = TermColors.GREEN if confidence >= 80 else TermColors.YELLOW if confidence >= 50 else TermColors.RED
    summary.append(f"Confidence: {conf_color}{confidence}%{TermColors.ENDC}")

    # Corrections
    if corrections_applied:
        summary.append(f"Corrections: {TermColors.YELLOW}Yes - chart has been corrected{TermColors.ENDC}")
    else:
        summary.append(f"Corrections: No - chart accurate as provided")

    # Message
    summary.append(f"\nDetails: {message}")

    return "\n".join(summary)

def prompt_for_questionnaire_answer(question: Dict[str, Any]) -> str:
    """Interactive prompt for user to answer a questionnaire question"""
    text = question.get("text", "")
    qtype = question.get("type", "boolean")

    # Format and display the question
    print(f"\n{TermColors.BOLD}{TermColors.CYAN}Question:{TermColors.ENDC} {text}")

    # Set up prompt based on question type
    if qtype == "boolean":
        print(f"1. {TermColors.GREEN}Yes{TermColors.ENDC}")
        print(f"2. {TermColors.RED}No{TermColors.ENDC}")
        print(f"3. {TermColors.YELLOW}Not sure{TermColors.ENDC}")

        # Get response
        while True:
            try:
                response = input("Enter your choice (1/2/3): ").strip()
                if response == "1" or response.lower() == "yes":
                    return "yes"
                elif response == "2" or response.lower() == "no":
                    return "no"
                elif response == "3" or response.lower() in ["not sure", "unsure"]:
                    return "unsure"
                else:
                    print(f"{TermColors.RED}Invalid choice. Please enter 1, 2, or 3.{TermColors.ENDC}")
            except KeyboardInterrupt:
                print(f"\n{TermColors.YELLOW}Question skipped.{TermColors.ENDC}")
                return "skipped"

    elif qtype == "multiple_choice":
        options = question.get("options", [])
        if not options:
            return prompt_for_text_answer()

        # Display options
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")

        # Get response
        while True:
            try:
                response = input(f"Enter your choice (1-{len(options)}): ").strip()
                try:
                    idx = int(response) - 1
                    if 0 <= idx < len(options):
                        return options[idx]
                    else:
                        print(f"{TermColors.RED}Invalid choice. Please enter a number between 1 and {len(options)}.{TermColors.ENDC}")
                except ValueError:
                    print(f"{TermColors.RED}Invalid choice. Please enter a number.{TermColors.ENDC}")
            except KeyboardInterrupt:
                print(f"\n{TermColors.YELLOW}Question skipped.{TermColors.ENDC}")
                return "skipped"

    elif qtype == "scale":
        min_val = question.get("min_value", 1)
        max_val = question.get("max_value", 10)

        print(f"Enter a value from {min_val} to {max_val}:")
        print(f"{min_val} = Not at all, {max_val} = Very much")

        # Get response
        while True:
            try:
                response = input(f"Your rating ({min_val}-{max_val}): ").strip()
                try:
                    val = int(response)
                    if min_val <= val <= max_val:
                        return str(val)
                    else:
                        print(f"{TermColors.RED}Invalid value. Please enter a number between {min_val} and {max_val}.{TermColors.ENDC}")
                except ValueError:
                    print(f"{TermColors.RED}Invalid value. Please enter a number.{TermColors.ENDC}")
            except KeyboardInterrupt:
                print(f"\n{TermColors.YELLOW}Question skipped.{TermColors.ENDC}")
                return "skipped"

    else:  # Default to text input
        return prompt_for_text_answer()

def prompt_for_text_answer() -> str:
    """Get a free-text answer from the user"""
    try:
        response = input("Your answer: ").strip()
        return response
    except KeyboardInterrupt:
        print(f"\n{TermColors.YELLOW}Question skipped.{TermColors.ENDC}")
        return "skipped"
