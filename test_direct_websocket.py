import asyncio
import websockets
import json

async def test_websocket():
    # Connect directly to the AI service WebSocket
    uri = 'ws://localhost:8001/ws/test-direct-websocket-session'

    # Try different header combinations to see which one works
    header_sets = [
        {
            "name": "Basic",
            "headers": {
                "X-Session-ID": "test-direct-websocket-session"
            }
        },
        {
            "name": "With Origin",
            "headers": {
                "X-Session-ID": "test-direct-websocket-session",
                "Origin": "http://localhost:8001"
            }
        },
        {
            "name": "With API Gateway Flag",
            "headers": {
                "X-Session-ID": "test-direct-websocket-session",
                "X-API-Gateway-Source": "true"
            }
        },
        {
            "name": "With API Gateway ID",
            "headers": {
                "X-Session-ID": "test-direct-websocket-session",
                "X-Client-ID": "api-gateway-testclient"
            }
        },
        {
            "name": "Complete",
            "headers": {
                "X-Session-ID": "test-direct-websocket-session",
                "X-API-Gateway-Source": "true",
                "X-Client-ID": "api-gateway-testclient",
                "Origin": "http://localhost:8001",
                "Host": "localhost:8001"
            }
        }
    ]

    for header_set in header_sets:
        print(f"\nTrying connection with {header_set['name']} headers:")
        print(f"Headers: {header_set['headers']}")

        try:
            async with websockets.connect(uri, extra_headers=header_set['headers']) as websocket:
                print(f"✅ Connected with {header_set['name']} headers!")

                # Send a ping message
                await websocket.send(json.dumps({'type': 'ping'}))
                print(f"Sent ping message")

                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    print(f"Received: {response}")
                    response_data = json.loads(response)
                    if response_data.get('type') == 'pong':
                        print(f"✅ WebSocket connection successful with {header_set['name']} headers - received pong response")
                    else:
                        print(f"❌ Unexpected response type: {response_data.get('type')}")
                except asyncio.TimeoutError:
                    print(f"❌ Timeout waiting for response with {header_set['name']} headers")

                # Exit after the first successful connection
                return
        except Exception as e:
            print(f"❌ Connection failed with {header_set['name']} headers: {str(e)}")

    print("\nAll connection attempts failed.")

if __name__ == "__main__":
    asyncio.run(test_websocket())
