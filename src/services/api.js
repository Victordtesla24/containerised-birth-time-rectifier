/**
 * API Service Module
 * This file is maintained for backward compatibility.
 * It re-exports the new centralized API Gateway to avoid breaking changes.
 */

import apiGateway, {
  apiClient,
  sessionService,
  chartService,
  geocodeService,
  questionnaireService
} from './api/index';

// Export the main API client for backward compatibility
const api = apiClient;
export default api;

// Re-export the session API service for backward compatibility
export const sessionApi = {
  initSession: sessionService.initSession,
  checkStatus: sessionService.checkStatus
};

// Re-export the geocoding API service for backward compatibility
export const geocodeApi = {
  geocodeLocation: geocodeService.geocodeLocation
};

// Re-export the chart API service for backward compatibility
export const chartApi = {
  generateChart: chartService.generateChart,
  getChart: chartService.getChart
};

// Initialize the API gateway when this module is imported
apiGateway.initialize().catch(error => {
  console.error('Failed to initialize API gateway during import:', error);
});

// Also export the full API gateway
export const api_gateway = apiGateway;
