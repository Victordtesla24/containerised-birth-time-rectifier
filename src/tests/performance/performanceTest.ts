import { test, expect } from '@playwright/test';

// Add TypeScript type declarations for non-standard browser APIs
declare global {
  interface Window {
    performanceMetrics?: {
      frames: number[];
      startTime: number;
      isRecording: boolean;
    };
    sceneInitTime?: number;
    sceneInitialized?: boolean;
    threeSceneReady?: boolean;
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

// Performance test suite for celestial visualization components
test.describe('Performance Tests', () => {
  test('EnhancedSpaceScene maintains acceptable frame rate', async ({ page }) => {
    // Navigate to the test page
    await page.goto('/test-pages/enhanced-space-scene?quality=high');

    // Inject performance measurement code
    await page.addScriptTag({
      content: `
        window.performanceMetrics = {
          frames: [],
          startTime: performance.now(),
          isRecording: false
        };

        // Record frame times
        function recordFrame(timestamp) {
          if (window.performanceMetrics.isRecording) {
            window.performanceMetrics.frames.push(timestamp);
          }
          requestAnimationFrame(recordFrame);
        }

        requestAnimationFrame(recordFrame);
      `
    });

    // Wait for scene to fully load
    await page.waitForTimeout(2000);

    // Start recording frames
    await page.evaluate(() => {
      if (!window.performanceMetrics) {
        window.performanceMetrics = {
          frames: [],
          startTime: 0,
          isRecording: false
        };
      }
      window.performanceMetrics.frames = [];
      window.performanceMetrics.startTime = performance.now();
      window.performanceMetrics.isRecording = true;
    });

    // Record for 5 seconds
    await page.waitForTimeout(5000);

    // Stop recording and calculate metrics
    const metrics = await page.evaluate(() => {
      if (!window.performanceMetrics) {
        console.error('Performance metrics not available');
        return {
          averageFps: 0,
          minFps: 0,
          maxFps: 0,
          frameCount: 0,
          totalTime: 0
        };
      }

      window.performanceMetrics.isRecording = false;
      const frames = window.performanceMetrics.frames;
      const frameTimes = [];

      // Calculate time between frames
      for (let i = 1; i < frames.length; i++) {
        frameTimes.push(frames[i] - frames[i-1]);
      }

      // Calculate metrics
      const avgFrameTime = frameTimes.reduce((sum, time) => sum + time, 0) / frameTimes.length;
      const fps = 1000 / avgFrameTime;
      const minFps = 1000 / Math.max(...frameTimes);
      const maxFps = 1000 / Math.min(...frameTimes);

      return {
        averageFps: fps,
        minFps,
        maxFps,
        frameCount: frames.length,
        totalTime: frames[frames.length - 1] - frames[0]
      };
    });

    console.log('Performance metrics:', metrics);

    // Assert acceptable performance
    expect(metrics.averageFps).toBeGreaterThan(30);
    expect(metrics.minFps).toBeGreaterThan(20);
  });

  test('Initial load time is within acceptable range', async ({ page }) => {
    // Create a promise that resolves when the load event fires
    const loadPromise = page.waitForEvent('load');

    // Start navigation and record timing
    const startTime = Date.now();
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    // Wait for the load event
    await loadPromise;
    const loadTime = Date.now() - startTime;

    console.log(`Page load time: ${loadTime}ms`);

    // Assert acceptable load time (adjust threshold as needed)
    expect(loadTime).toBeLessThan(5000);
  });

  test('3D scene initialization time', async ({ page }) => {
    await page.goto('/test-pages/celestial-canvas');

    // Inject timing code
    const initTime = await page.evaluate(() => {
      return new Promise(resolve => {
        // Reset any existing timing
        window.sceneInitTime = 0;

        // Create a MutationObserver to detect when the canvas is added
        const observer = new MutationObserver(() => {
          const canvas = document.querySelector('canvas');
          if (canvas) {
            observer.disconnect();

            // Start timing
            const startTime = performance.now();

            // Wait for the scene to be fully initialized
            // This assumes there's a global event or property that indicates scene readiness
            const checkInterval = setInterval(() => {
              // Check if scene is ready (adjust this condition based on your application)
              if (window.sceneInitialized || window.threeSceneReady) {
                clearInterval(checkInterval);
                window.sceneInitTime = performance.now() - startTime;
                resolve(window.sceneInitTime);
              }
            }, 100);

            // Timeout after 10 seconds
            setTimeout(() => {
              clearInterval(checkInterval);
              resolve(performance.now() - startTime);
            }, 10000);
          }
        });

        observer.observe(document.body, { childList: true, subtree: true });
      });
    });

    console.log(`3D scene initialization time: ${initTime}ms`);

    // Assert acceptable initialization time
    expect(initTime).toBeLessThan(3000);
  });

  test('Memory usage remains stable during animations', async ({ page }) => {
    await page.goto('/test-pages/planet-system');

    // Wait for scene to initialize
    await page.waitForTimeout(2000);

    // Measure memory at start
    const startMemory = await page.evaluate(() => {
      return performance.memory ? performance.memory.usedJSHeapSize : 0;
    });

    // Run animations for a period
    await page.waitForTimeout(10000);

    // Measure memory after animations
    const endMemory = await page.evaluate(() => {
      return performance.memory ? performance.memory.usedJSHeapSize : 0;
    });

    const memoryIncrease = endMemory - startMemory;
    console.log(`Memory increase during animations: ${memoryIncrease} bytes`);

    // Assert memory usage is stable (adjust threshold as needed)
    // This test may need to be conditional as performance.memory is Chrome-only
    if (startMemory > 0) {
      // Allow for some increase but not excessive
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024); // 50MB limit
    }
  });
});
