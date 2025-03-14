"""
Configuration and fixtures for the integration test suite.
"""

import os
import re
import time
import json
import logging
import pytest
from typing import Generator, Any
from playwright.sync_api import Page, Browser, BrowserContext, Route, Request, sync_playwright
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import our new route utilities
from tests.integration.route_utils import (
    extract_param_from_path,
    extract_params,
    debug_route_match,
    create_chart_id_matcher,
    create_questionnaire_answer_matcher,
    create_export_download_matcher,
)

# Get environment configuration
ENV = os.environ.get('TEST_ENV', 'dev')  # 'dev', 'test', or 'prod'
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:3000')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockElementHandle:
    def __init__(self, selector, page):
        self.selector = selector
        self.page = page

    def click(self):
        logger.info(f"Mock clicking on: {self.selector}")
        return True

    def fill(self, value):
        logger.info(f"Mock filling {self.selector} with value: {value}")
        return True

    def count(self):
        logger.info(f"Mock counting elements for selector: {self.selector}")
        return 1

    def text_content(self):
        logger.info(f"Mock getting text content for selector: {self.selector}")
        return "Mock text content"

    @property
    def first(self):
        logger.info(f"Mock getting first element for selector: {self.selector}")
        return self

    def content(self):
        logger.info(f"Mock getting content for element: {self.selector}")
        return "<html><body><div>Mock HTML Content</div></body></html>"

    def title(self):
        logger.info(f"Mock getting title")
        return "Mock Page Title"

    def screenshot(self, path=None):
        logger.info(f"Mock taking screenshot of element: {self.selector}")
        logger.info(f"Mock screenshot saved to: {path if path else 'not specified'}")
        return True

    def wait_for_element_state(self, state):
        logger.info(f"Mock waiting for element state: {state} for selector: {self.selector}")
        return True

class MockRequest:
    def __init__(self):
        self.headers = {}

    def get(self, url, **kwargs):
        logger.info(f"Mock GET request to: {url}, kwargs: {kwargs}")
        return MockResponse()

    def post(self, url, **kwargs):
        logger.info(f"Mock POST request to: {url}, kwargs: {kwargs}")
        return MockResponse()

class MockResponse:
    def __init__(self):
        self.status = 200
        self.ok = True
        self.headers = {"content-type": "application/json", "content-length": "100"}
        self.status_text = "OK"

    def json(self):
        return {"success": True, "message": "Mock response"}

    def text(self):
        return '{"success": true, "message": "Mock response"}'

class MockPage:
    def __init__(self):
        self.url = None
        self.content_str = "<html><body><h1>Mock Page</h1></body></html>"
        self.request = MockRequest()

    def goto(self, url):
        self.url = url
        logger.info(f"Mock navigating to: {url}")
        return True

    def locator(self, selector):
        logger.info(f"Mock locating element: {selector}")
        return MockElementHandle(selector, self)

    def get_by_role(self, role, **kwargs):
        logger.info(f"Mock getting element by role: {role}, kwargs: {kwargs}")
        return MockElementHandle(f"{role} {kwargs}", self)

    def get_by_text(self, text, **kwargs):
        logger.info(f"Mock getting element by text: {text}, kwargs: {kwargs}")
        return MockElementHandle(f"text='{text}'", self)

    def get_by_placeholder(self, placeholder, **kwargs):
        logger.info(f"Mock getting element by placeholder: {placeholder}, kwargs: {kwargs}")
        return MockElementHandle(f"placeholder='{placeholder}'", self)

    def fill(self, selector, value):
        logger.info(f"Mock filling {selector} with value: {value}")
        return True

    def wait_for_selector(self, selector, **kwargs):
        logger.info(f"Mock waiting for selector: {selector}, kwargs: {kwargs}")
        return MockElementHandle(selector, self)

    def wait_for_url(self, url, **kwargs):
        logger.info(f"Mock waiting for URL: {url}, kwargs: {kwargs}")
        return True

    def wait_for_function(self, fn, **kwargs):
        logger.info(f"Mock waiting for function, kwargs: {kwargs}")
        return True

    def wait_for_load_state(self, state):
        logger.info(f"Mock waiting for load state: {state}")
        return True

    def title(self):
        logger.info(f"Mock getting page title")
        return "Mock Page Title"

    def content(self):
        logger.info(f"Mock getting page content")
        return "<html><body><div>Mock HTML Content</div></body></html>"

    def screenshot(self, path=None):
        logger.info(f"Mock taking screenshot of page")
        logger.info(f"Mock screenshot saved to: {path if path else 'not specified'}")
        return True

    def route(self, url_pattern, handler):
        logger.info(f"Mock setting up route for pattern: {url_pattern}")
        return True

    def unroute(self, url_pattern, handler=None):
        logger.info(f"Mock removing route for pattern: {url_pattern}")
        return True

    def evaluate(self, expression):
        logger.info(f"Mock evaluating expression: {expression}")
        return {"result": "mock result"}

    def close(self):
        logger.info("Mock closing page")
        return True

    def set_default_timeout(self, timeout_ms):
        logger.info(f"Mock setting default timeout: {timeout_ms}ms")
        return True

    def set_extra_http_headers(self, headers):
        logger.info(f"Mock setting extra HTTP headers: {headers}")
        return True

class MockContext:
    def new_page(self):
        logger.info("Mock creating new page")
        return MockPage()

    def close(self):
        logger.info("Mock closing context")
        return True

    def set_default_navigation_timeout(self, timeout_ms):
        logger.info(f"Mock setting default navigation timeout: {timeout_ms}ms")
        return True

class MockBrowser:
    def new_context(self, **kwargs):
        logger.info(f"Mock creating new context with kwargs: {kwargs}")
        return MockContext()

@pytest.fixture(scope="function")
def browser() -> Generator:
    """
    Create a browser instance for testing.
    This will use a real browser via Playwright if available,
    otherwise it fails the test.
    """
    try:
        # First try to use a real browser
        from playwright.sync_api import sync_playwright
        playwright = sync_playwright().start()

        try:
            # Try to launch Chromium
            browser = playwright.chromium.launch(headless=True)
            yield browser
        except Exception as e:
            logger.error(f"Failed to launch real browser: {str(e)}")
            pytest.fail(f"Could not launch browser: {str(e)}")
        finally:
            playwright.stop()
    except Exception as e:
        logger.error(f"Failed to import or start Playwright: {str(e)}")
        pytest.fail(f"Failed to import or start Playwright: {str(e)}")

@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Return browser launch arguments based on environment."""
    # Common launch arguments
    args = {
        'headless': False,  # Run in headed mode to observe the tests
        'args': [
            '--disable-web-security',  # Allow cross-origin frames
            '--disable-site-isolation-trials',  # Enable interaction with cross-origin frames
            '--window-size=1280,720',
        ],
        'slow_mo': 100,  # Slow down execution by 100ms for visual inspection
    }

    # Add environment-specific settings
    if ENV == 'prod':
        # Production may need additional memory or rendering capabilities
        args['args'].extend([
            '--disable-dev-shm-usage',  # Use /tmp instead of /dev/shm
            '--no-sandbox',
        ])

    return args

@pytest.fixture(scope="function")
def browser_context_args(browser_context_args):
    """Configure the browser context."""
    return {
        **browser_context_args,
        'viewport': {'width': 1280, 'height': 720},
        'record_video_dir': 'test-videos',  # Record videos for later analysis
        'ignore_https_errors': True
    }

@pytest.fixture(scope="function")
def page(browser: Browser) -> Generator[Page, None, None]:
    """Creates a new page instance for each test."""
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        record_video_dir='test-videos'
    )

    page = context.new_page()

    # Set a longer timeout for navigation and actions
    page.set_default_timeout(60000)  # 60 seconds timeout

    # Initial navigation to the base URL to establish a session
    # Skip this to avoid duplicate navigation since tests usually start with navigation
    # page.goto(BASE_URL)

    # Configure environment-specific behaviors
    if ENV in ['test', 'prod']:
        # Enable browser console logging to capture WebGL errors
        page.on("console", lambda msg: print(f"BROWSER: {msg.text}"))

    yield page

    # Clean up
    context.close()

@pytest.fixture(scope="function")
def mock_api_requests(page: Page) -> Generator[None, None, None]:
    """Use real API endpoints for testing.

    This fixture ensures that real API endpoints are used and will fail
    the test if the API endpoints are not available.
    """
    # Check if APIs are available
    import requests
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            pytest.fail(f"API health check failed with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"API is not available: {str(e)}")

    # No request interception - using real APIs
    yield

@pytest.fixture(scope="function")
def enable_test_mode(page: Page) -> Generator[None, None, None]:
    """Enable test mode in the application for more reliable tests."""
    # Inject script to enable test mode
    page.evaluate("""() => {
        window.__testMode = true;
        window.__enableFancyEffects = true;

        // Store the original function for later cleanup
        if (typeof window.__originalConsoleWarn === 'undefined') {
            window.__originalConsoleWarn = console.warn;

            // Override console.warn to suppress WebGL warnings
            console.warn = (...args) => {
                if (args[0]?.includes?.('WebGL') ||
                    args[0]?.includes?.('RENDER') ||
                    args[0]?.includes?.('GL_') ||
                    args[0]?.includes?.('THREE.')) {
                    return; // Suppress known WebGL warnings
                }
                window.__originalConsoleWarn(...args); // Call original for other warnings
            };
        }

        // Add function to check for WebGL support
        if (typeof window.__hasWebGLSupport === 'undefined') {
            window.__hasWebGLSupport = () => {
                try {
                    const canvas = document.createElement('canvas');
                    return !!(
                        window.WebGLRenderingContext &&
                        (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
                    );
                } catch (e) {
                    return false;
                }
            };
        }

        console.log('Test mode enabled:', window.__testMode);
        console.log('WebGL support:', window.__hasWebGLSupport());
    }""")

    yield

@pytest.fixture(scope="function")
def critical_endpoints_mock(page: Page) -> Generator[None, None, None]:
    """Use real API endpoints for critical endpoints.

    This fixture ensures that real API endpoints are used and will fail
    the test if the API endpoints are not available.
    """
    # Check if APIs are available
    import requests
    try:
        # Test a few critical endpoints
        endpoints_to_test = [
            "http://localhost:8000/health",
            "http://localhost:8000/api/v1/geocode"
        ]

        for endpoint in endpoints_to_test:
            if endpoint.endswith("/geocode"):
                # POST endpoint
                response = requests.post(
                    endpoint,
                    json={"query": "London, UK"},
                    timeout=5
                )
            else:
                # GET endpoint
                response = requests.get(endpoint, timeout=5)

            if response.status_code not in [200, 201, 202]:
                pytest.fail(f"API endpoint {endpoint} check failed with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Critical API endpoints are not available: {str(e)}")

    # No request interception - using real APIs
    yield

@pytest.fixture(scope="function")
def production_environment(page: Page) -> Generator[None, None, None]:
    """Configure the page for production environment testing."""
    if ENV != 'prod':
        # Inject script to simulate production environment features
        page.evaluate("""() => {
            // Simulate production environment
            window.__visualizationMode = 'enhanced';
            window.__enableFancyEffects = true;
            window.__isProdEnvironment = true;

            // Add a style element to add production-specific styles
            const style = document.createElement('style');
            style.innerHTML = `
                /* Force show 3D elements */
                canvas, .threejs-container {
                    display: block !important;
                    visibility: visible !important;
                    opacity: 1 !important;
                }

                /* Show advanced UI controls */
                [data-testid="render-mode-select"],
                [data-testid="effects-toggle"],
                .controls-3d,
                .three-controls {
                    display: flex !important;
                }
            `;
            document.head.appendChild(style);

            console.log('Production environment simulation enabled');
        }""")

    yield
