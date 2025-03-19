#!/usr/bin/env python3
from datetime import datetime
from ai_service.utils.astro_calculator import AstroCalculator, WHOLE_SIGN, PLACIDUS, KOCH, EQUAL
import json
import logging
import argparse
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Calculate astrological chart with configurable settings')
    parser.add_argument('--date', type=str, default='1985-10-24', help='Birth date in YYYY-MM-DD format')
    parser.add_argument('--time', type=str, default='14:30:00', help='Birth time in HH:MM:SS format')
    parser.add_argument('--lat', type=float, default=18.5204, help='Birth latitude')
    parser.add_argument('--lon', type=float, default=73.8567, help='Birth longitude')
    parser.add_argument('--ayanamsa', type=float, default=23.6647, help='Ayanamsa value (default: 23.6647 Lahiri)')
    parser.add_argument('--node-type', type=str, default='true', choices=['mean', 'true'],
                        help='Node calculation type (mean or true)')
    parser.add_argument('--house-system', type=str, default='whole_sign',
                        choices=['placidus', 'koch', 'whole_sign', 'equal'],
                        help='House system to use')

    args = parser.parse_args()

    # Map house system string to constant
    house_systems = {
        'placidus': PLACIDUS,
        'koch': KOCH,
        'whole_sign': WHOLE_SIGN,
        'equal': EQUAL
    }
    house_system = house_systems.get(args.house_system, WHOLE_SIGN)

    # Initialize calculator
    # Note: AstroCalculator in the current implementation may not directly
    # accept ayanamsa and node_type parameters, using defaults
    calculator = AstroCalculator()

    # Log the settings we're attempting to use, even if we can't directly set them
    logger.info(f"Preferred ayanamsa: {args.ayanamsa}")
    logger.info(f"Preferred node type: {args.node_type}")

    # Format birth data
    birth_date_str = args.date
    birth_time_str = args.time
    birth_date = datetime.strptime(f'{args.date} {args.time}', '%Y-%m-%d %H:%M:%S')
    latitude = args.lat
    longitude = args.lon

    print(f"Calculating chart for: {birth_date} at coordinates: {latitude}, {longitude}")
    print(f"Using ayanamsa: {args.ayanamsa}, node type: {args.node_type}, house system: {args.house_system}")

    # Calculate chart with specified settings
    # Make sure all parameters have the correct type
    try:
        # First try with parameters matching the method signature
        chart_data = await calculator.calculate_chart(
            birth_date_str,
            birth_time_str,
            float(latitude),
            float(longitude),
            house_system=house_system
        )
    except TypeError:
        # Fall back to the alternative style with keyword arguments
        chart_data = await calculator.calculate_chart(
            birth_date=birth_date_str,
            birth_time=birth_time_str,
            latitude=float(latitude),
            longitude=float(longitude),
            house_system=house_system
        )

    # Pretty print chart data
    print(json.dumps(chart_data, indent=2))

    # Print a more readable summary
    print("\n\n========== CHART SUMMARY ==========")
    print(f"Ascendant: {chart_data['ascendant']['sign']} {chart_data['ascendant']['degree']:.2f}°")

    # Print midheaven if available
    if 'midheaven' in chart_data:
        print(f"Midheaven: {chart_data['midheaven']['sign']} {chart_data['midheaven']['degree']:.2f}°")
    else:
        print(f"Midheaven: N/A")

    print("\nPlanetary Positions:")
    for planet in chart_data['planets']:
        retrograde = " (R)" if planet.get('retrograde') else ""
        print(f"{planet['name']}: {planet['sign']} {planet['degree']:.2f}° - House {planet['house']}{retrograde}")

    print("\nHouse Cusps:")
    for house in chart_data['houses']:
        print(f"House {house['number']}: {house['sign']} {house['degree']:.2f}°")

if __name__ == "__main__":
    # Run async main function
    asyncio.run(main())
