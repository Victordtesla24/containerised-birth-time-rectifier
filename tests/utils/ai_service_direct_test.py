#!/usr/bin/env python3
"""
Direct test for the AI service geocode endpoint using httpx.
"""

import asyncio
import httpx
import json
import time

async def test_ai_service_geocode(query: str = "New York City"):
    """
    Test the AI service geocode endpoint directly.

    Args:
        query: The location to geocode
    """
    print(f"Testing AI service geocode endpoint for query: {query}")

    url = "http://localhost:8000/api/v1/geocode"

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.post(
                url,
                json={"query": query, "limit": 1, "exactly_one": False},
                headers={"Content-Type": "application/json"}
            )

            elapsed = time.time() - start_time
            print(f"Response received in {elapsed:.2f} seconds")
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Status: {data.get('status')}")
                print(f"Total results: {data.get('total', 0)}")
                results = data.get("results", [])
                if results:
                    first_result = results[0]
                    print(f"First result:")
                    print(f"  Address: {first_result.get('address')}")
                    print(f"  Coordinates: {first_result.get('latitude')}, {first_result.get('longitude')}")
                    print(f"  Provider: {first_result.get('provider')}")
                else:
                    print("No results found")
            else:
                print(f"Error response: {response.text[:200]}")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Error after {elapsed:.2f} seconds: {e}")

async def main():
    """Run the test."""
    await test_ai_service_geocode()

if __name__ == "__main__":
    asyncio.run(main())
