/**
 * NOTE FOR CONSOLIDATION: APIs should be consolidated under the /api/v1/ namespace.
 * This file can be merged with /api/v1/chart endpoints for better organization.
 *
 * API endpoints organization plan:
 * 1. Move all endpoints to /api/v1/* for proper versioning
 * 2. Eliminate duplicates between /api/* and /api/v1/* paths
 * 3. Consolidate chart-related endpoints under /api/v1/chart/
 *
 * @deprecated Use /api/v1/chart endpoints instead.
 */

import type { NextApiRequest, NextApiResponse } from 'next';
import { BirthDetails, ChartData } from '@/types';

// Mock chart data to use as fallback
const getMockChartData = (birthDetails: BirthDetails): ChartData => {
  // Generate mock Indian Vedic chart data
  return {
    ascendant: {
      sign: 'Aries',
      degree: 15,
      description: 'Rising sign representing your outward personality'
    },
    planets: [
      {
        planet: 'Sun',
        name: 'Sun',
        longitude: 45, // Taurus
        latitude: 0,
        speed: 1,
        house: 2,
        sign: 'Taurus',
        degree: '15',
        retrograde: false,
        description: 'Represents your core essence and identity'
      },
      {
        planet: 'Moon',
        name: 'Moon',
        longitude: 95, // Cancer
        latitude: 0,
        speed: 13,
        house: 4,
        sign: 'Cancer',
        degree: '5',
        retrograde: false,
        description: 'Represents your emotions and subconscious'
      },
      {
        planet: 'Mercury',
        name: 'Mercury',
        longitude: 48, // Taurus
        latitude: 0,
        speed: 1.5,
        house: 2,
        sign: 'Taurus',
        degree: '18',
        retrograde: false,
        description: 'Represents your communication and thinking style'
      },
      {
        planet: 'Venus',
        name: 'Venus',
        longitude: 76, // Gemini
        latitude: 0,
        speed: 1.2,
        house: 3,
        sign: 'Gemini',
        degree: '16',
        retrograde: false,
        description: 'Represents your values and approach to relationships'
      },
      {
        planet: 'Mars',
        name: 'Mars',
        longitude: 125, // Leo
        latitude: 0,
        speed: 0.8,
        house: 5,
        sign: 'Leo',
        degree: '5',
        retrograde: false,
        description: 'Represents your drive and how you take action'
      },
      {
        planet: 'Jupiter',
        name: 'Jupiter',
        longitude: 160, // Virgo
        latitude: 0,
        speed: 0.4,
        house: 6,
        sign: 'Virgo',
        degree: '10',
        retrograde: false,
        description: 'Represents expansion and growth in your life'
      },
      {
        planet: 'Saturn',
        name: 'Saturn',
        longitude: 188, // Libra
        latitude: 0,
        speed: 0.3,
        house: 7,
        sign: 'Libra',
        degree: '8',
        retrograde: false,
        description: 'Represents discipline and life lessons'
      },
      {
        planet: 'Rahu',
        name: 'Rahu',
        longitude: 250, // Sagittarius
        latitude: 0,
        speed: -0.05,
        house: 9,
        sign: 'Sagittarius',
        degree: '10',
        retrograde: true,
        description: 'Represents desires and material attachments'
      },
      {
        planet: 'Ketu',
        name: 'Ketu',
        longitude: 0, // Aries
        latitude: 0,
        speed: -0.05,
        house: 1,
        sign: 'Aries',
        degree: '30',
        retrograde: true,
        description: 'South Node - represents past karma and spirituality'
      }
    ],
    houses: Array.from({ length: 12 }, (_, i) => ({
      number: i + 1,
      startDegree: i * 30,
      endDegree: (i + 1) * 30,
      sign: ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'][i],
      degree: 0,
      planets: []
    })),
    divisionalCharts: {},
    aspects: [
      {
        planet1: 'sun',
        planet2: 'moon',
        aspectType: 'trine',
        orb: 2.5,
        influence: 'positive',
        description: 'Harmonious flow between conscious and unconscious mind'
      },
      {
        planet1: 'jupiter',
        planet2: 'saturn',
        aspectType: 'square',
        orb: 3.2,
        influence: 'neutral',
        description: 'Tension between expansion and limitation'
      }
    ]
  };
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Extract birth details from request
    const birthDetails = req.body.birthDetails as BirthDetails;

    if (!birthDetails) {
      return res.status(400).json({ error: 'Birth details are required' });
    }

    // Try to reach the external API
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    try {
      const response = await fetch(`${apiUrl}/charts`, {
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
      return res.status(200).json(data);
    } catch (apiError) {
      console.warn('Warning: API request failed, using mock data instead:', apiError);

      // Generate mock data as fallback
      const mockData = getMockChartData(birthDetails);

      // Return mock data with a note for the frontend
      return res.status(200).json({
        ...mockData,
        _warning: 'Using mock data due to API unavailability'
      });
    }
  } catch (error) {
    console.error('Error processing chart request:', error);
    const errorMessage = error instanceof Error
      ? error.message
      : 'Failed to generate chart data';
    return res.status(500).json({ error: errorMessage });
  }
}
