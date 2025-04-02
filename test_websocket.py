#!/usr/bin/env python3
"""
WebSocket connection test script.
"""

import asyncio
import websockets
import json
import uuid
from datetime import datetime

# Direct connection to AI service
AI_SERVICE_WS_URL = "ws://localhost:8001/ws"

async def test_direct_connection():
    """Test direct WebSocket connection to AI service"""
    print("\nTesting direct WebSocket connection to AI service...")

    # Use a random session ID
    session_id = str(uuid.uuid4())
    ws_url = f"{AI_SERVICE_WS_URL}/{session_id}"
    print(f"Connecting to {ws_url}...")

    try:
        async with websockets.connect(ws_url) as websocket:
            print("Connected to AI Service WebSocket successfully!")

            # Send a ping message
            message = {
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(message))
            print(f"Sent: {message}")

            # Receive response
            response = await websocket.recv()
            print(f"Received: {response}")

    except Exception as e:
        print(f"Error connecting to WebSocket: {e}")

async def main():
    """Run the test"""
    await test_direct_connection()

if __name__ == "__main__":
    asyncio.run(main())
