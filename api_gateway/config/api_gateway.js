/**
 * API Gateway Configuration
 *
 * This file defines all API endpoints and metadata for the Birth Time Rectifier application.
 * It is used by both the frontend Unified API Client and the API Gateway Handler.
 */

const API_VERSION = "v1";
const API_PREFIX = `/api/${API_VERSION}`;

const ENDPOINTS = {
  // Chart related endpoints
  CHART_GENERATE: `${API_PREFIX}/chart/generate`,
  CHART_GET: `${API_PREFIX}/chart/:id`,
  CHART_VALIDATE: `${API_PREFIX}/chart/validate`,
  CHART_COMPARE: `${API_PREFIX}/chart/compare`,
  CHART_RECTIFY: `${API_PREFIX}/chart/rectify`,
  CHART_EXPORT: `${API_PREFIX}/chart/export`,

  // Geocoding endpoint
  GEOCODE: `${API_PREFIX}/geocode`,

  // Questionnaire endpoints
  QUESTIONNAIRE_INIT: `${API_PREFIX}/questionnaire/initialize`,
  QUESTIONNAIRE_NEXT: `${API_PREFIX}/questionnaire/:session_id/next`,
  QUESTIONNAIRE_ANSWER: `${API_PREFIX}/questionnaire/:session_id/answer`,
  QUESTIONNAIRE_COMPLETE: `${API_PREFIX}/questionnaire/complete`,

  // Session management
  SESSION_INIT: `${API_PREFIX}/session/init`,
  SESSION_STATUS: `${API_PREFIX}/session/status`,
  SESSION_DATA: `${API_PREFIX}/session/data`,

  // Health check
  HEALTH: `${API_PREFIX}/health`,

  // AI status
  AI_STATUS: `${API_PREFIX}/ai/status`
};

// Legacy endpoints for backward compatibility
const LEGACY_ENDPOINTS = {
  // Chart related endpoints without /api prefix
  CHART_GENERATE_LEGACY: `/chart/generate`,
  CHART_GET_LEGACY: `/chart/:id`,
  CHART_VALIDATE_LEGACY: `/chart/validate`,
  CHART_COMPARE_LEGACY: `/chart/compare`,
  CHART_RECTIFY_LEGACY: `/chart/rectify`,
  CHART_EXPORT_LEGACY: `/chart/export`,

  // Other endpoints without /api prefix
  GEOCODE_LEGACY: `/geocode`,
  QUESTIONNAIRE_INIT_LEGACY: `/questionnaire/initialize`,
  SESSION_INIT_LEGACY: `/session/init`,
  HEALTH_LEGACY: `/health`,

  // API endpoints without version
  CHART_GENERATE_V0: `/api/chart/generate`,
  CHART_GET_V0: `/api/chart/:id`,
  GEOCODE_V0: `/api/geocode`,
};

// Endpoint metadata for client generation and documentation
const ENDPOINT_METADATA = {
  CHART_GENERATE: {
    description: "Generate an astrological chart based on birth details",
    method: "POST",
    requiredParams: ["birth_date", "birth_time", "latitude", "longitude"],
    optionalParams: ["location", "timezone", "verify_with_openai", "house_system", "zodiac_type"],
    permissions: [],
    rateLimited: true
  },
  CHART_GET: {
    description: "Retrieve an existing chart by ID",
    method: "GET",
    requiredParams: ["id"],
    optionalParams: [],
    permissions: [],
    rateLimited: false
  },
  CHART_VALIDATE: {
    description: "Validate birth details before generating a chart",
    method: "POST",
    requiredParams: ["birth_date", "birth_time", "latitude", "longitude"],
    optionalParams: ["timezone"],
    permissions: [],
    rateLimited: true
  },
  CHART_COMPARE: {
    description: "Compare two charts and highlight differences",
    method: "POST",
    requiredParams: ["chart1_id", "chart2_id"],
    optionalParams: ["comparison_type", "include_significance"],
    permissions: [],
    rateLimited: false
  },
  CHART_RECTIFY: {
    description: "Rectify birth time based on questionnaire answers",
    method: "POST",
    requiredParams: ["chart_id", "questionnaire_responses"],
    optionalParams: ["include_details"],
    permissions: [],
    rateLimited: true
  },
  CHART_EXPORT: {
    description: "Export a chart in various formats",
    method: "POST",
    requiredParams: ["chart_id", "format"],
    optionalParams: ["include_verification", "include_aspects"],
    permissions: [],
    rateLimited: false
  },
  GEOCODE: {
    description: "Geocode a location to get coordinates and timezone",
    method: "POST",
    requiredParams: ["query"],
    optionalParams: ["limit", "include_timezone"],
    permissions: [],
    rateLimited: true
  },
  SESSION_INIT: {
    description: "Initialize a new session",
    method: "GET",
    requiredParams: [],
    optionalParams: [],
    permissions: [],
    rateLimited: false
  },
  HEALTH: {
    description: "Check health status of the service",
    method: "GET",
    requiredParams: [],
    optionalParams: [],
    permissions: [],
    rateLimited: false
  }
};

module.exports = {
  API_VERSION,
  API_PREFIX,
  ENDPOINTS,
  LEGACY_ENDPOINTS,
  ENDPOINT_METADATA
};
