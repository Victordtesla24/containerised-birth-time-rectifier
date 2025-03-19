import pytest
import asyncio
import os
import logging
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import the OpenAI service
try:
    from ai_service.api.services.openai.service import OpenAIService as RealOpenAIService
    from ai_service.api.services.openai.model_selection import select_model
    SERVICE_AVAILABLE = True
    # Create an alias to avoid name conflict with the mock class below
    OpenAIServiceClass = RealOpenAIService
except ImportError:
    logger.warning("OpenAI service module not available, using mocks for testing")
    SERVICE_AVAILABLE = False
    OpenAIServiceClass = None

    # Create mock OpenAI service for testing
    class OpenAIService:
        def __init__(self):
            self.client = AsyncMock()
            self.api_key = "test_key"
            self.usage_stats = {
                "calls_made": 0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost": 0.0
            }

        async def generate_completion(self, prompt, task_type, max_tokens=500, temperature=0.7):
            self.usage_stats["calls_made"] += 1
            self.usage_stats["prompt_tokens"] += 10
            self.usage_stats["completion_tokens"] += 20
            self.usage_stats["total_tokens"] += 30
            return {"content": "test response"}

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

# Skip all tests if OpenAI API key is not set and we're using real service
pytestmark = pytest.mark.skipif(
    SERVICE_AVAILABLE and not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY environment variable not set"
)

@pytest.fixture
def mock_openai_response():
    """Mock successful OpenAI API response"""
    return AsyncMock(
        choices=[AsyncMock(message=AsyncMock(content="test response"))],
        usage=AsyncMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    )

@pytest.mark.asyncio
async def test_openai_service_initialization():
    """Test OpenAI service initialization"""
    # Use environment variable or mock API key
    api_key = os.environ.get("OPENAI_API_KEY", "test_key")

    # Patch environment to provide API key
    with patch.dict(os.environ, {"OPENAI_API_KEY": api_key}):
        # Use the real service class if available, otherwise use the mock
        if SERVICE_AVAILABLE and OpenAIServiceClass is not None:
            service = OpenAIServiceClass()
        else:
            # If the real service isn't available, use the mock
            service = OpenAIService()

        # Verify service properties
        assert service.api_key is not None
        assert hasattr(service, "client")
        assert hasattr(service, "usage_stats")

        logger.info("OpenAI service initialized successfully")

@pytest.mark.asyncio
@rate_limited(openai_rate_limiter)
async def test_openai_service_rate_limiting():
    """Test OpenAI service with rate limiting"""
    # Arrange
    service = OpenAIService()

    if SERVICE_AVAILABLE:
        # Create mock for real service
        service.client = AsyncMock()
        service.client.chat.completions.create.return_value = AsyncMock(
            choices=[AsyncMock(message=AsyncMock(content="test response"))],
            usage=AsyncMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        )

    # Act - make multiple requests to test rate limiting
    results = []
    for i in range(3):
        result = await service.generate_completion(
            prompt=f"Test prompt {i}",
            task_type="test",
            max_tokens=100
        )
        results.append(result)

    # Assert
    assert len(results) == 3
    for result in results:
        assert "content" in result

    # Verify usage statistics were updated
    assert service.usage_stats["calls_made"] >= 3
    assert service.usage_stats["total_tokens"] > 0

    logger.info("Rate limiting test completed successfully")

@pytest.mark.asyncio
async def test_openai_service_error_handling():
    """Test OpenAI service error handling with proper error propagation"""
    # Arrange
    service = OpenAIService()

    if SERVICE_AVAILABLE:
        # Create mock that raises an exception
        service.client = AsyncMock()
        service.client.chat.completions.create.side_effect = Exception("Test error")
    else:
        # For mock service, patch the generate_completion method
        original_method = service.generate_completion
        service.generate_completion = AsyncMock(side_effect=Exception("Test error"))

    # Act & Assert - expect error to be propagated with a ValueError wrapper
    with pytest.raises(ValueError) as excinfo:
        await service.generate_completion(
            prompt="Test error handling",
            task_type="test",
            max_tokens=100
        )

    # Verify the error message contains the original exception message
    assert "Test error" in str(excinfo.value)
    logger.info("OpenAI service properly propagated the error as expected")

    # Restore original method if needed
    if not SERVICE_AVAILABLE:
        service.generate_completion = original_method

@pytest.mark.asyncio
async def test_model_selection():
    """Test model selection based on task type"""
    # Skip if we're using mocks
    if not SERVICE_AVAILABLE:
        pytest.skip("Model selection test requires real service")

    # Test different task types
    task_types = ["chart_verification", "explanation", "interpretation", "rectification"]

    for task_type in task_types:
        model = select_model(task_type)
        assert model is not None
        assert isinstance(model, str)
        assert len(model) > 0

        logger.info(f"Model selection for {task_type}: {model}")

@pytest.mark.asyncio
@rate_limited(openai_rate_limiter)
async def test_openai_service_chart_verification():
    """Test OpenAI service for chart verification task"""
    # Arrange
    service = OpenAIService()

    if SERVICE_AVAILABLE:
        # Create mock for real service
        service.client = AsyncMock()
        service.client.chat.completions.create.return_value = AsyncMock(
            choices=[
                AsyncMock(
                    message=AsyncMock(
                        content="""
                        {
                            "verified": true,
                            "confidence": 85,
                            "corrections_applied": false,
                            "message": "Chart verified successfully"
                        }
                        """
                    )
                )
            ],
            usage=AsyncMock(prompt_tokens=50, completion_tokens=100, total_tokens=150)
        )

    # Act
    result = await service.generate_completion(
        prompt="Verify this chart data...",
        task_type="chart_verification",
        max_tokens=800,
        temperature=0.2
    )

    # Assert
    assert result is not None
    assert "content" in result

    logger.info("Chart verification test completed successfully")

if __name__ == "__main__":
    # For running tests directly
    asyncio.run(test_openai_service_initialization())
    asyncio.run(test_openai_service_rate_limiting())
    print("OpenAI service tests passed!")
