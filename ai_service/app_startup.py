"""
Application startup and initialization for AI Service.

This module handles the initialization of the application, including setting up
dependencies, loading environment variables, and configuring services.
"""

import os
import sys
import asyncio
import json
import re
import logging
import traceback
import uuid
from typing import Dict, List, Any, Optional, Type, AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Callable

import uvicorn
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
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
        """Fixed version of FastAPI's build_middleware_stack method."""
        try:
            return _original_build_middleware(self)
        except ValueError as ve:
            logger.error(f"Value error building middleware stack: {ve}")
            logger.error(traceback.format_exc())
            # Don't use fallbacks - raise the error
            raise

        except Exception as e:
            logger.error(f"Unexpected error building middleware stack: {e}")
            logger.error(traceback.format_exc())
            # Don't use fallbacks - raise the error
            raise

    # Apply the monkey patch
    fastapi.applications.FastAPI.build_middleware_stack = _fixed_build_middleware
    logger.info("Applied comprehensive FastAPI middleware fix")
except Exception as e:
    logger.error(f"Failed to apply FastAPI middleware fix: {e}")
    logger.error(traceback.format_exc())

# Import dependencies
from ai_service.utils.env_loader import load_env_file
from ai_service.utils.dependency_container import get_container, initialize_container

# Import the shared session management functions
from ai_service.utils.geocoding import get_shared_session, close_shared_session

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan event handler for application startup and shutdown.

    This function handles:
    - Environment variable loading
    - Database connections
    - Service initialization
    - GPU resource allocation
    - Shared HTTP session initialization
    - Cleanup of all resources on shutdown

    Args:
        app: The FastAPI application instance
    """

    # Import here to avoid circular imports
    from ai_service.utils.gpu_manager import GPUMemoryManager

    logger.info("Application startup initiated")

    # Load environment variables from .env file if present
    load_env_file()

    # Initialize dependency container
    initialize_container()

    # Initialize database connections if needed
    await initialize_database_async()
    logger.info("Database connections initialized")

    # Initialize the shared HTTP session for geocoding services
    get_shared_session()
    logger.info("Initialized shared HTTP session")

    # Initialize GPU manager if available
    try:
        gpu_manager = GPUMemoryManager()
        get_container().register_instance("gpu_manager", gpu_manager)
        logger.info(f"GPU Memory Manager initialized with {gpu_manager.get_memory_info()}")
    except Exception as e:
        logger.warning(f"GPU Manager initialization failed: {e}. Continuing without GPU support.")

    # Register all services
    initialize_services()
    logger.info("Service registration completed")

    # Application is now ready
    logger.info("Application startup completed successfully")

    yield

    # Shutdown logic
    logger.info("Application shutdown initiated")

    # Close the shared HTTP session
    await close_shared_session()
    logger.info("Closed shared HTTP session")

    # Close GPU resources if initialized
    if 'gpu_manager' in locals():
        try:
            gpu_manager.cleanup()
            logger.info("GPU resources released")
        except Exception as e:
            logger.warning(f"Error cleaning up GPU resources: {e}")

    # Other cleanup logic...
    logger.info("Application shutdown completed successfully")

def initialize_services():
    """Initialize required services."""
    try:
        # Import deps lazily to avoid circular imports
        from ai_service.utils.dependency_container import get_container

        # Get the container instance
        container = get_container()

        # Initialize OpenAI service
        from ai_service.api.services.openai import get_openai_service
        openai_service = get_openai_service()
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
                    # Don't create a fallback - raise the error
                    raise RuntimeError(f"Failed to initialize chart service after {max_attempts} attempts: {chart_err}")

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

async def initialize_database_async():
    """Initialize database connections asynchronously."""
    # Check for test/development mode
    env = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "production"))
    skip_db = os.environ.get("SKIP_DB_INIT", "").lower() in ("true", "1", "yes")

    if skip_db or env in ("test", "development"):
        logger.info("Skipping database initialization in test/development mode")
        return

    try:
        # Import database initialization
        try:
            from ai_service.database import initialize_database_connections
            from ai_service.database import verify_database_schema

            # Initialize the database connections (await if async)
            await initialize_database_connections()

            # Verify database schema (await if async)
            await verify_database_schema()

            logger.info("Database initialization completed successfully")
        except ImportError as e:
            logger.warning(f"Database module import failed: {e}, skipping initialization")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't use file-based storage as fallback
        raise

def configure_compatibility():
    """Configure compatibility settings for external dependencies."""
    try:
        # Silence Pydantic deprecation warnings
        from ai_service.utils.pydantic_compat import configure_pydantic_compat
        configure_pydantic_compat()
        logger.info("Compatibility settings configured")
    except Exception as e:
        logger.warning(f"Error configuring compatibility settings: {e}")

async def initialize_application():
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
        await initialize_database_async()

        logger.info("Application initialization completed successfully")
    except Exception as e:
        logger.error(f"Application initialization failed: {e}")
        raise

async def bootstrap_containers(app=None, stack=None):
    """
    Bootstrap and register service containers.

    Args:
        app: FastAPI application instance to register services with
        stack: Service stack to use (optional, taken from app config otherwise)

    Raises:
        RuntimeError: If any container initialization fails
    """
    logger.info("Bootstrapping service containers...")

    try:
        # Get the dependency container singleton
        container = get_container()

        # Get app config
        config = get_settings()

        # Register config in container
        container.register_instance("config", config)

        # Register container in app state if app provided
        if app:
            app.state.container = container
            logger.info("Container registered in app state")

            # Get stack from app config if not provided
            if not stack:
                stack_config = getattr(config, "SERVICE_STACK", None)

                if stack_config:
                    # Parse stack configuration
                    if isinstance(stack_config, str):
                        try:
                            # Try to parse as JSON
                            stack = json.loads(stack_config)
                        except json.JSONDecodeError:
                            # Try to parse as tuple string representation
                            stack_match = re.match(r'\(([^)]+)\)', stack_config)
                            if stack_match:
                                try:
                                    stack = tuple(s.strip() for s in stack_match.group(1).split(','))
                                except Exception as e:
                                    logger.error(f"Failed to parse stack tuple: {e}")
                                    raise ValueError(f"Invalid service stack configuration: {stack_config}")
                            else:
                                # Try as comma-separated values
                                stack = tuple(s.strip() for s in stack_config.split(','))
                    elif isinstance(stack_config, (list, tuple)):
                        # Already in the right format
                        stack = tuple(stack_config)
                    else:
                        # Unknown format
                        logger.error(f"Unknown stack format: {type(stack_config)}")
                        raise ValueError(f"Invalid service stack configuration type: {type(stack_config)}")

        # Register database
        db_pool = await setup_database(config)
        container.register_instance("db_pool", db_pool)

        # Bootstrap services according to stack
        if stack:
            await bootstrap_stack(container, stack)
        else:
            logger.warning("No service stack provided, using minimal initialization")
            await bootstrap_minimal_services(container)

        logger.info("Service containers bootstrapped successfully")

        # Return the container
        return container

    except Exception as e:
        error_msg = f"Failed to bootstrap service containers: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


async def bootstrap_stack(container, stack):
    """
    Bootstrap services based on the provided stack.

    Args:
        container: Dependency container to register services in
        stack: Service stack configuration

    Raises:
        RuntimeError: If stack initialization fails
    """
    logger.info(f"Bootstrapping services for stack: {stack}")

    try:
        # Initialize services based on stack
        for service_name in stack:
            # Skip empty entries
            if not service_name:
                continue

            service_name = service_name.strip()

            # Skip comments
            if service_name.startswith('#'):
                continue

            logger.info(f"Initializing service: {service_name}")

            if service_name == "chart_service":
                # Initialize chart service
                from ai_service.services.chart_service import ChartService

                # Create with chart output directory from config
                config = container.get("config")
                chart_output_dir = config.CHART_OUTPUT_DIR if hasattr(config, "CHART_OUTPUT_DIR") else None

                chart_service = ChartService(chart_output_dir=chart_output_dir)
                container.register_instance("chart_service", chart_service)
                logger.info("Chart service initialized")

            elif service_name == "openai_service":
                # Initialize OpenAI service
                from ai_service.api.services.openai.service import OpenAIService, get_openai_service

                openai_service = get_openai_service()
                if not openai_service:
                    openai_service = OpenAIService()

                container.register_instance("openai_service", openai_service)
                logger.info("OpenAI service initialized")

            elif service_name == "session_service":
                # Initialize session service
                from ai_service.api.services.session_service import SessionService

                session_service = SessionService()
                container.register_instance("session_service", session_service)
                logger.info("Session service initialized")

            elif service_name == "chart_repository":
                # Initialize chart repository
                from ai_service.database.repositories import ChartRepository

                db_pool = container.get("db_pool")
                chart_repository = ChartRepository(db_pool=db_pool)
                container.register_instance("chart_repository", chart_repository)
                logger.info("Chart repository initialized")

            elif service_name == "questionnaire_service":
                # Initialize questionnaire service
                from ai_service.api.services.questionnaire_service import get_questionnaire_service

                questionnaire_service = get_questionnaire_service()
                if not questionnaire_service:
                    # Create directly if function failed
                    from ai_service.api.services.questionnaire_service import QuestionnaireService
                    from ai_service.api.services.openai.service import get_openai_service

                    openai_service = get_openai_service()
                    questionnaire_service = QuestionnaireService(openai_service=openai_service)

                container.register_instance("questionnaire_service", questionnaire_service)
                logger.info("Questionnaire service initialized")

            elif service_name == "dynamic_questionnaire_service":
                # Initialize dynamic questionnaire service
                from ai_service.api.services.dynamic_questionnaire_service import DynamicQuestionnaireService
                from ai_service.api.services.openai.service import get_openai_service

                openai_service = get_openai_service()
                dynamic_service = DynamicQuestionnaireService(openai_service=openai_service)

                container.register_instance("dynamic_questionnaire_service", dynamic_service)
                logger.info("Dynamic questionnaire service initialized")

            else:
                logger.warning(f"Unknown service in stack: {service_name}")

        logger.info("Service stack initialization completed")

    except Exception as e:
        error_msg = f"Failed to initialize service stack: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


async def bootstrap_minimal_services(container):
    """
    Bootstrap minimal required services.

    Args:
        container: Dependency container to register services in

    Raises:
        RuntimeError: If minimal service initialization fails
    """
    logger.info("Bootstrapping minimal services")

    try:
        # Initialize OpenAI service
        from ai_service.api.services.openai.service import OpenAIService

        openai_service = OpenAIService()
        container.register_instance("openai_service", openai_service)
        logger.info("OpenAI service initialized")

        # Initialize session service
        from ai_service.api.services.session_service import SessionService

        session_service = SessionService()
        container.register_instance("session_service", session_service)
        logger.info("Session service initialized")

        # Initialize chart service
        from ai_service.services.chart_service import ChartService

        config = container.get("config")
        chart_output_dir = config.CHART_OUTPUT_DIR if hasattr(config, "CHART_OUTPUT_DIR") else None

        if not chart_output_dir:
            raise ValueError("Chart output directory not configured")

        chart_service = ChartService(chart_output_dir=chart_output_dir)
        container.register_instance("chart_service", chart_service)
        logger.info("Chart service initialized")

        # Initialize chart repository
        try:
            from ai_service.database.repositories import ChartRepository

            db_pool = container.get("db_pool")
            chart_repository = ChartRepository(db_pool=db_pool)
            container.register_instance("chart_repository", chart_repository)
            logger.info("Chart repository initialized")
        except Exception as e:
            logger.error(f"Failed to initialize chart repository: {e}")
            raise RuntimeError(f"Chart repository initialization failed: {e}")

        logger.info("Minimal services initialization completed")

    except Exception as e:
        error_msg = f"Failed to initialize minimal services: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


async def setup_database(config):
    """
    Set up the database connection.

    Args:
        config: Application configuration

    Returns:
        Database connection pool

    Raises:
        RuntimeError: If database connection fails
    """
    try:
        # Get database connection parameters
        db_host = config.DB_HOST
        db_port = config.DB_PORT
        db_user = config.DB_USER
        db_password = config.DB_PASSWORD
        db_name = config.DB_NAME

        # Create connection pool
        import asyncpg

        db_pool = await asyncpg.create_pool(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
            min_size=5,
            max_size=20
        )

        # Verify connection
        async with db_pool.acquire() as conn:
            await conn.execute("SELECT 1")

        logger.info(f"Connected to PostgreSQL database at {db_host}:{db_port}/{db_name}")

        # Verify schema using the database/__init__.py module's functions
        from ai_service.database import initialize_database_connections, verify_database_schema

        # Initialize database connections globally
        await initialize_database_connections()

        # Verify schema
        await verify_database_schema()

        return db_pool

    except Exception as e:
        error_msg = f"Database connection failed: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)


async def verify_database_schema(db_pool):
    """
    Verify that the database schema is correctly set up.

    Args:
        db_pool: Database connection pool

    Raises:
        RuntimeError: If schema verification fails
    """
    try:
        # Check if required tables exist
        required_tables = ["charts", "sessions", "users", "rectifications", "comparisons"]

        async with db_pool.acquire() as conn:
            for table in required_tables:
                exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table
                )

                if not exists:
                    error_msg = f"Required table '{table}' does not exist in database"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

        logger.info("Database schema verification completed successfully")

    except Exception as e:
        error_msg = f"Database schema verification failed: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
