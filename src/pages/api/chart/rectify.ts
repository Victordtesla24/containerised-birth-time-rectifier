import type { NextRequest } from 'next/server';
import type { NextResponse } from 'next/server';
import { QuestionnaireResponse, BirthDetails } from '@/types';

interface RectificationRequest {
  questionnaire: QuestionnaireResponse;
  birthDetails: BirthDetails;
}

interface RectificationResponse {
  success: boolean;
  originalTime: string;
  rectifiedTime: string;
  confidence: number;
  adjustmentMinutes: number;
  chartId: string;
  explanation?: string;
  error?: string;
}

export default async function handler(
  req: Request
) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({
      success: false,
      originalTime: '',
      rectifiedTime: '',
      confidence: 0,
      adjustmentMinutes: 0,
      chartId: '',
      error: 'Method not allowed'
    }), {
      status: 405,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  try {
    // Extract request data
    const body = await req.json();
    const { questionnaire, birthDetails } = body as RectificationRequest;

    // Validate required fields
    if (!questionnaire || !birthDetails) {
      return new Response(JSON.stringify({
        success: false,
        originalTime: '',
        rectifiedTime: '',
        confidence: 0,
        adjustmentMinutes: 0,
        chartId: '',
        error: 'Missing required data'
      }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }

    // Check if AI service is available
    const aiServiceUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    // Attempt to call the AI service with the correct endpoint
    const response = await fetch(`${aiServiceUrl}/api/v1/chart/rectify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        chart_id: questionnaire.chartId || 'test-chart-id',
        birth_details: birthDetails,
        answers: questionnaire.answers || []
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return new Response(JSON.stringify({
        success: false,
        originalTime: '',
        rectifiedTime: '',
        confidence: 0,
        adjustmentMinutes: 0,
        chartId: '',
        error: errorData.detail || `API responded with status ${response.status}`
      }), {
        status: response.status,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }

    const data = await response.json();

    // Parse the response and format it for the frontend
    const originalTime = data.original_time || data.originalTime || birthDetails.approximateTime;
    const rectifiedTime = data.rectified_time || data.rectifiedTime;
    const confidenceScore = data.confidence_score || data.confidence || 0;
    const chartId = data.rectified_chart_id || data.chartId || 'rectified-chart-id';

    // Calculate adjustment in minutes
    const originalMinutes = parseTimeToMinutes(originalTime);
    const rectifiedMinutes = parseTimeToMinutes(rectifiedTime);
    let adjustmentMinutes = Math.abs(rectifiedMinutes - originalMinutes);

    // Ensure we get the shortest time difference (considering day boundaries)
    if (adjustmentMinutes > 720) { // More than 12 hours
      adjustmentMinutes = 1440 - adjustmentMinutes; // 24 hours - difference
    }

    return new Response(JSON.stringify({
      success: true,
      originalTime,
      rectifiedTime,
      confidence: confidenceScore,
      adjustmentMinutes,
      chartId,
      explanation: data.explanation || 'Birth time rectified based on provided questionnaire data.'
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    console.error('Error rectifying chart:', error);
    return new Response(JSON.stringify({
      success: false,
      originalTime: '',
      rectifiedTime: '',
      confidence: 0,
      adjustmentMinutes: 0,
      chartId: '',
      error: 'Internal server error'
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
}

// Helper function to convert time string to minutes
function parseTimeToMinutes(timeStr: string): number {
  // Handle different time formats
  if (!timeStr) return 0;

  const parts = timeStr.split(':');
  if (parts.length < 2) return 0;

  const hours = parseInt(parts[0], 10);
  const minutes = parseInt(parts[1], 10);

  return hours * 60 + minutes;
}
