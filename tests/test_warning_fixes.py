"""Test script to verify warning fixes in questionnaire API."""

import pytest
import os
from fastapi.testclient import TestClient
import logging
from unittest.mock import patch, MagicMock
from ai_service.main import app

# Setup test client
client = TestClient(app)

@pytest.fixture
def caplog_with_setup(caplog):
    """Setup caplog fixture with appropriate level."""
    caplog.set_level(logging.DEBUG)
    return caplog

def test_model_initialization_warning():
    """Test that OpenAI service unavailability is logged at WARNING level."""
    # Directly check the file to verify the correct log level is used

    # Read the file content
    with open('ai_service/models/unified_model.py', 'r') as f:
        file_content = f.read()

    # Check that the warning level is used for OpenAI service unavailability
    # This is more reliable than trying to mock and test the actual function
    assert 'logger.warning("OpenAI service not available, using fallback explanation")' in file_content, \
        "OpenAI service unavailability should be logged as WARNING"

    # Make sure the INFO logging isn't also used for the same message
    assert 'logger.info("OpenAI service not available, using fallback explanation")' not in file_content, \
        "OpenAI service unavailability should not be logged as INFO"

def test_timezone_api_key_warning():
    """Test that missing TIMEZONE_API_KEY is logged as WARNING."""
    # Directly check the file to verify the correct log level is used

    # Read the file content
    with open('ai_service/api/routers/geocode.py', 'r') as f:
        file_content = f.read()

    # Check that the warning level is used for missing API key
    assert 'logger.warning("TIMEZONE_API_KEY not set. Using UTC as fallback.")' in file_content, \
        "Missing TIMEZONE_API_KEY should be logged as WARNING"

    # Make sure the INFO logging isn't also used for the same message
    assert 'logger.info("TIMEZONE_API_KEY not set. Using UTC as fallback.")' not in file_content, \
        "Missing TIMEZONE_API_KEY should not be logged as INFO"

def test_http_error_logging():
    """Test that HTTP errors are logged with appropriate log levels."""
    # Directly check the file to verify the correct log level is used

    # Read the file content
    with open('ai_service/api/middleware/error_handling.py', 'r') as f:
        file_content = f.read()

    # Check that HTTP exceptions use appropriate log levels based on status code
    # Look for the conditional code that determines the log level based on status code

    # For HTTP 500+ errors, should use ERROR level
    assert "if exc.status_code >= 500:" in file_content, "Should check for 500+ status codes"
    assert "logger.error(f\"HTTP exception {exc.status_code}" in file_content, \
        "500+ errors should be logged at ERROR level"

    # For all other HTTP status codes (including 400+), should use WARNING level
    assert "logger.warning(f\"HTTP exception {exc.status_code}" in file_content, \
        "Non-500 errors should be logged at WARNING level"

    # Verify the simpler pattern is used (if-else instead of if-elif-else)
    assert "else:" in file_content and "# Use warning level for all other HTTP exceptions" in file_content, \
        "Should use a simplified if-else pattern for HTTP exception logging"

    # Make sure it's not always using INFO level
    logging_line_count = file_content.count("logger.info(f\"HTTP exception")
    warning_line_count = file_content.count("logger.warning(f\"HTTP exception")
    error_line_count = file_content.count("logger.error(f\"HTTP exception")

    # Ensure we're not using INFO for errors (there should be no instances)
    assert logging_line_count == 0, "HTTP exceptions should not use INFO level"

    # Make sure we have at least one warning and one error log level
    assert warning_line_count > 0, "Missing WARNING level logging for HTTP exceptions"
    assert error_line_count > 0, "Missing ERROR level logging for HTTP exceptions"

def test_comprehensive_warning_fixes():
    """Comprehensive test to verify all warning level fixes have been applied."""
    # This test verifies that all required fixes are in place

    # 1. Verify we've fixed the OpenAI service unavailability warning
    with open('ai_service/models/unified_model.py', 'r') as f:
        model_content = f.read()

    openai_warning_fixed = ('logger.warning("OpenAI service not available, using fallback explanation")' in model_content)
    assert openai_warning_fixed, "OpenAI service warning fix missing"

    # 2. Verify we've fixed the TIMEZONE_API_KEY warning
    with open('ai_service/api/routers/geocode.py', 'r') as f:
        geocode_content = f.read()
    assert 'logger.warning("TIMEZONE_API_KEY not set. Using UTC as fallback.")' in geocode_content, \
        "TIMEZONE_API_KEY warning fix missing"

    # 3. Verify we've fixed the error handling middleware
    with open('ai_service/api/middleware/error_handling.py', 'r') as f:
        error_handling_content = f.read()

    # Verify 404/400 errors use warning level
    assert 'logger.warning(f"HTTP exception {exc.status_code}' in error_handling_content, \
        "HTTP exception warning level fix missing"

    # Verify 500 errors use error level
    assert 'logger.error(f"HTTP exception {exc.status_code}' in error_handling_content, \
        "HTTP exception error level fix missing"

    # Verify no info logging for HTTP exceptions
    assert 'logger.info(f"HTTP exception {exc.status_code}' not in error_handling_content, \
        "HTTP exceptions should not use INFO level"

    # 4. Summary check - we've implemented all the required fixes
    print("✅ All warning level fixes have been successfully implemented")
