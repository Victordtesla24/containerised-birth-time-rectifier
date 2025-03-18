import type { NextRequest } from 'next/server';
import type { NextResponse } from 'next/server';
import { BirthDetails, QuestionnaireResponse } from '@/types';

type ResponseData = {
  success?: boolean;
  questions?: any[];
  confidenceScore?: number;
  error?: string;
  meetsThreshold?: boolean;
  requestMoreQuestions?: boolean;
  sessionId?: string;
  rectificationSuggestions?: any[];
  _warning?: string;
}

// Confidence threshold for completing the questionnaire
const CONFIDENCE_THRESHOLD = 90;

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
    const { birthDetails, answers, confidenceScore } = body;

    // Validate required fields
    if (!birthDetails) {
      return new Response(JSON.stringify({
        success: false,
        error: 'Missing required questionnaire data'
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
    const response = await fetch(`${aiServiceUrl}/api/v1/questionnaire`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        birth_details: birthDetails,
        answers: answers || [],
        confidence_score: confidenceScore || 0
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Failed to parse error response' }));
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

    const data = await response.json();

    // Determine if we need more questions or if we've reached the threshold
    const currentConfidenceScore = data.confidence_score || data.confidenceScore || confidenceScore || 0;
    const meetsThreshold = currentConfidenceScore >= CONFIDENCE_THRESHOLD;

    // If the AI response includes rectification suggestions, include them in our response
    const rectificationSuggestions = data.rectification_suggestions || data.rectificationSuggestions || [];

    return new Response(JSON.stringify({
      success: true,
      questions: data.questions || [],
      confidenceScore: currentConfidenceScore,
      sessionId: data.session_id || data.sessionId,
      meetsThreshold,
      requestMoreQuestions: !meetsThreshold,
      rectificationSuggestions
    }), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    console.error('Error processing questionnaire:', error);

    // Return a proper error response with the actual error message
    return new Response(JSON.stringify({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error processing questionnaire'
    }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
}
