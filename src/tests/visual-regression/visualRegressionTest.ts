import { test, expect } from '@playwright/test';
// Import Percy with a dynamic require to avoid TypeScript errors
const percySnapshot = require('@percy/playwright');

// Visual regression test suite for celestial visualization components
test.describe('Visual Regression Tests', () => {
  // Configuration to ensure consistent rendering for screenshots
  test.beforeEach(async ({ page }) => {
    // Set viewport to ensure consistent size for comparisons
    await page.setViewportSize({ width: 1920, height: 1080 });
    // Disable animations during tests for consistent screenshots
    await page.addStyleTag({
      content: `
        * {
          animation-duration: 0s !important;
          transition-duration: 0s !important;
        }
      `
    });
  });

  test('CelestialBackground renders correctly', async ({ page }) => {
    await page.goto('/test-pages/celestial-background');
    // Wait for all textures and 3D elements to load completely
    await page.waitForTimeout(2000);
    await percySnapshot(page, 'CelestialBackground');

    // Test screenshot assertion
    const screenshot = await page.screenshot();
    expect(screenshot).toMatchSnapshot('celestial-background.png');
  });

  test('EnhancedSpaceScene with all features enabled', async ({ page }) => {
    await page.goto('/test-pages/enhanced-space-scene?quality=high');
    await page.waitForTimeout(2000);
    await percySnapshot(page, 'EnhancedSpaceScene-High-Quality');

    const screenshot = await page.screenshot();
    expect(screenshot).toMatchSnapshot('enhanced-space-scene-high.png');
  });

  test('PlanetSystem with orbital mechanics', async ({ page }) => {
    await page.goto('/test-pages/planet-system');
    await page.waitForTimeout(2000);
    await percySnapshot(page, 'PlanetSystem');

    const screenshot = await page.screenshot();
    expect(screenshot).toMatchSnapshot('planet-system.png');
  });

  test('Nebula effects render correctly', async ({ page }) => {
    await page.goto('/test-pages/nebula-effects');
    await page.waitForTimeout(2000);
    await percySnapshot(page, 'NebulaEffects');

    const screenshot = await page.screenshot();
    expect(screenshot).toMatchSnapshot('nebula-effects.png');
  });

  test('ShootingStars animation frames', async ({ page }) => {
    await page.goto('/test-pages/shooting-stars');

    // Capture multiple frames to verify animation
    for (let i = 0; i < 3; i++) {
      await page.waitForTimeout(500);
      await percySnapshot(page, `ShootingStars-Frame-${i}`);
    }
  });

  test('Responsive design breakpoints', async ({ page }) => {
    // Test multiple device sizes
    const breakpoints = [
      { width: 1920, height: 1080, name: 'desktop' },
      { width: 1024, height: 768, name: 'tablet' },
      { width: 375, height: 812, name: 'mobile' }
    ];

    for (const breakpoint of breakpoints) {
      await page.setViewportSize({
        width: breakpoint.width,
        height: breakpoint.height
      });
      await page.goto('/');
      await page.waitForTimeout(1000);
      await percySnapshot(page, `Responsive-${breakpoint.name}`);
    }
  });
});
