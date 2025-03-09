import { NextApiRequest, NextApiResponse } from 'next';
import { v4 as uuidv4 } from 'uuid';

// Define types for our response
interface ChartDifference {
  type: string;
  entity: string;
  description: string;
  details: string;
  significance?: number;
}

interface ComparisonResponse {
  comparison_id: string;
  chart1_id: string;
  chart2_id: string;
  differences: ChartDifference[];
  summary?: string;
}

// Chart comparison endpoint to handle both GET and POST requests
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    switch (req.method) {
      case 'GET':
        return handleGetComparison(req, res);
      case 'POST':
        return handlePostComparison(req, res);
      default:
        return res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (error: any) {
    console.error('Chart comparison error:', error);
    return res.status(500).json({ error: 'Internal server error', details: error?.message || 'Unknown error' });
  }
}

/**
 * Handle GET request for chart comparison
 */
async function handleGetComparison(req: NextApiRequest, res: NextApiResponse) {
  const { chart1_id, chart2_id, comparison_type = 'differences', include_significance = 'false' } = req.query;

  // Validate required parameters
  if (!chart1_id || !chart2_id) {
    return res.status(400).json({ error: 'Missing required parameters: chart1_id and chart2_id are required' });
  }

  try {
    // In a real implementation, we would fetch the charts from a database or API
    // For now, generate mock comparison data
    const comparisonData = generateComparisonData(
      chart1_id as string,
      chart2_id as string,
      comparison_type as string,
      include_significance === 'true'
    );

    return res.status(200).json(comparisonData);
  } catch (error: any) {
    console.error('Error generating chart comparison:', error);
    return res.status(500).json({ error: 'Failed to generate chart comparison', details: error?.message || 'Unknown error' });
  }
}

/**
 * Handle POST request for chart comparison
 */
async function handlePostComparison(req: NextApiRequest, res: NextApiResponse) {
  const { chart1_id, chart2_id, comparison_type = 'differences', include_significance = false } = req.body;

  // Validate required parameters
  if (!chart1_id || !chart2_id) {
    return res.status(400).json({ error: 'Missing required parameters: chart1_id and chart2_id are required' });
  }

  try {
    // In a real implementation, we would fetch the charts from a database or API
    // For now, generate mock comparison data
    const comparisonData = generateComparisonData(
      chart1_id,
      chart2_id,
      comparison_type,
      include_significance
    );

    return res.status(200).json(comparisonData);
  } catch (error: any) {
    console.error('Error generating chart comparison:', error);
    return res.status(500).json({ error: 'Failed to generate chart comparison', details: error?.message || 'Unknown error' });
  }
}

/**
 * Generate mock comparison data
 */
function generateComparisonData(
  chart1Id: string,
  chart2Id: string,
  comparisonType: string,
  includeSignificance: boolean
): ComparisonResponse {
  // Create a unique ID for this comparison
  const comparisonId = `comp_${Math.random().toString(36).substring(2, 10)}`;

  // Default response structure
  const response: ComparisonResponse = {
    comparison_id: comparisonId,
    chart1_id: chart1Id,
    chart2_id: chart2Id,
    differences: generateDifferences(includeSignificance),
  };

  // Add summary for full and summary comparison types
  if (comparisonType === 'full' || comparisonType === 'summary') {
    response.summary = 'This comparison reveals significant differences in planetary positions, particularly for the Moon and Ascendant, which have shifted houses due to the time difference. These changes impact personality expression and emotional tendencies.';
  }

  return response;
}

/**
 * Generate mock differences between charts
 */
function generateDifferences(includeSignificance: boolean) {
  const baseDifferences = [
    {
      type: 'PLANET_SIGN_CHANGE',
      entity: 'Moon',
      description: 'Moon has changed from Cancer to Leo',
      details: 'The Moon has moved from 29° Cancer to 3° Leo',
    },
    {
      type: 'HOUSE_CUSP',
      entity: 'Ascendant',
      description: 'Ascendant has shifted by 15 degrees',
      details: 'The Ascendant has moved from 15° Virgo to 0° Libra',
    },
    {
      type: 'PLANET_HOUSE',
      entity: 'Venus',
      description: 'Venus has moved from 9th house to 10th house',
      details: 'Venus at 18° Capricorn has changed houses due to house cusp shift',
    }
  ];

  // Add significance values if requested
  if (includeSignificance) {
    return baseDifferences.map((diff, index) => ({
      ...diff,
      significance: 0.85 - (index * 0.15) // Decreasing significance values
    }));
  }

  return baseDifferences;
}
