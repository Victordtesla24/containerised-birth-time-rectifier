/**
 * API Service Configuration
 *
 * This file provides configuration values and utilities for API services.
 */

/**
 * Get the base URL for API requests
 */
export const getBaseApiUrl = (): string => {
  // Use environment variable if available
  if (typeof window !== 'undefined') {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
    if (apiUrl) return apiUrl;
  }

  // Default to relative URL (same-origin) if no environment variable is set
  return '/api';
};

/**
 * Get the base URL for WebSocket connections
 */
export function getBaseWebSocketUrl(): string {
  // Use environment variables if available
  if (typeof window !== 'undefined') {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
    if (wsUrl) return wsUrl;

    // Default to constructing URL from window location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/ws`;
  }

  // Server-side default
  return process.env.WS_URL || 'ws://localhost:8000/ws';
}

/**
 * Get headers for API requests
 */
export const getDefaultHeaders = (sessionToken?: string): Record<string, string> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Add session token if available
  if (sessionToken) {
    headers['X-Session-ID'] = sessionToken;
  }

  return headers;
};

/**
 * API endpoint paths
 */
export const API_ENDPOINTS = {
  SESSION: {
    INIT: '/api/v1/session/init',
  },
  CHART: {
    GENERATE: '/api/v1/chart/generate',
    RECTIFY: '/api/v1/chart/rectify',
    COMPARE: '/api/v1/chart/compare',
    EXPORT: '/api/v1/chart/export',
  },
  QUESTIONNAIRE: {
    NEXT: '/api/v1/questionnaire/next',
    ANSWER: '/api/v1/questionnaire/answer',
    COMPLETE: '/api/v1/questionnaire/complete',
  },
  GEOCODE: {
    SEARCH: '/api/v1/geocode',
  },
};
