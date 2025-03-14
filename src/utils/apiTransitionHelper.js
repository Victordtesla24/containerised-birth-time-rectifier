/**
 * API Transition Helper
 *
 * This utility provides compatibility functions to transition from the legacy pythonBackendClient
 * to the new unifiedApiClient with minimal code changes in existing components.
 */

import unifiedApiClient from './unifiedApiClient';
import { logger } from './logger';

/**
 * Compatibility layer for the legacy generateChart function
 *
 * @param {Object} chartParams - Chart generation parameters
 * @returns {Promise<Object>} The generated chart data
 */
export async function generateChart(chartParams) {
  try {
    logger.info('Using unified API client for chart generation (transitional helper)');
    return await unifiedApiClient.chartService.generateChart(chartParams);
  } catch (error) {
    logger.error('Error generating chart with unified API client:', error);
    throw error;
  }
}

/**
 * Compatibility layer for the legacy rectifyBirthTime function
 *
 * @param {Object} rectifyParams - Rectification parameters
 * @returns {Promise<Object>} The rectification result
 */
export async function rectifyBirthTime(rectifyParams) {
  try {
    logger.info('Using unified API client for birth time rectification (transitional helper)');
    return await unifiedApiClient.chartService.rectifyChart(rectifyParams);
  } catch (error) {
    logger.error('Error rectifying birth time with unified API client:', error);
    throw error;
  }
}

/**
 * Compatibility layer for the legacy generateQuestionnaire function
 *
 * @param {Object} questionnaireParams - Questionnaire generation parameters
 * @returns {Promise<Object>} The generated questionnaire data
 */
export async function generateQuestionnaire(questionnaireParams) {
  try {
    logger.info('Using unified API client for questionnaire generation (transitional helper)');
    return await unifiedApiClient.questionnaireService.generateQuestionnaire(questionnaireParams);
  } catch (error) {
    logger.error('Error generating questionnaire with unified API client:', error);
    throw error;
  }
}

/**
 * Compatibility layer for the legacy submitQuestionnaireAnswers function
 *
 * @param {Object} answerParams - Answer submission parameters
 * @returns {Promise<Object>} The submission result
 */
export async function submitQuestionnaireAnswers(answerParams) {
  try {
    logger.info('Using unified API client for submitting questionnaire answers (transitional helper)');
    // Map the legacy structure to the new API
    if (answerParams.questionnaire_id && answerParams.answers) {
      return await unifiedApiClient.questionnaireService.submitAnswer(
        answerParams.questionnaire_id,
        { answers: answerParams.answers }
      );
    } else {
      return await unifiedApiClient.questionnaireService.submitAnswer(answerParams.id, answerParams);
    }
  } catch (error) {
    logger.error('Error submitting questionnaire answers with unified API client:', error);
    throw error;
  }
}

/**
 * Compatibility layer for the legacy validateBirthDetails function
 *
 * @param {Object} validateParams - Validation parameters
 * @returns {Promise<Object>} The validation result
 */
export async function validateBirthDetails(validateParams) {
  try {
    logger.info('Using unified API client for birth details validation (transitional helper)');
    return await unifiedApiClient.chartService.validateBirthDetails(validateParams);
  } catch (error) {
    logger.error('Error validating birth details with unified API client:', error);
    throw error;
  }
}

/**
 * Compatibility layer for the legacy isPythonBackendAvailable function
 *
 * @returns {Promise<boolean>} True if the backend is available
 */
export async function isPythonBackendAvailable() {
  try {
    logger.info('Using unified API client for health check (transitional helper)');
    await unifiedApiClient.healthService.checkHealth();
    return true;
  } catch (error) {
    logger.warn('Backend is not available (via unified API client):', error);
    return false;
  }
}

// Legacy compatibility default export that mimics the original pythonBackendClient
// This makes it possible to use:
// import pythonBackendClient from '../utils/pythonBackendClient'
// without changing the code
const legacyCompatClient = {
  get: async (url, config) => {
    logger.info(`Legacy GET request to ${url} via unified API client`);
    return await unifiedApiClient.rawClient.get(url, config);
  },
  post: async (url, data, config) => {
    logger.info(`Legacy POST request to ${url} via unified API client`);
    return await unifiedApiClient.rawClient.post(url, data, config);
  },
  put: async (url, data, config) => {
    logger.info(`Legacy PUT request to ${url} via unified API client`);
    return await unifiedApiClient.rawClient.put(url, data, config);
  },
  delete: async (url, config) => {
    logger.info(`Legacy DELETE request to ${url} via unified API client`);
    return await unifiedApiClient.rawClient.delete(url, config);
  }
};

export default legacyCompatClient;
