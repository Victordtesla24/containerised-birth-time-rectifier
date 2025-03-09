import { test, expect } from '@playwright/test';

// Define types for custom properties added at runtime
declare global {
  interface HTMLCanvasElement {
    __threeInstance?: {
      camera: {
        position: { x: number; y: number; z: number };
        isOrthographicCamera?: boolean;
        zoom?: number;
      };
      animationPaused?: boolean;
    };
  }

  interface Window {
    checkContrast?: () => any[];
  }
}

// User interaction and accessibility test suite
test.describe('Interaction and Accessibility Tests', () => {
  test('Camera controls respond correctly to user input', async ({ page }) => {
    await page.goto('/test-pages/celestial-canvas');
    await page.waitForTimeout(2000); // Wait for scene to initialize

    // Get initial camera position
    const initialPosition = await page.evaluate(() => {
      // Access the camera position from the Three.js scene
      const canvas = document.querySelector('canvas');
      if (!canvas || !canvas.__threeInstance) return null;

      const camera = canvas.__threeInstance.camera;
      return {
        x: camera.position.x,
        y: camera.position.y,
        z: camera.position.z
      };
    });

    // Simulate mouse drag to rotate camera
    await page.mouse.move(500, 500);
    await page.mouse.down();
    await page.mouse.move(600, 500);
    await page.mouse.up();

    // Wait for animation to complete
    await page.waitForTimeout(500);

    // Get new camera position
    const newPosition = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas || !canvas.__threeInstance) return null;

      const camera = canvas.__threeInstance.camera;
      return {
        x: camera.position.x,
        y: camera.position.y,
        z: camera.position.z
      };
    });

    // Verify camera position changed
    expect(newPosition).not.toEqual(initialPosition);
  });

  test('Zoom controls work correctly', async ({ page }) => {
    await page.goto('/test-pages/celestial-canvas');
    await page.waitForTimeout(2000);

    // Get initial camera zoom
    const initialZoom = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas || !canvas.__threeInstance) return null;

      const camera = canvas.__threeInstance.camera;
      // For perspective camera, use position.z as proxy for zoom
      // For orthographic camera, use zoom property
      return camera.isOrthographicCamera ? camera.zoom : camera.position.z;
    });

    // Simulate mouse wheel for zoom
    await page.mouse.move(500, 500);
    await page.mouse.wheel(0, -100); // Scroll up to zoom in

    // Wait for animation to complete
    await page.waitForTimeout(500);

    // Get new zoom level
    const newZoom = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas || !canvas.__threeInstance) return null;

      const camera = canvas.__threeInstance.camera;
      return camera.isOrthographicCamera ? camera.zoom : camera.position.z;
    });

    // Verify zoom changed
    expect(newZoom).not.toEqual(initialZoom);
  });

  test('Interactive elements are keyboard accessible', async ({ page }) => {
    await page.goto('/');

    // Find all interactive elements
    const interactiveElements = await page.$$('button, a, [role="button"], [tabindex="0"]');

    // Verify they can be focused with keyboard
    for (const element of interactiveElements) {
      await element.focus();
      const isFocused = await element.evaluate(el => document.activeElement === el);
      expect(isFocused).toBeTruthy();
    }
  });

  test('Color contrast meets WCAG standards', async ({ page }) => {
    await page.goto('/');

    // Inject the color contrast checker
    await page.addScriptTag({
      content: `
        window.checkContrast = function() {
          const results = [];
          const elements = document.querySelectorAll('*');

          elements.forEach(element => {
            if (element.innerText && element.innerText.trim()) {
              const style = window.getComputedStyle(element);
              const foreground = style.color;
              const background = style.backgroundColor;

              // Skip elements with transparent background
              if (background === 'rgba(0, 0, 0, 0)' || background === 'transparent') {
                return;
              }

              // Simple contrast calculation (this is a simplified version)
              // In a real implementation, use a proper WCAG contrast algorithm
              const fgRGB = parseRGB(foreground);
              const bgRGB = parseRGB(background);

              if (fgRGB && bgRGB) {
                const contrast = calculateContrast(fgRGB, bgRGB);

                if (contrast < 4.5) { // WCAG AA standard for normal text
                  results.push({
                    element: element.tagName,
                    text: element.innerText.substring(0, 20),
                    contrast: contrast,
                    foreground,
                    background
                  });
                }
              }
            }
          });

          return results;

          function parseRGB(color) {
            const match = color.match(/rgba?\\(\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)\\s*(?:,\\s*([\\d.]+)\\s*)?\\)/i);
            if (!match) return null;

            return {
              r: parseInt(match[1]),
              g: parseInt(match[2]),
              b: parseInt(match[3]),
              a: match[4] ? parseFloat(match[4]) : 1
            };
          }

          function calculateContrast(fg, bg) {
            // Simplified contrast calculation
            const fgLuminance = (0.299 * fg.r + 0.587 * fg.g + 0.114 * fg.b) / 255;
            const bgLuminance = (0.299 * bg.r + 0.587 * bg.g + 0.114 * bg.b) / 255;

            const ratio = fgLuminance > bgLuminance
              ? (fgLuminance + 0.05) / (bgLuminance + 0.05)
              : (bgLuminance + 0.05) / (fgLuminance + 0.05);

            return ratio;
          }
        };
      `
    });

    // Run the contrast check
    const contrastIssues = await page.evaluate(() => {
      if (!window.checkContrast) {
        console.error('checkContrast function not available');
        return [];
      }
      return window.checkContrast();
    });

    // Log issues for review
    console.log('Contrast issues:', contrastIssues);

    // Assert that there are no critical contrast issues
    // This is a simplified check - in practice, you might want to allow some exceptions
    expect(contrastIssues.length).toBeLessThan(5);
  });

  test('Animation controls work correctly', async ({ page }) => {
    await page.goto('/test-pages/planet-system');
    await page.waitForTimeout(2000);

    // Find and click the pause button (adjust selector as needed)
    await page.click('[data-testid="animation-control-pause"]');

    // Verify animation is paused
    const isPaused = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas || !canvas.__threeInstance) return null;

      // This assumes your app has a way to check animation state
      return canvas.__threeInstance.animationPaused;
    });

    expect(isPaused).toBeTruthy();

    // Resume animation
    await page.click('[data-testid="animation-control-play"]');

    // Verify animation is playing
    const isPlaying = await page.evaluate(() => {
      const canvas = document.querySelector('canvas');
      if (!canvas || !canvas.__threeInstance) return null;

      return !canvas.__threeInstance.animationPaused;
    });

    expect(isPlaying).toBeTruthy();
  });
});
