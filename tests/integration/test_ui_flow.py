import pytest
import requests
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Service URLs
FRONTEND_URL = "http://localhost:3000"

# Set UI tests to run by default
should_run_ui_tests = os.environ.get("SKIP_UI_TESTS", "false").lower() != "true"

# Test data
TEST_DATA = {
    "date": "1985-10-24",  # YYYY-MM-DD format
    "time": "14:30",       # 24-hour format
    "birthPlace": "Pune, Maharashtra",
    "expected_results": {
        "latitude": 18.5204,
        "longitude": 73.8567,
        "timezone": "Asia/Kolkata"
    }
}

@pytest.fixture(scope="module")
def selenium_driver():
    """Setup and teardown for Selenium WebDriver"""
    if os.environ.get("SKIP_SELENIUM", "false").lower() == "true":
        pytest.skip("Selenium tests skipped")

    try:
        # Setup Chrome options
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # Create driver
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)

        yield driver
    finally:
        if 'driver' in locals():
            driver.quit()

def check_services_running():
    """Check if required services are running"""
    try:
        # Check frontend
        response = requests.get(FRONTEND_URL, timeout=5)
        return response.status_code == 200
    except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
        return False

def check_full_ui_available():
    """More thorough check if UI elements are interactive"""
    try:
        # If the service check already failed, don't even try this check
        if not check_services_running():
            return False

        # Setup a quick driver just for checking
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(3)

        try:
            # Try to access the site
            driver.get(FRONTEND_URL)

            # Check if we can find the get-started button
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='get-started-button']"))
                )
                button = driver.find_element(By.CSS_SELECTOR, "[data-testid='get-started-button']")

                # Check if it's visible and interactable
                if not button.is_displayed() or not button.is_enabled():
                    return False

                # Further check - try to click the button and see if form appears
                button.click()

                # Wait for the form to appear
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.TAG_NAME, "form"))
                    )
                    return True
                except:
                    return False
            except:
                return False
        finally:
            driver.quit()

    except Exception as e:
        logger.warning(f"UI availability check failed: {str(e)}")
        return False

    return False  # Default fallback

def test_birth_details_form(selenium_driver):
    """Test the Birth Details Form with the specified test data"""
    driver = selenium_driver

    # Navigate to the application landing page
    logger.info("Navigating to the application")
    driver.get(FRONTEND_URL)

    # Wait for the landing page to load and find the Get Started button
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='get-started-button']"))
    )

    # Wait for any loading overlay to disappear
    try:
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading-overlay"))
        )
    except:
        logger.warning("Loading overlay might not be present or didn't disappear in time")

    # Use JavaScript to click the button to avoid overlay issues
    get_started_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='get-started-button']")
    driver.execute_script("arguments[0].click();", get_started_button)

    # Wait for the birth details form to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "form"))
    )

    # Fill in the form with test data
    logger.info("Filling in the birth details form")

    # Set date
    date_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='date']")
    date_input.clear()
    date_input.send_keys(TEST_DATA["date"])

    # Set time
    time_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='time']")
    time_input.clear()
    time_input.send_keys(TEST_DATA["time"])

    # Set birth place
    birthplace_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='birthPlace']")
    birthplace_input.clear()
    birthplace_input.send_keys(TEST_DATA["birthPlace"])

    # Wait for geocoding to complete and coordinates to appear
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='coordinates-display']"))
    )

    # Get coordinates and validate
    coordinates_display = driver.find_element(By.CSS_SELECTOR, "[data-testid='coordinates-display']")
    assert coordinates_display is not None, "Coordinates not displayed"
    assert "Coordinates:" in coordinates_display.text, "Coordinates text not found"

    # Submit the form
    submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    assert not submit_button.get_attribute("disabled"), "Submit button is disabled"
    submit_button.click()

    # Wait for results to appear
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.bg-green-50"))
    )

    # Validate results
    results_div = driver.find_element(By.CSS_SELECTOR, "div.bg-green-50")
    assert "Suggested Time" in results_div.text, "Results not displayed properly"

    logger.info("Test completed successfully")


def test_complete_ui_ux_flow(selenium_driver):
    """Test the complete UI/UX flow according to the implementation plan"""
    driver = selenium_driver
    logger.info("Starting complete UI/UX flow test")

    try:
        # 1. Landing Page
        driver.get(FRONTEND_URL)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-testid='get-started-button']"))
        )

        # Wait for any loading overlay to disappear
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading-overlay"))
            )
        except:
            logger.warning("Loading overlay might not be present or didn't disappear in time")

        # Click the Get Started button using JavaScript to avoid overlay issues
        get_started_button = driver.find_element(By.CSS_SELECTOR, "button[data-testid='get-started-button']")
        assert get_started_button.is_displayed(), "Get started button not visible"
        driver.execute_script("arguments[0].click();", get_started_button)

        # 2. Birth Details Form - Wait for form to appear on birth-time-analysis page
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "form"))
        )

        # Fill form with test data
        date_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='date']")
        date_input.send_keys(TEST_DATA["date"])

        time_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='time']")
        time_input.send_keys(TEST_DATA["time"])

        birthplace_input = driver.find_element(By.CSS_SELECTOR, "[data-testid='birthPlace']")
        birthplace_input.send_keys(TEST_DATA["birthPlace"])

        # Wait for geocoding and validate
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='coordinates-display']"))
        )

        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        # 3. Initial Chart Generation
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chart-visualization']"))
        )

        # Test chart interactivity
        chart_svg = driver.find_element(By.CSS_SELECTOR, "[data-testid='chart-svg']")

        # Test planet tooltips
        planets = driver.find_elements(By.CSS_SELECTOR, "[data-testid^='planet-']")
        for planet in planets:
            ActionChains(driver).move_to_element(planet).perform()
            time.sleep(0.5)  # Wait for tooltip
            tooltip = driver.find_element(By.CSS_SELECTOR, ".entity-details")
            assert tooltip.is_displayed(), f"Tooltip not shown for {planet.get_attribute('data-testid')}"

        # Test chart zoom
        ActionChains(driver).move_to_element(chart_svg).double_click().perform()
        time.sleep(1)
        zoomed_chart = driver.find_element(By.CSS_SELECTOR, ".chart-visualization.zoomed")
        assert zoomed_chart.is_displayed(), "Chart zoom not working"

        # 4. Questionnaire
        next_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='continue-to-questionnaire']")
        next_button.click()

        # Answer questions
        for _ in range(3):  # Assuming 3 questions
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".question"))
            )

            # Select an answer
            answer_option = driver.find_element(By.CSS_SELECTOR, "input[type='radio']")
            answer_option.click()

            # Click next
            next_question_button = driver.find_element(By.CSS_SELECTOR, ".next-question")
            next_question_button.click()

            time.sleep(1)  # Wait for transition

        # 5. AI Analysis
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".processing-indicator"))
        )

        # Wait for analysis completion
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".rectified-chart"))
        )

        # 6. Results based on confidence
        confidence_score = driver.find_element(By.CSS_SELECTOR, "[data-testid='confidence-score']")
        assert float(confidence_score.text) > 0, "Confidence score not calculated"

        # 7. Chart Visualization Comparison
        charts_container = driver.find_element(By.CSS_SELECTOR, ".chart-comparison")
        assert len(charts_container.find_elements(By.CSS_SELECTOR, ".chart-visualization")) == 2, "Both charts not displayed"

        # Test chart toggle
        view_toggle = driver.find_element(By.CSS_SELECTOR, ".view-toggle")
        view_toggle.click()

        # Verify table view
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".table-container"))
        )

        # 8. Export/Share
        export_button = driver.find_element(By.CSS_SELECTOR, "[data-testid='export-pdf']")
        export_button.click()

        # Wait for export completion
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".export-success"))
        )

        logger.info("Complete UI/UX flow test passed successfully")

    except Exception as e:
        logger.error(f"UI/UX flow test failed: {str(e)}")
        raise

    finally:
        # Cleanup any test data if needed
        pass

def test_api_integration():
    """Test the API integration for birth time rectification"""
    try:
        api_url = f"{FRONTEND_URL}/api/rectify"
        payload = {
            "date": TEST_DATA["date"],
            "time": TEST_DATA["time"],
            "latitude": TEST_DATA["expected_results"]["latitude"],
            "longitude": TEST_DATA["expected_results"]["longitude"],
            "timezone": TEST_DATA["expected_results"]["timezone"]
        }

        response = requests.post(api_url, json=payload, timeout=10)
        assert response.status_code == 200, f"API returned {response.status_code}"

        data = response.json()
        assert "suggestedTime" in data, "Response missing suggestedTime"
        assert "confidence" in data, "Response missing confidence"

        logger.info(f"API Response: {data}")
    except requests.exceptions.ConnectionError:
        pytest.skip("API service not available")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
