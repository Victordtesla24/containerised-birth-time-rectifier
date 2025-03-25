"""
Logging utility for the ai_service package.
"""

import logging
import os
import sys
from typing import Optional

# Set up the logger
logger = logging.getLogger("ai_service")

# Set default log level
DEFAULT_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, DEFAULT_LOG_LEVEL, logging.INFO)

# Configure logger if not already configured
if not logger.handlers:
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Set formatter for handler
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    # Set level
    logger.setLevel(log_level)

# Export the logger
__all__ = ["logger"]
