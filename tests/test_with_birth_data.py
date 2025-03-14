#!/usr/bin/env python3
"""
Test script to generate charts with specific birth data.

This script uses the provided birth data to generate and display charts.
"""

import json
import os
from datetime import datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from birth_time_rectifier.chart_visualizer import generate_multiple_charts, render_vedic_chart

def create_sample_chart_for_birth_data():
    """
    Create a sample chart for the specified birth data:
    Date: 1985-10-24
    Time: 14:30
    Place: Pune, India

    Returns:
        Dictionary containing chart data
    """
    # This is a sample chart data - in a real application, this would be calculated
    # based on the birth details, but for this test we're using simulated data
    # that approximately matches what might be expected for someone born in
    # Pune, India on October 24, 1985 at 14:30

    chart_data = {
        "ascendant": {"sign": "Libra", "sign_num": 7, "degree": 15.8},
        "planets": [
            {"name": "Sun", "sign": "Libra", "sign_num": 7, "degree": 7.2, "house": 1, "is_retrograde": False},
            {"name": "Moon", "sign": "Virgo", "sign_num": 6, "degree": 12.5, "house": 12, "is_retrograde": False},
            {"name": "Mars", "sign": "Gemini", "sign_num": 3, "degree": 28.3, "house": 9, "is_retrograde": False},
            {"name": "Mercury", "sign": "Libra", "sign_num": 7, "degree": 15.4, "house": 1, "is_retrograde": False},
            {"name": "Jupiter", "sign": "Aquarius", "sign_num": 11, "degree": 5.7, "house": 5, "is_retrograde": False},
            {"name": "Venus", "sign": "Scorpio", "sign_num": 8, "degree": 10.2, "house": 2, "is_retrograde": False},
            {"name": "Saturn", "sign": "Scorpio", "sign_num": 8, "degree": 25.8, "house": 2, "is_retrograde": True},
            {"name": "Rahu", "sign": "Taurus", "sign_num": 2, "degree": 3.1, "house": 8, "is_retrograde": False},
            {"name": "Ketu", "sign": "Scorpio", "sign_num": 8, "degree": 3.1, "house": 2, "is_retrograde": False}
        ],
        "houses": [
            {"number": 1, "sign": "Libra", "sign_num": 7},
            {"number": 2, "sign": "Scorpio", "sign_num": 8},
            {"number": 3, "sign": "Sagittarius", "sign_num": 9},
            {"number": 4, "sign": "Capricorn", "sign_num": 10},
            {"number": 5, "sign": "Aquarius", "sign_num": 11},
            {"number": 6, "sign": "Pisces", "sign_num": 12},
            {"number": 7, "sign": "Aries", "sign_num": 1},
            {"number": 8, "sign": "Taurus", "sign_num": 2},
            {"number": 9, "sign": "Gemini", "sign_num": 3},
            {"number": 10, "sign": "Cancer", "sign_num": 4},
            {"number": 11, "sign": "Leo", "sign_num": 5},
            {"number": 12, "sign": "Virgo", "sign_num": 6}
        ]
    }

    return chart_data

def main():
    """Test with specific birth data."""
    print("=" * 80)
    print("BIRTH TIME RECTIFIER TEST".center(80))
    print("=" * 80)
    print("\nUsing birth data:")
    print("  Date: 1985-10-24")
    print("  Time: 14:30")
    print("  Place: Pune, India")
    print("=" * 80)

    # Create chart data for our test birth information
    chart_data = create_sample_chart_for_birth_data()

    # Generate all chart types
    charts = generate_multiple_charts(chart_data)

    # Display each chart type
    for chart_type, chart_display in charts.items():
        print(f"\n{'-' * 80}")
        print(f"{chart_type.upper()} CHART".center(80))
        print(f"{'-' * 80}")
        print(chart_display)

    # Export the charts to files
    export_path = "chart_exports/test_birth_data"
    os.makedirs(export_path, exist_ok=True)

    # Export each chart to a file
    for chart_type, chart_display in charts.items():
        with open(f"{export_path}/{chart_type}_chart.txt", "w") as f:
            f.write(chart_display)

    print("\nCharts exported to:", export_path)

if __name__ == "__main__":
    main()
