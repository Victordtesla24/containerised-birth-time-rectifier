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

def load_env_file(env_file: Optional[str] = None) -> bool:
    """
    Load environment variables from .env file.

    Args:
        env_file: Path to .env file, defaults to .env in project root

    Returns:
        bool: True if environment variables were loaded successfully
    """
    if not DOTENV_AVAILABLE:
        logger.warning("Cannot load .env file: python-dotenv not installed")
        return False

    # Determine the .env file path
    if env_file is None:
        # Look for .env in the project root
        project_root = Path(__file__).parent.parent.parent
        env_file = str(project_root / ".env")  # Convert Path to string

    # Load the .env file
    try:
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")
        return True
    except Exception as e:
        logger.error(f"Error loading .env file: {e}")
        return False

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

def get_openai_api_key() -> str:
    """
    Get the OpenAI API key from environment variables.

    Returns:
        str: The OpenAI API key

    Raises:
        ValueError: If the API key is not set
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        error_msg = "OPENAI_API_KEY environment variable is not set"
        logger.error(error_msg)
        raise ValueError(error_msg)

    return api_key

# Load environment variables on module import
if DOTENV_AVAILABLE:
    load_env_file()
