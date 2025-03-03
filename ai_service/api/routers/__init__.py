"""
Routers module for the Birth Time Rectifier API
Contains all API router definitions
"""

# Import all routers for easy access
from .health import router as health_router
from .charts import chart_router
from .questionnaire import questionnaire_router
from .geocoding import geocoding_router
from .auth import auth_router

# Export all routers
__all__ = [
    "health_router",
    "chart_router",
    "questionnaire_router",
    "geocoding_router",
    "auth_router"
]

# Empty file to mark directory as a Python module

# routers package
