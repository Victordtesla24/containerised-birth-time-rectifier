#!/usr/bin/env python3
"""
Fixed test for the chart generation endpoint on the AI service.
With parameters matching the chart_service_calculation.py requirements.
"""

import asyncio
import httpx
import json
import time

async def test_direct_chart_generation():
    """
    Test the chart generation endpoint directly on the AI service.
    Using parameters that match the actual service requirements.
    """
    print("Testing chart generation with correct parameters")

    # Use birth data formatted according to the service requirements
    chart_request = {
        "birth_details": {
            "birth_date": "1990-01-15",
            "birth_time": "12:30:00",
            "latitude": 40.7127281,
            "longitude": -74.0060152,
            "timezone": "America/New_York",
            "location": "New York City, NY, USA",
            "house_system": "P"
            # No zodiac_type parameter
        },
        "verify_with_openai": False,
        "session_id": None,
        "generate_visualization": False
    }

    print("Request payload:")
    print(json.dumps(chart_request, indent=2))

    url = "http://localhost:8000/api/v1/charts/generate"

    start_time = time.time()
    print(f"Starting request to {url}")

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.post(
                url,
                json=chart_request,
                headers={"Content-Type": "application/json"}
            )

            elapsed = time.time() - start_time
            print(f"Response received in {elapsed:.2f} seconds")
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                chart_data = response.json()
                print("Chart generated successfully!")
                print(f"Chart ID: {chart_data.get('chart_id')}")

                # Print basic chart information if available
                if "chart_data" in chart_data and chart_data["chart_data"]:
                    planets = chart_data.get("chart_data", {}).get("planets", [])
                    if planets:
                        print("\nPlanets:")
                        for planet in list(planets.items())[:3]:  # Show only first 3 planets for brevity
                            planet_name, planet_data = planet
                            print(f"  {planet_name}: {planet_data.get('sign')} {planet_data.get('degrees')}°")
                return chart_data
            else:
                print(f"Error response ({response.status_code}):")
                print(response.text[:1000])
                return None
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Error after {elapsed:.2f} seconds: {e}")
        return None

async def main():
    """Run the test."""
    await test_direct_chart_generation()

if __name__ == "__main__":
    asyncio.run(main())
