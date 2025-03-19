#!/usr/bin/env python
"""
API Sequence Test Runner

This script runs the comprehensive API sequence tests for the Birth Time Rectifier application.
It coordinates the execution of individual test suites that validate the sequence flows
described in the sequence_diagram.md documentation.
"""

import os
import sys
import logging
import asyncio
import argparse
import time
from typing import Dict, List, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("api_sequence_tests.log")
    ]
)
logger = logging.getLogger("api-sequence-tests")

# Import test modules if available
try:
    from tests.integration.test_api_sequence_flow import TestApiSequenceFlow
except ImportError:
    logger.warning("Could not import TestApiSequenceFlow, skipping integration tests")
    TestApiSequenceFlow = None

try:
    from tests.unit.test_questionnaire_api_flow import TestQuestionnaireApiFlow
except ImportError:
    logger.warning("Could not import TestQuestionnaireApiFlow, skipping questionnaire tests")
    TestQuestionnaireApiFlow = None

try:
    from tests.unit.test_chart_verification import TestChartVerification
except ImportError:
    logger.warning("Could not import TestChartVerification, skipping chart verification tests")
    TestChartVerification = None

def setup_environment():
    """Set up the test environment."""
    logger.info("Setting up test environment")

    # Check if API service is reachable
    api_url = os.environ.get('API_URL', 'http://localhost:9000')
    logger.info(f"Using API URL: {api_url}")

    # Check for OpenAI API key
    if not os.environ.get('OPENAI_API_KEY'):
        logger.warning("OPENAI_API_KEY environment variable is not set")
        logger.warning("Tests requiring OpenAI API will be skipped or use mocks")

    return {
        "api_url": api_url,
        "openai_key_available": bool(os.environ.get('OPENAI_API_KEY'))
    }

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run API sequence tests")
    parser.add_argument(
        "--skip-openai",
        action="store_true",
        help="Skip tests that require OpenAI API"
    )
    parser.add_argument(
        "--test-suite",
        choices=["all", "integration", "questionnaire", "verification"],
        default="all",
        help="Specify which test suite to run"
    )
    parser.add_argument(
        "--api-url",
        help="Override the API URL (default: http://localhost:9000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()

async def run_integration_tests(env_config: Dict[str, Any]) -> bool:
    """Run integration tests for API sequence flow."""
    if not TestApiSequenceFlow:
        logger.error("Integration tests not available - TestApiSequenceFlow not imported")
        return False

    logger.info("Running API sequence flow integration tests")
    test_instance = TestApiSequenceFlow()

    try:
        await test_instance.setup()
        result = await test_instance.run_sequence_tests()
        return result
    except Exception as e:
        logger.error(f"Error running integration tests: {str(e)}")
        return False
    finally:
        await test_instance.teardown()

def run_questionnaire_tests(env_config: Dict[str, Any]) -> bool:
    """Run questionnaire API flow tests."""
    if not TestQuestionnaireApiFlow:
        logger.error("Questionnaire tests not available - TestQuestionnaireApiFlow not imported")
        return False

    logger.info("Running questionnaire API flow tests")
    test_instance = TestQuestionnaireApiFlow()

    try:
        test_instance.setup()
        result = test_instance.run_questionnaire_tests()
        return result
    except Exception as e:
        logger.error(f"Error running questionnaire tests: {str(e)}")
        return False
    finally:
        test_instance.teardown()

async def run_verification_tests(env_config: Dict[str, Any]) -> bool:
    """Run chart verification tests."""
    if not TestChartVerification:
        logger.error("Verification tests not available - TestChartVerification not imported")
        return False

    # Skip if OpenAI tests are disabled
    if env_config.get("skip_openai", False):
        logger.info("Skipping OpenAI verification tests as requested")
        return True

    # Skip if no OpenAI key
    if not env_config.get("openai_key_available", False):
        logger.warning("Skipping OpenAI verification tests due to missing API key")
        return True

    logger.info("Running chart verification tests")
    test_instance = TestChartVerification()

    try:
        test_instance.setup()
        result = await test_instance.run_verification_tests()
        return result
    except Exception as e:
        logger.error(f"Error running verification tests: {str(e)}")
        return False
    finally:
        test_instance.teardown()

async def run_all_tests(env_config: Dict[str, Any]) -> Dict[str, bool]:
    """Run all test suites."""
    results = {}

    # Run integration tests
    results["integration"] = await run_integration_tests(env_config)

    # Run questionnaire tests
    results["questionnaire"] = run_questionnaire_tests(env_config)

    # Run verification tests
    results["verification"] = await run_verification_tests(env_config)

    return results

async def main():
    """Main test runner function."""
    start_time = time.time()
    logger.info("Starting API sequence tests")

    # Parse arguments
    args = parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Setup environment
    env_config = setup_environment()

    # Override API URL if provided
    if args.api_url:
        env_config["api_url"] = args.api_url
        os.environ["API_URL"] = args.api_url

    # Add skip_openai flag
    env_config["skip_openai"] = args.skip_openai

    # Run tests based on selected suite
    results = {}
    if args.test_suite == "all":
        results = await run_all_tests(env_config)
    elif args.test_suite == "integration":
        results["integration"] = await run_integration_tests(env_config)
    elif args.test_suite == "questionnaire":
        results["questionnaire"] = run_questionnaire_tests(env_config)
    elif args.test_suite == "verification":
        results["verification"] = await run_verification_tests(env_config)

    # Calculate overall success
    success_count = sum(1 for result in results.values() if result)
    total_tests = len(results)
    success_rate = (success_count / total_tests) * 100 if total_tests > 0 else 0

    # Print results
    logger.info("-" * 50)
    logger.info(f"API Sequence Tests Results ({success_rate:.1f}% success rate):")

    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name.upper()}: {status}")

    logger.info("-" * 50)
    logger.info(f"Total execution time: {time.time() - start_time:.2f} seconds")

    # Exit with appropriate code
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.warning("Tests interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error during test execution: {str(e)}")
        sys.exit(1)
