# Integration Tests for Birth Time Rectifier

This directory contains integration tests for the containerized Birth Time Rectifier application, which tests the interaction between the frontend, AI service, and Redis components.

## Prerequisites

The integration tests assume that the following services are running:

1. Frontend service on `http://localhost:3000`
2. AI service on `http://localhost:8000`
3. Redis on `localhost:6379`

## Running Tests

### Option 1: With Containers Running

If you have all the required containers running, you can simply run:

```bash
python -m pytest tests/integration
```

The tests will automatically detect the running services and execute the tests against them.

### Option 2: Force Tests to Run

If you want to force the tests to run even if containers aren't detected, set the `RUN_CONTAINER_TESTS` environment variable:

```bash
RUN_CONTAINER_TESTS=true python -m pytest tests/integration
```

Note: This may cause tests to fail if the services are truly unavailable.

### Option 3: Run Tests as Part of CI Pipeline

In a CI environment, you should start your containers first, then run the tests:

```bash
docker-compose up -d
RUN_CONTAINER_TESTS=true python -m pytest tests/integration
```

## Test Categories

1. **Connectivity Tests**: Verify that all services are reachable and healthy
2. **Functional Tests**: Verify that core functionality works across services
3. **Stability Tests**: Verify consistent performance over time

## Common Issues

- **Connection Refused Errors**: Make sure all containers are running
- **Redis Connection Issues**: Verify Redis is running on the default port
- **Slow Tests**: Use `-m "not slow"` to skip the time-consuming stability tests

## Adding New Tests

When adding new integration tests:

1. Use the `@skip_if_no_containers` decorator to make tests skippable when services aren't available
2. Add appropriate try/except blocks to handle connection errors gracefully
3. Add timeouts to avoid tests hanging indefinitely 