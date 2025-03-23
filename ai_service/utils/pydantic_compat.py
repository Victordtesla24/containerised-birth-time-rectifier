"""
Pydantic compatibility module.

This module handles compatibility between different versions of Pydantic,
particularly for transitioning from v1 to v2.
"""

import logging
import warnings
import sys
from typing import Any, Dict, TypeVar, Type, cast, Generic, Optional, Union, ClassVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

def configure_pydantic_compat():
    """
    Configure Pydantic compatibility settings.

    This function:
    1. Silences deprecation warnings from Pydantic
    2. Applies patches for compatibility between versions
    """
    # Silence deprecation warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic")

    # Apply patches
    try:
        import pydantic

        # Check pydantic version
        version = getattr(pydantic, "__version__", "unknown")
        logger.info(f"Configured Pydantic compatibility (version: {version})")

        if version.startswith("2."):
            _apply_v2_patches()
        else:
            _apply_v1_patches()
    except ImportError:
        logger.warning("Pydantic not found, skipping compatibility configuration")

def _apply_v1_patches():
    """Apply patches for Pydantic v1.x compatibility."""
    try:
        # No patches needed yet
        pass
    except Exception as e:
        logger.error(f"Error applying Pydantic v1 patches: {e}")

def _apply_v2_patches():
    """Apply patches for Pydantic v2.x compatibility."""
    try:
        # Import v2-specific modules
        from pydantic import BaseModel

        # Add patches for v1 compatibility if not already present

        # Add dict method if not present
        if not hasattr(BaseModel, "dict"):
            def dict_wrapper(self, **kwargs) -> Dict[str, Any]:
                return self.model_dump(**kwargs)

            # Add the method to the class
            setattr(BaseModel, "dict", dict_wrapper)
            logger.debug("Added dict() method to BaseModel for v2 compatibility")

        # Add parse_obj method if not present
        if not hasattr(BaseModel, "parse_obj"):
            @classmethod
            def parse_obj_wrapper(cls: Type[T], obj: Any) -> T:
                """Parse a Python object into a model instance."""
                return cls.model_validate(obj)

            # Add the classmethod to the class
            setattr(BaseModel, "parse_obj", parse_obj_wrapper)
            logger.debug("Added parse_obj() method to BaseModel for v2 compatibility")

        # Add construct method if not present
        if not hasattr(BaseModel, "construct"):
            @classmethod
            def construct_wrapper(cls: Type[T], _fields_set: Optional[set] = None, **values: Any) -> T:
                """Create a model without validation."""
                return cls.model_construct(_fields_set=_fields_set or set(), **values)

            # Add the classmethod to the class
            setattr(BaseModel, "construct", construct_wrapper)
            logger.debug("Added construct() method to BaseModel for v2 compatibility")

        # Add from_orm method if not present
        if not hasattr(BaseModel, "from_orm"):
            @classmethod
            def from_orm_wrapper(cls: Type[T], obj: Any) -> T:
                """Create a model from an ORM object."""
                return cls.model_validate(obj)

            # Add the classmethod to the class
            setattr(BaseModel, "from_orm", from_orm_wrapper)
            logger.debug("Added from_orm() method to BaseModel for v2 compatibility")

    except Exception as e:
        logger.error(f"Error applying Pydantic v2 patches: {e}")
