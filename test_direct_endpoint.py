import asyncio
import websockets
import json

async def test_direct_websocket():
    """Test the direct WebSocket endpoint that doesn't require authentication."""
    uri = 'ws://localhost:8001/direct-ws/test-direct-session'

    print('Connecting to direct WebSocket...')
    try:
        async with websockets.connect(uri) as websocket:
            print('Connected!')

            # Wait for initial connection message
            response = await websocket.recv()
            print(f"Initial message: {response}")

            # Send a ping message
            await websocket.send(json.dumps({'type': 'ping'}))
            print('Sent ping message')

            # Wait for response
            response = await websocket.recv()
            print(f"Response: {response}")
            response_data = json.loads(response)

            if response_data.get('type') == 'pong':
                print('✅ Direct WebSocket connection successful - received pong response')
            else:
                print(f"❌ Unexpected response type: {response_data.get('type')}")
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

# Add a test for the API Gateway proxy
async def test_api_gateway_websocket():
    """Test the WebSocket via API Gateway proxy."""
    uri = 'ws://localhost:3001/ws/test-gateway-session'

    print('\nConnecting to API Gateway WebSocket...')
    try:
        async with websockets.connect(uri) as websocket:
            print('Connected to API Gateway!')

            # Wait for initial connection message
            response = await websocket.recv()
            print(f"Initial message: {response}")

            # Send a ping message
            await websocket.send(json.dumps({'type': 'ping'}))
            print('Sent ping message')

            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"Response: {response}")
                response_data = json.loads(response)
                if response_data.get('type') == 'pong':
                    print('✅ API Gateway WebSocket connection successful - received pong response')
                else:
                    print(f"❌ Unexpected response type: {response_data.get('type')}")
            except asyncio.TimeoutError:
                print('❌ Timeout waiting for response')
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")

async def main():
    """Run both WebSocket tests."""
    # Test direct endpoint first
    await test_direct_websocket()

    # Then test via API Gateway
    await test_api_gateway_websocket()

if __name__ == "__main__":
    asyncio.run(main())
