import type { NextApiRequest, NextApiResponse } from 'next';

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
  req: NextApiRequest,
  res: NextApiResponse<GenerateResponse>
) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    return res.status(405).json({
      success: false,
      error: 'Method not allowed'
    });
  }

  try {
    // Extract request data
    const { birthDetails, currentConfidence = 0, previousAnswers = {} } = req.body;

    // Validate required fields
    if (!birthDetails) {
      return res.status(400).json({
        success: false,
        message: 'Birth details are required'
      });
    }

    // Get AI service URL from environment or use default
    const aiServiceUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    // Call the AI service
    const response = await fetch(`${aiServiceUrl}/api/generate-questions`, {
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
      return res.status(response.status).json({
        success: false,
        error: errorData.detail || `AI service responded with status ${response.status}`
      });
    }

    // Successfully got data from AI service
    const data = await response.json();
    return res.status(200).json(data);
  } catch (error) {
    console.error('Error generating questionnaire:', error);
    return res.status(503).json({
      success: false,
      error: error instanceof Error
        ? `Service unavailable: ${error.message}`
        : 'Service unavailable: Failed to connect to AI service'
    });
  }
}
