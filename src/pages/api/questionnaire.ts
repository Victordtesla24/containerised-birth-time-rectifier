import type { NextApiRequest, NextApiResponse } from 'next';
import { BirthDetails, QuestionnaireResponse } from '@/types';

// Confidence threshold for birth time rectification
const CONFIDENCE_THRESHOLD = 90;

// Mock response generator for fallback
const getMockQuestionnaireResponse = (responses: any): any => {
  // In a real implementation, this would process questionnaire responses
  // and return rectification suggestions
  
  // Extract confidence score from responses or use default
  const confidenceScore = responses?.confidenceScore || 85;
  const meetsThreshold = confidenceScore >= CONFIDENCE_THRESHOLD;
  
  return {
    success: true,
    message: "Questionnaire processed successfully",
    confidenceScore: confidenceScore,
    meetsThreshold: meetsThreshold,
    requestMoreQuestions: !meetsThreshold,
    rectificationSuggestions: meetsThreshold ? [
      {
        suggestedTime: adjustBirthTime(responses?.birthDetails?.time || "12:00", 15, "earlier"),
        confidence: 85,
        explanation: "Based on your life events and planetary positions, a birth time 15 minutes earlier aligns better with your reported experiences."
      },
      {
        suggestedTime: adjustBirthTime(responses?.birthDetails?.time || "12:00", 7, "later"),
        confidence: 75,
        explanation: "An alternative possibility is a birth time 7 minutes later, which correlates with your relationship patterns."
      }
    ] : []
  };
};

// Helper function to adjust birth time by minutes
function adjustBirthTime(timeString: string, minuteAdjustment: number, direction: 'earlier' | 'later'): string {
  try {
    const [hours, minutes] = timeString.split(':').map(Number);
    let totalMinutes = hours * 60 + minutes;
    
    if (direction === 'earlier') {
      totalMinutes -= minuteAdjustment;
    } else {
      totalMinutes += minuteAdjustment;
    }
    
    // Handle day boundary overflow/underflow
    totalMinutes = ((totalMinutes % 1440) + 1440) % 1440;
    
    const newHours = Math.floor(totalMinutes / 60);
    const newMinutes = totalMinutes % 60;
    
    return `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}`;
  } catch (error) {
    console.error('Error adjusting birth time:', error);
    return timeString; // Return original if there's an error
  }
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Validate that we have the required data
    if (!req.body || (!req.body.answers && !req.body.lifeEvents)) {
      return res.status(400).json({ 
        error: 'Missing required questionnaire data. Please provide answers or life events.' 
      });
    }

    // Try to reach the external AI service
    const apiUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';
    
    try {
      const response = await fetch(`${apiUrl}/api/process-questionnaire`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(req.body),
        // Add timeout to prevent long waits
        signal: AbortSignal.timeout(5000)
      });
  
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `HTTP error! status: ${response.status}`
        );
      }
  
      const data = await response.json();
      
      // Check if the confidence score meets our threshold
      const confidenceScore = data.confidenceScore || 0;
      const meetsThreshold = confidenceScore >= CONFIDENCE_THRESHOLD;
      
      // Return the data with threshold check
      return res.status(200).json({
        ...data,
        meetsThreshold,
        requestMoreQuestions: !meetsThreshold
      });
    } catch (apiError) {
      console.warn('Warning: AI service unavailable, using mock data instead:', apiError);
      
      // Generate mock response data as fallback
      const mockResponse = getMockQuestionnaireResponse(req.body);
      
      // Return mock data with a note for the frontend
      return res.status(200).json({
        ...mockResponse,
        _warning: 'Using mock data due to AI service unavailability'
      });
    }
  } catch (error) {
    console.error('Error processing questionnaire data:', error);
    const errorMessage = error instanceof Error 
      ? error.message 
      : 'Failed to process questionnaire data';
    return res.status(500).json({ error: errorMessage });
  }
} 