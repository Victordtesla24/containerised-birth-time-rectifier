/**
 * Environment detection and adaptation helpers for tests
 * Ensures tests work consistently across dev, test, and production environments
 * Handles fancy UI/UX visualizations in production environment
 */

/**
 * Detects the current environment based on URL and page properties
 * @param {import('@playwright/test').Page} page - Playwright page
 * @returns {Promise<{env: 'dev'|'test'|'prod', hasAdvancedUI: boolean}>} Environment info
 */
async function detectEnvironment(page) {
  // Check URL to determine environment
  const url = page.url();
  const hostname = new URL(url).hostname;

  // Check for environment indicators
  let env = 'dev'; // Default to dev
  if (hostname.includes('vercel') || hostname.includes('production')) {
    env = 'prod';
  } else if (hostname.includes('test') || hostname.includes('staging')) {
    env = 'test';
  }

  // Check for advanced UI features presence
  const hasAdvancedUI = await page.evaluate(() => {
    return (
      // Check for global flags
      (typeof window.__visualizationMode !== 'undefined' && window.__visualizationMode === 'enhanced') ||
      (typeof window.__enableFancyEffects !== 'undefined' && window.__enableFancyEffects === true) ||

      // Check for style elements
      !!document.querySelector('link[href*="cosmic-effects"]') ||

      // Check for advanced components
      !!document.querySelector('.threejs-container') ||
      !!document.querySelector('canvas[data-engine="three.js"]') ||

      // Check for cosmic effects class
      document.body.classList.contains('cosmic-effects-enabled')
    );
  });

  console.log(`Detected environment: ${env}, Advanced UI: ${hasAdvancedUI}`);

  return { env, hasAdvancedUI };
}

/**
 * Enables test mode in the application to ensure tests run smoothly
 * @param {import('@playwright/test').Page} page - Playwright page
 */
async function enableTestMode(page) {
  await page.evaluate(() => {
    // Set test flags to ensure tests work with advanced UI
    window.__testMode = true;
    window.__testingBypassGeocodingValidation = true;

    // Add attributes to help test selectors find elements
    document.documentElement.setAttribute('data-test-visible', 'true');

    // Force tooltips to be visible for tests
    const style = document.createElement('style');
    style.innerHTML = `
      /* Make hover elements visible for tests */
      .entity-details, .tooltip, [data-tooltip], .hover-content {
        opacity: 1 !important;
        visibility: visible !important;
        display: block !important;
        pointer-events: all !important;
      }

      /* Make clickable elements more reliable */
      button, [role="button"], a, input[type="radio"], input[type="checkbox"] {
        pointer-events: all !important;
      }
    `;
    document.head.appendChild(style);

    console.log('Test mode enabled for UI testing');
  });
}

/**
 * Adapts selectors for the current environment
 * @param {import('@playwright/test').Page} page - Playwright page
 * @param {Object} baseSelectors - Base selectors for dev environment
 * @returns {Promise<Object>} Environment-specific selectors
 */
async function adaptSelectors(page, baseSelectors) {
  const { env, hasAdvancedUI } = await detectEnvironment(page);

  // Clone base selectors
  const adaptedSelectors = {...baseSelectors};

  // Adapt selectors based on environment
  if (env === 'prod' || hasAdvancedUI) {
    // Override selectors for production/advanced UI where needed
    if (baseSelectors.chartVisualization) {
      adaptedSelectors.chartVisualization = [
        baseSelectors.chartVisualization,
        '.chart-visualization-enhanced',
        '.threejs-chart',
        'canvas.chart-3d'
      ].join(', ');
    }

    if (baseSelectors.planets) {
      adaptedSelectors.planets = [
        baseSelectors.planets,
        '.planet-3d',
        '[data-object-type="planet"]'
      ].join(', ');
    }

    // Add special handling for advanced UI tooltips
    if (baseSelectors.tooltip) {
      adaptedSelectors.tooltip = [
        baseSelectors.tooltip,
        '.advanced-tooltip',
        '.hover-details-3d'
      ].join(', ');
    }
  }

  return adaptedSelectors;
}

/**
 * Handles WebGL/ThreeJS elements that may be present in production
 * @param {import('@playwright/test').Page} page - Playwright page
 */
async function prepareAdvancedVisualization(page) {
  // Wait for 3D canvas to be ready if present
  const hasCanvas = await page.locator('canvas').count() > 0;

  if (hasCanvas) {
    // Add hooks to stabilize WebGL for testing
    await page.evaluate(() => {
      // Pause animations for stable testing
      if (window.THREE && window.THREE.AnimationMixer) {
        // Store original update method
        const originalUpdate = THREE.AnimationMixer.prototype.update;

        // Override update to prevent animation during tests
        THREE.AnimationMixer.prototype.update = function() {
          if (window.__testMode) {
            // Skip animation updates in test mode
            return;
          }
          return originalUpdate.apply(this, arguments);
        };
      }

      // Make all planets/objects visible regardless of camera position
      document.querySelectorAll('[data-object-type="planet"], .planet-3d, .celestial-object').forEach(el => {
        if (el.style) {
          el.style.visibility = 'visible';
          el.style.opacity = '1';
        }
      });

      console.log('Advanced visualization prepared for testing');
    });
  }
}

/**
 * Waits for fancy animations and transitions to complete
 * @param {import('@playwright/test').Page} page - Playwright page
 */
async function waitForAnimations(page) {
  // Check if the page has animations
  const hasAnimations = await page.evaluate(() => {
    return document.querySelectorAll('.animate-*, [class*="animation"], [class*="transition"]').length > 0;
  });

  if (hasAnimations) {
    // Wait for animations to complete
    await page.waitForTimeout(1000); // Base wait time

    // Check if animations are still running
    const animationsRunning = await page.evaluate(() => {
      const runningAnimations = document.getAnimations().filter(a =>
        a.playState === 'running' &&
        !a.id.includes('test') // Ignore test-specific animations
      );
      return runningAnimations.length;
    });

    if (animationsRunning > 0) {
      console.log(`Waiting for ${animationsRunning} animations to complete`);
      await page.waitForTimeout(animationsRunning * 200); // Additional wait time based on running animations
    }
  }
}

module.exports = {
  detectEnvironment,
  enableTestMode,
  adaptSelectors,
  prepareAdvancedVisualization,
  waitForAnimations
};
