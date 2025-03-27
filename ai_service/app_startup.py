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
from ai_service.utils.env_loader import load_env_file, get_env_with_fallback
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
    - Redis connection initialization
    - Cleanup of all resources on shutdown

    Args:
        app: The FastAPI application instance
    """

    # Import here to avoid circular imports
    from ai_service.utils.gpu_manager import GPUMemoryManager
    from ai_service.utils.env_loader import get_env_with_fallback

    logger.info("Application startup initiated")

    # Load environment variables from .env file if present
    load_env_file()

    # Initialize dependency container
    initialize_container()
    container = get_container()

    # Initialize database connections if needed
    await initialize_database_async()
    logger.info("Database connections initialized")

    # Initialize Redis connection for session storage
    try:
        import redis.asyncio
        from ai_service.core.config import settings

        # Create Redis client using asyncio version
        redis_client = redis.asyncio.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

        # Store Redis client in app.state
        app.state.redis = redis_client

        # Test connection
        await redis_client.ping()
        logger.info("Redis connection initialized successfully")
    except ImportError:
        logger.warning("Redis package not installed. Session persistence will use in-memory storage.")
        app.state.redis = None
    except Exception as e:
        logger.warning(f"Failed to initialize Redis: {e}. Session persistence will use in-memory storage.")
        app.state.redis = None

    # Initialize the shared HTTP session for geocoding services
    try:
        from ai_service.utils.geocoding import get_shared_session
        await get_shared_session()  # Make sure to await this async function
        logger.info("Initialized shared HTTP session")
    except Exception as e:
        logger.error(f"Failed to initialize shared HTTP session: {e}")
        raise

    # Initialize GPU manager if available
    try:
        gpu_manager = GPUMemoryManager()
        container.register_instance("gpu_manager", gpu_manager)
        logger.info(f"GPU Memory Manager initialized with {gpu_manager.get_memory_info()}")
    except Exception as e:
        logger.warning(f"GPU Manager initialization failed: {e}. Continuing without GPU support.")

    # Initialize OpenAI service FIRST, since other services depend on it
    openai_service = None
    try:
        # Import OpenAI service
        from ai_service.api.services.openai import get_openai_service

        # Get API key from environment with .env fallback
        api_key = get_env_with_fallback("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment or .env file. OpenAI features will be disabled.")
            # Set feature flag indicating OpenAI is not available
            container.register_instance("openai_enabled", False)
        else:
            # Initialize the OpenAI service - must await
            openai_service = await get_openai_service()

            if openai_service:
                # Register in container if initialized successfully
                container.register_instance("openai_service", openai_service)
                container.register_instance("openai_enabled", True)
                logger.info("OpenAI service successfully initialized and registered")
            else:
                logger.warning("OpenAI service initialization returned None. Features requiring OpenAI will be disabled.")
                container.register_instance("openai_enabled", False)
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI service: {e}")
        logger.error(traceback.format_exc())
        # Continue without OpenAI - the system should still function without it
        container.register_instance("openai_enabled", False)

    # AFTER OpenAI is initialized, initialize Chart service
    try:
        # Import chart service
        from ai_service.services import get_chart_service_async

        # Initialize chart service asynchronously
        chart_service = await get_chart_service_async()

        # Set openai_service property explicitly if both are available
        if chart_service and openai_service:
            chart_service.openai_service = openai_service
            logger.info("Set OpenAI service on Chart service instance")

        # Register in container
        container.register_instance("chart_service", chart_service)
        logger.info("Chart service successfully initialized and registered")
    except Exception as e:
        logger.error(f"Failed to initialize Chart service: {e}")
        logger.error(traceback.format_exc())
        # Continue without properly initialized chart service

    # Register remaining services
    initialize_services()
    logger.info("Service registration completed")

    # Initialize other async services - this ensures all services are fully initialized
    try:
        # Explicitly await async initialization to ensure services are ready
        await initialize_services_async()
        logger.info("Async service initialization completed")
    except Exception as e:
        logger.error(f"Failed to complete async service initialization: {e}")
        logger.error(traceback.format_exc())
        # Continue despite initialization failures - services should handle missing dependencies

    # Application is now ready
    logger.info("Application startup completed successfully")

    yield

    # Shutdown logic
    logger.info("Application shutdown initiated")

    # Close the shared HTTP session
    try:
        from ai_service.utils.geocoding import close_shared_session
        await close_shared_session()
        logger.info("Closed shared HTTP session")
    except Exception as e:
        logger.warning(f"Error closing shared HTTP session: {e}")

    # Close GPU resources if initialized
    if 'gpu_manager' in locals():
        try:
            gpu_manager.cleanup()
            logger.info("GPU resources released")
        except Exception as e:
            logger.warning(f"Error cleaning up GPU resources: {e}")

    # Cleanup Redis connection
    if hasattr(app.state, "redis") and app.state.redis is not None:
        try:
            await app.state.redis.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")

    # Close OpenAI service
    try:
        if openai_service:
            await openai_service.close()
            logger.info("OpenAI service closed")
    except Exception as e:
        logger.warning(f"Error closing OpenAI service: {e}")

    # Other cleanup logic...
    logger.info("Application shutdown completed successfully")

def initialize_services():
    """Initialize required services."""
    try:
        # Import deps lazily to avoid circular imports
        from ai_service.utils.dependency_container import get_container
        from ai_service.utils.env_loader import get_env_with_fallback

        # Get the container instance
        container = get_container()

        # Initialize OpenAI service if API key is available - check both env and .env file
        api_key = get_env_with_fallback("OPENAI_API_KEY")
        if api_key:
            from ai_service.api.services.openai.service import OpenAIService

            # Create OpenAI service with API key
            openai_service = OpenAIService(api_key=api_key)
            container.register_instance("openai_service", openai_service)
            # Set feature flag indicating OpenAI is available
            container.register_instance("openai_enabled", True)
            logger.info("OpenAI service initialized successfully")
        else:
            # Set feature flag indicating OpenAI is not available
            container.register_instance("openai_enabled", False)
            logger.warning("OPENAI_API_KEY not found in environment or .env file. Advanced features requiring OpenAI will be disabled.")

        # Initialize chart service - with retry
        from ai_service.services import get_chart_service

        # Create a chart service instance
        chart_service = get_chart_service()

        # Register it in the container (it will be initialized during app startup)
        container.register_instance("chart_service", chart_service)
        logger.info("Chart service registered (will be initialized asynchronously)")

        # Initialize session service
        from ai_service.services.session_service import SessionService
        session_service = SessionService()
        container.register_instance("session_service", session_service)
        logger.info("Session service initialized successfully")

        # Initialize WebSocket service
        from ai_service.utils.websocket_manager import get_websocket_manager
        websocket_manager = get_websocket_manager()
        container.register_instance("websocket_manager", websocket_manager)
        logger.info("WebSocket manager initialized successfully")

    except Exception as e:
        logger.error(f"Error initializing services: {e}")
        logger.error(traceback.format_exc())
        raise

# Add a new function to asynchronously initialize services
async def initialize_services_async():
    """Asynchronously initialize services that require await."""
    try:
        # Import deps lazily to avoid circular imports
        from ai_service.utils.dependency_container import get_container
        container = get_container()

        # Initialize OpenAI service first
        try:
            from ai_service.api.services.openai import get_openai_service
            openai_service = await get_openai_service()
            if openai_service:
                # Register in container if not already there
                try:
                    existing_service = container.get("openai_service")
                    # If we get here, service exists, no need to register
                    logger.info("OpenAI service already in container")
                except ValueError:
                    # Service not in container, register it
                    container.register_instance("openai_service", openai_service)
                    logger.info("OpenAI service initialized successfully via async init")
        except Exception as e:
            logger.error(f"Error initializing OpenAI service: {e}")
            logger.error(traceback.format_exc())
            # Continue without OpenAI - the system should still function

        # Initialize the chart service
        try:
            chart_service = container.get("chart_service")
            if chart_service:
                await chart_service.initialize()
                logger.info("Chart service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing chart service: {e}")
            logger.error(traceback.format_exc())
            # Continue without full initialization

        # Add other async service initializations here if needed

    except Exception as e:
        logger.error(f"Error in async service initialization: {e}")
        logger.error(traceback.format_exc())
        # Don't re-raise to allow startup to continue

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
        container = get_container()
        logger.info("Dependency container initialized")

        # Load environment variables
        load_env_file()
        logger.info("Environment variables loaded")

        # Configure compatibility settings
        configure_compatibility()

        # Initialize database asynchronously
        await initialize_database_async()
        logger.info("Database initialized")

        # Initialize OpenAI service first
        try:
            from ai_service.api.services.openai import get_openai_service
            from ai_service.utils.env_loader import get_env_with_fallback

            # Get API key with .env fallback
            api_key = get_env_with_fallback("OPENAI_API_KEY")
            if api_key:
                openai_service = await get_openai_service()
                if openai_service:
                    container.register_instance("openai_service", openai_service)
                    container.register_instance("openai_enabled", True)
                    logger.info("OpenAI service initialized")
                else:
                    container.register_instance("openai_enabled", False)
                    logger.warning("OpenAI service initialization returned None")
            else:
                container.register_instance("openai_enabled", False)
                logger.warning("OPENAI_API_KEY not found in environment or .env file. OpenAI features will be disabled.")
        except Exception as e:
            logger.error(f"OpenAI service initialization failed: {e}")
            container.register_instance("openai_enabled", False)

        # Initialize chart service
        try:
            from ai_service.services import get_chart_service_async
            chart_service = await get_chart_service_async()
            if chart_service:
                container.register_instance("chart_service", chart_service)
                logger.info("Chart service initialized")
            else:
                logger.warning("Chart service initialization returned None")
        except Exception as e:
            logger.error(f"Chart service initialization failed: {e}")

        # Initialize remaining services
        initialize_services()
        logger.info("Services initialized")

        # Initialize async services
        await initialize_services_async()
        logger.info("Async services initialized")

        logger.info("Application initialization completed successfully")
    except Exception as e:
        logger.error(f"Application initialization failed: {e}")
        logger.error(traceback.format_exc())
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
        from ai_service.core.config import settings as app_settings

        # Register config in container
        container.register_instance("config", app_settings)

        # Register container in app state if app provided
        if app:
            app.state.container = container
            logger.info("Container registered in app state")

            # Get stack from app config if not provided
            if not stack:
                stack_config = getattr(app_settings, "SERVICE_STACK", None)

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
        db_pool = await setup_database(app_settings)
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
        # Import dependencies
        from ai_service.utils.env_loader import get_env_with_fallback

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
                # Initialize OpenAI service if API key is available - check both env and .env file
                api_key = get_env_with_fallback("OPENAI_API_KEY")
                if api_key:
                    from ai_service.api.services.openai.service import OpenAIService

                    # Create a new instance directly with API key
                    openai_service = OpenAIService(api_key=api_key)
                    container.register_instance("openai_service", openai_service)
                    container.register_instance("openai_enabled", True)
                    logger.info("OpenAI service initialized")
                else:
                    # Set flag to indicate OpenAI is not available
                    container.register_instance("openai_enabled", False)
                    logger.warning("OPENAI_API_KEY not found in environment or .env file. Advanced features requiring OpenAI will be disabled.")

            elif service_name == "session_service":
                # Initialize session service
                from ai_service.services.session_service import SessionService

                session_service = SessionService()
                container.register_instance("session_service", session_service)
                logger.info("Session service initialized")

            elif service_name == "chart_repository":
                # Initialize chart repository
                from ai_service.database.repositories import ChartRepository

                chart_repository = ChartRepository()
                container.register_instance("chart_repository", chart_repository)
                logger.info("Chart repository initialized")

            elif service_name == "questionnaire_service":
                # Initialize questionnaire service
                from ai_service.api.services.questionnaire_service import QuestionnaireService

                # Check if OpenAI is available
                openai_enabled = container.get("openai_enabled", False)
                if openai_enabled:
                    # Use the already initialized openai_service
                    openai_service = container.get("openai_service")
                    # Create service with OpenAI
                    questionnaire_service = QuestionnaireService(openai_service=openai_service)
                else:
                    # Create service without OpenAI - limited functionality
                    questionnaire_service = QuestionnaireService(openai_service=None)
                    logger.warning("Questionnaire service initialized with limited functionality (no OpenAI)")

                container.register_instance("questionnaire_service", questionnaire_service)
                logger.info("Questionnaire service initialized")

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
        # Import dependencies
        from ai_service.utils.env_loader import get_env_with_fallback

        # Initialize OpenAI service if API key is available - check both env and .env file
        api_key = get_env_with_fallback("OPENAI_API_KEY")
        if api_key:
            from ai_service.api.services.openai.service import OpenAIService

            openai_service = OpenAIService(api_key=api_key)
            container.register_instance("openai_service", openai_service)
            container.register_instance("openai_enabled", True)
            logger.info("OpenAI service initialized")
        else:
            # Set flag to indicate OpenAI is not available
            container.register_instance("openai_enabled", False)
            logger.warning("OPENAI_API_KEY not found in environment or .env file. Advanced features requiring OpenAI will be disabled.")

        # Initialize session service
        from ai_service.services.session_service import SessionService

        session_service = SessionService()
        container.register_instance("session_service", session_service)
        logger.info("Session service initialized")

        # Initialize chart service
        from ai_service.services.chart_service import ChartService

        config = container.get("config")
        chart_output_dir = config.CHART_OUTPUT_DIR if hasattr(config, "CHART_OUTPUT_DIR") else None

        if not chart_output_dir:
            logger.warning("Chart output directory not configured, using default")
            chart_output_dir = "exports"  # Use a default directory

        chart_service = ChartService(chart_output_dir=chart_output_dir)
        container.register_instance("chart_service", chart_service)
        logger.info("Chart service initialized")

        # Initialize chart repository
        try:
            from ai_service.database.repositories import ChartRepository

            chart_repository = ChartRepository()
            container.register_instance("chart_repository", chart_repository)
            logger.info("Chart repository initialized")
        except Exception as e:
            logger.error(f"Failed to initialize chart repository: {e}")
            logger.warning("Continuing without chart repository - some features may not work")

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
        Database connection pool or None if connection fails

    Raises:
        RuntimeError: If database connection fails in production mode
    """
    # Check if we're in test mode
    env = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "production"))
    skip_db = os.environ.get("SKIP_DB_INIT", "").lower() in ("true", "1", "yes")

    if skip_db or env in ("test", "development"):
        logger.info("Skipping database initialization in test/development mode")
        return None

    try:
        # Get database connection parameters
        db_host = config.DB_HOST
        db_port = config.DB_PORT
        db_user = config.DB_USER
        db_password = config.DB_PASSWORD
        db_name = config.DB_NAME

        logger.info(f"Connecting to PostgreSQL database at {db_host}:{db_port}/{db_name}")

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

        # Verify connection - only if we got a pool
        if db_pool:
            async with db_pool.acquire() as conn:
                await conn.execute("SELECT 1")
                logger.info(f"Successfully connected to PostgreSQL database")

            # Verify schema using the database/__init__.py module's functions
            try:
                from ai_service.database import verify_database_schema
                await verify_database_schema()
                logger.info("Database schema verification successful")
            except Exception as schema_error:
                logger.error(f"Database schema verification failed: {schema_error}")
                # In production, this is critical
                if env == "production":
                    raise RuntimeError(f"Database schema verification failed: {schema_error}")

        return db_pool

    except Exception as e:
        error_msg = f"Database connection failed: {e}"
        logger.error(error_msg)

        # In production, database connection is critical
        if env == "production":
            raise RuntimeError(error_msg)

        # In other environments, return None to allow app to function with limited capabilities
        logger.warning("Continuing without database connection - some features will be disabled")
        return None


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
