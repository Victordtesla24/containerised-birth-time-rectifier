/**
 * Application configuration
 */

// API base URL - defaults to localhost in development
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Environment detection
export const isDevelopment = process.env.NODE_ENV === 'development';
export const isProduction = process.env.NODE_ENV === 'production';
export const isTest = process.env.NODE_ENV === 'test';

// Feature flags
export const FEATURES = {
  enableMockData: isDevelopment || isTest,
  enableDetailedLogging: isDevelopment,
  enableAnalytics: isProduction,
};

// Timeouts
export const TIMEOUTS = {
  apiRequest: 30000, // 30 seconds
  geocoding: 10000,  // 10 seconds
};

// Default settings
export const DEFAULTS = {
  maxQuestions: 10,
  confidenceThreshold: 80, // Minimum confidence score to consider a rectification reliable
};

// Test environment detection
export const isTestEnvironment = () => {
  if (typeof window === 'undefined') return false;

  return (
    window.__testingBypassGeocodingValidation === true ||
    window.__testMode === true ||
    window.navigator.userAgent.includes('Playwright') ||
    window.navigator.userAgent.includes('HeadlessChrome')
  );
};
