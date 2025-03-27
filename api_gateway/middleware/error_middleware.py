"""
API Gateway Error Handling Middleware

This module provides error handling middleware for the API Gateway service,
using the shared error handler module from the AI service.
"""

import logging
import asyncio
import time
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from httpx import TimeoutException, HTTPStatusError, RequestError, Response as HTTPXResponse

# Import the shared error handler
from ai_service.utils.error_handler import (
    AppError,
    ErrorCode,
    convert_exception_to_error_response
)

# Configure logging
logger = logging.getLogger("api_gateway.error_middleware")

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling and standardizing error responses across the API.
    Uses the shared error handler module from the AI service.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_retries: int = 3,
        retry_delay: float = 0.5,
        retry_backoff_factor: float = 2.0,
        retry_status_codes: List[int] = [],
        debug_mode: bool = False
    ):
        super().__init__(app)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff_factor = retry_backoff_factor
        self.retry_status_codes = retry_status_codes or [502, 503, 504]
        self.debug_mode = debug_mode

        # Initialize retry statistics
        self.retry_stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "retry_by_status": {},
            "retry_by_error_type": {}
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request with error handling and retry logic."""
        # Extract request ID if present or generate one
        request_id = request.headers.get("X-Request-ID", f"req-{time.time()}")
        path = request.url.path

        # Log incoming request
        logger.debug(f"Processing request {request_id} to {path}")

        # Initialize retry counter and backoff
        retries = 0
        current_delay = self.retry_delay
        retry_attempted = False

        # Store the original request body for retries
        body = None
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                # Read and store request body for potential retries
                body = await request.body()
                # Create a copy of the request with the same body for each retry
                request = self._clone_request_with_body(request, body)
        except Exception as e:
            logger.error(f"Error reading request body: {str(e)}")

        # Check if this path should use enhanced retry logic
        should_retry = self._should_use_enhanced_retry(request)
        retry_start_time = time.time()

        while True:
            try:
                # Process the request
                response = await call_next(request)

                # Check if response indicates a retryable error
                if (response.status_code in self.retry_status_codes and
                    retries < self.max_retries and should_retry):
                    retry_attempted = True
                    retries += 1

                    # Update retry statistics
                    self.retry_stats["total_retries"] += 1
                    if str(response.status_code) not in self.retry_stats["retry_by_status"]:
                        self.retry_stats["retry_by_status"][str(response.status_code)] = 0
                    self.retry_stats["retry_by_status"][str(response.status_code)] += 1

                    logger.warning(
                        f"Retryable error detected (status: {response.status_code}, "
                        f"attempt: {retries}/{self.max_retries}) for request {request_id} to {path}"
                    )

                    # Implement backoff
                    await self._wait_with_backoff(current_delay)
                    current_delay *= self.retry_backoff_factor

                    # Clone request for retry
                    if body:
                        request = self._clone_request_with_body(request, body)

                    continue

                # If we previously retried and succeeded, log the success
                if retry_attempted and response.status_code < 500:
                    retry_time = time.time() - retry_start_time
                    self.retry_stats["successful_retries"] += 1
                    logger.info(
                        f"Request {request_id} succeeded after {retries} retries in {retry_time:.2f}s"
                    )

                    # Add retry information to response headers
                    if hasattr(response, "headers"):
                        response.headers["X-Retry-Count"] = str(retries)
                        response.headers["X-Retry-Time"] = f"{retry_time:.2f}s"

                return response

            except (TimeoutException, ConnectionError, RequestError) as e:
                # Handle retryable network errors
                if retries < self.max_retries and should_retry:
                    retry_attempted = True
                    retries += 1

                    # Update retry statistics
                    self.retry_stats["total_retries"] += 1
                    error_type = type(e).__name__
                    if error_type not in self.retry_stats["retry_by_error_type"]:
                        self.retry_stats["retry_by_error_type"][error_type] = 0
                    self.retry_stats["retry_by_error_type"][error_type] += 1

                    logger.warning(
                        f"Retryable error: {type(e).__name__} - {str(e)}, "
                        f"attempt: {retries}/{self.max_retries} for request {request_id} to {path}"
                    )

                    # Implement backoff
                    await self._wait_with_backoff(current_delay)
                    current_delay *= self.retry_backoff_factor

                    # Clone request for retry
                    if body:
                        request = self._clone_request_with_body(request, body)

                    continue
                else:
                    # Max retries reached, update failed stats
                    if retry_attempted:
                        self.retry_stats["failed_retries"] += 1

                    # Create error response using shared error handler
                    error_dict = self._create_error_dict(e, request_id, path, retries)
                    return JSONResponse(
                        status_code=error_dict.get("status_code", 500),
                        content={"error": error_dict.get("error", {})}
                    )

            except Exception as e:
                # Handle other errors (non-retryable)
                error_dict = self._create_error_dict(e, request_id, path, retries)
                return JSONResponse(
                    status_code=error_dict.get("status_code", 500),
                    content={"error": error_dict.get("error", {})}
                )

    def _should_use_enhanced_retry(self, request: Request) -> bool:
        """
        Determine if a request should use enhanced retry logic based on path and method.

        Args:
            request: The request to check

        Returns:
            True if enhanced retry should be used, False otherwise
        """
        # Get request method and path
        method = request.method
        path = request.url.path

        # Safe methods can always be retried
        if method in ["GET", "HEAD", "OPTIONS"]:
            return True

        # Specific paths that should use enhanced retry, even for mutation methods
        critical_paths = [
            "/api/chart/rectify",
            "/api/chart/generate",
            "/api/questionnaire/submit"
        ]

        # Check if path matches any critical path
        for critical_path in critical_paths:
            if critical_path in path:
                return True

        # Default to false for mutation methods on non-critical paths
        return False

    def _create_error_dict(
        self,
        exc: Exception,
        request_id: str,
        path: str,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Convert an exception to an error dictionary using the shared error handler.

        Args:
            exc: The exception that occurred
            request_id: The request ID
            path: The request path
            retry_count: Number of retries attempted

        Returns:
            Error dictionary
        """
        # Log the error
        logger.error(
            f"Error processing request {request_id} to {path}: {str(exc)}",
            exc_info=True
        )

        # Determine error code and status code based on exception type
        if isinstance(exc, TimeoutException):
            code = ErrorCode.SERVICE_UNAVAILABLE
            status_code = status.HTTP_504_GATEWAY_TIMEOUT
            message = "Request timed out while waiting for upstream service"
        elif isinstance(exc, ConnectionError):
            code = ErrorCode.SERVICE_UNAVAILABLE
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            message = "Failed to connect to upstream service"
        elif isinstance(exc, RequestError):
            code = ErrorCode.DEPENDENCY_ERROR
            status_code = status.HTTP_502_BAD_GATEWAY
            message = "Error communicating with upstream service"
        elif isinstance(exc, HTTPStatusError):
            code = ErrorCode.DEPENDENCY_ERROR
            status_code = status.HTTP_502_BAD_GATEWAY
            message = "Upstream service returned an error"
        elif isinstance(exc, RequestValidationError):
            code = ErrorCode.INVALID_REQUEST
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            message = "Request validation failed"
        elif isinstance(exc, ValueError):
            code = ErrorCode.INVALID_PARAM
            status_code = status.HTTP_400_BAD_REQUEST
            message = "Invalid request data"
        elif isinstance(exc, PermissionError):
            code = ErrorCode.UNAUTHORIZED
            status_code = status.HTTP_403_FORBIDDEN
            message = "Permission denied"
        elif isinstance(exc, StarletteHTTPException):
            code = ErrorCode.INTERNAL_ERROR
            status_code = exc.status_code
            message = str(exc.detail) if exc.detail else "HTTP error"
        else:
            code = ErrorCode.INTERNAL_ERROR
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            message = "An unexpected error occurred"

        # Create details
        details: Dict[str, Any] = {
            "exception_type": type(exc).__name__,
            "request_id": request_id,
            "path": path
        }

        # Add retry information if retries were attempted
        if retry_count > 0:
            details["retry_count"] = retry_count
            details["retry_exhausted"] = True

        # Add exception-specific details
        if isinstance(exc, StarletteHTTPException):
            details["status_code"] = exc.status_code

        elif isinstance(exc, RequestValidationError):
            details["validation_errors"] = []
            for error in exc.errors():
                details["validation_errors"].append({
                    "loc": error.get("loc", []),
                    "msg": error.get("msg", ""),
                    "type": error.get("type", "")
                })

        elif isinstance(exc, HTTPStatusError):
            # Get the upstream response
            http_exc_response: HTTPXResponse = getattr(exc, "response")

            if http_exc_response:
                details["upstream_status"] = http_exc_response.status_code
                try:
                    details["upstream_body"] = http_exc_response.json()
                except Exception:
                    try:
                        details["upstream_body"] = http_exc_response.text
                    except Exception:
                        pass

        # Use convert_exception_to_error_response from shared error handler if appropriate
        if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
            return convert_exception_to_error_response(exc)

        # Create error dictionary
        error_dict = {
            "status_code": status_code,
            "error": {
                "code": code,
                "message": message,
                "details": details
            }
        }

        return error_dict

    @staticmethod
    def _clone_request_with_body(request: Request, body: bytes) -> Request:
        """Clone a request with the same body for retries."""
        # Create a copy of the request with the same body
        # This is needed because the request body can only be read once
        request._body = body
        return request

    @staticmethod
    async def _wait_with_backoff(delay: float) -> None:
        """Wait with exponential backoff."""
        await asyncio.sleep(delay)

def add_error_handler(app: FastAPI, **kwargs) -> None:
    """
    Add error handling middleware to the FastAPI app.

    Args:
        app: The FastAPI application
        **kwargs: Additional configuration options for the middleware
    """
    # Add error handling middleware to the ASGI app
    app.add_middleware(ErrorHandlerMiddleware, **kwargs)

    # Add a route to get error handling statistics
    @app.get("/api/_internal/error-stats", include_in_schema=False)
    async def get_error_stats():
        """Get error handling statistics for monitoring."""
        middlewares = []
        if hasattr(app, 'middleware_stack') and app.middleware_stack and hasattr(app.middleware_stack, 'middlewares'):
            middlewares = [m for m in app.middleware_stack.middlewares if isinstance(m, ErrorHandlerMiddleware)]
        if middlewares:
            error_handler = middlewares[0]
            return {
                "retry_stats": error_handler.retry_stats,
                "timestamp": datetime.now().isoformat()
            }
        return {"error": "Error handler middleware not found"}
