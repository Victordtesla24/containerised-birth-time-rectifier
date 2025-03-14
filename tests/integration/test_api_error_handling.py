"""
Tests specifically focused on validating API error handling for critical endpoints.

This test ensures that our API error handling works correctly, specifically for
the critical endpoints that were returning 500 errors but tests were still passing:
- /api/chart/{id}
- /api/questionnaire/{id}/answer
- /api/export/{id}/download
"""

import pytest
import os
import logging
from playwright.sync_api import Page

from tests.integration.error_assertion_utils import assert_api_response, APIResponseValidator
from tests.integration.endpoints_utils import (
    check_chart_endpoint,
    check_questionnaire_answer_endpoint,
    check_export_download_endpoint
)

logger = logging.getLogger(__name__)

@pytest.mark.usefixtures("critical_endpoints_mock")
def test_critical_endpoints_validation(page: Page):
    """
    Test that critical endpoints return valid responses and not 500 errors.

    This test verifies that the following critical endpoints work correctly:
    - /api/chart/{id}
    - /api/questionnaire/{id}/answer}
    - /api/export/{id}/download
    """
    logger.info("Starting API error handling test")

    # Get BASE_URL from environment variables or use default
    base_url = os.environ.get('BASE_URL', 'http://localhost:3000')

    # Navigate to test page to ensure we have a valid session
    page.goto(f"{base_url}/test-form")
    assert '/test-form' in page.url, "Failed to navigate to test form page"

    # Test all critical endpoints using our utility functions
    check_chart_endpoint(page, base_url)
    check_questionnaire_answer_endpoint(page, base_url)
    check_export_download_endpoint(page, base_url)

    # All tests passed
    logger.info("All critical API endpoints validated successfully")

def test_utility_assert_api_response():
    """
    Test our assert_api_response utility function.

    This test verifies that:
    1. The utility correctly validates 200 responses as ok
    2. The utility correctly detects and raises AssertionError for 500 responses

    Note: This test intentionally generates an error log message during the negative test case,
    but this is expected behavior and not an actual test failure.
    """
    validator = APIResponseValidator()

    # Test with a mock response (as dict)
    mock_response = {
        "status_code": 200,
        "url": "/api/chart/123",
        "data": {"chart_id": "123"}
    }

    # Should return True for valid response
    assert assert_api_response(mock_response) is True, "Assertion failed for valid response"

    # Should raise AssertionError for 500 error (wrapped in pytest.raises to validate)
    mock_error_response = {
        "status_code": 500,
        "url": "/api/chart/123",
        "data": {"error": "Internal Server Error"}
    }

    # Test intentional 500 error detection - we expect 200 but get 500
    # Use test_mode=True to indicate this is an intentional error test
    with pytest.raises(AssertionError):
        assert_api_response(mock_error_response, expected_status=200, test_mode=True)

    logger.info("assert_api_response utility tested successfully")
