import type { NextApiRequest, NextApiResponse } from 'next';
import { fetchWithTimeout } from '@/utils/fetch';

interface QuestionnaireRequest {
  birthDetails: {
    name?: string;
    date: string;
    time: string;
    place: string;
    coordinates?: { latitude: number; longitude: number };
    timezone: string;
  };
  currentConfidence: number;
  previousAnswers: Record<string, any>;
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
    const { birthDetails, currentConfidence, previousAnswers } = req.body as QuestionnaireRequest;

    // Validate birth details
    if (!birthDetails) {
      return res.status(400).json({
        success: false,
        message: 'Birth details are required'
      });
    }

    // Required birth detail fields
    if (!birthDetails.date || !birthDetails.time || !birthDetails.place) {
      return res.status(400).json({
        success: false,
        message: 'Date, time, and place are required in birth details'
      });
    }

    // Get backend API URL from environment variable
    const apiUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    // Make request to backend API
    const response = await fetchWithTimeout(`${apiUrl}/api/v1/questionnaire/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        birth_details: {
          name: birthDetails.name || 'Anonymous',
          date: birthDetails.date,
          time: birthDetails.time,
          place: birthDetails.place,
          coordinates: birthDetails.coordinates,
          timezone: birthDetails.timezone
        },
        current_confidence: currentConfidence || 0,
        previous_answers: previousAnswers || {}
      }),
      timeout: 10000 // 10 second timeout
    });

    // Handle response
    const data = await response.json();

    // Return success response
    return res.status(response.status).json(data);
  } catch (error: any) {
    console.error('Questionnaire generation error:', error);

    // Handle error
    return res.status(500).json({
      success: false,
      message: error.message || 'Failed to generate questionnaire',
      error: error.toString()
    });
  }
}
