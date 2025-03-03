import type { NextApiRequest, NextApiResponse } from 'next';

type ResponseData = {
  aiServiceConnected: boolean;
  error?: string;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<ResponseData>
) {
  if (req.method !== 'GET') {
    return res.status(405).json({
      aiServiceConnected: false,
      error: 'Method not allowed'
    });
  }

  try {
    const aiServiceUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${aiServiceUrl}/health`);
    
    if (!response.ok) {
      throw new Error(`AI service responded with status: ${response.status}`);
    }
    
    const data = await response.json();
    
    return res.status(200).json({
      aiServiceConnected: data.status === 'healthy'
    });
  } catch (error) {
    console.error('Error checking AI service:', error);
    return res.status(200).json({
      aiServiceConnected: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
} 