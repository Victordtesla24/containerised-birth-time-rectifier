"""
Session management route handlers for the Birth Time Rectifier API Gateway.
"""

from fastapi import APIRouter, HTTPException, Request, status
from typing import Dict, Any, Optional
import httpx
import os
import logging
import time
import uuid
import traceback
import json
from fastapi.responses import JSONResponse

# Set up logging
logger = logging.getLogger("api_gateway.routes.session")

# Create router
router = APIRouter(prefix="/api/session", tags=["session"])

# AI Service URL
AI_SERVICE_URL = os.environ.get("AI_SERVICE_URL", "http://localhost:8001")
if AI_SERVICE_URL and AI_SERVICE_URL.endswith("/"):
    AI_SERVICE_URL = AI_SERVICE_URL[:-1]

# Helper function to request data from the AI service
async def request_ai_service(endpoint: str, data: Dict[str, Any] = {}, method: str = "POST") -> Dict[str, Any]:
    """Send a request to the AI service for session operations"""
    ai_service_url = AI_SERVICE_URL

    url = f"{ai_service_url}/api/v1/{endpoint}"
    logger.info(f"Requesting AI service at {url}")

    try:
        # Use proper HTTP client configuration
        timeout_seconds = 15.0  # Increase timeout for reliability

        async with httpx.AsyncClient(
            verify=True,  # Explicitly enable SSL verification
            timeout=timeout_seconds
        ) as client:
            if method == "GET":
                response = await client.get(url, params=data)
            else:
                response = await client.post(url, json=data)

            if response.status_code != 200:
                logger.error(f"AI service returned error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"AI service error: {response.text}"
                )

            return response.json()
    except httpx.ConnectError as e:
        logger.error(f"Connection error to AI service: {e} - URL: {url}")
        # Don't use fallbacks - propagate the real error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service connection error: {str(e)}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error to AI service: {e} - URL: {url}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service request error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error requesting AI service: {e} - {type(e).__name__}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

def save_local_session(session_id: str, session_data: Dict[str, Any]) -> bool:
    """
    Save session data to a local file.
    Used as a fallback when Redis is unavailable.

    Args:
        session_id: The unique session ID
        session_data: Session data to store

    Returns:
        bool: True if the session was saved successfully, False otherwise
    """
    try:
        # Create sessions directory if it doesn't exist
        sessions_dir = os.path.abspath("sessions")
        os.makedirs(sessions_dir, exist_ok=True)

        # Log the full path for debugging
        filepath = os.path.join(sessions_dir, f"{session_id}.json")
        logger.info(f"Saving session to {filepath}")

        # Write session data to file
        with open(filepath, "w") as f:
            json.dump(session_data, f)

        logger.info(f"Successfully saved session {session_id} to file")
        return True
    except Exception as e:
        logger.error(f"Error saving session to file: {e}")
        logger.exception("Exception details:")
        return False

@router.get("/init")
async def initialize_session(request: Request):
    """
    Initialize a new session.
    First tries to create a local session, then proxies to the AI service as a secondary option.
    """
    # Create a local session as the primary method
    try:
        # Generate a session locally
        session_id = str(uuid.uuid4())
        expires_at = int(time.time()) + 3600 * 24  # 24 hours expiry

        # Create session data
        session_data = {
            "session_id": session_id,
            "created_at": int(time.time()),
            "data": {
                "status": "active",
                "expires_at": expires_at,
                "created_at": int(time.time()),
                "local_fallback": True
            }
        }

        # Save locally
        if save_local_session(session_id, session_data):
            # Return session info
            result = {
                "session_id": session_id,
                "expires_at": expires_at,
                "status": "active",
                "created_by": "api_gateway"
            }

            logger.info(f"Created local session: {session_id}")

            # Return the JSON response with correct content-type
            return JSONResponse(
                content=result,
                status_code=200,
                headers={"Content-Type": "application/json"}
            )
        else:
            logger.error("Failed to create local session, trying AI service...")
    except Exception as e:
        logger.error(f"Error creating local session: {e}")
        logger.info("Trying AI service as fallback...")

    # Fall back to AI service if local creation fails
    try:
        # Construct target URL
        target_url = f"{AI_SERVICE_URL}/api/v1/session/init"

        logger.info(f"Forwarding session initialization request to {target_url}")

        # Extract headers
        headers = {k: v for k, v in request.headers.items()
                  if k.lower() not in ["host", "content-length"]}

        # Add important headers
        if "accept" not in {k.lower(): v for k, v in headers.items()}:
            headers["Accept"] = "application/json"

        logger.debug(f"Request headers: {headers}")

        # Try to make request to AI service with a shorter timeout
        try:
            async with httpx.AsyncClient(
                verify=True,  # Explicitly enable SSL verification
                timeout=5.0  # Shorter timeout for quicker fallback
            ) as client:
                logger.debug(f"Sending request to AI service: {target_url}")
                response = await client.get(target_url, headers=headers)
                logger.debug(f"Response status: {response.status_code}")
                logger.debug(f"Response headers: {response.headers}")

                # For successful responses, log the response content
                if response.status_code < 400:
                    try:
                        logger.debug(f"Response content: {response.text}")
                    except Exception:
                        logger.debug("Could not log response content")

                # Check response status
                if response.status_code >= 400:
                    logger.error(f"Error from AI service: {response.status_code} - {response.text}")
                    # Try to parse the error response as JSON
                    try:
                        error_detail = response.json().get("detail", response.text)
                    except:
                        error_detail = response.text

                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error initializing session: {error_detail}"
                    )

                # Parse response
                try:
                    # Try to parse JSON response
                    result = response.json()
                    logger.info(f"Session initialized successfully: {result.get('session_id', 'unknown')}")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing session response: {e}")
                    logger.error(f"Invalid JSON response: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Invalid response from session service"
                    )

        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            # AI service connection failed, fall back to local session creation
            logger.warning(f"AI service connection failed, using local fallback: {e}")

            # Generate a session locally
            session_id = str(uuid.uuid4())
            expires_at = int(time.time()) + 3600 * 24  # 24 hours expiry

            # Create session data
            session_data = {
                "session_id": session_id,
                "created_at": int(time.time()),
                "data": {
                    "status": "active",
                    "expires_at": expires_at,
                    "created_at": int(time.time()),
                    "local_fallback": True
                }
            }

            # Save locally
            save_local_session(session_id, session_data)

            # Return session info
            result = {
                "session_id": session_id,
                "expires_at": expires_at,
                "status": "active",
                "created_by": "api_gateway_fallback"
            }

            logger.info(f"Created fallback session locally: {session_id}")

            # Return the JSON response with correct content-type
            return JSONResponse(
                content=result,
                status_code=200,
                headers={"Content-Type": "application/json"}
            )

    except httpx.RequestError as e:
        logger.error(f"Error making request to session service: {e}")
        logger.exception("Full exception details:")

        # Create a session locally as fallback
        session_id = str(uuid.uuid4())
        expires_at = int(time.time()) + 3600 * 24  # 24 hours expiry

        # Create session data
        session_data = {
            "session_id": session_id,
            "created_at": int(time.time()),
            "data": {
                "status": "active",
                "expires_at": expires_at,
                "created_at": int(time.time()),
                "local_fallback": True
            }
        }

        # Save locally
        save_local_session(session_id, session_data)

        # Return session info with correct content-type
        result = {
            "session_id": session_id,
            "expires_at": expires_at,
            "status": "active",
            "created_by": "api_gateway_fallback"
        }

        logger.info(f"Created fallback session locally: {session_id}")

        # Return the JSON response with correct content-type
        return JSONResponse(
            content=result,
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
    except Exception as e:
        logger.error(f"Unhandled exception during session initialization: {e}")
        logger.exception("Exception details:")

        # Final fallback - create a session even if everything else fails
        session_id = str(uuid.uuid4())
        expires_at = int(time.time()) + 3600 * 24  # 24 hours expiry

        return JSONResponse(
            content={
                "session_id": session_id,
                "expires_at": expires_at,
                "status": "active",
                "created_by": "api_gateway_emergency_fallback"
            },
            status_code=200,
            headers={"Content-Type": "application/json"}
        )

@router.get("/status")
async def get_session_status(session_id: str):
    """
    Get the status of the current session.

    Returns session metadata including active status and expiration time.
    """
    logger.info(f"Getting status for session: {session_id}")

    # First check for a local session
    try:
        sessions_dir = os.path.abspath("sessions")
        filepath = os.path.join(sessions_dir, f"{session_id}.json")

        logger.debug(f"Checking for local session file: {filepath}")

        if os.path.exists(filepath):
            logger.info(f"Found local session file: {filepath}")
            with open(filepath, "r") as f:
                session_data = json.load(f)
            logger.info(f"Retrieved local fallback session: {session_id}")

            # Return session info properly formatted
            return JSONResponse(content={
                "session_id": session_id,
                "status": session_data.get("data", {}).get("status", "active"),
                "last_activity": int(time.time())
            })
    except Exception as local_error:
        logger.error(f"Error retrieving local session: {local_error}")
        logger.exception("Exception details:")
        # Continue to try the AI service

    try:
        # Forward to AI service
        result = await request_ai_service(
            "session/status",
            {"session_id": session_id},
            method="GET"
        )

        return result
    except Exception as e:
        logger.error(f"Error getting session status: {e}")

        # Try again with local session (in case we missed it)
        try:
            sessions_dir = os.path.abspath("sessions")
            filepath = os.path.join(sessions_dir, f"{session_id}.json")

            # List all files in the sessions directory to help with debugging
            try:
                logger.debug(f"Files in {sessions_dir}:")
                for f in os.listdir(sessions_dir):
                    logger.debug(f" - {f}")
            except Exception as list_err:
                logger.error(f"Error listing files in sessions directory: {list_err}")

            if os.path.exists(filepath):
                logger.info(f"Found local session file on second attempt: {filepath}")
                with open(filepath, "r") as f:
                    session_data = json.load(f)
                logger.info(f"Retrieved local fallback session on second attempt: {session_id}")

                # Return session info properly formatted
                return JSONResponse(content={
                    "session_id": session_id,
                    "status": session_data.get("data", {}).get("status", "active"),
                    "last_activity": int(time.time())
                })
        except Exception as local_error:
            logger.error(f"Error retrieving local session on second attempt: {local_error}")
            logger.exception("Exception details:")

        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session status: {str(e)}"
        )

@router.post("/data")
async def update_session_data(session_id: str, data: Dict[str, Any]):
    """
    Update session data.

    Adds or updates custom data in the session.
    """
    try:
        # Forward to AI service
        result = await request_ai_service(
            "session/data",
            {"session_id": session_id, **data},
            method="POST"
        )

        return result
    except Exception as e:
        logger.error(f"Error updating session data: {e}")

        # Try to update local session
        try:
            filepath = os.path.join("sessions", f"{session_id}.json")
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    session_data = json.load(f)

                # Update session data
                if "data" in session_data:
                    session_data["data"].update(data)
                else:
                    session_data["data"] = data

                # Save updated session
                with open(filepath, "w") as f:
                    json.dump(session_data, f)

                logger.info(f"Updated local fallback session: {session_id}")
                return {
                    "status": "success",
                    "message": "Session data updated (local fallback)"
                }
        except Exception as local_error:
            logger.error(f"Error updating local session: {local_error}")

        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session data: {str(e)}"
        )

@router.get("/data")
async def get_session_data(session_id: str):
    """
    Get session data.

    Returns all custom data stored in the session.
    """
    try:
        # Forward to AI service
        result = await request_ai_service(
            "session/data",
            {"session_id": session_id},
            method="GET"
        )

        return result
    except Exception as e:
        logger.error(f"Error getting session data: {e}")

        # Try to get data from local session
        try:
            filepath = os.path.join("sessions", f"{session_id}.json")
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    session_data = json.load(f)
                logger.info(f"Retrieved data from local fallback session: {session_id}")
                return session_data.get("data", {})
        except Exception as local_error:
            logger.error(f"Error retrieving data from local session: {local_error}")

        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session data: {str(e)}"
        )
