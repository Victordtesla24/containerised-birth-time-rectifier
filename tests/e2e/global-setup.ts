import { FullConfig } from '@playwright/test';

/**
 * Global setup for Playwright tests
 * This runs once before all tests
 */
async function globalSetup(config: FullConfig) {
  // Set up Percy if PERCY_TOKEN is available
  if (process.env.PERCY_TOKEN) {
    console.log('Setting up Percy for visual regression testing...');
    try {
      // This would normally import and initialize Percy
      // For now, we'll just log that it would be set up
      console.log('Percy would be initialized here with token');
    } catch (error) {
      console.error('Failed to initialize Percy:', error);
    }
  } else {
    console.log('Percy token not found. Visual regression tests will use local snapshots only.');
  }

  // Set up any other global test dependencies here
  console.log('Setting up test environment...');

  // Example: Set up mock data or environment variables
  process.env.TEST_MODE = 'true';
  process.env.NEXT_PUBLIC_ENABLE_HIGH_QUALITY = 'true';

  console.log('Global setup complete');
}

export default globalSetup;
