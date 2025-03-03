import pytest
import logging
import os

# Set up logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def pytest_configure(config):
    """
    Configure pytest for container integration tests.
    """
    # Add a marker for slow tests
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    
    # Check if we're in a CI environment
    is_ci = os.environ.get("CI", "false").lower() == "true"
    
    # Log environment information
    if is_ci:
        logging.info("Running in CI environment")
    else:
        logging.info("Running in local environment")
        
    # Log whether container tests will be run or skipped
    run_container_tests = os.environ.get("RUN_CONTAINER_TESTS", "false").lower() == "true"
    if run_container_tests:
        logging.info("Container tests will be run (RUN_CONTAINER_TESTS=true)")
    else:
        logging.info("Container tests will be skipped unless containers are running (RUN_CONTAINER_TESTS=false)")

def pytest_report_header(config):
    """
    Add information to test report header.
    """
    return "Birth Time Rectifier - Integration Tests" 