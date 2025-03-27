#!/usr/bin/env python3
"""
Direct test for the API Gateway geocode endpoint using httpx.
"""

import asyncio
import httpx
import json
import time
import sys

# Add more verbose logging for httpx
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

async def test_api_gateway_geocode(query: str = "New York City"):
    """
    Test the API Gateway geocode endpoint directly.

    Args:
        query: The location to geocode
    """
    print(f"Testing API Gateway geocode endpoint for query: {query}")

    url = "http://localhost:3000/api/geocode"

    # First, let's get a session ID
    print("Getting session ID...")
    session_id = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:3000/api/session/init")
            if response.status_code == 200:
                data = response.json()
                session_id = data.get("session_id")
                print(f"Got session ID: {session_id}")
            else:
                print(f"Failed to get session ID: {response.status_code}")
                print(response.text)
    except Exception as e:
        print(f"Error getting session ID: {e}")

    start_time = time.time()
    print(f"Starting geocode request at {start_time}")

    try:
        # Use a client with more generous timeout
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            headers = {"Content-Type": "application/json"}
            if session_id:
                headers["X-Session-ID"] = session_id

            print(f"Sending request to {url} with headers: {headers}")

            response = await client.post(
                url,
                json={"query": query, "limit": 1, "exactly_one": False},
                headers=headers
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
    except httpx.TimeoutException:
        elapsed = time.time() - start_time
        print(f"Timeout after {elapsed:.2f} seconds")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Error after {elapsed:.2f} seconds: {e}")

async def main():
    """Run the test."""
    await test_api_gateway_geocode()

if __name__ == "__main__":
    asyncio.run(main())
