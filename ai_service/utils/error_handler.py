"""
Centralized error handling for Birth Time Rectifier application.

This module provides common error handling functions and utilities that can be
used across both the AI service and API Gateway to ensure consistent error handling.
"""

import logging
import sys
import traceback
from typing import Dict, Any, Optional, List, Callable, TypeVar, Awaitable, Union, cast
from functools import wraps
import asyncio
import json

from fastapi import HTTPException, status

# Configure logging
logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar('T')
AsyncCallable = Callable[..., Awaitable[T]]
SyncCallable = Callable[..., T]

# Error codes
class ErrorCode:
    """Common error codes across the application."""
    # Authentication errors
    INVALID_TOKEN = "INVALID_TOKEN"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    MISSING_TOKEN = "MISSING_TOKEN"
    UNAUTHORIZED = "UNAUTHORIZED"

    # Validation errors
    INVALID_REQUEST = "INVALID_REQUEST"
    MISSING_PARAM = "MISSING_PARAM"
    INVALID_PARAM = "INVALID_PARAM"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"

    # Service errors
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"

    # Chart errors
    CHART_CALCULATION_ERROR = "CHART_CALCULATION_ERROR"
    GEOCODING_ERROR = "GEOCODING_ERROR"
    RECTIFICATION_ERROR = "RECTIFICATION_ERROR"

    # WebSocket errors
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"
    CONNECTION_ERROR = "CONNECTION_ERROR"

# Base error class
class AppError(Exception):
    """Base error class for application errors."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        """
        Initialize the error.

        Args:
            code: Error code
            message: Error message
            details: Optional error details
            status_code: HTTP status code
        """
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary.

        Returns:
            Dictionary representation of error
        """
        # Create a properly typed dictionary for error response
        result: Dict[str, Dict[str, Any]] = {
            "error": {
                "code": self.code,
                "message": self.message
            }
        }

        # Add details if they exist
        if self.details:
            try:
                # Try to add details directly
                result["error"]["details"] = self.details
            except TypeError:
                # If there's a type error, convert to string representation
                result["error"]["details"] = str(self.details)

        return result

    def to_http_exception(self) -> HTTPException:
        """
        Convert error to HTTPException.

        Returns:
            HTTPException with appropriate status code and details
        """
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict()["error"]
        )

# Specific error classes
class ValidationError(AppError):
    """Validation error."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Optional field that failed validation
            details: Optional error details
        """
        error_details = details or {}
        if field:
            error_details["field"] = field

        super().__init__(
            code=ErrorCode.INVALID_PARAM if field else ErrorCode.INVALID_REQUEST,
            message=message,
            details=error_details,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class NotFoundError(AppError):
    """Resource not found error."""

    def __init__(self, resource_type: str, resource_id: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize not found error.

        Args:
            resource_type: Type of resource (e.g., "chart", "user")
            resource_id: ID of resource
            details: Optional error details
        """
        message = f"{resource_type.capitalize()} not found: {resource_id}"
        error_details = details or {}
        error_details.update({
            "resource_type": resource_type,
            "resource_id": resource_id
        })

        super().__init__(
            code=ErrorCode.NOT_FOUND,
            message=message,
            details=error_details,
            status_code=status.HTTP_404_NOT_FOUND
        )

class AuthenticationError(AppError):
    """Authentication error."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize authentication error.

        Args:
            code: Error code
            message: Error message
            details: Optional error details
        """
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

class ServiceError(AppError):
    """Service error."""

    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize service error.

        Args:
            service: Service name
            message: Error message
            details: Optional error details
        """
        error_details = details or {}
        error_details["service"] = service

        super().__init__(
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message=message,
            details=error_details,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

# Error handling decorators
def handle_errors(
    func: SyncCallable[T]
) -> SyncCallable[T]:
    """
    Decorator to handle errors in synchronous functions.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except AppError as e:
            logger.error(f"Application error: {e.code} - {e.message}")
            if e.details:
                logger.error(f"Error details: {json.dumps(e.details)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            logger.error(traceback.format_exc())

            # Create app error
            app_error = AppError(
                code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred",
                details={"original_error": str(e)}
            )
            raise app_error from e

    return wrapper

def handle_async_errors(
    func: AsyncCallable[T]
) -> AsyncCallable[T]:
    """
    Decorator to handle errors in asynchronous functions.

    Args:
        func: Async function to decorate

    Returns:
        Decorated async function
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await func(*args, **kwargs)
        except AppError as e:
            logger.error(f"Application error: {e.code} - {e.message}")
            if e.details:
                logger.error(f"Error details: {json.dumps(e.details)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            logger.error(traceback.format_exc())

            # Create app error
            app_error = AppError(
                code=ErrorCode.INTERNAL_ERROR,
                message="An unexpected error occurred",
                details={"original_error": str(e)}
            )
            raise app_error from e

    return wrapper

# Error conversion functions
def convert_exception_to_error_response(exception: Exception) -> Dict[str, Any]:
    """
    Convert an exception to a standardized error response.

    Args:
        exception: Exception to convert

    Returns:
        Standardized error response dictionary
    """
    if isinstance(exception, AppError):
        return exception.to_dict()
    elif isinstance(exception, HTTPException):
        # Convert FastAPI HTTPException to app error
        return AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message=str(exception.detail) if exception.detail else "HTTP error occurred",
            status_code=exception.status_code
        ).to_dict()
    else:
        # Generic error
        return AppError(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred",
            details={"original_error": str(exception)}
        ).to_dict()

def log_error(
    error: Union[Exception, str],
    log_level: int = logging.ERROR,
    include_traceback: bool = True
) -> None:
    """
    Log an error with standardized formatting.

    Args:
        error: Error to log
        log_level: Logging level
        include_traceback: Whether to include traceback
    """
    error_message = str(error)

    if log_level >= logging.ERROR:
        if isinstance(error, Exception) and include_traceback:
            logger.log(log_level, f"Error: {error_message}\n{traceback.format_exc()}")
        else:
            logger.log(log_level, f"Error: {error_message}")
    else:
        logger.log(log_level, error_message)
