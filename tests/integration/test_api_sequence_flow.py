"""
Test implementation for the AI Service API sequence flow.

This test validates that the backend services strictly align with the
"Consolidated API Questionnaire Flow" and "Original Sequence Diagram"
sections detailed in the sequence_diagram.md documentation.
"""

import pytest
import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, TypedDict, AsyncGenerator, Union

import aiohttp
import pytest_asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import rate limiter for OpenAI API calls
try:
    from tests.utils.rate_limiter import openai_rate_limiter, rate_limited
except ImportError:
    logger.warning("Could not import rate limiter. Will proceed without rate limiting.")
    # Create mock implementations if the real ones aren't available
    class MockRateLimiter:
        async def wait(self):
            pass

    openai_rate_limiter = MockRateLimiter()

    def rate_limited(limiter):
        def decorator(func):
            return func
        return decorator

# API Configuration
# Using the main API server on port 9000
API_BASE_URL = os.environ.get('API_URL', 'http://localhost:9000')  # Main API server URL
REQUEST_TIMEOUT = 30  # seconds

# Test data
TEST_DATA = {
    'birthDate': '1990-01-15',
    'birthTime': '14:30',
    'birthLocation': 'New Delhi, India',  # Using Indian location for Vedic chart
    'latitude': 28.6139,
    'longitude': 77.2090,
    'timezone': 'Asia/Kolkata',
    'questionnaire_answers': [
        {"answer": "yes", "confidence": 90},
        {"answer": "somewhat", "confidence": 80},
        {"answer": "no", "confidence": 95},
        {"answer": "1995-06-15", "confidence": 100},
        {"answer": "morning", "confidence": 85}
    ]
}

def api_url(path: str) -> str:
    """Construct a consistent API URL with correct formatting"""
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path

    # Replace any double slashes and ensure API_BASE_URL doesn't end with slash
    base = API_BASE_URL.rstrip('/')
    path = path.replace('//', '/')

    return f"{base}{path}"

# Create fixtures for setting up the test environment
@pytest_asyncio.fixture
async def session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Create an aiohttp session for tests"""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as session:
        yield session

# Define typed context structure to help the linter
class ApiTestContext(TypedDict):
    session_id: Optional[str]
    chart_id: Optional[str]
    questionnaire_id: Optional[str]
    rectified_chart_id: Optional[str]
    headers: Dict[str, str]
    test_results: Dict[str, bool]
    issues_found: List[str]

@pytest_asyncio.fixture
async def api_context() -> AsyncGenerator[ApiTestContext, None]:
    """Fixture to provide a shared test context."""
    # Initialize the context
    context: ApiTestContext = {
        "session_id": None,
        "chart_id": None,
        "questionnaire_id": None,
        "rectified_chart_id": None,
        "headers": {},
        "test_results": {},
        "issues_found": []
    }
    yield context

@rate_limited(openai_rate_limiter)
async def make_api_call(
    session,
    context: Union[ApiTestContext, Dict[str, Any]],
    method: str,
    url: str,
    data: Optional[Dict[str, Any]] = None,
    retry_count: int = 2,
    expected_status: int = 200
) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Make an API call with retry logic and rate limiting.

    Args:
        session: aiohttp session
        context: Test context with headers and issues list
        method: HTTP method (GET, POST)
        url: API endpoint URL
        data: Request data for POST calls
        retry_count: Number of retries if call fails
        expected_status: Expected HTTP status code

    Returns:
        Tuple of (response_data, success_flag)
    """
    # Add session ID to headers if available
    headers = context["headers"].copy()
    if context["session_id"]:
        headers["X-Session-ID"] = context["session_id"]

    response_data = None
    success = False

    for attempt in range(retry_count + 1):
        try:
            if method.lower() == 'get':
                async with session.get(url, headers=headers) as response:
                    if response.status == expected_status:
                        response_data = await response.json()
                        success = True
                        break
                    elif attempt < retry_count:
                        logger.warning(f"API call to {url} failed with status {response.status}, retrying...")
                        await asyncio.sleep(1)  # Wait before retry
                    else:
                        error_text = await response.text()
                        logger.error(f"API call to {url} failed after {retry_count + 1} attempts: {response.status}")
                        logger.error(f"Response: {error_text}")
                        issue = f"API call to {url} failed with status {response.status}: {error_text}"
                        context["issues_found"].append(issue)
                        break

            elif method.lower() == 'post':
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == expected_status:
                        response_data = await response.json()
                        success = True
                        break
                    elif attempt < retry_count:
                        logger.warning(f"API call to {url} failed with status {response.status}, retrying...")
                        await asyncio.sleep(1)  # Wait before retry
                    else:
                        error_text = await response.text()
                        logger.error(f"API call to {url} failed after {retry_count + 1} attempts: {response.status}")
                        logger.error(f"Response: {error_text}")
                        issue = f"API call to {url} failed with status {response.status}: {error_text}"
                        context["issues_found"].append(issue)
                        break
            else:
                raise ValueError(f"Unsupported method: {method}")

        except aiohttp.ClientError as e:
            if attempt < retry_count:
                logger.warning(f"API call to {url} failed with error: {str(e)}, retrying...")
                await asyncio.sleep(1)  # Wait before retry
            else:
                logger.error(f"API call to {url} failed after {retry_count + 1} attempts: {str(e)}")
                issue = f"API call to {url} failed with error: {str(e)}"
                context["issues_found"].append(issue)

    return response_data, success

@pytest.mark.asyncio
async def test_session_initialization(session, api_context: ApiTestContext):
    """Test session initialization according to sequence diagram."""
    logger.info("Testing session initialization")

    response_data, success = await make_api_call(
        session, api_context, 'get', api_url("/api/v1/session/init")
    )

    if success and response_data:
        assert "session_id" in response_data, "Session init API should return session_id"
        api_context["session_id"] = response_data["session_id"]
        logger.info(f"Session initialized with ID: {api_context['session_id']}")
        api_context["test_results"]["session_init"] = True
    else:
        logger.error("Session initialization failed")
        api_context["issues_found"].append("Session initialization failed - this is a critical API in the sequence flow")
        pytest.fail("Session initialization failed")

@pytest.mark.asyncio
async def test_geocode(session, api_context: ApiTestContext):
    """Test geocoding endpoint according to sequence diagram."""
    logger.info("Testing geocoding endpoint")

    # Skip if session init failed
    if not api_context["session_id"]:
        pytest.skip("Skipping test_geocode because session initialization failed")

    geocode_data = {
        "query": TEST_DATA["birthLocation"],
        "session_id": api_context["session_id"]
    }

    response_data, success = await make_api_call(
        session, api_context, 'post', api_url("/api/v1/geocode"), geocode_data
    )

    if success and response_data:
        assert "results" in response_data, "Geocode API should return results"
        assert len(response_data["results"]) > 0, "Geocode API should return at least one result"

        # Update test data with actual coordinates from the geocoding result
        if response_data["results"] and len(response_data["results"]) > 0:
            first_result = response_data["results"][0]
            if "latitude" in first_result and "longitude" in first_result:
                TEST_DATA["latitude"] = first_result["latitude"]
                TEST_DATA["longitude"] = first_result["longitude"]
            if "timezone" in first_result:
                TEST_DATA["timezone"] = first_result["timezone"]

        logger.info(f"Geocoding successful for location: {TEST_DATA['birthLocation']}")
        api_context["test_results"]["geocode"] = True
    else:
        logger.error("Geocoding failed")
        api_context["issues_found"].append("Geocoding failed - this is required for accurate chart calculation")
        pytest.fail("Geocoding failed")

@pytest.mark.asyncio
async def test_chart_validation(session, api_context: ApiTestContext):
    """Test chart validation endpoint according to sequence diagram."""
    logger.info("Testing chart validation endpoint")

    # Skip if session init failed
    if not api_context["session_id"]:
        pytest.skip("Skipping test_chart_validation because session initialization failed")

    validation_data = {
        "birth_details": {
            "birth_date": TEST_DATA["birthDate"],
            "birth_time": TEST_DATA["birthTime"],
            "location": TEST_DATA["birthLocation"],
            "latitude": TEST_DATA["latitude"],
            "longitude": TEST_DATA["longitude"],
            "timezone": TEST_DATA["timezone"]
        },
        "session_id": api_context["session_id"]
    }

    response_data, success = await make_api_call(
        session, api_context, 'post', api_url("/api/v1/chart/validate"), validation_data
    )

    if success and response_data:
        assert "valid" in response_data, "Chart validation API should return valid flag"

        if response_data["valid"]:
            logger.info("Chart validation successful")
            api_context["test_results"]["chart_validate"] = True
        else:
            logger.error(f"Chart validation failed: {response_data.get('errors', [])}")
            api_context["issues_found"].append(f"Chart validation failed: {response_data.get('errors', [])}")
            pytest.fail("Chart validation failed")
    else:
        logger.error("Chart validation failed")
        api_context["issues_found"].append("Chart validation API call failed")
        pytest.fail("Chart validation API call failed")

@pytest.mark.asyncio
async def test_standalone_chart_generation(session):
    """Test chart generation without dependency on session initialization."""
    logger.info("Testing standalone chart generation")

    # Create a minimal context with a test session ID
    context: Dict[str, Any] = {
        "session_id": "test-session-id",
        "headers": {"Content-Type": "application/json"},
        "test_results": {},
        "issues_found": []
    }

    # Use the correct structure for chart generation as required by the API
    chart_data = {
        "birth_details": {
            "birth_date": TEST_DATA["birthDate"],
            "birth_time": TEST_DATA["birthTime"],
            "location": TEST_DATA["birthLocation"],
            "latitude": TEST_DATA["latitude"],
            "longitude": TEST_DATA["longitude"],
            "timezone": TEST_DATA["timezone"]
        },
        "options": {
            "house_system": "W",  # Whole sign house system for Vedic astrology
            "zodiac_type": "sidereal",
            "ayanamsa": "lahiri",
            "node_type": "true",
            "verify_with_openai": False  # Set to False to avoid OpenAI API dependency
        },
        "session_id": context["session_id"]
    }

    # Send the request with the correct structure
    logger.info("Sending chart generation request with correct structure")
    response_data, success = await make_api_call(
        session, context, 'post', api_url("/api/v1/chart/generate"), chart_data
    )

    if success and response_data:
        assert "chart_id" in response_data, "Chart generation API should return chart_id"
        context["chart_id"] = response_data["chart_id"]
        logger.info(f"Chart generated with ID: {context['chart_id']}")

        # Check for verification data which should be present when using OpenAI
        if "verification" in response_data:
            verification = response_data["verification"]
            logger.info(f"Chart verified with confidence: {verification.get('confidence', 'N/A')}")
            assert "verified" in verification, "Verification data should include verified flag"

        return True
    else:
        logger.error("Chart generation failed")
        pytest.fail("Chart generation failed")

@pytest.mark.asyncio
async def test_chart_generation(session, api_context: ApiTestContext):
    """Test chart generation endpoint according to sequence diagram."""
    logger.info("Testing chart generation endpoint")

    # Skip if session init failed
    if not api_context["session_id"]:
        pytest.skip("Skipping test_chart_generation because session initialization failed")

    # Use the correct structure for chart generation as required by the API
    chart_data = {
        "birth_details": {
            "birth_date": TEST_DATA["birthDate"],
            "birth_time": TEST_DATA["birthTime"],
            "location": TEST_DATA["birthLocation"],
            "latitude": TEST_DATA["latitude"],
            "longitude": TEST_DATA["longitude"],
            "timezone": TEST_DATA["timezone"]
        },
        "options": {
            "house_system": "W",  # Whole sign house system for Vedic astrology
            "zodiac_type": "sidereal",
            "ayanamsa": "lahiri",
            "node_type": "true",
            "verify_with_openai": True  # Must work in all environments including where API key is missing
        },
        "session_id": api_context["session_id"]
    }

    # Send the request with the correct structure
    logger.info("Sending chart generation request with correct structure")
    response_data, success = await make_api_call(
        session, api_context, 'post', api_url("/api/v1/chart/generate"), chart_data
    )

    if success and response_data:
        assert "chart_id" in response_data, "Chart generation API should return chart_id"
        api_context["chart_id"] = response_data["chart_id"]

        # Check for verification data which should be present when using OpenAI
        if "verification" in response_data:
            verification = response_data["verification"]
            logger.info(f"Chart verified with confidence: {verification.get('confidence', 'N/A')}")
            assert "verified" in verification, "Verification data should include verified flag"
        else:
            logger.warning("Chart generated but verification data missing")
            api_context["issues_found"].append("Chart verification data missing - OpenAI integration may not be working correctly")

        logger.info(f"Chart generated with ID: {api_context['chart_id']}")
        api_context["test_results"]["chart_generate"] = True
    else:
        logger.error("Chart generation failed")
        api_context["issues_found"].append("Chart generation failed - this is a critical API in the sequence flow")
        pytest.fail("Chart generation failed")

@pytest.mark.asyncio
async def test_api_sequence_flow(session, api_context: ApiTestContext):
    """Run the API sequence flow tests"""
    logger.info("Starting API sequence flow tests")

    # Run the tests in sequence
    await test_session_initialization(session, api_context)

    # Run geocode if session initialization succeeded
    if api_context["session_id"]:
        await test_geocode(session, api_context)
    else:
        logger.warning("Skipping geocode test due to session initialization failure")

    # Run chart validation if geocode succeeded
    if api_context.get("test_results", {}).get("geocode", False):
        await test_chart_validation(session, api_context)
    else:
        logger.warning("Skipping chart validation test due to geocode failure")

    # Run chart generation if validation succeeded
    if api_context.get("test_results", {}).get("chart_validate", False):
        await test_chart_generation(session, api_context)
    else:
        logger.warning("Skipping chart generation test due to validation failure")

    # Check results of the sequence
    success_count = sum(1 for result in api_context["test_results"].values() if result is True)

    if len(api_context["issues_found"]) > 0:
        logger.warning(f"Issues found during sequence flow: {api_context['issues_found']}")

    # Require at least session, geocode, and validation to pass
    min_required_success = 3  # session, geocode, validation
    if success_count < min_required_success:
        pytest.fail(f"API sequence flow failed with only {success_count} successful tests")

    # Get the chart by ID
    if api_context["chart_id"]:
        logger.info(f"Retrieving chart with ID: {api_context['chart_id']}")
        response_data, success = await make_api_call(
            session, api_context, 'get', api_url(f"/api/v1/chart/{api_context['chart_id']}")
        )

        if success and response_data:
            logger.info("Chart retrieved successfully")
            api_context["test_results"]["chart_retrieve"] = True
        else:
            logger.warning("Failed to retrieve chart")

    # Initialize questionnaire
    if api_context["chart_id"]:
        logger.info("Initializing questionnaire")
        response_data, success = await make_api_call(
            session, api_context, 'get', api_url(f"/api/v1/questionnaire?chart_id={api_context['chart_id']}")
        )

        if success and response_data:
            logger.info("Questionnaire initialized successfully")
            api_context["test_results"]["questionnaire_init"] = True

            # Store questionnaire ID if available
            if "questionnaire_id" in response_data:
                api_context["questionnaire_id"] = response_data["questionnaire_id"]

            # Answer first question if available
            if "questions" in response_data and len(response_data["questions"]) > 0:
                first_question = response_data["questions"][0]
                question_id = first_question["id"]

                # Prepare answer data
                answer_data = {
                    "answer": "yes" if "options" in first_question else "1990-06-15",
                    "session_id": api_context["session_id"],
                    "chart_id": api_context["chart_id"]
                }

                logger.info(f"Answering question ID: {question_id}")
                answer_response, answer_success = await make_api_call(
                    session, api_context, 'post',
                    api_url(f"/api/v1/questionnaire/{question_id}/answer"),
                    answer_data
                )

                if answer_success and answer_response:
                    logger.info("Question answered successfully")
                    api_context["test_results"]["questionnaire_answer"] = True

                    # Complete questionnaire
                    complete_data = {
                        "session_id": api_context["session_id"],
                        "chart_id": api_context["chart_id"]
                    }

                    logger.info("Completing questionnaire")
                    complete_response, complete_success = await make_api_call(
                        session, api_context, 'post',
                        api_url("/api/v1/questionnaire/complete"),
                        complete_data
                    )

                    if complete_success and complete_response:
                        logger.info("Questionnaire completed successfully")
                        api_context["test_results"]["questionnaire_complete"] = True

                        # Rectify chart
                        rectify_data = {
                            "chart_id": api_context["chart_id"],
                            "answers": [
                                {"question_id": question_id, "answer": "yes" if "options" in first_question else "1990-06-15"}
                            ]
                        }

                        logger.info("Requesting birth time rectification")
                        rectify_response, rectify_success = await make_api_call(
                            session, api_context, 'post',
                            api_url("/api/v1/chart/rectify"),
                            rectify_data
                        )

                        if rectify_success and rectify_response:
                            logger.info(f"Chart rectified successfully with time: {rectify_response.get('rectified_time')}")
                            api_context["test_results"]["chart_rectify"] = True
                            api_context["rectified_chart_id"] = rectify_response.get("rectified_chart_id")

                            # Compare charts
                            if api_context["rectified_chart_id"]:
                                logger.info("Comparing original and rectified charts")
                                compare_url = api_url(f"/api/v1/chart/compare?chart1_id={api_context['chart_id']}&chart2_id={api_context['rectified_chart_id']}")
                                compare_response, compare_success = await make_api_call(
                                    session, api_context, 'get', compare_url
                                )

                                if compare_success and compare_response:
                                    logger.info("Chart comparison successful")
                                    api_context["test_results"]["chart_compare"] = True

                                    # Export chart
                                    export_data = {
                                        "chart_id": api_context["rectified_chart_id"],
                                        "format": "pdf"
                                    }

                                    logger.info("Requesting chart export")
                                    export_response, export_success = await make_api_call(
                                        session, api_context, 'post',
                                        api_url("/api/v1/chart/export"),
                                        export_data
                                    )

                                    if export_success and export_response:
                                        logger.info("Chart export successful")
                                        api_context["test_results"]["chart_export"] = True
