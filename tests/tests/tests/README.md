# Birth Time Rectification Test Suite

This directory contains the test suite for the Birth Time Rectification application. The tests are organized into different categories to ensure comprehensive test coverage.

## Directory Structure

```
tests/
├── components/         # Component tests
├── docker/             # Docker-related tests
├── integration/        # Integration tests
│   ├── birth_time_rectification/
│   ├── geocoding/
│   └── sequence_flows/
├── shell_scripts/      # Shell scripts for testing
├── test_data/          # Test data files
├── test_results/       # Test result storage
├── unit/               # Unit tests
│   ├── api/
│   ├── components/
│   ├── pages/
│   └── utils/
└── utils/              # Test utilities
    └── helpers/
```

## Test Types

### Unit Tests

Unit tests verify the functionality of individual functions, classes, or modules in isolation. They're located in the `tests/unit/` directory and organized by module.

### Integration Tests

Integration tests verify the interaction between multiple components or services. They're located in the `tests/integration/` directory and organized by feature.

### Component Tests

Component tests verify the functionality of specific components or services. They're located in the `tests/components/` directory.

### Docker Tests

Docker tests verify the application's behavior in a containerized environment. They're located in the `tests/docker/` directory.

## File Naming Convention

Test files follow a consistent naming pattern:

- Python: `test_<type>_<name>.py` (e.g., `test_unit_geocoding.py`)
- JavaScript/TypeScript: `test_<type>_<name>.js/ts/tsx` (e.g., `test_unit_component_LifeEventsQuestionnaire.tsx`)

Where:
- `<type>` is the test type (unit, integration, component, etc.)
- `<name>` is a descriptive name for the test

## Running Tests

### Running All Tests

To run all tests:

```bash
pytest tests/
```

### Running Specific Test Types

To run unit tests:

```bash
pytest tests/unit/
```

To run integration tests:

```bash
pytest tests/integration/
```

### Running Birth Time Rectification Integration Tests

The birth time rectification tests should be run in sequence due to their interdependencies. Use the provided script:

```bash
cd tests/integration/birth_time_rectification
python run_all_tests.py
```

This script runs the tests in the correct order:

1. Session initialization
2. Geocoding
3. Birth chart calculation
4. OpenAI verification
5. Dynamic questionnaire
6. Adaptive flow
7. Birth time rectification
8. Chart comparison
9. Chart interpretation
10. Chart export

### Running Shell Scripts

Test shell scripts are located in `tests/shell_scripts/`:

```bash
cd tests/shell_scripts/integration_tests
./run_tests.sh
```

## Test Data

Test data files are stored in `tests/test_data/`. These files include sample birth details, charts, and other data needed for testing.

## Test Results

Test results are stored in `tests/test_results/`. This directory contains logs, reports, and other output files generated during test runs.

## Test Utilities

Common test utilities are located in `tests/utils/`. These include helper functions, API clients, and other shared test code.

## Adding New Tests

When adding new tests:

1. Follow the established file naming convention
2. Place the test in the appropriate directory based on its type
3. Use the existing test utilities for common tasks
4. Add any necessary test data to `tests/test_data/`
5. Update this README if necessary

## Dependencies

The tests require the following dependencies:

- pytest
- pytest-asyncio (for async tests)
- playwright (for UI tests)

Install dependencies with:

```bash
pip install -r requirements-dev.txt
```
