"""
GPU Memory Management for PyTorch.

This module provides utilities for managing GPU memory when running PyTorch.
When torch is not available, it provides mock implementations.
"""

import os
import logging
from typing import Optional, Dict, Any, Union

# Configure logging
logger = logging.getLogger(__name__)

# Check if torch is available
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("PyTorch not found. Using mock GPU manager.")
    TORCH_AVAILABLE = False

class GPUMemoryManager:
    """
    Manages GPU memory allocation for PyTorch.

    This class helps control how much GPU memory is allocated to PyTorch,
    which is useful when running on shared systems or when you want to
    limit memory usage.
    """

    def __init__(self, memory_fraction: float = 0.7):
        """
        Initialize the GPU memory manager.

        Args:
            memory_fraction: Fraction of GPU memory to allocate (0.0 to 1.0)
        """
        self.memory_fraction = memory_fraction
        self.is_cuda_available = TORCH_AVAILABLE and self._check_cuda_available() if TORCH_AVAILABLE else False

        if self.is_cuda_available:
            logger.info(f"CUDA is available. Setting memory fraction to {memory_fraction}")
            self._set_memory_fraction(memory_fraction)
        else:
            logger.info("CUDA is not available or torch is not installed. GPU memory management disabled.")

    def _check_cuda_available(self) -> bool:
        """Check if CUDA is available."""
        if TORCH_AVAILABLE:
            return torch.cuda.is_available()
        return False

    def _set_memory_fraction(self, memory_fraction: float) -> None:
        """
        Set the memory fraction for all available GPUs.

        Args:
            memory_fraction: Fraction of GPU memory to allocate (0.0 to 1.0)
        """
        if not self.is_cuda_available or not TORCH_AVAILABLE:
            return

        try:
            for device in range(torch.cuda.device_count()):
                torch.cuda.set_per_process_memory_fraction(memory_fraction, device)
                logger.info(f"Set memory fraction to {memory_fraction} for GPU {device}")
        except Exception as e:
            logger.error(f"Error setting GPU memory fraction: {e}")

    def get_gpu_info(self) -> Union[Dict[str, Dict[str, float]], Dict[str, str]]:
        """
        Get information about available GPUs.

        Returns:
            Dictionary with GPU info (total memory, used memory, free memory)
            or status dictionary if GPUs are not available
        """
        if not self.is_cuda_available or not TORCH_AVAILABLE:
            return {"status": "no_gpu_available"}

        try:
            info = {}
            for device in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(device)
                total_memory = props.total_memory / 1024**3  # Convert to GB
                memory_allocated = torch.cuda.memory_allocated(device) / 1024**3
                memory_reserved = torch.cuda.memory_reserved(device) / 1024**3

                info[f"gpu_{device}"] = {
                    "name": props.name,
                    "total_memory_gb": round(total_memory, 2),
                    "allocated_memory_gb": round(memory_allocated, 2),
                    "reserved_memory_gb": round(memory_reserved, 2),
                    "free_memory_gb": round(total_memory - memory_reserved, 2)
                }
            return info
        except Exception as e:
            logger.error(f"Error getting GPU info: {e}")
            return {"status": "error", "message": str(e)}

# Create a singleton instance
gpu_manager = GPUMemoryManager(
    memory_fraction=float(os.getenv("GPU_MEMORY_FRACTION", "0.7"))
)
