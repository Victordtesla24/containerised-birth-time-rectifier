/**
 * Test constants for the astrological chart application
 * This file defines API endpoints and test data used across the e2e tests
 */

/**
 * API Endpoints used by the application
 * The paths should match the actual API implementation in the backend
 *
 * API structure follows the dual-registration pattern:
 *
 * 1. Primary endpoints (with /api/ prefix):
 *    - Chart-related endpoints follow nested routing: `/api/chart/[endpoint]`
 *    - Other service endpoints follow flat routing: `/api/[endpoint]`
 *
 * 2. Alternative endpoints (without /api/ prefix):
 *    - Chart-related endpoints: `/chart/[endpoint]`
 *    - Other service endpoints: `/[endpoint]`
 *
 * Both endpoint patterns are supported for backward compatibility,
 * but primary endpoints with `/api/` prefix are recommended for new development.
 */
export const API_ENDPOINTS = {
    // Primary endpoints (with /api/ prefix)
    validate: '/api/chart/validate',
    geocode: '/api/geocode',
    chartGenerate: '/api/chart/generate',
    chartById: '/api/chart/{id}',
    questionnaire: '/api/questionnaire',
    rectify: '/api/chart/rectify',
    export: '/api/chart/export',
    health: '/api/health',
    // AI model integration test endpoints
    aiTest: '/api/ai/test_explanation',
    aiModelRouting: '/api/ai/test_model_routing',
    aiUsageStats: '/api/ai/usage_statistics',

    // Alternative endpoints without /api/ prefix (for backward compatibility)
    validateAlt: '/chart/validate',
    geocodeAlt: '/geocode',
    chartGenerateAlt: '/chart/generate',
    chartByIdAlt: '/chart/{id}',
    questionnaireAlt: '/questionnaire',
    rectifyAlt: '/chart/rectify',
    exportAlt: '/chart/export',
    healthAlt: '/health',
    // AI model integration test endpoints (alternative)
    aiTestAlt: '/ai/test_explanation',
    aiModelRoutingAlt: '/ai/test_model_routing',
    aiUsageStatsAlt: '/ai/usage_statistics',

    // Session management
    sessionInit: '/api/session/init',
    sessionInitAlt: '/session/init'
};

/**
 * Test data used across different test cases
 */
export const TEST_DATA = {
    // Standard test case for happy path
    STANDARD: {
        birthDate: '1985-10-24',
        birthTime: '14:30',
        birthPlace: 'Pune, India',
        latitude: 18.52,
        longitude: 73.86,
        timezone: 'Asia/Kolkata'
    },

    // Test case for validation errors
    INVALID: {
        birthDate: '',  // Empty date
        birthTime: '99:99',  // Invalid time in valid format for HTML5 time inputs
        birthPlace: '',  // Empty place
        // No coordinates as geocoding will fail
    },

    // Test case for low confidence AI analysis
    LOW_CONFIDENCE: {
        birthDate: '1990-03-15',
        birthTime: '03:45',
        birthPlace: 'Berlin, Germany',
        latitude: 52.52,
        longitude: 13.41,
        timezone: 'Europe/Berlin',
        // This data will trigger low confidence in AI analysis
    },

    // Test cases for boundary conditions
    BOUNDARY: {
        // Testing polar coordinates
        polarTest: {
            birthDate: '1980-12-01',
            birthTime: '12:00',
            birthPlace: 'Longyearbyen, Svalbard',
            latitude: 78.22,
            longitude: 15.65,
            timezone: 'Arctic/Longyearbyen'
        },

        // Testing international date line crossing
        dateLineTest: {
            birthDate: '1975-06-15',
            birthTime: '18:30',
            birthPlace: 'Suva, Fiji',
            latitude: -18.14,
            longitude: 178.44,
            timezone: 'Pacific/Fiji'
        },

        // Testing equator crossing
        equatorTest: {
            birthDate: '1995-09-23',
            birthTime: '09:15',
            birthPlace: 'Quito, Ecuador',
            latitude: 0.18,
            longitude: -78.47,
            timezone: 'America/Guayaquil'
        }
    }
};

/**
 * Utility functions for tests
 */
export const testUtils = {
    /**
     * Waits for a network request to complete
     * @param {Page} page - Playwright page object
     * @param {string} urlPattern - URL pattern to match
     * @param {number} timeout - Timeout in milliseconds
     */
    waitForRequest: async (page, urlPattern, timeout = 30000) => {
        return page.waitForRequest(
            request => request.url().includes(urlPattern),
            { timeout }
        );
    },

    /**
     * Waits for a network response to complete
     * @param {Page} page - Playwright page object
     * @param {string} urlPattern - URL pattern to match
     * @param {number} timeout - Timeout in milliseconds
     */
    waitForResponse: async (page, urlPattern, timeout = 30000) => {
        return page.waitForResponse(
            response => response.url().includes(urlPattern),
            { timeout }
        );
    },

    /**
     * Formats a date string to YYYY-MM-DD format
     * @param {Date} date - Date object
     * @returns {string} Formatted date string
     */
    formatDate: (date) => {
        return date.toISOString().split('T')[0];
    },

    /**
     * Formats a time string to HH:MM format
     * @param {Date} date - Date object
     * @returns {string} Formatted time string
     */
    formatTime: (date) => {
        return date.toISOString().split('T')[1].substring(0, 5);
    },

    /**
     * Tries both primary and alternative endpoints
     * Useful for testing the dual-registration pattern
     *
     * @param {string} baseUrl - Base URL for the API
     * @param {string} primaryEndpoint - Primary endpoint with /api/ prefix
     * @param {string} altEndpoint - Alternative endpoint without /api/ prefix
     * @param {string} method - HTTP method (GET, POST, etc.)
     * @param {object} payload - Request payload for non-GET requests
     * @returns {Promise<object>} Response from the first successful endpoint
     */
    tryBothEndpoints: async (baseUrl, primaryEndpoint, altEndpoint, method = 'GET', payload = null) => {
        // Try primary endpoint first
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            };

            if (payload && method !== 'GET') {
                options.body = JSON.stringify(payload);
            }

            const primaryResponse = await fetch(`${baseUrl}${primaryEndpoint}`, options);
            if (primaryResponse.ok) {
                return {
                    response: primaryResponse,
                    usedEndpoint: primaryEndpoint,
                    isAlternative: false
                };
            }
        } catch (error) {
            console.log(`Primary endpoint ${primaryEndpoint} failed: ${error.message}`);
        }

        // If primary fails, try alternative
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
            };

            if (payload && method !== 'GET') {
                options.body = JSON.stringify(payload);
            }

            const altResponse = await fetch(`${baseUrl}${altEndpoint}`, options);
            if (altResponse.ok) {
                return {
                    response: altResponse,
                    usedEndpoint: altEndpoint,
                    isAlternative: true
                };
            }
        } catch (error) {
            console.log(`Alternative endpoint ${altEndpoint} failed: ${error.message}`);
        }

        throw new Error(`Both endpoints failed: ${primaryEndpoint} and ${altEndpoint}`);
    }
}
