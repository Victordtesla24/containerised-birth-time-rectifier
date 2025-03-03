/**
 * Questionnaire Service - Handles questionnaire API interactions
 */
import axios from 'axios';

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generate a personalized questionnaire based on birth details
 *
 * @param {Object} birthDetails - Birth details from the form
 * @param {Object} options - Optional questionnaire generation options
 * @param {Object} options.previousAnswers - Previous answers, if any
 * @param {number} options.currentConfidence - Current confidence score
 * @param {string[]} options.focusAreas - Areas to focus questions on
 * @param {number} options.maxQuestions - Maximum number of questions to generate
 * @returns {Promise<Object>} - Generated questionnaire
 */
export const generateQuestionnaire = async (birthDetails, options = {}) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/questionnaire`, {
      birthDetails: {
        name: birthDetails.name,
        birthDate: birthDetails.birthDate,
        birthTime: birthDetails.birthTime || '00:00:00',
        latitude: parseFloat(birthDetails.latitude),
        longitude: parseFloat(birthDetails.longitude),
        timezone: birthDetails.timezone,
        gender: birthDetails.gender,
        location: birthDetails.location
      },
      previousAnswers: options.previousAnswers || {},
      currentConfidence: options.currentConfidence || 0,
      focusAreas: options.focusAreas || [],
      maxQuestions: options.maxQuestions || 10
    });

    return response.data;
  } catch (error) {
    console.error('Error generating questionnaire:', error);
    throw new Error(error.response?.data?.detail || 'Failed to generate questionnaire');
  }
};

/**
 * Submit questionnaire answers for birth time rectification
 *
 * @param {Object} birthDetails - Birth details from the form
 * @param {Array} answers - Array of question answers
 * @param {string} sessionId - Questionnaire session ID
 * @returns {Promise<Object>} - Birth time rectification results
 */
export const submitQuestionnaire = async (birthDetails, answers, sessionId) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/questionnaire/rectify`, {
      birthDetails: {
        name: birthDetails.name,
        birthDate: birthDetails.birthDate,
        birthTime: birthDetails.birthTime || '00:00:00',
        latitude: parseFloat(birthDetails.latitude),
        longitude: parseFloat(birthDetails.longitude),
        timezone: birthDetails.timezone,
        gender: birthDetails.gender,
        location: birthDetails.location
      },
      answers: answers,
      sessionId: sessionId
    });

    return response.data;
  } catch (error) {
    console.error('Error submitting questionnaire:', error);
    throw new Error(error.response?.data?.detail || 'Failed to process questionnaire');
  }
};

/**
 * Get session information
 *
 * @param {string} sessionId - Questionnaire session ID
 * @returns {Promise<Object>} - Session data
 */
export const getSession = async (sessionId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/questionnaire/sessions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error retrieving session:', error);
    throw new Error(error.response?.data?.detail || 'Failed to retrieve session');
  }
};
