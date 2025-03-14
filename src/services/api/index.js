/**
 * Centralized API Gateway
 *
 * This module serves as the main entry point for all API services,
 * providing a unified interface for the application to interact with
 * the backend services.
 */

import apiClient from './client';
import endpoints from './endpoints';
import { sessionService } from './services/session';
import sessionManager from './services/sessionManager';
import chartService from './services/chart';
import geocodeService from './services/geocode';
import questionnaireService from './services/questionnaire';

/**
 * API Gateway that consolidates all API-related functionality
 */
const apiGateway = {
  // Core API client and endpoints
  client: apiClient,
  endpoints,

  // Service modules
  session: sessionService,
  sessionManager,
  chart: chartService,
  geocode: geocodeService,
  questionnaire: questionnaireService,

  /**
   * Initialize the API gateway
   * Sets up necessary session and authentication
   *
   * @returns {Promise<{initialized: boolean, session?: object, error?: Error}>}
   */
  initialize: async () => {
    try {
      // Set test mode if in test environment
      if (process.env.NODE_ENV === 'test') {
        if (typeof window !== 'undefined') {
          window.__testMode = true;
        }
      }

      // Skip session initialization in SSR context
      if (typeof window === 'undefined') {
        return { initialized: true, ssr: true };
      }

      // Use the advanced session manager for robust session handling
      const sessionResult = await sessionManager.initialize();

      return {
        initialized: true,
        session: sessionResult.session,
        error: sessionResult.error
      };
    } catch (error) {
      console.error('Failed to initialize API gateway:', error);

      // Return initialization failed but don't throw to prevent app crashes
      return { initialized: false, error };
    }
  },

  /**
   * Handle a standard API error with improved error details
   *
   * @param {Error} error - The error object from an API call
   * @returns {object} Standardized error object with code, message, and details
   */
  handleError: (error) => {
    // If the error has already been processed by our interceptor
    if (error.standardizedError) {
      return error.standardizedError;
    }

    // Default error structure
    const errorResponse = {
      code: 'UNKNOWN_ERROR',
      message: error.message || 'An unknown error occurred',
      details: {}
    };

    // Extract additional information from response if available
    if (error.response) {
      errorResponse.code = `HTTP_${error.response.status}`;
      errorResponse.status = error.response.status;

      // Try to extract structured error info if present
      if (error.response.data) {
        if (error.response.data.error) {
          // Already in expected format
          return error.response.data.error;
        } else if (typeof error.response.data === 'object') {
          // Add response data to details
          errorResponse.details = error.response.data;
          // Try to extract message if available
          if (error.response.data.message) {
            errorResponse.message = error.response.data.message;
          }
        }
      }
    }

    return errorResponse;
  },

  /**
   * Check if the app is running in test mode
   *
   * @returns {boolean} True if in test mode
   */
  isTestMode: () => {
    return (
      typeof window !== 'undefined' &&
      (window.__testMode === true || process.env.NODE_ENV === 'test')
    );
  }
};

export default apiGateway;

// Also export individual components for direct imports if needed
export {
  apiClient,
  endpoints,
  sessionService,
  sessionManager,
  chartService,
  geocodeService,
  questionnaireService
};
