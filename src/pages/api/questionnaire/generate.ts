import type { NextRequest } from 'next/server';
import type { NextResponse } from 'next/server';

type GenerateResponse = {
  success?: boolean;
  message?: string;
  data?: any;
  error?: string;
  questions?: any[];
  confidenceScore?: number;
  isComplete?: boolean;
  hasReachedThreshold?: boolean;
  sessionId?: string;
  initialConfidence?: number;
  _warning?: string;
};

// Removed fallback mechanism to ensure tests properly fail when services are unavailable

export default async function handler(
  req: Request,
  res: Response
) {
  // Only allow POST requests
  if (req.method !== 'POST') {
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
    // Extract request data
    const body = await req.json();
    const { birthDetails, currentConfidence = 0, previousAnswers = {} } = body;

    // Validate required fields
    if (!birthDetails) {
      return new Response(JSON.stringify({
        success: false,
        message: 'Birth details are required'
      }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }

    // Get AI service URL from environment or use default
    const aiServiceUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    // Call the AI service with the correct endpoint
    const response = await fetch(`${aiServiceUrl}/api/v1/questionnaire/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        birthDetails,
        currentConfidence,
        previousAnswers
      }),
    });

    // Handle API response
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to parse API error response' }));
      console.error('AI service error:', errorData);
      return new Response(JSON.stringify({
        success: false,
        error: errorData.detail || `AI service responded with status ${response.status}`
      }), {
        status: response.status,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }

    // Successfully got data from AI service
    const data = await response.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    console.error('Error generating questionnaire:', error);
    return new Response(JSON.stringify({
      success: false,
      error: error instanceof Error
        ? `Service unavailable: ${error.message}`
        : 'Service unavailable: Failed to connect to AI service'
    }), {
      status: 503,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
}
