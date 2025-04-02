"""
API Gateway Routes
-----------------
This package contains all the route definitions for the API Gateway.
"""

import logging
import importlib
import sys

logger = logging.getLogger("api_gateway.routes")

# We'll use a safer approach to load modules to avoid circular imports
def load_route_module(module_name):
    """Safely import a route module and log the result."""
    try:
        # Direct import to avoid circular references
        module = importlib.import_module(f"api_gateway.routes.{module_name}")
        logger.info(f"Loaded {module_name} routes")
        return module
    except ImportError as e:
        logger.warning(f"Failed to import {module_name} routes: {e}")
        return None

# Load all route modules
questionnaire = load_route_module("questionnaire")
chart = load_route_module("chart")
session = load_route_module("session")
geocode = load_route_module("geocode")
auth = load_route_module("auth")
user = load_route_module("user")

# Export modules that were successfully loaded
__all__ = [name for name, module in locals().items()
           if not name.startswith('_') and name not in ('logging', 'importlib', 'sys', 'load_route_module', 'logger')
           and module is not None]
