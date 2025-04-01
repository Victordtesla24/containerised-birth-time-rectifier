"""
GPU Memory Management Module

This module provides utilities for managing GPU memory allocation.
"""

import logging
import os
from typing import Dict, Union, Optional, Any

# Configure logging
logger = logging.getLogger(__name__)

# Check for TensorFlow
TF_AVAILABLE = False
try:
    import tensorflow as tf  # type: ignore
    TF_AVAILABLE = True
except ImportError:
    # Define a placeholder for type checking when tensorflow is not available
    class MockTensorflow:
        """Mock class when tensorflow is not available."""
        class config:
            @staticmethod
            def list_physical_devices(*args, **kwargs):
                return []

            class experimental:
                @staticmethod
                def set_memory_growth(*args, **kwargs):
                    pass

        class keras:
            class backend:
                @staticmethod
                def clear_session():
                    pass

    # Create a placeholder for linter
    tf = MockTensorflow()  # type: ignore
    logger.warning("TensorFlow not available. GPU acceleration will be disabled.")

# Check for psutil (for memory tracking)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available. Memory tracking will be limited.")

class GPUMemoryManager:
    """
    Manages GPU memory allocation for the application.
    This class provides utilities to allocate and manage GPU memory for
    machine learning models and other GPU-accelerated operations.
    """

    def __init__(self, memory_fraction=0.7):
        """
        Initialize the GPU memory manager.

        Args:
            memory_fraction: Fraction of GPU memory to allocate (default 0.7)
        """
        self.memory_fraction = memory_fraction
        self.is_gpu_available = False
        self.devices = []
        self.initialized = False

        # Initialize GPU if available
        if TF_AVAILABLE:
            try:
                # Try to initialize TensorFlow with GPU support
                gpus = tf.config.list_physical_devices('GPU')

                if gpus:
                    self.is_gpu_available = True
                    self.devices = gpus

                    # Set memory growth
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)

                    # Log GPU information
                    logger.info(f"Found {len(gpus)} GPU devices")
                    self.initialized = True
                else:
                    logger.info("No GPU devices available, running in CPU mode")
            except Exception as e:
                logger.error(f"Error initializing GPU: {e}")
        else:
            logger.info("TensorFlow not installed, GPU acceleration disabled")

    def get_memory_info(self):
        """
        Get current GPU memory usage information.

        Returns:
            Dictionary with GPU memory information
        """
        if not self.is_gpu_available:
            return {"status": "gpu_not_available", "devices": 0}

        if not TF_AVAILABLE:
            return {"status": "tensorflow_not_available", "devices": 0}

        try:
            memory_info = []
            for i, device in enumerate(self.devices):
                try:
                    # Get memory info for each GPU
                    memory_info.append({
                        "device_id": i,
                        "device_name": device.name.decode('utf-8') if hasattr(device.name, 'decode') else device.name,
                        "memory_limit_fraction": self.memory_fraction
                    })
                except Exception as e:
                    logger.error(f"Error getting memory info for GPU {i}: {e}")

            # Also get system memory info if psutil is available
            system_memory = {}
            if PSUTIL_AVAILABLE:
                mem = psutil.virtual_memory()
                system_memory = {
                    "total": mem.total,
                    "available": mem.available,
                    "percent_used": mem.percent
                }

            return {
                "status": "gpu_available",
                "devices": len(self.devices),
                "gpu_memory_info": memory_info,
                "system_memory": system_memory
            }
        except Exception as e:
            logger.error(f"Error getting GPU memory info: {e}")
            return {"status": "error", "message": str(e), "devices": len(self.devices)}

    def cleanup(self):
        """
        Release GPU resources when shutting down.
        """
        if not self.is_gpu_available or not TF_AVAILABLE:
            return

        try:
            # Clear TensorFlow session
            tf.keras.backend.clear_session()
            logger.info("TensorFlow session cleared")

            # Additional cleanup if needed
            import gc
            gc.collect()

            logger.info("GPU resources released")
        except Exception as e:
            logger.error(f"Error cleaning up GPU resources: {e}")

# Create a singleton instance
_instance = None

def get_gpu_manager() -> GPUMemoryManager:
    """
    Get the GPU memory manager singleton instance.

    Returns:
        GPUMemoryManager instance
    """
    global _instance
    if _instance is None:
        # Get memory fraction from environment or use default
        memory_fraction = float(os.environ.get("GPU_MEMORY_FRACTION", "0.7"))
        _instance = GPUMemoryManager(memory_fraction=memory_fraction)
    return _instance
