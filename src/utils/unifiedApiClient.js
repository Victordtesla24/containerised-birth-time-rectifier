/**
 * Unified API Client
 *
 * This module provides a centralized way for the frontend application to interact with all API endpoints.
 * It includes service objects for different API areas, error handling, request interceptors, and response transformation.
 */

import axios from 'axios';
import { API_PREFIX, ENDPOINTS } from '../../api_gateway/config/api_gateway';

// Default configuration for the API client
const defaultConfig = {
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  validateStatus: status => status < 500 // Consider only 5xx as errors
};

// Create base axios instance with default configuration
const apiClient = axios.create(defaultConfig);

// Session token storage and management
let sessionToken = null;

// Request interceptor for automatic session token injection
apiClient.interceptors.request.use(config => {
  // Add session token if available
  if (sessionToken) {
    config.headers['X-Session-ID'] = sessionToken;
  }

  // Add timestamp for debugging/cache busting
  config.headers['X-Request-Time'] = new Date().toISOString();

  return config;
}, error => {
  console.error('Request error:', error);
  return Promise.reject(error);
});

// Response interceptor for error handling and transformation
apiClient.interceptors.response.use(response => {
  // Transform successful responses if needed
  return response.data;
}, error => {
  // Handle errors consistently
  let errorMessage = 'An unknown error occurred';
  let errorCode = 'UNKNOWN_ERROR';
  let statusCode = 500;

  if (error.response) {
    // Server responded with an error status
    statusCode = error.response.status;

    if (error.response.data && error.response.data.error) {
      // Extract structured error info if available
      errorMessage = error.response.data.error.message || error.response.data.error;
      errorCode = error.response.data.error.code || `ERROR_${statusCode}`;
    } else {
      // Fallback error message
      errorMessage = `Server error: ${statusCode}`;
      errorCode = `SERVER_ERROR_${statusCode}`;
    }
  } else if (error.request) {
    // Request was made but no response received
    errorMessage = 'No response received from server';
    errorCode = 'NO_RESPONSE';
  } else {
    // Request configuration error
    errorMessage = error.message || 'Error setting up the request';
    errorCode = 'REQUEST_SETUP_ERROR';
  }

  // Create normalized error object
  const normalizedError = {
    message: errorMessage,
    code: errorCode,
    status: statusCode,
    originalError: error
  };

  // Log errors in development
  if (process.env.NODE_ENV !== 'production') {
    console.error('API Error:', normalizedError);
  }

  // Reject promise with normalized error
  return Promise.reject(normalizedError);
});

/**
 * Initialize a session for the client.
 *
 * @returns {Promise<Object>} Session data including session ID
 */
const initSession = async () => {
  try {
    const response = await apiClient.get(ENDPOINTS.SESSION_INIT);
    if (response && response.session_id) {
      sessionToken = response.session_id;
      localStorage.setItem('sessionToken', sessionToken);
    }
    return response;
  } catch (error) {
    console.error('Session initialization failed:', error);
    throw error;
  }
};

/**
 * Load session from local storage if available.
 */
const loadSession = () => {
  const storedToken = localStorage.getItem('sessionToken');
  if (storedToken) {
    sessionToken = storedToken;
    return true;
  }
  return false;
};

/**
 * Clear the current session.
 */
const clearSession = () => {
  sessionToken = null;
  localStorage.removeItem('sessionToken');
};

/**
 * Chart Service - Methods for chart-related API endpoints
 */
const chartService = {
  /**
   * Generate a new chart based on birth details.
   *
   * @param {Object} birthDetails Birth details including date, time, and location
   * @param {Object} options Chart generation options
   * @returns {Promise<Object>} Generated chart data
   */
  generateChart: async (birthDetails, options = {}) => {
    const payload = {
      birth_date: birthDetails.birthDate,
      birth_time: birthDetails.birthTime,
      latitude: birthDetails.latitude,
      longitude: birthDetails.longitude,
      location: birthDetails.location || '',
      timezone: birthDetails.timezone || 'UTC',
      verify_with_openai: options.verifyWithOpenai !== false, // Default to true
      house_system: options.houseSystem || 'P',
      zodiac_type: options.zodiacType || 'sidereal'
    };

    return apiClient.post(ENDPOINTS.CHART_GENERATE, payload);
  },

  /**
   * Retrieve a chart by ID.
   *
   * @param {string} chartId The ID of the chart to retrieve
   * @returns {Promise<Object>} Chart data
   */
  getChart: async (chartId) => {
    return apiClient.get(ENDPOINTS.CHART_GET.replace(':id', chartId));
  },

  /**
   * Validate birth details before generating a chart.
   *
   * @param {Object} birthDetails Birth details to validate
   * @returns {Promise<Object>} Validation results
   */
  validateBirthDetails: async (birthDetails) => {
    return apiClient.post(ENDPOINTS.CHART_VALIDATE, {
      birth_details: {
        birth_date: birthDetails.birthDate,
        birth_time: birthDetails.birthTime,
        latitude: birthDetails.latitude,
        longitude: birthDetails.longitude,
        timezone: birthDetails.timezone || 'UTC'
      }
    });
  },

  /**
   * Compare two charts to identify differences.
   *
   * @param {string} chart1Id ID of the first chart
   * @param {string} chart2Id ID of the second chart
   * @param {Object} options Comparison options
   * @returns {Promise<Object>} Comparison results
   */
  compareCharts: async (chart1Id, chart2Id, options = {}) => {
    const payload = {
      chart1_id: chart1Id,
      chart2_id: chart2Id,
      comparison_type: options.comparisonType || 'differences',
      include_significance: options.includeSignificance !== false // Default to true
    };

    return apiClient.post(ENDPOINTS.CHART_COMPARE, payload);
  },

  /**
   * Rectify birth time based on questionnaire responses.
   *
   * @param {string} chartId Chart ID to rectify
   * @param {Array} questionnaireResponses List of questionnaire responses
   * @param {Object} options Rectification options
   * @returns {Promise<Object>} Rectification results
   */
  rectifyBirthTime: async (chartId, questionnaireResponses, options = {}) => {
    const payload = {
      chart_id: chartId,
      questionnaire_responses: questionnaireResponses,
      include_details: options.includeDetails || false
    };

    return apiClient.post(ENDPOINTS.CHART_RECTIFY, payload);
  },

  /**
   * Export a chart in the specified format.
   *
   * @param {string} chartId Chart ID to export
   * @param {string} format Export format (pdf, png, json)
   * @param {Object} options Export options
   * @returns {Promise<Object>} Export results including download URL
   */
  exportChart: async (chartId, format = 'pdf', options = {}) => {
    const payload = {
      chart_id: chartId,
      format: format,
      include_verification: options.includeVerification || false,
      include_aspects: options.includeAspects !== false // Default to true
    };

    return apiClient.post(ENDPOINTS.CHART_EXPORT, payload);
  }
};

/**
 * Geocode Service - Methods for location geocoding
 */
const geocodeService = {
  /**
   * Geocode a location to get coordinates and timezone.
   *
   * @param {string} query Location to geocode
   * @param {Object} options Geocoding options
   * @returns {Promise<Object>} Geocoding results
   */
  geocodeLocation: async (query, options = {}) => {
    const payload = {
      query: query,
      limit: options.limit || 5,
      include_timezone: options.includeTimezone !== false // Default to true
    };

    return apiClient.post(ENDPOINTS.GEOCODE, payload);
  }
};

/**
 * Questionnaire Service - Methods for dynamic questionnaire
 */
const questionnaireService = {
  /**
   * Initialize a new questionnaire.
   *
   * @param {Object} birthDetails Birth details for personalized questions
   * @returns {Promise<Object>} Questionnaire initialization data
   */
  initQuestionnaire: async (birthDetails) => {
    return apiClient.post(ENDPOINTS.QUESTIONNAIRE_INIT, {
      birth_details: birthDetails
    });
  },

  /**
   * Get the next question in the questionnaire.
   *
   * @param {string} sessionId Session ID for the questionnaire
   * @returns {Promise<Object>} Next question data
   */
  getNextQuestion: async (sessionId) => {
    return apiClient.get(ENDPOINTS.QUESTIONNAIRE_NEXT.replace(':session_id', sessionId));
  },

  /**
   * Submit an answer to a question.
   *
   * @param {string} sessionId Session ID for the questionnaire
   * @param {string} questionId ID of the question being answered
   * @param {any} answer Answer to the question
   * @returns {Promise<Object>} Response with next question or completion status
   */
  submitAnswer: async (sessionId, questionId, answer) => {
    return apiClient.post(ENDPOINTS.QUESTIONNAIRE_ANSWER.replace(':session_id', sessionId), {
      question_id: questionId,
      answer: answer
    });
  },

  /**
   * Complete the questionnaire and get rectification results.
   *
   * @param {string} sessionId Session ID for the questionnaire
   * @param {string} chartId Chart ID to associate with rectification
   * @returns {Promise<Object>} Completion results with rectification data
   */
  completeQuestionnaire: async (sessionId, chartId) => {
    return apiClient.post(ENDPOINTS.QUESTIONNAIRE_COMPLETE, {
      session_id: sessionId,
      chart_id: chartId
    });
  }
};

/**
 * Session Service - Methods for session management
 */
const sessionService = {
  /**
   * Initialize a new session.
   *
   * @returns {Promise<Object>} Session data
   */
  initSession,

  /**
   * Get session status.
   *
   * @returns {Promise<Object>} Session status information
   */
  getSessionStatus: async () => {
    return apiClient.get(`${ENDPOINTS.SESSION_STATUS}?session_id=${sessionToken}`);
  },

  /**
   * Update session data.
   *
   * @param {Object} data Data to store in the session
   * @returns {Promise<Object>} Updated session information
   */
  updateSessionData: async (data) => {
    return apiClient.post(`${ENDPOINTS.SESSION_DATA}?session_id=${sessionToken}`, data);
  },

  /**
   * Get stored session data.
   *
   * @returns {Promise<Object>} Session data
   */
  getSessionData: async () => {
    return apiClient.get(`${ENDPOINTS.SESSION_DATA}?session_id=${sessionToken}`);
  }
};

/**
 * Health Service - Methods for health monitoring
 */
const healthService = {
  /**
   * Check API health status.
   *
   * @returns {Promise<Object>} Health status information
   */
  checkHealth: async () => {
    return apiClient.get(ENDPOINTS.HEALTH);
  }
};

/**
 * AI Status Service - Methods for AI service status
 */
const aiStatusService = {
  /**
   * Get AI status information.
   *
   * @returns {Promise<Object>} AI status data
   */
  getAiStatus: async () => {
    return apiClient.get(ENDPOINTS.AI_STATUS);
  }
};

/**
 * Handle API errors in a standardized way.
 *
 * @param {Object} error Normalized error from API client
 * @param {Function} callback Optional callback for custom error handling
 * @returns {Object} Error information for UI display
 */
const handleApiError = (error, callback) => {
  // Default error info
  const errorInfo = {
    title: 'Error',
    message: error.message || 'An unknown error occurred',
    code: error.code || 'UNKNOWN_ERROR',
    retry: false,
    critical: error.status >= 500
  };

  // Set retry flag for specific errors
  if (error.status === 429 || error.status === 503) {
    errorInfo.retry = true;
    errorInfo.title = 'Service Temporarily Unavailable';
  }

  // Execute callback if provided
  if (callback && typeof callback === 'function') {
    callback(errorInfo, error);
  }

  return errorInfo;
};

// Initialize session from localStorage if available
loadSession();

// Export the Unified API Client
export default {
  // Service objects
  chartService,
  geocodeService,
  questionnaireService,
  sessionService,
  healthService,
  aiStatusService,

  // Session management
  loadSession,
  clearSession,

  // Error handling
  handleApiError,

  // Expose the base axios instance for advanced use cases
  apiClient
};
