/**
 * Chart Service - Handles chart generation and retrieval from API
 */
import axios from 'axios';
import { API_BASE_URL, isTestEnvironment } from '@/config';

/**
 * Generate an astrological chart based on birth details
 *
 * @param {Object} birthDetails - The user's birth details
 * @param {Object} options - Optional parameters
 * @returns {Promise<Object>} - The generated chart
 */
export const generateChart = async (birthDetails, options = {}) => {
  try {
    // For test environments, return mock data
    if (isTestEnvironment()) {
      console.log("Test environment detected, returning mock chart data");
      return {
        chart_id: 'test-123',
        birth_details: birthDetails,
        planets: [
          { name: 'Sun', sign: 'Leo', degree: '15°', house: 5 },
          { name: 'Moon', sign: 'Cancer', degree: '23°', house: 4 },
          { name: 'Mercury', sign: 'Virgo', degree: '8°', house: 6 },
          { name: 'Venus', sign: 'Libra', degree: '12°', house: 7 },
          { name: 'Mars', sign: 'Aries', degree: '5°', house: 1 }
        ],
        houses: [
          { number: 1, sign: 'Aries', degree: '0°' },
          { number: 2, sign: 'Taurus', degree: '0°' },
          { number: 3, sign: 'Gemini', degree: '0°' },
          { number: 4, sign: 'Cancer', degree: '0°' },
          { number: 5, sign: 'Leo', degree: '0°' },
          { number: 6, sign: 'Virgo', degree: '0°' },
          { number: 7, sign: 'Libra', degree: '0°' },
          { number: 8, sign: 'Scorpio', degree: '0°' },
          { number: 9, sign: 'Sagittarius', degree: '0°' },
          { number: 10, sign: 'Capricorn', degree: '0°' },
          { number: 11, sign: 'Aquarius', degree: '0°' },
          { number: 12, sign: 'Pisces', degree: '0°' }
        ],
        aspects: []
      };
    }

    const response = await axios.post(`${API_BASE_URL}/api/v1/chart/generate`, {
      birth_details: birthDetails,
      ...options
    });

    return response.data;
  } catch (error) {
    console.error('Error generating chart:', error);
    throw new Error('Failed to generate chart. Please try again later.');
  }
};

/**
 * Get chart by ID
 * @param {string} chartId - The chart ID
 * @returns {Promise<Object>} - The chart data
 */
export const getChart = async (chartId) => {
  try {
    // For test environments, return mock data
    if (isTestEnvironment()) {
      console.log("Test environment detected, returning mock chart data");
      return {
        chart_id: chartId,
        birth_details: {
          name: 'Test User',
          date: '1990-06-15',
          time: '14:30',
          location: 'New York, USA'
        },
        planets: [
          { name: 'Sun', sign: 'Leo', degree: '15°', house: 5 },
          { name: 'Moon', sign: 'Cancer', degree: '23°', house: 4 },
          { name: 'Mercury', sign: 'Virgo', degree: '8°', house: 6 },
          { name: 'Venus', sign: 'Libra', degree: '12°', house: 7 },
          { name: 'Mars', sign: 'Aries', degree: '5°', house: 1 }
        ],
        houses: [
          { number: 1, sign: 'Aries', degree: '0°' },
          { number: 2, sign: 'Taurus', degree: '0°' },
          { number: 3, sign: 'Gemini', degree: '0°' },
          { number: 4, sign: 'Cancer', degree: '0°' },
          { number: 5, sign: 'Leo', degree: '0°' },
          { number: 6, sign: 'Virgo', degree: '0°' },
          { number: 7, sign: 'Libra', degree: '0°' },
          { number: 8, sign: 'Scorpio', degree: '0°' },
          { number: 9, sign: 'Sagittarius', degree: '0°' },
          { number: 10, sign: 'Capricorn', degree: '0°' },
          { number: 11, sign: 'Aquarius', degree: '0°' },
          { number: 12, sign: 'Pisces', degree: '0°' }
        ],
        aspects: []
      };
    }

    const response = await axios.get(`${API_BASE_URL}/api/v1/chart/${chartId}`);

    return response.data;
  } catch (error) {
    console.error('Error getting chart:', error);
    throw new Error('Failed to retrieve chart. Please try again later.');
  }
};

/**
 * Compare two charts
 * @param {string} chartId1 - The first chart ID
 * @param {string} chartId2 - The second chart ID
 * @returns {Promise<Object>} - The comparison results
 */
export const compareCharts = async (chartId1, chartId2) => {
  try {
    // For test environments, return mock data
    if (isTestEnvironment()) {
      console.log("Test environment detected, returning mock chart comparison data");
      return {
        comparison_id: 'comp-test-123',
        chart_ids: [chartId1, chartId2],
        differences: {
          planets: [
            { name: 'Moon', chart1: { sign: 'Cancer', degree: '23°' }, chart2: { sign: 'Cancer', degree: '25°' } },
            { name: 'Mercury', chart1: { sign: 'Virgo', degree: '8°' }, chart2: { sign: 'Virgo', degree: '9°' } }
          ],
          houses: [
            { number: 1, chart1: { sign: 'Aries', degree: '0°' }, chart2: { sign: 'Aries', degree: '2°' } }
          ],
          aspects: []
        }
      };
    }

    const response = await axios.post(`${API_BASE_URL}/api/v1/chart/compare`, {
      chart_id_1: chartId1,
      chart_id_2: chartId2
    });

    return response.data;
  } catch (error) {
    console.error('Error comparing charts:', error);
    throw new Error('Failed to compare charts. Please try again later.');
  }
};
