import type { NextApiRequest, NextApiResponse } from 'next';
import { GATEWAY_CONFIG } from '../../config/apiGateway';
import pkg from '../../../package.json';

// Define interfaces for the health response object
interface BackendConnection {
  status: string;
  statusCode?: number;
  message?: string;
  url: string;
}

interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  uptime: number;
  environment: "development" | "production" | "test";
  nextConfig: {
    hasConfig: boolean;
  };
  buildInfo: {
    nextBuildExists: boolean;
  };
  backendConnection?: BackendConnection;
}

/**
 * Health check endpoint
 *
 * Provides detailed status information about the frontend service
 * and its ability to connect to backend services.
 *
 * @param req - The HTTP request object
 * @param res - The HTTP response object
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  try {
    // Basic health information
    const health: HealthResponse = {
      status: 'ok',
      service: 'frontend',
      version: pkg.version || '1.0.0',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      environment: (process.env.NODE_ENV as "development" | "production" | "test") || "production",
      nextConfig: {
        hasConfig: !!require('../../../next.config.js'),
      },
      buildInfo: {
        nextBuildExists: true, // We'll assume this is true if this endpoint runs
      }
    };

    // Try to check backend connection if requested
    if (req.query.checkBackend === 'true') {
      try {
        const apiUrl = GATEWAY_CONFIG.proxy.target;
        const backendResponse = await fetch(`${apiUrl}/health`, {
          method: 'GET',
          headers: { 'Accept': 'application/json' }
        });

        health.backendConnection = {
          status: backendResponse.status === 200 ? 'ok' : 'error',
          statusCode: backendResponse.status,
          url: apiUrl
        };
      } catch (error: unknown) {
        const backendError = error as Error;
        health.backendConnection = {
          status: 'error',
          message: backendError.message || 'Unknown error occurred',
          url: GATEWAY_CONFIG.proxy.target
        };
      }
    }

    // Return the health status
    res.status(200).json(health);
  } catch (error: unknown) {
    console.error('Health check error:', error);
    const errorObj = error as Error;
    res.status(500).json({
      status: 'error',
      service: 'frontend',
      timestamp: new Date().toISOString(),
      error: errorObj.message || 'Unknown error occurred'
    });
  }
}
