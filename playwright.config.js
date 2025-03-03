// @ts-check
const { defineConfig, devices } = require('@playwright/test');

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
    baseURL: 'http://localhost:3000',

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
      args: [
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-setuid-sandbox',
        '--no-sandbox',
        '--window-size=1280,720'
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
          args: [
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-setuid-sandbox',
            '--no-sandbox',
            '--window-size=1280,720'
          ]
        }
      },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 180000,
    stderr: 'pipe',
    stdout: 'pipe'
  },
});
