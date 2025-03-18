import type { NextRequest } from 'next/server';
import type { NextResponse } from 'next/server';
import { withSessionRoute } from '@/lib/session';
import { logger } from '@/lib/logger';
import { validateBirthDetails } from '@/lib/validation';

/**
 * API endpoint to generate an astrological chart
 *
 * @param req - The request object
 * @param res - The response object
 */
export default withSessionRoute(async function handler(
  req: Request,
  res: Response
) {
  if (req.method !== 'POST') {
    return new Response(JSON.stringify({ message: 'Method not allowed' }), {
      status: 405,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  try {
    // Extract birth details from request body
    const body = await req.json();
    const {
      birthDate,
      birthTime,
      latitude,
      longitude,
      location,
      fullName,
      gender,
      options = {}
    } = body;

    // Validate required fields
    if (!birthDate || !birthTime) {
      return new Response(JSON.stringify({ message: 'Birth date and time are required' }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }

    // Validate birth details
    const validationResult = validateBirthDetails({
      birthDate,
      birthTime,
      latitude,
      longitude,
      location
    });

    if (!validationResult.isValid) {
      return new Response(JSON.stringify({ message: validationResult.message }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }

    // Normalize options with defaults
    const chartOptions = {
      houseSystem: options.houseSystem || 'W', // Whole Sign as default
      zodiacType: options.zodiacType || 'sidereal',
      ayanamsa: options.ayanamsa || 'lahiri',
      nodeType: options.nodeType || 'true',
      verifyWithOpenAI: options.verifyWithOpenAI !== false // Default to true
    };

    // Log request details
    logger.info('Generating chart', {
      birthDate,
      birthTime,
      location,
      options: chartOptions
    });

    // Call backend service to generate chart with the correct endpoint
    const response = await fetch(`${process.env.BACKEND_API_URL || 'http://localhost:8000'}/api/v1/chart/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.BACKEND_API_KEY || ''
      },
      body: JSON.stringify({
        birth_date: birthDate,
        birth_time: birthTime,
        latitude: parseFloat(latitude),
        longitude: parseFloat(longitude),
        location,
        full_name: fullName,
        gender,
        house_system: chartOptions.houseSystem,
        zodiac_type: chartOptions.zodiacType,
        ayanamsa: chartOptions.ayanamsa,
        node_type: chartOptions.nodeType,
        verify_with_openai: chartOptions.verifyWithOpenAI
      })
    });

    // Handle API response
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.message || `Failed to generate chart: ${response.status} ${response.statusText}`;
      logger.error('Chart generation failed', { status: response.status, error: errorMessage });
      return new Response(JSON.stringify({ message: errorMessage }), {
        status: response.status,
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }

    // Parse response data
    const chartData = await response.json();

    // Log verification status if available
    if (chartData.verification) {
      logger.info('Chart verification status', {
        status: chartData.verification.status,
        confidence: chartData.verification.confidence
      });
    }

    // Prepare response based on verification status
    let responseMessage = 'Chart generated successfully';
    let responseStatus = 200;

    if (chartData.verification) {
      const { status, confidence } = chartData.verification;

      if (status === 'verified') {
        responseMessage = `Chart verified with ${confidence}% confidence`;
      } else if (status === 'errors_found') {
        responseMessage = 'Chart generated with corrections';
        responseStatus = 206; // Partial Content
      } else if (status === 'verification_error') {
        responseMessage = 'Chart generated but verification failed';
        responseStatus = 207; // Multi-Status
      }
    }

    // Return chart data
    return new Response(JSON.stringify({
      message: responseMessage,
      chartId: chartData.chart_id || 'temp-chart',
      chartData
    }), {
      status: responseStatus,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    logger.error('Error generating chart', { error: (error as Error).message });
    return new Response(JSON.stringify({ message: 'Failed to generate chart' }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
});
