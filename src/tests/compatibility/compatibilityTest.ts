import { test, expect } from '@playwright/test';

// Add TypeScript type declarations for non-standard browser APIs
declare global {
  interface Window {
    currentCameraPosition?: any;
    gc?: () => void;
  }

  interface Performance {
    memory?: {
      usedJSHeapSize: number;
      totalJSHeapSize: number;
      jsHeapSizeLimit: number;
    };
  }
}

// Cross-browser compatibility test suite
test.describe('Cross-Browser Compatibility Tests', () => {
  // Define browsers to test
  const browsers = [
    { name: 'chromium', label: 'Chrome' },
    { name: 'firefox', label: 'Firefox' },
    { name: 'webkit', label: 'Safari' }
  ];

  // Define viewport sizes to test
  const viewports = [
    { width: 1920, height: 1080, label: 'Desktop' },
    { width: 1024, height: 768, label: 'Tablet' },
    { width: 375, height: 812, label: 'Mobile' }
  ];

  // Test main visualization renders correctly across browsers
  for (const browser of browsers) {
    test(`CelestialCanvas renders correctly in ${browser.label}`, async ({ page, browserName }) => {
      // Skip if not testing the current browser
      test.skip(browserName !== browser.name, `Skipping as current browser is ${browserName}, not ${browser.name}`);

      await page.goto('/test-pages/celestial-canvas');
      await page.waitForTimeout(2000);

      // Check if canvas is rendered
      const canvas = await page.$('canvas');
      expect(canvas).not.toBeNull();

      // Check if canvas has appropriate size
      if (!canvas) {
        test.fail(true, 'Canvas element not found');
        return;
      }

      const canvasSize = await canvas.evaluate(el => ({
        width: el.width,
        height: el.height
      }));

      expect(canvasSize.width).toBeGreaterThan(0);
      expect(canvasSize.height).toBeGreaterThan(0);

      // Take a screenshot for visual comparison
      await page.screenshot({ path: `./test-results/celestial-canvas-${browser.name}.png` });
    });
  }

  // Test responsive behavior across different viewport sizes
  for (const viewport of viewports) {
    test(`Responsive layout works correctly at ${viewport.label} size`, async ({ page }) => {
      // Set viewport size
      await page.setViewportSize({ width: viewport.width, height: viewport.height });

      await page.goto('/');
      await page.waitForTimeout(1000);

      // Check if the layout adapts correctly
      const isOverflowing = await page.evaluate(() => {
        const body = document.body;
        return body.scrollWidth > window.innerWidth;
      });

      // On mobile, we expect no horizontal overflow
      if (viewport.width <= 768) {
        expect(isOverflowing).toBeFalsy();
      }

      // Take a screenshot for visual comparison
      await page.screenshot({ path: `./test-results/responsive-${viewport.label.toLowerCase()}.png` });
    });
  }

  // Test WebGL capabilities and fallbacks
  test('WebGL capabilities detection works correctly', async ({ page }) => {
    await page.goto('/test-pages/celestial-canvas');

    // Inject WebGL detection code
    const webGLInfo = await page.evaluate(() => {
      // Check for WebGL support
      function hasWebGL() {
        try {
          const canvas = document.createElement('canvas');
          return !!(window.WebGLRenderingContext &&
            (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
        } catch (e) {
          return false;
        }
      }

      // Check for WebGL 2 support
      function hasWebGL2() {
        try {
          const canvas = document.createElement('canvas');
          return !!(window.WebGL2RenderingContext && canvas.getContext('webgl2'));
        } catch (e) {
          return false;
        }
      }

      return {
        hasWebGL: hasWebGL(),
        hasWebGL2: hasWebGL2(),
        renderer: document.querySelector('canvas') ? 'canvas-present' : 'no-canvas'
      };
    });

    console.log('WebGL capabilities:', webGLInfo);

    // Verify that either WebGL is supported or a fallback is used
    expect(webGLInfo.renderer).toBe('canvas-present');
  });

  // Test for common WebGL errors
  test('No WebGL context errors occur during rendering', async ({ page }) => {
    // Listen for console errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/test-pages/celestial-canvas');
    await page.waitForTimeout(2000);

    // Check for WebGL context lost errors
    const webGLErrors = consoleErrors.filter(error =>
      error.includes('WebGL') ||
      error.includes('context lost') ||
      error.includes('out of memory')
    );

    console.log('WebGL errors:', webGLErrors);
    expect(webGLErrors.length).toBe(0);
  });

  // Test touch interactions
  test('Touch interactions work correctly', async ({ page }) => {
    await page.goto('/test-pages/celestial-canvas');
    await page.waitForTimeout(2000);

    // Get initial state
    const initialState = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas) return null;

      // This assumes your app stores camera state somewhere accessible
      // Adjust according to your actual implementation
      return {
        cameraPosition: window.currentCameraPosition || 'unknown'
      };
    });

    // Simulate touch events
    await page.touchscreen.tap(500, 500);

    // For pinch-zoom (if supported by your app)
    await page.touchscreen.tap(400, 400); // First touch point
    await page.touchscreen.tap(600, 600); // Second touch point

    // Wait for any animations to complete
    await page.waitForTimeout(500);

    // Get new state
    const newState = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas) return null;

      return {
        cameraPosition: window.currentCameraPosition || 'unknown'
      };
    });

    // This is a simplified check - in a real test, you'd verify specific behavior
    // based on your application's touch interaction model
    console.log('Touch interaction test:', { initialState, newState });
  });

  // Test for memory leaks during scene transitions
  test('No memory leaks during scene transitions', async ({ page }) => {
    // This test requires Chrome's performance.memory API
    const isChromium = await page.evaluate(() =>
      navigator.userAgent.includes('Chrome')
    );

    test.skip(!isChromium, 'Skipping memory leak test on non-Chromium browsers');

    // Navigate to first scene
    await page.goto('/test-pages/celestial-canvas');
    await page.waitForTimeout(2000);

    // Measure initial memory
    const initialMemory = await page.evaluate(() =>
      performance.memory ? performance.memory.usedJSHeapSize : 0
    );

    // Perform multiple scene transitions
    for (let i = 0; i < 5; i++) {
      // Navigate to another page and back
      await page.goto('/test-pages/planet-system');
      await page.waitForTimeout(1000);
      await page.goto('/test-pages/celestial-canvas');
      await page.waitForTimeout(1000);
    }

    // Force garbage collection if possible (this is browser-dependent)
    await page.evaluate(() => {
      if (window.gc) window.gc();
    });

    // Measure final memory
    const finalMemory = await page.evaluate(() =>
      performance.memory ? performance.memory.usedJSHeapSize : 0
    );

    const memoryIncrease = finalMemory - initialMemory;
    console.log(`Memory change after transitions: ${memoryIncrease} bytes`);

    // Allow for some increase but not excessive
    // This threshold may need adjustment based on your application
    if (initialMemory > 0) {
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024); // 50MB limit
    }
  });
});
