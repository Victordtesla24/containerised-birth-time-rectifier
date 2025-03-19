# API Sequence Tests

This directory contains comprehensive test implementations for the Birth Time Rectifier API sequence flows.

## Overview

The tests are designed to validate that the backend services strictly align with the sequence diagrams
documented in `docs/architecture/sequence_diagram.md`, specifically:

1. **Consolidated API Questionnaire Flow** - Tests the questionnaire interaction pattern
2. **Original Sequence Diagram** - Tests the complete end-to-end API flow
3. **Vedic Chart Verification Flow** - Tests the OpenAI verification integration

## Test Structure

The test suite is organized into three main components:

### 1. Integration Tests

Location: `tests/integration/test_api_sequence_flow.py`

These tests validate the complete API sequence flow with real API calls. They follow the sequence
described in the diagrams and verify that each API endpoint works correctly in the sequence.

### 2. Unit Tests

Location:
- `tests/unit/test_questionnaire_api_flow.py` - Tests the questionnaire API flow
- `tests/unit/test_chart_verification.py` - Tests the chart verification with OpenAI

These tests focus on specific parts of the API sequence to provide more targeted testing of
critical components.

### 3. Test Runner

Location: `tests/run_api_sequence_tests.py`

This script coordinates the execution of all test suites and provides a unified interface for
running the tests.

## Rate Limiting

The tests implement rate limiting for OpenAI API calls to prevent exceeding API quotas during testing.
The rate limiter is implemented in `tests/utils/rate_limiter.py` and uses a token bucket algorithm.

## Running the Tests

### Prerequisites

1. The AI service API must be running and accessible
2. OpenAI API key should be set in the environment as `OPENAI_API_KEY`

### Running All Tests

```bash
./tests/run_api_sequence_tests.py
```

### Running Specific Test Suites

```bash
# Run only integration tests
./tests/run_api_sequence_tests.py --test-suite integration

# Run only questionnaire tests
./tests/run_api_sequence_tests.py --test-suite questionnaire

# Run only verification tests
./tests/run_api_sequence_tests.py --test-suite verification

# Skip OpenAI-dependent tests
./tests/run_api_sequence_tests.py --skip-openai

# Use a different API URL
./tests/run_api_sequence_tests.py --api-url http://api.example.com

# Enable debug logging
./tests/run_api_sequence_tests.py --debug
```

## Test Results

The test runner will output the results of each test suite and an overall success rate.
Detailed logs are also written to `api_sequence_tests.log`.

## Implementation Notes

1. The tests use real API calls, not mocks or simulations, to ensure that the sequence flows
   work properly in a real environment.

2. The tests are designed to be run against a real instance of the AI service, but can fall
   back to using mocks for components like OpenAI integration if necessary.

3. The tests include comprehensive error reporting to help identify issues in the API
   sequence implementation.

4. Rate limiting is implemented to prevent exceeding OpenAI API quotas during testing.

## Related Documentation

- [Sequence Diagram Documentation](../docs/architecture/sequence_diagram.md)
- [API Documentation](../docs/api/README.md)
