# Integration Tests for Birth Time Rectifier

This directory contains integration tests that verify the proper functioning of the Birth Time Rectifier application through its main UI/UX flow.

## Test Coverage

These tests cover the complete UI/UX flow as depicted in the flowchart:

```
A[Landing Page] --> B[Birth Details Form]
B --> C{Valid Details?}
C -->|Yes| D[Initial Chart Generation]
C -->|No| B
D --> E[Real Time Questionnaire]
E --> F[AI Analysis]
F --> G{Confidence > 80%?}
G -->|Yes| H[Results Page]
G -->|No| I[Additional Questions]
I --> F
H --> J[Chart Visualization]
J --> K[Export/Share]
```

The tests are organized into 4 files, each covering a specific segment of the flow:

1. `01-landing-to-form.test.tsx`: Tests navigation from landing page to birth details form
2. `02-form-to-chart-generation.test.tsx`: Tests form validation and initial chart generation
3. `03-questionnaire-to-analysis.test.tsx`: Tests questionnaire interaction and AI analysis
4. `04-results-to-export.test.tsx`: Tests results page and export/share functionality

## Requirements

To run these tests, both the frontend and AI services must be running. The tests will automatically check for running services and provide options to start them if they're not running.

## Running the Tests

Use the provided shell script to run the integration tests:

```bash
./run-integration-tests.sh
```

This script will:
1. Check if required services are running
2. Offer to start the services if they're not running
3. Run the static tests first
4. Run the integration tests if static tests pass

## Manual Test Execution

If you prefer to run tests manually, you can use:

```bash
# Run all integration tests
npm test -- --testMatch=**/__tests__/integration/**/*test.{ts,tsx}

# Run a specific integration test
npm test -- --testMatch=**/__tests__/integration/01-landing-to-form.test.tsx
```

## Testing Strategy

These integration tests focus on real-world user interactions and service integration rather than just unit functionality. They verify that:

1. UI components interact properly with each other
2. API calls are made correctly
3. Data flows through the application as expected
4. User interactions trigger the appropriate responses
5. Error states are handled properly

## Mocking Strategy

While these are integration tests, they use strategic mocking to ensure tests are reliable and fast:

- External services like geocoding are mocked
- Network requests use MSW (Mock Service Worker)
- Browser APIs like window.print and navigator.share are mocked
- Session storage is mocked with test data

## Troubleshooting

If tests fail, check:

1. Are both services running? (Frontend on port 3000, AI service on port 8000)
2. Is there a network issue preventing services from communicating?
3. Have there been UI changes that affected test selectors?
4. Have API contracts changed? 