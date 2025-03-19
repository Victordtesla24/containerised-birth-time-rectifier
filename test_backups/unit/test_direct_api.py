#!/usr/bin/env python3
import asyncio
import aiohttp
import json

# Test data
TEST_DATA = {
    'birthDate': '1990-01-15',
    'birthTime': '14:30',
    'birthLocation': 'New Delhi, India',
    'latitude': 28.6139,
    'longitude': 77.2090,
    'timezone': 'Asia/Kolkata'
}

async def test_api_formats():
    """Test different request formats for chart generation API"""
    async with aiohttp.ClientSession() as session:
        # Format 1: Standard nested format
        data1 = {
            "birth_details": {
                "birth_date": TEST_DATA["birthDate"],
                "birth_time": TEST_DATA["birthTime"],
                "location": TEST_DATA["birthLocation"],
                "latitude": TEST_DATA["latitude"],
                "longitude": TEST_DATA["longitude"],
                "timezone": TEST_DATA["timezone"]
            },
            "options": {
                "house_system": "W",
                "verify_with_openai": True
            },
            "session_id": "test-session-1"
        }

        # Format 2: Alternative field names
        data2 = {
            "birth_details": {
                "date": TEST_DATA["birthDate"],
                "time": TEST_DATA["birthTime"],
                "location": TEST_DATA["birthLocation"],
                "latitude": TEST_DATA["latitude"],
                "longitude": TEST_DATA["longitude"],
                "tz": TEST_DATA["timezone"]
            },
            "options": {
                "house_system": "W",
                "verify_with_openai": True
            },
            "session_id": "test-session-2"
        }

        # Format 3: Dual field names
        data3 = {
            "birth_details": {
                "birth_date": TEST_DATA["birthDate"],
                "date": TEST_DATA["birthDate"],
                "birth_time": TEST_DATA["birthTime"],
                "time": TEST_DATA["birthTime"],
                "location": TEST_DATA["birthLocation"],
                "latitude": TEST_DATA["latitude"],
                "longitude": TEST_DATA["longitude"],
                "timezone": TEST_DATA["timezone"],
                "tz": TEST_DATA["timezone"]
            },
            "options": {
                "house_system": "W",
                "verify_with_openai": True
            },
            "session_id": "test-session-3"
        }

        # Format 4: No nesting
        data4 = {
            "birth_date": TEST_DATA["birthDate"],
            "birth_time": TEST_DATA["birthTime"],
            "location": TEST_DATA["birthLocation"],
            "latitude": TEST_DATA["latitude"],
            "longitude": TEST_DATA["longitude"],
            "timezone": TEST_DATA["timezone"],
            "options": {
                "house_system": "W",
                "verify_with_openai": True
            },
            "session_id": "test-session-4"
        }

        # Try with direct AI service
        url = "http://localhost:8000/api/v1/chart/generate"

        print(f"\n*** Testing Direct AI Service at {url} ***")
        await _test_endpoint(session, url, data1, "Standard nested format")
        await _test_endpoint(session, url, data2, "Alternative field names")
        await _test_endpoint(session, url, data3, "Dual field names")
        await _test_endpoint(session, url, data4, "No nesting")

        # Try with API Gateway
        url = "http://localhost:9000/api/v1/chart/generate"

        print(f"\n*** Testing API Gateway at {url} ***")
        await _test_endpoint(session, url, data1, "Standard nested format")
        await _test_endpoint(session, url, data2, "Alternative field names")
        await _test_endpoint(session, url, data3, "Dual field names")
        await _test_endpoint(session, url, data4, "No nesting")

async def _test_endpoint(session, url, data, description):
    """Test an endpoint with the given data"""
    try:
        print(f"\nTesting {description}:")
        print(f"Request: {json.dumps(data, indent=2)}")

        async with session.post(url, json=data) as response:
            status = response.status
            response_text = await response.text()

            print(f"Status: {status}")
            try:
                response_json = json.loads(response_text)
                print(f"Response: {json.dumps(response_json, indent=2)}")
            except:
                print(f"Response: {response_text}")

            if status == 200:
                print("✅ SUCCESS")
            else:
                print("❌ FAILED")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_formats())
