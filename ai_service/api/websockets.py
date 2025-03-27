"""
WebSocket Connection Manager for Birth Time Rectifier API

This module provides WebSocket functionality for real-time updates
during long-running processes like birth time rectification.

This module delegates to the canonical implementation in ai_service.utils.websocket_manager.
"""

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from typing import Dict, List, Any, Optional, cast
import logging
import json
import time
from datetime import datetime

# Import the canonical WebSocket manager
from ai_service.utils.websocket_manager import manager as ws_manager, get_websocket_manager

# Configure logging
logger = logging.getLogger(__name__)

# Re-export the manager instance
# This ensures backwards compatibility with existing code
# Usage: from ai_service.api.websockets import manager

# Export handler function for FastAPI WebSocket endpoints
async def handle_websocket_connection(websocket: WebSocket, session_id: str):
    """
    Handle a WebSocket connection according to the sequence diagram.

    Args:
        websocket: The WebSocket connection
        session_id: The session ID to associate with this connection
    """
    # Connect using the canonical manager
    connected = await ws_manager.connect(websocket, session_id)

    if not connected:
        logger.error(f"Failed to establish WebSocket connection for session {session_id}")
        if websocket.client_state != websocket.client_state.DISCONNECTED:
            await websocket.close(code=1011)  # Internal error
        return

    try:
        # Main message processing loop
        while True:
            data = await websocket.receive_text()
            try:
                # Parse and process the message
                message = json.loads(data)
                message_type = message.get("type", "")

                # Handle ping messages
                if message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": time.time(),
                        "message": "Server is alive"
                    })

                    # Update activity timestamp in metadata
                    if session_id in ws_manager.client_metadata:
                        ws_manager.client_metadata[session_id]["last_activity"] = datetime.now().isoformat()

                # Handle subscription messages
                elif message_type == "subscribe" and "channel" in message:
                    channel = message.get("channel", "")
                    if isinstance(channel, str) and channel:
                        success = await ws_manager.subscribe(session_id, channel)
                        await websocket.send_json({
                            "type": "subscription_status",
                            "channel": channel,
                            "status": "subscribed" if success else "failed",
                            "timestamp": time.time()
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid channel name",
                            "timestamp": time.time()
                        })

                # Handle unsubscription messages
                elif message_type == "unsubscribe" and "channel" in message:
                    channel = message.get("channel", "")
                    if isinstance(channel, str) and channel:
                        success = await ws_manager.unsubscribe(session_id, channel)
                        await websocket.send_json({
                            "type": "subscription_status",
                            "channel": channel,
                            "status": "unsubscribed" if success else "failed",
                            "timestamp": time.time()
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid channel name",
                            "timestamp": time.time()
                        })

                # Echo other messages for debugging
                else:
                    await websocket.send_json({
                        "type": "echo",
                        "original_message": message,
                        "timestamp": time.time()
                    })

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": time.time()
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": time.time()
                })
    except WebSocketDisconnect:
        # Handle normal client disconnection
        ws_manager.disconnect(session_id)
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"WebSocket error for session {session_id}: {e}")
        ws_manager.disconnect(session_id)


