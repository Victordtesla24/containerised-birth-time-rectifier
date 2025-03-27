#!/usr/bin/env python3
"""
Simplified API Gateway for direct testing.
"""

import asyncio
import httpx
import uvicorn
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Initialize FastAPI app
app = FastAPI(title="Simplified API Gateway")

# Constants
AI_SERVICE_URL = "http://localhost:8000"

@app.get("/health")
async def health():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "simplified-gateway"}

@app.get("/api/session/init")
async def session_init():
    """Create a new session."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{AI_SERVICE_URL}/api/v1/session/init")
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to initialize session: {str(e)}"}
        )

@app.post("/api/geocode")
async def geocode(request: Request):
    """Simplified geocode endpoint."""
    try:
        # Get session ID from header
        session_id = request.headers.get("X-Session-ID", "")

        # Get request body
        body = await request.json()

        # Forward to AI service
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.post(
                f"{AI_SERVICE_URL}/api/v1/geocode",
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Session-ID": session_id,
                    "X-Request-ID": str(uuid.uuid4())
                }
            )

            # Return the response
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.status_code == 200 else {"error": "Geocode service error"}
            )
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"error": "Request timed out"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error: {str(e)}"}
        )

@app.post("/api/geocode/static")
async def geocode_static():
    """Static geocode endpoint that doesn't call any external service."""
    await asyncio.sleep(0.1)  # Small delay
    return {
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

if __name__ == "__main__":
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=3001)
