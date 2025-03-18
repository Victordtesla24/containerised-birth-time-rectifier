import type { NextRequest } from 'next/server';
import type { NextResponse } from 'next/server';

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
  req: Request
) {
  // Allow GET for retrieving comparison and POST for creating
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
    // Get AI service URL from environment or use default
    const aiServiceUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';
    let response;

    if (req.method === 'GET') {
      // Extract comparison ID from URL
      const url = new URL(req.url);
      const id = url.searchParams.get('id');
      const type = url.searchParams.get('type') || 'full';

      if (!id) {
        return new Response(JSON.stringify({
          success: false,
          message: 'Comparison ID is required'
        }), {
          status: 400,
          headers: {
            'Content-Type': 'application/json'
          }
        });
      }

      // Call the backend service to retrieve the comparison with the correct endpoint
      response = await fetch(`${aiServiceUrl}/api/v1/chart/compare/${id}?type=${type}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': req.headers.get('x-session-token') || '',
        }
      });
    } else {
      // POST request to create a comparison
      const body = await req.json();
      const {
        originalChartId,
        rectifiedChartId,
        originalTime,
        rectifiedTime,
        comparisonType = 'full'
      } = body;

      // Validate required fields
      if (!originalChartId || !rectifiedChartId) {
        return new Response(JSON.stringify({
          success: false,
          message: 'Both original and rectified chart IDs are required'
        }), {
          status: 400,
          headers: {
            'Content-Type': 'application/json'
          }
        });
      }

      // Call the backend service to create a comparison with the correct endpoint
      response = await fetch(`${aiServiceUrl}/api/v1/chart/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Token': req.headers.get('x-session-token') || '',
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
      comparison_id: data.comparison_id,
      comparison_data: data.comparison_data,
      differences: data.differences,
      original_chart: data.original_chart,
      rectified_chart: data.rectified_chart,
      message: data.message || 'Chart comparison successful'
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });

  } catch (error) {
    console.error('Error comparing charts:', error);
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
