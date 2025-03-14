"""
Legacy path support middleware for backward compatibility.

This module provides middleware to maintain backward compatibility with old API paths.
"""

from fastapi import Request
import re
from starlette.middleware.base import BaseHTTPMiddleware
import logging

# Configure logging
logger = logging.getLogger(__name__)

class PathRewriterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to rewrite legacy API paths to standardized v1 API paths.
    This allows backward compatibility without duplicate router registration.
    """

    def __init__(self, app, add_deprecation_warnings: bool = True):
        """
        Initialize the path rewriter middleware.

        Args:
            app: The FastAPI application
            add_deprecation_warnings: Whether to add deprecation warnings in response headers
        """
        super().__init__(app)
        self.add_deprecation_warnings = add_deprecation_warnings

        # Define path mapping rules - from legacy paths to standardized v1 paths
        self.path_mappings = [
            # Root level legacy routes
            (r"^/health$", "/api/v1/health"),
            (r"^/geocode$", "/api/v1/geocode"),
            (r"^/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/questionnaire$", "/api/v1/questionnaire"),
            (r"^/export/(.*)$", r"/api/v1/export/\1"),

            # Unversioned /api/ routes
            (r"^/api/health$", "/api/v1/health"),
            (r"^/api/geocode$", "/api/v1/geocode"),
            (r"^/api/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/api/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/api/questionnaire$", "/api/v1/questionnaire"),
            (r"^/api/export/(.*)$", r"/api/v1/export/\1"),
        ]

    async def dispatch(self, request: Request, call_next):
        """
        Dispatch method for the middleware.

        Args:
            request: The incoming request
            call_next: The next middleware/handler in the chain

        Returns:
            Response from the next middleware/handler
        """
        # Save original path for logging
        original_path = request.url.path

        # Apply path rewriting
        for pattern, replacement in self.path_mappings:
            if re.match(pattern, original_path):
                # Rewrite the path
                rewritten_path = re.sub(pattern, replacement, original_path)

                # Update the request's scope with the new path
                request.scope["path"] = rewritten_path

                # Log the path rewriting
                logger.debug(f"Rewrote path: {original_path} -> {rewritten_path}")

                # Process the request with next middleware
                response = await call_next(request)

                # Add deprecation warning if enabled
                if self.add_deprecation_warnings:
                    response.headers["X-Deprecation-Warning"] = (
                        f"The path '{original_path}' is deprecated. "
                        f"Please use '{rewritten_path}' instead."
                    )

                return response

        # If no rewriting occurred, just pass the request through
        return await call_next(request)

# Export the middleware for use in FastAPI app
legacy_path_middleware = PathRewriterMiddleware
