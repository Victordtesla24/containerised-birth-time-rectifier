#!/usr/bin/env python3
"""
Test script for chart visualization

This script demonstrates the chart visualization capabilities
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from birth_time_rectifier.chart_visualizer import generate_multiple_charts, render_vedic_square_chart

def main():
    """Main function to test chart visualization"""
    # Sample test data representing a Vedic astrological chart
    sample_chart = {
        "ascendant": {"sign": "Taurus", "sign_num": 2, "degree": 15.5},
        "planets": [
            {"name": "Sun", "sign": "Aries", "sign_num": 1, "degree": 10.2, "house": 12, "is_retrograde": False},
            {"name": "Moon", "sign": "Gemini", "sign_num": 3, "degree": 25.8, "house": 2, "is_retrograde": False},
            {"name": "Mercury", "sign": "Pisces", "sign_num": 12, "degree": 5.3, "house": 11, "is_retrograde": True},
            {"name": "Venus", "sign": "Taurus", "sign_num": 2, "degree": 18.7, "house": 1, "is_retrograde": False},
            {"name": "Mars", "sign": "Cancer", "sign_num": 4, "degree": 9.1, "house": 3, "is_retrograde": False},
            {"name": "Jupiter", "sign": "Libra", "sign_num": 7, "degree": 28.4, "house": 6, "is_retrograde": False},
            {"name": "Saturn", "sign": "Capricorn", "sign_num": 10, "degree": 12.6, "house": 9, "is_retrograde": True},
            {"name": "Rahu", "sign": "Virgo", "sign_num": 6, "degree": 3.8, "house": 5, "is_retrograde": False},
            {"name": "Ketu", "sign": "Pisces", "sign_num": 12, "degree": 3.8, "house": 11, "is_retrograde": False}
        ],
        "houses": [
            {"number": 1, "sign": "Taurus", "sign_num": 2},
            {"number": 2, "sign": "Gemini", "sign_num": 3},
            {"number": 3, "sign": "Cancer", "sign_num": 4},
            {"number": 4, "sign": "Leo", "sign_num": 5},
            {"number": 5, "sign": "Virgo", "sign_num": 6},
            {"number": 6, "sign": "Libra", "sign_num": 7},
            {"number": 7, "sign": "Scorpio", "sign_num": 8},
            {"number": 8, "sign": "Sagittarius", "sign_num": 9},
            {"number": 9, "sign": "Capricorn", "sign_num": 10},
            {"number": 10, "sign": "Aquarius", "sign_num": 11},
            {"number": 11, "sign": "Pisces", "sign_num": 12},
            {"number": 12, "sign": "Aries", "sign_num": 1}
        ]
    }

    # Create a slight variation for a "rectified" chart
    rectified_chart = json.loads(json.dumps(sample_chart))  # Deep copy via JSON
    rectified_chart["ascendant"]["degree"] = 18.7  # Change the ascendant degree

    # Move the Moon to a different house
    for planet in rectified_chart["planets"]:
        if planet["name"] == "Moon":
            planet["sign"] = "Cancer"
            planet["sign_num"] = 4
            planet["house"] = 3
            planet["degree"] = 2.5

    print("\n" + "=" * 80)
    print("VEDIC CHART VISUALIZATION DEMONSTRATION".center(80))
    print("=" * 80)

    # Generate and display the single Lagna chart
    print("\nLAGNA (BIRTH) CHART")
    print("-" * 80)
    lagna_chart = render_vedic_square_chart(sample_chart, "Lagna Chart")
    print(lagna_chart)

    # Generate and display all chart types for the original chart
    print("\n" + "=" * 80)
    print("ORIGINAL CHART - MULTIPLE FORMATS".center(80))
    print("=" * 80)
    original_charts = generate_multiple_charts(sample_chart)
    for chart_type, chart_display in original_charts.items():
        print(f"\n{'-' * 80}\n{chart_type.upper()} CHART\n{'-' * 80}")
        print(chart_display)

    # Generate and display all chart types for the rectified chart
    print("\n" + "=" * 80)
    print("RECTIFIED CHART - MULTIPLE FORMATS".center(80))
    print("=" * 80)
    rectified_charts = generate_multiple_charts(rectified_chart)
    for chart_type, chart_display in rectified_charts.items():
        print(f"\n{'-' * 80}\n{chart_type.upper()} CHART\n{'-' * 80}")
        print(chart_display)

if __name__ == "__main__":
    main()
