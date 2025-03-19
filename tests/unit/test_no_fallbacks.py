"""
Test to verify that the questionnaire service has no fallbacks or mockups.
"""

import pytest
import logging
import warnings
from unittest.mock import MagicMock, AsyncMock, patch
import importlib
from typing import Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ignore deprecation warnings about astro_calculator
warnings.filterwarnings("ignore", message=".*astro_calculator is deprecated.*", category=DeprecationWarning)
