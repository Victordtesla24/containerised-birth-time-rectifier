"""
Birth Time Rectifier API Gateway
--------------------------------
Main application file for the API Gateway service.
Acts as a central point for routing requests to appropriate microservices.
Includes WebSocket proxy functionality for real-time updates.
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
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
import starlette.requests

# Import WebSocket proxy
from api_gateway.websocket_proxy import proxy as websocket_proxy

# Import routers
from api_gateway.routes.chart import router as chart_router
from api_gateway.routes.questionnaire import router as questionnaire_router
from api_gateway.routes.session import router as session_router

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
        logger.info("Rate limiting middleware added with Redis")
    except Exception as e:
        logger.warning(f"Failed to add Redis rate limiting middleware: {e}")
        logger.info("Falling back to in-memory rate limiting")
        try:
            # Add in-memory rate limiting as fallback
            from fastapi.middleware.trustedhost import TrustedHostMiddleware
            from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
            from starlette.middleware.base import BaseHTTPMiddleware
            from datetime import datetime, timedelta
            from collections import defaultdict
            import threading

            # Simple in-memory rate limiter
            class InMemoryRateLimiter(BaseHTTPMiddleware):
                def __init__(self, app, rate_limit: int = 60, window: int = 60):
                    super().__init__(app)
                    self.rate_limit = rate_limit
                    self.window = window
                    self.requests = defaultdict(list)
                    self.lock = threading.Lock()

                async def dispatch(self, request: Request, call_next):
                    # Get client IP safely
                    client_ip = "unknown"
                    if request.client and hasattr(request.client, "host"):
                        client_ip = request.client.host
                    else:
                        # Try to get IP from headers
                        forwarded_for = request.headers.get("X-Forwarded-For")
                        if forwarded_for:
                            client_ip = forwarded_for.split(",")[0].strip()
                        else:
                            client_ip = request.headers.get("X-Real-IP", "unknown")

                    now = datetime.now()

                    with self.lock:
                        # Clean old requests
                        self.requests[client_ip] = [
                            req_time for req_time in self.requests[client_ip]
                            if now - req_time < timedelta(seconds=self.window)
                        ]

                        # Check rate limit
                        if len(self.requests[client_ip]) >= self.rate_limit:
                            return JSONResponse(
                                status_code=429,
                                content={"error": "Too many requests"}
                            )

                        self.requests[client_ip].append(now)

                    return await call_next(request)

            app.add_middleware(
                InMemoryRateLimiter,
                rate_limit=int(os.getenv("RATE_LIMIT", "60")),
                window=int(os.getenv("RATE_LIMIT_WINDOW", "60"))
            )
            logger.info("In-memory rate limiting middleware added as fallback")
        except Exception as fallback_error:
            logger.error(f"Failed to add in-memory rate limiting: {fallback_error}")
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
v1_router.include_router(session_router, prefix="/session", tags=["Session"])

# Make sure the v1_router is included with the app
app.include_router(v1_router)

# Add health endpoint to v1 router
@v1_router.get("/health")
async def v1_health_check():
    """Health check endpoint for v1 API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service",
        "middleware_bypassed": True,
        "path": "/api/v1/health"
    }

# Specific implementation for the /api/geocode endpoint as per sequence diagram
@app.post("/api/geocode")
async def geocode_endpoint(request: Request):
    """
    Geocode a location and return coordinates and address details.

    Simplified implementation based on working code.
    """
    try:
        # Get session ID from header or cookie
        session_id = request.headers.get("X-Session-ID", request.cookies.get(SESSION_COOKIE_NAME, ""))

        # Parse request body
        try:
            body = await request.json()
            query = body.get("query", "")
            if not query:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Missing query parameter"}
                )
        except Exception as e:
            logger.error(f"Error parsing request body: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid JSON format: {str(e)}"}
            )

        # Forward to AI service with short timeout
        timeout = httpx.Timeout(5.0, connect=3.0)
        logger.info(f"Geocoding request for '{query}' with session: {session_id}")

        # Make request to AI service
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/geocode",
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Session-ID": session_id,
                    "X-Request-ID": str(uuid.uuid4())
                }
            )

            # Handle response
            if response.status_code == 200:
                logger.info(f"Geocode successful for '{query}'")
                return response.json()
            else:
                logger.error(f"Geocode error: {response.status_code} - {response.text[:100]}")
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": f"Geocode service error: {response.status_code}"}
                )
    except httpx.TimeoutException as e:
        logger.error(f"Geocode request timed out: {str(e)}")
        return JSONResponse(
            status_code=504,
            content={"error": "Geocode service timed out"}
        )
    except Exception as e:
        logger.error(f"Error in geocode endpoint: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# API v1 routes - exclude /api/geocode from this catch-all
@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], response_model=None)
async def api_proxy_v1(request: Request, path: str):
    """Proxy requests to AI service"""
    # Skip proxying if this is a geocode request (we handle it directly above)
    if request.url.path == "/api/geocode" and request.method == "POST":
        return JSONResponse(
            status_code=405,
            content={"error": "Method not allowed for this path"}
        )

    return await proxy_to_ai_service(request, path, f"{AI_SERVICE_URL}/api/v1/{path}")

# Legacy API routes (without /api/v1 prefix) - exclude /api/geocode from this catch-all
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], response_model=None)
async def api_proxy(request: Request, path: str):
    """Proxy requests to AI service"""
    # Skip proxying if this is a geocode request (we handle it directly above)
    if request.url.path == "/api/geocode" and request.method == "POST":
        return JSONResponse(
            status_code=405,
            content={"error": "Method not allowed for this path"}
        )

    return await proxy_to_ai_service(request, path, f"{AI_SERVICE_URL}/{path}")

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

# Proxy function to forward requests to AI service
async def proxy_to_ai_service(request: Request, path: str, target_url: str):
    """
    Proxy requests to AI service.

    Args:
        request: The incoming request
        path: The path of the request
        target_url: The target URL to proxy to

    Returns:
        Response from AI service
    """
    try:
        # Get session ID from cookie or headers
        session_id = request.cookies.get(SESSION_COOKIE_NAME, request.headers.get("X-Session-ID", ""))

        # Get request headers, removing CORS headers and adding session ID
        headers = {k: v for k, v in request.headers.items()
                  if k.lower() not in ["host", "cookie", "connection", "content-length"]}

        # Add request ID and session ID if available
        if session_id:
            headers["X-Session-ID"] = session_id
        headers["X-Request-ID"] = str(uuid.uuid4())

        # Create HTTP client with appropriate timeout
        timeout = 60.0  # Default timeout in seconds
        if "stream" in path.lower() or "export" in path.lower():
            timeout = 300.0  # Higher timeout for streaming and export endpoints

        # Include query parameters in the target URL
        query_string = request.url.query
        if query_string:
            target_url = f"{target_url}?{query_string}"

        logger.info(f"Proxying {request.method} request to {target_url}")

        # Get request body with proper error handling
        try:
            body = await request.body()
        except starlette.requests.ClientDisconnect:
            logger.warning(f"Client disconnected while reading request body for {path}")
            return JSONResponse(
                status_code=499,  # Client Closed Request
                content={"error": "Client disconnected"}
            )

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            try:
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body
                )

                # Handle streaming responses differently
                if "stream" in path.lower():
                    return StreamingResponse(
                        response.aiter_bytes(),
                        status_code=response.status_code,
                        headers=dict(response.headers)
                    )

                # For regular responses, try to parse JSON
                try:
                    content = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"message": response.text}
                except json.JSONDecodeError:
                    content = {"message": response.text}

                # Log non-200 responses
                if response.status_code >= 400:
                    logger.error(f"AI service returned error for {path}: {response.status_code} - {response.text[:500]}")

                return JSONResponse(
                    status_code=response.status_code,
                    content=content
                )

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP status error for {path}: {e}")
                return JSONResponse(
                    status_code=e.response.status_code,
                    content={"error": f"AI service returned error: {e.response.text}"}
                )
            except httpx.TimeoutException as e:
                logger.error(f"Request timeout for {path}: {e}")
                return JSONResponse(
                    status_code=504,
                    content={"error": "Request timed out"}
                )
            except Exception as e:
                logger.error(f"Error proxying request to AI service: {e}")
                return JSONResponse(
                    status_code=502,
                    content={"error": f"Error communicating with AI service: {str(e)}"}
                )

    except starlette.requests.ClientDisconnect:
        logger.warning(f"Client disconnected during request processing for {path}")
        return JSONResponse(
            status_code=499,  # Client Closed Request
            content={"error": "Client disconnected"}
        )
    except httpx.RequestError as e:
        logger.error(f"Proxy error for {path}: {e}")
        return JSONResponse(
            status_code=502,
            content={"error": f"Could not connect to AI service: {str(e)}"}
        )
    except Exception as e:
        logger.error(f"Unexpected error proxying {path}: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"}
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
        port=3000,
        reload=True,
        log_level="info"
    )

@app.post("/api/geocode/simple")
async def geocode_endpoint_simple(request: Request):
    """Simplified geocoding endpoint for debugging"""

    try:
        # Simple fixed query to test service
        query = "New York City"

        # Log what we're doing
        logger.info(f"Simple geocode test with fixed query: '{query}'")

        # Forward directly to AI service with shorter timeout
        timeout = httpx.Timeout(7.0, connect=3.0)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            endpoint = f"{AI_SERVICE_URL}/api/v1/geocode"

            logger.info(f"Sending test request to: {endpoint}")

            response = await client.post(
                endpoint,
                json={"query": query, "limit": 1, "exactly_one": True},
                headers={"Content-Type": "application/json"}
            )

            logger.info(f"Response status: {response.status_code}")

            if response.status_code == 200:
                logger.info("Geocode test successful!")
                return response.json()
            else:
                logger.error(f"Geocode test failed: {response.text[:100]}")
                return {
                    "error": "Geocode test failed",
                    "status_code": response.status_code,
                    "details": response.text[:100]
                }

    except httpx.TimeoutException as e:
        logger.error(f"Timeout in simple geocode test: {str(e)}")
        return {"error": f"Timeout: {str(e)}"}
    except Exception as e:
        logger.error(f"Error in simple geocode test: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e)}

@app.post("/api/geocode/minimal")
async def geocode_endpoint_minimal(request: Request):
    """Most minimal geocoding endpoint possible for testing."""
    await asyncio.sleep(0.1)  # Minimal delay
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Hardcoded test response",
            "query": "New York City",
            "results": [
                {
                    "address": "New York City, NY, USA",
                    "latitude": 40.7128,
                    "longitude": -74.006,
                    "provider": "test"
                }
            ]
        }
    )

@app.post("/api/geocode/static")
async def geocode_static():
    """Static geocode endpoint that doesn't call any external service."""
    await asyncio.sleep(0.1)  # Small delay
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Static geocode response",
            "results": [
                {
                    "address": "New York City, NY, USA",
                    "latitude": 40.7128,
                    "longitude": -74.006,
                    "provider": "static"
                }
            ]
        }
    )
