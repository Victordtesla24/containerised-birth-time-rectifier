/**
 * Chart Service - Handles chart generation and retrieval from API
 */
import axios from 'axios';

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generate an astrological chart based on birth details
 *
 * @param {Object} birthDetails - Birth details from the form
 * @param {string} birthDetails.birthDate - Birth date in YYYY-MM-DD format
 * @param {string} birthDetails.birthTime - Birth time in HH:MM:SS format
 * @param {number} birthDetails.latitude - Latitude of birth location
 * @param {number} birthDetails.longitude - Longitude of birth location
 * @param {string} birthDetails.timezone - Timezone name (e.g., 'America/New_York')
 * @param {Object} options - Optional chart generation options
 * @returns {Promise<Object>} - Generated chart data
 */
export const generateChart = async (birthDetails, options = {}) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/charts/generate`, {
      birthDate: birthDetails.birthDate,
      birthTime: birthDetails.birthTime || '00:00:00',
      latitude: parseFloat(birthDetails.latitude),
      longitude: parseFloat(birthDetails.longitude),
      timezone: birthDetails.timezone,
      options: {
        house_system: options.houseSystem || 'P',
        zodiac_type: options.zodiacType || 'tropical',
        ayanamsa: options.ayanamsa || 'lahiri',
        chart_type: options.chartType || 'all'
      }
    });

    return response.data;
  } catch (error) {
    console.error('Error generating chart:', error);
    throw new Error(error.response?.data?.detail || 'Failed to generate chart');
  }
};

/**
 * Retrieve a chart by its ID
 *
 * @param {string} chartId - ID of the chart to retrieve
 * @returns {Promise<Object>} - Chart data
 */
export const getChart = async (chartId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/charts/${chartId}`);
    return response.data;
  } catch (error) {
    console.error('Error retrieving chart:', error);
    throw new Error(error.response?.data?.detail || 'Failed to retrieve chart');
  }
};

/**
 * Compare two charts and calculate differences
 *
 * @param {string} chartId1 - ID of the first chart
 * @param {string} chartId2 - ID of the second chart
 * @returns {Promise<Object>} - Comparison results
 */
export const compareCharts = async (chartId1, chartId2) => {
  try {
    const response = await axios.post(`${API_BASE_URL}/api/charts/compare`, {
      chartId1,
      chartId2
    });
    return response.data;
  } catch (error) {
    console.error('Error comparing charts:', error);
    throw new Error(error.response?.data?.detail || 'Failed to compare charts');
  }
};
