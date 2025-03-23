#!/bin/bash
set -e

# Default settings
OPTIMIZED=false
PLAYWRIGHT_VERSION="v1.40.0-jammy"
INSTALL_BROWSERS=true
DEBUG=true
HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --optimized)
      OPTIMIZED=true
      shift
      ;;
    --no-browser-install)
      INSTALL_BROWSERS=false
      shift
      ;;
    --no-debug)
      DEBUG=false
      shift
      ;;
    --playwright-version)
      PLAYWRIGHT_VERSION="$2"
      shift 2
      ;;
    --help)
      HELP=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      HELP=true
      shift
      ;;
  esac
done

# Show help message
if [ "$HELP" = true ]; then
  echo "Usage: $0 [OPTIONS]"
  echo "Options:"
  echo "  --optimized           Run optimized version (skips browser installation if possible)"
  echo "  --no-browser-install  Skip browser installation"
  echo "  --no-debug            Disable debug mode"
  echo "  --playwright-version  Specify Playwright Docker image version (default: v1.40.0-jammy)"
  echo "  --help                Show this help message"
  exit 0
fi

# Set Playwright image
PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright:${PLAYWRIGHT_VERSION}"

# Set options for debug mode
DEBUG_OPTIONS=""
if [ "$DEBUG" = true ]; then
  DEBUG_OPTIONS="-e DEBUG=pw:browser*"
fi

# Display settings
echo "Starting Docker Playwright test..."
echo "Mode: $([ "$OPTIMIZED" = true ] && echo "Optimized" || echo "Standard")"
echo "Playwright Image: $PLAYWRIGHT_IMAGE"
echo "Install Browsers: $([ "$INSTALL_BROWSERS" = true ] && echo "Yes" || echo "No")"
echo "Debug Mode: $([ "$DEBUG" = true ] && echo "Enabled" || echo "Disabled")"

# Prepare browser installation command
BROWSER_INSTALL_CMD=""
if [ "$INSTALL_BROWSERS" = true ]; then
  echo "Will install Playwright browsers"
  BROWSER_INSTALL_CMD="echo 'Installing Playwright browsers...' && npx playwright install chromium --with-deps &&"
fi

# Prepare Playwright test package installation
TEST_INSTALL_CMD="npm install @playwright/test --save-dev &&"
if [ "$OPTIMIZED" = true ]; then
  echo "Running in optimized mode, skipping package reinstall if possible"
  TEST_INSTALL_CMD="npm list @playwright/test || npm install @playwright/test --save-dev &&"
fi

# Check if the config file exists
CONFIG_PATH="playwright.docker.config.js"
if [ ! -f "$CONFIG_PATH" ] && [ -f "config/playwright.docker.config.js" ]; then
  CONFIG_PATH="config/playwright.docker.config.js"
  echo "Using config file at: $CONFIG_PATH"
elif [ ! -f "$CONFIG_PATH" ]; then
  echo "❌ ERROR: Config file not found at $CONFIG_PATH or config/playwright.docker.config.js"
  exit 1
fi

# Check if a test file exists, create a simple one if not
DOCKER_TEST_DIR="tests"
DOCKER_TEST_FILE="${DOCKER_TEST_DIR}/docker-test.js"

if [ ! -d "$DOCKER_TEST_DIR" ]; then
  echo "Creating tests directory..."
  mkdir -p "$DOCKER_TEST_DIR"
fi

if [ ! -f "$DOCKER_TEST_FILE" ]; then
  echo "No docker-test.js found. Creating a sample test file..."
  cat > "$DOCKER_TEST_FILE" << EOL
// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Simple test to verify Docker environment
 */
test('Docker environment test', async ({ page }) => {
  // Navigate to the base URL (defined in config)
  await page.goto('/');

  // Simple verification that we loaded a page
  const title = await page.title();
  console.log('Page title:', title);

  // This test should pass regardless of the content
  expect(true).toBeTruthy();
});
EOL
  echo "Created sample test file at $DOCKER_TEST_FILE"
fi

# Run the test in Docker
echo "Running Docker container..."
docker run --rm \
  -v "$(pwd):/app" \
  -w /app \
  --ipc=host \
  ${DEBUG_OPTIONS} \
  ${PLAYWRIGHT_IMAGE} \
  /bin/bash -c "cd /app && \
    echo 'Installing dependencies...' && \
    npm ci --legacy-peer-deps && \
    ${TEST_INSTALL_CMD} \
    echo 'Creating constraints file to prevent pydantic version conflicts...' && \
    echo 'pydantic!=2.0.0,!=2.0.1,<3.0.0,>=1.7.4' > /tmp/constraints.txt && \
    pip install --no-cache-dir -r requirements.txt -c /tmp/constraints.txt && \
    ${BROWSER_INSTALL_CMD} \
    echo 'Running Docker-specific test...' && \
    npx playwright test -c ${CONFIG_PATH}"

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "✅ Docker Playwright test completed successfully!"
else
  echo "❌ Docker Playwright test failed with exit code $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE
