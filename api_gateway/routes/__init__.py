"""
API Gateway Routes
-----------------
This package contains all the route definitions for the API Gateway.
"""

import logging

logger = logging.getLogger("api_gateway.routes")

# Initialize the package by attempting to import all route modules
try:
    from api_gateway.routes import questionnaire
    logger.info("Loaded questionnaire routes")
except ImportError as e:
    logger.warning(f"Failed to import questionnaire routes: {e}")

try:
    from api_gateway.routes import chart
    logger.info("Loaded chart routes")
except ImportError as e:
    logger.warning(f"Failed to import chart routes: {e}")

try:
    from api_gateway.routes import session
    logger.info("Loaded session routes")
except ImportError as e:
    logger.warning(f"Failed to import session routes: {e}")

try:
    from api_gateway.routes import geocode
    logger.info("Loaded geocode routes")
except ImportError as e:
    logger.warning(f"Failed to import geocode routes: {e}")
