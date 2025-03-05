#!/bin/bash

# Debug script for Playwright browser installation issues
set -e

echo -e "\033[0;33m===== Playwright Browser Diagnostic Tool =====\033[0m"

# Check environment
echo -e "\033[0;33m[1] Checking environment:\033[0m"
echo "Node version: $(node -v)"
echo "NPM version: $(npm -v)"
echo "OS: $(uname -a)"

# Check if running in Docker
if [ -f /.dockerenv ]; then
  echo "Running in Docker container: Yes"
else
  echo "Running in Docker container: No"
fi

# Check for important environment variables
echo -e "\n\033[0;33m[2] Checking environment variables:\033[0m"
echo "PLAYWRIGHT_BROWSERS_PATH: ${PLAYWRIGHT_BROWSERS_PATH:-Not set}"
echo "DOCKER_ENV: ${DOCKER_ENV:-Not set}"
echo "TEST_URL: ${TEST_URL:-Not set}"

# Check package.json for Playwright version
echo -e "\n\033[0;33m[3] Checking Playwright version in package.json:\033[0m"
if [ -f "package.json" ]; then
  PW_VERSION=$(grep -o '"@playwright/test": "[^"]*"' package.json | cut -d'"' -f4)
  echo "Installed Playwright version: $PW_VERSION"
else
  echo "package.json not found!"
fi

# Check for browser installation locations
echo -e "\n\033[0;33m[4] Checking browser installation directories:\033[0m"
BROWSER_DIRS=(
  "./.tmp/playwright-cache"
  "./node_modules/.cache/ms-playwright"
  "/ms-playwright"
  "/root/.cache/ms-playwright"
)

for dir in "${BROWSER_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    echo -e "\n\033[0;32mDirectory exists: $dir\033[0m"
    echo "Contents:"
    ls -la "$dir"

    # Look for browser binaries
    BROWSER_FILES=$(find "$dir" -type f -name "chrome*" -o -name "firefox*" -o -name "webkit*" -o -name "headless*" 2>/dev/null)
    if [ -n "$BROWSER_FILES" ]; then
      echo -e "\n\033[0;32mBrowser executables found in $dir:\033[0m"
      echo "$BROWSER_FILES"

      # Check permissions
      echo -e "\nPermissions:"
      ls -la $(echo "$BROWSER_FILES" | head -n1)
    else
      echo -e "\n\033[0;31mNo browser executables found in $dir\033[0m"
    fi
  else
    echo -e "\033[0;31mDirectory does not exist: $dir\033[0m"
  fi
done

# Try to install browsers with debug info
echo -e "\n\033[0;33m[5] Attempting to install Playwright browsers with debug info:\033[0m"
export DEBUG=pw:install
npx playwright install --with-deps chromium

echo -e "\n\033[0;33m[6] Final browser check after installation:\033[0m"
# Set browser path to look for browsers
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-./.tmp/playwright-cache}"
# Create directory if it doesn't exist
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"

# Check if browsers are installed
npx playwright browsers

echo -e "\n\033[0;32mDiagnostic complete. Use this information to troubleshoot Playwright issues.\033[0m"
