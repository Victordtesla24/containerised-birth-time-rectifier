#!/bin/bash
set -e

echo "=== Playwright Browser Installation Diagnostic in Docker ==="
echo "This script will check the Playwright browser installation in a Docker container"

# Use the official Playwright Docker image
PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright:v1.40.0-jammy"

echo "Using Playwright Docker image: $PLAYWRIGHT_IMAGE"

# Run diagnostic in Docker
docker run --rm \
  -v "$(pwd):/app" \
  -w /app \
  --ipc=host \
  ${PLAYWRIGHT_IMAGE} \
  /bin/bash -c "
    echo '=== System Information ==='
    echo 'Node.js version:' && node --version
    echo 'NPM version:' && npm --version
    echo 'OS information:' && cat /etc/os-release

    echo '=== Checking Playwright Installation ==='
    cd /app

    echo 'Installing dependencies...'
    npm ci --legacy-peer-deps

    echo 'Checking Playwright version...'
    npx playwright --version

    echo 'Installing Playwright browsers...'
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright npx playwright install chromium --with-deps

    echo '=== Verifying Browser Installation ==='
    echo 'Checking browser installation directories...'
    ls -la /ms-playwright || echo 'Directory not found: /ms-playwright'

    echo 'Checking browser executables...'
    find /ms-playwright -name 'chrome*' -type f -executable || echo 'No Chrome executables found'

    echo '=== Running Browser Launch Test ==='
    echo 'Creating test script...'
    cat > /tmp/browser-test.js << 'EOF'
    const { chromium } = require('playwright');

    (async () => {
      console.log('Attempting to launch browser...');
      try {
        const browser = await chromium.launch({
          executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
          args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        console.log('Browser launched successfully!');
        const context = await browser.newContext();
        const page = await context.newPage();
        await page.goto('https://playwright.dev/');
        console.log('Page title:', await page.title());
        await browser.close();
        console.log('Browser closed successfully');
      } catch (error) {
        console.error('Failed to launch browser:', error);
        process.exit(1);
      }
    })();
    EOF

    echo 'Running browser launch test...'
    DEBUG=pw:browser* node /tmp/browser-test.js

    echo '=== Diagnostic Complete ==='
  "

DIAGNOSTIC_EXIT_CODE=$?

if [ $DIAGNOSTIC_EXIT_CODE -eq 0 ]; then
  echo "✅ Docker browser diagnostic completed successfully!"
else
  echo "❌ Docker browser diagnostic failed with exit code $DIAGNOSTIC_EXIT_CODE"
fi

exit $DIAGNOSTIC_EXIT_CODE
