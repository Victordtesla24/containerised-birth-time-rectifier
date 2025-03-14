/**
 * Python Backend API Client
 *
 * This utility provides a client for communicating with the Python backend services.
 * It handles the connection, error handling, and response formatting.
 */

import axios from 'axios';
import { logger } from './logger';

// Configure the Python backend URL
// In Docker, use the service name instead of localhost
const PYTHON_BACKEND_URL = process.env.API_SERVICE_URL || process.env.NEXT_PUBLIC_API_SERVICE_URL || 'http://ai_service:8000';

// Create an Axios instance for the Python backend
const pythonClient = axios.create({
  baseURL: PYTHON_BACKEND_URL,
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add request interceptor
pythonClient.interceptors.request.use(
  (config) => {
    logger.debug(`Making request to Python backend: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    logger.error('Error in Python backend request:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor
pythonClient.interceptors.response.use(
  (response) => {
    logger.debug(`Received response from Python backend: ${response.status}`);
    return response.data;
  },
  (error) => {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      logger.error(`Python backend error: ${error.response.status}`, error.response.data);

      // Return a standardized error format
      return Promise.reject({
        status: error.response.status,
        error: error.response.data.error || 'python_backend_error',
        message: error.response.data.message || 'Error received from Python backend'
      });
    } else if (error.request) {
      // The request was made but no response was received
      logger.error('Python backend did not respond', error.request);
      return Promise.reject({
        status: 503,
        error: 'service_unavailable',
        message: 'Python backend service is unavailable'
      });
    } else {
      // Something happened in setting up the request that triggered an Error
      logger.error('Error setting up Python backend request', error.message);
      return Promise.reject({
        status: 500,
        error: 'internal_server_error',
        message: 'Error setting up request to Python backend'
      });
    }
  }
);

/**
 * Generate a chart using the Python backend
 *
 * @param {Object} chartParams - Chart generation parameters
 * @param {string} chartParams.birth_date - Birth date in YYYY-MM-DD format
 * @param {string} chartParams.birth_time - Birth time in HH:MM:SS format
 * @param {number} chartParams.latitude - Birth latitude
 * @param {number} chartParams.longitude - Birth longitude
 * @param {string} chartParams.timezone - Timezone string
 * @param {Object} chartParams.options - Optional chart calculation options
 * @returns {Promise<Object>} The generated chart data
 */
export async function generateChart(chartParams) {
  try {
    return await pythonClient.post('/api/chart/generate', chartParams);
  } catch (error) {
    logger.error('Error generating chart with Python backend:', error);
    throw error;
  }
}

/**
 * Rectify birth time using the Python backend
 *
 * @param {Object} rectifyParams - Rectification parameters
 * @param {string} rectifyParams.chart_id - Chart ID
 * @param {Array} rectifyParams.answers - Questionnaire answers
 * @param {Object} rectifyParams.birth_time_range - Optional birth time range
 * @returns {Promise<Object>} The rectification result
 */
export async function rectifyBirthTime(rectifyParams) {
  try {
    return await pythonClient.post('/api/chart/rectify', rectifyParams);
  } catch (error) {
    logger.error('Error rectifying birth time with Python backend:', error);
    throw error;
  }
}

/**
 * Generate a personalized questionnaire using the Python backend
 *
 * @param {Object} questionnaireParams - Questionnaire generation parameters
 * @param {string} questionnaireParams.chart_id - Chart ID to base questions on
 * @returns {Promise<Object>} The generated questionnaire data
 */
export async function generateQuestionnaire(questionnaireParams) {
  try {
    return await pythonClient.post('/api/questionnaire/generate', questionnaireParams);
  } catch (error) {
    logger.error('Error generating questionnaire with Python backend:', error);
    throw error;
  }
}

/**
 * Submit questionnaire answers using the Python backend
 *
 * @param {Object} answerParams - Answer submission parameters
 * @param {string} answerParams.questionnaire_id - Questionnaire ID
 * @param {Array} answerParams.answers - List of answers
 * @returns {Promise<Object>} The submission result
 */
export async function submitQuestionnaireAnswers(answerParams) {
  try {
    return await pythonClient.post('/api/questionnaire/submit', answerParams);
  } catch (error) {
    logger.error('Error submitting questionnaire answers with Python backend:', error);
    throw error;
  }
}

/**
 * Validate birth details using the Python backend
 *
 * @param {Object} validateParams - Validation parameters
 * @returns {Promise<Object>} The validation result
 */
export async function validateBirthDetails(validateParams) {
  try {
    return await pythonClient.post('/api/chart/validate', validateParams);
  } catch (error) {
    logger.error('Error validating birth details with Python backend:', error);
    throw error;
  }
}

/**
 * Check if the Python backend is available
 *
 * @returns {Promise<boolean>} True if the backend is available
 */
export async function isPythonBackendAvailable() {
  try {
    await pythonClient.get('/health');
    return true;
  } catch (error) {
    logger.warn('Python backend is not available:', error);
    return false;
  }
}

// Export the client for direct use if needed
export default pythonClient;
