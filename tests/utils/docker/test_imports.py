#!/usr/bin/env python3
"""
Test script to verify imports work correctly in the containerized environment.
This helps catch circular dependencies and missing dependencies early.
"""

import sys
import importlib
import traceback
import os

def test_import(module_name):
    """Test importing a module and report success or failure."""
    try:
        module = importlib.import_module(module_name)
        print(f"✅ Successfully imported {module_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to import {module_name}: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # List of critical modules to verify
    modules_to_test = [
        "fastapi",
        "pytest",
        "pyswisseph",
        "timezonefinder",
        "matplotlib",
        "reportlab",
        "geopy",
        "ai_service",
        "ai_service.utils",
        "ai_service.utils.formatting",  # Test the formatting module specifically
    ]

    # Show PYTHONPATH for debugging
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")
    print(f"sys.path: {sys.path}")

    success_count = 0
    for module in modules_to_test:
        if test_import(module):
            success_count += 1

    total = len(modules_to_test)
    print(f"\nImport test results: {success_count}/{total} modules imported successfully")

    # Print Python executable path
    print(f"\nPython executable: {sys.executable}")

    # Verify that all formatting functions can be imported
    if "ai_service.utils.formatting" in modules_to_test:
        try:
            from ai_service.utils.formatting import (
                format_degree,
                format_longitude,
                format_time,
                format_aspect,
                format_planet_position
            )
            print("\n✅ All formatting functions imported successfully!")
        except ImportError as e:
            print(f"\n❌ Failed to import formatting functions: {e}")
            traceback.print_exc()

    # Exit with success only if the original error is fixed
    if "ai_service.utils.formatting" in modules_to_test and not test_import("ai_service.utils.formatting"):
        sys.exit(1)

    print("Formatting module imports successful!")
    sys.exit(0)
