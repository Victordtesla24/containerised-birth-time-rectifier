// @ts-check
const { defineConfig, devices } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

/**
 * Determine the executable path with fallbacks
 * @returns {string|undefined} The path to the executable or undefined
 */
function getExecutablePath() {
  // First check environment variable
  if (process.env.EXECUTABLE_PATH && fs.existsSync(process.env.EXECUTABLE_PATH)) {
    console.log(`Using EXECUTABLE_PATH from environment: ${process.env.EXECUTABLE_PATH}`);
    return process.env.EXECUTABLE_PATH;
  }

  // When running in Docker, use a more dynamic approach to find executables
  if (process.env.DOCKER_ENV === 'true') {
    // Check for browsers in standard Playwright locations
    const rootDirs = [
      process.env.PLAYWRIGHT_BROWSERS_PATH || '/ms-playwright',
      '/ms-playwright',
      '/root/.cache/ms-playwright',
      path.join(process.cwd(), '.tmp/playwright-cache')
    ];

    console.log('Searching for browser executables in directories:', rootDirs);

    for (const rootDir of rootDirs) {
      if (!fs.existsSync(rootDir)) {
        console.log(`Directory does not exist: ${rootDir}`);
        continue;
      }

      // Try to find chromium executables recursively
      console.log(`Searching in ${rootDir}...`);
      const files = findExecutables(rootDir);

      if (files.length > 0) {
        console.log(`Found browser executable in Docker: ${files[0]}`);
        return files[0];
      }
    }

    // If no executable found, log warning
    console.warn('No browser executable found in Docker environment. Will rely on Playwright auto-install.');
  }

  // For local execution, let Playwright handle it automatically
  console.log('Using default browser executable path');
  return undefined;
}

/**
 * Find executable files recursively
 * @param {string} dir - Directory to search
 * @returns {string[]} - List of found executables
 */
function findExecutables(dir) {
  try {
    // If path doesn't exist, return empty array
    if (!fs.existsSync(dir)) return [];

    const files = [];
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        // Recursively search subdirectories
        const subFiles = findExecutables(fullPath);
        files.push(...subFiles);
      } else if (
        entry.isFile() &&
        (entry.name === 'headless_shell' ||
         entry.name === 'chrome' ||
         entry.name === 'chromium' ||
         entry.name === 'msedge' ||
         entry.name.includes('chrome')) &&
        isExecutable(fullPath)
      ) {
        // Check if this is a browser executable
        files.push(fullPath);
      }
    }

    return files;
  } catch (error) {
    console.error(`Error searching directory ${dir}:`, error);
    return [];
  }
}

/**
 * Check if a file is executable
 * @param {string} file - File path
 * @returns {boolean} - True if file is executable
 */
function isExecutable(file) {
  try {
    const stats = fs.statSync(file);
    // Check if file has execute permission
    return !!(stats.mode & 0o111);
  } catch (error) {
    return false;
  }
}

/**
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './tests/e2e',
  timeout: 180000,
  expect: {
    timeout: 60000
  },
  /* Run tests in files in parallel */
  fullyParallel: false,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 1,
  /* Opt out of parallel tests on CI. */
  workers: 1,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [['html'], ['list']],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.TEST_URL || 'http://localhost:3000',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'retain-on-failure',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Record video for visual regression tests */
    video: 'retain-on-failure',

    /* Enable built-in test isolation */
    testIsolation: true,

    testIdAttribute: 'data-testid',
    actionTimeout: 60000,
    navigationTimeout: 90000,
    waitForNavigation: 'networkidle',
    retries: 2,
    viewport: { width: 1280, height: 720 },
    ignoreHTTPSErrors: true,
    click: {
      force: true,
      timeout: 45000,
      trial: false
    },
    hasTouch: false,
    isMobile: false,
    bypassCSP: true,
    launchOptions: {
      slowMo: 50,
      headless: true,
      executablePath: getExecutablePath(),
      args: [
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-setuid-sandbox',
        '--no-sandbox',
        '--window-size=1280,720',
        '--allow-running-insecure-content',
        '--enable-automation',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding'
      ]
    }
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          headless: true,
          executablePath: getExecutablePath(),
          args: [
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-setuid-sandbox',
            '--no-sandbox',
            '--window-size=1280,720',
            '--allow-running-insecure-content',
            '--enable-automation',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
          ]
        }
      },
    },
  ],

  /* Run your local dev server before starting the tests */
  // Disable automatic web server start in Docker as we're handling this with docker-compose
  webServer: process.env.DOCKER_ENV ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 180000,
    stderr: 'pipe',
    stdout: 'pipe'
  },
});
