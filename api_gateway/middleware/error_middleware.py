import json
import logging
import traceback
import time
import asyncio
from typing import Callable, Dict, Any, Optional, Type, Union, List
from datetime import datetime

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from httpx import TimeoutException, HTTPStatusError, RequestError, Response as HTTPXResponse

# Configure logging
logger = logging.getLogger("api_gateway.error_middleware")

# Define standard error response structure
class StandardErrorResponse:
    """Standard structure for all API error responses."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
        timestamp: Optional[str] = None,
        retryable: bool = False,
        suggestion: Optional[str] = None
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.request_id = request_id
        self.path = path
        self.timestamp = timestamp or datetime.now().isoformat()
        self.retryable = retryable
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "error": {
                "status_code": self.status_code,
                "code": self.error_code,
                "message": self.message,
                "timestamp": self.timestamp,
                "retryable": self.retryable
            }
        }

        if self.details:
            result["error"]["details"] = self.details

        if self.request_id:
            result["error"]["request_id"] = self.request_id

        if self.path:
            result["error"]["path"] = self.path

        if self.suggestion:
            result["error"]["suggestion"] = self.suggestion

        return result

    def to_response(self) -> JSONResponse:
        """Convert to FastAPI JSON response."""
        return JSONResponse(
            status_code=self.status_code,
            content=self.to_dict()
        )

# Error classification mappings
ERROR_CLASSIFICATION = {
    # Network errors
    TimeoutException: {
        "status_code": status.HTTP_504_GATEWAY_TIMEOUT,
        "error_code": "GATEWAY_TIMEOUT",
        "message": "Request timed out while waiting for upstream service",
        "retryable": True,
        "suggestion": "Please try again later"
    },
    ConnectionError: {
        "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
        "error_code": "SERVICE_UNAVAILABLE",
        "message": "Failed to connect to upstream service",
        "retryable": True,
        "suggestion": "Please try again later"
    },
    # HTTP errors
    RequestError: {
        "status_code": status.HTTP_502_BAD_GATEWAY,
        "error_code": "BAD_GATEWAY",
        "message": "Error communicating with upstream service",
        "retryable": True,
        "suggestion": "Please try again in a few minutes"
    },
    HTTPStatusError: {
        "status_code": status.HTTP_502_BAD_GATEWAY,
        "error_code": "UPSTREAM_ERROR",
        "message": "Upstream service returned an error",
        "retryable": False
    },
    # Validation errors
    RequestValidationError: {
        "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "error_code": "VALIDATION_ERROR",
        "message": "Request validation failed",
        "retryable": False,
        "suggestion": "Please check your request parameters"
    },
    ValueError: {
        "status_code": status.HTTP_400_BAD_REQUEST,
        "error_code": "INVALID_REQUEST",
        "message": "Invalid request data",
        "retryable": False
    },
    # Authentication errors
    PermissionError: {
        "status_code": status.HTTP_403_FORBIDDEN,
        "error_code": "FORBIDDEN",
        "message": "Permission denied",
        "retryable": False,
        "suggestion": "Please check your authorization credentials"
    },
    # Generic errors
    Exception: {
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "error_code": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred",
        "retryable": False,
        "suggestion": "Please contact support if the issue persists"
    }
}

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling and standardizing error responses across the API.

    Features:
    - Standardized error response format
    - Proper error classification and logging
    - Retry logic for transient failures
    - Detailed error information for debugging
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

                    # Return enhanced error response
                    return self._create_error_response(e, request_id, path, retries)

            except Exception as e:
                # Handle other errors (non-retryable)
                return self._create_error_response(e, request_id, path, retries)

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

    def _create_error_response(
        self,
        exc: Exception,
        request_id: str,
        path: str,
        retry_count: int = 0
    ) -> JSONResponse:
        """Create a standardized error response based on the exception type."""
        # Log the error
        logger.error(
            f"Error processing request {request_id} to {path}: {str(exc)}",
            exc_info=True
        )

        # Get error classification based on exception type
        error_info = self._get_error_classification(exc)
        error_info_copy = error_info.copy()  # Make a copy to avoid modifying the original

        # Create error details
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
            details["status_code"] = str(exc.status_code)
            error_info_copy["status_code"] = exc.status_code
            error_info_copy["message"] = str(exc.detail) if exc.detail else error_info_copy["message"]

        elif isinstance(exc, RequestValidationError):
            details["validation_errors"] = []
            for error in exc.errors():
                details["validation_errors"].append({
                    "loc": error.get("loc", []),
                    "msg": error.get("msg", ""),
                    "type": error.get("type", "")
                })

        elif isinstance(exc, HTTPStatusError):
            # Type hint the variable to tell the linter what it is
            http_exc_response: HTTPXResponse = getattr(exc, "response")

            if http_exc_response:
                details["upstream_status"] = str(http_exc_response.status_code)
                try:
                    details["upstream_body"] = http_exc_response.json()
                except Exception:
                    try:
                        details["upstream_body"] = http_exc_response.text
                    except Exception:
                        pass

        # Add stack trace in debug mode
        if self.debug_mode:
            details["stack_trace"] = traceback.format_exc()

        # Create standardized recovery instructions
        recovery_instructions = self._generate_recovery_instructions(exc, error_info_copy, retry_count)
        if recovery_instructions:
            details["recovery_instructions"] = recovery_instructions

        # Create the standardized error response
        error_response = StandardErrorResponse(
            status_code=error_info_copy["status_code"],
            error_code=error_info_copy["error_code"],
            message=error_info_copy.get("message", str(exc)),
            details=details,
            request_id=request_id,
            path=path,
            retryable=error_info_copy.get("retryable", False),
            suggestion=error_info_copy.get("suggestion")
        )

        response = error_response.to_response()

        # Add appropriate headers for retryable errors
        if error_info_copy.get("retryable", False):
            retry_after = 5 if isinstance(exc, TimeoutException) else 1
            response.headers["Retry-After"] = str(retry_after)

        return response

    def _generate_recovery_instructions(
        self,
        exc: Exception,
        error_info: Dict[str, Any],
        retry_count: int
    ) -> Optional[Dict[str, Any]]:
        """
        Generate recovery instructions based on error type.

        Args:
            exc: The exception that occurred
            error_info: The error classification information
            retry_count: Number of retries already attempted

        Returns:
            Recovery instructions or None if not applicable
        """
        if not error_info.get("retryable", False):
            return None

        # Generate instructions based on error type
        if isinstance(exc, TimeoutException):
            return {
                "action": "retry_with_backoff",
                "suggestion": "The server is currently experiencing high load. Please try again in a few seconds.",
                "retry_after": 5,
                "exponential_backoff": True
            }
        elif isinstance(exc, ConnectionError):
            return {
                "action": "check_and_retry",
                "suggestion": "Please check your network connection and try again.",
                "retry_after": 2,
                "max_retries": 3
            }
        elif isinstance(exc, RequestError):
            return {
                "action": "wait_and_retry",
                "suggestion": "The service is temporarily unavailable. Please try again later.",
                "retry_after": 10,
                "max_retries": 2
            }
        elif retry_count > 0:
            # Generic instructions for retried requests
            return {
                "action": "contact_support",
                "suggestion": f"Request failed after {retry_count} retries. Please try again later or contact support if the issue persists.",
                "retry_after": 30
            }

        return None

    def _get_error_classification(self, exc: Exception) -> Dict[str, Any]:
        """Get error classification based on exception type."""
        # Check if the exception type is directly mapped
        for error_type, classification in ERROR_CLASSIFICATION.items():
            if isinstance(exc, error_type):
                return classification

        # If not found, use the base Exception classification
        return ERROR_CLASSIFICATION[Exception]

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
    Add error handling middleware and exception handlers to the FastAPI app.

    Args:
        app: The FastAPI application
        **kwargs: Additional configuration options for the middleware
    """
    # Add error handling middleware to the ASGI app
    app.add_middleware(ErrorHandlerMiddleware, **kwargs)

    # Register exception handlers for FastAPI specific exceptions
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", f"req-{time.time()}")
        return StandardErrorResponse(
            status_code=exc.status_code,
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            request_id=request_id,
            path=request.url.path,
            retryable=exc.status_code in [502, 503, 504]
        ).to_response()

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", f"req-{time.time()}")
        details = {
            "validation_errors": []
        }

        for error in exc.errors():
            details["validation_errors"].append({
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", "")
            })

        return StandardErrorResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details=details,
            request_id=request_id,
            path=request.url.path,
            retryable=False,
            suggestion="Please check your request parameters"
        ).to_response()

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", f"req-{time.time()}")
        error_info = ERROR_CLASSIFICATION.get(type(exc), ERROR_CLASSIFICATION[Exception])

        details = {
            "exception_type": type(exc).__name__
        }

        # Log the error
        logger.error(
            f"Unhandled exception in request {request_id} to {request.url.path}: {str(exc)}",
            exc_info=True
        )

        return StandardErrorResponse(
            status_code=error_info["status_code"],
            error_code=error_info["error_code"],
            message=str(exc) if str(exc) else error_info["message"],
            details=details,
            request_id=request_id,
            path=request.url.path,
            retryable=error_info.get("retryable", False),
            suggestion=error_info.get("suggestion")
        ).to_response()

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
