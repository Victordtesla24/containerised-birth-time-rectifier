/**
 * Integration Test Utilities
 * Helper functions for integration tests
 */

import { waitFor } from '@testing-library/react';

/**
 * Checks if required services are running
 * @returns {Promise<boolean>} True if all services are running
 */
export const checkServicesRunning = async (): Promise<boolean> => {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';
    const aiServiceUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    // Check if API server is running
    const apiResponse = await fetch(`${apiUrl}/health`).catch(() => ({ ok: false }));

    // Check if AI service is running
    const aiResponse = await fetch(`${aiServiceUrl}/health`).catch(() => ({ ok: false }));

    return apiResponse.ok && aiResponse.ok;
  } catch (error) {
    console.error('Error checking services:', error);
    return false;
  }
};

/**
 * Waits for network requests to complete
 * @param waitTime Time in ms to wait for network operations
 */
export const waitForNetwork = async (waitTime = 1000): Promise<void> => {
  // Use a simple timeout instead of act
  await new Promise(resolve => setTimeout(resolve, waitTime));
};

/**
 * Retry a callback until it returns true
 * @param callback Function that returns true when ready
 * @param options Timeout, interval, and retry count configuration
 */
export const waitForWithRetry = async (
  callback: () => boolean | void,
  options: { timeout?: number; interval?: number; retries?: number } = {}
): Promise<void> => {
  const {
    timeout = 5000,
    interval = 100,
    retries = 3
  } = options;

  const startTime = Date.now();
  let attemptCount = 0;

  // Helper function to run the attempt
  const runAttempt = async (): Promise<boolean> => {
    try {
      const result = callback();
      return !!result;
    } catch (error) {
      if (attemptCount >= retries) {
        throw error;
      }
      return false;
    }
  };

  while (Date.now() - startTime < timeout) {
    attemptCount++;
    const result = await runAttempt();

    if (result) {
      return;
    }

    if (attemptCount >= retries) {
      throw new Error(`Callback did not succeed after ${retries} attempts (timed out)`);
    }

    await new Promise(resolve => setTimeout(resolve, interval));
  }

  throw new Error(`Timed out after ${timeout}ms`);
};

/**
 * Wait for an element's position to stabilize (for animations, etc.)
 * @param getElement Function that returns the element to check
 * @param maxAttempts Maximum number of attempts to wait for stabilization
 */
export const waitForElementToStabilize = async (
  getElement: () => HTMLElement | null,
  maxAttempts = 5
): Promise<void> => {
  let lastRect: DOMRect | null = null;
  let attempts = 0;

  while (attempts < maxAttempts) {
    const element = getElement();
    if (!element) {
      await new Promise(resolve => setTimeout(resolve, 100));
      attempts++;
      continue;
    }

    const rect = element.getBoundingClientRect();

    if (lastRect &&
        rect.top === lastRect.top &&
        rect.left === lastRect.left &&
        rect.width === lastRect.width &&
        rect.height === lastRect.height) {
      // Element has stabilized
      return;
    }

    lastRect = rect;
    attempts++;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
};

/**
 * Checks if services are available and reports issues but doesn't skip tests
 * This ensures tests will fail properly when services aren't running
 */
export const checkServicesAvailability = async (): Promise<void> => {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';
    const aiServiceUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    // Check if API server is running
    const apiResponse = await fetch(`${apiUrl}/health`).catch(() => ({ ok: false }));

    // Check if AI service is running
    const aiResponse = await fetch(`${aiServiceUrl}/health`).catch(() => ({ ok: false }));

    if (!apiResponse.ok || !aiResponse.ok) {
      const services = [];
      if (!apiResponse.ok) services.push('API Server');
      if (!aiResponse.ok) services.push('AI Service');

      console.error(`
      ================================================================
      ERROR: Required services are not running: ${services.join(', ')}

      Please start all required services before running tests:
      - Run 'docker-compose up' to start all services
      - Or run 'npm run start:services' to start them individually

      Tests will continue but will likely fail with connection errors
      ================================================================
      `);
    }
  } catch (error) {
    console.error(`Failed to check service availability: ${error}`);
  }
};

/**
 * @deprecated Use checkServicesAvailability instead - this function would skip tests
 */
export const skipIfServicesNotRunning = () => {
  console.warn('skipIfServicesNotRunning is deprecated - use checkServicesAvailability instead');
  return checkServicesAvailability();
};
