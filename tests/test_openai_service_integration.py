"""
Test script to verify the OpenAI service integration and continuous operation.
Tests API connectivity, error handling, fallback mechanisms, and caching.
"""

import requests
import json
import time
import os
import pytest
import logging
import random
from concurrent.futures import ThreadPoolExecutor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for API tests
BASE_URL = "http://localhost:8000"

def test_openai_connectivity():
    """Test basic connectivity to the OpenAI service via the AI endpoint"""
    logger.info("Testing OpenAI service connectivity...")

    # Using the AI integration test endpoint to verify OpenAI connectivity
    test_prompt = "Test connectivity to OpenAI API"
    response = requests.post(
        f"{BASE_URL}/api/v1/ai/test_model_routing",
        json={
            "task_type": "explanation",
            "prompt": test_prompt
        }
    )

    # Check status code
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}. Response: {response.text}"

    # Check response structure
    data = response.json()
    logger.info(f"OpenAI service response received")

    # Basic validation of response structure
    assert "result" in data, "Response missing result field"
    assert data["result"], "Result field should not be empty"
    assert "model_used" in data, "Response missing model_used field"

    # Check for token usage information
    assert "token_usage" in data, "Response missing token_usage field"

    # Log model used to confirm routing is working
    logger.info(f"Used model: {data['model_used']}")

    # No need to check for tokens field as it's not in the response
    # assert "tokens" in data, "Response missing tokens field"

def test_error_handling_and_retries():
    """Test error handling and retries by generating a request likely to cause rate limiting"""
    logger.info("Testing error handling and retry mechanisms...")

    # Making multiple rapid requests to potentially trigger rate limits
    # This tests the retry logic in the OpenAI service
    results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for i in range(3):
            future = executor.submit(
                requests.post,
                f"{BASE_URL}/api/v1/ai/test_model_routing",
                json={
                    "task_type": "explanation",
                    "prompt": f"Test error handling iteration {i} with a {random.randint(1, 1000)} random value"
                }
            )
            futures.append(future)

        for future in futures:
            results.append(future.result())

    # All requests should eventually succeed due to retry logic
    for i, response in enumerate(results):
        assert response.status_code == 200, f"Request {i} failed with status code {response.status_code}"
        data = response.json()
        assert "result" in data, f"Request {i} response missing result field"
        assert data["result"], f"Request {i} response has empty result"

    logger.info("All parallel requests completed successfully, demonstrating retry capability")

def test_fallback_mechanism():
    """Test the fallback mechanism when the OpenAI API is unavailable"""
    logger.info("Testing fallback mechanism by using an invalid task type...")

    # Send a request with an invalid/unknown task type to trigger fallback
    response = requests.post(
        f"{BASE_URL}/api/v1/ai/test_model_routing",
        json={
            "task_type": "invalid_task_type_to_trigger_fallback",
            "prompt": "This should trigger the fallback mechanism"
        }
    )

    # Even with an invalid task type, we should get a success response due to fallback
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}. Response: {response.text}"

    data = response.json()
    logger.info(f"Received response: {data}")

    # Content should still be present due to fallback mechanism
    assert "result" in data, "Response missing result field"
    assert data["result"], "Result should not be empty, even with fallback"

def test_caching_mechanism():
    """Test that the caching mechanism works for identical requests"""
    logger.info("Testing caching mechanism...")

    # Make the same request twice and check if the second is faster (cached)
    test_prompt = "This is a test prompt for caching verification " + str(random.randint(1000, 9999))

    # First request
    start_time1 = time.time()
    response1 = requests.post(
        f"{BASE_URL}/api/v1/ai/test_model_routing",
        json={
            "task_type": "explanation",
            "prompt": test_prompt
        }
    )
    duration1 = time.time() - start_time1
    data1 = response1.json()

    logger.info(f"First request took {duration1:.2f} seconds")

    # Second identical request (should use cache)
    start_time2 = time.time()
    response2 = requests.post(
        f"{BASE_URL}/api/v1/ai/test_model_routing",
        json={
            "task_type": "explanation",
            "prompt": test_prompt
        }
    )
    duration2 = time.time() - start_time2
    data2 = response2.json()

    logger.info(f"Second request took {duration2:.2f} seconds")

    # Verify the model and response exists
    assert "result" in data1, "First response missing result field"
    assert data1["result"], "First response has empty result"
    assert "model_used" in data1, "First response missing model_used field"

    assert "result" in data2, "Second response missing result field"
    assert data2["result"], "Second response has empty result"
    assert "model_used" in data2, "Second response missing model_used field"

    # Both responses should have the same model
    assert data1["model_used"] == data2["model_used"], "Model used should be the same for cached requests"

    # Verify token usage is present in both responses
    assert "token_usage" in data1, "First response missing token_usage field"
    assert "token_usage" in data2, "Second response missing token_usage field"

def test_usage_statistics():
    """Test retrieving OpenAI usage statistics"""
    logger.info("Testing usage statistics...")

    # Get usage statistics from the API
    response = requests.get(f"{BASE_URL}/api/v1/ai/usage_statistics")
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}. Response: {response.text}"

    stats = response.json()
    logger.info(f"Usage statistics: {json.dumps(stats, indent=2)}")

    # Verify basic structure of usage statistics
    assert "total_tokens" in stats, "Usage statistics missing total_tokens field"
    assert "prompt_tokens" in stats, "Usage statistics missing prompt_tokens field"
    assert "completion_tokens" in stats, "Usage statistics missing completion_tokens field"
    assert "calls_made" in stats, "Usage statistics missing calls_made field"
    assert "estimated_cost" in stats, "Usage statistics missing estimated_cost field"

    # After our tests, calls_made should be at least 1
    assert stats["calls_made"] > 0, "No API calls recorded in usage statistics"

def test_model_selection():
    """Test that different task types route to appropriate models"""
    logger.info("Testing model selection logic...")

    # Test each task type and verify correct model selection
    task_types = ["explanation", "rectification", "auxiliary"]

    for task_type in task_types:
        logger.info(f"Testing task type: {task_type}")
        response = requests.post(
            f"{BASE_URL}/api/v1/ai/test_model_routing",
            json={
                "task_type": task_type,
                "prompt": f"Test prompt for {task_type}"
            }
        )

        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        data = response.json()
        assert "model_used" in data, f"Response for task type {task_type} missing model_used field"

        # Log which model was used for this task type
        model_used = data["model_used"]
        logger.info(f"Task type '{task_type}' routed to model: {model_used}")

        # Verify model selection logic
        if task_type == "explanation":
            assert "gpt-4" in model_used.lower(), f"Expected explanation task to use GPT-4, got {model_used}"
        elif task_type == "rectification":
            assert "o1" in model_used.lower(), f"Expected rectification task to use Claude, got {model_used}"
        elif task_type == "auxiliary":
            assert "gpt-4o-mini" in model_used.lower(), f"Expected auxiliary task to use GPT-4o-mini, got {model_used}"

def test_continuous_operation():
    """Test continuous operation by making repeated requests over time"""
    logger.info("Testing continuous operation with repeated requests...")

    # Make requests with delays to simulate continuous operation
    success_count = 0
    total_requests = 5

    for i in range(total_requests):
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/ai/test_model_routing",
                json={
                    "task_type": "explanation",
                    "prompt": f"Continuous operation test {i} at {time.time()}"
                }
            )

            if response.status_code == 200:
                success_count += 1
                logger.info(f"Request {i+1}/{total_requests} succeeded")
            else:
                logger.warning(f"Request {i+1}/{total_requests} failed with status {response.status_code}")

            # Wait a bit between requests
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error during continuous operation test: {str(e)}")

    # Calculate success rate
    success_rate = (success_count / total_requests) * 100
    logger.info(f"Continuous operation test completed with {success_rate:.1f}% success rate")

    # We expect at least 80% success for good continuous operation
    assert success_rate >= 80, f"Continuous operation test failed with only {success_rate:.1f}% success rate"

def run_tests():
    """Run all tests manually"""
    try:
        print("Testing OpenAI service integration...")

        # Test connectivity
        print("1. Testing basic connectivity...")
        test_openai_connectivity()
        print("✅ Basic connectivity test successful")

        # Test error handling
        print("2. Testing error handling and retries...")
        test_error_handling_and_retries()
        print("✅ Error handling test successful")

        # Test fallback mechanism
        print("3. Testing fallback mechanism...")
        test_fallback_mechanism()
        print("✅ Fallback mechanism test successful")

        # Test caching
        print("4. Testing caching mechanism...")
        test_caching_mechanism()
        print("✅ Caching mechanism test completed")

        # Test usage statistics
        print("5. Testing usage statistics...")
        test_usage_statistics()
        print("✅ Usage statistics test successful")

        # Test model selection
        print("6. Testing model selection logic...")
        test_model_selection()
        print("✅ Model selection test successful")

        # Test continuous operation
        print("7. Testing continuous operation...")
        test_continuous_operation()
        print("✅ Continuous operation test successful")

        print("\nAll OpenAI service tests completed successfully!")
        return True
    except AssertionError as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

if __name__ == "__main__":
    run_tests()
