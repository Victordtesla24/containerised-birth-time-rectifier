/**
 * Unified API Client
 *
 * Centralized client for all API interactions, providing:
 * - Standardized error handling
 * - Automatic session token management
 * - Request/response transformation
 * - Service-specific methods
 */

import axios from 'axios';
import { ENDPOINTS, GATEWAY_CONFIG, LEGACY_ENDPOINTS } from '../config/apiGateway';

/**
 * Create the core axios instance with default configuration
 */
const apiClient = axios.create({
  timeout: GATEWAY_CONFIG.defaultTimeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor to add session token and handle common request tasks
 */
apiClient.interceptors.request.use(
  (config) => {
    // Add session token to headers if available
    const sessionToken = localStorage.getItem('sessionToken');
    if (sessionToken) {
      config.headers['X-Session-Token'] = sessionToken;
    }

    // Log request in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor to handle errors and transform responses
 */
apiClient.interceptors.response.use(
  (response) => {
    // Process successful responses
    return response.data;
  },
  async (error) => {
    // Get the original request
    const originalRequest = error.config;

    // Handle network errors
    if (!error.response) {
      return Promise.reject({
        error: {
          code: 'NETWORK_ERROR',
          message: 'Network error: Cannot connect to server',
          details: error.message,
        }
      });
    }

    // Handle 404 errors - specially for API version migration
    if (error.response.status === 404 && !originalRequest._alternate_route_attempted) {
      const originalUrl = originalRequest.url;

      // Check if we have an alternative endpoint mapping for this URL
      let alternateUrl = null;

      // Handle versioned endpoints first
      if (originalUrl.startsWith('/api/v1/')) {
        // Try without version
        alternateUrl = originalUrl.replace('/api/v1/', '/api/');
        console.log(`API Gateway: Trying alternate endpoint ${alternateUrl} for ${originalUrl}`);
      } else if (originalUrl.startsWith('/api/')) {
        // Check if there's a legacy route without '/api/' prefix
        const pathWithoutApi = originalUrl.replace('/api/', '/');
        if (LEGACY_ENDPOINTS[pathWithoutApi]) {
          alternateUrl = pathWithoutApi;
          console.log(`API Gateway: Trying legacy endpoint ${alternateUrl} for ${originalUrl}`);
        }
      }

      // If we have an alternate URL, retry with that
      if (alternateUrl) {
        originalRequest.url = alternateUrl;
        originalRequest._alternate_route_attempted = true;
        return apiClient(originalRequest);
      }
    }

    // Handle retry for 5xx errors
    if (error.response.status >= 500 && !originalRequest._retry &&
        GATEWAY_CONFIG.retry.maxRetries > 0) {

      originalRequest._retry = (originalRequest._retry || 0) + 1;

      // Implement exponential backoff
      const delay = GATEWAY_CONFIG.retry.initialDelayMs *
        Math.pow(GATEWAY_CONFIG.retry.backoffFactor, (originalRequest._retry - 1));

      // Wait and retry
      await new Promise(resolve => setTimeout(resolve, delay));
      return apiClient(originalRequest);
    }

    // Handle validation errors specifically
    if (error.response.status === 422) {
      // Format validation errors in a more user-friendly way
      return Promise.reject({
        error: {
          code: 'VALIDATION_ERROR',
          message: 'The provided data is invalid.',
          details: error.response?.data?.detail || error.response?.data?.error?.details || {},
          status: error.response.status,
          fields: error.response?.data?.detail || {} // Field-specific validation errors
        }
      });
    }

    // Standardize error format
    const errorResponse = {
      error: {
        code: error.response?.data?.error?.code || `HTTP_${error.response.status}`,
        message: error.response?.data?.error?.message || error.message || 'Unknown error',
        details: error.response?.data?.error?.details || {},
        status: error.response.status,
      }
    };

    // Check for session expiration (401)
    if (error.response.status === 401) {
      // Trigger session refresh if implemented
      // This would call sessionService.refresh() or similar
      // If refresh fails, could redirect to login/home
    }

    return Promise.reject(errorResponse);
  }
);

/**
 * Session Service - handles session management
 */
const sessionService = {
  /**
   * Initialize a new session
   * @param {Object} options - Session options
   * @returns {Promise<Object>} Session data
   */
  initSession: async (options = {}) => {
    const response = await apiClient.post(ENDPOINTS.session.init, options);
    if (response.token) {
      localStorage.setItem('sessionToken', response.token);
    }
    return response;
  },

  /**
   * Refresh the current session
   * @returns {Promise<Object>} Updated session data
   */
  refreshSession: async () => {
    const response = await apiClient.post(ENDPOINTS.session.refresh);
    if (response.token) {
      localStorage.setItem('sessionToken', response.token);
    }
    return response;
  },

  /**
   * Check session status
   * @returns {Promise<Object>} Session status
   */
  checkStatus: async () => {
    return await apiClient.get(ENDPOINTS.session.status);
  },

  /**
   * End the current session
   * @returns {Promise<Object>} End session confirmation
   */
  endSession: async () => {
    const response = await apiClient.post(ENDPOINTS.session.end);
    localStorage.removeItem('sessionToken');
    return response;
  },

  /**
   * Get the current session token
   * @returns {string|null} The session token or null if not available
   */
  getSessionToken: () => {
    return localStorage.getItem('sessionToken');
  },
};

/**
 * Chart Service - handles chart-related operations
 */
const chartService = {
  /**
   * Validate birth details
   * @param {Object} birthDetails - Birth details to validate
   * @returns {Promise<Object>} Validation result
   */
  validateBirthDetails: async (birthDetails) => {
    return await apiClient.post(ENDPOINTS.chart.validate, birthDetails);
  },

  /**
   * Generate a birth chart
   * @param {Object} birthDetails - Birth details for chart generation
   * @returns {Promise<Object>} Generated chart data
   */
  generateChart: async (birthDetails) => {
    return await apiClient.post(ENDPOINTS.chart.generate, birthDetails);
  },

  /**
   * Get a chart by ID
   * @param {string} chartId - The chart ID to retrieve
   * @returns {Promise<Object>} Chart data
   */
  getChart: async (chartId) => {
    return await apiClient.get(`${ENDPOINTS.chart.get}/${chartId}`);
  },

  /**
   * Rectify a birth chart
   * @param {Object} rectifyParams - Parameters for rectification
   * @returns {Promise<Object>} Rectified chart data
   */
  rectifyChart: async (rectifyParams) => {
    return await apiClient.post(ENDPOINTS.chart.rectify, rectifyParams);
  },

  /**
   * Compare two charts
   * @param {string} chartId1 - First chart ID
   * @param {string} chartId2 - Second chart ID
   * @returns {Promise<Object>} Comparison results
   */
  compareCharts: async (chartId1, chartId2) => {
    // Use the updated chart-comparison endpoint
    return await apiClient.get(`${ENDPOINTS.chart.compare}?chart1=${chartId1}&chart2=${chartId2}`);
  },

  /**
   * Export a chart
   * @param {string} chartId - Chart ID to export
   * @param {Object} options - Export options
   * @returns {Promise<Object>} Export data
   */
  exportChart: async (chartId, options = {}) => {
    return await apiClient.post(`${ENDPOINTS.chart.export}/${chartId}`, options);
  },
};

/**
 * Geocoding Service - handles location-related operations
 */
const geocodeService = {
  /**
   * Search for a location
   * @param {string} query - Location search query
   * @returns {Promise<Object>} Location search results
   */
  searchLocation: async (query) => {
    return await apiClient.get(`${ENDPOINTS.geocode.search}?query=${encodeURIComponent(query)}`);
  },

  /**
   * Get location suggestions
   * @param {string} query - Partial location name
   * @returns {Promise<Object>} Location suggestions
   */
  getLocationSuggestions: async (query) => {
    return await apiClient.get(`${ENDPOINTS.geocode.suggestions}?query=${encodeURIComponent(query)}`);
  },
};

/**
 * Questionnaire Service - handles questionnaire-related operations
 */
const questionnaireService = {
  /**
   * Generate a questionnaire
   * @param {Object} params - Parameters for questionnaire generation
   * @returns {Promise<Object>} Generated questionnaire
   */
  generateQuestionnaire: async (params) => {
    return await apiClient.post(ENDPOINTS.questionnaire.generate, params);
  },

  /**
   * Submit an answer to a questionnaire
   * @param {string} id - Questionnaire ID
   * @param {Object} answer - Answer data
   * @returns {Promise<Object>} Next question or completion
   */
  submitAnswer: async (id, answer) => {
    return await apiClient.post(`${ENDPOINTS.questionnaire.answer}/${id}`, answer);
  },

  /**
   * Complete a questionnaire
   * @param {string} id - Questionnaire ID
   * @returns {Promise<Object>} Questionnaire completion results
   */
  completeQuestionnaire: async (id) => {
    return await apiClient.post(`${ENDPOINTS.questionnaire.complete}/${id}`);
  },
};

/**
 * Export Service - handles export-related operations
 */
const exportService = {
  /**
   * Download an exported document
   * @param {string} id - Export ID
   * @returns {Promise<Blob>} Document as binary data
   */
  downloadExport: async (id) => {
    // Use different axios settings for binary data
    const response = await axios.get(`${ENDPOINTS.export.download}/${id}`, {
      responseType: 'blob',
    });
    return response.data;
  },
};

/**
 * Health Service - handles health checks
 */
const healthService = {
  /**
   * Check API health status
   * @returns {Promise<Object>} Health status
   */
  checkHealth: async () => {
    return await apiClient.get(ENDPOINTS.health);
  },
};

/**
 * Utility function to handle API errors consistently
 * @param {Object} error - Error object from API client
 * @param {Function} fallback - Optional fallback function
 * @returns {Object} Standardized error object
 */
export const handleApiError = (error, fallback = null) => {
  console.error('[API Error]', error);

  // If a fallback is provided and this is a server error, try the fallback
  if (fallback && error?.error?.status >= 500) {
    return fallback();
  }

  // Return standardized error
  return {
    error: error?.error || {
      code: 'UNKNOWN_ERROR',
      message: error?.message || 'An unknown error occurred',
      details: {},
    }
  };
};

// Unified API client with all services
const unifiedApiClient = {
  // Core services
  sessionService,
  chartService,
  geocodeService,
  questionnaireService,
  exportService,
  healthService,

  // Utility functions
  handleApiError,

  // Expose the raw client for advanced usage
  rawClient: apiClient,
};

export default unifiedApiClient;
