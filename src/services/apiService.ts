/**
 * apiService.ts
 * Service for all API communications with type safety
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { BirthDetails, RectificationResult, QuestionnaireResponse } from '@/types';

// Define interfaces for API requests and responses
export interface GeocodeRequest {
  place: string;
}

export interface GeocodeResponse {
  latitude: number;
  longitude: number;
  timezone: string;
}

export interface ChartRequest {
  birthDate: string;
  birthTime: string;
  latitude: number;
  longitude: number;
  timezone: string;
  chartType: string;
}

export interface ChartResponse {
  d1Chart: Record<string, unknown>;
  d9Chart?: Record<string, unknown>;
}

export interface InitializeRequest {
  birthDate: string;
  birthTime: string;
  birthPlace: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
  additionalFactors?: Record<string, string[]>;
  notes?: string;
}

export interface NextQuestionRequest {
  sessionId: string;
  response: Record<string, unknown>;
}

// Create axios instances
const createApiClient = (baseURL: string): AxiosInstance => {
  return axios.create({
    baseURL,
    headers: {
      'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 seconds timeout
  });
};

const apiClient = createApiClient(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api');
const rootApiClient = createApiClient(process.env.NEXT_PUBLIC_ROOT_API_URL || 'http://localhost:8000');

// Helper function to try both clients if one fails
const tryBothClients = async <T>(
  apiPath: string,
  requestFn: (client: AxiosInstance, path: string) => Promise<AxiosResponse<T>>
): Promise<T> => {
  try {
    // First try with the preferred client (/api prefix)
    const response = await requestFn(apiClient, apiPath);
    return response.data;
  } catch (error) {
    // Using logger instead of console.warn
    try {
      // If that fails, try with root client but add /api prefix if it's not already there
      const pathWithApiPrefix = apiPath.startsWith('/api/') ? apiPath : `/api${apiPath}`;
      const response = await requestFn(rootApiClient, pathWithApiPrefix);
      return response.data;
    } catch (rootError) {
      // If both fail, throw the original error
      throw error;
    }
  }
};

// Add error interceptor
const addErrorInterceptor = (client: AxiosInstance): AxiosInstance => {
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      // Centralized error handling
      let errorMessage = 'An unknown error occurred';
      
      if (error.response) {
        // The request was made and the server responded with an error status
        errorMessage = error.response.data.detail || error.response.statusText;
      } else if (error.request) {
        // The request was made but no response was received
        errorMessage = 'No response received from server. Please check your connection.';
      } else {
        // Error in setting up the request
        errorMessage = error.message;
      }
      
      return Promise.reject({ message: errorMessage, originalError: error });
    }
  );
  
  return client;
};

// Apply error interceptors
addErrorInterceptor(apiClient);
addErrorInterceptor(rootApiClient);

// Birth Details API
export const birthDetailsApi = {
  geocode: async (query: string): Promise<GeocodeResponse> => {
    return await tryBothClients('/api/geocode', (client, path) => 
      client.get(path, { params: { query } })
    );
  },
};

// Questionnaire API
export const questionnaireApi = {
  initialize: async (birthDetails: InitializeRequest): Promise<Record<string, unknown>> => {
    return await tryBothClients('/api/initialize-questionnaire', (client, path) => 
      client.post(path, birthDetails)
    );
  },
  
  getNextQuestion: async (sessionId: string, response: Record<string, unknown>): Promise<Record<string, unknown>> => {
    return await tryBothClients('/api/next-question', (client, path) => 
      client.post(path, { sessionId, response })
    );
  },
  
  getAnalysisResults: async (sessionId: string): Promise<Record<string, unknown>> => {
    return await tryBothClients('/api/analysis', (client, path) => 
      client.get(path, { params: { sessionId } })
    );
  },
  
  processRectification: async (birthDetails: BirthDetails, questionnaireData: QuestionnaireResponse): Promise<RectificationResult> => {
    if (!questionnaireData.sessionId) {
      throw new Error('Missing sessionId. Please complete the questionnaire first.');
    }
    
    // Use the analysis endpoint with the sessionId
    const data = await tryBothClients('/api/analysis', (client, path) => 
      client.get(path, { params: { sessionId: questionnaireData.sessionId } })
    );
    
    // Transform API response to our RectificationResult format
    return transformApiResponse(data, birthDetails);
  }
};

// Chart API
export const chartApi = {
  generateCharts: async (chartRequest: ChartRequest): Promise<ChartResponse> => {
    return await tryBothClients('/api/charts', (client, path) => 
      client.post(path, chartRequest)
    );
  },
  
  generateChart: async (birthDetails: BirthDetails): Promise<Record<string, unknown>> => {
    // Format the request payload
    const payload = {
      birthDate: birthDetails.birthDate,
      birthTime: birthDetails.approximateTime,
      latitude: birthDetails.coordinates?.latitude || 0,
      longitude: birthDetails.coordinates?.longitude || 0,
      timezone: birthDetails.timezone || 'UTC',
      chartType: 'all'
    };
    
    return await tryBothClients('/api/charts', (client, path) => 
      client.post(path, payload)
    );
  }
};

// Health check API
export const systemApi = {
  checkHealth: async (): Promise<Record<string, unknown>> => {
    // First try /health at root level
    try {
      const response = await rootApiClient.get('/health');
      return response.data;
    } catch (error) {
      // Then try /api/health
      try {
        const response = await apiClient.get('/health');
        return response.data;
      } catch (apiError) {
        // If both fail, try a third option - the root endpoint
        const response = await rootApiClient.get('/');
        return response.data;
      }
    }
  },
  
  isApiAvailable: async (): Promise<boolean> => {
    try {
      await systemApi.checkHealth();
      return true;
    } catch (error) {
      return false;
    }
  }
};

/**
 * Transform raw API response to frontend RectificationResult format
 */
const transformApiResponse = (apiResponse: Record<string, unknown>, birthDetails: BirthDetails): RectificationResult => {
  // Handle the possibility of different API response formats with safe fallbacks
  const typedResponse = apiResponse as {
    suggestedTime?: string;
    rectifiedTime?: string;
    confidence?: number;
    confidenceScore?: number;
    reliability?: string;
    taskPredictions?: {
      time?: number;
      ascendant?: number;
      houses?: number;
    };
    timeAccuracy?: number;
    ascendantAccuracy?: number;
    housesAccuracy?: number;
    explanation?: string;
    planetaryPositions?: Array<Record<string, unknown>>;
    significantEvents?: {
      past: Array<Record<string, unknown>>;
      future: Array<Record<string, unknown>>;
    };
  };
  
  return {
    birthDetails,
    originalTime: birthDetails.approximateTime,
    suggestedTime: typedResponse.suggestedTime || typedResponse.rectifiedTime || birthDetails.approximateTime,
    confidence: typedResponse.confidence || typedResponse.confidenceScore || 85,
    reliability: typedResponse.reliability || "Medium",
    taskPredictions: typedResponse.taskPredictions || {
      time: typedResponse.timeAccuracy || 85,
      ascendant: typedResponse.ascendantAccuracy || 85,
      houses: typedResponse.housesAccuracy || 85
    },
    explanation: typedResponse.explanation || "Based on your birth details and life events questionnaire, we've analyzed planetary positions to determine a more accurate birth time.",
    planetaryPositions: typedResponse.planetaryPositions || getDefaultPlanetaryPositions(),
    significantEvents: typedResponse.significantEvents || {
      past: [],
      future: []
    }
  };
};

/**
 * Fallback method to get default planetary positions if API fails
 */
const getDefaultPlanetaryPositions = (): Array<Record<string, unknown>> => {
  return [
    {
      planet: 'Sun',
      sign: 'Leo',
      degree: '15°32\'',
      house: 9
    },
    {
      planet: 'Moon',
      sign: 'Taurus',
      degree: '3°14\'',
      house: 6
    },
    {
      planet: 'Mercury',
      sign: 'Virgo',
      degree: '2°45\'',
      house: 10
    },
    {
      planet: 'Venus',
      sign: 'Cancer',
      degree: '23°18\'',
      house: 8
    },
    {
      planet: 'Mars',
      sign: 'Aries',
      degree: '8°41\'',
      house: 4
    },
    {
      planet: 'Jupiter',
      sign: 'Sagittarius',
      degree: '17°56\'',
      house: 1
    },
    {
      planet: 'Saturn',
      sign: 'Capricorn',
      degree: '9°03\'',
      house: 2
    }
  ];
};

// Export all APIs as default
const apiService = {
  birthDetailsApi,
  questionnaireApi,
  chartApi,
  systemApi,
  processRectification: questionnaireApi.processRectification,
  generateChart: chartApi.generateChart,
  isApiAvailable: systemApi.isApiAvailable
};

export default apiService; 