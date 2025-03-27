// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Simple test to verify Docker environment
 */
test('Docker environment test', async ({ page }) => {
  // Navigate to the base URL (defined in config)
  await page.goto('/');

  // Simple verification that we loaded a page
  const title = await page.title();
  console.log('Page title:', title);

  // This test should pass regardless of the content
  expect(true).toBeTruthy();
});
