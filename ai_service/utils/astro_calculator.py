"""DEPRECATED: Compatibility module - Use ai_service.core.astro_calculator instead."""

import logging
import warnings

# Issue a deprecation warning
warnings.warn(
    "ai_service.utils.astro_calculator is deprecated. Use ai_service.core.astro_calculator instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import all items from the core module
from ai_service.core.astro_calculator import *

# Add constants for backward compatibility
PLACIDUS = "P"
KOCH = "K"
EQUAL = "E"
WHOLE_SIGN = "W"

# Set up logging
logger = logging.getLogger(__name__)
logger.warning("Using deprecated astro_calculator from utils. Update imports to use ai_service.core.astro_calculator")
