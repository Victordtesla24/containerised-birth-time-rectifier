#!/usr/bin/env python3
"""
Direct test for Nominatim API without any intermediaries.
"""

import asyncio
import aiohttp
import json
import time

async def direct_nominatim_test(query: str):
    """
    Test Nominatim API directly with aiohttp.

    Args:
        query: The location to geocode
    """
    print(f"Testing direct Nominatim API for query: {query}")

    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 1
    }
    headers = {
        "User-Agent": "birth-time-rectifier-test/1.0"
    }

    start_time = time.time()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=10) as response:
                elapsed = time.time() - start_time
                print(f"Response received in {elapsed:.2f} seconds")
                print(f"Status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    print(f"Found {len(data)} results")
                    if data:
                        print(f"First result: {json.dumps(data[0], indent=2)}")
                    else:
                        print("No results found")
                else:
                    text = await response.text()
                    print(f"Error response: {text[:200]}")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Error after {elapsed:.2f} seconds: {e}")

async def main():
    """Run the test."""
    await direct_nominatim_test("New York City")

if __name__ == "__main__":
    asyncio.run(main())
