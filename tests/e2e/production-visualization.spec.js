/**
 * Production Environment UI/UX Visualization Tests
 *
 * Tests advanced visualizations and fancy UI effects present in the production environment
 * while still ensuring tests pass in all environments (dev, test, production)
 */

import { test, expect } from '@playwright/test';
import { TEST_DATA } from './constants';
import {
  detectEnvironment,
  enableTestMode,
  adaptSelectors,
  prepareAdvancedVisualization,
  waitForAnimations
} from './utils/environment-helpers';

// Base selectors for the application (these will be adapted based on environment)
const baseSelectors = {
  // Form selectors
  birthDetailsForm: 'form, [data-testid="birth-form"]',
  dateInput: 'input[type="date"], [data-testid="birth-date"], [name="birthDate"]',
  timeInput: 'input[type="time"], [data-testid="birth-time"], [name="birthTime"]',
  locationInput: 'input[placeholder*="location"], [data-testid="birth-location"], [name="birthPlace"]',
  submitButton: 'button[type="submit"], [data-testid="submit-button"]',

  // Chart visualization selectors
  chartVisualization: '.chart-container, .chart-visualization, [data-testid="chart-visualization"]',
  planets: '.planet, [data-testid^="planet-"]',
  houses: '.house, [data-testid^="house-"]',
  ascendant: '.ascendant, [data-testid="ascendant"]',
  tooltip: '.entity-details, .tooltip, [data-testid="tooltip"]',

  // Results section
  rectificationResults: '.rectified-chart, [data-testid="rectification-results"]',
  confidenceScore: '[data-testid="confidence-score"]',
  comparisonView: '.chart-comparison, [data-testid="chart-comparison"]',

  // Controls
  zoomControl: '[data-testid="zoom-toggle"], [data-testid="zoom-control"]',
  renderModeSelect: '[data-testid="render-mode-select"]',
  effectsToggle: '[data-testid="effects-toggle"]',
  comparisonToggle: '[data-testid="comparison-toggle"]'
};

test.describe('Production Environment UI/UX Testing', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/');

    // Enable test mode to help with testing
    await enableTestMode(page);

    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle');
    await waitForAnimations(page);
  });

  test('should handle fancy visualizations correctly in all environments', async ({ page }) => {
    // Detect current environment (dev, test, prod)
    const { env, hasAdvancedUI } = await detectEnvironment(page);
    console.log(`Testing in "${env}" environment with ${hasAdvancedUI ? 'advanced' : 'standard'} UI`);

    // Get environment-specific selectors
    const selectors = await adaptSelectors(page, baseSelectors);

    // If we have advanced visualizations, prepare them for testing
    if (hasAdvancedUI) {
      await prepareAdvancedVisualization(page);
    }

    // ===== TEST FORM SUBMISSION =====
    console.log('Testing birth details form submission...');

    // Check if we're on the form already, otherwise navigate to it
    const isOnFormPage = await page.isVisible(selectors.birthDetailsForm);
    if (!isOnFormPage) {
      // Try to find and click a "Get Started" button
      const getStartedVisible = await page.isVisible('button:has-text("Get Started"), [data-testid="get-started-button"]');
      if (getStartedVisible) {
        await page.click('button:has-text("Get Started"), [data-testid="get-started-button"]');
        await waitForAnimations(page);
      } else {
        // Navigate directly to form page
        await page.goto('/test-form');
      }

      await page.waitForSelector(selectors.birthDetailsForm);
    }

    // Fill in the form with test data
    await page.fill(selectors.dateInput, TEST_DATA.STANDARD.birthDate);
    await page.fill(selectors.timeInput, TEST_DATA.STANDARD.birthTime);
    await page.fill(selectors.locationInput, TEST_DATA.STANDARD.birthPlace);

    // Take a screenshot of the filled form
    await page.screenshot({ path: `form-${env}-ui.png` });

    // Submit the form
    await page.click(selectors.submitButton);
    console.log('Form submitted...');

    // Wait for the chart visualization page to load
    await page.waitForSelector(selectors.chartVisualization, { timeout: 30000 });
    await waitForAnimations(page);
    console.log('Chart visualization loaded');

    // Take a screenshot of the chart visualization
    await page.screenshot({ path: `chart-${env}-ui.png` });

    // ===== TEST CHART VISUALIZATION INTERACTIONS =====
    console.log('Testing chart visualization interactions...');

    // Check for render mode controls (enhanced UI feature)
    const hasRenderModeControl = await page.isVisible(selectors.renderModeSelect);
    if (hasRenderModeControl) {
      // Test different render modes
      console.log('Testing render mode switching');
      await page.selectOption(selectors.renderModeSelect, 'enhanced');
      await waitForAnimations(page);
      await page.screenshot({ path: `chart-enhanced-${env}.png` });

      if (env === 'prod' || hasAdvancedUI) {
        // Try 3D mode if available
        await page.selectOption(selectors.renderModeSelect, '3d');
        await waitForAnimations(page);
        await page.screenshot({ path: `chart-3d-${env}.png` });
      }
    }

    // Test effects toggle if present (enhanced UI feature)
    const hasEffectsToggle = await page.isVisible(selectors.effectsToggle);
    if (hasEffectsToggle) {
      console.log('Testing effects toggle');
      await page.check(selectors.effectsToggle);
      await waitForAnimations(page);
      await page.screenshot({ path: `chart-effects-on-${env}.png` });
    }

    // Test planet interactions
    const planetElements = page.locator(selectors.planets);
    const planetCount = await planetElements.count();
    console.log(`Found ${planetCount} planet elements`);

    // Only test if we find planets
    if (planetCount > 0) {
      // Hover over the first planet to test tooltip
      await planetElements.first().hover();
      await page.waitForTimeout(500); // Brief wait for tooltip

      // Check if tooltip is visible
      const tooltipVisible = await page.isVisible(selectors.tooltip);
      console.log(`Planet tooltip visible: ${tooltipVisible}`);

      if (tooltipVisible) {
        await page.screenshot({ path: `planet-tooltip-${env}.png` });
      }
    }

    // Test comparison view toggle if present
    const hasComparisonToggle = await page.isVisible(selectors.comparisonToggle);
    if (hasComparisonToggle) {
      console.log('Testing comparison view toggle');
      await page.check(selectors.comparisonToggle);
      await waitForAnimations(page);
      await page.screenshot({ path: `comparison-view-${env}.png` });

      // Verify both original and rectified charts are shown
      const comparisonVisible = await page.isVisible(selectors.comparisonView);
      expect(comparisonVisible).toBeTruthy();
    }

    // ===== TEST RECTIFICATION RESULTS =====
    console.log('Testing rectification results...');

    // Check for rectification results
    const hasResults = await page.isVisible(selectors.rectificationResults);
    expect(hasResults).toBeTruthy();

    // Check confidence score is present
    const confidenceElement = page.locator(selectors.confidenceScore);
    const confidenceText = await confidenceElement.textContent();
    console.log(`Confidence score: ${confidenceText}`);

    // Extract numeric value from confidence text
    const confidenceValue = parseInt(confidenceText.replace(/\D/g, ''));
    expect(confidenceValue).toBeGreaterThan(0);

    // ===== TEST EXPORT FUNCTIONALITY =====
    console.log('Testing export functionality...');

    // Check for export button
    const exportButtonVisible = await page.isVisible('[data-testid="export-pdf"], button:has-text("Export")');
    if (exportButtonVisible) {
      // Click export button (but don't wait for download in tests)
      await page.click('[data-testid="export-pdf"], button:has-text("Export")');
      console.log('Export button clicked');

      // Check for any success indication
      await page.waitForTimeout(1000);
      const successVisible = await page.isVisible('.export-success, .success-message, text=success');
      console.log(`Export success indicator visible: ${successVisible}`);
    }

    // Test completed successfully
    console.log(`Production UI/UX testing completed in ${env} environment`);
  });

  test('should handle fancy visualizations in production environment', async ({ page }) => {
    // Skip this test if we're not in production environment
    const { env, hasAdvancedUI } = await detectEnvironment(page);
    if (env !== 'prod' && !hasAdvancedUI) {
      console.log('Skipping production-specific test in non-production environment');
      test.skip();
    }

    console.log('Running production-specific visualization test');

    // Get environment-specific selectors
    const selectors = await adaptSelectors(page, baseSelectors);

    // Prepare advanced visualizations
    await prepareAdvancedVisualization(page);

    // Navigate directly to chart page with test ID
    await page.goto('/chart/test-123');
    await page.waitForSelector(selectors.chartVisualization);
    await waitForAnimations(page);

    // Production environments should have advanced visualization controls
    const hasControls = await page.isVisible(selectors.renderModeSelect) ||
                         await page.isVisible(selectors.effectsToggle);

    expect(hasControls).toBeTruthy();

    // Check for 3D/WebGL components in production
    const hasCanvas = await page.locator('canvas').count() > 0;
    expect(hasCanvas).toBeTruthy();

    // Production should have fancy cosmic background effects
    const hasCosmicEffects = await page.evaluate(() => {
      return (
        document.querySelector('.cosmic-background') !== null ||
        document.querySelector('.stars-container') !== null ||
        document.body.classList.contains('cosmic-effects-enabled') ||
        document.documentElement.classList.contains('cosmic-bg')
      );
    });

    expect(hasCosmicEffects).toBeTruthy();

    // Take screenshot of production visualization
    await page.screenshot({ path: 'production-visualization.png' });

    console.log('Production-specific visualization test completed successfully');
  });
});
