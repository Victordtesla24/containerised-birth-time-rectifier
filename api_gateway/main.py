"""
Birth Time Rectifier API Gateway
--------------------------------
Main application file for the API Gateway service.
Acts as a central point for routing requests to appropriate microservices.
Includes WebSocket proxy functionality for real-time updates.
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
import sys
import httpx
import uuid
import traceback
from typing import Optional, Dict, Any, List, Union
import asyncio
from datetime import datetime
import json
import concurrent.futures

# Import WebSocket proxy
from api_gateway.websocket_proxy import proxy as websocket_proxy

# Import routers
from api_gateway.routes.chart import router as chart_router
from api_gateway.routes.questionnaire import router as questionnaire_router

# Import rate limiter
from api_gateway.middleware.rate_limiter import add_rate_limiter

# Import error handling middleware
from api_gateway.middleware.error_middleware import add_error_handler

# Import authentication middleware
from api_gateway.middleware.auth_middleware import verify_token

# Define constants
SESSION_COOKIE_NAME = "birth_rectifier_session"

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join("logs", "api_gateway.log"), mode="a")
    ]
)
logger = logging.getLogger("api_gateway")

# Initialize FastAPI application
app = FastAPI(
    title="Birth Time Rectifier API Gateway",
    description="API Gateway for the Birth Time Rectifier application",
    version="1.0.0",
    docs_url="/swagger" if os.getenv("ENVIRONMENT", "development") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT", "development") != "production" else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be restricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting if Redis is available
redis_url = os.getenv("REDIS_URL")
if redis_url:
    try:
        add_rate_limiter(
            app,
            redis_url=redis_url,
            rate_limit=int(os.getenv("RATE_LIMIT", "60")),
            window=int(os.getenv("RATE_LIMIT_WINDOW", "60"))
        )
        logger.info("Rate limiting middleware added")
    except Exception as e:
        logger.error(f"Failed to add rate limiting middleware: {e}")
        logger.warning("Rate limiting will not be enforced")

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Add security headers
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Add Content-Security-Policy in non-development environments
    if os.getenv("ENVIRONMENT", "development").lower() != "development":
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )

    return response

# AI Service URLs
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
AI_SERVICE_WS_URL = os.getenv("AI_SERVICE_WS_URL", "ws://localhost:8000/ws")

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)

    # Get client IP, safely handling proxy forwarding
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    # Log the request details
    logger.info(
        f"{client_ip} - {request.method} {request.url.path} "
        f"- {response.status_code} - {time.time() - start_time:.4f}s"
    )

    return response

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and container orchestration"""
    return {"status": "ok"}

# Include routers
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(chart_router, prefix="/chart", tags=["Chart"])
v1_router.include_router(questionnaire_router, prefix="/questionnaire", tags=["Questionnaire"])

# Add session endpoint
@v1_router.get("/session/init")
async def init_session():
    """Initialize a new session and return session details"""
    session_id = str(uuid.uuid4())
    response = {
        "session_id": session_id,
        "status": "success",
        "created_at": time.time()
    }
    logger.info(f"Session initialized: {session_id}")
    return response

@v1_router.post("/geocode")
async def geocode_location(request: Request):
    """
    Geocode a location and return coordinates and address details.

    This endpoint forwards geocoding requests to the AI service, which
    handles the actual geocoding through various providers.
    """
    # Parse request body
    try:
        body = await request.json()
        query = body.get("query", "")
        exactly_one = body.get("exactly_one", False)
        limit = body.get("limit", 5)

        if not query or not isinstance(query, str):
            return JSONResponse(
                status_code=400,
                content={"error": "Missing or invalid 'query' parameter"}
            )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": f"Invalid JSON format: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Error parsing request body: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": f"Error parsing request: {str(e)}"}
        )

    # Get session ID from cookie or headers
    session_id = request.cookies.get(SESSION_COOKIE_NAME, request.headers.get("X-Session-ID", ""))

    # Forward request to AI service
    try:
        # Use increased timeout for geocoding operations
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/geocode",
                json={
                    "query": query,
                    "exactly_one": exactly_one,
                    "limit": limit
                },
                headers={
                    "X-Session-ID": session_id,
                    "X-Request-ID": str(uuid.uuid4()),
                    "Content-Type": "application/json"
                }
            )

            # Return response from AI service
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
    except httpx.TimeoutException as e:
        logger.error(f"Geocoding request timed out for query: {query}: {str(e)}")
        return JSONResponse(
            status_code=504,
            content={
                "results": [],
                "query": query,
                "count": 0,
                "status": "error",
                "error": "Geocoding service timed out. Please try again later."
            }
        )
    except httpx.RequestError as e:
        logger.error(f"Geocoding request error for query '{query}': {e}")
        return JSONResponse(
            status_code=502,
            content={
                "results": [],
                "query": query,
                "count": 0,
                "status": "error",
                "error": f"Error connecting to geocoding service: {str(e)}"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in geocoding request for query '{query}': {e}")
        return JSONResponse(
            status_code=500,
            content={
                "results": [],
                "query": query,
                "count": 0,
                "status": "error",
                "error": f"Internal server error: {str(e)}"
            }
        )

@v1_router.post("/geocode/reverse")
async def reverse_geocode(request: Request):
    """
    Reverse geocode coordinates to address details.

    This endpoint forwards reverse geocoding requests to the AI service.
    """
    # Parse request body
    try:
        body = await request.json()
        latitude = body.get("latitude")
        longitude = body.get("longitude")

        # Validate coordinates
        if latitude is None or longitude is None:
            return JSONResponse(
                status_code=400,
                content={
                    "results": [],
                    "query": f"{latitude},{longitude}" if latitude is not None and longitude is not None else "",
                    "count": 0,
                    "status": "error",
                    "error": "Missing 'latitude' or 'longitude' parameters"
                }
            )

        try:
            latitude = float(latitude)
            longitude = float(longitude)

            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                return JSONResponse(
                    status_code=400,
                    content={
                        "results": [],
                        "query": f"{latitude},{longitude}",
                        "count": 0,
                        "status": "error",
                        "error": "Invalid coordinates: latitude must be between -90 and 90, longitude between -180 and 180"
                    }
                )
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=400,
                content={
                    "results": [],
                    "query": f"{latitude},{longitude}" if latitude is not None and longitude is not None else "",
                    "count": 0,
                    "status": "error",
                    "error": "Invalid coordinates: latitude and longitude must be numbers"
                }
            )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "results": [],
                "query": "",
                "count": 0,
                "status": "error",
                "error": f"Invalid JSON format: {str(e)}"
            }
        )
    except Exception as e:
        logger.error(f"Error parsing request body: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "results": [],
                "query": "",
                "count": 0,
                "status": "error",
                "error": f"Error parsing request: {str(e)}"
            }
        )

    # Get session ID from cookie or headers
    session_id = request.cookies.get(SESSION_COOKIE_NAME, request.headers.get("X-Session-ID", ""))

    # Forward request to AI service
    try:
        # Use increased timeout for geocoding operations
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/geocode/reverse",
                json={
                    "latitude": latitude,
                    "longitude": longitude
                },
                headers={
                    "X-Session-ID": session_id,
                    "X-Request-ID": str(uuid.uuid4()),
                    "Content-Type": "application/json"
                }
            )

            # Return response from AI service
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
    except httpx.TimeoutException:
        logger.error(f"Reverse geocoding request timed out for coordinates: {latitude}, {longitude}")
        return JSONResponse(
            status_code=504,
            content={
                "results": [],
                "query": f"{latitude},{longitude}",
                "count": 0,
                "status": "error",
                "error": "Reverse geocoding service timed out. Please try again later."
            }
        )
    except httpx.RequestError as e:
        logger.error(f"Reverse geocoding request error for coordinates {latitude}, {longitude}: {e}")
        return JSONResponse(
            status_code=502,
            content={
                "results": [],
                "query": f"{latitude},{longitude}",
                "count": 0,
                "status": "error",
                "error": f"Error connecting to reverse geocoding service: {str(e)}"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in reverse geocoding request for coordinates {latitude}, {longitude}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "results": [],
                "query": f"{latitude},{longitude}",
                "count": 0,
                "status": "error",
                "error": f"Internal server error: {str(e)}"
            }
        )

@v1_router.post("/geocode/timezone")
async def get_timezone(request: Request):
    """
    Get timezone information for coordinates.

    This endpoint forwards timezone requests to the AI service.
    """
    # Parse request body
    try:
        body = await request.json()
        latitude = body.get("latitude")
        longitude = body.get("longitude")

        # Validate coordinates
        if latitude is None or longitude is None:
            return JSONResponse(
                status_code=400,
                content={
                    "coordinates": "",
                    "status": "error",
                    "error": "Missing 'latitude' or 'longitude' parameters"
                }
            )

        try:
            latitude = float(latitude)
            longitude = float(longitude)

            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                return JSONResponse(
                    status_code=400,
                    content={
                        "coordinates": f"{latitude},{longitude}",
                        "status": "error",
                        "error": "Invalid coordinates: latitude must be between -90 and 90, longitude between -180 and 180"
                    }
                )
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=400,
                content={
                    "coordinates": f"{latitude},{longitude}" if latitude is not None and longitude is not None else "",
                    "status": "error",
                    "error": "Invalid coordinates: latitude and longitude must be numbers"
                }
            )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "coordinates": "",
                "status": "error",
                "error": f"Invalid JSON format: {str(e)}"
            }
        )
    except Exception as e:
        logger.error(f"Error parsing request body: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "coordinates": "",
                "status": "error",
                "error": f"Error parsing request: {str(e)}"
            }
        )

    # Get session ID from cookie or headers
    session_id = request.cookies.get(SESSION_COOKIE_NAME, request.headers.get("X-Session-ID", ""))

    # Forward request to AI service
    try:
        # Use increased timeout for timezone operations
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/geocode/timezone",
                json={
                    "latitude": latitude,
                    "longitude": longitude
                },
                headers={
                    "X-Session-ID": session_id,
                    "X-Request-ID": str(uuid.uuid4()),
                    "Content-Type": "application/json"
                }
            )

            # Return response from AI service
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
    except httpx.TimeoutException:
        logger.error(f"Timezone request timed out for coordinates: {latitude}, {longitude}")
        return JSONResponse(
            status_code=504,
            content={
                "coordinates": f"{latitude},{longitude}",
                "timezone": {
                    "timezone_id": "UTC",
                    "timezone_name": "Coordinated Universal Time",
                    "dst_offset": 0,
                    "raw_offset": 0,
                    "total_offset": 0,
                    "source": "utc_standard"
                },
                "status": "error",
                "error": "Timezone service timed out. Please try again later."
            }
        )
    except httpx.RequestError as e:
        logger.error(f"Timezone request error for coordinates {latitude}, {longitude}: {e}")
        return JSONResponse(
            status_code=502,
            content={
                "coordinates": f"{latitude},{longitude}",
                "timezone": {
                    "timezone_id": "UTC",
                    "timezone_name": "Coordinated Universal Time",
                    "dst_offset": 0,
                    "raw_offset": 0,
                    "total_offset": 0,
                    "source": "utc_standard"
                },
                "status": "error",
                "error": f"Error connecting to timezone service: {str(e)}"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in timezone request for coordinates {latitude}, {longitude}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "coordinates": f"{latitude},{longitude}",
                "timezone": {
                    "timezone_id": "UTC",
                    "timezone_name": "Coordinated Universal Time",
                    "dst_offset": 0,
                    "raw_offset": 0,
                    "total_offset": 0,
                    "source": "utc_standard"
                },
                "status": "error",
                "error": f"Internal server error: {str(e)}"
            }
        )

app.include_router(v1_router)

# WebSocket endpoints
@app.websocket("/ws/{session_id}")
async def websocket_endpoint_with_id(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time updates with session ID.
    Proxies the connection to the AI service.

    Args:
        websocket: The WebSocket connection
        session_id: The session ID to associate with this connection
    """
    try:
        # Connect to the WebSocket proxy
        await websocket_proxy.connect(websocket, session_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")

@app.websocket("/ws")
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint with proxy to AI service.

    This endpoint handles real-time communication between the client and the AI service,
    including authentication, message validation, and proper error recovery.
    """
    # Generate client ID and session ID
    client_id = f"client-{uuid.uuid4().hex[:8]}"
    session_id = f"session-{uuid.uuid4().hex[:8]}"  # Default session if not provided

    try:
        # Accept the connection
        await websocket.accept()
        logger.info(f"WebSocket connection established for client {client_id}")

        # Send initial welcome message - this helps determine if connection is working
        await websocket.send_json({
            "type": "welcome",
            "client_id": client_id,
            "message": "Connection established. Please send initialization message.",
            "timestamp": datetime.now().isoformat()
        })

        # Wait for initialization message
        try:
            # Set a timeout for receiving the initialization message
            init_message_task = asyncio.create_task(websocket.receive_json())
            try:
                init_message = await asyncio.wait_for(init_message_task, timeout=10.0)

                # Get session ID from initialization message or use the default
                provided_session_id = init_message.get("session_id")
                if provided_session_id:
                    session_id = provided_session_id

                token = init_message.get("token")

                # Send acknowledgment immediately to confirm receipt
                await websocket.send_json({
                    "type": "initialize_ack",
                    "session_id": session_id,
                    "client_id": client_id,
                    "timestamp": datetime.now().isoformat()
                })

                # Start WebSocket proxy with error handling and recovery
                await websocket_proxy.handle_websocket(
                    websocket=websocket,
                    session_id=session_id,
                    upstream_url=f"{AI_SERVICE_WS_URL}/{session_id}",
                    client_id=client_id,
                    token=token or "",
                    ping_interval=int(os.getenv("WS_PING_INTERVAL", "30"))
                )
            except asyncio.TimeoutError:
                logger.warning(f"No initialization message received from client {client_id} within timeout")
                await websocket.send_json({
                    "type": "error",
                    "message": "Initialization timeout. No initialization message received.",
                    "timestamp": datetime.now().isoformat()
                })
                await websocket.close(1013)  # Try/again later
                return

        except json.JSONDecodeError as json_error:
            logger.warning(f"Invalid JSON from client {client_id}: {str(json_error)}")
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON in initialization message",
                "error_details": str(json_error),
                "timestamp": datetime.now().isoformat()
            })
            await websocket.close(1003)  # Unsupported data
            return
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected during initialization")
            return

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket handler for client {client_id}: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        try:
            # Check if the connection is still open before sending error
            if websocket.client_state.CONNECTED:
                await websocket.send_json({
                    "type": "error",
                    "message": f"WebSocket error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
                await websocket.close(1011)  # Internal error
        except Exception:
            pass
    finally:
        # Clean up
        logger.info(f"WebSocket connection closed for client {client_id}, session {session_id}")

        # Clean up any resources for this session
        try:
            await websocket_proxy.disconnect(websocket, session_id)
        except Exception as cleanup_error:
            logger.warning(f"Error during WebSocket cleanup: {str(cleanup_error)}")

# API v1 routes
@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], response_model=None)
async def api_proxy_v1(request: Request, path: str):
    """Proxy requests to AI service"""
    return await proxy_to_ai_service(request, path, f"{AI_SERVICE_URL}/api/v1/{path}")

# Legacy API routes (without /api/v1 prefix)
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], response_model=None)
async def api_proxy(request: Request, path: str):
    """Proxy requests to AI service"""
    return await proxy_to_ai_service(request, path, f"{AI_SERVICE_URL}/{path}")

# Proxy function to forward requests to AI service
async def proxy_to_ai_service(request: Request, path: str, target_url: str):
    """Proxy requests to AI service with proper error handling"""
    try:
        body = await request.body()
        method = request.method
        headers = dict(request.headers)

        # Remove host header to avoid conflicts
        headers.pop("host", None)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=True,
            )

            return JSONResponse(
                content=response.json() if response.headers.get("content-type") == "application/json" else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except Exception as e:
        logger.error(f"Proxy error for {path}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "Error connecting to backend service"}
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred"},
    )

# Not found handler
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: Exception):
    """Handle 404 Not Found exceptions"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "The requested resource was not found"},
    )

# Add enhanced error handling
add_error_handler(
    app,
    max_retries=3,
    retry_delay=0.5,
    retry_backoff_factor=2.0,
    retry_status_codes=[502, 503, 504, 429],
    debug_mode=os.getenv("ENVIRONMENT", "development") != "production"
)

# Entry point for running the app directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
