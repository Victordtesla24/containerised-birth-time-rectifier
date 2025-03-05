"""
Health check router for the Birth Time Rectifier API.
Handles all health check related endpoints.
"""

from fastapi import APIRouter, Request
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from datetime import datetime
import platform
import psutil
import os

# Create router without prefix (will be added in main.py)
router = APIRouter(
    tags=["health"],
    responses={404: {"description": "Not found"}},
)

def get_gpu_info():
    """
    Get GPU information if available.
    Returns a dict with GPU details or a placeholder if GPU is not available.
    """
    try:
        # Try to import torch for GPU detection
        import torch

        if torch.cuda.is_available():
            device = "cuda"
            # Get GPU properties
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"

            # Try to get memory info
            try:
                total_memory = torch.cuda.get_device_properties(0).total_memory
                allocated_memory = torch.cuda.memory_allocated(0)
                utilization = allocated_memory / total_memory if total_memory > 0 else 0

                return {
                    "device": device,
                    "name": device_name,
                    "count": device_count,
                    "total": round(total_memory / (1024 * 1024), 2),  # MB
                    "allocated": round(allocated_memory / (1024 * 1024), 2),  # MB
                    "utilization": round(utilization * 100, 2)  # percentage
                }
            except Exception:
                # If we can't get memory info
                return {
                    "device": device,
                    "name": device_name,
                    "count": device_count
                }
        else:
            # No CUDA available
            return {
                "device": "cpu",
                "message": "No GPU available, running on CPU"
            }
    except ImportError:
        # Torch not installed
        return {
            "device": "cpu",
            "message": "PyTorch not installed, running on CPU"
        }
    except Exception as e:
        # Some other error
        return {
            "device": "unknown",
            "message": f"Error detecting GPU: {str(e)}"
        }

@router.get("/health")
async def health_check(request: Request):
    """
    Health check endpoint to verify the API is running.
    """
    # Try to get GPU information if available
    gpu_info = get_gpu_info()

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Birth Time Rectifier API",
        "gpu": gpu_info
    }

@router.get("/details")
async def health_details(request: Request):
    """
    Detailed health check with system information.
    """
    # Try to get GPU information if available
    gpu_info = get_gpu_info()

    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Birth Time Rectifier API",
        "system": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
        },
        "gpu": gpu_info
    }

@router.get("/metrics", include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
