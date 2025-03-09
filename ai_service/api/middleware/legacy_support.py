"""
Legacy support middleware for the Birth Time Rectifier API.
Provides backward compatibility with older API paths.
"""

import logging
from fastapi import Request

from ai_service.core.config import settings

# Setup logging
logger = logging.getLogger("birth-time-rectifier.legacy-support")

async def legacy_path_middleware(request: Request, call_next):
    """
    Middleware to handle legacy paths without the /api prefix.

    This middleware provides backward compatibility by:
    1. Identifying paths that don't have the configured API_PREFIX
    2. Rewriting them to use the current API_PREFIX if they match an expected API pattern
    3. Passing the modified request through to the next middleware

    Args:
        request: The incoming request
        call_next: The next middleware in the chain

    Returns:
        Response from downstream middlewares
    """
    # Original path
    original_path = request.url.path

    # Current API prefix (e.g., /api/v1)
    api_prefix = settings.API_PREFIX

    # If the path already starts with the API prefix, no modification needed
    if original_path.startswith(api_prefix):
        return await call_next(request)

    # List of recognized API endpoints that should be prefixed
    # These are the endpoints that were previously available without the /api prefix
    recognized_patterns = [
        "/health",
        "/chart",
        "/charts",
        "/geocode",
        "/questionnaire",
        "/rectify",
        "/session",
        "/ai"
    ]

    # Check if the path starts with any of the recognized patterns
    for pattern in recognized_patterns:
        if original_path.startswith(pattern):
            # Rewrite the path to include the API prefix
            new_path = f"{api_prefix}{original_path}"

            # Log the rewrite
            logger.debug(f"Rewriting legacy path: {original_path} -> {new_path}")

            # Create modified request scope with new path
            request.scope["path"] = new_path

            # Update raw path (needed for some frameworks)
            if "raw_path" in request.scope:
                request.scope["raw_path"] = new_path.encode("utf-8")

            break

    # Continue to the next middleware
    return await call_next(request)
