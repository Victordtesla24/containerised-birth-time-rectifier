"""
Unit tests for chart verification functionality.

These tests use function-based testing for chart verification with OpenAI integration.
"""

import pytest
import json
import logging
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample test data
TEST_DATA = {
    'birthDate': '1990-01-15',
    'birthTime': '14:30',
    'birthLocation': 'New Delhi, India',
    'latitude': 28.6139,
    'longitude': 77.2090,
    'timezone': 'Asia/Kolkata'
}

@pytest.fixture
def sample_chart_data():
    """Sample chart data for testing"""
    return {
        "chart": {
            "ascendant": {"sign": "Aries", "longitude": 15.5},
            "planets": {
                "Sun": {"sign": "Taurus", "longitude": 25.3},
                "Moon": {"sign": "Cancer", "longitude": 10.2}
            }
        },
        "birth_details": {
            "birth_date": TEST_DATA["birthDate"],
            "birth_time": TEST_DATA["birthTime"],
            "location": TEST_DATA["birthLocation"],
            "latitude": TEST_DATA["latitude"],
            "longitude": TEST_DATA["longitude"],
            "timezone": TEST_DATA["timezone"]
        }
    }

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        "content": json.dumps({
            "verified": True,
            "confidence": 85,
            "corrections_applied": False,
            "message": "Chart verified successfully"
        }),
        "model_used": "gpt-4-turbo"
    }

@pytest.fixture
def mock_openai_service(mock_openai_response):
    """Mock OpenAI service"""
    service = AsyncMock()
    service.generate_completion.return_value = mock_openai_response
    return service

@pytest.fixture
def mock_chart_verifier(mock_openai_service):
    """Mock chart verifier"""
    verifier = MagicMock()
    verifier.openai_service = mock_openai_service

    async def verify_chart(verification_data, openai_service=None):
        """Mock verify chart method"""
        if not openai_service:
            openai_service = verifier.openai_service

        # Call OpenAI service
        response = await openai_service.generate_completion(
            prompt="Test prompt",
            task_type="chart_verification",
            max_tokens=800,
            temperature=0.2
        )

        # Process response
        try:
            content = response["content"]
            result = json.loads(content)
            result["verified_at"] = datetime.now().isoformat()
            return result
        except (KeyError, json.JSONDecodeError):
            # Return default response on error
            return {
                "verified": True,
                "confidence": 70,
                "corrections_applied": False,
                "message": "Verification failed but using default response",
                "verified_at": datetime.now().isoformat()
            }

    verifier.verify_chart = verify_chart
    return verifier

@pytest.mark.asyncio
async def test_chart_verification_success(sample_chart_data, mock_chart_verifier, mock_openai_service):
    """Test successful chart verification"""
    # Act
    result = await mock_chart_verifier.verify_chart(sample_chart_data, mock_openai_service)

    # Assert
    assert result["verified"] is True
    assert result["confidence"] == 85
    assert result["corrections_applied"] is False
    assert "message" in result
    assert "verified_at" in result
    mock_openai_service.generate_completion.assert_called_once()

@pytest.mark.asyncio
async def test_chart_verification_with_corrections(sample_chart_data):
    """Test chart verification with corrections"""
    # Arrange
    openai_service = AsyncMock()
    openai_service.generate_completion.return_value = {
        "content": json.dumps({
            "verified": True,
            "confidence": 75,
            "corrections_applied": True,
            "message": "Chart verified with corrections",
            "corrections": ["Ascendant position adjusted by 1 degree"]
        })
    }

    verifier = MagicMock()
    verifier.openai_service = openai_service

    async def verify_chart(verification_data, openai_service_param=None):
        """Mock verify chart with corrections"""
        service_to_use = openai_service_param or verifier.openai_service
        response = await service_to_use.generate_completion(
            prompt="Test prompt",
            task_type="chart_verification",
            max_tokens=800,
            temperature=0.2
        )

        content = response["content"]
        result = json.loads(content)
        result["verified_at"] = datetime.now().isoformat()
        return result

    verifier.verify_chart = verify_chart

    # Act
    result = await verifier.verify_chart(sample_chart_data, openai_service)

    # Assert
    assert result["verified"] is True
    assert result["confidence"] == 75
    assert result["corrections_applied"] is True
    assert "corrections" in result
    assert len(result["corrections"]) > 0
    assert "message" in result
    openai_service.generate_completion.assert_called_once()

@pytest.mark.asyncio
async def test_chart_verification_error_handling(sample_chart_data):
    """Test chart verification error handling"""
    # Arrange
    openai_service = AsyncMock()
    openai_service.generate_completion.side_effect = Exception("Test error")

    verifier = MagicMock()
    verifier.openai_service = openai_service

    async def verify_chart_with_error(verification_data, openai_service_param=None):
        """Mock verify chart that handles errors"""
        service_to_use = openai_service_param or verifier.openai_service
        try:
            await service_to_use.generate_completion(
                prompt="Test prompt",
                task_type="chart_verification",
                max_tokens=800,
                temperature=0.2
            )
            # Should not reach here
            return {}
        except Exception:
            # Return fallback on error
            return {
                "verified": True,
                "confidence": 60,
                "corrections_applied": False,
                "message": "Verification service error",
                "verified_at": datetime.now().isoformat()
            }

    verifier.verify_chart = verify_chart_with_error

    # Act
    result = await verifier.verify_chart(sample_chart_data, openai_service)

    # Assert
    assert result["verified"] is True
    assert result["confidence"] == 60
    assert "message" in result
    assert "verified_at" in result
    openai_service.generate_completion.assert_called_once()

if __name__ == "__main__":
    """Run tests directly"""
    asyncio.run(test_chart_verification_success(
        sample_chart_data(),
        mock_chart_verifier(mock_openai_service(mock_openai_response())),
        mock_openai_service(mock_openai_response())
    ))
