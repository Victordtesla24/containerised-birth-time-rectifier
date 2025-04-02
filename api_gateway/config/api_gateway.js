/**
 * API Gateway Configuration
 *
 * This file defines all API endpoints and metadata for the Birth Time Rectifier application.
 * All endpoints use the standardized /api/v1/ prefix.
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

// Endpoint metadata for documentation and client usage
const ENDPOINT_METADATA = {
  CHART_GENERATE: {
    description: "Generate a new birth chart",
    method: "POST",
    requiredParams: ["birth_details"],
    optionalParams: ["chart_type", "verify_with_openai"],
    permissions: [],
    rateLimited: true
  },
  CHART_GET: {
    description: "Get a specific birth chart by ID",
    method: "GET",
    requiredParams: ["id"],
    optionalParams: [],
    permissions: [],
    rateLimited: false
  },
  CHART_VALIDATE: {
    description: "Validate birth details for chart generation",
    method: "POST",
    requiredParams: ["birth_details"],
    optionalParams: [],
    permissions: [],
    rateLimited: true
  },
  CHART_COMPARE: {
    description: "Compare two birth charts",
    method: "GET",
    requiredParams: ["chart1", "chart2"],
    optionalParams: ["comparison_type"],
    permissions: [],
    rateLimited: true
  },
  CHART_RECTIFY: {
    description: "Rectify a birth chart based on questionnaire answers",
    method: "POST",
    requiredParams: ["chart_id", "session_id"],
    optionalParams: ["questionnaire_id"],
    permissions: [],
    rateLimited: true
  },
  CHART_EXPORT: {
    description: "Export a birth chart to a specified format",
    method: "POST",
    requiredParams: ["chart_id", "format"],
    optionalParams: ["include_aspects", "include_interpretations"],
    permissions: [],
    rateLimited: true
  },
  GEOCODE: {
    description: "Geocode a location string to coordinates and timezone",
    method: "GET",
    requiredParams: ["query"],
    optionalParams: ["limit", "include_timezone"],
    permissions: [],
    rateLimited: true
  },
  QUESTIONNAIRE_INIT: {
    description: "Initialize a new questionnaire session",
    method: "GET",
    requiredParams: ["chart_id"],
    optionalParams: ["questionnaire_type"],
    permissions: [],
    rateLimited: false
  },
  QUESTIONNAIRE_NEXT: {
    description: "Get the next question in a questionnaire",
    method: "GET",
    requiredParams: ["session_id"],
    optionalParams: [],
    permissions: [],
    rateLimited: false
  },
  QUESTIONNAIRE_ANSWER: {
    description: "Submit an answer to a questionnaire question",
    method: "POST",
    requiredParams: ["session_id", "answer"],
    optionalParams: ["confidence"],
    permissions: [],
    rateLimited: false
  },
  QUESTIONNAIRE_COMPLETE: {
    description: "Mark a questionnaire as complete",
    method: "POST",
    requiredParams: ["session_id"],
    optionalParams: [],
    permissions: [],
    rateLimited: false
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
  ENDPOINT_METADATA
};
