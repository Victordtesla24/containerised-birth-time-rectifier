import pytest
import requests
import json
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Service URLs
FRONTEND_URL = "http://localhost:3000"

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
        response = requests.get(FRONTEND_URL, timeout=2)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

@pytest.mark.skipif(not check_services_running(), reason="Services not running")
def test_birth_details_form(selenium_driver):
    """Test the Birth Details Form with the specified test data"""
    driver = selenium_driver
    
    # Navigate to the application
    logger.info("Navigating to the application")
    driver.get(FRONTEND_URL)
    
    # Wait for the page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "form"))
    )
    
    # Fill in the form with test data
    logger.info("Filling in the birth details form")
    
    # Set date
    date_input = driver.find_element(By.ID, "date")
    date_input.clear()
    date_input.send_keys(TEST_DATA["date"])
    
    # Set time
    time_input = driver.find_element(By.ID, "time")
    time_input.clear()
    time_input.send_keys(TEST_DATA["time"])
    
    # Set birth place
    birthplace_input = driver.find_element(By.ID, "birthPlace")
    birthplace_input.clear()
    birthplace_input.send_keys(TEST_DATA["birthPlace"])
    
    # Wait for geocoding to complete
    time.sleep(2)
    
    # Get coordinates and validate
    coordinates_display = driver.find_element(By.CSS_SELECTOR, "[data-testid='coordinates-display']")
    assert coordinates_display is not None, "Coordinates not displayed"
    
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

@pytest.mark.skipif(not check_services_running(), reason="Services not running")
def test_complete_ui_ux_flow():
    """Test the complete UI/UX flow according to the implementation plan"""
    # This is a placeholder for the complete UI/UX flow test
    # This should test all steps in the UI/UX Flow Chart from the implementation plan
    # 1. Landing Page -> Birth Details Form
    # 2. Form validation
    # 3. Initial Chart Generation
    # 4. Questionnaire
    # 5. AI Analysis
    # 6. Results based on confidence
    # 7. Chart Visualization
    # 8. Export/Share functionality
    
    logger.info("This test is a placeholder for the complete UI/UX flow test")
    logger.info("Implement this test when all UI/UX components are available")
    pytest.skip("Complete UI/UX flow not implemented yet")

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
        
        response = requests.post(api_url, json=payload, timeout=5)
        assert response.status_code == 200, f"API returned {response.status_code}"
        
        data = response.json()
        assert "suggestedTime" in data, "Response missing suggestedTime"
        assert "confidence" in data, "Response missing confidence"
        
        logger.info(f"API Response: {data}")
    except requests.exceptions.ConnectionError:
        pytest.skip("API service not available")

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 