"""
Application Startup Module.

This module handles initializing services and the dependency container
at application startup time, implementing the key best practices:

1. Error First Approach
2. Robust Error Handling
3. Dependency Requirements
4. Configuration Validation
5. Proper Logging
"""

import os
import logging
import sys
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import environment loader
from ai_service.utils.env_loader import load_env_file, validate_required_env_vars

# Import dependency container
from ai_service.utils.dependency_container import get_container

# Import service factories
from ai_service.api.services.openai.service import create_openai_service
from ai_service.services.chart_service import create_chart_service

# Import Pydantic compatibility layer first to ensure it's applied
# before any other imports that might use Pydantic
from ai_service.utils import pydantic_compat

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import logging.config

from ai_service.core.config import settings


def validate_configuration() -> Dict[str, Any]:
    """
    Validate required configuration settings.

    This implements the "Configuration Validation" best practice by checking
    all required settings at startup time.

    Returns:
        Dict with configuration values

    Raises:
        ValueError: If any required configuration is missing
    """
    logger.info("Validating application configuration")

    # Load environment variables from .env file
    load_env_file()

    # Required environment variables
    required_vars = [
        "OPENAI_API_KEY"
    ]

    # Validate required variables and get their values
    env_vars = validate_required_env_vars(required_vars)

    # Optional environment variables with defaults
    config = {
        "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", "gpt-4-turbo-preview"),
        "OPENAI_TEMPERATURE": float(os.environ.get("OPENAI_TEMPERATURE", "0.7")),
        "ENABLE_CACHE": os.environ.get("ENABLE_CACHE", "true").lower() == "true",
        "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO")
    }

    # Add required variables to config
    config.update(env_vars)

    # Log the configuration (excluding sensitive values)
    safe_config = {k: v for k, v in config.items() if "KEY" not in k and "SECRET" not in k}
    logger.info(f"Configuration validated: {safe_config}")

    return config


def register_services():
    """
    Register services with the dependency container.

    This implements the "Dependency Requirements" best practice by explicitly
    defining and registering all service dependencies.
    """
    logger.info("Registering services with dependency container")

    # Get container
    container = get_container()

    try:
        # Register OpenAI service
        container.register("openai_service", create_openai_service)
        logger.info("Registered OpenAI service factory")

        # Register Chart service
        container.register("chart_service", create_chart_service)
        logger.info("Registered Chart service factory")

        # Additional services would be registered here

    except Exception as e:
        logger.error(f"Error registering services: {e}")
        raise ValueError(f"Failed to register services: {e}")


def initialize_application() -> bool:
    """
    Initialize the application.

    This implements the "Error First Approach" and "Robust Error Handling"
    best practices by failing fast with clear errors.

    Returns:
        True if initialization was successful

    Raises:
        ValueError: If initialization fails
    """
    try:
        logger.info("Beginning application initialization")

        # Validate configuration
        config = validate_configuration()

        # Register services
        register_services()

        # Pre-create singleton instances to verify they work
        # This helps catch errors at startup time rather than at first use
        container = get_container()

        try:
            # Create OpenAI service to verify it works
            openai_service = container.get("openai_service")
            logger.info("OpenAI service initialized successfully")

            # Create Chart service to verify it works
            chart_service = container.get("chart_service")
            logger.info("Chart service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise ValueError(f"Failed to initialize services: {e}")

        logger.info("Application initialization completed successfully")
        return True

    except Exception as e:
        logger.critical(f"Application initialization failed: {e}")
        raise


if __name__ == "__main__":
    # When run directly, initialize the application
    try:
        initialize_application()
        logger.info("Application is ready")
    except Exception as e:
        logger.critical(f"Failed to initialize application: {e}")
        sys.exit(1)
