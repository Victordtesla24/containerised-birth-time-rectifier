import axios from 'axios';

// Environment variables for services
const AI_SERVICE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * API handler for questionnaire operations
 * 
 * This endpoint handles:
 * - Initializing the questionnaire with birth details (POST with birthData)
 * - Getting the next question based on previous answers (POST with questionResponses)
 * - Checking the analysis completion status (GET)
 */
export default async function handler(req, res) {
  try {
    // Handle different HTTP methods
    if (req.method === 'POST') {
      // Initialize questionnaire or submit response
      if (req.body.birthData) {
        return await initializeQuestionnaire(req, res);
      } else if (req.body.questionResponses) {
        return await getNextQuestion(req, res);
      } else {
        return res.status(400).json({ error: 'Invalid request body' });
      }
    } else if (req.method === 'GET') {
      // Check status or get completed analysis
      if (req.query.completed === 'true') {
        return await getCompletedAnalysis(req, res);
      } else {
        return await getCurrentStatus(req, res);
      }
    } else {
      return res.status(405).json({ error: 'Method not allowed' });
    }
  } catch (error) {
    console.error('Questionnaire API error:', error);
    
    // Check if it's a response error with status and data
    if (error.response) {
      return res.status(error.response.status).json({
        error: 'AI Service error',
        message: error.response.data.detail || error.message,
      });
    }
    
    // Generic error
    return res.status(500).json({
      error: 'Internal server error',
      message: error.message,
    });
  }
}

/**
 * Initialize a new questionnaire session with birth details
 */
async function initializeQuestionnaire(req, res) {
  const { birthData } = req.body;
  
  // Validate required birth data
  if (!birthData.birthDate || !birthData.approximateTime || !birthData.birthPlace) {
    return res.status(400).json({
      error: 'Missing required birth data',
      message: 'Birth date, time, and place are required',
    });
  }
  
  try {
    // Call AI service to initialize questionnaire
    const response = await axios.post(`${AI_SERVICE_URL}/api/initialize`, {
      birthDate: birthData.birthDate,
      birthTime: birthData.approximateTime,
      birthPlace: birthData.birthPlace,
      latitude: birthData.latitude,
      longitude: birthData.longitude,
      timezone: birthData.timezone,
      additionalFactors: birthData.lifeEvents ? { lifeEvents: birthData.lifeEvents } : {},
      notes: birthData.notes || "",
    });
    
    // Return the initial chart and first question
    return res.status(200).json({
      sessionId: response.data.sessionId,
      initialChart: response.data.initialChart,
      firstQuestion: response.data.firstQuestion,
      confidence: response.data.confidence
    });
  } catch (error) {
    console.error('Error initializing questionnaire:', error);
    throw error;
  }
}

/**
 * Get the next question based on previous responses
 */
async function getNextQuestion(req, res) {
  const { questionResponses, sessionId } = req.body;
  
  if (!sessionId || !questionResponses) {
    return res.status(400).json({
      error: 'Missing required data',
      message: 'Session ID and question responses are required',
    });
  }
  
  try {
    // Call AI service to get next question
    const response = await axios.post(`${AI_SERVICE_URL}/api/next-question`, {
      sessionId: sessionId,
      responses: questionResponses
    });
    
    // Return the next question or completion status
    return res.status(200).json({
      question: response.data.question,
      confidence: response.data.confidence,
      isComplete: response.data.isComplete,
      updatedChart: response.data.updatedChart
    });
  } catch (error) {
    console.error('Error getting next question:', error);
    throw error;
  }
}

/**
 * Get the current status of the questionnaire
 */
async function getCurrentStatus(req, res) {
  const { sessionId } = req.query;
  
  if (!sessionId) {
    return res.status(400).json({
      error: 'Missing session ID',
      message: 'Session ID is required',
    });
  }
  
  try {
    // Call AI service to get questionnaire status
    const response = await axios.get(`${AI_SERVICE_URL}/api/status?sessionId=${sessionId}`);
    
    // Return the questionnaire status
    return res.status(200).json({
      questionCount: response.data.questionCount,
      responseCount: response.data.responseCount,
      confidence: response.data.confidence,
      isComplete: response.data.isComplete,
      currentChart: response.data.currentChart
    });
  } catch (error) {
    console.error('Error getting questionnaire status:', error);
    throw error;
  }
}

/**
 * Get the completed analysis results
 */
async function getCompletedAnalysis(req, res) {
  const { sessionId } = req.query;
  
  if (!sessionId) {
    return res.status(400).json({
      error: 'Missing session ID',
      message: 'Session ID is required',
    });
  }
  
  try {
    // Call AI service to get completed analysis
    const response = await axios.get(`${AI_SERVICE_URL}/api/analysis?sessionId=${sessionId}`);
    
    // Check if analysis is complete
    if (!response.data.isComplete) {
      return res.status(400).json({
        error: 'Analysis not complete',
        message: 'The analysis has not reached sufficient confidence level yet',
      });
    }
    
    // Return the completed analysis
    return res.status(200).json(response.data);
  } catch (error) {
    console.error('Error getting completed analysis:', error);
    throw error;
  }
} 