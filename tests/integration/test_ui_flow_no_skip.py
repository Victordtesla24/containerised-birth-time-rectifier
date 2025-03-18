import pytest
from playwright.sync_api import Page, expect
import time
import logging
import os
import shutil
from pathlib import Path
import json
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get base URL from environment or use default
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:3000')
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL', 'http://localhost:9000')
AI_SERVICE_URL = os.environ.get('AI_SERVICE_URL', 'http://localhost:8000')

# Test data
TEST_DATA = {
    'birthDate': '1990-01-15',
    'birthTime': '14:30',
    'birthLocation': 'New York, USA'
}

@pytest.fixture(scope='function', autouse=True)
def setup_browser_context(page: Page):
    """Configure the browser context before each test."""
    # Set the base URL
    page.context.set_default_navigation_timeout(60000)  # 60 seconds

    # Verify all services are running
    try:
        # Check frontend
        frontend_response = requests.get(f"{BASE_URL}", timeout=5)
        assert frontend_response.status_code == 200, "Frontend service is not running"

        # Check API gateway
        api_gateway_response = requests.get(f"{API_GATEWAY_URL}/health", timeout=5)
        assert api_gateway_response.status_code == 200, "API gateway service is not running"

        # Check AI service
        ai_service_response = requests.get(f"{AI_SERVICE_URL}/health", timeout=5)
        assert ai_service_response.status_code == 200, "AI service is not running"

        logger.info("All services are running and healthy")
    except (requests.RequestException, AssertionError) as e:
        pytest.fail(f"Service health check failed: {str(e)}")

    return page

def test_birth_details_form_submission(page: Page):
    """Test the full birth details form submission flow with proper error handling."""
    logger.info("Starting birth details form submission test")

    # Navigate to the application
    page.goto(f'{BASE_URL}/')
    logger.info("Navigated to application")

    # Look for and click the "Get Started" button first
    get_started_selectors = [
        'button#get-started-button',
        'button[data-testid="get-started-button"]',
        'button:has-text("Get Started")',
        '.cosmic-button.primary',
        'a:has-text("Get Started")',
        'a.get-started-link'
    ]

    get_started_found = False
    for selector in get_started_selectors:
        if page.locator(selector).count() > 0:
            button = page.locator(selector).first
            get_started_found = True
            logger.info(f"Found Get Started button with selector: {selector}")
            # Take screenshot before clicking
            page.screenshot(path="/tmp/before_get_started.png")
            # Click the button
            button.click()
            logger.info("Clicked Get Started button")
            # Wait for navigation to complete
            page.wait_for_load_state("networkidle")
            break

    assert get_started_found, "Get Started button not found on homepage"
    logger.info("Navigated to form page after clicking Get Started")

    # Take screenshot of current state after navigation
    page.screenshot(path='/tmp/after_get_started.png')

    # Look for the birth details form
    form_selectors = [
        'form.birth-details-form',
        'form#birth-details-form',
        'form[data-testid="birth-details-form"]',
        'form',
        '.form',
        'form:has(input[type="date"])',
        'form:has(input[name="birthDate"])'
    ]

    # First check if there are ANY forms at all
    all_forms = page.locator('form')
    form_count = all_forms.count()
    logger.info(f"Found {form_count} forms on the page")

    if form_count > 0:
        # Log information about each form
        for i in range(form_count):
            form = all_forms.nth(i)
            try:
                form_id = form.get_attribute('id') or 'no-id'
                form_class = form.get_attribute('class') or 'no-class'
                form_action = form.get_attribute('action') or 'no-action'

                # Check for inputs inside this form
                inputs = form.locator('input')
                input_count = inputs.count()
                logger.info(f"Form {i+1}: id={form_id}, class={form_class}, action={form_action}, inputs={input_count}")
            except Exception as e:
                logger.error(f"Error inspecting form {i+1}: {str(e)}")

    # Also look for specific input elements
    input_selectors = [
        'input[type="date"]',
        'input[name="birthDate"]',
        'input[placeholder*="date"]',
        'input[type="time"]',
        'input[name="birthTime"]'
    ]

    for selector in input_selectors:
        input_count = page.locator(selector).count()
        if input_count > 0:
            logger.info(f"Found {input_count} inputs matching {selector}")

    form_found = False
    for selector in form_selectors:
        if page.locator(selector).count() > 0:
            form = page.locator(selector).first
            form_found = True
            logger.info(f"Found form with selector: {selector}")
            break

    # Take screenshot of current state
    page.screenshot(path='/tmp/form-state.png')

    # Assert form is found - don't continue with fallbacks if no form is found
    assert form_found, "Form element not found on page. UI test cannot proceed without form."

    # Fill out the form with valid data
    # Try different selectors for date input
    date_selectors = [
        'input[name="birthDate"]',
        'input[type="date"]',
        'input[data-testid="birth-date"]'
    ]

    date_filled = False
    for selector in date_selectors:
        if page.locator(selector).count() > 0:
            page.fill(selector, TEST_DATA['birthDate'])
            logger.info(f"Filled date with selector: {selector}")
            date_filled = True
            break

    assert date_filled, "Date input field not found"

    # Try different selectors for time input
    time_selectors = [
        'input[name="birthTime"]',
        'input[type="time"]',
        'input[data-testid="birth-time"]'
    ]

    time_filled = False
    for selector in time_selectors:
        if page.locator(selector).count() > 0:
            page.fill(selector, TEST_DATA['birthTime'])
            logger.info(f"Filled time with selector: {selector}")
            time_filled = True
            break

    assert time_filled, "Time input field not found"

    # Try different selectors for location input
    location_selectors = [
        'input[name="birthLocation"]',
        'input[placeholder*="location" i]',
        'input[data-testid="birth-location"]'
    ]

    location_filled = False
    for selector in location_selectors:
        if page.locator(selector).count() > 0:
            page.fill(selector, TEST_DATA['birthLocation'])
            logger.info(f"Filled location with selector: {selector}")
            # Wait for location suggestions to appear
            try:
                # Wait for the suggestion dropdown to appear
                time.sleep(1)  # Give time for suggestion API to respond
                suggestion_selectors = [
                    '.location-suggestions li',
                    '.autocomplete-suggestions div',
                    '[data-testid="location-suggestion"]'
                ]

                for suggestion_selector in suggestion_selectors:
                    if page.locator(suggestion_selector).count() > 0:
                        # Click the first suggestion
                        page.locator(suggestion_selector).first.click()
                        logger.info(f"Selected location suggestion with selector: {suggestion_selector}")
                        break
            except Exception as e:
                logger.error(f"Location suggestion selection failed: {str(e)}")
            location_filled = True
            break

    assert location_filled, "Location input field not found"

    # Find and click the submit button
    submit_selectors = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Generate Chart")',
        'button:has-text("Submit")',
        'button.primary-button',
        'button.submit-button'
    ]

    submit_button_found = False
    for selector in submit_selectors:
        if page.locator(selector).count() > 0:
            submit_button = page.locator(selector).first
            submit_button_found = True
            logger.info(f"Found submit button with selector: {selector}")
            # Save before submission
            page.screenshot(path="/tmp/before_submit.png")
            # Click the submit button
            submit_button.click()
            logger.info("Clicked submit button")
            break

    assert submit_button_found, "Submit button not found"

    # Wait for chart page to load
    chart_page_selectors = [
        '.chart-container',
        '.birth-chart',
        'canvas.chart-canvas',
        '[data-testid="chart-page"]',
        'h1:has-text("Birth Chart")',
        'h2:has-text("Birth Chart")',
        'svg' # Generic chart indicator
    ]

    chart_found = False
    for selector in chart_page_selectors:
        try:
            if page.wait_for_selector(selector, timeout=10000, state='visible') is not None:
                chart_found = True
                logger.info(f"Chart page loaded with selector: {selector}")
                break
        except Exception as e:
            logger.error(f"Selector {selector} not found: {str(e)}")

    # Take a screenshot if chart not found
    if not chart_found:
        page.screenshot(path="/tmp/chart_not_found.png")

    assert chart_found, "Chart not found after form submission"

    # Verify birth chart components are present
    chart_component_selectors = [
        # Chart visualization
        '.chart-visualization',
        'canvas.chart-canvas',
        '[data-testid="chart-visualization"]',
        'svg', # Generic chart visualization

        # Planet positions or details table
        '.planet-positions',
        'table.positions-table',
        '[data-testid="planet-positions"]',

        # Chart details/info section
        '.chart-details',
        '.chart-info',
        '[data-testid="chart-details"]'
    ]

    components_found = 0
    for selector in chart_component_selectors:
        if page.locator(selector).count() > 0:
            components_found += 1
            logger.info(f"Found chart component with selector: {selector}")

    assert components_found > 0, "No chart components found"
    logger.info(f"Found {components_found} chart components")

    # Test interaction with chart (click/hover on elements)
    interaction_selectors = [
        '.chart-visualization .planet',
        '.interactive-element',
        '[data-testid="interactive-chart"] *',
        'canvas.chart-canvas',
        'svg'
    ]

    for selector in interaction_selectors:
        if page.locator(selector).count() > 0:
            # Try clicking or hovering
            try:
                el = page.locator(selector).first
                # Hover first to see if tooltips appear
                el.hover()
                time.sleep(0.5)  # Brief wait for tooltip
                # Then click to test interaction
                el.click()
                logger.info(f"Successfully interacted with chart element: {selector}")
                break
            except Exception as e:
                logger.error(f"Error interacting with chart element {selector}: {str(e)}")

    logger.info("Birth details form test completed")

def test_advanced_visualizations(page: Page):
    """Test advanced chart visualizations like 3D view and interactive elements."""
    logger.info("Starting advanced visualizations test")

    # First create a chart using the API directly to ensure we have a valid chart
    chart_data = {
        "birth_details": {
            "birth_date": TEST_DATA["birthDate"],
            "birth_time": TEST_DATA["birthTime"],
            "location": TEST_DATA["birthLocation"],
            "latitude": 40.7128,  # New York
            "longitude": -74.006,
            "timezone": "America/New_York"
        },
        "options": {
            "house_system": "W"  # Use Whole Sign houses for more reliable calculations
        }
    }

    try:
        # Make a direct call to the API gateway chart generation endpoint
        response = requests.post(
            f"{API_GATEWAY_URL}/api/v1/chart/generate",
            headers={"Content-Type": "application/json"},
            json=chart_data,
            timeout=10
        )

        assert response.status_code == 200, f"Failed to create chart: {response.status_code} {response.text}"

        chart_response = response.json()
        chart_id = chart_response.get("chart_id")

        assert chart_id is not None, "No chart_id in API response"
        logger.info(f"Successfully created chart with ID: {chart_id}")

        # Navigate directly to this chart
        page.goto(f"{BASE_URL}/chart/{chart_id}", timeout=30000)
        logger.info(f"Navigated to chart page: {BASE_URL}/chart/{chart_id}")

    except (requests.RequestException, AssertionError) as e:
        pytest.fail(f"Failed to create chart using API: {str(e)}")

    # Verify chart visualization elements are present
    visualization_selectors = [
        # Chart visualization
        '.chart-visualization',
        'canvas.chart-canvas',
        '[data-testid="chart-visualization"]',
        'svg',  # Generic chart visualization

        # Tabs or switches for different views
        '.chart-tabs',
        '.view-switcher',
        '[data-testid="view-switcher"]',
        'button:has-text("3D View")',
        'button:has-text("Interactive")',

        # Other interactive elements
        '.chart-controls',
        '.interactive-controls',
        '[data-testid="chart-controls"]'
    ]

    visualization_elements_found = 0
    found_selectors = []

    for selector in visualization_selectors:
        elements = page.locator(selector)
        count = elements.count()
        if count > 0:
            visualization_elements_found += count
            found_selectors.append(selector)
            logger.info(f"Found {count} visualization elements with selector: {selector}")

    assert visualization_elements_found > 0, "No visualization elements found"

    # Click on a visualization element to activate it
    if len(found_selectors) > 0:
        selector = found_selectors[0]
        try:
            page.locator(selector).first.click()
            logger.info(f"Clicked visualization element: {selector}")
            page.screenshot(path="/tmp/visualization_clicked.png")
        except Exception as e:
            logger.error(f"Error clicking visualization element: {str(e)}")

    # Look for 3D visualization or interactive elements
    interactive_selectors = [
        # 3D elements
        'canvas',
        '.chart-3d',
        '#chart3d-container',
        '[data-testid="3d-chart"]',

        # Interactive controls
        '.zoom-controls',
        '.rotation-controls',
        '.planet-filter',
        '.aspect-filter',
        '[data-testid="interactive-controls"]'
    ]

    interactive_elements_found = 0
    for selector in interactive_selectors:
        count = page.locator(selector).count()
        if count > 0:
            interactive_elements_found += count
            logger.info(f"Found {count} interactive elements with selector: {selector}")

            # Try to interact with the elements
            try:
                el = page.locator(selector).first
                el.hover()
                el.click()
                logger.info(f"Successfully interacted with element: {selector}")
            except Exception as e:
                logger.error(f"Error interacting with element {selector}: {str(e)}")

    # Test chart controls if available
    control_selectors = [
        'button:has-text("Zoom In")',
        'button:has-text("Zoom Out")',
        'button:has-text("Rotate")',
        'button:has-text("Filter")',
        '.chart-option',
        '[data-testid="chart-option"]'
    ]

    for selector in control_selectors:
        count = page.locator(selector).count()
        if count > 0:
            logger.info(f"Found {count} control elements with selector: {selector}")

            try:
                el = page.locator(selector).first
                el.click()
                logger.info(f"Successfully clicked control: {selector}")
                time.sleep(0.5)  # Allow time for any animations or changes
            except Exception as e:
                logger.error(f"Error clicking control {selector}: {str(e)}")

    logger.info("Advanced visualizations test completed")
