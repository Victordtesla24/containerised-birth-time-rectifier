import type { NextRequest } from 'next/server';
import type { NextResponse } from 'next/server';

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
  req: Request
) {
  // We only support GET requests for export
  if (req.method !== 'GET' && req.method !== 'POST') {
    return new Response(JSON.stringify({
      success: false,
      error: 'Method not allowed'
    }), {
      status: 405,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  try {
    const url = new URL(req.url);
    let chartId, comparisonId, exportType;

    if (req.method === 'GET') {
      // Get parameters from URL
      chartId = url.searchParams.get('chartId');
      comparisonId = url.searchParams.get('comparisonId');
      exportType = url.searchParams.get('type') || 'pdf';
    } else {
      // Get parameters from body
      const body = await req.json();
      chartId = body.chartId;
      comparisonId = body.comparisonId;
      exportType = body.type || 'pdf';
    }

    // Validate required fields
    if (!chartId && !comparisonId) {
      return new Response(JSON.stringify({
        success: false,
        message: 'Either chart ID or comparison ID is required'
      }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }

    // Get AI service URL from environment or use default
    const aiServiceUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    // Determine endpoint based on what's being exported
    let endpoint = '';
    let requestBody = {};

    if (chartId) {
      endpoint = `/api/v1/chart/export/${chartId}?type=${exportType}`;
      requestBody = { chart_id: chartId, export_type: exportType };
    } else if (comparisonId) {
      endpoint = `/api/v1/chart/export-comparison/${comparisonId}?type=${exportType}`;
      requestBody = { comparison_id: comparisonId, export_type: exportType };
    }

    // Call the backend service
    const response = await fetch(`${aiServiceUrl}${endpoint}`, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Token': req.headers.get('x-session-token') || '',
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

      return new Response(JSON.stringify({
        success: false,
        error: errorMessage
      }), {
        status: statusCode,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }

    // Successfully got data from backend service
    const data = await response.json();

    return new Response(JSON.stringify({
      success: true,
      url: data.url,
      export_id: data.export_id,
      message: data.message || 'Export generated successfully'
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });

  } catch (error) {
    console.error('Error exporting chart:', error);
    return new Response(JSON.stringify({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error'
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
}
