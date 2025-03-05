#!/bin/bash

# Debug script for Playwright browser installation issues in Docker
set -e

echo -e "\033[0;33m===== Playwright Browser Diagnostic Tool (Docker) =====\033[0m"

# Run the diagnostic in a Docker container
docker run --rm \
  -v $(pwd):/app \
  -w /app \
  mcr.microsoft.com/playwright:v1.40.0-jammy \
  bash -c "
    set -e
    cd /app

    echo -e '\033[0;33m[1] Checking environment:\033[0m'
    echo 'Node version: '\$(node -v)
    echo 'NPM version: '\$(npm -v)
    echo 'OS: '\$(uname -a)
    echo 'Running in Docker container: Yes'

    echo -e '\n\033[0;33m[2] Checking package.json for Playwright version:\033[0m'
    if [ -f 'package.json' ]; then
      PW_VERSION=\$(grep -o '\"@playwright/test\": \"[^\"]*\"' package.json | cut -d'\"' -f4)
      echo 'Installed Playwright version: '\$PW_VERSION
    else
      echo 'package.json not found!'
    fi

    echo -e '\n\033[0;33m[3] Installing dependencies:\033[0m'
    npm ci --legacy-peer-deps

    echo -e '\n\033[0;33m[4] Installing Playwright browsers with debug info:\033[0m'
    DEBUG=pw:install npx playwright install --with-deps chromium

    echo -e '\n\033[0;33m[5] Checking browser installation locations:\033[0m'
    BROWSER_DIRS=(
      '/ms-playwright'
      '/root/.cache/ms-playwright'
      './node_modules/.cache/ms-playwright'
    )

    for dir in \"\${BROWSER_DIRS[@]}\"; do
      if [ -d \"\$dir\" ]; then
        echo -e '\n\033[0;32mDirectory exists: '\$dir'\033[0m'
        echo 'Contents:'
        ls -la \"\$dir\"

        # Look for browser binaries
        BROWSER_FILES=\$(find \"\$dir\" -type f -name \"chrome*\" -o -name \"firefox*\" -o -name \"webkit*\" -o -name \"headless*\" 2>/dev/null)
        if [ -n \"\$BROWSER_FILES\" ]; then
          echo -e '\n\033[0;32mBrowser executables found in '\$dir':\033[0m'
          echo \"\$BROWSER_FILES\"

          # Check permissions
          echo -e '\nPermissions:'
          ls -la \$(echo \"\$BROWSER_FILES\" | head -n1)
        else
          echo -e '\n\033[0;31mNo browser executables found in '\$dir'\033[0m'
        fi
      else
        echo -e '\033[0;31mDirectory does not exist: '\$dir'\033[0m'
      fi
    done

    echo -e '\n\033[0;33m[6] Verifying browser installation with Playwright:\033[0m'
    npx playwright browsers

    echo -e '\n\033[0;33m[7] Testing browser launch:\033[0m'
    echo 'const { chromium } = require(\"playwright\"); (async () => { try { const browser = await chromium.launch(); console.log(\"Browser launched successfully\"); await browser.close(); } catch (e) { console.error(\"Failed to launch browser:\", e); } })()' > /tmp/test-browser.js
    node /tmp/test-browser.js

    echo -e '\n\033[0;32mDiagnostic complete. Use this information to troubleshoot Playwright issues.\033[0m'
  "

echo -e "\n\033[0;33mDocker diagnostic completed.\033[0m"
