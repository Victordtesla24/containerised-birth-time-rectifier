"""
Birth Time Rectifier API Gateway
--------------------------------
This module serves as the API gateway for the Birth Time Rectifier application,
routing requests to the appropriate microservices and handling common functionality.
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
from datetime import datetime
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
# Third party imports
from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import redis.asyncio as redis
import jwt
from starlette.middleware.base import BaseHTTPMiddleware

# Local imports
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

# Try to import route modules - with fallback for missing modules
try:
    from api_gateway.routes import questionnaire
    app.include_router(questionnaire.router)
    logger.info("Included questionnaire routes")
except ImportError as e:
    logger.warning(f"Failed to import questionnaire routes: {e}")

try:
    from api_gateway.routes import chart
    app.include_router(chart.router)
    logger.info("Included chart routes")
except ImportError as e:
    logger.warning(f"Failed to import chart routes: {e}")

try:
    from api_gateway.routes import session
    app.include_router(session.router)
    logger.info("Included session routes")
except ImportError as e:
    logger.warning(f"Failed to import session routes: {e}")

try:
    from api_gateway.routes import geocode
    app.include_router(geocode.router)
    logger.info("Included geocode routes")
except ImportError as e:
    logger.warning(f"Failed to import geocode routes: {e}")

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
AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://ai_service:8001")
logger.info("AI service URL: %s", AI_SERVICE_URL)

# Normalize URL (handle trailing slash)
if AI_SERVICE_URL and AI_SERVICE_URL.endswith("/"):
    AI_SERVICE_URL = AI_SERVICE_URL[:-1]
logger.info("Final AI_SERVICE_URL: %s", AI_SERVICE_URL)

# Configure WebSocket URL
AI_SERVICE_WS_URL = os.environ.get("AI_SERVICE_WS_URL", "ws://ai_service:8001/ws")
logger.info("AI service WebSocket URL: %s", AI_SERVICE_WS_URL)

# Route conflict prevention middleware
@app.middleware("http")
async def handle_route_conflicts(request: Request, call_next):
    """
    Middleware to handle potential route conflicts, especially for the root path.
    This middleware runs before the PathRewriterMiddleware.
    """
    path = request.url.path

    # Add dedicated handling for paths that might cause conflicts
    if path == "/":
        logger.debug("Route conflict prevention: Root path detected")
        # Let the dedicated root handler take care of it
        return await call_next(request)

    if path in ("/health", "/api/health", "/api/basic-health"):
        logger.debug("Route conflict prevention: Health path detected - %s", path)
        # Direct health check handled by dedicated endpoint
        return await call_next(request)

    # For all other paths, continue normal processing
    return await call_next(request)

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
        start_time = time.time()
        result = await loop.run_in_executor(redis_executor, operation_func)
        time_diff = time.time() - start_time
        logger.info("Redis operation completed in %.2f seconds", time_diff)
        return result
    except Exception as e:
        logger.error("Redis operation error: %s", e)
        return None

# Session validation middleware
@app.middleware("http")
async def validate_session(request: Request, call_next):
    session_token = request.headers.get("X-Session-Token")

    # Paths that don't require session validation
    exempt_path_prefixes = [
        "/api/geocode", "/api/v1/geocode",
        "/api/chart/validate", "/api/v1/chart/validate",
        "/api/chart/generate", "/api/v1/chart/generate",
        "/api/chart/", "/api/v1/chart/",
        "/api/questionnaire/initialize", "/api/v1/questionnaire/initialize"
    ]

    # Skip session validation for certain paths
    if request.url.path == "/" or request.url.path in ["/health", "/api/v1/health", "/api/v1/session/init", "/api/session/init"] or \
       any(request.url.path.startswith(prefix) for prefix in exempt_path_prefixes):
        return await call_next(request)

    # For questionnaire endpoints, we should be more lenient with session validation
    is_questionnaire_path = "/questionnaire/" in request.url.path

    # If no session token and not a questionnaire path, require authentication
    if not session_token and not is_questionnaire_path:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token is required"
        )

    # If we have a token, try to validate it
    if session_token:
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
                        logger.warning("Session %s not found in Redis", session_id)
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
                        logger.debug("Redis hset result: %s", update_result)

                # Add session info to request state
                request.state.session_id = session_id
            except Exception as redis_error:
                logger.error("Redis error: %s", redis_error)
                # Continue with JWT validation only
                request.state.session_id = session_id

        except jwt.ExpiredSignatureError as exc:
            logger.warning("Session %s has expired", session_token)

            # For questionnaire endpoints, generate a new session instead of failing
            if is_questionnaire_path:
                logger.warning("Expired token for questionnaire endpoint - generating new session")
                request.state.session_id = str(uuid.uuid4())
                return await call_next(request)

            # For other endpoints, require authentication
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired"
            ) from exc
        except jwt.InvalidTokenError as exc:
            logger.error("Invalid JWT token: %s", exc)

            # Special handling for questionnaire endpoints - generate new session instead of failing
            if is_questionnaire_path:
                logger.warning("Invalid token for questionnaire endpoint - generating new session")
                request.state.session_id = str(uuid.uuid4())
                return await call_next(request)

            # For other endpoints, require valid authentication
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session token"
            ) from exc
    # If no token but it's a questionnaire path, generate a new session ID
    elif is_questionnaire_path:
        request.state.session_id = str(uuid.uuid4())
        logger.info("Generated new session ID for questionnaire endpoint: %s", request.state.session_id)

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

# Direct API health endpoint with additional debugging
@app.route("/api/health", methods=["GET"])
async def direct_api_health(_request):
    """Direct handler for /api/health to bypass middleware and routing issues"""
    logger.info("Direct API health endpoint accessed")
    try:
        # Return a simple response with no dependencies
        return JSONResponse(
            content={
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "api_gateway",
                "version": "compatibility",
                "direct_handler": True
            },
            status_code=200
        )
    except Exception as e:
        logger.error("Error in direct health handler: %s", e)
        logger.error(traceback.format_exc())
        # Most basic response possible
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500
        )

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

# Legacy path mappings
LEGACY_PATHS = {
    # Root level paths
    "/chart": "/api/chart",
    "/questionnaire": "/api/questionnaire",
    "/session": "/api/session",
    "/geocode": "/api/geocode",
    "/health": "/api/health"
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
    """
    Proxy requests to the AI service.

    This endpoint forwards requests from the API gateway to the AI service,
    handling errors and providing fallbacks when necessary.
    """
    # Extract the path from the request
    path = request.url.path

    # Remove leading '/api/v1/' if present to avoid double api prefixes
    if path.startswith('/api/v1/'):
        path = path[8:]  # Remove '/api/v1/'
    # Also remove '/api/' prefix if present
    elif path.startswith('/api/'):
        path = path[5:]  # Remove '/api/' prefix

    # Normalize path - remove leading slash to avoid double slashes
    path = path.lstrip('/')

    # Get the AI service URL from environment
    ai_service_url = os.getenv("AI_SERVICE_URL", "http://ai_service:8001")

    # Remove trailing slash from AI service URL if present
    ai_service_url = ai_service_url.rstrip('/')

    # Construct target URL with normalized path
    target_url = f"{ai_service_url}/api/v1/{path}"

    # Log the full target URL for debugging
    logger.info("Proxying request to: %s", target_url)

    try:
        # Get request body for POST/PUT methods
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            request_body = await request.body()

            # For debugging: log the request body if it's a questionnaire request
            if "questionnaire" in path and request_body:
                try:
                    request_data = json.loads(request_body)
                    logger.debug("Request data: %s", request_data)
                except Exception:
                    logger.debug("Could not parse request body as JSON")

        # Make the request to the AI service with explicit SSL verification
        async with httpx.AsyncClient(
            timeout=60.0,
            verify=True  # Explicitly enable SSL verification
        ) as client:
            headers = {k: v for k, v in request.headers.items()
                      if k.lower() not in ["host", "content-length"]}

            # Send the request to the AI service
            if request.method == "GET":
                response = await client.get(target_url, params=dict(request.query_params), headers=headers)
            elif request.method == "POST":
                response = await client.post(target_url, content=request_body, headers=headers)
            elif request.method == "PUT":
                response = await client.put(target_url, content=request_body, headers=headers)
            elif request.method == "DELETE":
                response = await client.delete(target_url, headers=headers)
            else:
                return JSONResponse(
                    status_code=405,
                    content={"error": "Method not allowed", "detail": f"Method {request.method} is not supported"}
                )

        # Log the response status
        logger.info("\n%s %s - %s %s\n%s\n",
                   request.method, path, response.status_code, response.reason_phrase,
                   "-" * 80)

        # Return the response from the AI service
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    except Exception as e:
        logger.error("Error proxying API request: %s", e)

        # Handle the error with a friendly message
        error_detail = str(e)
        if "Connection refused" in error_detail:
            error_message = "AI service is currently unavailable. Please try again later."
        elif "Read timed out" in error_detail:
            error_message = "Request to AI service timed out. Please try again."
        else:
            error_message = f"Error connecting to AI service: {error_detail}"

        # Return a JSON error response
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": error_message,
                    "type": "ServiceUnavailableError",
                    "request_id": str(uuid.uuid4())
                }
            }
        )

# API v1 routes - Proxy all requests to the AI service
@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], response_model=None)
async def api_proxy_v1(request: Request, path: str):
    """Proxy requests to the v1 API endpoints"""
    logger.debug("Proxying request to v1 API path: %s", path)
    return await proxy_to_ai_service(request)

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

# Legacy API routes - Proxy with path rewriting
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"], response_model=None, include_in_schema=True)
async def api_proxy(request: Request, path: str):
    """Proxy requests with legacy path rewriting"""
    # Skip specific endpoints that have dedicated handlers
    if path == "" or request.url.path == "/" or request.url.path == "/health" or request.url.path == "/api/health" or request.url.path == "/api/basic-health":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found - handled by dedicated endpoint"
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

    # If this is a legacy path, update path to match expected API path
    if rewritten:
        # Remove the /api prefix from the path since proxy_to_ai_service will add it
        if target_path.startswith("/api/"):
            path = target_path[5:]  # Remove /api/ prefix
        else:
            path = target_path

    response_data = await proxy_to_ai_service(request)

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
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as e:
        logger.error("WebSocket error for session %s: %s", session_id, e)

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

            # Connect to AI service
            await websocket_proxy.connect(websocket, session_id)

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
