/**
 * Python API Adapter
 *
 * This utility provides a direct adapter for the Python backend API when needed,
 * while still using the unified API client infrastructure for consistency.
 */

import axios from 'axios';
import { logger } from './logger';
import { GATEWAY_CONFIG } from '../config/apiGateway';

// Configure the Python backend URL
const PYTHON_BACKEND_URL = process.env.API_SERVICE_URL ||
                           process.env.NEXT_PUBLIC_API_SERVICE_URL ||
                           'http://ai_service:8000';

/**
 * Create a direct API client for the Python backend
 * This is helpful for special endpoints not covered by the unified API client
 * or for direct backend access during development
 */
const createDirectPythonClient = () => {
  // Create a new axios instance specific to the Python backend
  const pythonClient = axios.create({
    baseURL: PYTHON_BACKEND_URL,
    timeout: GATEWAY_CONFIG.defaultTimeout || 30000,
    headers: {
      'Content-Type': 'application/json'
    }
  });

  // Add request interceptor for logging and session handling
  pythonClient.interceptors.request.use(
    (config) => {
      logger.debug(`Making direct request to Python backend: ${config.method?.toUpperCase()} ${config.url}`);

      // Add session token if available
      const sessionToken = localStorage.getItem('sessionToken');
      if (sessionToken) {
        config.headers['X-Session-Token'] = sessionToken;
      }

      return config;
    },
    (error) => {
      logger.error('Error in direct Python backend request:', error);
      return Promise.reject(error);
    }
  );

  // Add response interceptor for standardized error handling
  pythonClient.interceptors.response.use(
    (response) => {
      logger.debug(`Received direct response from Python backend: ${response.status}`);
      return response.data;
    },
    (error) => {
      // Use the same error handling pattern as the unified client
      if (error.response) {
        logger.error(`Python backend error: ${error.response.status}`, error.response.data);
        return Promise.reject({
          error: {
            code: error.response.data?.error?.code || `HTTP_${error.response.status}`,
            message: error.response.data?.error?.message || 'Error received from Python backend',
            details: error.response.data?.error?.details || {},
            status: error.response.status
          }
        });
      } else if (error.request) {
        logger.error('Python backend did not respond', error.request);
        return Promise.reject({
          error: {
            code: 'SERVICE_UNAVAILABLE',
            message: 'Python backend service is unavailable',
            details: {},
            status: 503
          }
        });
      } else {
        logger.error('Error setting up Python backend request', error.message);
        return Promise.reject({
          error: {
            code: 'INTERNAL_SERVER_ERROR',
            message: 'Error setting up request to Python backend',
            details: {},
            status: 500
          }
        });
      }
    }
  );

  return pythonClient;
};

// Create the Python client instance
const pythonClient = createDirectPythonClient();

/**
 * Direct access to OpenAI verification features
 */
const openaiService = {
  /**
   * Verify a chart using OpenAI against Vedic standards
   * @param {Object} chartData - The chart data to verify
   * @returns {Promise<Object>} Verification result with confidence score
   */
  verifyChart: async (chartData) => {
    try {
      return await pythonClient.post('/api/openai/verify-chart', chartData);
    } catch (error) {
      logger.error('Error verifying chart with OpenAI:', error);
      throw error;
    }
  },

  /**
   * Analyze birth time rectification data with OpenAI
   * @param {Object} rectificationData - Data for rectification analysis
   * @returns {Promise<Object>} Analysis results with confidence score
   */
  analyzeBirthTimeData: async (rectificationData) => {
    try {
      return await pythonClient.post('/api/openai/analyze-birth-time', rectificationData);
    } catch (error) {
      logger.error('Error analyzing birth time data with OpenAI:', error);
      throw error;
    }
  }
};

/**
 * Direct access to advanced chart features
 */
const advancedChartService = {
  /**
   * Generate a detailed chart with extended data
   * @param {Object} params - Chart parameters with advanced options
   * @returns {Promise<Object>} Enhanced chart data
   */
  generateDetailedChart: async (params) => {
    try {
      return await pythonClient.post('/api/chart/detailed', params);
    } catch (error) {
      logger.error('Error generating detailed chart:', error);
      throw error;
    }
  },

  /**
   * Generate additional chart data not included in standard endpoints
   * @param {Object} params - Chart parameters
   * @returns {Promise<Object>} Specialized chart data
   */
  generateSpecializedData: async (params) => {
    try {
      return await pythonClient.post('/api/chart/specialized', params);
    } catch (error) {
      logger.error('Error generating specialized chart data:', error);
      throw error;
    }
  }
};

/**
 * Direct access to WebSocket features
 */
const realtimeService = {
  /**
   * Get WebSocket connection details
   * @returns {Promise<Object>} WebSocket connection information
   */
  getWebSocketDetails: async () => {
    try {
      return await pythonClient.get('/api/websocket/connection-info');
    } catch (error) {
      logger.error('Error getting WebSocket connection details:', error);
      throw error;
    }
  }
};

/**
 * Utility for checking backend availability
 * @returns {Promise<boolean>} True if backend is available
 */
const checkBackendAvailability = async () => {
  try {
    await pythonClient.get('/health');
    return true;
  } catch (error) {
    logger.warn('Python backend is not available:', error);
    return false;
  }
};

// Combine all services
const pythonApiAdapter = {
  // Specialized services
  openaiService,
  advancedChartService,
  realtimeService,

  // Utility functions
  checkBackendAvailability,

  // Direct access to raw client for advanced use cases
  client: pythonClient
};

export default pythonApiAdapter;
