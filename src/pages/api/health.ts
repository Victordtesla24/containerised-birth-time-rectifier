import type { NextApiRequest, NextApiResponse } from 'next';

/**
 * Health check API for integration tests and monitoring
 * 
 * @param req - NextApiRequest object
 * @param res - NextApiResponse object
 */
export default function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Return a simple health check response
  res.status(200).json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'frontend'
  });
} 