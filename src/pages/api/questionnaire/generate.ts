import type { NextApiRequest, NextApiResponse } from 'next';
import { BirthDetails, DynamicQuestion, QuestionnaireGenerationRequest, QuestionnaireGenerationResponse, ApiError } from '@/types';

// Fallback question generators if AI service is unavailable
const generateCareerQuestions = (birthDetails: BirthDetails): DynamicQuestion[] => {
  // In a real implementation, this would analyze planetary positions
  // For now, we'll return some sample questions
  return [
    {
      id: 'career-major-change',
      text: 'Did you experience a major career change between ages 28-32?',
      type: 'yes_no',
      weight: 0.15
    },
    {
      id: 'career-satisfaction',
      text: 'Which period of your career has been most satisfying?',
      type: 'multiple_choice',
      options: ['Early career (20s)', 'Mid-career (30s-40s)', 'Later career (50+)', 'None'],
      weight: 0.12
    }
  ];
};

const generateRelationshipQuestions = (birthDetails: BirthDetails): DynamicQuestion[] => {
  return [
    {
      id: 'relationship-marriage',
      text: 'Have you been married or in a significant long-term relationship?',
      type: 'yes_no',
      weight: 0.15
    },
    {
      id: 'relationship-challenge',
      text: 'Did you face relationship challenges around the age of 35?',
      type: 'yes_no',
      weight: 0.12
    }
  ];
};

const generateHealthQuestions = (birthDetails: BirthDetails): DynamicQuestion[] => {
  return [
    {
      id: 'health-major-illness',
      text: 'Have you experienced any major health issues in your life?',
      type: 'yes_no',
      weight: 0.13
    },
    {
      id: 'health-chronic',
      text: 'Do you have any chronic health conditions that started between ages 20-30?',
      type: 'yes_no',
      weight: 0.12
    }
  ];
};

const generateSpiritualQuestions = (birthDetails: BirthDetails): DynamicQuestion[] => {
  return [
    {
      id: 'spiritual-practice',
      text: 'Do you engage in regular spiritual or religious practices?',
      type: 'yes_no',
      weight: 0.10
    },
    {
      id: 'spiritual-journey',
      text: 'When did you begin your spiritual journey or develop interest in astrology?',
      type: 'multiple_choice',
      options: ['Childhood', 'Teens/Early 20s', 'Late 20s/30s', 'Later in life', 'Not applicable'],
      weight: 0.08
    }
  ];
};

// Mock function that would be replaced by AI service call
const analyzeAnswersAndRefineQuestions = (
  previousAnswers: Record<string, string>,
  currentConfidence: number
): { additionalQuestions: DynamicQuestion[], confidenceAdjustment: number } => {
  // In a real implementation, this would call the AI service to analyze answers
  // and generate appropriate follow-up questions

  // For demo purposes, we'll just check if we have answers and provide follow-ups
  const hasAnswers = Object.keys(previousAnswers).length > 0;

  if (!hasAnswers) {
    return {
      additionalQuestions: [],
      confidenceAdjustment: 0
    };
  }

  // Generate follow-up questions based on previous answers
  const followUpQuestions: DynamicQuestion[] = [];

  // If they answered yes to marriage question, ask about children
  if (previousAnswers['relationship-marriage'] === 'Yes') {
    followUpQuestions.push({
      id: 'relationship-children',
      text: 'Do you have children?',
      type: 'yes_no',
      weight: 0.12
    });
  }

  // If they answered yes to major health issues, ask about recovery
  if (previousAnswers['health-major-illness'] === 'Yes') {
    followUpQuestions.push({
      id: 'health-recovery',
      text: 'How long did your recovery from health issues typically take?',
      type: 'multiple_choice',
      options: ['Days', 'Weeks', 'Months', 'Years', 'Ongoing'],
      weight: 0.10
    });
  }

  // Calculate confidence adjustment
  const confidenceAdjustment = hasAnswers ? 5 : 0; // In real implementation, this would be more sophisticated

  return {
    additionalQuestions: followUpQuestions,
    confidenceAdjustment
  };
};

// Shuffle array - Fisher-Yates algorithm
const shuffleArray = <T>(array: T[]): T[] => {
  const newArray = [...array];
  for (let i = newArray.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
  }
  return newArray;
};

// Connect to the AI backend service for question generation
async function getQuestionsFromAIService(request: QuestionnaireGenerationRequest): Promise<QuestionnaireGenerationResponse | null> {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_AI_SERVICE_URL || 'http://localhost:8000';

    const response = await fetch(`${apiUrl}/api/generate-questions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(5000) // 5-second timeout
    });

    if (!response.ok) {
      throw new Error(`AI service returned ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Failed to get questions from AI service:', error);
    return null;
  }
}

// Generate fallback questions without AI service
function generateFallbackQuestions(request: QuestionnaireGenerationRequest): QuestionnaireGenerationResponse {
  const { birthDetails, currentConfidence, previousAnswers } = request;

  // Generate base questions from different categories
  const careerQuestions = generateCareerQuestions(birthDetails);
  const relationshipQuestions = generateRelationshipQuestions(birthDetails);
  const healthQuestions = generateHealthQuestions(birthDetails);
  const spiritualQuestions = generateSpiritualQuestions(birthDetails);

  // Combine all questions
  let allQuestions = [
    ...careerQuestions,
    ...relationshipQuestions,
    ...healthQuestions,
    ...spiritualQuestions
  ];

  // Filter out questions that have already been answered
  allQuestions = allQuestions.filter(
    question => !previousAnswers || !Object.keys(previousAnswers).includes(question.id)
  );

  // Analyze previous answers to generate more targeted follow-up questions
  const { additionalQuestions, confidenceAdjustment } = analyzeAnswersAndRefineQuestions(
    previousAnswers || {},
    currentConfidence || 0
  );

  // Add the additional questions
  allQuestions = [...allQuestions, ...additionalQuestions];

  // Shuffle the questions and limit to 5 at a time
  const shuffledQuestions = shuffleArray(allQuestions).slice(0, 5);

  // Calculate new confidence score
  const newConfidenceScore = Math.min(100, (currentConfidence || 0) + confidenceAdjustment);

  // Determine if we've reached completion threshold
  const hasReachedThreshold = newConfidenceScore >= 90;

  // Return the questions with updated confidence
  return {
    questions: shuffledQuestions,
    confidence: newConfidenceScore,
    sessionId: `session-${Date.now()}`,
    message: 'Questions generated successfully'
  };
}

// Function to handle the API request
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<QuestionnaireGenerationResponse | ApiError>
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 405, message: 'Method not allowed' });
  }

  try {
    const { birthDetails, previousAnswers, currentConfidence, focusAreas, maxQuestions } =
      req.body as QuestionnaireGenerationRequest;

    if (!birthDetails) {
      throw new Error('Birth details are required');
    }

    // Prepare the request for the AI service
    const aiServiceRequest: QuestionnaireGenerationRequest = {
      birthDetails,
      currentConfidence,
      previousAnswers,
      focusAreas,
      maxQuestions
    };

    // Try to get questions from AI service first
    const aiResponse = await getQuestionsFromAIService(aiServiceRequest);

    if (aiResponse) {
      // Successfully got questions from AI service
      res.status(200).json(aiResponse);
    } else {
      // AI service unavailable, use fallback
      console.warn('Using fallback question generation');
      const fallbackResponse = generateFallbackQuestions(aiServiceRequest);

      // Add warning for frontend
      res.status(200).json({
        ...fallbackResponse,
        message: 'Using fallback questions due to AI service unavailability'
      });
    }
  } catch (error) {
    console.error('Error generating questionnaire:', error);
    res.status(500).json({
      status: 500,
      message: 'Failed to generate questionnaire',
      detail: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}
