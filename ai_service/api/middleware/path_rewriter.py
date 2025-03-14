"""
Path Rewriter Middleware for the Birth Time Rectifier API.

This middleware handles legacy routes by rewriting them to the standardized v1 API paths,
allowing backward compatibility without duplicate router registration.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
from typing import Dict, Tuple, List, Optional
import re

logger = logging.getLogger(__name__)

class PathRewriterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to rewrite legacy API paths to standardized v1 API paths.
    This allows backward compatibility without duplicate router registration.
    """

    def __init__(self, app, add_deprecation_warnings: bool = True):
        super().__init__(app)
        self.add_deprecation_warnings = add_deprecation_warnings

        # Define path mapping rules - from legacy paths to standardized v1 paths
        self.path_mappings = [
            # Root level legacy routes
            (r"^/health$", "/api/v1/health"),
            (r"^/geocode$", "/api/v1/geocode"),
            (r"^/session/(.*)$", r"/api/v1/session/\1"),
            (r"^/chart/validate$", "/api/v1/chart/validate"),
            (r"^/chart/generate$", "/api/v1/chart/generate"),
            (r"^/chart/rectify$", "/api/v1/chart/rectify"),
            (r"^/chart/export$", "/api/v1/chart/export"),
            (r"^/chart/export/(.*)$", r"/api/v1/chart/export/\1"),
            (r"^/chart/compare$", "/api/v1/chart/compare"),
            (r"^/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/questionnaire$", "/api/v1/questionnaire"),
            (r"^/ai/(.*)$", r"/api/v1/ai/\1"),

            # Unversioned /api/ routes
            (r"^/api/health$", "/api/v1/health"),
            (r"^/api/geocode$", "/api/v1/geocode"),
            (r"^/api/session/(.*)$", r"/api/v1/session/\1"),
            (r"^/api/chart/validate$", "/api/v1/chart/validate"),
            (r"^/api/chart/generate$", "/api/v1/chart/generate"),
            (r"^/api/chart/rectify$", "/api/v1/chart/rectify"),
            (r"^/api/chart/export$", "/api/v1/chart/export"),
            (r"^/api/chart/export/(.*)$", r"/api/v1/chart/export/\1"),
            (r"^/api/chart/compare$", "/api/v1/chart/compare"),
            (r"^/api/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/api/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
            (r"^/api/questionnaire$", "/api/v1/questionnaire"),
            (r"^/api/ai/(.*)$", r"/api/v1/ai/\1"),

            # Legacy versioned endpoints
            (r"^/api/chart/v2/(.*)$", r"/api/v1/chart/\1"),
            (r"^/api/chart/v3/(.*)$", r"/api/v1/chart/\1"),
            (r"^/api/chart/robust/(.*)$", r"/api/v1/chart/\1"),

            # Direct implementation routes
            (r"^/api/rectify$", "/api/v1/chart/rectify"),
            (r"^/api/v1/chart/rectify$", "/api/v1/chart/rectify"),
        ]

        # Compile regular expressions for better performance
        self.compiled_mappings = [(re.compile(pattern), replacement) for pattern, replacement in self.path_mappings]

    async def dispatch(self, request: Request, call_next):
        original_path = request.url.path
        rewritten = False

        # Check if path needs to be rewritten
        for pattern, replacement in self.compiled_mappings:
            match = pattern.match(original_path)
            if match:
                # Rewrite path
                rewritten_path = pattern.sub(replacement, original_path)

                # Log the rewrite
                logger.debug(f"Rewriting path: {original_path} -> {rewritten_path}")

                # Update request scope with new path
                request.scope["path"] = rewritten_path
                rewritten = True
                break

        # Process the request
        response = await call_next(request)

        # Add deprecation warning header for rewritten paths
        if rewritten and self.add_deprecation_warnings:
            response.headers["X-Deprecation-Warning"] = f"The path '{original_path}' is deprecated. Please use '{request.scope['path']}' instead."

        return response
