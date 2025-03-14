/**
 * Centralized API endpoint registry
 *
 * This file contains all API endpoint definitions in one place to ensure
 * consistency across the application and test suite.
 */

// Version settings - can be configured for different environments
export const API_VERSION = 'v1';
export const USE_VERSIONED_ENDPOINTS = true;

// Base paths by environment
export const API_BASE_PATH = process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:8000/api';

/**
 * Generate the full endpoint URL with proper versioning
 *
 * @param {string} path - The endpoint path without version or api prefix
 * @param {boolean} [includeVersion=true] - Whether to include version in the path
 * @returns {string} The complete endpoint path
 */
export const getEndpointPath = (path, includeVersion = true) => {
  // Ensure path starts with a slash if not empty
  const formattedPath = path && !path.startsWith('/') ? `/${path}` : path;

  // Add version if needed
  if (USE_VERSIONED_ENDPOINTS && includeVersion) {
    return `/${API_VERSION}${formattedPath || ''}`;
  }

  return formattedPath || '';
};

/**
 * Complete endpoint registry
 *
 * All API endpoints are defined here to maintain consistency across the application.
 * Each endpoint has a function that can build the URL with optional parameters.
 */
export const endpoints = {
  // Session endpoints
  SESSION: {
    INIT: () => getEndpointPath('/session/init'),
    STATUS: () => getEndpointPath('/session/status'),
    REFRESH: () => getEndpointPath('/session/refresh'),
    END: () => getEndpointPath('/session/end'),
  },

  // Chart endpoints
  chart: {
    validate: () => getEndpointPath('/chart/validate'),
    generate: () => getEndpointPath('/chart/generate'),
    get: (chartId) => getEndpointPath(`/chart/${chartId}`),
    rectify: () => getEndpointPath('/chart/rectify'),
    compare: () => getEndpointPath('/chart/compare'),
    export: () => getEndpointPath('/chart/export'),
  },

  // Geocoding endpoint
  geocode: () => getEndpointPath('/geocode'),

  // Questionnaire endpoints
  questionnaire: {
    get: () => getEndpointPath('/questionnaire'),
    answer: (questionId) => getEndpointPath(`/questionnaire/${questionId}/answer`),
    complete: () => getEndpointPath('/questionnaire/complete'),
  },

  // Interpretation endpoint
  interpretation: (chartId) =>
    getEndpointPath(`/interpretation${chartId ? `?chart_id=${chartId}` : ''}`),

  // Export download endpoint
  exportDownload: (exportId) => getEndpointPath(`/export/${exportId}/download`),

  // Health check endpoint
  health: () => getEndpointPath('/health'),

  // Alternative (non-versioned) endpoints for backward compatibility
  alt: {
    chart: {
      validate: () => getEndpointPath('/chart/validate', false),
      generate: () => getEndpointPath('/chart/generate', false),
      get: (chartId) => getEndpointPath(`/chart/${chartId}`, false),
      rectify: () => getEndpointPath('/chart/rectify', false),
      compare: () => getEndpointPath('/chart/compare', false),
      export: () => getEndpointPath('/chart/export', false),
    },
    geocode: () => getEndpointPath('/geocode', false),
    questionnaire: {
      get: () => getEndpointPath('/questionnaire', false),
      answer: (questionId) => getEndpointPath(`/questionnaire/${questionId}/answer`, false),
      complete: () => getEndpointPath('/questionnaire/complete', false),
    }
  }
};

export default endpoints;
