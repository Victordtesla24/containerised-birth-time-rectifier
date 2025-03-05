#!/bin/bash

# Unified Debug script for Playwright browser installation issues
# Works for both local and Docker environments

set -e

# Command line options
ENVIRONMENT="local" # Default to local environment
HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --docker)
      ENVIRONMENT="docker"
      shift
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
  echo "  --docker    Run diagnostic in Docker environment"
  echo "  --help      Show this help message"
  exit 0
fi

# Header with environment info
echo -e "\033[0;33m===== Playwright Browser Diagnostic Tool (Environment: ${ENVIRONMENT}) =====\033[0m"

# Function for local diagnostics
run_local_diagnostics() {
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

  # Test browser launch
  echo -e "\n\033[0;33m[7] Testing browser launch:\033[0m"
  echo 'const { chromium } = require("playwright"); (async () => { try { const browser = await chromium.launch(); console.log("Browser launched successfully"); await browser.close(); } catch (e) { console.error("Failed to launch browser:", e); } })()' > /tmp/test-browser.js
  node /tmp/test-browser.js
}

# Function for Docker diagnostics
run_docker_diagnostics() {
  # Run the diagnostic in a Docker container
  docker run --rm \
    -v $(pwd):/app \
    -w /app \
    mcr.microsoft.com/playwright:v1.40.0-jammy \
    bash -c '
      set -e
      cd /app

      echo -e "\033[0;33m[1] Checking environment:\033[0m"
      echo "Node version: $(node -v)"
      echo "NPM version: $(npm -v)"
      echo "OS: $(uname -a)"
      echo "Running in Docker container: Yes"

      echo -e "\n\033[0;33m[2] Checking package.json for Playwright version:\033[0m"
      if [ -f "package.json" ]; then
        PW_VERSION=$(grep -o "\"@playwright/test\": \"[^\"]*\"" package.json | cut -d"\"" -f4)
        echo "Installed Playwright version: $PW_VERSION"
      else
        echo "package.json not found!"
      fi

      echo -e "\n\033[0;33m[3] Installing dependencies:\033[0m"
      npm ci --legacy-peer-deps

      echo -e "\n\033[0;33m[4] Installing Playwright browsers with debug info:\033[0m"
      DEBUG=pw:install npx playwright install --with-deps chromium

      echo -e "\n\033[0;33m[5] Checking browser installation locations:\033[0m"
      BROWSER_DIRS=(
        "/ms-playwright"
        "/root/.cache/ms-playwright"
        "./node_modules/.cache/ms-playwright"
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

      echo -e "\n\033[0;33m[6] Verifying browser installation with Playwright:\033[0m"
      npx playwright browsers

      echo -e "\n\033[0;33m[7] Testing browser launch:\033[0m"
      echo "const { chromium } = require(\"playwright\"); (async () => { try { const browser = await chromium.launch(); console.log(\"Browser launched successfully\"); await browser.close(); } catch (e) { console.error(\"Failed to launch browser:\", e); } })()" > /tmp/test-browser.js
      node /tmp/test-browser.js

      echo -e "\n\033[0;32mDiagnostic complete. Use this information to troubleshoot Playwright issues.\033[0m"
    '
}

# Run diagnostics based on environment
if [ "$ENVIRONMENT" = "docker" ]; then
  run_docker_diagnostics
else
  run_local_diagnostics
fi

echo -e "\n\033[0;32mDiagnostic completed for ${ENVIRONMENT} environment.\033[0m"
