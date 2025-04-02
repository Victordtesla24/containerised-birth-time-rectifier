import asyncio
import websockets
import json
import uuid

async def test_direct_connection():
    """Test direct WebSocket connection to AI service"""
    print("\nTesting direct WebSocket connection to AI service...")

    # Create a random session ID
    session_id = str(uuid.uuid4())
    print(f"Using session ID: {session_id}")

    # Try to connect directly to AI service
    ws_url = f"ws://localhost:8001/ws/{session_id}"
    print(f"Connecting to {ws_url}...")

    try:
        async with websockets.connect(ws_url) as websocket:
            print("Connected to AI Service WebSocket successfully!")

            # Send a ping message
            message = {"type": "ping", "message": "Hello from WebSocket!"}
            await websocket.send(json.dumps(message))
            print(f"Sent: {message}")

            # Receive response
            response = await websocket.recv()
            print(f"Received: {response}")

    except Exception as e:
        print(f"Error connecting to WebSocket: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_connection())
