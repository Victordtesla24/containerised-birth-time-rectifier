"""
Environment Variables Loader.

This module handles loading environment variables from .env files
and provides utilities for validating required variables.
"""

import os
import logging
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

# Set up logging
logger = logging.getLogger(__name__)

# Try to import dotenv
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    logger.warning("python-dotenv not installed, .env files will not be loaded automatically")
    DOTENV_AVAILABLE = False

def load_env_file(env_file_path: Optional[str] = None) -> Dict[str, str]:
    """
    Load environment variables from a .env file.

    Args:
        env_file_path: Path to the .env file (default: None, uses current directory)

    Returns:
        Dictionary of loaded environment variables
    """
    # Default to .env in the current or parent directory
    if env_file_path is None:
        # Check if .env exists in the current directory
        if os.path.exists(".env"):
            env_file_path = ".env"
        # Check if .env exists in the parent directory
        elif os.path.exists("../.env"):
            env_file_path = "../.env"
        # Check if .env exists in the project root directory
        elif os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")):
            env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        else:
            logger.info("No .env file found in current, parent, or project root directory")
            return {}

    # Ensure env_file_path is a Path object
    env_path = Path(env_file_path)

    # Check if the file exists
    if not env_path.exists():
        logger.info(f"Env file does not exist: {env_path}")
        return {}

    # Load environment variables from the file
    loaded_vars = {}
    try:
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Split the line into key and value
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]

                    # Set environment variable if not already set
                    if key not in os.environ:
                        os.environ[key] = value
                        loaded_vars[key] = value
                        logger.debug(f"Loaded env var: {key}")
                    else:
                        logger.debug(f"Env var already exists: {key}")

        # Special handling for critical variables like OPENAI_API_KEY
        if 'OPENAI_API_KEY' in loaded_vars:
            logger.info("OPENAI_API_KEY loaded from .env file")

        return loaded_vars
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")
        return {}

def validate_required_env_vars(required_vars: List[str]) -> Dict[str, str]:
    """
    Validate that required environment variables are set.

    Args:
        required_vars: List of required environment variable names

    Returns:
        Dict mapping variable names to their values

    Raises:
        ValueError: If any required variables are missing
    """
    # Check for missing variables
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Return values of required variables
    return {var: os.environ.get(var, "") for var in required_vars}

def get_env_with_fallback(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get an environment variable with fallback to .env file.

    This function prioritizes environment variables over .env files,
    which allows for runtime configuration through container env vars.

    Args:
        key: Environment variable name
        default: Default value if not found (default: None)

    Returns:
        Environment variable value or default
    """
    # First check if the variable is already in the environment
    value = os.environ.get(key)

    # If not found, try to load from .env file
    if value is None:
        env_vars = load_env_file()
        value = env_vars.get(key)

        # If found in .env, set it in the environment for future use
        if value is not None:
            os.environ[key] = value
            logger.info(f"Set {key} from .env file")

    # Return the value or default
    return value if value is not None else default

# Load environment variables on module import
if DOTENV_AVAILABLE:
    load_env_file()
