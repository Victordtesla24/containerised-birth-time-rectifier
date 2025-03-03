# Birth Time Rectifier Testing Framework

This document provides a comprehensive overview of the testing framework for the Birth Time Rectifier application.

## Testing Philosophy

Our testing strategy follows a comprehensive pyramid approach:
1. **Unit Tests**: Testing individual components in isolation
2. **Integration Tests**: Testing interactions between components
3. **End-to-End Tests**: Testing the full application flow

## Test Coverage Goals

We aim for the following minimum test coverage:
- Backend: 80% code coverage
- Frontend: 70% code coverage
- Critical paths: 100% coverage

## Test Structure

### Backend Tests
- `tests/test_astro_calculator.py`: Tests for astrological calculations
- `tests/test_api_endpoints.py`: Tests for API endpoints
- `tests/test_ai_rectification.py`: Tests for AI rectification models
- `tests/test_ascendant_ketu_calculation.py`: Tests for critical Ketu and Ascendant calculations
- `tests/integration/`: Integration tests between backend components

### Frontend Tests
- `__tests__/components/`: Tests for React components
- `__tests__/pages/`: Tests for Next.js pages
- `__tests__/api/`: Tests for API client code
- `__tests__/integration/`: Integration tests for frontend flows

## Running Tests

### Backend Tests

```bash
# Run all backend tests
cd /path/to/project
pytest

# Run specific test file
pytest tests/test_astro_calculator.py

# Run with coverage
pytest --cov=ai_service tests/
```

### Frontend Tests

```bash
# Run all frontend tests
npm test

# Run specific test
npm test -- -t "BirthDetailsForm"

# Run with coverage
npm test -- --coverage
```

### End-to-End Tests

```bash
# Run end-to-end tests
npm run test:e2e
```

## Continuous Integration

Our CI pipeline (GitHub Actions) automatically runs tests on:
- Pull requests to main branch
- Commits to main branch

The pipeline:
1. Sets up the environment
2. Installs dependencies
3. Runs backend tests with coverage
4. Runs frontend tests with coverage
5. Generates and stores test reports
6. Fails the build if coverage thresholds are not met

## Test Report Location

Test reports are stored in:
- Backend: `tests/results/backend-coverage/`
- Frontend: `coverage/`

## Writing New Tests

When adding new features or fixing bugs:
1. Write tests before implementing the feature (TDD approach)
2. Ensure tests cover both happy paths and edge cases
3. For UI components, test both rendering and interactions
4. For API endpoints, test both valid and invalid inputs
5. For calculations, test with known reference data

## Critical Paths Testing

The following paths are considered critical and require 100% test coverage:
1. Birth details form submission
2. Chart generation with correct Ketu and Ascendant calculations
3. Questionnaire flow
4. Birth time rectification process
5. User authentication (when implemented)

## Mocking Strategy

- Backend: Use pytest fixtures and mocks for external dependencies
- Frontend: Use Jest mocks and React Testing Library for UI components
- Both: Use mock data to simulate API responses

## Automated Test Reports

Test reports are automatically generated and published:
1. Coverage reports as HTML
2. JUnit XML reports for CI integration
3. Performance test results for critical paths

## Historical Test Results

Historical test results are tracked and analyzed for:
1. Regression identification
2. Performance trend analysis
3. Coverage trend analysis

This comprehensive testing framework ensures the reliability and accuracy of the Birth Time Rectifier application.
