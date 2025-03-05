#!/bin/bash

# Simple script to run a basic test to verify Playwright is working
set -e  # Exit immediately if a command exits with a non-zero status

echo -e "\033[0;33mSetting up Playwright for a simple test...\033[0m"

# Run the test in a Docker container
echo -e "\033[0;33mRunning simple test in Docker container...\033[0m"

# Create simple test file
cat > simple-test.js << 'EOL'
const { test, expect } = require('@playwright/test');

test('basic test', async ({ page }) => {
  console.log('Starting basic test...');
  await page.goto('https://playwright.dev/');
  const title = await page.title();
  console.log(`Page title: ${title}`);
  expect(title).toContain('Playwright');
});
EOL

# Create a simple playwright config
cat > playwright.config.simple.js << 'EOL'
// @ts-check
const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './',
  testMatch: '**/*.js',
  use: {
    headless: true,
    launchOptions: {
      args: [
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--no-sandbox'
      ]
    }
  },
  reporter: 'list',
});
EOL

# Run the test in Docker
echo -e "\033[0;33mRunning test in Docker...\033[0m"
docker run --rm \
  -v $(pwd):/app \
  -w /app \
  mcr.microsoft.com/playwright:v1.40.0-jammy \
  bash -c "cd /app && \
    ls -la && \
    echo 'Installing dependencies...' && \
    npm ci --legacy-peer-deps && \
    echo 'Installing Playwright browsers...' && \
    npx playwright install chromium --with-deps && \
    echo 'Running test with debug info...' && \
    DEBUG=pw:browser* npx playwright test -c playwright.config.simple.js"

# Check result
TEST_EXIT_CODE=$?
if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo -e "\033[0;32m✅ Simple test completed successfully!\033[0m"
else
  echo -e "\033[0;31m❌ Simple test failed.\033[0m"
fi

# Cleanup
rm -f simple-test.js playwright.config.simple.js

exit $TEST_EXIT_CODE
