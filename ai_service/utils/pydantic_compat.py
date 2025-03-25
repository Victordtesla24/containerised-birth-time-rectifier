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
        logger.error("Pydantic not installed, skipping compatibility patches")
    except Exception as e:
        logger.error(f"Error configuring Pydantic compatibility: {e}")

def _apply_v1_patches():
    """Apply patches for Pydantic v1.x compatibility."""
    try:
        # No patches needed yet
        pass
    except Exception as e:
        logger.error(f"Error applying Pydantic v1 patches: {e}")

def _apply_v2_patches():
    """Apply patches for Pydantic v2 compatibility with v1 code."""
    try:
        from pydantic import BaseModel

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
            def parse_obj_wrapper(cls, obj: Any):
                """Parse a Python object into a model instance."""
                if hasattr(cls, "model_validate"):
                    return cls.model_validate(obj)
                else:
                    # Raise error if model_validate is not available
                    raise NotImplementedError(
                        f"Class {cls.__name__} must implement model_validate for Pydantic v2 compatibility"
                    )

            # Add the classmethod to the class
            setattr(BaseModel, "parse_obj", parse_obj_wrapper)
            logger.debug("Added parse_obj() method to BaseModel for v2 compatibility")

        # Add construct method if not present
        if not hasattr(BaseModel, "construct"):
            @classmethod
            def construct_wrapper(cls, _fields_set: Optional[set] = None, **values: Any):
                """Create a model without validation."""
                if hasattr(cls, "model_construct"):
                    return cls.model_construct(_fields_set=_fields_set, **values)
                else:
                    # Raise error if model_construct is not available
                    raise NotImplementedError(
                        f"Class {cls.__name__} must implement model_construct for Pydantic v2 compatibility"
                    )

            # Add the classmethod to the class
            setattr(BaseModel, "construct", construct_wrapper)
            logger.debug("Added construct() method to BaseModel for v2 compatibility")

        # Add from_orm method if not present
        if not hasattr(BaseModel, "from_orm"):
            @classmethod
            def from_orm_wrapper(cls, obj: Any):
                """Create a model instance from an ORM object."""
                if hasattr(cls, "model_validate"):
                    return cls.model_validate(obj, from_attributes=True)
                else:
                    # Raise error if model_validate is not available
                    raise NotImplementedError(
                        f"Class {cls.__name__} must implement model_validate for Pydantic v2 compatibility"
                    )

            # Add the classmethod to the class
            setattr(BaseModel, "from_orm", from_orm_wrapper)
            logger.debug("Added from_orm() method to BaseModel for v2 compatibility")

        logger.info("Applied Pydantic v2 compatibility patches")
    except ImportError:
        logger.warning("Pydantic not available, skipping v2 patches")
    except Exception as e:
        logger.error(f"Error applying Pydantic v2 patches: {e}")
        raise
