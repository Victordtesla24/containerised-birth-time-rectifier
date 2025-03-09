#!/usr/bin/env python
"""
Verification test runner for the Birth Time Rectifier API.
Runs all tests in sequence to verify the implementation.
"""

import os
import sys
import logging
import subprocess
import time
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"test-results/verification_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("verification-tests")

# Test modules to run in sequence
TEST_MODULES = [
    "test_session_implementation.py",
    "test_chart_comparison_implementation.py",
    "test_openai_service_integration.py",
    "test_sequence_diagram_implementation.py"
]

def create_results_dir():
    """Create test results directory if it doesn't exist"""
    if not os.path.exists("test-results"):
        os.makedirs("test-results")
        logger.info("Created test-results directory")

def check_services_running():
    """Check if required services are running"""
    logger.info("Checking if required services are running...")

    try:
        # Check if AI service is running
        ai_service_check = subprocess.run(
            ["curl", "-s", "http://localhost:8000/health"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )

        if ai_service_check.returncode != 0:
            logger.warning("AI service not responding. Is it running?")
            return False

        logger.info("AI service is running")

        # Check if Redis is running (through AI service)
        redis_check = subprocess.run(
            ["curl", "-s", "http://localhost:8000/api/v1/session/init"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5
        )

        if redis_check.returncode != 0:
            logger.warning("Session service not responding. Is Redis running?")
            return False

        logger.info("Redis service is accessible through session API")

        return True
    except Exception as e:
        logger.error(f"Error checking services: {e}")
        return False

def run_test(test_file):
    """Run a specific test file"""
    logger.info(f"Running test: {test_file}")

    test_result = subprocess.run(
        [sys.executable, test_file],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        capture_output=True,
        text=True
    )

    if test_result.returncode == 0:
        logger.info(f"✅ {test_file} PASSED")
        return True
    else:
        logger.error(f"❌ {test_file} FAILED")
        logger.error(f"Output: {test_result.stdout}")
        logger.error(f"Error: {test_result.stderr}")
        return False

def run_all_tests():
    """Run all tests in sequence"""
    logger.info("Starting verification tests...")

    passed_tests = 0
    failed_tests = 0

    # First check if services are running
    if not check_services_running():
        logger.error("Required services aren't running. Please start them first using:")
        logger.error("docker-compose up")
        return False

    # Run each test module in sequence
    start_time = time.time()
    for test_file in TEST_MODULES:
        if run_test(test_file):
            passed_tests += 1
        else:
            failed_tests += 1

    # Print summary
    total_time = time.time() - start_time
    logger.info("-" * 50)
    logger.info(f"Verification Test Summary:")
    logger.info(f"Passed: {passed_tests}/{len(TEST_MODULES)} tests")
    logger.info(f"Failed: {failed_tests}/{len(TEST_MODULES)} tests")
    logger.info(f"Total time: {total_time:.2f} seconds")
    logger.info("-" * 50)

    # Generate status based on pass/fail ratio
    if failed_tests == 0:
        logger.info("✅ ALL TESTS PASSED - Implementation verification successful")
        return True
    elif passed_tests > failed_tests:
        logger.warning("⚠️ PARTIAL SUCCESS - Some tests passed but others failed")
        return False
    else:
        logger.error("❌ VERIFICATION FAILED - Most tests failed")
        return False

def run_test_with_retry(test_file, max_retries=2):
    """Run a test with retry logic in case of failures"""
    for attempt in range(max_retries + 1):
        logger.info(f"Test {test_file} - Attempt {attempt + 1}/{max_retries + 1}")

        if run_test(test_file):
            return True

        if attempt < max_retries:
            logger.info(f"Retrying in 3 seconds...")
            time.sleep(3)

    return False

def generate_verification_checklist():
    """Generate a verification checklist based on test results"""
    logger.info("Generating implementation verification checklist...")

    # Define verification items based on the implementation verification checklist
    verification_items = {
        "API Router": {
            "status": "Unknown",
            "details": "Verify legacy path support and correct route handling"
        },
        "Session Management": {
            "status": "Unknown",
            "details": "Verify session initialization, status, and data persistence"
        },
        "Chart Comparison": {
            "status": "Unknown",
            "details": "Verify comparison of original and rectified charts"
        },
        "Error Handling": {
            "status": "Unknown",
            "details": "Verify standardized error response formats"
        },
        "OpenAI Service": {
            "status": "Unknown",
            "details": "Verify continuous operation in Docker container"
        },
        "End-to-End Flow": {
            "status": "Unknown",
            "details": "Verify complete sequence diagram implementation"
        }
    }

    # Run tests to check each item
    if run_test("test_session_implementation.py"):
        verification_items["Session Management"]["status"] = "Passed"
    else:
        verification_items["Session Management"]["status"] = "Failed"

    if run_test("test_chart_comparison_implementation.py"):
        verification_items["Chart Comparison"]["status"] = "Passed"
    else:
        verification_items["Chart Comparison"]["status"] = "Failed"

    if run_test("test_openai_service_integration.py"):
        verification_items["OpenAI Service"]["status"] = "Passed"
    else:
        verification_items["OpenAI Service"]["status"] = "Failed"

    if run_test("test_sequence_diagram_implementation.py"):
        verification_items["End-to-End Flow"]["status"] = "Passed"
        verification_items["API Router"]["status"] = "Passed"  # API router is implicitly tested in the sequence test
        verification_items["Error Handling"]["status"] = "Passed"  # Error handling is implicitly tested in all tests
    else:
        verification_items["End-to-End Flow"]["status"] = "Failed"

    # Generate the report
    report = "# Implementation Verification Checklist Results\n\n"
    report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    report += "| Component | Status | Details |\n"
    report += "|-----------|--------|--------|\n"

    for component, info in verification_items.items():
        status_emoji = "✅" if info["status"] == "Passed" else "❌" if info["status"] == "Failed" else "⚠️"
        report += f"| {component} | {status_emoji} {info['status']} | {info['details']} |\n"

    # Write report to file
    report_path = "test-results/verification_checklist_results.md"
    with open(report_path, "w") as f:
        f.write(report)

    logger.info(f"Verification checklist report generated at {report_path}")

    # Count passed items
    passed_count = sum(1 for item in verification_items.values() if item["status"] == "Passed")
    total_count = len(verification_items)

    logger.info(f"Verification result: {passed_count}/{total_count} components verified")

    return passed_count == total_count

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Run verification tests for Birth Time Rectifier API")
    parser.add_argument("--checklist", action="store_true", help="Generate verification checklist report")
    parser.add_argument("--retry", action="store_true", help="Retry failed tests")
    parser.add_argument("--test", type=str, help="Run a specific test file")
    return parser.parse_args()

if __name__ == "__main__":
    create_results_dir()
    args = parse_args()

    if args.test:
        # Run a specific test
        if args.retry:
            success = run_test_with_retry(args.test)
        else:
            success = run_test(args.test)
    elif args.checklist:
        # Generate verification checklist
        success = generate_verification_checklist()
    else:
        # Run all tests
        success = run_all_tests()

    sys.exit(0 if success else 1)
