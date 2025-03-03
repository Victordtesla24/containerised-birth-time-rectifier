#!/usr/bin/env python3

import sys
import torch
import subprocess
from typing import Dict, List, Tuple

def check_cuda_version() -> Tuple[bool, str]:
    """Check CUDA version and availability."""
    if not torch.cuda.is_available():
        return False, "CUDA is not available"
    
    return True, f"CUDA Version: {torch.version.cuda}"

def check_gpu_info() -> Tuple[bool, List[Dict[str, str]]]:
    """Get information about available GPUs."""
    if not torch.cuda.is_available():
        return False, []
    
    gpu_info = []
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        gpu_info.append({
            "name": props.name,
            "compute_capability": f"{props.major}.{props.minor}",
            "total_memory": f"{props.total_memory / 1024**3:.2f} GB",
            "multi_processor_count": str(props.multi_processor_count)
        })
    
    return True, gpu_info

def check_nvidia_driver() -> Tuple[bool, str]:
    """Check NVIDIA driver version."""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                              capture_output=True, text=True, check=True)
        return True, f"NVIDIA Driver Version: {result.stdout.strip()}"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "NVIDIA driver not found or not accessible"

def main():
    print("=== GPU Support Verification ===\n")
    
    # Check CUDA
    cuda_available, cuda_msg = check_cuda_version()
    print(f"CUDA Status: {'✓' if cuda_available else '✗'}")
    print(cuda_msg)
    print()
    
    # Check NVIDIA Driver
    driver_available, driver_msg = check_nvidia_driver()
    print(f"NVIDIA Driver Status: {'✓' if driver_available else '✗'}")
    print(driver_msg)
    print()
    
    # Check GPU Information
    gpu_available, gpu_info = check_gpu_info()
    print(f"GPU Status: {'✓' if gpu_available else '✗'}")
    if gpu_available:
        print(f"Number of GPUs: {len(gpu_info)}")
        for i, gpu in enumerate(gpu_info):
            print(f"\nGPU {i}:")
            for key, value in gpu.items():
                print(f"  {key}: {value}")
    else:
        print("No GPUs detected")
    
    # Check PyTorch
    print(f"\nPyTorch Version: {torch.__version__}")
    print(f"PyTorch CUDA: {'✓' if torch.cuda.is_available() else '✗'}")
    
    # Determine if system meets requirements
    meets_requirements = cuda_available and driver_available and gpu_available
    print(f"\nSystem meets GPU requirements: {'✓' if meets_requirements else '✗'}")
    
    return 0 if meets_requirements else 1

if __name__ == "__main__":
    sys.exit(main()) 