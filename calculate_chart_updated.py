#!/usr/bin/env python3
from datetime import datetime
from ai_service.utils.astro_calculator import AstroCalculator, WHOLE_SIGN
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)

def main():
    # Initialize calculator
    calculator = AstroCalculator()

    # Try to set ayanamsa to match PDF (23.6647)
    # Note: We'll use AstroCalculator to handle this rather than direct swisseph calls
    # which may not be available or compatible
    print("Using Lahiri ayanamsa (standard in Indian astrology)")

    # Format birth data
    birth_date = datetime.strptime('1985-10-24 14:30:00', '%Y-%m-%d %H:%M:%S')
    latitude = 18.5204
    longitude = 73.8567

    print(f"Calculating chart for: {birth_date} at coordinates: {latitude}, {longitude}")
    print(f"Using whole sign house system")

    # Calculate chart with whole sign houses
    chart_data = calculator.calculate_chart(birth_date, latitude, longitude, house_system=WHOLE_SIGN)

    # Pretty print chart data
    print(json.dumps(chart_data, indent=2))

    # Print a more readable summary
    print("\n\n========== CHART SUMMARY ==========")
    print(f"Ascendant: {chart_data['ascendant']['sign']} {chart_data['ascendant']['degree']:.2f}°")
    print(f"Midheaven: {chart_data.get('midheaven', {}).get('sign', 'N/A')} {chart_data.get('midheaven', {}).get('degree', 0):.2f}°")

    print("\nPlanetary Positions:")
    for planet in chart_data['planets']:
        retrograde = " (R)" if planet.get('retrograde') else ""
        print(f"{planet['name']}: {planet['sign']} {planet['degree']:.2f}° - House {planet['house']}{retrograde}")

    print("\nHouse Cusps:")
    for house in chart_data['houses']:
        print(f"House {house['number']}: {house['sign']} {house['degree']:.2f}°")

if __name__ == "__main__":
    main()
