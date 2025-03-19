# Birth Time Rectifier Tests

This directory contains tests for the Birth Time Rectifier application, focusing on ensuring that backend services align with the sequence diagrams defined in the documentation.

## Test Structure

The tests are organized into several categories:

- **Unit Tests**: Located in `tests/unit/`. These test individual components in isolation.
- **Component Tests**: Located in `tests/components/`. These test components with dependencies.
- **Integration Tests**: Located in `tests/integration/`. These test multiple components working together.
- **API Sequence Tests**: Documented in `tests/API_SEQUENCE_TESTS.md`. These test the full API sequence flow.

## Running Tests

### Local Development

For local development, you can run tests using pytest:

```bash
# Run all tests
PYTHONPATH=. pytest

# Run unit tests only
PYTHONPATH=. pytest tests/unit/

# Run component tests only
PYTHONPATH=. pytest tests/components/

# Run integration tests only
PYTHONPATH=. pytest tests/integration/

# Run a specific test file
PYTHONPATH=. pytest tests/unit/test_chart_verification_functions.py
```

### Using Docker

For containerized testing, use the provided script:

```bash
# Run all tests
./run_tests.sh

# Run unit tests only
./run_tests.sh --unit

# Run component tests only
./run_tests.sh --component

# Run integration tests only
./run_tests.sh --integration

# Skip OpenAI tests
./run_tests.sh --skip-openai

# Run tests with debug output
./run_tests.sh --debug
```

### Docker Compose

You can also use Docker Compose directly:

```bash
# Run all tests
docker-compose -f docker-compose.test.yml up --build

# Run tests and clean up
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
docker-compose -f docker-compose.test.yml down
```

## Test Dependencies

The tests require the following dependencies:

- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock
- aiohttp
- httpx
- websockets
- fastapi
- redis

These are installed automatically when running tests in Docker.

## API Rate Limiting

The tests include rate limiting for OpenAI API calls to prevent exceeding API quotas during testing. The rate limiter is implemented in `tests/utils/rate_limiter.py`.

## Alignment with Sequence Diagrams

The tests are designed to ensure that the backend services align with the sequence diagrams defined in the documentation. The following sequence flows are tested:

1. **Consolidated API Questionnaire Flow**: Tests the questionnaire interaction pattern.
2. **Original Sequence Diagram**: Tests the complete end-to-end API flow.
3. **Vedic Chart Verification Flow**: Tests the OpenAI verification integration.

## Troubleshooting

If tests are failing, check the following:

1. Ensure dependencies are installed.
2. Ensure environment variables are set correctly.
3. Check Redis connection if using the Redis rate limiter.
4. If OpenAI tests are failing, check the OpenAI API key.

For more information, see the API sequence tests documentation in `tests/API_SEQUENCE_TESTS.md`.
