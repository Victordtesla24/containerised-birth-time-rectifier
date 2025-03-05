# AI Model Routing Implementation Guide

This guide documents the implementation of the AI model routing system for birth time rectification, designed to dynamically route requests to the most appropriate AI model based on task type and requirement.

## 1. Components Overview

### 1.1 OpenAI Service (`ai_service/api/services/openai_service.py`)

This service provides a unified interface for interacting with OpenAI's different models:

- **Intelligent Model Selection**: Routes tasks to the appropriate model based on complexity
  - `o1-preview`: High-accuracy astronomical calculations (birth time rectification)
  - `GPT-4 Turbo`: Cost-efficient natural language explanations
  - `GPT-4o-mini`: Lightweight auxiliary tasks like confidence scoring

- **Error Handling**: Implements retry logic with exponential backoff for API resilience
- **Cost Tracking**: Calculates and tracks costs for proper budgeting
- **Caching**: Supports caching for repeated requests to reduce API costs
- **Environment Variables**: Loads API keys from environment variables for security

### 1.2 Enhanced Unified Rectification Model (`ai_service/models/unified_model.py`)

The unified model now supports:

- **Multi-task Architecture**: Combines different astrological techniques:
  - Tattva (Traditional): 40% weighting
  - Nadi: 35% weighting
  - KP (Krishnamurti Paddhati): 25% weighting

- **AI-Based Rectification**: Uses the `o1-preview` model for high-precision astrological calculations
- **Fallback Mechanism**: Falls back to simulation if the AI is unavailable or errors occur
- **Explanation Generation**: Uses `GPT-4 Turbo` to generate natural language explanations
- **Significant Event Identification**: Uses `GPT-4o-mini` to identify astrological correlations
- **Response Caching**: Caches responses to improve performance and reduce costs

### 1.3 Testing Router (`ai_service/api/routers/ai_integration_test.py`)

The test router provides endpoints for testing and demonstrating the AI model routing:

- **Model Routing Endpoint**: Tests the model selection logic with different task types
- **Explanation Generation**: Tests the explanation generation functionality
- **Rectification Testing**: Tests the complete rectification process
- **Usage Statistics**: Provides insights into API usage and costs

### 1.4 FastAPI Integration (`ai_service/main.py`)

The main application now includes:

- **Model Preloading**: AI models are preloaded at application startup for better performance
- **Improved Lifespan Management**: GPU resources and model initialization are properly managed
- **Router Registration**: Follows dual-registration pattern for consistent API usage

## 2. Implementation Details

### 2.1 Model Routing Logic

The model selection is based on the task type, as defined in `_select_model` method in `OpenAIService`:

```python
def _select_model(self, task_type: str) -> str:
    if "rectification" in task_type.lower():
        return "o1-preview"  # High-accuracy astronomical calculations
    elif "explanation" in task_type.lower():
        return "gpt-4-turbo"  # Cost-efficient user interactions
    else:
        return "gpt-4o-mini"  # Lightweight auxiliary tasks
```

### 2.2 Cost Efficiency

Cost calculations are implemented in the `_calculate_cost` method:

```python
def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    # Set rate per 1M tokens (in USD)
    rates = {
        "o1-preview": {"input": 15.0, "output": 75.0},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        "gpt-4o-mini": {"input": 5.0, "output": 15.0}
    }

    # Default to GPT-4 Turbo rates if model not found
    rate = rates.get(model, rates["gpt-4-turbo"])

    # Calculate cost (convert to per-token rate from per-million rate)
    input_cost = (prompt_tokens / 1_000_000) * rate["input"]
    output_cost = (completion_tokens / 1_000_000) * rate["output"]

    return round(input_cost + output_cost, 6)
```

### 2.3 Fallback Mechanism

If AI is unavailable or encounters an error, the system falls back to the original simulation-based logic:

```python
# If AI rectification failed or unavailable, use simulation
if adjustment_minutes is None:
    logger.info("Using simulated rectification method")
    # Use existing simulation logic
    direction = 1 if random.random() > 0.5 else -1
    magnitude = random.randint(1, 30)
    adjustment_minutes = direction * magnitude
```

### 2.4 Continuous Operation

Models are now preloaded at application startup in the FastAPI lifespan context manager:

```python
# Preload AI models
try:
    from ai_service.models.unified_model import UnifiedRectificationModel
    logger.info("Preloading AI models for continuous operation...")
    app.state.rectification_model = UnifiedRectificationModel()
    logger.info("AI models preloaded successfully")
except Exception as e:
    logger.error(f"Error preloading AI models: {e}")
    app.state.rectification_model = None
```

## 3. Configuration

### 3.1 Environment Variables

The system requires the following environment variables:

```
# OpenAI API Key (required)
OPENAI_API_KEY=your_api_key_here

# Optional configuration
API_TIMEOUT=30
CACHE_EXPIRY=3600
GPU_MEMORY_FRACTION=0.7
MODEL_CACHE_SIZE=100
```

### 3.2 Docker Configuration

Docker Compose has been updated to pass these environment variables to the containers:

```yaml
environment:
  - PYTHONUNBUFFERED=1
  - ENVIRONMENT=development
  - APP_ENV=development
  - REDIS_URL=redis://redis:6379/0
  - LOG_LEVEL=DEBUG
  - SWISSEPH_PATH=/app/ephemeris
  - OPENAI_API_KEY=${OPENAI_API_KEY:-}
  - OPENAI_API_KEY_DEV=${OPENAI_API_KEY_DEV:-}
  - API_TIMEOUT=30
  - CACHE_EXPIRY=3600
  - GPU_MEMORY_FRACTION=0.7
  - MODEL_CACHE_SIZE=100
```

## 4. Testing

### 4.1 Automated Testing Script

A script for testing the AI integration has been provided:

```bash
scripts/test_ai_integration.sh
```

This script tests:
- Model routing for different task types
- Explanation generation
- Rectification process
- Usage statistics

### 4.2 Python Test Suite

The Python test suite in `tests/test_ai_model_integration.py` includes more comprehensive tests:

- Unit tests for model routing
- Tests with mock OpenAI responses
- Usage statistics verification

### 4.3 Manual Testing

You can test the API endpoints manually using curl:

```bash
# Test model routing
curl -X POST "http://localhost:8000/api/ai/test_model_routing" \
  -H "Content-Type: application/json" \
  -d '{"task_type": "rectification", "prompt": "Test prompt"}'

# Test explanation generation
curl -X POST "http://localhost:8000/api/ai/test_explanation" \
  -H "Content-Type: application/json" \
  -d '{"adjustment_minutes": 15, "reliability": "high"}'

# Test rectification
curl -X POST "http://localhost:8000/api/ai/test_rectification" \
  -H "Content-Type: application/json" \
  -d '{"birth_details": {"birthDate": "1990-01-01", "birthTime": "12:00"}}'

# Check usage statistics
curl "http://localhost:8000/api/ai/usage_statistics"
```

## 5. Running with Docker

To run the application with Docker:

1. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_key_here
   ```

2. Start the Docker containers:
   ```bash
   docker-compose up
   ```

3. Run the test script:
   ```bash
   scripts/test_ai_integration.sh
   ```

## 6. Troubleshooting

### 6.1 Common Issues

- **API Key Issues**: Ensure the `OPENAI_API_KEY` environment variable is set correctly
- **Model Timeout**: Increase the `API_TIMEOUT` value if requests are timing out
- **Memory Issues**: Adjust `GPU_MEMORY_FRACTION` if encountering memory-related errors
- **Import Errors**: Ensure required packages (`openai`, `tenacity`) are installed

### 6.2 Debugging

Enable debug logging for more detailed information:

```
LOG_LEVEL=DEBUG
```

Check the logs for detailed error information:

```bash
tail -f logs/ai_service.log
```

## 7. Performance Considerations

- **Caching**: Responses are cached based on input parameters to reduce API calls
- **Cache Expiry**: Cache is automatically cleared after 1 hour or 1000 requests
- **GPU Memory**: GPU memory is allocated efficiently for better performance
- **Model Preloading**: Models are preloaded at startup to reduce latency

## 8. Security Considerations

- **API Key Management**: API keys are loaded from environment variables, not hardcoded
- **Error Handling**: Error messages are sanitized to prevent information leakage
- **Rate Limiting**: Retry logic respects API rate limits to prevent account suspension
- **Monitoring**: Usage is monitored to detect unusual patterns or potential abuse
