import type { NextApiRequest, NextApiResponse } from 'next';
import { fetchWithTimeout } from '@/utils/fetch';

interface QuestionnaireRequest {
  birthDetails?: {
    name?: string;
    birthDate?: string;
    approximateTime?: string;
    birthTime?: string;
    birthLocation?: string;
    birthPlace?: string;
    coordinates?: { latitude: number; longitude: number };
    timezone?: string;
  };
  answers?: Array<{
    questionId: string;
    question?: string;
    answer: any;
  }>;
  confidenceScore?: number;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Only allow POST method
  if (req.method !== 'POST') {
    return res.status(405).json({
      success: false,
      error: 'Method not allowed'
    });
  }

  try {
    const data = req.body as QuestionnaireRequest;

    // Validate required data
    if (!data.birthDetails) {
      return res.status(400).json({
        success: false,
        error: 'Missing required questionnaire data: birthDetails'
      });
    }

    // Get backend API URL from environment variable
    const apiUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    // Transform data to backend format
    const backendData = {
      birth_details: {
        name: data.birthDetails.name || 'Anonymous',
        date: data.birthDetails.birthDate,
        time: data.birthDetails.birthTime || data.birthDetails.approximateTime,
        place: data.birthDetails.birthPlace || data.birthDetails.birthLocation,
        coordinates: data.birthDetails.coordinates,
        timezone: data.birthDetails.timezone
      },
      previous_answers: data.answers?.reduce((acc, answer) => {
        acc[answer.questionId] = answer.answer;
        return acc;
      }, {} as Record<string, any>) || {},
      current_confidence: data.confidenceScore || 0
    };

    // Make request to backend API
    const response = await fetchWithTimeout(`${apiUrl}/api/v1/questionnaire/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendData),
      timeout: 10000 // 10 second timeout
    });

    // Handle response
    const responseData = await response.json();

    // Transform response format if needed
    const formattedResponse = {
      success: true,
      questions: responseData.questions || [],
      confidenceScore: responseData.confidence || 0,
      isComplete: responseData.is_complete || false,
      sessionId: responseData.session_id
    };

    // Return success response
    return res.status(200).json(formattedResponse);
  } catch (error: any) {
    console.error('Questionnaire processing error:', error);

    // Handle error
    return res.status(500).json({
      success: false,
      error: error.message || 'Failed to process questionnaire data',
      details: error.toString()
    });
  }
}
