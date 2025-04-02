import asyncio
import websockets
import json
import uuid
import requests

async def test_gateway_connection():
    """Test WebSocket connection through API Gateway"""
    print("\nTesting WebSocket connection through API Gateway...")

    # First authenticate to get a session token
    try:
        # API Gateway may not have the /api/v1/ws-auth endpoint implemented
        # For testing, we'll just use a random session ID
        session_id = str(uuid.uuid4())
        token = None
        print(f"Using random session ID for testing: {session_id}")
    except Exception as e:
        print(f"Error authenticating: {e}")
        # Use a random session ID as fallback
        session_id = str(uuid.uuid4())
        token = None

    # Try to connect through API Gateway
    gateway_ws_url = f"ws://localhost:3000/ws/{session_id}"
    print(f"Connecting to Gateway WebSocket at {gateway_ws_url}...")

    # Set the auth token as a header if we have one
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with websockets.connect(gateway_ws_url, extra_headers=headers) as websocket:
            print("Connected to Gateway WebSocket successfully!")

            # Send a ping message
            message = {"type": "ping", "message": "Hello from Gateway WebSocket!"}
            await websocket.send(json.dumps(message))
            print(f"Sent to Gateway: {message}")

            # Receive multiple responses (connection status, etc.)
            for _ in range(3):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    print(f"Received from Gateway: {response}")
                except asyncio.TimeoutError:
                    print("No more messages received (timeout).")
                    break
                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break
    except Exception as e:
        print(f"Error connecting to Gateway WebSocket: {e}")

if __name__ == "__main__":
    asyncio.run(test_gateway_connection())
