/**
 * Questionnaire Service - Handles questionnaire API interactions
 */
import axios from 'axios';
import { API_BASE_URL } from '@/config';

/**
 * Generate a personalized questionnaire based on birth details
 * @param {Object} birthDetails - The user's birth details
 * @param {Object} options - Optional parameters
 * @returns {Promise<Object>} - The generated questionnaire
 */
export const generateQuestionnaire = async (birthDetails, options = {}) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/v1/questionnaire/generate`, {
      birth_details: birthDetails,
      ...options
    });

    return response.data;
  } catch (error) {
    console.error('Error generating questionnaire:', error);
    throw new Error('Failed to generate questionnaire. Please try again later.');
  }
};

/**
 * Submit questionnaire answers for birth time rectification
 * @param {Object} birthDetails - The user's birth details
 * @param {Array} answers - The user's answers to the questionnaire
 * @param {string} sessionId - Optional session ID for continuing a session
 * @returns {Promise<Object>} - The rectification results
 */
export const submitQuestionnaire = async (birthDetails, answers = [], sessionId = null) => {
  try {
    const payload = {
      birth_details: birthDetails,
      answers: answers
    };

    if (sessionId) {
      payload.session_id = sessionId;
    }

    const response = await axios.post(`${API_BASE_URL}/api/v1/questionnaire/analyze`, payload);

    return response.data;
  } catch (error) {
    console.error('Error submitting questionnaire:', error);
    throw new Error('Failed to submit questionnaire. Please try again later.');
  }
};

/**
 * Get session information by session ID
 * @param {string} sessionId - The session ID
 * @returns {Promise<Object>} - The session information
 */
export const getSession = async (sessionId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/v1/questionnaire/sessions/${sessionId}`);

    return response.data;
  } catch (error) {
    console.error('Error getting session:', error);
    throw new Error('Failed to retrieve session information. Please try again later.');
  }
};

/**
 * Update session with additional information
 * @param {string} sessionId - The session ID
 * @param {Object} data - The data to update
 * @returns {Promise<Object>} - The updated session
 */
export const updateSession = async (sessionId, data) => {
  try {
    const response = await axios.put(`${API_BASE_URL}/api/v1/questionnaire/sessions/${sessionId}`, data);

    return response.data;
  } catch (error) {
    console.error('Error updating session:', error);
    throw new Error('Failed to update session. Please try again later.');
  }
};
