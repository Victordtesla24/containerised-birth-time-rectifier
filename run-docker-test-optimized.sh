#!/bin/bash
set -e

echo "Starting optimized Docker Playwright test..."

# Use the official Playwright Docker image with browsers pre-installed
PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright:v1.40.0-jammy"

# Run the test in Docker
docker run --rm \
  -v "$(pwd):/app" \
  -w /app \
  --ipc=host \
  ${PLAYWRIGHT_IMAGE} \
  /bin/bash -c "cd /app && \
    echo 'Installing dependencies...' && \
    npm ci --legacy-peer-deps && \
    echo 'Running Docker-specific test...' && \
    DEBUG=pw:browser* npx playwright test -c playwright.docker.config.js"

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "✅ Docker Playwright test completed successfully!"
else
  echo "❌ Docker Playwright test failed with exit code $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE
