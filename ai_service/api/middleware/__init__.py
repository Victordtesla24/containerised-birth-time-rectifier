"""
API middleware initialization.

This module initializes all middleware for the API.
"""

from .error_handling import validation_exception_handler, http_exception_handler
from .session import SimpleSessionMiddleware

# Export middleware classes
__all__ = [
    'validation_exception_handler',
    'http_exception_handler',
    'SimpleSessionMiddleware',
]
