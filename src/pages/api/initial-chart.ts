import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    // This would normally call the backend chart generation service
    // For now, we'll return mock data

    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Mock chart data
    const chartData = {
      ascendant: {
        sign: 'Libra',
        degree: 15.5,
        description: 'Libra ascendant indicates balance and harmony in one\'s approach to life'
      },
      planets: [
        {
          name: 'Sun',
          sign: 'Leo',
          degree: 25.0,
          house: 10,
          retrograde: false,
          description: 'Strong Sun in Leo in the 10th house indicates leadership qualities'
        },
        {
          name: 'Moon',
          sign: 'Cancer',
          degree: 18.3,
          house: 9,
          retrograde: false,
          description: 'Moon in Cancer indicates emotional sensitivity and nurturing nature'
        },
        {
          name: 'Mercury',
          sign: 'Virgo',
          degree: 10.7,
          house: 11,
          retrograde: false,
          description: 'Mercury in Virgo enhances analytical abilities and attention to detail'
        },
        {
          name: 'Venus',
          sign: 'Libra',
          degree: 5.2,
          house: 12,
          retrograde: false,
          description: 'Venus in Libra brings harmony and grace to relationships'
        },
        {
          name: 'Mars',
          sign: 'Aries',
          degree: 28.9,
          house: 6,
          retrograde: false,
          description: 'Mars in Aries gives strong initiative and pioneering energy'
        }
      ],
      houses: [
        {
          number: 1,
          sign: 'Libra',
          degree: 15.5,
          planets: [],
          description: 'First house in Libra indicates grace and harmony in self-expression'
        },
        {
          number: 2,
          sign: 'Scorpio',
          degree: 15.5,
          planets: [],
          description: 'Second house in Scorpio suggests intensity in handling resources'
        },
        {
          number: 3,
          sign: 'Sagittarius',
          degree: 15.5,
          planets: [],
          description: 'Third house in Sagittarius indicates expansive communication style'
        }
      ],
      aspects: [
        {
          planet1: 'Sun',
          planet2: 'Moon',
          aspectType: 'Trine',
          orb: 1.2,
          influence: 'positive',
          description: 'Harmonious aspect creating emotional balance and creative expression'
        }
      ]
    };

    return res.status(200).json(chartData);
  } catch (error) {
    console.error('Error generating initial chart:', error);
    const errorMessage = error instanceof Error 
      ? error.message 
      : 'Failed to generate chart data';
    return res.status(500).json({ error: errorMessage });
  }
} 