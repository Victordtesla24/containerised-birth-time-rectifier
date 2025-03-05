const { test, expect } = require('@playwright/test');

test('basic test', async ({ page }) => {
  console.log('Starting basic test...');
  await page.goto('https://playwright.dev/');
  const title = await page.title();
  console.log(`Page title: ${title}`);
  expect(title).toContain('Playwright');
});
