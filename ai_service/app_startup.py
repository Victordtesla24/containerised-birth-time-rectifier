"""
Application startup and initialization for AI Service.

This module handles the initialization of the application, including setting up
dependencies, loading environment variables, and configuring services.
"""

import logging
import os
import sys
import traceback
from typing import Dict, Any, List, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Comprehensive middleware fix
try:
    # Patch FastAPI to handle invalid middleware gracefully
    import fastapi.applications
    from fastapi import FastAPI

    # Store the original method
    _original_build_middleware = fastapi.applications.FastAPI.build_middleware_stack

    # Define a fixed version that handles malformed middleware entries
    def _fixed_build_middleware(self):
        """Safe version of build_middleware_stack that handles malformed middleware."""
        # Clear any existing middleware stack
        self.user_middleware = getattr(self, 'user_middleware', [])

        # Detailed logging of middleware before sanitization
        logger.debug(f"Middleware stack before sanitization: {self.user_middleware}")

        # Filter and sanitize middleware to ensure correct format
        sanitized_middleware = []
        for i, middleware in enumerate(self.user_middleware):
            try:
                # Check type and convert to proper format if needed
                if isinstance(middleware, tuple):
                    # Handle tuples of different sizes
                    if len(middleware) == 2:
                        # This is correct format (cls, options)
                        sanitized_middleware.append(middleware)
                    elif len(middleware) > 2:
                        # Too many items - take only the first two
                        logger.warning(f"Middleware entry {i} has too many values, truncating: {middleware}")
                        sanitized_middleware.append((middleware[0], middleware[1]))
                    elif len(middleware) == 1:
                        # Missing options - add empty dict
                        logger.warning(f"Middleware entry {i} is missing options, adding empty dict: {middleware}")
                        sanitized_middleware.append((middleware[0], {}))
                    else:
                        # Empty tuple - skip
                        logger.warning(f"Skipping empty middleware tuple at position {i}")
                elif hasattr(middleware, "__call__"):
                    # It's a callable (like a function) - wrap with empty options
                    logger.warning(f"Converting callable middleware to tuple format at position {i}")
                    sanitized_middleware.append((middleware, {}))
                elif isinstance(middleware, list) and len(middleware) >= 2:
                    # It's a list with at least 2 items - convert to tuple
                    logger.warning(f"Converting list middleware to tuple format at position {i}")
                    sanitized_middleware.append((middleware[0], middleware[1]))
                else:
                    # Unknown format - log and skip
                    logger.warning(f"Skipping malformed middleware entry at position {i}: {middleware}")
            except Exception as e:
                logger.warning(f"Error processing middleware entry at position {i}: {e}")
                logger.debug(traceback.format_exc())

        # Replace with sanitized list
        self.user_middleware = sanitized_middleware
        logger.debug(f"Middleware stack after sanitization: {self.user_middleware}")

        # Now build the middleware stack safely
        try:
            # Check each middleware one last time
            for i, (cls, options) in enumerate(self.user_middleware):
                if not isinstance(options, dict):
                    self.user_middleware[i] = (cls, {})
                    logger.warning(f"Fixed non-dict options in middleware {i}")

            # Rebuild middleware stack
            return _original_build_middleware(self)
        except ValueError as ve:
            if "too many values to unpack" in str(ve):
                # Log the error in detail
                logger.error(f"ValueError during middleware stack build: {ve}")
                logger.error(f"Current middleware stack that caused error: {self.user_middleware}")

                # Emergency fallback - if we still have issues, use a minimal stack
                logger.warning("Middleware stack rebuild failed, using minimal stack")
                self.user_middleware = []
                return _original_build_middleware(self)
            raise
        except Exception as e:
            logger.error(f"Unexpected error building middleware stack: {e}")
            logger.error(traceback.format_exc())
            # Try without middleware as a last resort
            self.user_middleware = []
            return _original_build_middleware(self)

    # Apply the monkey patch
    fastapi.applications.FastAPI.build_middleware_stack = _fixed_build_middleware
    logger.info("Applied comprehensive FastAPI middleware fix")
except Exception as e:
    logger.error(f"Failed to apply FastAPI middleware fix: {e}")
    logger.error(traceback.format_exc())

# Import dependencies
from ai_service.utils.env_loader import load_env_file
from ai_service.utils.dependency_container import initialize_container

def initialize_services():
    """Initialize required services."""
    try:
        # Import deps lazily to avoid circular imports
        from ai_service.utils.dependency_container import get_container

        # Get the container instance
        container = get_container()

        # Initialize OpenAI service
        from ai_service.api.services.openai.service import create_openai_service
        openai_service = create_openai_service()
        container.register_instance("openai_service", openai_service)
        logger.info("OpenAI service initialized successfully")

        # Initialize chart service - with retry
        from ai_service.services import get_chart_service

        # Try up to 3 times to initialize the chart service
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                chart_service = get_chart_service()
                container.register_instance("chart_service", chart_service)
                logger.info("Chart service initialized successfully")
                break
            except Exception as chart_err:
                if attempt < max_attempts:
                    logger.warning(f"Chart service initialization failed (attempt {attempt}/{max_attempts}): {chart_err}")
                    # Delay before retry
                    import time
                    time.sleep(1)
                else:
                    logger.error(f"Chart service initialization failed after {max_attempts} attempts: {chart_err}")
                    # Create chart service directly
                    from ai_service.services.chart_service import create_chart_service
                    chart_service = create_chart_service()
                    container.register_instance("chart_service", chart_service)
                    logger.info("Created chart service directly as fallback")

        # Initialize session service
        from ai_service.services.session_service import SessionService
        session_service = SessionService()
        container.register_instance("session_service", session_service)
        logger.info("Session service initialized successfully")

        # Initialize WebSocket service
        from ai_service.services.websocket_service import get_websocket_manager
        websocket_manager = get_websocket_manager()
        container.register_instance("websocket_manager", websocket_manager)
        logger.info("WebSocket service initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        logger.error(traceback.format_exc())
        raise

def initialize_database():
    """Initialize database connections."""
    try:
        from ai_service.database.repositories import initialize_database_pool

        # Create and run a task to properly await the async function
        import asyncio
        loop = asyncio.get_event_loop()
        loop.create_task(initialize_database_pool())

        logger.info("Database initialization task scheduled")
    except Exception as e:
        logger.warning(f"Database initialization error: {e}")
        logger.info("Using file-based storage as fallback")

def configure_compatibility():
    """Configure compatibility settings for external dependencies."""
    try:
        # Silence Pydantic deprecation warnings
        from ai_service.utils.pydantic_compat import configure_pydantic_compat
        configure_pydantic_compat()
        logger.info("Compatibility settings configured")
    except Exception as e:
        logger.warning(f"Error configuring compatibility settings: {e}")

def initialize_application():
    """
    Main initialization function for the application.
    Called during FastAPI startup.
    """
    try:
        logger.info("Starting application initialization")

        # Initialize dependency container
        initialize_container()
        logger.info("Dependency container initialized")

        # Load environment variables
        load_env_file()
        logger.info("Environment variables loaded")

        # Configure compatibility settings
        configure_compatibility()

        # Initialize services
        initialize_services()

        # Initialize database
        initialize_database()

        logger.info("Application initialization completed successfully")
    except Exception as e:
        logger.error(f"Application initialization failed: {e}")
        logger.error(traceback.format_exc())
        raise
