/**
 * sessionStorage.ts
 * Utility for managing session storage data consistently across the application
 */

// Define interfaces for our stored data
export interface BirthDetails {
  birthDate: string;
  birthTime: string;
  birthPlace: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
  notes?: string;
}

export interface QuestionnaireSession {
  sessionId: string;
  questionHistory: any[];
  userResponses: Record<string, any>;
  confidence: number;
}

export interface AnalysisResults {
  rectifiedBirthTime: string;
  confidenceScore: number;
  chartData: any;
  interpretations: any[];
}

// Session storage keys
const KEYS = {
  BIRTH_DETAILS: 'birthTimeRectifier_birthDetails',
  QUESTIONNAIRE: 'birthTimeRectifier_questionnaire',
  ANALYSIS: 'birthTimeRectifier_analysis',
};

// Utility functions
const sessionStorage = {
  // Birth details
  saveBirthDetails: (data: BirthDetails): void => {
    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem(KEYS.BIRTH_DETAILS, JSON.stringify(data));
    }
  },
  
  getBirthDetails: (): BirthDetails | null => {
    if (typeof window !== 'undefined') {
      const data = window.sessionStorage.getItem(KEYS.BIRTH_DETAILS);
      return data ? JSON.parse(data) : null;
    }
    return null;
  },
  
  // Questionnaire session
  saveQuestionnaireSession: (data: QuestionnaireSession): void => {
    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem(KEYS.QUESTIONNAIRE, JSON.stringify(data));
    }
  },
  
  getQuestionnaireSession: (): QuestionnaireSession | null => {
    if (typeof window !== 'undefined') {
      const data = window.sessionStorage.getItem(KEYS.QUESTIONNAIRE);
      return data ? JSON.parse(data) : null;
    }
    return null;
  },
  
  // Analysis results
  saveAnalysisResults: (data: AnalysisResults): void => {
    if (typeof window !== 'undefined') {
      window.sessionStorage.setItem(KEYS.ANALYSIS, JSON.stringify(data));
    }
  },
  
  getAnalysisResults: (): AnalysisResults | null => {
    if (typeof window !== 'undefined') {
      const data = window.sessionStorage.getItem(KEYS.ANALYSIS);
      return data ? JSON.parse(data) : null;
    }
    return null;
  },
  
  // Clear all data
  clearAll: (): void => {
    if (typeof window !== 'undefined') {
      window.sessionStorage.removeItem(KEYS.BIRTH_DETAILS);
      window.sessionStorage.removeItem(KEYS.QUESTIONNAIRE);
      window.sessionStorage.removeItem(KEYS.ANALYSIS);
    }
  },
};

export default sessionStorage; 