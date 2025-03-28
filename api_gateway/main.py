"""
Birth Time Rectifier API Gateway
--------------------------------
Main application file for the API Gateway service.
Acts as a central point for routing requests to appropriate microservices.
Implements the Unified API Gateway Architecture with path rewriting.
"""

from fastapi import FastAPI, Request, HTTPException, status, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
import sys
import httpx
import uuid
import traceback
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
import json
import redis.asyncio as redis
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
import re
import threading
from concurrent.futures import ThreadPoolExecutor

# Import WebSocket proxy
from api_gateway.websocket_proxy import proxy as websocket_proxy

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

# Initialize Redis client
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    redis_pool = redis.ConnectionPool.from_url(REDIS_URL)
    redis_client = redis.Redis(connection_pool=redis_pool)
    logger.info("Redis client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Redis client: {e}")
    redis_client = None

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")  # Should be properly configured in production
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 3600  # 1 hour

# AI Service URLs
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8000")
AI_SERVICE_WS_URL = os.getenv("AI_SERVICE_WS_URL", "ws://localhost:8000/ws")
# Should be properly configured in production

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be restricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Helper function to run Redis operations in a separate thread
async def run_redis_operation(operation_func):
    """Run Redis operation in a thread to avoid blocking the event loop"""
    if redis_client is None:
        logger.warning("Redis client is None, skipping operation")
        return None

    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(redis_executor, operation_func)
    except Exception as e:
        logger.error(f"Redis operation error: {e}")
        return None

# Session validation middleware
@app.middleware("http")
async def validate_session(request: Request, call_next):
    session_token = request.headers.get("X-Session-Token")

    # Skip session validation for certain paths
    if request.url.path in ["/health", "/api/v1/health", "/api/v1/session/init", "/api/session/init"] or \
       request.url.path.startswith("/api/geocode") or request.url.path.startswith("/api/v1/geocode") or \
       request.url.path.startswith("/api/chart/validate") or request.url.path.startswith("/api/v1/chart/validate") or \
       request.url.path.startswith("/api/chart/generate") or request.url.path.startswith("/api/v1/chart/generate") or \
       request.url.path.startswith("/api/chart/") or request.url.path.startswith("/api/v1/chart/"):
        return await call_next(request)

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is required"
        )

    try:
        # Verify JWT token
        payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        session_id = payload.get("session_id")

        # Check if session exists in Redis
        try:
            if redis_client:
                # Check if session exists
                def check_session_exists():
                    if redis_client:
                        return redis_client.exists(f"session:{session_id}")
                    return None

                session_exists = await run_redis_operation(check_session_exists)
                if session_exists is not None and not bool(session_exists):
                    logger.warning(f"Session {session_id} not found in Redis")
                    # Continue with JWT validation only

                # Update session last activity
                def update_session_activity():
                    if redis_client:
                        return redis_client.hset(
                            f"session:{session_id}",
                            mapping={"last_activity": datetime.now().isoformat()}
                        )
                    return None

                update_result = await run_redis_operation(update_session_activity)
                if update_result is not None:
                    logger.debug(f"Redis hset result: {update_result}")

            # Add session info to request state
            request.state.session_id = session_id
        except Exception as redis_error:
            logger.error(f"Redis error: {redis_error}")
            # Continue with JWT validation only
            request.state.session_id = session_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token"
        )

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
        f"{client_ip} - {request.method} {request.url.path} "
        f"- {response.status_code} - {time.time() - start_time:.4f}s"
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
async def initialize_session():
    """Initialize a new session and return a session token"""
    session_id = str(uuid.uuid4())

    # Create session in Redis
    session_data = {
        "created_at": datetime.now().isoformat(),
        "last_activity": datetime.now().isoformat(),
        "client_ip": "unknown"  # Should be set from request in production
    }

    try:
        if redis_client:
            # Use mapping parameter for hset
            def set_session_data():
                if redis_client:
                    return redis_client.hset(f"session:{session_id}", mapping=session_data)
                return None

            result = await run_redis_operation(set_session_data)
            if result is not None:
                logger.debug(f"Redis hset result: {result}")

            # Set expiration
            def set_expiration():
                if redis_client:
                    return redis_client.expire(f"session:{session_id}", JWT_EXPIRATION)
                return None

            expire_result = await run_redis_operation(set_expiration)
            if expire_result is not None:
                logger.debug(f"Redis expire result: {expire_result}")
    except Exception as redis_err:
        logger.error(f"Failed to create session in Redis: {redis_err}")
        # Continue without Redis - we can still create the JWT token

    # Generate JWT token
    token_data = {
        "session_id": session_id,
        "exp": datetime.now().timestamp() + JWT_EXPIRATION
    }
    token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)

    return {
        "session_id": session_id,
        "token": token,
        "expires_in": JWT_EXPIRATION
    }

# API Gateway Configuration
API_PATHS = {
    "chart": "/api/v1/chart",
    "questionnaire": "/api/v1/questionnaire",
    "session": "/api/v1/session",
    "geocode": "/api/v1/geocode",
    "ai": "/api/v1/ai",
    "user": "/api/v1/user"
}

# Legacy path mappings
LEGACY_PATHS = {
    # Root level paths
    "/chart": "/api/v1/chart",
    "/questionnaire": "/api/v1/questionnaire",
    "/session": "/api/v1/session",
    "/geocode": "/api/v1/geocode",
    "/ai": "/api/v1/ai",
    "/user": "/api/v1/user",

    # API paths without version
    "/api/chart": "/api/v1/chart",
    "/api/questionnaire": "/api/v1/questionnaire",
    "/api/session": "/api/v1/session",
    "/api/geocode": "/api/v1/geocode",
    "/api/ai": "/api/v1/ai",
    "/api/user": "/api/v1/user"
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

# Proxy function for forwarding requests to the AI service
async def proxy_to_ai_service(request: Request, path: str, target_url: str) -> Any:
    """Proxy a request to the AI service with standardized response handling"""
    request_id = request.headers.get('X-Request-ID', str(uuid.uuid4().hex[:8]))
    session_id = request.headers.get('X-Session-ID', 'no-session')

    logger.info(f"[{request_id}] Proxying {request.method} request to {target_url}/{path}")

    # Extract request body and query parameters
    try:
        body = await request.body()
        params = dict(request.query_params)

        # Extract request headers, forwarding essential ones
        headers = {}
        for key, value in request.headers.items():
            if key.lower() in (
                'authorization',
                'content-type',
                'user-agent',
                'x-session-id',
                'x-request-id'
            ):
                headers[key] = value

        # Set timeout based on the operation
        timeout = httpx.Timeout(
            connect=5.0,                    # Connection timeout
            read=30.0,                     # Read timeout
            write=5.0,                     # Write timeout
            pool=5.0                       # Connection pool timeout
        )

        # Some operations need extended timeouts
        if 'rectify' in path or 'generate' in path:
            timeout = httpx.Timeout(
                connect=5.0,                # Connection timeout
                read=120.0,                 # Extended read timeout
                write=5.0,                  # Write timeout
                pool=5.0                    # Connection pool timeout
            )

        # Make the request to the AI service
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Construct the final URL correctly
            url = f"{target_url}/{path}"
            logger.debug(f"Proxying to URL: {url}")

            response = await client.request(
                method=request.method,
                url=url,
                params=params,
                headers=headers,
                content=body
            )

            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = response.text

            # Return standardized response
            if response.is_success:
                return create_response(
                    data=response_data,
                    meta={"request_id": request_id}
                )
            else:
                return create_response(
                    error={
                        "code": f"AI_SERVICE_ERROR_{response.status_code}",
                        "message": str(response_data),
                        "status_code": response.status_code
                    },
                    meta={"request_id": request_id}
                )

    except httpx.TimeoutException:
        logger.error(f"[{request_id}] Request to AI service timed out for {path}")
        return create_response(
            error={
                "code": "TIMEOUT",
                "message": "Request to AI service timed out",
                "status_code": 504
            },
            meta={"request_id": request_id}
        )
    except Exception as e:
        logger.error(f"[{request_id}] Error proxying request: {e}")
        logger.error(traceback.format_exc())
        return create_response(
            error={
                "code": "INTERNAL_SERVER_ERROR",
                "message": f"An unexpected error occurred: {str(e)}",
                "status_code": 500
            },
            meta={"request_id": request_id}
        )

# Path rewriting middleware implementation
class PathRewriterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, add_deprecation_warnings: bool = True):
        super().__init__(app)
        self.add_deprecation_warnings = add_deprecation_warnings

        # Define path mapping rules - from legacy paths to standardized v1 paths
        self.path_mappings = [
            # Root level legacy routes
            (r"^/health$", "/api/v1/health"),
            (r"^/geocode$", "/api/v1/geocode"),
            (r"^/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/export/(.*)$", r"/api/v1/export/\1"),

            # Unversioned /api/ routes
            (r"^/api/health$", "/api/v1/health"),
            (r"^/api/geocode$", "/api/v1/geocode"),
            (r"^/api/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/api/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/api/export/(.*)$", r"/api/v1/export/\1"),
            (r"^/api/session/init$", "/api/v1/session/init"),
            (r"^/api/session/(.*)$", r"/api/v1/session/\1"),
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        rewritten = False

        # Check if path needs rewriting
        for pattern, replacement in self.path_mappings:
            if re.match(pattern, path):
                rewritten_path = re.sub(pattern, replacement, path)
                # Create modified scope with new path
                new_scope = dict(request.scope)
                new_scope["path"] = rewritten_path
                new_scope["raw_path"] = rewritten_path.encode()

                # Create new request with modified scope
                request = Request(scope=new_scope, receive=request.receive)
                rewritten = True
                break

        # Process the request
        response = await call_next(request)

        # Add deprecation headers if path was rewritten
        if rewritten and self.add_deprecation_warnings:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "Wed, 1 Jan 2025 00:00:00 GMT"
            response.headers["Link"] = f"<{rewritten_path}>; rel=\"successor-version\""

        return response

# API v1 routes - Proxy all requests to the AI service
@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], response_model=None)
async def api_proxy_v1(request: Request, path: str):
    """Proxy requests to the v1 API endpoints"""
    return await proxy_to_ai_service(request, path, f"{AI_SERVICE_URL}/api/v1")

# Legacy API routes - Proxy with path rewriting
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], response_model=None)
async def api_proxy(request: Request, path: str):
    """Proxy requests with legacy path rewriting"""
    # Skip proxying health check (handled directly above)
    if request.url.path == "/health":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found"
        )

    # Add deprecation header for legacy paths
    original_path = request.url.path
    rewritten = False
    target_path = original_path

    # Check if this is a legacy path that should be rewritten
    for prefix, new_prefix in LEGACY_PATHS.items():
        if original_path.startswith(prefix):
            # Rewrite the path
            rest_of_path = original_path[len(prefix):]
            if rest_of_path and not rest_of_path.startswith("/"):
                rest_of_path = f"/{rest_of_path}"
            target_path = f"{new_prefix}{rest_of_path}"
            rewritten = True
            break

    # Forward the request to the appropriate backend endpoint
    response_data = await proxy_to_ai_service(request, path, f"{AI_SERVICE_URL}")

    # Add deprecation header if path was rewritten
    if rewritten:
        # Create a JSONResponse with the data to add headers
        response = JSONResponse(
            content=response_data,
            status_code=200
        )
        response.headers["X-API-Warning"] = f"This endpoint is deprecated. Please use {target_path} instead."
        return response

    return response_data

# WebSocket endpoints
@app.websocket("/ws/{session_id}")
async def websocket_endpoint_with_id(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time updates with session ID.
    Proxies the connection to the AI service.
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

    This endpoint handles WebSocket connections without a session ID.
    A session ID will be generated and provided to the client.
    """
    # Generate client ID and session ID
    client_id = f"client-{uuid.uuid4().hex[:8]}"
    session_id = f"session-{uuid.uuid4().hex[:8]}"  # Default session if not provided

    try:
        # Accept the connection
        await websocket.accept()
        logger.info(f"WebSocket connection established for client {client_id}")

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

            # Get session ID from initialization message or use the default
            provided_session_id = init_message.get("session_id")
            if provided_session_id:
                session_id = provided_session_id

            token = init_message.get("token")

            # Send acknowledgment
            await websocket.send_json({
                "type": "initialize_ack",
                "session_id": session_id,
                "client_id": client_id,
                "timestamp": datetime.now().isoformat()
            })

            # Start WebSocket proxy
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
                "error": "initialization_timeout",
                "message": "No initialization message received within timeout period",
                "timestamp": datetime.now().isoformat()
            })
            await websocket.close(code=1013)  # Try to close with "Try Again Later" code
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for client {client_id}")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        try:
            await websocket.close(code=1011)  # Internal Error
        except:
            pass

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions across the application."""
    logger.error(f"Unhandled exception: {exc}")
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
async def not_found_exception_handler(request: Request, exc: Exception):
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
