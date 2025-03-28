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
        # Complete implementation based on API architecture documentation
        self.path_mappings = [
            # Root level legacy routes
            (r"^/health$", "/api/v1/health"),
            (r"^/geocode$", "/api/v1/geocode"),
            (r"^/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/session/(.*)$", r"/api/v1/session/\1"),
            (r"^/export/(.*)$", r"/api/v1/export/\1"),
            (r"^/user/(.*)$", r"/api/v1/user/\1"),

            # Unversioned /api/ routes
            (r"^/api/health$", "/api/v1/health"),
            (r"^/api/geocode$", "/api/v1/geocode"),
            (r"^/api/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/api/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/api/session/(.*)$", r"/api/v1/session/\1"),
            (r"^/api/export/(.*)$", r"/api/v1/export/\1"),
            (r"^/api/user/(.*)$", r"/api/v1/user/\1"),

            # Chart-specific endpoints
            (r"^/chart/generate$", "/api/v1/chart/generate"),
            (r"^/chart/validate$", "/api/v1/chart/validate"),
            (r"^/chart/rectify$", "/api/v1/chart/rectify"),
            (r"^/chart/export$", "/api/v1/chart/export"),
            (r"^/chart/compare$", "/api/v1/chart/compare"),

            # Special case for download endpoint which needs proper handling
            (r"^/export/(.+)/download$", r"/api/v1/chart/export/\1/download"),
        ]
        # Compile the regex patterns for better performance
        self.compiled_mappings = [(re.compile(pattern), replacement) for pattern, replacement in self.path_mappings]

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
        for pattern, replacement in self.compiled_mappings:
            match = pattern.match(original_path)
            if match:
                # Rewrite the path
                new_path = pattern.sub(replacement, original_path)
                request.scope["path"] = new_path
                request.scope["raw_path"] = new_path.encode()
                rewritten = True

                # Log the rewrite for debugging
                logger.debug(f"Rewriting path from {original_path} to {new_path}")
                break

        # Process the request with next middleware
        response = await call_next(request)

        # Add deprecation warning header if needed
        if rewritten and self.add_deprecation_warnings:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "Wed, 1 Jan 2025 00:00:00 GMT"
            response.headers["Link"] = f"<{request.scope['path']}>; rel=\"successor-version\""
            response.headers["X-API-Warning"] = "This endpoint is deprecated. Please use the /api/v1/ prefix in future requests."

        return response

# Export the middleware class directly
legacy_path_middleware = PathRewriterMiddleware
