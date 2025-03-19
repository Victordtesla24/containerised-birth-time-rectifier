"""
Legacy path support middleware for backward compatibility.

This module provides middleware to maintain backward compatibility with old API paths.
"""

from fastapi import Request
import re
import logging
from starlette.middleware.base import BaseHTTPMiddleware

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
        # Based on the sequence diagram endpoints
        self.path_mappings = [
            # Root level legacy routes
            (r"^/health$", "/api/v1/health"),
            (r"^/geocode$", "/api/v1/geocode"),
            (r"^/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/session/(.*)$", r"/api/v1/session/\1"),

            # Unversioned /api/ routes
            (r"^/api/health$", "/api/v1/health"),
            (r"^/api/geocode$", "/api/v1/geocode"),
            (r"^/api/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/api/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/api/session/(.*)$", r"/api/v1/session/\1"),
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
        # Get the original path
        original_path = request.url.path

        # Check if the path matches any of our mapping rules
        rewritten = False
        for pattern, replacement in self.path_mappings:
            if re.match(pattern, original_path):
                # Rewrite the path
                new_path = re.sub(pattern, replacement, original_path)
                request.scope["path"] = new_path
                rewritten = True

                # Log the rewrite for debugging
                logger.debug(f"Rewriting path from {original_path} to {new_path}")
                break

        # Process the request with next middleware
        response = await call_next(request)

        # Add deprecation warning header if needed
        if rewritten and self.add_deprecation_warnings:
            response.headers["X-API-Warning"] = "This endpoint is deprecated. Please use the /api/v1/ prefix in future requests."

        return response

# Export the middleware class directly
legacy_path_middleware = PathRewriterMiddleware
