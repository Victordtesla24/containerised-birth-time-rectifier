#!/usr/bin/env python3
"""
Direct test for the API Gateway simple geocode endpoint.
"""

import asyncio
import httpx
import json
import time

async def test_api_gateway_simple_geocode():
    """
    Test the API Gateway simple geocode endpoint directly.
    """
    print("Testing API Gateway simple geocode endpoint")

    url = "http://localhost:3000/api/geocode/simple"

    start_time = time.time()
    print(f"Starting request at {start_time}")

    try:
        # Use a client with timeout
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            print(f"Sending request to {url}")

            response = await client.post(url)

            elapsed = time.time() - start_time
            print(f"Response received in {elapsed:.2f} seconds")
            print(f"Status: {response.status_code}")

            print(f"Response: {response.text[:500]}")
    except httpx.TimeoutException:
        elapsed = time.time() - start_time
        print(f"Timeout after {elapsed:.2f} seconds")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Error after {elapsed:.2f} seconds: {e}")

async def main():
    """Run the test."""
    await test_api_gateway_simple_geocode()

if __name__ == "__main__":
    asyncio.run(main())
