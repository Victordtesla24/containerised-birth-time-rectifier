"""
Birth Time Rectifier API Gateway
--------------------------------
This module serves as the API Gateway for the Birth Time Rectifier application,
implementing the Consolidated Single-Registration Architecture with versioned API endpoints.

The API Gateway enforces the standardized /api/v1/ prefix for all API requests,
returning appropriate 404 responses for non-compliant paths. This ensures consistent
API versioning across the application and simplifies future maintenance and extensions.
"""

# Standard library imports
import os
import sys
import time
import uuid
import json
import asyncio
import logging
import traceback
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
# Third party imports
from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import JSONResponse, Response, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import redis.asyncio as redis
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.websockets import WebSocketState
# Import directly from the routes directory
import importlib.util
from fastapi import APIRouter

# Local imports
from api_gateway.websocket_proxy import proxy as websocket_proxy
from api_gateway.websocket_proxy import WebSocketProxy

# Configure logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join("logs", "api_gateway.log"), mode="a")
    ]
)
logger = logging.getLogger("api_gateway")

# Create a thread pool for Redis operations
redis_executor = ThreadPoolExecutor(max_workers=4)

# Initialize FastAPI application
app = FastAPI(
    title="Birth Time Rectifier API Gateway",
    description="API Gateway for the Birth Time Rectifier application",
    version="1.0.0",
    docs_url="/swagger" if os.getenv("ENVIRONMENT", "development") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT", "development") != "production" else None,
)

# Add this function near the top of the file, after imports
async def run_redis_operation(operation_func):
    """
    Run a Redis operation with proper error handling.
    If Redis is not available, returns False.

    Args:
        operation_func: A function that performs Redis operations

    Returns:
        The result of the operation or False if Redis is not available
    """
    try:
        if redis_client is None:
            logger.warning("Redis client not available, skipping operation")
            return False

        return operation_func()
    except Exception as e:
        logger.warning(f"Redis operation failed: {e}")
        return False

# Function to safely import router modules
def import_router_module(module_name):
    """Safely import a router module and include it if it has a router attribute."""
    try:
        # Build the full module name
        full_module_name = f"api_gateway.routes.{module_name}"

        # Try to import the module
        module = importlib.import_module(full_module_name)

        # Check if it has a router attribute
        if hasattr(module, 'router'):
            # Include the router
            app.include_router(module.router)
            logger.info(f"Included {module_name} router")
        else:
            logger.warning(f"Module {module_name} doesn't have a router attribute")

    except ImportError as e:
        logger.warning(f"Failed to import {module_name} router: {e}")
    except Exception as e:
        logger.error(f"Error including {module_name} router: {e}")

# Import and include all router modules
for router_module in ['questionnaire', 'chart', 'session', 'geocode']:
    import_router_module(router_module)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    redis_pool = redis.ConnectionPool.from_url(REDIS_URL)
    redis_client = redis.Redis(connection_pool=redis_pool)
    logger.info("Redis client initialized successfully")
except Exception as e:
    logger.error("Failed to initialize Redis client: %s", e)
    redis_client = None

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")  # Should be properly configured in production
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 3600  # 1 hour

# Determine AI service URLs
AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://localhost:8001")
logger.info("AI service URL: %s", AI_SERVICE_URL)

# Normalize URL (handle trailing slash)
if AI_SERVICE_URL and AI_SERVICE_URL.endswith("/"):
    AI_SERVICE_URL = AI_SERVICE_URL[:-1]
logger.info("Final AI_SERVICE_URL: %s", AI_SERVICE_URL)

# Configure WebSocket URL
AI_SERVICE_WS_URL = os.environ.get("AI_SERVICE_WS_URL", "ws://localhost:8001/ws")
logger.info("AI service WebSocket URL: %s", AI_SERVICE_WS_URL)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

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

# Session validation middleware
@app.middleware("http")
async def validate_session(request: Request, call_next):
    """Validate session for protected routes"""
    # Skip for non-API routes, health checks and WebSocket connections
    path = request.url.path
    if (
        not path.startswith("/api/") or
        path.startswith("/api/v1/health") or
        path.startswith("/api/v1/ws-auth") or
        path.startswith("/ws/")
    ):
        return await call_next(request)

    # Skip validation for public routes
    if path in PUBLIC_ROUTES:
        return await call_next(request)

    # Skip for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)

    # Get session ID from cookies or headers
    session_id = None
    if "session_id" in request.cookies:
        session_id = request.cookies.get("session_id")
    elif "Authorization" in request.headers:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.replace("Bearer ", "")
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                session_id = payload.get("session_id")
            except Exception as e:
                logger.warning(f"Invalid JWT token: {e}")

    # Validate session exists
    if not session_id:
        logger.warning("No session ID provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    # Check if session exists in Redis
    try:
        session_valid = False

        if redis_client is not None:
            result = await run_redis_operation(
                lambda: redis_client.exists(f"session:{session_id}") if redis_client else False
            )
            session_valid = bool(result)

            if not session_valid:
                logger.warning(f"Invalid session ID: {session_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired session"
                )
        else:
            # If Redis is unavailable, skip validation in development
            if ENV == "development":
                logger.warning("Redis unavailable, skipping session validation in development")
                session_valid = True
            else:
                logger.error("Redis unavailable and not in development - rejecting request")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable"
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        if ENV == "development":
            logger.warning("Continuing despite session validation error in development")
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Session validation error"
            )

    # Add session ID to request state
    request.state.session_id = session_id

    # Continue with request
    return await call_next(request)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    logger.info(
        "%s - %s %s - %s - %.4fs",
        client_ip,
        request.method,
        request.url.path,
        response.status_code,
        time.time() - start_time
    )

    return response

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and container orchestration"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "api_gateway"
    }

# V1 Health check endpoint
@app.get("/api/v1/health")
async def v1_health_check():
    """Health check endpoint for v1 API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "api_gateway",
        "version": "v1"
    }

# Session initialization endpoint
@app.get("/api/v1/session/init")
async def initialize_session(request: Request):
    """Initialize a new session and return a session token by proxying to AI service"""
    try:
        # Forward request to AI service
        return await proxy_to_ai_service(request)
    except Exception as e:
        logger.error("Session initialization error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize session"
        ) from e

# API Gateway Configuration
API_PATHS = {
    "chart": "/api/v1/chart",
    "questionnaire": "/api/v1/questionnaire",
    "session": "/api/v1/session",
    "geocode": "/api/v1/geocode",
    "ai": "/api/v1/ai",
    "user": "/api/v1/user"
}

# Standardized response structure
def create_response(data: Any = None, error: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a standardized API response"""
    response = {
        "timestamp": datetime.now().isoformat(),
        "success": error is None
    }

    if data is not None:
        response["data"] = data

    if error is not None:
        response["error"] = error

    if meta is not None:
        response["meta"] = meta

    return response

# Store HTTP connections to avoid reconnecting for each request
http_client = httpx.AsyncClient(
    timeout=60.0,  # Default 60 second timeout
    verify=True,  # Enable SSL verification for security
)

async def proxy_to_ai_service(request: Request):
    """Generic proxy function to forward requests to the AI service"""
    try:
        # Get target path by removing the API Gateway's path prefix
        path = request.url.path
        if path.startswith("/api/v1/"):
            path = path[8:]  # Remove "/api/v1/" prefix

        # Construct the target URL, ensuring no double slashes
        target_path = path.lstrip("/")  # Remove leading slash to avoid double slash
        target_url = f"{AI_SERVICE_URL}/api/v1/{target_path}"
        logger.info(f"Proxying request to: {target_url}")

        # Get request method and params
        method = request.method
        params = dict(request.query_params)

        # Extract headers
        headers = {k: v for k, v in request.headers.items()
                if k.lower() not in ["host", "content-length"]}

        # Extract request body for non-GET requests
        body = None
        if method != "GET":
            body = await request.body()

        try:
            # Make the request to the AI service
            async with httpx.AsyncClient(timeout=30.0, verify=True) as client:
                if method == "GET":
                    response = await client.get(target_url, params=params, headers=headers)
                elif method == "POST":
                    response = await client.post(target_url, params=params, headers=headers, content=body)
                elif method == "PUT":
                    response = await client.put(target_url, params=params, headers=headers, content=body)
                elif method == "DELETE":
                    response = await client.delete(target_url, params=params, headers=headers)
                else:
                    logger.error(f"Unsupported method {method} for proxying")
                    return JSONResponse(
                        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                        content={"error": f"Method {method} not supported for proxying"}
                    )

            # Log the response status
            logger.info(f"Received response from AI service with status: {response.status_code}")

            # Return the response from the AI service
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        except httpx.ConnectError as e:
            logger.error(f"Error connecting to AI service: {e}")
            error_message = f"Error connecting to AI service: {str(e)}"
            # Return more detailed error information
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": {
                        "message": error_message,
                        "type": "ServiceUnavailableError",
                        "request_id": str(uuid.uuid4())
                    }
                }
            )
        except (httpx.ReadTimeout, httpx.RequestError) as e:
            logger.error(f"Timeout or request error connecting to AI service: {e}")
            error_message = f"Timeout connecting to AI service: {str(e)}"
            # Return more detailed error information
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": {
                        "message": error_message,
                        "type": "GatewayTimeoutError",
                        "request_id": str(uuid.uuid4())
                    }
                }
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from AI service: {e} - Status: {e.response.status_code}")
            try:
                error_response = e.response.json()
                # Forward the error response from the AI service
                return JSONResponse(
                    status_code=e.response.status_code,
                    content=error_response
                )
            except Exception:
                # If we can't parse the error response, return a generic one
                return JSONResponse(
                    status_code=e.response.status_code,
                    content={
                        "error": {
                            "message": f"Error from AI service: {str(e)}",
                            "type": "ServiceError",
                            "request_id": str(uuid.uuid4())
                        }
                    }
                )
    except Exception as e:
        logger.error(f"Unhandled error in proxy_to_ai_service: {e}")
        logger.error(traceback.format_exc())

        # Include more detailed error information
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": f"Proxy error: {str(e)}",
                    "type": "ProxyError",
                    "request_id": str(uuid.uuid4())
                }
            }
        )

# Special proxy handler for geocode requests to transform parameters
@app.get("/api/v1/geocode")
async def geocode_proxy(request: Request, address: Optional[str] = None):
    """
    Special proxy handler for geocode requests that transforms parameters.
    The API Gateway accepts 'address' but the AI Service expects 'query'.
    """
    # Clone the original request query params for modification
    params = dict(request.query_params)

    # Transform 'address' parameter to 'query' parameter if present
    if address:
        params["query"] = address
        # Remove the original address parameter to avoid confusion
        if "address" in params:
            del params["address"]

    logger.info(f"Geocode proxy: Transforming address='{address}' to query parameter")

    # Construct the target URL for the geocode endpoint
    target_url = f"{AI_SERVICE_URL}/api/v1/geocode"
    logger.info(f"Proxying geocode request to: {target_url} with params: {params}")

    # Extract headers
    headers = {k: v for k, v in request.headers.items()
              if k.lower() not in ["host", "content-length"]}

    try:
        # Make the request to the AI service
        async with httpx.AsyncClient(timeout=30.0, verify=True) as client:
            response = await client.get(target_url, params=params, headers=headers)

        # Log the response status
        logger.info(f"Received geocode response from AI service with status: {response.status_code}")

        # Return the response from the AI service
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    except Exception as e:
        logger.error(f"Error proxying geocode request: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": f"Geocode proxy error: {str(e)}",
                    "type": "ProxyError",
                    "request_id": str(uuid.uuid4())
                }
            }
        )

# API v1 routes - Proxy all requests to the AI service
@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], response_model=None)
async def api_proxy_v1(request: Request, path: str):
    """Proxy requests to the v1 API endpoints"""
    # Skip paths that have dedicated handlers
    if request.url.path == "/api/v1/geocode" or request.url.path == "/api/v1/test-event":
        logger.debug("Skipping general proxy for dedicated endpoint: %s", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This endpoint is handled by a dedicated handler"
        )

    logger.debug("Proxying request to v1 API path: %s", path)
    return await proxy_to_ai_service(request)

# Add test-event endpoint for WebSocket testing
@app.post("/api/v1/test-event", response_class=JSONResponse)
async def send_test_event(request: Request):
    """
    Send a test event to a WebSocket client.
    This endpoint is used by test scripts to verify WebSocket functionality.
    """
    try:
        # Parse the request body
        data = await request.json()
        session_id = data.get("session_id")
        message = data.get("message", "Test event from API Gateway")

        # Get session ID from header if not in body
        if not session_id:
            session_id = request.headers.get("X-Session-ID")

        if not session_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Missing session_id in request body or X-Session-ID header"}
            )

        logger.info(f"Sending test event to session {session_id}")

        # Use a TaskGroup with proper exception handling
        try:
            result = await websocket_proxy.send_test_event(session_id, message)

            if result:
                return JSONResponse(
                    content={"success": True, "message": f"Test event sent to session {session_id}"}
                )
            else:
                logger.warning(f"No active WebSocket connection for session {session_id}")
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"error": f"No active WebSocket connection found for session {session_id}"}
                )
        except asyncio.CancelledError:
            logger.warning("Test event sending was cancelled")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "Operation cancelled"}
            )
        except Exception as send_error:
            logger.error(f"Error sending test event: {send_error}")
            logger.error(traceback.format_exc())
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"Failed to send test event: {str(send_error)}"}
            )

    except json.JSONDecodeError as json_error:
        logger.error(f"Invalid JSON in request: {json_error}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid JSON in request body"}
        )
    except Exception as e:
        logger.error(f"Error processing test event request: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": f"Server error: {str(e)}"}
        )

# Add root endpoint handler
@app.get("/", include_in_schema=True, response_class=JSONResponse)
async def root_endpoint(request: Request):
    """
    Root endpoint handler with enhanced error handling and safety checks.
    Provides a direct response instead of proxying to the AI service.
    """
    # Safety check - ensure we only handle the exact root path
    if request.url.path != "/":
        logger.warning("Root handler received non-root path: %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "PATH_MISMATCH",
                    "message": "This handler is for root path only",
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

    logger.info("Root endpoint accessed - providing direct response")

    # Return a direct response instead of proxying to AI Service
    return JSONResponse(
        content=create_response(
            data={
                "message": "Birth Time Rectifier API Gateway",
                "status": "available",
                "timestamp": datetime.now().isoformat(),
                "service": "api_gateway",
                "version": "1.0.0",
                "documentation": "/swagger",
            },
            meta={"request_id": str(uuid.uuid4().hex[:8])}
        ),
        status_code=200
    )

# WebSocket endpoints
@app.websocket("/ws/{session_id}")
async def websocket_endpoint_with_session(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint with session ID.

    This endpoint handles WebSocket connections with a specified session ID
    by establishing a connection to the upstream AI service and proxying messages.
    """
    client_id = f"client-{uuid.uuid4().hex[:8]}"

    try:
        # First, verify the session is valid
        is_authenticated = False

        # Check for session token in headers or cookies
        headers = dict(websocket.headers.items())
        token = headers.get("authorization", "")
        if token.startswith("Bearer "):
            token = token[7:]  # Remove "Bearer " prefix

        # Verify token if provided
        if token:
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                token_session_id = payload.get("session_id")
                if token_session_id == session_id:
                    is_authenticated = True
                    logger.info(f"Authenticated WebSocket connection with token: {session_id}")
            except Exception as e:
                logger.warning(f"Invalid token for WebSocket connection: {e}")

        # If not authenticated by token, check Redis
        if not is_authenticated and redis_client is not None:
            try:
                # Check if session exists in Redis
                def check_session():
                    if redis_client is not None:
                        return redis_client.exists(f"session:{session_id}")
                    return False

                session_exists = await run_redis_operation(check_session)
                is_authenticated = bool(session_exists)

                if is_authenticated:
                    logger.info(f"Authenticated WebSocket connection from Redis: {session_id}")
            except Exception as e:
                logger.warning(f"Redis session check failed: {e}")

        # In development, allow unauthenticated connections for testing
        if not is_authenticated and ENV == "development":
            logger.warning(f"Accepting unauthenticated WebSocket in development: {session_id}")
            is_authenticated = True

        # Reject unauthenticated connections in production
        if not is_authenticated:
            logger.warning(f"Unauthenticated WebSocket connection attempt: {session_id}")
            await websocket.accept()
            await websocket.send_json({
                "type": "error",
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Authentication required for WebSocket connection",
                "timestamp": datetime.now().isoformat()
            })
            await websocket.close(code=1008)  # Policy violation
            return

        # Connection is authenticated, connect to the upstream AI service
        logger.info(f"Connecting to upstream AI service for session: {session_id}")
        proxy = WebSocketProxy()

        # Get the upstream URL from settings
        upstream_url = f"{AI_SERVICE_WS_URL}"

        # Accept the connection and start proxying
        await websocket.accept()

        await proxy.handle_websocket(
            websocket=websocket,
            session_id=session_id,
            upstream_url=upstream_url,
            client_id=client_id,
            token=token
        )

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        logger.error(traceback.format_exc())

        # Try to send an error message if the connection is still open
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        except Exception:
            pass

@app.websocket("/ws")
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint with proxy to AI service.

    This endpoint handles WebSocket connections without a session ID.
    A session ID will be generated and provided to the client.
    """
    # Generate client ID and session ID
    client_id = f"client-{uuid.uuid4().hex[:8]}"
    session_id = f"session-{uuid.uuid4().hex[:8]}"  # Default session if not provided

    try:
        # Accept the connection
        await websocket.accept()
        logger.info("WebSocket connection established: %s", session_id)

        # Send initial welcome message
        await websocket.send_json({
            "type": "welcome",
            "client_id": client_id,
            "session_id": session_id,
            "message": "Connection established. Please use this session ID for future communications.",
            "timestamp": datetime.now().isoformat()
        })

        # Wait for initialization message
        try:
            # Set a timeout for receiving the initialization message
            init_message_task = asyncio.create_task(websocket.receive_json())
            init_message = await asyncio.wait_for(init_message_task, timeout=10.0)

            # Process initialization message
            if "session_id" in init_message:
                session_id = init_message["session_id"]
                logger.info("Updated session ID to %s for client %s", session_id, client_id)

            # Connect to AI service using handle_websocket instead of just connect
            upstream_url = f"{AI_SERVICE_WS_URL}"
            await websocket_proxy.handle_websocket(
                websocket=websocket,
                session_id=session_id,
                upstream_url=upstream_url,
                client_id=client_id,
                token="",  # No token for now
                ping_interval=30
            )

        except asyncio.TimeoutError:
            logger.warning("No initialization message received within timeout for client %s", client_id)
            await websocket.send_json({
                "type": "error",
                "code": "TIMEOUT",
                "message": "No initialization message received within timeout"
            })
            await websocket.close()
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected during initialization for client %s", client_id)
        except Exception as e:
            logger.error("Error during WebSocket initialization for client %s: %s", client_id, e)
            logger.error(traceback.format_exc())
            await websocket.send_json({
                "type": "error",
                "code": "INITIALIZATION_ERROR",
                "message": f"Failed to initialize WebSocket connection: {str(e)}"
            })
            await websocket.close()

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for client %s", client_id)
    except Exception as e:
        logger.error("WebSocket error for client %s: %s", client_id, e)
        logger.error(traceback.format_exc())

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    """Handle all uncaught exceptions across the application."""
    logger.error("Unhandled exception: %s", exc)
    logger.error(traceback.format_exc())

    # Return a standardized error response
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc) if os.getenv("DEBUG") == "true" else "An unexpected error occurred",
                "timestamp": datetime.now().isoformat()
            }
        }
    )

# Not found exception handler
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, _exc: Exception):
    """Handle 404 Not Found exceptions."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": {
                "code": "NOT_FOUND",
                "message": f"The requested resource was not found: {request.url.path}",
                "timestamp": datetime.now().isoformat()
            }
        }
    )

# Basic health check endpoint (fallback for compatibility)
@app.get("/api/basic-health")
def basic_api_health():
    """Extremely simple health check endpoint with minimal dependencies"""
    return {"status": "ok"}

# Create a dedicated health check app with no middleware
health_app = FastAPI(
    title="Health Check API",
    description="Health check endpoints with no middleware",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    middleware=[]  # Completely empty middleware stack
)

@health_app.get("/")
async def direct_health_check():
    """Health check endpoint with no middleware to ensure it's always available."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "api_gateway",
        "middleware_free": True
    }

# Mount the health app before any middleware is added
app.mount("/health", health_app)
app.mount("/api/health", health_app)
app.mount("/api/basic-health", health_app)

# Add middleware to enforce v1 API paths
@app.middleware("http")
async def api_path_validator(request: Request, call_next):
    """
    Middleware to validate API paths and enforce the versioned API architecture.

    This middleware ensures all API paths follow the standardized /api/v1/ prefix pattern.
    Non-compliant paths receive a 404 response with helpful guidance on proper usage.
    Root, health, and documentation paths are exempted from this validation.
    """
    path = request.url.path

    # Skip v1 API paths, they should be handled normally
    if path.startswith("/api/v1/"):
        return await call_next(request)

    # Skip root, health, websocket and documentation paths
    if path == "/" or path == "/health" or path.startswith("/ws") or path in ["/docs", "/redoc", "/openapi.json", "/swagger"]:
        return await call_next(request)

    # Return 404 for any other API path that starts with /api/
    if path.startswith("/api/"):
        # Extract the path without the /api/ prefix for better guidance
        resource_path = path[5:] if len(path) > 5 else ""
        suggested_path = f"/api/v1/{resource_path}" if resource_path else "/api/v1/"

        # Identify common API resources for helpful suggestions
        common_resources = {
            "chart": "Access chart data with /api/v1/chart/...",
            "geocode": "Geocode locations with /api/v1/geocode",
            "questionnaire": "Access questionnaires with /api/v1/questionnaire/...",
            "health": "Check API health with /api/v1/health",
            "session": "Manage sessions with /api/v1/session/..."
        }

        # Find potential resource matches
        resource_suggestion = ""
        for resource, description in common_resources.items():
            if resource in resource_path:
                resource_suggestion = description
                break

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "ENDPOINT_NOT_FOUND",
                    "message": "Endpoint not found. All API requests must use the /api/v1/ prefix.",
                    "details": "The API uses a versioned architecture to ensure consistency and future compatibility.",
                    "suggested_path": suggested_path,
                    "resource_hint": resource_suggestion if resource_suggestion else "See documentation for available endpoints",
                    "documentation_url": "/api/v1/docs",
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

    # For all other paths, continue normal processing
    return await call_next(request)

# Main entry point
if __name__ == "__main__":
    import uvicorn

    # Get port from environment or use default
    port = int(os.environ.get("PORT", "3000"))
    print(f"Starting API Gateway on port {port}")

    # Run the API Gateway
    uvicorn.run(
        app,  # Use the app instance directly instead of importing by string
        host="0.0.0.0",
        port=port,
        reload=False
    )

@app.post("/api/v1/ws-auth")
async def websocket_auth(request: Request):
    """
    WebSocket authentication endpoint to create valid sessions before establishing WebSocket connections.
    """
    try:
        # Extract session ID if provided
        data = await request.json()
        session_id = data.get("session_id")

        # If no session ID provided, create a new one
        if not session_id:
            session_id = f"ws-{uuid.uuid4().hex}"

        # Create session token with simple JWT
        payload = {
            "session_id": session_id,
            "type": "websocket",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp())
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        # Store session in Redis if available
        if redis_client is not None:
            try:
                redis_client.hset(
                    f"session:{session_id}",
                    mapping={
                        "created_at": datetime.now().isoformat(),
                        "type": "websocket",
                        "client_ip": request.client.host if request.client else "unknown",
                        "authenticated": "true"
                    }
                )
                redis_client.expire(f"session:{session_id}", 3600)  # 1 hour expiry
                logger.info(f"Created WebSocket session in Redis: {session_id}")
            except Exception as redis_error:
                logger.warning(f"Failed to store WebSocket session in Redis: {redis_error}")
                # Continue anyway - the JWT token will still work

        logger.info(f"Created WebSocket auth session: {session_id}")

        return JSONResponse({
            "session_id": session_id,
            "token": token,
            "expires_in": 3600  # 1 hour in seconds
        })
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create WebSocket session: {str(e)}"
        )

# Define public routes that don't require authentication
PUBLIC_ROUTES = [
    "/api/v1/session/init",
    "/api/v1/health",
    "/api/v1/health/ping",
    "/api/v1/health/basic",
    "/api/v1/ws-auth",
    "/docs",
    "/redoc",
    "/openapi.json"
]

# Get the environment
ENV = os.environ.get("ENVIRONMENT", "development").lower()
