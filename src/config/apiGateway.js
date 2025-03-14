/**
 * API Gateway Configuration
 *
 * This file contains all configuration for the unified API Gateway,
 * including endpoint definitions, proxy settings, and error handling.
 */

// API Version and prefix
export const API_VERSION = 'v1';
export const API_PREFIX = `/api/${API_VERSION}`;

// Legacy API prefix (for backward compatibility)
export const LEGACY_PREFIX = '/api';

// Direct prefix without version (for backward compatibility)
export const DIRECT_PREFIX = '/api';

// Target backend URL (configurable via environment variables)
const BACKEND_URL = process.env.NEXT_PUBLIC_API_SERVICE_URL || 'http://localhost:9000';

// Endpoints configuration
export const ENDPOINTS = {
  // Health check endpoints
  health: `${API_PREFIX}/health`,

  // Session endpoints
  session: {
    init: `${API_PREFIX}/session/init`,
    refresh: `${API_PREFIX}/session/refresh`,
    status: `${API_PREFIX}/session/status`,
    end: `${API_PREFIX}/session/end`,
  },

  // Chart endpoints
  chart: {
    validate: `${API_PREFIX}/chart/validate`,
    generate: `${API_PREFIX}/chart/generate`,
    get: `${API_PREFIX}/chart`,
    compare: `${API_PREFIX}/chart/chart-comparison`, // Updated to use the more specific endpoint name
    rectify: `${API_PREFIX}/chart/rectify`,
    export: `${API_PREFIX}/chart/export`,
  },

  // Geocoding endpoints
  geocode: {
    search: `${API_PREFIX}/geocode`,
    suggestions: `${API_PREFIX}/geocode/suggestions`,
  },

  // Questionnaire endpoints
  questionnaire: {
    generate: `${API_PREFIX}/questionnaire`,
    answer: `${API_PREFIX}/questionnaire`,
    complete: `${API_PREFIX}/questionnaire/complete`,
  },

  // Export endpoints
  export: {
    download: `${API_PREFIX}/export`,
  },

  // AI endpoints
  ai: {
    status: `${API_PREFIX}/ai/status`,
    models: `${API_PREFIX}/ai/models`,
  },
};

// Legacy endpoints mapping (for backward compatibility)
export const LEGACY_ENDPOINTS = {
  // Health endpoint
  '/health': ENDPOINTS.health,

  // Chart endpoints
  '/chart/validate': ENDPOINTS.chart.validate,
  '/chart/generate': ENDPOINTS.chart.generate,
  '/chart/rectify': ENDPOINTS.chart.rectify,
  '/chart/export': ENDPOINTS.chart.export,
  '/chart/chart-comparison': ENDPOINTS.chart.compare, // Updated to match the backend endpoint
  '/chart/comparison': ENDPOINTS.chart.compare, // Add alternate endpoint for comparison

  // Direct API endpoints
  '/api/chart/validate': ENDPOINTS.chart.validate,
  '/api/chart/generate': ENDPOINTS.chart.generate,
  '/api/chart/rectify': ENDPOINTS.chart.rectify,
  '/api/chart/export': ENDPOINTS.chart.export,
  '/api/chart/chart-comparison': ENDPOINTS.chart.compare, // Updated to match the backend endpoint
  '/api/chart/comparison': ENDPOINTS.chart.compare, // Add alternate endpoint for comparison

  // Version 1 endpoints
  '/api/v1/chart/validate': ENDPOINTS.chart.validate,
  '/api/v1/chart/generate': ENDPOINTS.chart.generate,
  '/api/v1/chart/rectify': ENDPOINTS.chart.rectify,
  '/api/v1/chart/export': ENDPOINTS.chart.export,
  '/api/v1/chart/chart-comparison': ENDPOINTS.chart.compare, // Updated to match the backend endpoint
  '/api/v1/chart/comparison': ENDPOINTS.chart.compare, // Add alternate endpoint for comparison

  // Geocoding endpoints
  '/geocode': ENDPOINTS.geocode.search,
  '/api/geocode': ENDPOINTS.geocode.search,
  '/api/v1/geocode': ENDPOINTS.geocode.search,

  // Questionnaire endpoints
  '/questionnaire': ENDPOINTS.questionnaire.generate,
  '/api/questionnaire': ENDPOINTS.questionnaire.generate,
  '/api/v1/questionnaire': ENDPOINTS.questionnaire.generate,
};

// Gateway configuration
export const GATEWAY_CONFIG = {
  // Default timeout for API requests (ms)
  defaultTimeout: 30000,

  // Proxy configuration
  proxy: {
    target: BACKEND_URL,
    pathRewrite: {
      // Rewrite paths to match backend expectations
      '^/api/v1': '/api',  // Strip version from path for backend
      '^/api/chart/chart-comparison': '/api/chart/comparison', // Ensure comparison endpoint works both ways
      '^/api/v1/chart/chart-comparison': '/api/chart/comparison', // Ensure comparison endpoint works both ways with versioning
    },
    // Set headers for better debugging
    headers: {
      'X-API-Gateway': 'unified-api-gateway', // Identify gateway in requests
    },
  },

  // Retry configuration
  retry: {
    maxRetries: 2,
    initialDelayMs: 1000,
    backoffFactor: 2,
    statusCodesToRetry: [408, 429, 500, 502, 503, 504],
  },

  // Error handling configuration
  errors: {
    standardization: true,
    includeDevelopmentDetails: process.env.NODE_ENV === 'development',
  },

  // Session configuration
  session: {
    header: 'X-Session-Token',
    cookieName: 'sessionToken',
    expiry: 60 * 60 * 24, // 24 hours
    refreshThreshold: 60 * 60 * 1, // 1 hour
  },

  // Feature flags
  features: {
    caching: true,
    rateLimiting: process.env.NODE_ENV === 'production',
    metrics: process.env.NODE_ENV === 'production',
  },
};

// Export the complete gateway configuration
export default {
  API_VERSION,
  API_PREFIX,
  LEGACY_PREFIX,
  ENDPOINTS,
  LEGACY_ENDPOINTS,
  GATEWAY_CONFIG,
};
