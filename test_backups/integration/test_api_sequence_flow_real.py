# tests/integration/test_api_sequence_flow_real.py
import pytest
import asyncio
import aiohttp
import json
import os
import logging
from typing import Dict, Any

# Import rate limiter if available
try:
    from tests.utils.rate_limiter import openai_rate_limiter, rate_limited
except ImportError:
    # Mock rate limiter if not available
    def rate_limited(limiter):
        def decorator(func):
            return func
        return decorator

    class MockRateLimiter:
        async def wait(self):
            pass

    openai_rate_limiter = MockRateLimiter()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = os.environ.get('API_URL', 'http://localhost:9000')
REQUEST_TIMEOUT = 30  # seconds

# Test data for the sequence flow
TEST_DATA = {
    'birthDate': '1990-01-15',
    'birthTime': '14:30',
    'birthLocation': 'New Delhi, India',
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
    if not path.startswith('/'):
        path = '/' + path
    base = API_BASE_URL.rstrip('/')
    path = path.replace('//', '/')
    return f"{base}{path}"

# Test the sequence flow with real API calls
@pytest.mark.asyncio
@rate_limited(openai_rate_limiter)
async def test_full_sequence_flow():
    """
    Test the full API sequence flow as described in the sequence diagram.

    This follows the "Consolidated API Questionnaire Flow" and
    "Original Sequence Diagram" from the architecture documentation.
    """
    logger.info("Starting full API sequence flow test")

    async with aiohttp.ClientSession() as session:
        # 1. Session initialization
        logger.info("Step 1: Session initialization")
        async with session.get(api_url("/api/v1/session/init")) as response:
            assert response.status == 200, f"Session initialization failed with status {response.status}"
            data = await response.json()
            assert "session_id" in data, "Session initialization response missing session_id"
            session_id = data["session_id"]
            logger.info(f"Session initialized with ID: {session_id}")

        # 2. Geocoding
        logger.info("Step 2: Geocoding")
        geocode_data = {
            "query": TEST_DATA["birthLocation"],
            "session_id": session_id
        }
        headers = {"X-Session-ID": session_id}

        async with session.post(
            api_url("/api/v1/geocode"),
            json=geocode_data,
            headers=headers
        ) as response:
            assert response.status == 200, f"Geocoding failed with status {response.status}"
            data = await response.json()
            assert "results" in data, "Geocoding response missing results"
            assert len(data["results"]) > 0, "Geocoding returned empty results"

            # Extract coordinates from response
            first_result = data["results"][0]
            if "latitude" in first_result and "longitude" in first_result:
                TEST_DATA["latitude"] = first_result["latitude"]
                TEST_DATA["longitude"] = first_result["longitude"]
            if "timezone" in first_result:
                TEST_DATA["timezone"] = first_result["timezone"]

            logger.info(f"Geocoded {TEST_DATA['birthLocation']} to coordinates: {TEST_DATA['latitude']}, {TEST_DATA['longitude']}")

        # 3. Chart validation
        logger.info("Step 3: Chart validation")
        validation_data = {
            "birth_details": {
                "birth_date": TEST_DATA["birthDate"],
                "birth_time": TEST_DATA["birthTime"],
                "location": TEST_DATA["birthLocation"],
                "latitude": TEST_DATA["latitude"],
                "longitude": TEST_DATA["longitude"],
                "timezone": TEST_DATA["timezone"]
            },
            "session_id": session_id
        }

        async with session.post(
            api_url("/api/v1/chart/validate"),
            json=validation_data,
            headers=headers
        ) as response:
            assert response.status == 200, f"Chart validation failed with status {response.status}"
            data = await response.json()
            assert "valid" in data, "Chart validation response missing valid field"
            assert data["valid"] is True, f"Chart validation failed: {data.get('errors', [])}"
            logger.info("Chart validation successful")

        # 4. Chart generation with OpenAI verification
        logger.info("Step 4: Chart generation with verification")
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
                "verify_with_openai": True
            },
            "session_id": session_id
        }

        async with session.post(
            api_url("/api/v1/chart/generate"),
            json=chart_data,
            headers=headers
        ) as response:
            assert response.status == 200, f"Chart generation failed with status {response.status}"
            data = await response.json()
            assert "chart_id" in data, "Chart generation response missing chart_id"
            chart_id = data["chart_id"]

            # Check for verification data
            verification = data.get("verification", {})
            if verification:
                logger.info(f"Chart verified with confidence: {verification.get('confidence', 'N/A')}")

            logger.info(f"Chart generated with ID: {chart_id}")

        # 5. Chart retrieval
        logger.info("Step 5: Chart retrieval")
        async with session.get(
            api_url(f"/api/v1/chart/{chart_id}"),
            headers=headers
        ) as response:
            assert response.status == 200, f"Chart retrieval failed with status {response.status}"
            data = await response.json()
            assert "chart" in data, "Chart retrieval response missing chart data"
            logger.info(f"Chart retrieved successfully: {chart_id}")

        # 6. Questionnaire initialization
        logger.info("Step 6: Questionnaire initialization")
        questionnaire_data = {
            "chart_id": chart_id,
            "session_id": session_id
        }

        async with session.post(
            api_url("/api/v1/questionnaire/initialize"),
            json=questionnaire_data,
            headers=headers
        ) as response:
            assert response.status == 200, f"Questionnaire initialization failed with status {response.status}"
            data = await response.json()
            assert "question" in data, "Questionnaire initialization response missing question"

            # Store question for answering
            current_question = data["question"]
            questionnaire_id = data.get("sessionId", session_id)

            logger.info(f"Questionnaire initialized with first question: {current_question.get('id', 'unknown')}")

        # 7. Answer questionnaire questions
        logger.info("Step 7: Answer questionnaire questions")

        # Answer multiple questions in sequence
        question_count = 0
        max_questions = min(3, len(TEST_DATA["questionnaire_answers"]))

        while question_count < max_questions and current_question:
            question_id = current_question.get("id")

            # Get answer data for this question
            answer_data = {
                "sessionId": questionnaire_id,
                "questionId": question_id,
                "answer": TEST_DATA["questionnaire_answers"][question_count]["answer"],
                "confidence": TEST_DATA["questionnaire_answers"][question_count]["confidence"]
            }

            async with session.post(
                api_url("/api/v1/questionnaire/answer"),
                json=answer_data,
                headers=headers
            ) as response:
                assert response.status == 200, f"Question answer failed with status {response.status}"
                data = await response.json()

                # Check if questionnaire is complete
                if data.get("complete", False):
                    logger.info("Questionnaire completed after answering question")
                    break

                # Find next question
                next_question = None
                if "question" in data:
                    next_question = data["question"]
                elif "nextQuestion" in data:
                    next_question = data["nextQuestion"]

                if next_question:
                    current_question = next_question
                    question_count += 1
                    logger.info(f"Answered question {question_count}, received next question")
                else:
                    logger.warning("No next question received, ending questionnaire")
                    break

        logger.info(f"Answered {question_count} questions successfully")

        # 8. Complete questionnaire
        logger.info("Step 8: Complete questionnaire")
        completion_data = {
            "sessionId": questionnaire_id
        }

        async with session.post(
            api_url("/api/v1/questionnaire/complete"),
            json=completion_data,
            headers=headers
        ) as response:
            assert response.status == 200, f"Questionnaire completion failed with status {response.status}"
            data = await response.json()
            assert "status" in data, "Completion response missing status"
            logger.info(f"Questionnaire completed with status: {data['status']}")

        # 9. Birth time rectification
        logger.info("Step 9: Birth time rectification")
        rectification_data = {
            "chart_id": chart_id,
            "questionnaire_id": questionnaire_id,
            "session_id": session_id
        }

        async with session.post(
            api_url("/api/v1/chart/rectify"),
            json=rectification_data,
            headers=headers
        ) as response:
            assert response.status == 200, f"Chart rectification failed with status {response.status}"
            data = await response.json()
            assert "rectified_chart_id" in data, "Rectification response missing rectified_chart_id"

            rectified_chart_id = data["rectified_chart_id"]
            logger.info(f"Chart rectified with new ID: {rectified_chart_id}")

            if "rectified_time" in data:
                logger.info(f"Birth time rectified to: {data['rectified_time']}")

        # 10. Chart comparison
        logger.info("Step 10: Chart comparison")
        async with session.get(
            api_url(f"/api/v1/chart/compare?chart1={chart_id}&chart2={rectified_chart_id}"),
            headers=headers
        ) as response:
            assert response.status == 200, f"Chart comparison failed with status {response.status}"
            data = await response.json()
            assert "differences" in data, "Comparison response missing differences"

            logger.info(f"Charts compared successfully, found {len(data['differences'])} differences")

        # 11. Chart export
        logger.info("Step 11: Chart export")
        export_data = {
            "chart_id": rectified_chart_id,
            "format": "pdf",
            "session_id": session_id
        }

        async with session.post(
            api_url("/api/v1/chart/export"),
            json=export_data,
            headers=headers
        ) as response:
            assert response.status == 200, f"Chart export failed with status {response.status}"
            data = await response.json()
            assert "download_url" in data, "Export response missing download_url"

            download_url = data["download_url"]
            logger.info(f"Chart export prepared with download URL: {download_url}")

        logger.info("Full API sequence flow test completed successfully")

if __name__ == "__main__":
    # For running the test directly
    asyncio.run(test_full_sequence_flow())
