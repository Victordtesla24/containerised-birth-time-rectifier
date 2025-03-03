import type { NextApiRequest, NextApiResponse } from 'next';
import { BirthDetails, RectificationResult } from '@/types';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { birthDetails, questionnaireResponses } = req.body;

    if (!birthDetails) {
      return res.status(400).json({ error: 'Birth details are required' });
    }

    // In a production environment, this would call the AI service
    // For now, we'll simulate a response with a rectified birth time

    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500));

    // Generate a rectification based on the provided details
    const originalTime = birthDetails.time;

    // Generate a small time adjustment (±15 minutes)
    const adjustment = Math.floor(Math.random() * 31) - 15; // -15 to +15 minutes

    // Calculate new time
    const [hours, minutes] = originalTime.split(':').map(Number);
    let newTotalMinutes = hours * 60 + minutes + adjustment;

    // Handle day wrap around
    newTotalMinutes = ((newTotalMinutes % 1440) + 1440) % 1440;
    const newHours = Math.floor(newTotalMinutes / 60);
    const newMinutes = newTotalMinutes % 60;
    const suggestedTime = `${String(newHours).padStart(2, '0')}:${String(newMinutes).padStart(2, '0')}`;

    // Generate confidence score between 75-95%
    const confidence = 0.75 + (Math.random() * 0.2);

    // Create detailed rectification result
    const result: RectificationResult = {
      birthDetails,
      originalTime,
      suggestedTime,
      confidence,
      reliability: confidence > 0.85 ? 'High' : 'Medium',
      explanation: `Based on the analysis of your birth chart and life events, the suggested birth time of ${suggestedTime} aligns better with the planetary positions that would influence the events you've experienced. This rectification takes into account the positions of your ascendant, moon, and key planetary aspects that correlate with significant life events you've reported.`,
      taskPredictions: {
        time: 0.85,
        ascendant: 0.78,
        houses: 0.82
      },
      planetaryPositions: [
        {
          planet: 'Moon',
          sign: 'Cancer',
          degree: '15',
          house: 4,
          retrograde: false,
          explanation: 'Emotional patterns and instinctual responses'
        },
        {
          planet: 'Sun',
          sign: 'Aries',
          degree: '10',
          house: 1,
          retrograde: false,
          explanation: 'Core identity and life purpose'
        },
        {
          planet: adjustment > 0 ? 'Jupiter' : 'Saturn',
          sign: adjustment > 0 ? 'Sagittarius' : 'Capricorn',
          degree: '5',
          house: adjustment > 0 ? 9 : 10,
          retrograde: false,
          explanation: adjustment > 0
            ? 'Expansion and growth opportunities'
            : 'Discipline and life lessons'
        }
      ],
      significantEvents: {
        past: [
          {
            date: '2018-05',
            description: 'Major career transition aligns with Saturn transit',
            confidence: 0.82,
            impactAreas: ['Career', 'Personal Growth']
          },
          {
            date: '2020-11',
            description: 'Relationship development corresponds with Venus-Jupiter aspect',
            confidence: 0.78,
            impactAreas: ['Relationships', 'Emotional Well-being']
          }
        ],
        future: [
          {
            date: '2024-09',
            description: 'Potential for significant personal growth with Jupiter transit',
            confidence: 0.75,
            impactAreas: ['Personal Development', 'Spirituality']
          },
          {
            date: '2025-03',
            description: 'Career advancement opportunity with Saturn-Sun aspect',
            confidence: 0.68,
            impactAreas: ['Career', 'Finances']
          }
        ]
      }
    };

    res.status(200).json(result);
  } catch (error) {
    console.error('Error generating rectification:', error);
    const errorMessage = error instanceof Error
      ? error.message
      : 'Failed to generate birth time rectification';
    return res.status(500).json({ error: errorMessage });
  }
}
