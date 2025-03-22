"""
Pydantic compatibility layer.

This module provides compatibility between different versions of Pydantic,
particularly to handle the transition between Pydantic V1 and Pydantic V2
where Config.Extra has been deprecated in favor of model_config with string literals.
"""

import logging
import sys
import inspect
import warnings
import types
from typing import Any, Dict, Type, Optional, TypeVar, cast

logger = logging.getLogger(__name__)

# Try to import from pydantic
try:
    import pydantic
    from pydantic import BaseModel
    PYDANTIC_V2 = hasattr(pydantic, "__version__") and pydantic.__version__.startswith("2.")
except ImportError:
    PYDANTIC_V2 = False
    logger.warning("Pydantic not installed, compatibility layer will have no effect")

# Create a direct replacement for the Extra enum that won't emit warnings
class SilentExtra:
    """Replacement for Pydantic's Extra enum that doesn't emit deprecation warnings."""
    allow = 'allow'
    ignore = 'ignore'
    forbid = 'forbid'

    def __eq__(self, other):
        """Allow comparison with string values."""
        if isinstance(other, str):
            return other in (self.allow, self.ignore, self.forbid)
        return super().__eq__(other)

def update_models_in_module(module_name):
    """Update all Pydantic models in a module to use V2 style configuration."""
    try:
        module = sys.modules.get(module_name)
        if not module:
            return False

        updated = 0
        for name, obj in inspect.getmembers(module):
            # Check if it's a Pydantic model class
            if (
                inspect.isclass(obj) and
                hasattr(obj, "__mro__") and
                BaseModel in obj.__mro__ and
                hasattr(obj, "Config") and
                hasattr(obj.Config, "extra")
            ):
                # Convert from v1 Config.extra to v2 model_config
                extra_value = getattr(obj.Config, "extra", None)
                if extra_value:
                    # Map the Extra enum to string values
                    if hasattr(extra_value, "name"):
                        # Handle enum case (like Extra.allow)
                        string_value = extra_value.name.lower()
                    else:
                        # Handle string-like case
                        string_value = str(extra_value).lower()

                    # Set the new model_config
                    if not hasattr(obj, "model_config"):
                        obj.model_config = {"extra": string_value}
                    else:
                        obj.model_config["extra"] = string_value

                    updated += 1
                    logger.info(f"Updated {module_name}.{name} to use model_config['extra'] = '{string_value}'")

        return updated > 0
    except Exception as e:
        logger.warning(f"Error updating models in module {module_name}: {e}")
        return False

def silence_extra_deprecation_warnings():
    """Directly patch Pydantic to use our silent Extra implementation."""
    if not PYDANTIC_V2:
        return

    try:
        # First approach: replace the Extra class in pydantic.config
        if hasattr(pydantic, "config") and hasattr(pydantic.config, "Extra"):
            # Store a reference to the original for restoration if needed
            original_extra = pydantic.config.Extra

            # Replace with our silent version
            pydantic.config.Extra = SilentExtra()

            # Make any getattr to pydantic.config that looks for Extra return our version
            original_getattr = pydantic.config.__getattribute__

            def patched_getattr(self, name):
                if name == 'Extra':
                    return SilentExtra()
                return original_getattr(self, name)

            # Apply the patch
            pydantic.config.__getattribute__ = patched_getattr

            # Also try to patch the warning itself
            warnings.filterwarnings("ignore", message=".*pydantic.config.Extra is deprecated.*")

            logger.info("Successfully silenced Pydantic Extra deprecation warnings")
            return True
    except Exception as e:
        logger.warning(f"Error silencing Extra deprecation warnings: {e}")
        return False

def setup_pydantic_compatibility():
    """Set up the Pydantic compatibility layer by updating model configurations."""
    if not PYDANTIC_V2:
        return False

    # First silence the deprecation warnings
    silence_extra_deprecation_warnings()

    # Find and update all pydantic models in ai_service modules
    updated_modules = 0
    for module_name in list(sys.modules.keys()):
        if module_name.startswith('ai_service.'):
            if update_models_in_module(module_name):
                updated_modules += 1

    logger.info(f"Pydantic compatibility: updated models in {updated_modules} modules")
    return True

# Auto-apply the compatibility layer when this module is imported
setup_pydantic_compatibility()
