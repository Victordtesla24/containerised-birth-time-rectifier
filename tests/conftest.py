"""
Test configuration for pytest.

This module provides fixtures and configuration for the test suite.
"""

import pytest
import os
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from unittest.mock import MagicMock, AsyncMock
import asyncio
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock classes for testing
class MockOpenAIService:
    """Mock OpenAI service for testing"""

    def __init__(self):
        self.api_key = "test_key"
        self.client = AsyncMock()
        self.usage_stats = {
            "calls_made": 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost": 0.0
        }

    async def generate_completion(self, prompt, task_type, max_tokens=500, temperature=0.7):
        """Mock generate completion"""
        self.usage_stats["calls_made"] += 1
        self.usage_stats["prompt_tokens"] += 10
        self.usage_stats["completion_tokens"] += 20
        self.usage_stats["total_tokens"] += 30

        # Return a default response
        return {
            "content": json.dumps({
                "verified": True,
                "confidence": 85,
                "corrections_applied": False,
                "message": "Chart verified successfully"
            }),
            "model_used": "gpt-4-turbo"
        }

class MockChartVerifier:
    """Mock chart verifier for testing"""

    def __init__(self):
        self.openai_service = MockOpenAIService()

    async def verify_chart(self, verification_data, openai_service=None):
        """Mock verify chart"""
        if not openai_service:
            openai_service = self.openai_service

        # Call OpenAI service
        response = await openai_service.generate_completion(
            prompt="Test prompt",
            task_type="chart_verification",
            max_tokens=800,
            temperature=0.2
        )

        # Parse response
        if isinstance(response, dict) and "content" in response:
            try:
                result = json.loads(response["content"])
                result["verified_at"] = "2023-01-01T00:00:00.000Z"
                return result
            except json.JSONDecodeError:
                pass

        # Default response
        return {
            "verified": True,
            "confidence": 70,
            "corrections_applied": False,
            "message": "Chart verified with default response",
            "verified_at": "2023-01-01T00:00:00.000Z"
        }

class MockChartService:
    """Mock chart service for testing"""

    def __init__(self):
        self.chart_verifier = MockChartVerifier()

    async def generate_chart(self, *args, **kwargs):
        """Mock generate chart"""
        return {
            "id": "test-chart-id",
            "ascendant": {"sign": "Aries", "longitude": 15.5},
            "planets": {
                "Sun": {"sign": "Taurus", "longitude": 25.3},
                "Moon": {"sign": "Cancer", "longitude": 10.2}
            }
        }

# Fixtures for testing
@pytest.fixture
def mock_openai_service():
    """Fixture for mock OpenAI service"""
    return MockOpenAIService()

@pytest.fixture
def mock_chart_verifier():
    """Fixture for mock chart verifier"""
    return MockChartVerifier()

@pytest.fixture
def mock_chart_service():
    """Fixture for mock chart service"""
    return MockChartService()

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up environment variables for testing."""
    # Store original environment variables
    original_env = os.environ.copy()

    # Set test environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY environment variable is not set in .env file.")

    # For yield fixture
    yield

    # Restore original environment after tests
    for key, value in original_env.items():
        os.environ[key] = value
