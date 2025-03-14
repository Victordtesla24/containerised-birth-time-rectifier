"""
Error handling middleware for the Birth Time Rectifier API.
Provides standardized error responses across all endpoints.
"""

import logging
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Dict, List, Any, Optional, Union, Callable, Awaitable

# Setup logging
logger = logging.getLogger("birth-time-rectifier.error-handling")

# Define ExceptionHandler type aliases for type checking
RequestValidationExceptionHandler = Callable[[Request, RequestValidationError], Awaitable[JSONResponse]]
HTTPExceptionHandler = Callable[[Request, HTTPException], Awaitable[JSONResponse]]

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle validation errors from pydantic models.
    Returns a standardized error response with field-specific validation details.

    Args:
        request: The FastAPI request
        exc: The validation exception

    Returns:
        JSONResponse with standardized error format
    """
    # Extract error details
    errors = []

    for error in exc.errors():
        # Get the field name from the location
        field = ".".join(str(loc) for loc in error.get("loc", []))

        # Skip body validation errors without specific fields
        if field == "body":
            field = "request_body"

        # Create error detail
        errors.append({
            "field": field,
            "issue": error.get("msg", "Validation error"),
            "type": error.get("type", "unknown_error")
        })

    # Log the validation error
    logger.warning(f"Validation error for {request.url.path}: {errors}")

    # Return formatted response
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "invalid_request",
                "message": "The request was invalid",
                "details": errors
            }
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions.
    Returns a standardized error response for all HTTP exceptions.

    Args:
        request: The FastAPI request
        exc: The HTTP exception

    Returns:
        JSONResponse with standardized error format
    """
    # Map status codes to error codes
    error_codes = {
        401: "authentication_required",
        403: "permission_denied",
        404: "resource_not_found",
        409: "conflict",
        429: "rate_limit_exceeded",
    }

    # Get the error code or use generic status_code based code
    error_code = error_codes.get(exc.status_code, f"error_{exc.status_code}")

    # Extract details if available
    details = getattr(exc, "details", None)

    # Create error response
    error_response = {
        "error": {
            "code": error_code,
            "message": exc.detail
        }
    }

    # Add details if available
    if details:
        error_response["error"]["details"] = details

    # Add headers from exception if available
    headers = getattr(exc, "headers", None)

    # Log the HTTP exception with appropriate log level based on status code
    if exc.status_code >= 500:
        logger.error(f"HTTP exception {exc.status_code} for {request.url.path}: {exc.detail}")
    else:
        # Use warning level for all other HTTP exceptions including 4xx and 3xx
        # This ensures we don't miss important information in logs
        logger.warning(f"HTTP exception {exc.status_code} for {request.url.path}: {exc.detail}")

    # Return formatted response
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
        headers=headers
    )

def create_error_response(
    code: str,
    message: str,
    status_code: int = 400,
    details: Any = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.

    Args:
        code: Error code (e.g., "invalid_request")
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional details (any type that is JSON serializable)

    Returns:
        Dict with standardized error format
    """
    # Create response dict with explicit Any type to avoid typing issues
    response: Dict[str, Any] = {
        "error": {
            "code": code,
            "message": message
        }
    }

    # Add details if provided
    if details is not None:
        # Use explicit Dict[str, Any] type for error
        response["error"] = dict(response["error"])
        response["error"]["details"] = details

    return response
