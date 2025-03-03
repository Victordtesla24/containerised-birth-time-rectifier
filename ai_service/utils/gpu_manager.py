import torch
import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class GPUMemoryManager:
    def __init__(self, model_allocation: float = 0.7, viz_allocation: float = 0.3):
        """Initialize GPU memory manager.
        
        Args:
            model_allocation: Fraction of GPU memory to allocate for AI model
            viz_allocation: Fraction of GPU memory to allocate for visualization
        """
        self.model_allocation = model_allocation
        self.viz_allocation = viz_allocation
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        if self.device == "cuda":
            self.total_memory = torch.cuda.get_device_properties(0).total_memory
            self._setup_memory_allocation()
            logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
            logger.info(f"Total GPU memory: {self.total_memory / 1e9:.2f} GB")
        else:
            logger.warning("No GPU detected, using CPU")
    
    def _setup_memory_allocation(self):
        """Set up GPU memory allocation."""
        try:
            # Set memory fraction for model
            torch.cuda.set_per_process_memory_fraction(self.model_allocation)
            
            # Empty cache
            torch.cuda.empty_cache()
            
            logger.info(f"GPU memory allocated for model: {self.model_allocation * 100:.1f}%")
            logger.info(f"GPU memory allocated for visualization: {self.viz_allocation * 100:.1f}%")
        except Exception as e:
            logger.error(f"Error setting up GPU memory allocation: {e}")
            raise
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get current GPU memory usage information."""
        if self.device == "cpu":
            return {"device": "cpu"}
            
        try:
            allocated = torch.cuda.memory_allocated()
            cached = torch.cuda.memory_reserved()
            
            return {
                "device": self.device,
                "total": self.total_memory,
                "allocated": allocated,
                "allocated_gb": allocated / 1e9,
                "cached": cached,
                "cached_gb": cached / 1e9,
                "utilization": allocated / self.total_memory * 100
            }
        except Exception as e:
            logger.error(f"Error getting GPU memory info: {e}")
            return {"device": self.device, "error": str(e)}
    
    def optimize_memory(self, model: Optional[torch.nn.Module] = None):
        """Optimize GPU memory usage.
        
        Args:
            model: PyTorch model to optimize
        """
        if self.device == "cpu":
            return
            
        try:
            # Clear cache
            torch.cuda.empty_cache()
            
            if model is not None:
                # Use mixed precision if available
                if torch.cuda.is_available() and hasattr(torch.cuda, 'amp'):
                    model.half()
                    logger.info("Using mixed precision (FP16)")
                
                # Enable gradient checkpointing if available
                if hasattr(model, 'gradient_checkpointing_enable'):
                    model.gradient_checkpointing_enable()
                    logger.info("Gradient checkpointing enabled")
            
            logger.info("Memory optimization completed")
            logger.info(f"Current memory usage: {self.get_memory_info()}")
        except Exception as e:
            logger.error(f"Error optimizing GPU memory: {e}")
            raise
    
    def cleanup(self):
        """Clean up GPU memory."""
        if self.device == "cpu":
            return
            
        try:
            torch.cuda.empty_cache()
            logger.info("GPU memory cache cleared")
        except Exception as e:
            logger.error(f"Error cleaning up GPU memory: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup() 