#!/usr/bin/env python3
"""
Script to run all birth time rectification integration tests in sequence.
This script combines all the individual test files and runs them together.
"""

import asyncio
import logging
import os
import sys
import pytest
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("birth_time_rectification_tests")

# Add project root to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Create a clean state for test sequence
def clear_test_state():
    """Clear any test sequence state from previous runs."""
    state_file = Path.home() / ".birth_rectifier_test_state.json"
    if state_file.exists():
        state_file.unlink()
        logger.info(f"Cleared test state file: {state_file}")

async def run_all_tests():
    """Run all birth time rectification tests in sequence."""
    logger.info("Starting all birth time rectification tests")

    # Clear previous test state
    clear_test_state()

    # Order of tests to run
    test_files = [
        "test_integration_birth_time_01_session_init.py",
        "test_integration_birth_time_02_geocoding.py",
        "test_integration_birth_time_03_birth_chart.py",
        "test_integration_birth_time_04_openai_verification.py",
        "test_integration_birth_time_05_dynamic_questionnaire.py",
        "test_integration_birth_time_06_adaptive_flow.py",
        "test_integration_birth_time_07_birth_time_rectification.py",
        "test_integration_birth_time_08_chart_comparison.py",
        "test_integration_birth_time_09_chart_interpretation.py",
        "test_integration_birth_time_10_chart_export.py",
    ]

    # Full path to test directory
    test_dir = Path(__file__).parent

    # Run each test in sequence
    for test_file in test_files:
        test_path = test_dir / test_file
        if not test_path.exists():
            logger.warning(f"Test file not found: {test_path}")
            continue

        logger.info(f"Running test: {test_file}")
        # Run the test using pytest in a subprocess
        exit_code = pytest.main(["-xvs", str(test_path)])

        if exit_code != 0:
            logger.error(f"Test {test_file} failed with exit code {exit_code}")
            return exit_code

        logger.info(f"Test {test_file} completed successfully")

    # Finally, run the sequence flow real test
    logger.info("Running sequence flow real test")
    sequence_test = Path(__file__).parent.parent / "sequence_flows" / "test_integration_sequence_flow_real.py"
    if sequence_test.exists():
        exit_code = pytest.main(["-xvs", str(sequence_test)])

        if exit_code != 0:
            logger.error(f"Sequence flow test failed with exit code {exit_code}")
            return exit_code

        logger.info("Sequence flow test completed successfully")
    else:
        logger.warning(f"Sequence flow test file not found: {sequence_test}")

    logger.info("All tests completed successfully")
    return 0

if __name__ == "__main__":
    # Run all tests
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
