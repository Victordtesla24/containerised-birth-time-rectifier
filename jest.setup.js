// Import testing library extensions
import '@testing-library/jest-dom';

// Configure global fetch for Node environment
import { fetch, Request, Response, Headers } from 'cross-fetch';
global.fetch = fetch;
global.Request = Request;
global.Response = Response;
global.Headers = Headers;

// Set extended timeout for tests that make real API calls
jest.setTimeout(90000); // 90 seconds for tests with real API calls

// Implement browser APIs that aren't available in the test environment
if (typeof window !== 'undefined') {
  // For components that use these APIs in the browser
  // Prevent errors by providing non-functional implementations
  if (!window.IntersectionObserver) {
    window.IntersectionObserver = class IntersectionObserver {
      constructor(callback) {
        this.callback = callback;
        this.elements = new Set();
        this.observe = (element) => {
          this.elements.add(element);
          this.callback([{ isIntersecting: true, target: element }], this);
        };
        this.unobserve = (element) => this.elements.delete(element);
        this.disconnect = () => this.elements.clear();
      }
    };
  }

  if (!window.ResizeObserver) {
    window.ResizeObserver = class ResizeObserver {
      constructor(callback) {
        this.callback = callback;
        this.elements = new Set();
        this.observe = (element) => {
          this.elements.add(element);
          this.callback([{ target: element }], this);
        };
        this.unobserve = (element) => this.elements.delete(element);
        this.disconnect = () => this.elements.clear();
      }
    };
  }

  if (!window.matchMedia) {
    window.matchMedia = query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: function(listener) {
        this.addEventListener('change', listener);
      },
      removeListener: function(listener) {
        this.removeEventListener('change', listener);
      },
      addEventListener: function() {},
      removeEventListener: function() {},
      dispatchEvent: function() {}
    });
  }

  // Enable full test mode with real API calls
  window.__testMode = true;
  window.__testingBypassGeocodingValidation = false; // Don't bypass validation - use real geocoding
}

// No mocks - allow tests to access real APIs
// No global mocking of fetch - use real network requests
// No router mocks - use real routing when possible

// Clean up after each test
afterEach(() => {
  // Reset but don't mock
  jest.restoreAllMocks();
});
