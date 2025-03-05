# Running Tests Outside Docker

This guide explains how to run the Birth Time Rectifier application tests directly on your host machine instead of using Docker containers.

## Prerequisites

1. Node.js and npm installed on your machine
2. Playwright installed globally or locally
3. Application running locally or in Docker

## Setting Up Playwright

If you haven't already installed Playwright:

```bash
# Install Playwright
npm install -D @playwright/test

# Install browsers
npx playwright install
```

## Running the Tests

### API Tests

These tests check the API endpoints directly without browser interaction:

```bash
# Run all API tests
npx playwright test tests/e2e/api.spec.js

# Run a specific test
npx playwright test -g "health endpoint"
```

### UI Form Tests

These tests check the form behavior:

```bash
# Run all form tests
npx playwright test tests/e2e/form.spec.js

# Run with browser visible
npx playwright test tests/e2e/form.spec.js --headed

# Run in debug mode
npx playwright test tests/e2e/form.spec.js --debug
```

### Checking Test Results

After running the tests, you can view the HTML report:

```bash
npx playwright show-report
```

## Test Structure

The tests are organized as follows:

1. **API Tests** (`tests/e2e/api.spec.js`): Direct API endpoint testing
2. **Form Tests** (`tests/e2e/form.spec.js`): Basic form submission testing
3. **Full E2E Tests** (`tests/e2e/chart.spec.js`): Complete application flow tests

## Connecting to Local or Docker Services

The tests are configured to connect to `http://localhost:3000` by default. To change this:

```bash
# Connect to a different URL
TEST_URL=http://your-custom-url npx playwright test
```

## Troubleshooting

Common issues and solutions:

1. **Browser not found**: Run `npx playwright install` to install the required browsers
2. **Connection errors**: Ensure the application is running (either locally or in Docker)
3. **Element not found**: Check if the selectors in the tests match your current UI

## Test Data

Test data is defined in `tests/e2e/constants.js`. You can modify this file to change the test data.
