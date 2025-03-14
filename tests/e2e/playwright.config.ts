import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Celestial Visualization testing
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/e2e',
  /* Maximum time one test can run for */
  timeout: 60000,
  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  /* Opt out of parallel tests on CI */
  workers: process.env.CI ? 1 : undefined,
  /* Reporter to use */
  reporter: [
    ['html', { open: 'never' }],
    ['list']
  ],
  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')` */
    baseURL: 'http://localhost:3000',
    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',
    /* Record video for visual tests */
    video: 'on-first-retry',
    /* Take screenshot on failure */
    screenshot: 'only-on-failure',
  },
  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        /* Chromium-specific settings for WebGL testing */
        launchOptions: {
          args: [
            '--use-gl=egl',
            '--enable-webgl',
            '--enable-features=WebGLDraftExtensions',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process'
          ]
        }
      },
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        /* Firefox-specific settings */
        launchOptions: {
          firefoxUserPrefs: {
            'webgl.force-enabled': true,
            'gfx.webrender.all': true
          }
        }
      },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    /* Test against mobile viewports */
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  /* Run local development server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
    stderr: 'pipe',
  },
  /* Global setup to install Percy for visual regression testing */
  globalSetup: './tests/e2e/global-setup.ts',
});
