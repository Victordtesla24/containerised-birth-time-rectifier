/**
 * Utilities for Vercel deployment
 */

// Check if we're running on Vercel
export const isVercel = process.env.VERCEL === '1';

// Get the API URL
export const getApiUrl = () => {
  if (isVercel) {
    return process.env.NEXT_PUBLIC_API_URL || 'https://birth-time-rectifier.vercel.app/api';
  }

  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';
};

// Check if AI service is available
export async function isAiServiceAvailable() {
  try {
    const response = await fetch(`${getApiUrl()}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 2000, // 2 second timeout
    });

    return response.ok;
  } catch (error) {
    console.error('Error checking AI service:', error);
    return false;
  }
}

// Helper for handling API requests in Vercel
export async function handleApiRequest(handler, fallback, req, res) {
  try {
    return await handler(req, res);
  } catch (error) {
    console.error('API error:', error);

    if (fallback) {
      return fallback(req, res);
    }

    res.status(500).json({
      error: 'An error occurred processing your request',
      message: error.message,
    });
  }
}
