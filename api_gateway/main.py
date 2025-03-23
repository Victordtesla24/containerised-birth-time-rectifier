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
from typing import Optional, Dict, Any, List, Union
import asyncio
from datetime import datetime
import json

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
    """Geocode a location and return coordinates"""
    # Parse request body
    body = await request.json()
    query = body.get("query", "")

    if not query:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing query parameter"}
        )

    logger.info(f"Geocoding location: {query}")

    # Mock geocoding response - in a real implementation, this would call an external API
    mock_response = {
        "results": [
            {
                "formatted_address": "New York, NY, USA",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "confidence": 0.9
            }
        ],
        "status": "success"
    }

    return mock_response

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
    session_id = None

    try:
        # Accept the connection
        await websocket.accept()
        logger.info(f"WebSocket connection established for client {client_id}")

        # Receive initialization message with authentication
        try:
            init_message = await websocket.receive_json()
            session_id = init_message.get("session_id")
            token = init_message.get("token")

            # Validate initialization message
            if not init_message.get("type") == "initialize" or not session_id:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid initialization message. Must include type='initialize' and session_id",
                    "timestamp": datetime.now().isoformat()
                })
                await websocket.close(1008)  # Policy violation
                logger.warning(f"Invalid initialization message from client {client_id}")
                return

            # Verify token if provided
            if token:
                try:
                    verify_token(token)
                except HTTPException as auth_error:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Authentication failed: {auth_error.detail}",
                        "timestamp": datetime.now().isoformat()
                    })
                    await websocket.close(1008)  # Policy violation
                    logger.warning(f"Authentication failed for client {client_id}")
                    return

            # Send acknowledgment
            await websocket.send_json({
                "type": "initialize_ack",
                "session_id": session_id,
                "client_id": client_id,
                "timestamp": datetime.now().isoformat()
            })

            # Start WebSocket proxy with proper error handling and recovery
            await websocket_proxy.handle_websocket(
                websocket=websocket,
                session_id=session_id,
                upstream_url=f"{AI_SERVICE_WS_URL}/{session_id}",
                client_id=client_id,
                token=token or "",
                ping_interval=int(os.getenv("WS_PING_INTERVAL", "30"))
            )

        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JSON in initialization message",
                "timestamp": datetime.now().isoformat()
            })
            await websocket.close(1003)  # Unsupported data
            logger.warning(f"Invalid JSON from client {client_id}")
            return

    except Exception as e:
        logger.error(f"Error in WebSocket handler for client {client_id}: {str(e)}")
        try:
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
        if session_id:
            logger.info(f"WebSocket connection closed for client {client_id}, session {session_id}")
        else:
            logger.info(f"WebSocket connection closed for client {client_id}")

# API v1 routes
@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def api_v1_proxy(request: Request, path: str):
    """Proxy all API v1 requests to the AI service"""
    return await proxy_to_ai_service(request, f"api/v1/{path}")

# Legacy API routes (without /api/v1 prefix)
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def legacy_api_proxy(request: Request, path: str):
    """Proxy legacy API requests to the AI service"""
    # Skip static files and other non-API routes
    if path.startswith(("_next/", "static/", "favicon.ico")):
        raise HTTPException(status_code=404, detail="Not found")

    return await proxy_to_ai_service(request, path)

async def proxy_to_ai_service(request: Request, path: str):
    """
    Proxy a request to the AI service with enhanced error handling and retry logic.

    This implementation follows the Enhanced Error Handling Sequence specified in the
    architecture sequence diagram, including proper retry logic, intelligent fallbacks,
    and comprehensive error reporting.
    """
    # Get request body
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()

    # Get request headers
    headers = dict(request.headers)
    # Remove headers that should not be forwarded
    headers.pop("host", None)

    # Get query parameters
    params = dict(request.query_params)

    # Create target URL
    target_url = f"{AI_SERVICE_URL}/{path}"

    # Get client IP for logging
    client_ip = request.client.host if request.client else "unknown"
    request_id = str(uuid.uuid4())

    # Add request ID to headers for tracking
    headers["X-Request-ID"] = request_id

    # Log incoming request
    logger.info(f"Proxying request {request_id} from {client_ip} to {target_url} ({request.method})")

    # Enhanced retry configuration with endpoint-specific settings
    retry_config = {
        # Chart generation and rectification endpoints need more retries and longer timeouts
        "chart": {
            "max_retries": 5,
            "base_timeout": 90.0,
            "retry_delay": 1.0,
            "backoff_factor": 2.0,
            "max_timeout": 180.0
        },
        # Questionnaire endpoints need moderate retries and timeouts
        "questionnaire": {
            "max_retries": 4,
            "base_timeout": 60.0,
            "retry_delay": 0.5,
            "backoff_factor": 1.5,
            "max_timeout": 120.0
        },
        # Export endpoints need longer timeouts but fewer retries
        "export": {
            "max_retries": 3,
            "base_timeout": 120.0,
            "retry_delay": 2.0,
            "backoff_factor": 1.5,
            "max_timeout": 240.0
        },
        # Default configuration for other endpoints
        "default": {
            "max_retries": 3,
            "base_timeout": 60.0,
            "retry_delay": 0.5,
            "backoff_factor": 1.5,
            "max_timeout": 120.0
        }
    }

    # Determine which configuration to use based on the path
    config_key = "default"
    for key in retry_config:
        if key in path:
            config_key = key
            break

    config = retry_config[config_key]

    # Extract configuration values
    max_retries = config["max_retries"]
    base_timeout = config["base_timeout"]
    retry_delay = config["retry_delay"]
    backoff_factor = config["backoff_factor"]
    max_timeout = config["max_timeout"]

    # Endpoint-specific adjustments for timeouts
    if "rectify" in path:
        base_timeout = max(base_timeout, 180.0)  # Minimum 3 minutes for rectification
    elif "generate" in path and "chart" in path:
        base_timeout = max(base_timeout, 90.0)   # Minimum 90 seconds for chart generation
    elif "export" in path:
        base_timeout = max(base_timeout, 120.0)  # Minimum 2 minutes for exports

    # Initialize the adaptive timeout (will increase with retries)
    timeout = base_timeout

    # Categorize endpoints for retry logic and alternative routing
    critical_endpoints = [
        "chart/generate",
        "chart/rectify",
        "questionnaire/submit",
        "questionnaire/complete",
        "chart/export"
    ]
    idempotent_methods = ["GET", "HEAD", "OPTIONS"]
    can_retry = request.method in idempotent_methods or any(endpoint in path for endpoint in critical_endpoints)

    # Keep track of attempts
    attempt = 0
    last_error = None
    start_time = time.time()
    response_data = None
    status_code = None

    # Set up circuit breaker for the endpoint
    circuit_breaker_key = path.split("/")[0] if "/" in path else path
    circuit_open = False

    # Check if circuit breaker is open for this endpoint category
    circuit_breaker_state = await _get_circuit_breaker_state(circuit_breaker_key)
    if circuit_breaker_state.get("status") == "open":
        # Circuit is open - check if cooldown period has elapsed
        last_failure = circuit_breaker_state.get("last_failure", 0)
        cooldown_period = circuit_breaker_state.get("cooldown_period", 60)

        if time.time() - last_failure < cooldown_period:
            # Circuit is still open - use fallback if available or return error
            logger.warning(f"Circuit breaker open for {circuit_breaker_key}, request rejected")
            return JSONResponse(
                content={
                    "detail": "Service temporarily unavailable due to repeated failures",
                    "request_id": request_id,
                    "error_type": "circuit_open",
                    "retry_after": int(cooldown_period - (time.time() - last_failure))
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": str(int(cooldown_period - (time.time() - last_failure)))}
            )
        else:
            # Cooldown period has elapsed - reset circuit breaker to half-open
            await _update_circuit_breaker_state(circuit_breaker_key, {
                "status": "half-open",
                "failure_count": 0,
                "last_failure": 0
            })
            circuit_open = False

    # Try request with enhanced retry logic
    while attempt <= max_retries:
        attempt += 1
        try:
            # Calculate current timeout with exponential backoff
            if attempt > 1:
                # Increase timeout with each retry, but cap at max_timeout
                timeout = min(max_timeout, base_timeout * (backoff_factor ** (attempt - 1)))

            async with httpx.AsyncClient() as client:
                # Log retry attempts
                if attempt > 1:
                    logger.info(f"Retry attempt {attempt-1} for request {request_id} to {target_url} (timeout: {timeout:.1f}s)")

                # Send request to AI service with current timeout
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    params=params,
                    headers=headers,
                    content=body,
                    cookies=request.cookies,
                    follow_redirects=True,
                    timeout=timeout
                )

                # Log successful response
                elapsed = time.time() - start_time
                logger.info(f"Request {request_id} completed with status {response.status_code} in {elapsed:.2f}s")

                # Capture response data and status code
                status_code = response.status_code

                # Try to parse response as JSON
                try:
                    response_data = response.json()
                except ValueError:
                    # Not JSON, use text
                    response_data = response.text

                # Reset circuit breaker on success if it was half-open
                circuit_breaker_state = await _get_circuit_breaker_state(circuit_breaker_key)
                if circuit_breaker_state.get("status") == "half-open":
                    await _update_circuit_breaker_state(circuit_breaker_key, {
                        "status": "closed",
                        "failure_count": 0,
                        "last_failure": 0,
                        "success_count": circuit_breaker_state.get("success_count", 0) + 1
                    })

                # Check if response indicates an error (5xx)
                if 500 <= response.status_code < 600:
                    error_data = {"status_code": response.status_code}

                    # Try to extract error details if JSON
                    try:
                        if response.headers.get("content-type") == "application/json":
                            response_json = response.json()
                            if "detail" in response_json:
                                error_data["detail"] = response_json["detail"]
                    except Exception:
                        # If parsing fails, continue with the response as is
                        pass

                    # Log backend error
                    logger.error(f"Backend service error: {error_data} for request {request_id}")

                    # Update circuit breaker failure count
                    circuit_breaker_state = await _get_circuit_breaker_state(circuit_breaker_key)
                    failure_count = circuit_breaker_state.get("failure_count", 0) + 1

                    # Update circuit breaker state
                    await _update_circuit_breaker_state(circuit_breaker_key, {
                        "status": "closed",
                        "failure_count": failure_count,
                        "last_failure": time.time()
                    })

                    # If failure count exceeds threshold, open circuit breaker
                    if failure_count >= 5:  # Threshold for opening circuit
                        await _update_circuit_breaker_state(circuit_breaker_key, {
                            "status": "open",
                            "failure_count": failure_count,
                            "last_failure": time.time(),
                            "cooldown_period": 60  # 1 minute cooldown
                        })
                        circuit_open = True

                    # Check if we should retry based on error and endpoint
                    if attempt <= max_retries and can_retry:
                        # Store error and retry after delay
                        last_error = error_data
                        retry_wait = retry_delay * (backoff_factor ** (attempt - 1))
                        await asyncio.sleep(retry_wait)
                        continue

                # Create response with the same status code, headers, and body
                return JSONResponse(
                    content=response_data,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )

        except httpx.TimeoutException as e:
            # Handle timeout specifically
            logger.error(f"Timeout error connecting to AI service for request {request_id}: {e}")
            last_error = {"type": "timeout", "detail": str(e)}

            # Update circuit breaker for timeout errors
            circuit_breaker_state = await _get_circuit_breaker_state(circuit_breaker_key)
            timeout_count = circuit_breaker_state.get("timeout_count", 0) + 1

            await _update_circuit_breaker_state(circuit_breaker_key, {
                "status": circuit_breaker_state.get("status", "closed"),
                "timeout_count": timeout_count,
                "last_timeout": time.time()
            })

            # If too many timeouts, consider opening circuit breaker
            if timeout_count >= 3:  # Lower threshold for timeouts
                await _update_circuit_breaker_state(circuit_breaker_key, {
                    "status": "open",
                    "timeout_count": timeout_count,
                    "last_failure": time.time(),
                    "cooldown_period": 30  # 30 second cooldown for timeouts
                })
                circuit_open = True

            # Only retry idempotent requests or critical endpoints on timeout
            if attempt <= max_retries and (request.method in idempotent_methods or any(endpoint in path for endpoint in critical_endpoints)):
                retry_wait = retry_delay * (backoff_factor ** (attempt - 1))
                logger.info(f"Waiting {retry_wait:.2f}s before retry attempt {attempt}")
                await asyncio.sleep(retry_wait)
                continue

            # Return timeout-specific error
            return JSONResponse(
                content={
                    "detail": "The request to the backend service timed out",
                    "request_id": request_id,
                    "error_type": "timeout",
                    "retry_after": 5,
                    "timeout_value": timeout
                },
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                headers={"Retry-After": "5"}
            )

        except httpx.RequestError as e:
            # Connection errors, DNS failures, etc.
            logger.error(f"Connection error to AI service for request {request_id}: {e}")
            last_error = {"type": "connection", "detail": str(e)}

            # Update circuit breaker for connection errors
            circuit_breaker_state = await _get_circuit_breaker_state(circuit_breaker_key)
            connection_errors = circuit_breaker_state.get("connection_errors", 0) + 1

            await _update_circuit_breaker_state(circuit_breaker_key, {
                "status": circuit_breaker_state.get("status", "closed"),
                "connection_errors": connection_errors,
                "last_connection_error": time.time()
            })

            # If too many connection errors, consider opening circuit breaker
            if connection_errors >= 3:
                await _update_circuit_breaker_state(circuit_breaker_key, {
                    "status": "open",
                    "connection_errors": connection_errors,
                    "last_failure": time.time(),
                    "cooldown_period": 45  # 45 second cooldown for connection errors
                })
                circuit_open = True

            # Check if we should retry
            if attempt <= max_retries and can_retry:
                retry_wait = retry_delay * (backoff_factor ** (attempt - 1))
                logger.info(f"Waiting {retry_wait:.2f}s before retry attempt {attempt}")
                await asyncio.sleep(retry_wait)
                continue

            # Return connection-specific error
            return JSONResponse(
                content={
                    "detail": "Error connecting to backend service",
                    "request_id": request_id,
                    "error_type": "connection",
                    "retry_after": 5,
                    "error_message": str(e)
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "5"}
            )

        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error proxying request {request_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            last_error = {"type": "unknown", "detail": str(e)}

            # Update circuit breaker for unexpected errors
            circuit_breaker_state = await _get_circuit_breaker_state(circuit_breaker_key)
            unexpected_errors = circuit_breaker_state.get("unexpected_errors", 0) + 1

            await _update_circuit_breaker_state(circuit_breaker_key, {
                "status": circuit_breaker_state.get("status", "closed"),
                "unexpected_errors": unexpected_errors,
                "last_unexpected_error": time.time()
            })

            # Don't retry on unexpected errors unless idempotent
            if attempt <= max_retries and request.method in idempotent_methods:
                retry_wait = retry_delay * (backoff_factor ** (attempt - 1))
                logger.info(f"Waiting {retry_wait:.2f}s before retry attempt {attempt}")
                await asyncio.sleep(retry_wait)
                continue

            # Return general server error
            return JSONResponse(
                content={
                    "detail": "Internal server error while processing your request",
                    "request_id": request_id,
                    "error_type": "server_error",
                    "error_message": str(e)
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # If we've exhausted all retries, return appropriate error based on last error
    logger.error(f"All retry attempts failed for request {request_id}")

    # Update circuit breaker to open state after max retries
    await _update_circuit_breaker_state(circuit_breaker_key, {
        "status": "open",
        "failure_count": circuit_breaker_state.get("failure_count", 0) + 1,
        "last_failure": time.time(),
        "cooldown_period": 60  # 1 minute cooldown
    })

    # Determine appropriate error response based on last error
    if last_error and isinstance(last_error, dict):
        error_type = last_error.get("type", "unknown")
        if error_type == "timeout":
            return JSONResponse(
                content={
                    "detail": "The request to the backend service timed out after multiple attempts",
                    "request_id": request_id,
                    "error_type": "timeout",
                    "retry_after": 10,
                    "attempts_made": attempt
                },
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                headers={"Retry-After": "10"}
            )
        elif error_type == "connection":
            return JSONResponse(
                content={
                    "detail": "Unable to connect to backend service after multiple attempts",
                    "request_id": request_id,
                    "error_type": "connection",
                    "retry_after": 10,
                    "attempts_made": attempt
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                headers={"Retry-After": "10"}
            )

    # Default error response after retries
    return JSONResponse(
        content={
            "detail": "Backend service failed to process the request after multiple attempts",
            "request_id": request_id,
            "error_type": "server_error",
            "attempts_made": attempt,
            "last_status_code": status_code
        },
        status_code=status.HTTP_502_BAD_GATEWAY
    )

# Helper functions for circuit breaker pattern
async def _get_circuit_breaker_state(key: str) -> Dict[str, Any]:
    """Get the current state of a circuit breaker"""
    # In a real implementation, this would use Redis or another shared store
    # For this implementation, we'll use a global dictionary
    if not hasattr(_get_circuit_breaker_state, "state_store"):
        _get_circuit_breaker_state.state_store = {}

    return _get_circuit_breaker_state.state_store.get(key, {
        "status": "closed",
        "failure_count": 0,
        "last_failure": 0,
        "timeout_count": 0,
        "connection_errors": 0,
        "unexpected_errors": 0
    })

async def _update_circuit_breaker_state(key: str, state: Dict[str, Any]) -> None:
    """Update the state of a circuit breaker"""
    # In a real implementation, this would use Redis or another shared store
    if not hasattr(_update_circuit_breaker_state, "state_store"):
        _update_circuit_breaker_state.state_store = {}

    _update_circuit_breaker_state.state_store[key] = {
        **_get_circuit_breaker_state.state_store.get(key, {}),
        **state
    }

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
