import type { NextApiRequest, NextApiResponse } from 'next';

type ExportResponse = {
  success?: boolean;
  message?: string;
  error?: string;
  url?: string;
  export_id?: string;
};

/**
 * Chart Export API Endpoint
 *
 * This endpoint handles the generation of PDF reports for astrological charts
 * and birth time rectification results.
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ExportResponse>
) {
  // We only support GET requests for export
  if (req.method !== 'GET' && req.method !== 'POST') {
    return res.status(405).json({
      success: false,
      error: 'Method not allowed'
    });
  }

  try {
    // Get chart ID from query params or body
    const chartId = req.method === 'GET'
      ? req.query.chartId as string
      : req.body.chartId;

    // Get comparison ID from query params or body (optional)
    const comparisonId = req.method === 'GET'
      ? req.query.comparisonId as string
      : req.body.comparisonId;

    // Get export type from query params or body (optional)
    const exportType = req.method === 'GET'
      ? (req.query.type as string) || 'pdf'
      : req.body.type || 'pdf';

    // Validate required fields
    if (!chartId && !comparisonId) {
      return res.status(400).json({
        success: false,
        message: 'Either chart ID or comparison ID is required'
      });
    }

    // Get AI service URL from environment or use default
    const aiServiceUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    // Determine endpoint based on what's being exported
    let endpoint = '';
    let requestBody = {};

    if (chartId) {
      endpoint = `/api/chart/export/${chartId}?type=${exportType}`;
      requestBody = { chart_id: chartId, export_type: exportType };
    } else if (comparisonId) {
      endpoint = `/api/chart/export-comparison/${comparisonId}?type=${exportType}`;
      requestBody = { comparison_id: comparisonId, export_type: exportType };
    }

    // Call the backend service
    const response = await fetch(`${aiServiceUrl}${endpoint}`, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': req.headers['x-session-token'] as string || '',
      },
      ...(req.method === 'POST' && { body: JSON.stringify(requestBody) }),
    });

    // Handle API response
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: 'Failed to parse API error response'
      }));

      const statusCode = response.status;
      const errorMessage = errorData.detail || errorData.message ||
        `Export service responded with status ${statusCode}`;

      console.error('Export service error:', errorMessage);

      return res.status(statusCode).json({
        success: false,
        error: errorMessage
      });
    }

    // Successfully got data from backend service
    const data = await response.json();

    return res.status(200).json({
      success: true,
      url: data.url,
      export_id: data.export_id,
      message: data.message || 'Export generated successfully'
    });

  } catch (error) {
    console.error('Error exporting chart:', error);
    return res.status(500).json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error'
    });
  }
}
