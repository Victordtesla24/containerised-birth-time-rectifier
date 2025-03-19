# Questionnaire Integration Tests

This document outlines the integration tests for the questionnaire functionality in the birth time rectification system.

## Overview

These tests validate the questionnaire functionality using **real API calls** to ensure the system works correctly with actual dependencies rather than mocks or stubs. This approach validates:

1. Questionnaire data processing with actual calculations
2. Questionnaire submission flows with real OpenAI API integration
3. Response handling with real data structures
4. End-to-end questionnaire flow

## Test Cases

The test suite includes:

1. **Basic Question Generation** - Tests that a single question can be generated with valid structure
2. **Question Generation with Previous Answers** - Tests that follow-up questions are influenced by previous responses
3. **Full Questionnaire Flow** - Tests a complete flow with multiple questions and answers

## Docker Container Persistence

The tests are designed to run in Docker containers and maintain persistence across rebuilds using:

1. A dedicated persistent volume (`persistent_tests`) defined in docker-compose.yml
2. Backup scripts to ensure tests are preserved
3. Automatic test restoration when containers are rebuilt

## Running the Tests

To run the questionnaire tests:

```bash
# Run the tests and backup to persistent volume
./scripts/run_questionnaire_tests.sh

# Only backup the tests (if modified)
./scripts/backup_questionnaire_tests.sh
```

## Requirements

- Docker and docker-compose must be installed and running
- An OpenAI API key must be available in the container environment
- All test dependencies must be installed in the container

## No Mocks Policy

These tests follow a strict "no mocks" policy, meaning:

- NO MOCK UPS
- NO FALL BACKS
- NO STUBS
- STRICTLY REAL AND ACTUAL API CALLS

This ensures that our validation is against the actual services the system will interact with in production.

## Technical Implementation

The tests use:

1. Real OpenAI service for AI-based question generation
2. Actual ephemeris data for astrological calculations
3. Real geocoding for location resolution
4. Full end-to-end questionnaire processing
5. Real validation of response data structures

## Troubleshooting

If tests fail, check:

1. OpenAI API key validity and quota
2. Network connectivity from container
3. Container dependencies (Redis, etc.)
4. Error logs in the container
