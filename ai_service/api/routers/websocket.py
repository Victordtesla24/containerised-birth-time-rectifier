"""
WebSocket router for real-time updates.

This module provides WebSocket endpoints for real-time updates during
long-running processes like birth time rectification.
"""

import logging
from typing import Dict, Any, Optional, List
import json
import time
from datetime import datetime
import asyncio
import traceback
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from starlette.websockets import WebSocketState, WebSocket as StarletteWebSocket

from ai_service.utils.websocket_manager import get_websocket_manager, WebSocketManager
from ai_service.services.session_service import SessionService, get_session_service
from ai_service.api.services.chart.service import get_chart_service
from ai_service.utils.websocket_events import EventType
from ai_service.api.dependencies.auth import verify_token as auth_verify_token

# Configure logging
logger = logging.getLogger(__name__)

# Setup router
router = APIRouter(prefix="/ws", tags=["websocket"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Global references to services
_chart_service = None
_websocket_manager = None

# Active connections store
active_connections: Dict[str, WebSocket] = {}

async def get_session_service_async() -> SessionService:
    """Get the session service for async contexts."""
    # This is actually a synchronous call, but we wrap it
    # in an async function for consistency in this file
    return get_session_service()

async def get_manager() -> WebSocketManager:
    """Get the WebSocket manager singleton."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = get_websocket_manager()
    return _websocket_manager

@router.websocket("/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time updates.

    This endpoint follows the sequence diagram flow for WebSocket communication,
    maintaining a connection that can receive progress updates for long-running
    processes like birth time rectification.

    Args:
        websocket: The WebSocket connection
        session_id: The session ID for authentication and association
        token: Optional authentication token
    """
    # Get the WebSocket manager
    manager = await get_manager()

    # Log all headers for debugging
    logger.info(f"WebSocket connection attempt - Session ID: {session_id}")
    client_headers = {}
    for header_key, header_value in websocket.headers.items():
        client_headers[header_key] = header_value
        logger.debug(f"Header {header_key}: {header_value}")

    # Check if this is a connection from the API Gateway
    headers = {k.lower(): v for k, v in websocket.headers.items()}
    logger.debug(f"Lowercase Headers: {headers}")

    is_from_gateway = any([
        headers.get("x-api-gateway-source") == "true",
        headers.get("x-client-id", "").startswith("api-gateway-"),
        headers.get("origin") == "http://localhost:3001"
    ])

    logger.info(f"Gateway check - x-api-gateway-source: {headers.get('x-api-gateway-source')}")
    logger.info(f"Gateway check - x-client-id: {headers.get('x-client-id')}")
    logger.info(f"Gateway check - origin: {headers.get('origin')}")
    logger.info(f"Is gateway connection: {is_from_gateway}")

    # For direct connections, validate session
    if not is_from_gateway:
        # For testing purposes, accept any direct connection
        logger.info(f"Accepting direct connection with session ID: {session_id} (TESTING)")
        session_valid = True

        # In production, you would validate the session properly:
        # session_service = get_session_service()
        # session_data = session_service.get_session(session_id)
        # session_valid = session_data is not None
    else:
        logger.info(f"Accepting gateway connection for session: {session_id}")

    # Accept the connection
    try:
        await websocket.accept()
        logger.info(f"WebSocket connection established for session {session_id}")

        # Register with WebSocket manager
        await manager.connect(websocket, session_id)

        # Send confirmation message
        await websocket.send_json({
            "type": "connection_established",
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "message": "WebSocket connection established"
        })

        # Main message loop with ping/pong heartbeat
        last_ping_time = time.time()
        ping_interval = 20  # seconds

        while True:
            try:
                # Set a timeout for receiving messages to allow for heartbeats
                receive_message_task = asyncio.create_task(
                    websocket.receive_text()
                )

                # Calculate time to next ping
                current_time = time.time()
                time_to_ping = max(0.1, ping_interval - (current_time - last_ping_time))

                # Wait for a message or timeout
                try:
                    message_text = await asyncio.wait_for(receive_message_task, timeout=time_to_ping)

                    # Process received message
                    try:
                        message = json.loads(message_text)
                        message_type = message.get("type", "")

                        # Handle message types
                        if message_type == "ping":
                            # Respond to ping with pong
                            await websocket.send_json({
                                "type": "pong",
                                "timestamp": datetime.now().isoformat(),
                                "session_id": session_id
                            })
                        elif message_type == "subscribe":
                            # Subscribe to channel
                            channel = message.get("channel", "")
                            if channel:
                                await manager.subscribe(session_id, channel)
                                await websocket.send_json({
                                    "type": "subscription_confirmed",
                                    "channel": channel,
                                    "timestamp": datetime.now().isoformat()
                                })
                        elif message_type == "event":
                            # Handle specific event types for questionnaire
                            event_name = message.get("event", "")
                            event_data = message.get("data", {})

                            if event_name == "questionnaire_answer":
                                # Process questionnaire answer as per sequence diagram
                                question_id = event_data.get("question_id")
                                answer = event_data.get("answer")

                                if question_id and answer is not None:
                                    # Store answer
                                    await process_questionnaire_answer(session_id, question_id, answer)

                                    # Send back next question or completion status
                                    await send_next_question(websocket, session_id)
                            elif event_name == "start_rectification":
                                # Trigger birth time rectification process
                                await trigger_rectification_process(websocket, session_id, event_data)
                        else:
                            # Echo back other messages
                            await websocket.send_json({
                                "type": "message_received",
                                "original_type": message_type,
                                "timestamp": datetime.now().isoformat()
                            })
                    except json.JSONDecodeError:
                        logger.warning(f"Received invalid JSON: {message_text[:100]}")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": datetime.now().isoformat()
                        })
                except asyncio.TimeoutError:
                    # Time for a ping
                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.now().isoformat()
                    })
                    last_ping_time = time.time()

            except WebSocketDisconnect:
                logger.info(f"Client disconnected: {session_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                logger.error(traceback.format_exc())
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception:
                    # Connection likely broken
                    break
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Clean up the connection
        manager.disconnect(session_id)
        logger.info(f"Cleaned up WebSocket connection for session {session_id}")


async def process_questionnaire_answer(session_id: str, question_id: str, answer: Any) -> None:
    """
    Process a questionnaire answer and store it in the database.

    Args:
        session_id: Session ID
        question_id: Question ID
        answer: Answer data
    """
    logger.info(f"Processing questionnaire answer for session {session_id}, question {question_id}")
    # TODO: Implement answer processing logic
    # This would normally store the answer in the database and update progress


async def send_next_question(websocket: WebSocket, session_id: str) -> None:
    """
    Send the next question to the client or complete the questionnaire.

    Args:
        websocket: WebSocket connection
        session_id: Session ID
    """
    # TODO: Implement next question logic
    # This would normally retrieve the next question from the database

    # For now, just send a mock next question
    await websocket.send_json({
        "type": "next_question",
        "question": {
            "id": str(uuid.uuid4()),
            "text": "What significant life event occurred around age 25?",
            "options": [
                "Career change",
                "Relationship milestone",
                "Health issue",
                "Location change",
                "None of these"
            ]
        },
        "progress": 0.6,  # 60% complete
        "timestamp": datetime.now().isoformat()
    })


async def trigger_rectification_process(websocket: WebSocket, session_id: str, data: Dict[str, Any]) -> None:
    """
    Trigger the birth time rectification process.

    Args:
        websocket: WebSocket connection
        session_id: Session ID
        data: Rectification parameters
    """
    logger.info(f"Starting rectification process for session {session_id}")

    # Send initial status
    await websocket.send_json({
        "type": "rectification_status",
        "status": "started",
        "progress": 0.0,
        "message": "Starting birth time rectification process",
        "timestamp": datetime.now().isoformat()
    })

    # In a real implementation, this would spawn a background task
    # For now, just simulate progress updates
    for progress in [0.2, 0.4, 0.6, 0.8, 1.0]:
        await asyncio.sleep(1)  # Simulate processing time

        await websocket.send_json({
            "type": "rectification_status",
            "status": "in_progress" if progress < 1.0 else "completed",
            "progress": progress,
            "message": f"Processing rectification (step {int(progress * 5)}/5)",
            "timestamp": datetime.now().isoformat()
        })

    # Send final result
    await websocket.send_json({
        "type": "rectification_result",
        "rectified_time": "15:30:00",
        "confidence": 87.5,
        "message": "Birth time rectification completed",
        "timestamp": datetime.now().isoformat()
    })

@router.get("/clients", response_model=Dict[str, Any])
async def get_active_clients() -> Dict[str, Any]:
    """
    Get information about active WebSocket clients.

    Returns:
        Dictionary with active client information
    """
    try:
        manager = await get_manager()

        # Check if manager is None
        if manager is None:
            return {
                "active_connections": [],
                "count": 0,
                "timestamp": datetime.now().isoformat(),
                "error": "WebSocket manager not available"
            }

        return {
            "active_connections": manager.active_connections,
            "count": len(manager.active_connections),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting active clients: {e}")
        return {
            "active_connections": [],
            "count": 0,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@router.post("/session/register", response_model=Dict[str, Any])
async def register_websocket_session(request: Request):
    """
    Register a session that is allowed to connect via WebSocket.
    This endpoint is called by the API Gateway when a user authenticates.
    """
    try:
        # Get the WebSocketManager
        manager = await get_manager()

        # Check if request is from the API Gateway
        headers = {k.lower(): v for k, v in request.headers.items()}
        is_from_gateway = headers.get("x-api-gateway-source") == "true"

        if not is_from_gateway:
            logger.warning("Unauthorized attempt to register WebSocket session")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the API Gateway can register WebSocket sessions"
            )

        # Get session data from request
        data = await request.json()
        session_id = data.get("session_id")

        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="session_id is required"
            )

        # Register the session
        manager.register_session(session_id)

        # Also store in session service for redundancy
        session_service = get_session_service()
        session_service.create_session(session_id)

        logger.info(f"Registered WebSocket session: {session_id}")

        return {
            "success": True,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering WebSocket session: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register WebSocket session: {str(e)}"
        )
