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
  DEBUG_OPTIONS="DEBUG=pw:browser*"
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

# Run the test in Docker
echo "Running Docker container..."
docker run --rm \
  -v "$(pwd):/app" \
  -w /app \
  --ipc=host \
  ${PLAYWRIGHT_IMAGE} \
  /bin/bash -c "cd /app && \
    echo 'Installing dependencies...' && \
    npm ci --legacy-peer-deps && \
    ${BROWSER_INSTALL_CMD} \
    echo 'Running Docker-specific test...' && \
    ${DEBUG_OPTIONS} npx playwright test -c playwright.docker.config.js"

TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo "✅ Docker Playwright test completed successfully!"
else
  echo "❌ Docker Playwright test failed with exit code $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE
