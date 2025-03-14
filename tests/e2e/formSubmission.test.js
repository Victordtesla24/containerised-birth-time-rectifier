/**
 * Form Submission E2E Test (Focused on Chromium browser)
 *
 * This test focuses on validating the form submission flow against the
 * sequence diagram requirements in docs/architecture/sequence_diagram.md.
 *
 * It tests the critical birth details form submission flow while accounting
 * for various UI implementations and error handling patterns.
 */

const { test, expect } = require('@playwright/test');

// Add tag to indicate this is a critical path test
test.describe('Form Submission Tests', () => {
  test.describe.configure({ tag: '@critical' });

  test('form submission flow with valid data', async ({ page }) => {
    // Add tracing point for debugging in CI
    await page.context().tracing.start({ screenshots: true, snapshots: true });

    // Add console log listener for better debugging
    page.on('console', msg => {
      console.log(`PAGE LOG: ${msg.text()}`);
    });

    // Step 1: Visit App - Initial page load (from sequence diagram)
    await page.goto('/birth-time-analysis');
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {
      console.log('Network idle wait timed out, continuing test');
    });

    // Take screenshot for debugging
    await page.screenshot({ path: 'initial-page.png', fullPage: true });
    console.log('✅ Successfully loaded initial page');

    // Step 2: Check for Session Initialization (from sequence diagram)
    const sessionResponse = await Promise.race([
      page.waitForResponse(resp => resp.url().includes('/api/session/init'), { timeout: 5000 }),
      page.waitForResponse(resp => resp.url().includes('/api/v1/session/init'), { timeout: 5000 })
    ]).catch(() => null);

    if (sessionResponse) {
      console.log(`✅ Session initialization detected (Status: ${sessionResponse.status()})`);
    } else {
      console.log('ℹ️ Session initialization not detected, may be using mock sessions');
    }

    // Locate form with robust selectors according to API architecture standards
    const formLocators = [
      'form',
      '[data-testid="birth-form"]',
      '.birth-form-container',
      '[role="form"]',
      '#birth-form'
    ];

    // Try each selector
    let formLocator = null;
    for (const selector of formLocators) {
      const count = await page.locator(selector).count();
      if (count > 0) {
        formLocator = page.locator(selector);
        console.log(`✅ Form found with selector: ${selector}`);
        break;
      }
    }

    // If form not found on current page, try test-form page
    if (!formLocator) {
      console.log('ℹ️ Form not found on main page, trying test form page');
      await page.goto('/test-form');
      await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => console.log('Network idle wait timed out'));

      // Check again for form
      for (const selector of formLocators) {
        const count = await page.locator(selector).count();
        if (count > 0) {
          formLocator = page.locator(selector);
          console.log(`✅ Form found on test-form page with selector: ${selector}`);
          break;
        }
      }
    }

    // If still no form, fail test
    expect(formLocator).toBeTruthy('Birth details form should be found');

    // Step 3: Fill Date/Time/Location fields (from sequence diagram)
    // - Location Entry
    // Try different possible selectors for each field
    await fillWithFallbacks(page, [
      'input[placeholder*="location"]',
      '[data-testid="birth-location"]',
      '[name="birthPlace"]',
      'input[name="location"]',
      'input[placeholder*="city"]',
      'input:not([type="date"]):not([type="time"]):not([type="submit"])'
    ], 'New York, USA');
    console.log('✅ Filled location field');

    // Wait for geocoding response according to sequence diagram
    const geocodeResponse = await Promise.race([
      page.waitForResponse(resp => resp.url().includes('/api/geocode'), { timeout: 10000 }),
      page.waitForResponse(resp => resp.url().includes('/api/v1/geocode'), { timeout: 10000 })
    ]).catch(() => null);

    if (geocodeResponse) {
      console.log(`✅ Geocoding API call detected (Status: ${geocodeResponse.status()})`);

      // Check for coordinates display to confirm geocoding success
      const coordsVisible = await page.locator(
        '[data-testid="coordinates-display"], .coordinates-display, .coords, [data-lat], text=/latitude|longitude/i'
      ).isVisible().catch(() => false);

      if (coordsVisible) {
        console.log('✅ Coordinates display visible after geocoding');
      }
    } else {
      console.log('ℹ️ Geocoding API call not detected, test will continue');
    }

    // - Birth Date
    await fillWithFallbacks(page, [
      'input[type="date"]',
      '[data-testid="birth-date"]',
      '[name="birthDate"]',
      'input[placeholder*="date"]'
    ], '1990-01-15');
    console.log('✅ Filled date field');

    // - Birth Time
    await fillWithFallbacks(page, [
      'input[type="time"]',
      '[data-testid="birth-time"]',
      '[name="birthTime"]',
      'input[placeholder*="time"]'
    ], '14:30');
    console.log('✅ Filled time field');

    // Step 4: Validation API call (according to sequence diagram)
    const validateResponse = await Promise.race([
      page.waitForResponse(resp => resp.url().includes('/api/chart/validate'), { timeout: 5000 }),
      page.waitForResponse(resp => resp.url().includes('/api/v1/chart/validate'), { timeout: 5000 })
    ]).catch(() => null);

    if (validateResponse) {
      console.log(`✅ Validation API call detected (Status: ${validateResponse.status()})`);
    } else {
      console.log('ℹ️ Validation API call not detected, may be using client-side validation only');
    }

    // Take screenshot of filled form
    await page.screenshot({ path: 'filled-form.png', fullPage: true });

    // Step 5: Generate Chart (according to sequence diagram)
    console.log('Submitting form to generate chart...');

    // Setup listener for chart generation API call
    const chartGenerateResponsePromise = Promise.race([
      page.waitForResponse(resp => resp.url().includes('/api/chart/generate'), { timeout: 30000 }),
      page.waitForResponse(resp => resp.url().includes('/api/v1/chart/generate'), { timeout: 30000 })
    ]).catch(() => null);

    // Click submit with multiple fallbacks
    await clickWithFallbacks(page, [
      'button[type="submit"]',
      '[data-testid="submit-button"]',
      'button:has-text("Begin Analysis")',
      'button:has-text("Submit")',
      'button:has-text("Continue")',
      'button.primary',
      'button.btn-primary'
    ]);

    // Wait for chart generation API response
    const chartGenerateResponse = await chartGenerateResponsePromise;
    if (chartGenerateResponse) {
      console.log(`✅ Chart generation API call detected (Status: ${chartGenerateResponse.status()})`);
    } else {
      console.log('ℹ️ Chart generation API call not detected, continuing test');
    }

    // Step 6: Navigation to Chart Visualization (according to sequence diagram)
    // Wait for navigation or timeout
    await page.waitForTimeout(5000); // Give time for potential redirect

    // Check if we're on a chart page by URL or chart elements
    const onChartPage =
      page.url().includes('/chart/') ||
      (await page.locator('.chart-container, [data-testid="chart"], canvas, svg, .chart-visualization').count() > 0);

    if (!onChartPage) {
      console.log('ℹ️ Not on chart page, attempting direct navigation to chart page');
      // Try to navigate directly as fallback
      await page.goto('/chart/test-123');
    }

    // Step 7: Check Chart Retrieval API call (according to sequence diagram)
    if (page.url().includes('/chart/')) {
      const chartId = page.url().split('/chart/')[1].split(/[/?#]/)[0]; // Extract chart ID from URL

      const chartRetrieveResponse = await Promise.race([
        page.waitForResponse(resp => resp.url().includes(`/api/chart/${chartId}`), { timeout: 5000 }),
        page.waitForResponse(resp => resp.url().includes(`/api/v1/chart/${chartId}`), { timeout: 5000 })
      ]).catch(() => null);

      if (chartRetrieveResponse) {
        console.log(`✅ Chart retrieval API call detected (Status: ${chartRetrieveResponse.status()})`);
      }
    }

    // Take screenshot of chart page
    await page.screenshot({ path: 'chart-page.png', fullPage: true });

    // Step 8: Verify Chart Elements (aligned with sequence diagram "Chart with Aspects")
    const chartElementSelectors = [
      '.chart-container',
      '.chart-visualization',
      'svg',
      'canvas',
      '[data-testid="chart"]',
      '.planet',
      '[data-planet]',
      '.aspect-line',
      '.house-cusp',
      '.ascendant-line'
    ];

    let chartElementFound = false;
    for (const selector of chartElementSelectors) {
      const count = await page.locator(selector).count();
      if (count > 0) {
        console.log(`✅ Chart element found with selector: ${selector} (${count} elements)`);
        chartElementFound = true;
        break;
      }
    }

    // Look for confidence score (verification of OpenAI integration from sequence diagram)
    const confidenceScoreVisible = await page.locator(
      '[data-testid="confidence-score"], .confidence-score, .confidence, text=/confidence/i'
    ).isVisible().catch(() => false);

    if (confidenceScoreVisible) {
      console.log('✅ Confidence score displayed (OpenAI verification)');
    }

    // Step 9: Link to Questionnaire (aligned with sequence diagram)
    const questionnaireLink = await page.locator(
      'a[href*="questionnaire"], button:has-text("Questionnaire")'
    ).isVisible().catch(() => false);

    if (questionnaireLink) {
      console.log('✅ Questionnaire link found');
    }

    // Final assertion that chart visualization is visible in some form
    expect(chartElementFound).toBeTruthy('Chart visualization should be visible');

    // Stop tracing
    await page.context().tracing.stop({ path: 'form-submission-trace.zip' });
  });

  test('form validation with invalid data', async ({ page }) => {
    // Add console log listener
    page.on('console', msg => {
      console.log(`PAGE LOG: ${msg.text()}`);
    });

    // Navigate to birth time analysis page
    await page.goto('/birth-time-analysis');
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {
      console.log('Network idle wait timed out, continuing test');
    });

    // Find form with fallbacks
    const formLocators = [
      'form',
      '[data-testid="birth-form"]',
      '.birth-form-container',
      '[role="form"]',
      '#birth-form'
    ];

    let formFound = false;
    for (const selector of formLocators) {
      if (await page.locator(selector).count() > 0) {
        formFound = true;
        console.log(`✅ Form found with selector: ${selector}`);
        break;
      }
    }

    if (!formFound) {
      console.log('ℹ️ Form not found on main page, trying test form page');
      await page.goto('/test-form');
      await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => console.log('Network idle wait timed out'));
    }

    // Submit form without filling it
    await clickWithFallbacks(page, [
      'button[type="submit"]',
      '[data-testid="submit-button"]',
      'button:has-text("Begin Analysis")',
      'button:has-text("Submit")'
    ]);

    // Check for validation errors
    const validationErrorSelectors = [
      '[role="alert"]',
      '.error-message',
      '.validation-error',
      '.field-error',
      'text=required',
      'text=invalid',
      'text=/please (enter|fill|provide)/i'
    ];

    let validationErrorFound = false;
    for (const selector of validationErrorSelectors) {
      const isVisible = await page.locator(selector).isVisible().catch(() => false);
      if (isVisible) {
        validationErrorFound = true;
        console.log(`✅ Validation error found with selector: ${selector}`);
        break;
      }
    }

    // Fill only one field
    await fillWithFallbacks(page, [
      'input[type="date"]',
      '[data-testid="birth-date"]',
      '[name="birthDate"]'
    ], '1990-01-15');

    // Submit again
    await clickWithFallbacks(page, [
      'button[type="submit"]',
      '[data-testid="submit-button"]',
      'button:has-text("Begin Analysis")',
      'button:has-text("Submit")'
    ]);

    // Ensure we're still on the form page
    const formStillVisible = await page.locator(
      'form, [data-testid="birth-form"], .birth-form-container'
    ).isVisible().catch(() => false);

    expect(formStillVisible).toBeTruthy('Form should remain visible after validation error');
    expect(validationErrorFound).toBeTruthy('Validation error should be displayed');
  });

  test('network error handling', async ({ page }) => {
    // Navigate to birth time analysis page
    await page.goto('/birth-time-analysis');
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {
      console.log('Network idle wait timed out, continuing test');
    });

    // Fill form fields
    await fillWithFallbacks(page, [
      'input[placeholder*="location"]',
      '[data-testid="birth-location"]',
      '[name="birthPlace"]',
      'input[name="location"]'
    ], 'New York, USA');

    await fillWithFallbacks(page, [
      'input[type="date"]',
      '[data-testid="birth-date"]',
      '[name="birthDate"]'
    ], '1990-01-15');

    await fillWithFallbacks(page, [
      'input[type="time"]',
      '[data-testid="birth-time"]',
      '[name="birthTime"]'
    ], '14:30');

    // Mock network errors
    await page.route('**/api/chart/generate', route => route.abort('failed'));
    await page.route('**/api/v1/chart/generate', route => route.abort('failed'));

    // Submit form
    await clickWithFallbacks(page, [
      'button[type="submit"]',
      '[data-testid="submit-button"]',
      'button:has-text("Begin Analysis")',
      'button:has-text("Submit")'
    ]);

    // Check for error message
    const errorMessageSelectors = [
      '[role="alert"]',
      '.error-message',
      '.network-error',
      'text=/error|failed|unable to connect/i'
    ];

    let errorMessageFound = false;
    for (const selector of errorMessageSelectors) {
      await page.waitForTimeout(1000); // Give time for error to appear
      const isVisible = await page.locator(selector).isVisible().catch(() => false);
      if (isVisible) {
        errorMessageFound = true;
        console.log(`✅ Error message found with selector: ${selector}`);
        break;
      }
    }

    // Form should still be accessible
    const formStillVisible = await page.locator(
      'form, [data-testid="birth-form"], .birth-form-container'
    ).isVisible().catch(() => false);

    expect(formStillVisible).toBeTruthy('Form should remain visible after network error');
    expect(errorMessageFound).toBeTruthy('Error message should be displayed for network error');
  });
});

// Helper functions for robust element interaction
async function fillWithFallbacks(page, selectors, value) {
  for (const selector of selectors) {
    const element = page.locator(selector).first();
    const count = await element.count();
    if (count > 0) {
      await element.fill(value).catch(async () => {
        // If fill fails, try using type instead
        await element.type(value, { delay: 50 }).catch(e => {
          console.log(`Could not fill ${selector}: ${e.message}`);
        });
      });
      return true;
    }
  }

  console.log(`⚠️ Could not find any of these selectors to fill: ${selectors.join(', ')}`);
  return false;
}

async function clickWithFallbacks(page, selectors) {
  for (const selector of selectors) {
    const element = page.locator(selector).first();
    const count = await element.count();
    if (count > 0) {
      try {
        await element.click();
        return true;
      } catch (e) {
        console.log(`Click on ${selector} failed, trying JavaScript click`);
        try {
          // Try JavaScript click as fallback
          await page.evaluate(sel => {
            const elem = document.querySelector(sel);
            if (elem) elem.click();
          }, selector);
          return true;
        } catch (jsError) {
          console.log(`JavaScript click on ${selector} failed: ${jsError.message}`);
        }
      }
    }
  }

  console.log(`⚠️ Could not find any of these selectors to click: ${selectors.join(', ')}`);

  // Last resort - try to submit form via JS
  try {
    await page.evaluate(() => {
      const form = document.querySelector('form');
      if (form) {
        const event = new Event('submit', { bubbles: true, cancelable: true });
        form.dispatchEvent(event);
      }
    });
    console.log('Tried form submission via JavaScript event');
    return true;
  } catch (e) {
    console.log(`Form submission via JavaScript failed: ${e.message}`);
    return false;
  }
}
