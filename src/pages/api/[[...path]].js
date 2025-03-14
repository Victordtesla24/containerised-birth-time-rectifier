/**
 * Unified API Gateway Handler
 *
 * This catch-all Next.js API route serves as the central gateway for all API requests.
 * It handles:
 * - Request forwarding to the Python backend
 * - Path rewriting and versioning
 * - Session management
 * - Error handling and standardization
 * - Legacy endpoint mapping
 */

import { createProxyMiddleware } from 'http-proxy-middleware';
import { GATEWAY_CONFIG, LEGACY_ENDPOINTS, API_PREFIX } from '../../config/apiGateway';
import nc from 'next-connect';

// Setup next-connect handler with error handling
const handler = nc({
  onError: (err, req, res) => {
    console.error('API Gateway Error:', err);
    res.status(500).json({
      error: {
        code: err.code || 'GATEWAY_ERROR',
        message: err.message || 'An unexpected error occurred',
        details: err.stack || {},
      }
    });
  },
  onNoMatch: (req, res) => {
    res.status(404).json({
      error: {
        code: 'ENDPOINT_NOT_FOUND',
        message: `Cannot ${req.method} ${req.url}`,
        details: { method: req.method, url: req.url },
      }
    });
  },
});

// Add session middleware
const addSessionMiddleware = (req, res, next) => {
  // Get session token from headers or cookies
  const sessionToken = req.headers['x-session-token'] ||
                      (req.cookies && req.cookies.sessionToken);

  if (sessionToken) {
    // Add session token to the request for future middleware and backend
    req.sessionToken = sessionToken;

    // Add to headers to ensure it's sent to the backend
    req.headers['x-session-token'] = sessionToken;
  }

  // Continue processing
  next();
};

// Add logging middleware
const addLoggingMiddleware = (req, res, next) => {
  // Log request details in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[API Gateway] ${req.method} ${req.url}`);

    // Log request body for non-GET requests if not too large
    if (req.method !== 'GET' && req.body &&
        JSON.stringify(req.body).length < 1000) {
      console.log('[API Gateway] Request Body:', req.body);
    }
  }

  // Track response timing
  const startTime = Date.now();

  // Override res.end to add response logging
  const originalEnd = res.end;
  res.end = function(...args) {
    const duration = Date.now() - startTime;

    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Gateway] Response: ${res.statusCode} (${duration}ms)`);
    }

    return originalEnd.apply(this, args);
  };

  next();
};

// Apply session and logging middleware
handler.use(addSessionMiddleware);
handler.use(addLoggingMiddleware);

// Legacy endpoint handler with enhanced path handling
const handleLegacyEndpoint = (req, res, next) => {
  const path = req.url.split('?')[0]; // Remove query string

  // Check for specific known problematic endpoints
  if (path === '/chart/validate' || path === '/api/chart/validate') {
    // Special handling for validation endpoint which was causing issues
    const newPath = '/api/v1/chart/validate';

    // Add a deprecation warning header
    res.setHeader('X-Deprecation-Warning',
      `This endpoint is deprecated. Please use ${newPath} instead.`);

    // Rewrite the URL
    req.url = newPath + (req.url.includes('?') ? req.url.substring(req.url.indexOf('?')) : '');

    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Gateway] Special path mapped: ${path} -> ${newPath}`);
    }
  }
  // Check if this is a legacy endpoint that needs mapping
  else if (LEGACY_ENDPOINTS[path]) {
    // Map to standardized endpoint
    const newPath = LEGACY_ENDPOINTS[path];

    // Add a deprecation warning header
    res.setHeader('X-Deprecation-Warning',
      `This endpoint is deprecated. Please use ${newPath} instead.`);

    // Rewrite the URL
    req.url = newPath + (req.url.includes('?') ? req.url.substring(req.url.indexOf('?')) : '');

    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Gateway] Legacy path mapped: ${path} -> ${newPath}`);
    }
  }

  next();
};

// Apply legacy endpoint handling
handler.use(handleLegacyEndpoint);

// Handle dynamic path parameters (like :id)
const handleDynamicPaths = (req, res, next) => {
  // Extract path components
  const pathWithoutQuery = req.url.split('?')[0];
  const pathParts = pathWithoutQuery.split('/').filter(Boolean);

  // Process dynamic segments
  // Example: If URL is /api/v1/chart/123/compare
  // We extract 'chart' as the resource and '123' as the id
  if (pathParts.length >= 2) {
    const version = pathParts[1] === 'v1' ? pathParts[1] : null;
    const resourceStartIndex = version ? 2 : 1;

    const resource = pathParts[resourceStartIndex];

    if (pathParts.length > resourceStartIndex + 1) {
      // Check if the next segment is an ID (non-word characters typically suggest an operation, not ID)
      if (!/^\w+$/.test(pathParts[resourceStartIndex + 1])) {
        req.resourceId = pathParts[resourceStartIndex + 1];
      }
    }

    // Store for future reference
    req.apiResource = resource;
    req.apiVersion = version;
  }

  next();
};

// Apply dynamic path handling
handler.use(handleDynamicPaths);

// Configure the proxy middleware
const proxy = createProxyMiddleware({
  target: GATEWAY_CONFIG.proxy.target,
  changeOrigin: true,
  pathRewrite: {
    ...GATEWAY_CONFIG.proxy.pathRewrite,
    // Ensure chart comparison endpoint works with all variations
    '^/api/chart/compare': '/api/chart/chart-comparison',
    '^/api/v1/chart/compare': '/api/chart/chart-comparison',
    '^/chart/compare': '/api/chart/chart-comparison',
  },
  logLevel: process.env.NODE_ENV === 'development' ? 'debug' : 'silent',

  // Custom handler for proxy responses
  onProxyRes: (proxyRes, req, res) => {
    // Handle error responses
    if (proxyRes.statusCode >= 400) {
      console.error(`[API Gateway] Backend error: ${proxyRes.statusCode} for ${req.url}`);
    }

    // Add gateway version header
    proxyRes.headers['x-api-gateway-version'] = '1.0';
  },

  // Custom error handler
  onError: (err, req, res) => {
    console.error('[API Gateway] Proxy error:', err);

    res.status(500).json({
      error: {
        code: 'BACKEND_CONNECTION_ERROR',
        message: 'Cannot connect to the backend service',
        details: {
          originalError: err.message,
        },
      }
    });
  },
});

// Process all API requests with the proxy
handler.all('*', (req, res) => {
  // Forward the request to the backend
  return proxy(req, res);
});

export default handler;

// Configure Next.js to handle all HTTP methods
export const config = {
  api: {
    bodyParser: true,
    externalResolver: true,
  },
};
