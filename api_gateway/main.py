"""
Birth Time Rectifier API Gateway
--------------------------------
Main application file for the API Gateway service.
Acts as a central point for routing requests to appropriate microservices.
Includes WebSocket proxy functionality for real-time updates.
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import os
import sys
import httpx
import uuid
from typing import Optional, Dict, Any

# Import WebSocket proxy
from api_gateway.websocket_proxy import proxy as websocket_proxy

# Import routers
from api_gateway.routes.chart import router as chart_router
from api_gateway.routes.questionnaire import router as questionnaire_router

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
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
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, this should be restricted
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
async def websocket_endpoint(websocket: WebSocket, session_id: str):
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
async def default_websocket_endpoint(websocket: WebSocket):
    """
    Default WebSocket endpoint that generates a session ID automatically.
    Proxies the connection to the AI service.

    Args:
        websocket: The WebSocket connection
    """
    # Generate a unique session ID
    session_id = f"auto-{uuid.uuid4().hex[:8]}"
    logger.info(f"Auto-generated session ID for WebSocket connection: {session_id}")

    try:
        # Connect to the WebSocket proxy
        await websocket_proxy.connect(websocket, session_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for auto-generated session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for auto-generated session {session_id}: {e}")

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
    """Proxy a request to the AI service"""
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

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                params=params,
                headers=headers,
                content=body,
                cookies=request.cookies,
                follow_redirects=True,
                timeout=60.0  # 60 second timeout
            )

            # Create response with the same status code, headers, and body
            return JSONResponse(
                content=response.json() if response.headers.get("content-type") == "application/json" else response.text,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
    except httpx.RequestError as e:
        logger.error(f"Error proxying request to AI service: {e}")
        return JSONResponse(
            content={"detail": "Error connecting to backend service"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"Unexpected error proxying request: {e}")
        return JSONResponse(
            content={"detail": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
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
