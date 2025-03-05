// Basic Playwright test for Docker
const { test, expect } = require('@playwright/test');

/**
 * Simple test to verify Playwright is working in Docker
 * This test doesn't rely on node-fetch or other problematic dependencies
 */

test('Basic browser test in Docker', async ({ page }) => {
  console.log('Starting basic browser test in Docker');

  // Navigate to a public website that's reliable
  await page.goto('https://playwright.dev/');

  // Simple assertion to verify the page loaded
  const title = await page.title();
  console.log(`Page title: ${title}`);

  // Check if the page contains expected text
  const content = await page.textContent('body');
  expect(content).toContain('Playwright');

  console.log('Basic browser test completed successfully');
});
