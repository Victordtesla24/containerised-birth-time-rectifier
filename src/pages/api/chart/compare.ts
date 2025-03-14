import type { NextApiRequest, NextApiResponse } from 'next';

type ChartComparisonResponse = {
  success?: boolean;
  message?: string;
  error?: string;
  comparison_id?: string;
  comparison_data?: any;
  differences?: any[];
  original_chart?: any;
  rectified_chart?: any;
};

/**
 * Chart Comparison API Endpoint
 *
 * This endpoint allows comparison between original and rectified charts
 * to visualize the differences and their astrological significance.
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ChartComparisonResponse>
) {
  // Allow GET for retrieving comparison and POST for creating
  if (req.method !== 'GET' && req.method !== 'POST') {
    return res.status(405).json({
      success: false,
      error: 'Method not allowed'
    });
  }

  try {
    // Get AI service URL from environment or use default
    const aiServiceUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';
    let response;

    if (req.method === 'GET') {
      // Extract comparison ID from query
      const { id, type = 'full' } = req.query;

      if (!id) {
        return res.status(400).json({
          success: false,
          message: 'Comparison ID is required'
        });
      }

      // Call the backend service to retrieve the comparison
      response = await fetch(`${aiServiceUrl}/api/chart/compare/${id}?type=${type}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': req.headers['x-session-token'] as string || '',
        }
      });
    } else {
      // POST request to create a comparison
      const {
        originalChartId,
        rectifiedChartId,
        originalTime,
        rectifiedTime,
        comparisonType = 'full'
      } = req.body;

      // Validate required fields
      if (!originalChartId || !rectifiedChartId) {
        return res.status(400).json({
          success: false,
          message: 'Both original and rectified chart IDs are required'
        });
      }

      // Call the backend service to create a comparison
      response = await fetch(`${aiServiceUrl}/api/chart/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': req.headers['x-session-token'] as string || '',
        },
        body: JSON.stringify({
          original_chart_id: originalChartId,
          rectified_chart_id: rectifiedChartId,
          original_time: originalTime,
          rectified_time: rectifiedTime,
          comparison_type: comparisonType
        }),
      });
    }

    // Handle API response
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: 'Failed to parse API error response'
      }));

      const statusCode = response.status;
      const errorMessage = errorData.detail || errorData.message ||
        `Chart comparison service responded with status ${statusCode}`;

      console.error('Chart comparison service error:', errorMessage);

      return res.status(statusCode).json({
        success: false,
        error: errorMessage
      });
    }

    // Successfully got data from backend service
    const data = await response.json();

    // Store comparison data in session if available (for POST requests)
    if (req.method === 'POST' && typeof window !== 'undefined' && data.comparison_id) {
      try {
        sessionStorage.setItem('chartComparison', JSON.stringify({
          comparisonId: data.comparison_id,
          originalChart: data.original_chart,
          rectifiedChart: data.rectified_chart,
          differences: data.differences
        }));
      } catch (e) {
        console.warn('Failed to store comparison data in session storage', e);
      }
    }

    return res.status(200).json({
      success: true,
      comparison_id: data.comparison_id,
      comparison_data: data.comparison_data,
      differences: data.differences,
      original_chart: data.original_chart,
      rectified_chart: data.rectified_chart,
      message: data.message || 'Chart comparison successful'
    });

  } catch (error) {
    console.error('Error comparing charts:', error);
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error'
    });
  }
}
