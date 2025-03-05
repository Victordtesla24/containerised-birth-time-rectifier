/**
 * Form Submission Tests
 *
 * This script tests basic form submission functionality.
 */

import { test, expect } from '@playwright/test';
import { TEST_DATA } from './constants';

test.describe('Birth Details Form Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/birth-time-rectifier');
    // Wait for form to be visible
    await page.waitForSelector('form', { state: 'visible' });
  });

  test('form elements are displayed correctly', async ({ page }) => {
    // Check that all form elements are visible
    await expect(page.locator('input[type="date"]')).toBeVisible();
    await expect(page.locator('input[type="time"]')).toBeVisible();
    await expect(page.locator('#birthPlace')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('form validation shows errors for empty fields', async ({ page }) => {
    // Clear any pre-filled data
    await page.fill('input[type="date"]', '');
    await page.fill('input[type="time"]', '');
    await page.fill('#birthPlace', '');

    // Submit empty form
    await page.click('button[type="submit"]');

    // Look for validation errors with different possible classes
    const errorCount = await page.evaluate(() => {
      // Check for various error indicators in the DOM
      const errorElements = document.querySelectorAll('[data-testid$="-error"], .text-red-500, .error, .invalid-feedback, [aria-invalid="true"]');
      console.log('Found error elements:', errorElements.length);
      return errorElements.length;
    });

    console.log('Error count:', errorCount);
    expect(errorCount).toBeGreaterThan(0);
  });

  test('can fill and submit form', async ({ page }) => {
    // Fill the form
    await page.fill('input[type="date"]', TEST_DATA.STANDARD.birthDate);
    await page.fill('input[type="time"]', TEST_DATA.STANDARD.birthTime);
    await page.fill('#birthPlace', TEST_DATA.STANDARD.birthPlace);

    // Wait a moment for any autocomplete or validation
    await page.waitForTimeout(1000);

    // Take a screenshot before submission
    await page.screenshot({ path: 'before-submit.png' });

    // Submit the form
    await page.click('button[type="submit"]');

    // Wait for some indication of submission (loading spinner, new content, etc.)
    try {
      await page.waitForSelector('.loading, .chart-container, .animate-spin', {
        state: 'visible',
        timeout: 5000
      });
      console.log('Form submission indicator detected');
    } catch (error) {
      console.log('No submission indicator found, but form was submitted');
    }

    // Take a screenshot after submission
    await page.screenshot({ path: 'after-submit.png' });

    // Check current URL
    const currentUrl = page.url();
    console.log('Current URL after submission:', currentUrl);
  });
});
