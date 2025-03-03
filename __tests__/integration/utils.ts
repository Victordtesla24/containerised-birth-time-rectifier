/**
 * Integration Test Utilities
 * Helper functions for integration tests
 */

import fetch from 'isomorphic-unfetch';
import { act } from 'react-dom/test-utils';
import { waitFor } from '@testing-library/react';

/**
 * In mock testing mode, we always return true as services are now mocked
 * @returns {Promise<boolean>} True as services are considered running via mocks
 */
export const checkServicesRunning = async (): Promise<boolean> => {
  // In integration tests with mocks, return true as services are considered running
  return true;
  
  // Previous implementation commented out
  /*
  try {
    // Check if AI service is running
    const aiResponse = await fetch('http://localhost:8000/health');
    if (!aiResponse.ok) return false;

    // Check if frontend service is running
    const frontendResponse = await fetch('http://localhost:3001/api/health');
    if (!frontendResponse.ok) return false;

    return true;
  } catch (error) {
    console.error('Error checking services:', error);
    return false;
  }
  */
};

/**
 * Waits for network requests to complete
 * @param waitTime Time in ms to wait for network operations
 */
export const waitForNetwork = async (waitTime = 1000): Promise<void> => {
  await act(async () => {
    await new Promise(resolve => setTimeout(resolve, waitTime));
  });
};

/**
 * Enhanced wait function with extended timeout and retry logic
 * @param callback Function to execute
 * @param options Wait options
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
  
  let retryCount = 0;
  
  while (retryCount < retries) {
    try {
      await waitFor(callback, { timeout });
      return; // Success, exit
    } catch (error) {
      console.log(`Retry attempt ${retryCount + 1}/${retries}`);
      retryCount++;
      
      if (retryCount >= retries) {
        throw error; // All retries failed
      }
      
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, interval));
    }
  }
};

/**
 * Wait for an element to stabilize
 * @param getElement Function that returns the element
 * @param maxAttempts Maximum attempts to wait
 */
export const waitForElementToStabilize = async (
  getElement: () => HTMLElement | null,
  maxAttempts = 5
): Promise<void> => {
  let previousHTML = '';
  let attempts = 0;

  await waitFor(
    () => {
      const element = getElement();
      if (!element) return false;

      const currentHTML = element.innerHTML;
      const isStable = currentHTML === previousHTML;
      previousHTML = currentHTML;

      attempts++;
      return isStable || attempts >= maxAttempts;
    },
    { timeout: 5000 }
  );
};

/**
 * Skip tests if services aren't running
 * Now always runs tests since we're using mocks
 */
export const skipIfServicesNotRunning = () => {
  // Always run tests with our updated mock approach
  return;
  
  // Previous implementation commented out
  /*
  beforeAll(async () => {
    const servicesRunning = await checkServicesRunning();
    if (!servicesRunning) {
      console.warn('Skipping integration tests: services not running');
      test.skip.each([])('', () => {});
    }
  });
  */
}; 