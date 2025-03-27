#!/usr/bin/env python3
"""
Test script for birth chart generation.
"""

import asyncio
import httpx
import json
import time

async def test_birth_chart_generation():
    """
    Test the process of generating a birth chart:
    1. Initialize a session
    2. Geocode a location
    3. Generate a birth chart
    4. Verify the chart data is correct
    """
    print("Testing birth chart generation")

    # First, initialize a session
    print("\n1. Initializing session...")
    session_id = None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:3001/api/session/init")
            if response.status_code == 200:
                data = response.json()
                session_id = data.get("session_id")
                print(f"Session initialized with ID: {session_id}")
            else:
                print(f"Error initializing session: {response.status_code}")
                print(response.text)
                return
    except Exception as e:
        print(f"Error initializing session: {e}")
        return

    # Next, geocode a location
    print("\n2. Geocoding location...")
    location_data = None

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.post(
                "http://localhost:3001/api/geocode",
                json={"query": "New York City"},
                headers={
                    "Content-Type": "application/json",
                    "X-Session-ID": session_id
                }
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    location_data = results[0]
                    print(f"Location geocoded: {location_data.get('address')}")
                    print(f"Coordinates: {location_data.get('latitude')}, {location_data.get('longitude')}")
                    print(f"Timezone: {location_data.get('timezone', {}).get('timezone_id')}")
                else:
                    print("No geocode results found")
                    return
            else:
                print(f"Error geocoding location: {response.status_code}")
                print(response.text)
                return
    except Exception as e:
        print(f"Error geocoding location: {e}")
        return

    # Now, create a birth chart
    print("\n3. Generating birth chart...")

    # Format the request according to the API requirements
    chart_request = {
        "birth_details": {
            "birth_date": "1990-01-15",
            "birth_time": "12:30:00",
            "latitude": location_data.get("latitude"),
            "longitude": location_data.get("longitude"),
            "timezone": location_data.get("timezone", {}).get("timezone_id", "UTC"),
            "location": location_data.get("address"),
            "house_system": "P"
        },
        "verify_with_openai": False,
        "session_id": session_id,
        "generate_visualization": False
    }

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/charts/generate",
                json=chart_request,
                headers={
                    "Content-Type": "application/json",
                    "X-Session-ID": session_id
                }
            )

            if response.status_code == 200:
                chart_data = response.json()

                print("Birth chart generated successfully!")
                print(f"Chart ID: {chart_data.get('chart_id')}")

                # Print basic chart information
                planets = chart_data.get("chart_data", {}).get("planets", [])
                houses = chart_data.get("chart_data", {}).get("houses", [])

                if planets:
                    print("\nPlanets:")
                    for planet in planets[:3]:  # Show only first 3 planets for brevity
                        print(f"  {planet.get('name')}: {planet.get('sign')} {planet.get('degrees')}°")

                if houses:
                    print("\nHouses:")
                    for house in houses[:3]:  # Show only first 3 houses for brevity
                        print(f"  House {house.get('house')}: {house.get('sign')} {house.get('degrees')}°")

                # Return the chart data for potential further use
                return chart_data
            else:
                print(f"Error generating birth chart: {response.status_code}")
                print(response.text)
                return None
    except Exception as e:
        print(f"Error generating birth chart: {e}")
        return None

async def main():
    """Run the test."""
    await test_birth_chart_generation()

if __name__ == "__main__":
    asyncio.run(main())
